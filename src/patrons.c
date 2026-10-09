// Patrons: the pool, its rules (walk, catch a full mug, get pushed back, drink, send the empty back, leave
// through the door), spawning and the start patrons, tips and the dancers' show.
//
// The pool is structure-of-arrays (patron_x[p], ...) because the tests read and poke it by name. SDCC pays a
// 16-bit address computation (and usually a stack spill) for every patron_xxx[p], so the rules are written to
// touch few fields per patron per frame, and every question about "the other patrons on this bar" goes through
// per-bar lists instead of a scan of all 16 slots:
//   - bar_list[b] holds the live slots of bar b (in no particular order: patrons on a bar keep PATRON_SPACING px
//     apart, so their footprints never overlap and no rule depends on the order). It is kept up to date
//     incrementally: add_patron() appends, remove_patron() takes the entry out (patrons never change bars). It is
//     rebuilt from the pool (build_lists) only when lists_ok is clear: after clear_patrons(), or when a test has
//     poked patron_state / patron_bar between frames and set lists_dirty (tests/conftest.py does that for every
//     such write); the next frame then clears lists_ok. Users still skip an entry whose state is PATRON_NONE.
//   - catch_full() answers "who catches this full mug" from the bar's rightmost catcher, found once per bar per
//     frame (and again after a catch), so the usual case is one compare.
#include <gb/gb.h>
#include <stdint.h>

#include "game.h"
#include "music.h"

// patron pool
uint8_t  patron_state[MAX_PATRONS];    // PATRON_*
uint8_t  patron_bar[MAX_PATRONS];
uint8_t  patron_x[MAX_PATRONS];        // pixel x of the figure's left edge, 0..127 (screen coords)
uint8_t  patron_frac[MAX_PATRONS];     // sub-pixel fraction, 1/256 px
uint8_t  patron_draw[MAX_PATRONS];     // x it is drawn at (patron_x & ~1, +2 while swaying); 255 = not drawn yet
uint8_t  patron_variant[MAX_PATRONS];  // 0..2
uint8_t  patron_timer[MAX_PATRONS];
uint8_t  patron_aux[MAX_PATRONS];      // px left to be pushed back
uint8_t  patron_mug[MAX_PATRONS];      // mug slot held while pushed/drinking, NO_SLOT otherwise
uint8_t  patron_catchx[MAX_PATRONS];   // x of the last full mug it caught (where its tip would lie)
uint8_t  patron_dist[MAX_PATRONS];     // 1: watching the show (stands still, ignores mugs)
uint8_t  patrons_live;

// per-bar lists of live slots (slot order); see the top of the file
uint8_t  bar_list[NUM_BARS][MAX_PATRONS];
uint8_t  bar_n[NUM_BARS];
uint8_t  lists_ok;
uint8_t  lists_dirty;                  // test hook: patron_state / patron_bar were written behind the game's back

// Fair empties: an empty is only sent when it arrives at the bartender's end no sooner than empty_gap frames
// after the last one scheduled. next_arrival = frames from now until the earliest moment the next empty may
// arrive (the last scheduled arrival + empty_gap), counting down to 0.
uint16_t next_arrival;

// the rightmost patron of each bar who would catch a full mug (walking, not watching the show)
static uint8_t catch_p[NUM_BARS], catch_x[NUM_BARS];
static uint8_t catch_ok;               // bit b: catch_p/catch_x of bar b are up to date

// Sway phases by timer value: bit 0 = (t / SWAY_FRAMES) & 1 (drinking), bit 1 = (t / DIST_BOB) & 1 (watching
// the show). A table: SDCC's 8-bit divide is a ~100-cycle call, and this is asked for every drinker every frame.
#define SWAY(t)   ((uint8_t)((((t) / SWAY_FRAMES) & 1) | ((((t) / DIST_BOB) & 1) << 1)))
#define SWAY4(n)  SWAY(n), SWAY((n) + 1), SWAY((n) + 2), SWAY((n) + 3)
#define SWAY16(n) SWAY4(n), SWAY4((n) + 4), SWAY4((n) + 8), SWAY4((n) + 12)
#define SWAY64(n) SWAY16(n), SWAY16((n) + 16), SWAY16((n) + 32), SWAY16((n) + 48)
static const uint8_t sway_tab[256] = { SWAY64(0), SWAY64(64), SWAY64(128), SWAY64(192) };

static void list_add(uint8_t p) {
    uint8_t b = patron_bar[p] & (NUM_BARS - 1);
    bar_list[b][bar_n[b]++] = p;
}

void build_lists(void) {
    uint8_t p;
    bar_n[0] = bar_n[1] = bar_n[2] = bar_n[3] = 0;
    for (p = 0; p != MAX_PATRONS; p++)
        if (patron_state[p] != PATRON_NONE) list_add(p);
    lists_ok = 1;
}

// Where patron p is drawn: its position at 2 px granularity, +2 px on alternate beats while drinking (sway)
// or watching the show (bob).
static uint8_t drawn_x(uint8_t p) {
    uint8_t x = patron_x[p] & 0xFE, w = sway_tab[patron_timer[p]];
    if (patron_state[p] == PATRON_DRINKING && (w & 1)) x += 2;
    else if (patron_dist[p] && (w & 2)) x += 2;
    return x;
}

// p is now drawn at nd: mark the columns it leaves and the ones it covers.
// (Only a change of columns changes the CGB attributes: moving within his columns he changes tile ids only.)
static void redraw_at(uint8_t p, uint8_t nd) {
    uint8_t od = patron_draw[p], lo, hi;
    patron_draw[p] = nd;
    if (od == 255) { mark_dirty_attrs(patron_bar[p], nd >> 3, (nd >> 3) + 3); return; }
    if (nd < od) { lo = nd; hi = od; } else { lo = od; hi = nd; }
    lo >>= 3; hi >>= 3;
    if (lo == hi) mark_dirty(patron_bar[p], lo, lo + 3);
    else mark_dirty_attrs(patron_bar[p], lo, hi + 3);
}

static void refresh_patron(uint8_t p) {
    uint8_t nd = drawn_x(p);
    if (nd != patron_draw[p]) redraw_at(p, nd);
}

uint8_t add_patron(uint8_t b, uint8_t x, uint8_t variant) {
    uint8_t p;
    for (p = 0; p < MAX_PATRONS; p++) {
        if (patron_state[p] != PATRON_NONE) continue;
        patron_state[p] = PATRON_WALKING;
        patron_bar[p] = b; patron_x[p] = x; patron_frac[p] = 0; patron_variant[p] = variant;
        patron_timer[p] = 0; patron_aux[p] = 0; patron_mug[p] = NO_SLOT;
        patron_dist[p] = 0; patron_catchx[p] = x;
        patron_draw[p] = 255;
        refresh_patron(p);
        if (lists_ok) list_add(p);
        return 1;
    }
    return 0;
}

static void free_held_mug(uint8_t p) {
    uint8_t m = patron_mug[p];
    if (m != NO_SLOT && mug_state[m] == MUG_HELD) {
        mug_state[m] = MUG_FREE;
        if (mugs_live) mugs_live--;
    }
    patron_mug[p] = NO_SLOT;
}

// Take slot p out of its bar's list (the last entry moves into its place).
static void list_remove(uint8_t p) {
    uint8_t b = patron_bar[p] & (NUM_BARS - 1), n = bar_n[b];
    uint8_t *q = bar_list[b];
    for (; n; n--, q++) {
        if (*q != p) continue;
        *q = bar_list[b][--bar_n[b]];
        return;
    }
}

void remove_patron(uint8_t p) {
    uint8_t d = patron_draw[p] >> 3;
    patron_state[p] = PATRON_NONE;
    if (lists_ok) list_remove(p);
    free_held_mug(p);
    if (patron_draw[p] != 255) mark_dirty_attrs(patron_bar[p], d, d + 3);
    patron_draw[p] = 255;
}

void clear_patrons(void) {
    uint8_t p;
    for (p = 0; p < MAX_PATRONS; p++) patron_state[p] = PATRON_NONE;
    lists_ok = 0;
}

// A served patron may leave a tip where it last caught a mug: not while a tip lies there or a show runs.
static void maybe_tip(uint8_t p) {
    if (tip_timer || show_timer) return;
    if (!tip_chance || (tip_chance != 255 && next_rand() >= tip_chance)) return;   // 0 never (and draws no random number)
    tip_timer = TIP_FRAMES;
    tip_bar = patron_bar[p];
    tip_x = patron_catchx[p];
}

void end_show(void) {
    uint8_t p;
    show_timer = 0;
    for (p = 0; p < MAX_PATRONS; p++) { patron_dist[p] = 0; patron_timer[p] = 0; }
    if (spawn_timer > (spawn_interval / SHOW_SPAWN_DIV)) spawn_timer = spawn_interval / SHOW_SPAWN_DIV;   // new patrons come sooner, once
}

// The tip is picked up: each walking patron is distracted with probability 1/2 (at least one if any walk).
void start_show(void) {
    uint8_t p, any = 0, first = NO_SLOT;
    show_timer = SHOW_FRAMES;
    dancer_frame = 0; dance_tick = 0;
    for (p = 0; p < MAX_PATRONS; p++) {
        patron_dist[p] = 0;
        if (patron_state[p] != PATRON_WALKING) continue;
        if (first == NO_SLOT) first = p;
        if (next_rand() & 0x40) { patron_dist[p] = 1; patron_timer[p] = 0; any = 1; }
    }
    if (!any && first != NO_SLOT) { patron_dist[first] = 1; patron_timer[first] = 0; }
}

// Is another patron of bar b within PATRON_SPACING px ahead of x (to the right), so that a walker at x may not
// step one px right? (The walker itself is never strictly ahead of its own x.)
static uint8_t blocked_ahead(uint8_t b, uint8_t x) {
    const uint8_t *q;
    uint8_t n, s, qx;
    if (!lists_ok) build_lists();
    q = bar_list[b];
    for (n = bar_n[b]; n; n--) {
        s = *q++;
        if (patron_state[s] == PATRON_NONE) continue;
        qx = patron_x[s];
        if (qx > x && (uint8_t)(qx - x) <= PATRON_SPACING) return 1;
    }
    return 0;
}

// ... or behind (to the left), so that a pushed patron at x may not slide one px left?
static uint8_t blocked_behind(uint8_t b, uint8_t x) {
    const uint8_t *q;
    uint8_t n, s, qx;
    if (!lists_ok) build_lists();
    q = bar_list[b];
    for (n = bar_n[b]; n; n--) {
        s = *q++;
        if (patron_state[s] == PATRON_NONE) continue;
        qx = patron_x[s];
        if (qx < x && (uint8_t)(x - qx) <= PATRON_SPACING) return 1;
    }
    return 0;
}

// ---- catching full mugs -------------------------------------------------------------------------
// Per bar and per frame, found when first asked: the rightmost catcher (walking, not watching the show; the
// highest x, the lowest slot among equals) in catch_p/catch_x, and catch_lim = his x + 16, or 0 if nobody on
// the bar would catch. A full mug at x >= catch_lim cannot be caught by anyone on that bar this frame (every
// other catcher's 16 px end at or before his), which is the test mugs.c makes for every full mug; only a mug
// below it comes here. 255 = not known yet this frame.
uint8_t catch_lim[NUM_BARS];

void begin_catch_frame(void) {
    catch_ok = 0;
    catch_lim[0] = catch_lim[1] = catch_lim[2] = catch_lim[3] = 255;
}

static uint8_t fc_best, fc_x;

static void catcher_candidate(uint8_t s) {
    uint8_t l;
    if (patron_state[s] != PATRON_WALKING || patron_dist[s]) return;    // distracted: the mug slides past
    l = patron_x[s];
    if (fc_best == NO_SLOT || l > fc_x) { fc_best = s; fc_x = l; }
}

static void find_catcher(uint8_t b) {
    const uint8_t *q;
    uint8_t n;
    if (!lists_ok) build_lists();
    fc_best = NO_SLOT; fc_x = 0;
    q = bar_list[b];
    for (n = bar_n[b]; n; n--, q++) catcher_candidate(*q);
    catch_p[b] = fc_best; catch_x[b] = fc_x;
    catch_lim[b] = fc_best == NO_SLOT ? 0 : fc_x >= 256 - PATRON_W ? 255 : fc_x + PATRON_W;
    catch_ok |= bar_bit[b];
}

// The catcher with the highest x <= the mug's x whose 16 px contain it (the general rule; only needed when the
// mug is already left of the bar's rightmost catcher, i.e. it slid past him while he was busy).
static uint8_t scan_catcher(uint8_t b, uint8_t x) {
    const uint8_t *q = bar_list[b];
    uint8_t n, s, l, best = NO_SLOT, bx = 0;
    for (n = bar_n[b]; n; n--) {
        s = *q++;
        if (patron_state[s] != PATRON_WALKING || patron_dist[s]) continue;
        l = patron_x[s];
        if (x >= l && (uint8_t)(x - l) < PATRON_W && (best == NO_SLOT || l > bx)) { best = s; bx = l; }
    }
    return best;
}

// He catches mug i: it stays in his hand (MUG_HELD) and he is pushed back.
static void caught(uint8_t i, uint8_t p) {
    patron_state[p] = PATRON_PUSHED;
    patron_timer[p] = 0;
    patron_aux[p] = pushback_px;
    patron_frac[p] = 0;
    patron_mug[p] = i;
    patron_catchx[p] = mug_x[i];
    mug_state[i] = MUG_HELD;
    mug_patron[i] = p;
}

// Full mug i at mug_x[i] reaches the rightmost walking patron whose 16 px contain it: he catches it.
uint8_t catch_full(uint8_t i) {
    uint8_t b = mug_bar[i], x, p;
    if (b >= NUM_BARS) return 0;
    if (!(catch_ok & bar_bit[b])) {
        find_catcher(b);
        if (mug_x[i] >= catch_lim[b]) return 0;
    }
    p = catch_p[b];
    if (p == NO_SLOT) return 0;
    x = mug_x[i];
    if (x < catch_x[b]) {
        p = scan_catcher(b, x);
        if (p == NO_SLOT) return 0;
    }
    caught(i, p);
    catch_ok &= ~bar_bit[b];                     // he no longer catches: find the bar's next one when asked
    catch_lim[b] = 255;
    return 1;
}

// ---- spawning ------------------------------------------------------------------------------------
// New patron at the door of a random bar, if its first PATRON_SPACING px are free.
static uint8_t try_spawn(void) {
    uint8_t b = (next_rand() >> 2) & 3, n, s, v;
    const uint8_t *q;
    if (!lists_ok) build_lists();
    q = bar_list[b];
    for (n = bar_n[b]; n; n--) {
        s = *q++;
        if (patron_state[s] != PATRON_NONE && patron_x[s] < PATRON_SPACING) return 0;
    }
    v = next_rand() % 3;
    if (!add_patron(b, 0, v)) return 0;
    spawned++;
    return 1;
}

// Put the level's start patrons on the bars (2nd group 32 px on where the level has two),
// but never more than the quota still to serve.
void place_start_patrons(void) {
    uint8_t b, k, placed = 0, remaining = quota > served ? quota - served : 0;
    for (k = 0; k < start_per_bar; k++)
        for (b = 0; b < NUM_BARS; b++)
            if ((start_mask & bar_bit[b]) && placed < remaining) { add_patron(b, PATRON_SPACING * k, next_rand() % 3); placed++; }
    spawned = served + placed;
    patrons_live = placed;
}

// ---- the frame ----------------------------------------------------------------------------------------
// One small function per state: SDCC keeps the slot number in a register in a function this size, so each
// patron_xxx[p] is a 16-bit add and a load (one big loop body spills everything to the stack instead).
// Each returns 1 while the patron stays.
static uint8_t go_now;                // the intro delay is over: walkers walk

// A walker's whole pixel: blocked, one px on, or at the tap (a life). Returns 0 when he is gone.
static uint8_t walker_pixel(uint8_t p, uint8_t f) {
    uint8_t x = patron_x[p];
    if (blocked_ahead(patron_bar[p], x)) return 1;      // waits (the fraction stays where it was)
    patron_frac[p] = f;
    patron_x[p] = ++x;
    if (x >= PATRON_FAR_X) {                              // reached the tap
        remove_patron(p);
        lose_life();
        return 0;
    }
    return 1;
}

static uint8_t walking_step(uint8_t p) {
    uint8_t f, o;
    if (patron_dist[p]) {                                 // watching the show: no walking, just the bob
        patron_timer[p]++;
        refresh_patron(p);
        return 1;
    }
    if (go_now) {
        o = patron_frac[p];
        f = o + patron_speed;
        if (f < o) {                                      // carried: one whole pixel
            if (!walker_pixel(p, f)) return 0;
        } else {
            patron_frac[p] = f;
        }
    }
    o = patron_x[p] & 0xFE;                               // drawn_x() of a walker who is not watching the show
    if (o != patron_draw[p]) redraw_at(p, o);
    return 1;
}

static void start_drinking(uint8_t p) {
    patron_state[p] = PATRON_DRINKING;
    patron_timer[p] = 0;
}

static void served_out(uint8_t p) {                       // pushed out through the door: served
    remove_patron(p);
    served++;
    add_score(serve_score);
    SFX(SFX_SERVE);
    maybe_tip(p);
}

// One px toward the door, unless someone stands right behind: then he stays put and drinks.
static void push_px(uint8_t p) {
    if (blocked_behind(patron_bar[p], patron_x[p])) {
        patron_aux[p] = 0;
        start_drinking(p);
        return;
    }
    patron_x[p] -= PUSH_SPEED;
    if ((patron_aux[p] -= PUSH_SPEED) == 0) start_drinking(p);
}

// Pushed back by a caught mug: one px a frame toward the door, then he drinks.
static uint8_t pushed_step(uint8_t p) {
    if (patron_aux[p] == 0) start_drinking(p);
    else if (patron_x[p] == 0) { served_out(p); return 0; }
    else push_px(p);
    refresh_patron(p);
    return 1;
}

// May patron p send his empty now? Its predicted arrival at the bartender's end (frames from now: the px from
// where it starts to TAP_X, EMPTY_STEP_FRAMES each) must be no sooner than next_arrival; if so, it is scheduled.
static uint8_t empty_may_go(uint8_t p) {
    uint8_t x = patron_x[p] + PATRON_W;                    // where the empty starts
    uint16_t t = x >= TAP_X ? 0 : (uint16_t)(uint8_t)(TAP_X - x) * EMPTY_STEP_FRAMES;
    if (t < next_arrival) return 0;
    next_arrival = t + empty_gap;
    return 1;
}

// Done drinking: the empty slides out to the right and he walks on.
static void drink_done(uint8_t p) {
    uint8_t m = patron_mug[p];
    if (m != NO_SLOT && mug_state[m] == MUG_HELD) {
        mug_state[m] = MUG_EMPTY;
        mug_x[m] = patron_x[p] + PATRON_W;
        mug_timer[m] = 0;                                 // (its half-px step phase, see mugs.c)
    }
    patron_mug[p] = NO_SLOT;
    patron_state[p] = PATRON_WALKING;
    patron_timer[p] = 0;
}

// Drinking; at the end he holds the empty (last pose, standing still) until it may go (fair empties).
static uint8_t drinking_step(uint8_t p) {
    uint8_t t = patron_timer[p] + 1, m;
    if (t < DRINK_FRAMES) patron_timer[p] = t;
    else {
        m = patron_mug[p];
        if (m != NO_SLOT && mug_state[m] == MUG_HELD && !empty_may_go(p))
            return 1;                                     // holds the empty: the pose is frozen, nothing to redraw
        drink_done(p);
    }
    refresh_patron(p);
    return 1;
}

void update_patrons(void) {
    uint8_t p, st, live = 0;

    if (next_arrival) next_arrival--;
    go_now = (intro_timer == 0);
    if (!go_now) {
        if (intro_timer) intro_timer--;
    } else if (spawned < quota) {
        if (spawn_timer) spawn_timer--;
        else spawn_timer = try_spawn() ? spawn_interval : SPAWN_RETRY;
    }

    for (p = 0; p != MAX_PATRONS; p++) {
        st = patron_state[p];
        if (st == PATRON_NONE) continue;
        if (st == PATRON_WALKING) live += walking_step(p);
        else if (st == PATRON_PUSHED) live += pushed_step(p);
        else live += drinking_step(p);
    }
    patrons_live = live;
    if (spawned >= quota && patrons_live == 0 && mugs_live == 0) level_clear = 1;
}
