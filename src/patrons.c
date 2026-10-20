// Patrons: the pool, its rules (walk in from the screen's left edge, catch a full mug, get pushed back, drink, send the
// empty back, slide out past the left edge when served), spawning and the start patrons, tips and the dancers' show.
//
// The pool is structure-of-arrays (patron_x[p], ...) because the tests read and poke it by name. SDCC pays a
// 16-bit address computation (and usually a stack spill) for every patron_xxx[p], so the rules are written to
// touch few fields per patron per frame, and every question about "the other patrons on this bar" goes through
// per-bar lists instead of a scan of all 16 slots:
//   - bar_list[b] holds the live slots of bar b (in no particular order: no rule depends on it; M13b patrons may
//     overlap, and lift.c / render.c decide who is drawn over whom). It is kept up to date
//     incrementally: add_patron() appends, remove_patron() takes the entry out (patrons never change bars). It is
//     rebuilt from the pool (build_lists) only when lists_ok is clear: after clear_patrons(), or when a test has
//     poked patron_state / patron_bar between frames and set lists_dirty (tests/conftest.py does that for every
//     such write); the next frame then clears lists_ok. Users still skip an entry whose state is PATRON_NONE.
//   - catch_full() answers "who catches this full mug" from the bar's rightmost catcher, found once per bar per
//     frame (and again after a catch), so the usual case is one compare.
#include <gb/gb.h>
#include <stdint.h>

#include "game.h"
#include "asm_cfg.h"
#include "music.h"

// patron pool
uint8_t  patron_state[MAX_PATRONS];    // PATRON_*
uint8_t  patron_bar[MAX_PATRONS];
uint8_t  patron_x[MAX_PATRONS];        // pixel x of the figure's left edge, 0..127 (screen coords)
uint8_t  patron_frac[MAX_PATRONS];     // sub-pixel fraction, 1/256 px
uint8_t  patron_draw[MAX_PATRONS];     // x it is drawn at (patron_x, +2 while swaying; | DRAW_BACK in its back view); 255 = not drawn yet
uint8_t  patron_variant[MAX_PATRONS];  // 0..2
uint8_t  patron_timer[MAX_PATRONS];
uint8_t  patron_aux[MAX_PATRONS];      // PUSHED: px left to be pushed back; DRINKING: DRINK_MIN / DRINK_WAIT / DRINK_WINDUP (M8d);
                                       // WALKING (entering) / LEAVING: px of him beyond the screen's left edge (game.h ENTRY_X)
uint8_t  patron_mug[MAX_PATRONS];      // mug slot held while pushed/drinking, NO_SLOT otherwise
uint8_t  patron_catchx[MAX_PATRONS];   // x of the last full mug it caught (where its tip would lie)
uint8_t  patron_drinks[MAX_PATRONS];    // mugs caught since spawning: the push-back is pushback_px times this (thirst)
uint8_t  patron_dist[MAX_PATRONS];     // 1: distracted by the show (shuffles to a multiple of 8 px, then stands still; ignores mugs)
uint8_t  patron_facing[MAX_PATRONS];   // 1: drawn in its back view, turned to watch the stage (mirrors patron_draw & DRAW_BACK)
uint8_t  patrons_live;
uint8_t  patron_hurry[MAX_PATRONS];    // M13b: 1 = a hurried walker (hurry_speed instead of patron_speed)
uint8_t  hurry_speed;                  // this level's hurried walking speed (1/256 px per frame); 0: nobody hurries

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

// Sway phase by timer value: (t / SWAY_FRAMES) & 1 (drinking). A table: SDCC's 8-bit divide is a ~100-cycle
// call, and this is asked for every drinker every frame.
#define SWAY(t)   ((uint8_t)((t) < WINDUP_T0 && (((t) / SWAY_FRAMES) & 1)))   // (M8d: he stands still while he winds up)
#define SWAY4(n)  SWAY(n), SWAY((n) + 1), SWAY((n) + 2), SWAY((n) + 3)
#define SWAY16(n) SWAY4(n), SWAY4((n) + 4), SWAY4((n) + 8), SWAY4((n) + 12)
#define SWAY64(n) SWAY16(n), SWAY16((n) + 16), SWAY16((n) + 32), SWAY16((n) + 48)
const uint8_t sway_tab[256] = { SWAY64(0), SWAY64(64), SWAY64(128), SWAY64(192) };

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

// Where patron p is drawn (pushed back or drinking): its position, +2 px on alternate beats while drinking (sway).
// (draw_mask, P4: 0xFE on a DMG mixed level, where the patrons are drawn at even x only: mirror.c)
static uint8_t drawn_x(uint8_t p) {
    uint8_t x = patron_x[p] & draw_mask;
    if (patron_state[p] == PATRON_DRINKING && sway_tab[patron_timer[p]]) x += 2;
    return x;
}

// p is now drawn at nd (| DRAW_BACK: in its back view): mark the columns it leaves and the ones it covers.
// (Only a change of columns changes the CGB attributes: moving within his columns, or turning round, he changes
// tile ids only.)
void redraw_at(uint8_t p, uint8_t nd) {
    uint8_t od = patron_draw[p], lo, hi;
    patron_draw[p] = nd;
    patron_facing[p] = nd >> 7;
    if (od == 255) { nd &= ~DRAW_BACK; mark_dirty_attrs(patron_bar[p], nd >> 3, (nd >> 3) + 3); ovl_touch(p); return; }
    if (!((od | nd) & DRAW_BACK) && (od >> 3) == (nd >> 3)) {          // a step within his columns
        if (!(od & 7)) ovl_touch(p);                  // (off shift 0: 2 -> 3 real columns; the other way can only end an overlap)
        mark_quick(p);
        return;
    }
    nd &= ~DRAW_BACK; od &= ~DRAW_BACK;
    if (nd < od) { lo = nd; hi = od; } else { lo = od; hi = nd; }
    lo >>= 3; hi >>= 3;
    if (lo == hi) mark_dirty(patron_bar[p], lo, lo + 3);
    else mark_dirty_attrs(patron_bar[p], lo, hi + 3);
    ovl_touch(p);
}

static void refresh_patron(uint8_t p) {
    uint8_t nd = drawn_x(p);
    if (nd != patron_draw[p]) redraw_at(p, nd);
}

// (Split in two so SDCC keeps the slot in a register while it fills the fields: add_patron runs on a spawn frame,
// usually the busiest of all.)
static uint8_t np_b, np_x, np_v, np_h, np_p;
static void init_patron(uint8_t p) {
    np_p = p;
    patron_state[p] = PATRON_WALKING;
    patron_bar[p] = np_b; patron_x[p] = np_x; patron_frac[p] = 0; patron_variant[p] = np_v;
    patron_hurry[p] = np_h; np_h = 0;
    patron_lift[p] = LIFT_BG;                         // (M13c: lift_spawn needs it; a test may have emptied a lifted slot)
    patron_timer[p] = 0; patron_aux[p] = 0; patron_mug[p] = NO_SLOT;
    patron_dist[p] = 0; patron_facing[p] = 0; patron_catchx[p] = np_x; patron_drinks[p] = 0;
    patron_shove[p] = patron_stag[p] = 0;             // (the mosh pit, src/mosh.c: a slot's old shove is not his)
    patron_draw[p] = np_x & draw_mask;                // drawn where he stands, facing the bar: his 3 columns change
    np_x >>= 3;
    mark_dirty_attrs(np_b, np_x, np_x + 3);
    if (lists_ok) list_add(p);
    ovl_touch(p);
}

uint8_t add_patron(uint8_t b, uint8_t x, uint8_t variant) {
    const uint8_t *s = patron_state;
    uint8_t p = 0;
    while (*s != PATRON_NONE) {                       // the first free slot
        s++;
        if (++p == MAX_PATRONS) return 0;
    }
    np_b = b; np_x = x; np_v = variant;
    init_patron(p);
    return 1;
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
    uint8_t d = (patron_draw[p] & ~DRAW_BACK) >> 3;
    if (patron_ovl[p] | lift_n[patron_bar[p] & (NUM_BARS - 1)]) ovl_dirty |= bar_bit[patron_bar[p] & (NUM_BARS - 1)];
    patron_state[p] = PATRON_NONE;
    patron_lift[p] = LIFT_BG;                         // (a lifted one's sprite goes with the next draw_lifted; lift.c recounts)
    if (lists_ok) list_remove(p);
    free_held_mug(p);
    if (patron_draw[p] != 255) mark_dirty_attrs(patron_bar[p], d, d + 3);
    patron_draw[p] = 255;
}

void clear_patrons(void) {
    uint8_t p;
    for (p = 0; p < MAX_PATRONS; p++) { patron_state[p] = PATRON_NONE; patron_lift[p] = LIFT_BG; }
    lift_n[0] = lift_n[1] = lift_n[2] = lift_n[3] = 0; lift_total = 0; ovl_bars = 0;
    lists_ok = 0;
}

// A patron whose mug is going to serve him (the push carries him off the left edge) may tip: the coin drops under him where he
// stands as the mug lands and the push takes him away, so it is his and shows while he is still on the screen (owner 2026-10-17: it
// used to appear after he was gone). Not while a tip lies there, nor while a show runs, unless the pocket is on and empty (pocket.c).
void maybe_tip(uint8_t p) {              // (level.c push_for: the push that serves him)
    if (tip_timer || tip_first || (show_timer && tip_pocket != TILE_HUD_BLANK)) return;   // (CLASSIC: not before the level's first tip, send_empty)
    if (!tip_chance || (tip_chance != 255 && next_rand() >= tip_chance)) return;   // 0 never (and draws no random number)
    tip_timer = TIP_FRAMES;
    tip_bar = patron_bar[p];
    tip_x = patron_x[p] + 4;                            // (centred under him, as classic_tip puts the first one)
}

// M13b: patrons overlap. A patron's real columns are c = draw >> 3 (without DRAW_BACK) and c + 1, and c + 2 unless he
// stands on a multiple of 8 (shift 0, or his back view). col_scan(b, k, p): how many patrons of bar b other than p
// cover column k; cs_dist is set when one of them is distracted by the show (he cannot be lifted, lift.c).
uint8_t cs_dist;
uint8_t col_scan(uint8_t b, uint8_t k, uint8_t p) {
    const uint8_t *q;
    uint8_t n, s, d, cnt = 0;
    if (!lists_ok) build_lists();
    cs_dist = 0;
    q = bar_list[b];
    for (n = bar_n[b]; n; n--) {
        s = *q++;
        if (s == p || patron_state[s] == PATRON_NONE || (d = patron_draw[s]) == 255) continue;
        d &= ~DRAW_BACK;
        if (k < (d >> 3)) continue;
        if ((uint8_t)(k - (d >> 3)) >= 2 && ((uint8_t)(k - (d >> 3)) != 2 || !(d & 7))) continue;
        cnt++;
        cs_dist |= patron_dist[s];
    }
    return cnt;
}

// Is another patron of bar b within PATRON_SPACING px behind x (to the left)? (The spawn check: one entering or leaving
// at the left end counts, he stands at x 0..16.)
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

#if ASM_SCANS
// find_catcher and scan_catcher, hand-written (asm pass batch 4; the C versions are under #else, the reference). Both walk a bar's
// list; the C pays a call (can_catch / catcher_candidate) and several 16-bit address sums per patron (~150 T), here ~90.
// fc_best / fc_x are the walk's scratch (dead after the call; scan_catcher borrows them too). The test of "who catches" is the
// C can_catch: a walker with dist | aux == 0, or a drinker with aux != DRINK_MIN; inlined in both loops.
#if NUM_BARS != 4 || MAX_PATRONS != 16 || PATRON_W != 16 || NO_SLOT != 255
#error "find_catcher / scan_catcher: the constants written into the asm"
#endif
typedef char catch_enums[(PATRON_WALKING == 1 && PATRON_DRINKING == 3 && DRINK_MIN == 0) ? 1 : -1];
static uint8_t fc_best, fc_x;

static void find_catcher(uint8_t b) __naked {
    (void)b;
__asm
    ld   c, a               ; c = bar
    ld   a, (_lists_ok)
    or   a, a
    jr   nz, 1$
    push bc
    call _build_lists
    pop  bc
1$:
    push bc                 ; (the bar, kept for the stores below)
    ld   b, #0
    ld   hl, #_bar_n
    add  hl, bc
    ld   e, #255            ; e = best (NO_SLOT)
    xor  a, a
    ld   (_fc_x), a         ; fc_x = 0
    ld   a, (hl)
    or   a, a
    jr   z, 9$
    ld   d, a               ; d = patrons left
    ld   a, c               ; hl = bar_list + 16 * bar
    swap a
    add  a, #<_bar_list
    ld   l, a
    ld   a, #>_bar_list
    adc  a, #0
    ld   h, a
2$:
    ld   a, (hl+)
    push hl
    ld   c, a               ; c = slot
    ld   hl, #_patron_state ; (can_catch, inlined: a walker with dist | aux == 0, or a drinker past DRINK_MIN)
    add  hl, bc
    ld   a, (hl)
    cp   a, #1
    jr   nz, 6$
    ld   hl, #_patron_dist
    add  hl, bc
    ld   a, (hl)
    ld   hl, #_patron_aux
    add  hl, bc
    or   a, (hl)
    jr   nz, 3$
    jr   10$
6$:
    cp   a, #3
    jr   nz, 3$
    ld   hl, #_patron_aux
    add  hl, bc
    ld   a, (hl)
    or   a, a
    jr   z, 3$
10$:
    ld   hl, #_patron_x
    add  hl, bc
    ld   a, (hl)            ; a = his x
    inc  e
    jr   z, 4$              ; (no best yet: he is it)
    dec  e
    ld   hl, #_fc_x
    cp   a, (hl)
    jr   c, 3$
    jr   z, 3$              ; (higher only: the lowest slot among equals)
4$:
    ld   e, c
    ld   (_fc_x), a
3$:
    pop  hl
    dec  d
    jr   nz, 2$
9$:
    pop  bc                 ; c = bar
    ld   b, #0
    ld   hl, #_catch_p
    add  hl, bc
    ld   (hl), e
    ld   a, (_fc_x)
    ld   d, a
    ld   hl, #_catch_x
    add  hl, bc
    ld   (hl), a
    ld   a, e               ; lim: 0 with no catcher, 255 from x = 240, else x + 16
    inc  a
    ld   a, #0
    jr   z, 5$
    ld   a, d
    add  a, #16
    jr   nc, 5$
    ld   a, #255
5$:
    ld   hl, #_catch_lim
    add  hl, bc
    ld   (hl), a
    ld   hl, #_bar_bit
    add  hl, bc
    ld   a, (_catch_ok)
    or   a, (hl)
    ld   (_catch_ok), a
    ret
__endasm;
}

static uint8_t scan_catcher(uint8_t b, uint8_t x) __naked {
    (void)b; (void)x;
__asm
    ld   c, a               ; c = bar, e = the mug's x
    ld   b, #0
    ld   hl, #_bar_n
    add  hl, bc
    ld   a, #255
    ld   (_fc_best), a
    ld   a, (hl)
    or   a, a
    jr   nz, 1$
    ld   a, #255            ; (an empty bar: NO_SLOT)
    ret
1$:
    ld   d, a               ; d = patrons left
    ld   a, c
    swap a
    add  a, #<_bar_list
    ld   l, a
    ld   a, #>_bar_list
    adc  a, #0
    ld   h, a
2$:
    ld   a, (hl+)
    push hl
    ld   c, a
    ld   hl, #_patron_state ; (can_catch, inlined: a walker with dist | aux == 0, or a drinker past DRINK_MIN)
    add  hl, bc
    ld   a, (hl)
    cp   a, #1
    jr   nz, 6$
    ld   hl, #_patron_dist
    add  hl, bc
    ld   a, (hl)
    ld   hl, #_patron_aux
    add  hl, bc
    or   a, (hl)
    jr   nz, 3$
    jr   10$
6$:
    cp   a, #3
    jr   nz, 3$
    ld   hl, #_patron_aux
    add  hl, bc
    ld   a, (hl)
    or   a, a
    jr   z, 3$
10$:
    ld   hl, #_patron_x
    add  hl, bc
    ld   l, (hl)            ; l = his x: it must be <= the mug's x < l + 16
    ld   a, e
    sub  a, l
    jr   c, 3$
    cp   a, #16
    jr   nc, 3$
    ld   a, (_fc_best)
    inc  a
    jr   z, 4$
    ld   a, (_fc_x)
    cp   a, l
    jr   nc, 3$             ; (the best so far is at least as far right)
4$:
    ld   a, c
    ld   (_fc_best), a
    ld   a, l
    ld   (_fc_x), a
3$:
    pop  hl
    dec  d
    jr   nz, 2$
    ld   a, (_fc_best)
    ret
__endasm;
}
#else
static uint8_t fc_best, fc_x;

// Who catches a full mug: a walker not watching the show, or (M8d) a drinker who has finished and waits to send
// its empty (DRINK_WAIT / DRINK_WINDUP). One still in his minimum drink lets it slide past.
static uint8_t can_catch(uint8_t s) {
    uint8_t st = patron_state[s];
    if (st == PATRON_WALKING) return !(patron_dist[s] | patron_aux[s]);   // distracted (or still off the screen): the mug slides past
    return st == PATRON_DRINKING && patron_aux[s] != DRINK_MIN;
}

static void catcher_candidate(uint8_t s) {          // (can_catch, inlined: asked for every patron of the bar)
    uint8_t l = patron_state[s];
    if (l == PATRON_WALKING) { if (patron_dist[s] | patron_aux[s]) return; }   // (aux: part of him still off the screen)
    else if (l != PATRON_DRINKING || patron_aux[s] == DRINK_MIN) return;
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
        if (!can_catch(s)) continue;
        l = patron_x[s];
        if (x >= l && (uint8_t)(x - l) < PATRON_W && (best == NO_SLOT || l > bx)) { best = s; bx = l; }
    }
    return best;
}
#endif

static void send_empty(uint8_t p);
static uint16_t empty_travel(uint8_t p);

// He catches mug i: it stays in his hand (MUG_HELD) and he is pushed back. A finished drinker (M8d) first lets
// his empty go at once (the player's mug made him: no fair-empties wait), and later empties keep their gap after it.
static void caught(uint8_t i, uint8_t p) {
    if (patron_state[p] == PATRON_DRINKING) {
        uint16_t t = empty_travel(p) + empty_gap;
        if (t > next_arrival) next_arrival = t;
        send_empty(p);
    }
    patron_state[p] = PATRON_PUSHED;
    patron_timer[p] = 0;
    if (mosh_on) mosh_caught(p);                 // the mosh pit (src/mosh.c): a new push, a new bump
    patron_aux[p] = push_for(p);
    patron_drinks[p]++;                          // (255 marks a served one leaving, served_out: 254 mugs never happen)
    patron_frac[p] = 0;
    patron_mug[p] = i;
    patron_catchx[p] = mug_x[i];
    if (story_on) perfect_catch(i);              // story: was it a perfect pour? (src/pour.c)
    mug_state[i] = MUG_HELD;
    mug_patron[i] = p;
}

// Full mug i at mug_x[i] reaches the rightmost walking patron whose 16 px contain it: he catches it.
uint8_t catch_full(uint8_t i) {
    uint8_t b = mug_bar[i], x, p;
    if (b >= NUM_BARS) return 0;
    if (b == boss_bar) return mug_x[i] < boss_lim ? boss_catch(i) : 0;   // a boss fight: his bar is his (src/boss.c)
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
// New patron at the left edge of a random bar, if the PATRON_SPACING px from SPAWN_X are free: at SPAWN_X with all of
// him still off the screen (patron_aux = PATRON_W), a sprite from the start (LIFT_EDGE, lift.c). No sprite room for him
// on that bar now (lift.c's budgets, or this frame's copy list): he is taken back and the spawn is tried again
// SPAWN_RETRY frames later.
uint8_t  pat_len, pat_bar;             // story shifts: an arrival pattern, its next bar (game.h)
extern uint8_t rng_state;

static uint8_t try_spawn(void) {
    uint8_t b = pat_len ? pat_bar : (next_rand() >> 2) & 3, v = NUM_BARS;
    if (!lists_ok) build_lists();
    while (bar_n[b] >= bar_cap[b]) {              // CLASSIC: the bar is at its cap: the next one that is not
        b = (b + 1) & (NUM_BARS - 1);
        if (!--v) return 0;
    }
    if (blocked_behind(b, SPAWN_X + PATRON_SPACING)) return 0;   // someone within PATRON_SPACING px of the spawn point
    v = next_rand();                              // v % 3 without SDCC's divide call (16 = 4 = 1 mod 3)
    v = (v >> 4) + (v & 15);
    v = (v >> 2) + (v & 3);
    v = (v >> 2) + (v & 3);
    if (v >= 3) v -= 3;
    if (v == 2 && boss_on) v = rng_state & 1;     // a boss fight: variant C's tiles are the boss's (src/boss.c)
    if (hurry_speed && !(next_rand() & 3)) np_h = 1;   // M13b: about 1 in 4 hurries (from level 3; level.c)
    if (!add_patron(b, SPAWN_X, v)) { np_h = 0; return 0; }
    patron_aux[np_p] = PATRON_W;
    if (!lift_spawn(np_p)) { remove_patron(np_p); return 0; }
    spawned++;
    return 1;
}

// ---- the frame ----------------------------------------------------------------------------------------
// One small function per state: SDCC keeps the slot number in a register in a function this size, so each
// patron_xxx[p] is a 16-bit add and a load (one big loop body spills everything to the stack instead).
// Each returns 1 while the patron stays.
static uint8_t go_now;                // the intro delay is over: walkers walk

// A walker's whole pixel: blocked, one px on, or at the tap (a life). Returns 0 when he is gone.
static uint8_t walker_pixel(uint8_t p, uint8_t f) {
    uint8_t x = patron_x[p];
    if (patron_aux[p]) { patron_aux[p]--; patron_frac[p] = f; return 1; }   // entering: one more px of him on the screen
    // M13b: he passes slower walkers and drinkers. He waits (the fraction stays where it was) only if this step would
    // make three patrons share a tile column: from a multiple of 8 the step takes him into column (x >> 3) + 2.
    if (!(x & 7) && col_scan(patron_bar[p], (x >> 3) + 2, p) >= 2) return 1;
    patron_frac[p] = f;
    patron_x[p] = ++x;
    if (x == ENTRY_X && patron_lift[p] == LIFT_EDGE) patron_lift[p] = LIFT_OBJ;   // in: an ordinary lifted patron (drops when clear)
    if (x >= PATRON_FAR_X - 8 * 3 * TAPER_MAX && x >= bar_tap[patron_bar[p] & (NUM_BARS - 1)]) {   // reached the tap (P6)
        remove_patron(p);
        lose_life();
        return 0;
    }
    return 1;
}

static uint8_t walking_step(uint8_t p) {
    uint8_t f, o;
    if (patron_dist[p]) {                               // distracted by the show: no walking
        f = patron_x[p] | DRAW_BACK;
        if (patron_draw[p] == f) return 1;              // (already watching the stage, x a multiple of 8: watch_step would only say so, a banked call a frame)
        return watch_step(p);
    }
    if (mosh_on && (patron_shove[p] | patron_stag[p])) mosh_step(p);   // shoved or staggering (src/mosh.c)
    else if (go_now) {
        o = patron_frac[p];
        f = o + (patron_x[p] < WALK_X ? EMERGE_SPEED : patron_hurry[p] ? hurry_speed : patron_speed);   // (entering)
        if (f < o) {                                      // carried: one whole pixel
            if (!walker_pixel(p, f)) return 0;
        } else {
            patron_frac[p] = f;
        }
    }
    o = patron_x[p] & draw_mask;                          // a walker who is not watching is drawn at his x, facing
    f = patron_draw[p];                                   // the bar (a stale back view, bit 7, differs too)
    if (o == f) return 1;
    if (patron_lift[p] == LIFT_EDGE) { patron_draw[p] = o; return 1; }   // entering: a sprite only, nothing on the BG
    if ((uint8_t)(o ^ f) & 0xF8) redraw_at(p, o);
    else {                                                // a 1 px step within his columns (redraw_at's quick case)
        patron_draw[p] = o; mark_quick(p);
        if (!(f & 7)) ovl_touch(p);                      // off a multiple of 8: 2 -> 3 real columns
    }
    return 1;
}

static void start_drinking(uint8_t p) {
    patron_state[p] = PATRON_DRINKING;
    patron_timer[p] = 0;
}

// Served (the push carries him all the way off): he slides out past the screen's left edge, mug in hand
// (leaving_step); the serve counts when he is gone (served_done). patron_drinks 255 marks him (the engine's other
// leavers, a boss's scared regulars, score nothing).
static void served_out(uint8_t p) {
    patron_state[p] = PATRON_LEAVING;
    patron_aux[p] = 0;
    patron_drinks[p] = 255;
}

// All of a served patron is off the screen: score, count (his tip was dropped when his mug landed: caught).
void served_done(uint8_t p) {
    if (patron_drinks[p] != 255) return;
    served++;
    add_score(serve_score);
    SFX(SFX_SERVE);
}

// Leaving: lifted first (LIFT_EDGE; no sprite room: he is gone at once), then PUSH_SPEED px a frame to x 0 and on past
// the edge (patron_aux px of him gone); removed when all of him is. A sprite only: nothing on the BG changes. One lifted
// off the BG here stands still (patron_timer 1) until his BG copy is off the screen (the sprite covers it exactly).
static uint8_t leaving_step(uint8_t p) {
    uint8_t x;
    if (patron_lift[p] != LIFT_EDGE) {
        if (!(x = lift_leave(p))) { served_done(p); remove_patron(p); return 0; }
        patron_timer[p] = x - 1;
    }
    if (patron_timer[p]) {
        if (vq_held || bg_pending(p)) return 1;
        patron_timer[p] = 0;
    }
    if ((x = patron_x[p])) { x -= PUSH_SPEED; patron_x[p] = x; patron_draw[p] = x & draw_mask; return 1; }
    if ((patron_aux[p] += PUSH_SPEED) < PATRON_W) return 1;
    served_done(p);
    remove_patron(p);
    return 0;
}

// One px toward the left end. M13b: he slides through anyone in his way (lift.c lifts him over them); the push ends
// only when it is used up or he reaches ENTRY_X (served, pushed_step). In the mosh pit he bumps the walker behind him.
static void push_px(uint8_t p) {
    patron_x[p] -= PUSH_SPEED;
    if ((patron_aux[p] -= PUSH_SPEED) == 0) start_drinking(p);
    if (mosh_on && !patron_mosh[p]) mosh_bump(p);        // the mosh pit (src/mosh.c): the walker behind him is shoved
}

// Pushed back by a caught mug: one px a frame toward the left end, then he drinks (or, with a push that carries him
// past ENTRY_X and on, he is served: push_for).
static uint8_t pushed_step(uint8_t p) {
    if (patron_aux[p] == 0) start_drinking(p);
    else if (patron_x[p] <= ENTRY_X) { served_out(p); return leaving_step(p); }
    else push_px(p);
    refresh_patron(p);
    return 1;
}

// Frames an empty sent by p now takes to reach the bartender's end (the px from where it starts to his bar's tap,
// EMPTY_STEP_FRAMES each).
static uint16_t empty_travel(uint8_t p) {
    uint8_t x = patron_x[p] + PATRON_W, t = bar_tap[patron_bar[p] & (NUM_BARS - 1)];   // where the empty starts
    return x >= t ? 0 : (uint16_t)(uint8_t)(t - x) * EMPTY_STEP_FRAMES;
}

// May patron p start his wind-up now? The empty's arrival (the wind-up, then the slide) must be no sooner than
// next_arrival; if so, it is scheduled.
static uint8_t empty_may_go(uint8_t p) {
    uint16_t t = empty_travel(p) + WINDUP_FRAMES;
    if (t < next_arrival) return 0;
    next_arrival = t + empty_gap;
    return 1;
}

// The held mug becomes an empty sliding out to the right.
static void send_empty(uint8_t p) {
    uint8_t m = patron_mug[p];
    if (m != NO_SLOT && mug_state[m] == MUG_HELD) {
        mug_state[m] = MUG_EMPTY;
        mug_x[m] = patron_x[p] + PATRON_W;
        mug_timer[m] = 0;                                 // (its half-px step phase, see mugs.c)
        if (tip_first && !--tip_first) classic_tip(p);   // CLASSIC: the level's 2nd empty: the first tip (classic.c)
    }
    patron_mug[p] = NO_SLOT;
}

static void walk_on(uint8_t p) {
    patron_state[p] = PATRON_WALKING;
    patron_timer[p] = 0;
    patron_aux[p] = 0;
}

// The bartender on p's bar (the caller checked) overlapping him (16 px each) takes his glass (M8d): scored like a
// caught empty.
static uint8_t glass_taken(uint8_t p) {
    uint8_t x = patron_x[p];
    if (bartender_x >= (uint8_t)(x + PATRON_W) || (uint8_t)(bartender_x + 16) <= x || patron_mug[p] == NO_SLOT) return 0;
    free_held_mug(p);
    walk_on(p);
    add_score(EMPTY_SCORE);
    SFX(SFX_CATCH);
    catch_pose = CATCH_POSE_FRAMES;
    return 1;
}

// A drinker who has finished (t: his timer + 1): the bartender may take the glass; winding up, he sends the empty
// at the end; otherwise he sips on (the timer loops over the sipping poses) until the empty may go, then winds up.
static void finished_step(uint8_t p, uint8_t t) {
    uint8_t a;
    if (patron_bar[p] == bar && glass_taken(p)) return;
    a = patron_aux[p];
    if (a == DRINK_WINDUP) {
        if (t < WINDUP_T0 + WINDUP_FRAMES) patron_timer[p] = t;
        else { send_empty(p); walk_on(p); }
        return;
    }
    if (patron_mug[p] == NO_SLOT) { walk_on(p); return; }  // nothing to send
    if (t >= DRINK_FRAMES) t = SIP_LOOP_T;
    if (empty_may_go(p)) { a = DRINK_WINDUP; t = WINDUP_T0; }
    else a = DRINK_WAIT;
    patron_aux[p] = a;
    patron_timer[p] = t;
}

// Drinking: DRINK_FRAMES at least (DRINK_MIN), then finished_step (M8d). Redrawn only when the sway changes.
// A drinker is stepped every other frame (update_patrons: the drinkers of the bars 0 and 2 on one frame, of 1 and 3 on the next), his timer counting 2 a step: the same pace, the poses
// and the sway changing on the frame they did or one later, and the bartender's glass catch looking every other frame.
static uint8_t drinking_step(uint8_t p) {
    uint8_t t = patron_timer[p] + 2;
    if (patron_aux[p] == DRINK_MIN && t < DRINK_FRAMES) patron_timer[p] = t;
    else {
        finished_step(p, t);
        if (patron_state[p] != PATRON_DRINKING) { refresh_patron(p); return 1; }
        t = patron_timer[p];
    }
    if (sway_tab[t] == sway_tab[(uint8_t)(t - 2)] && patron_draw[p] != 255) return 1;   // same sway: drawn as before
    refresh_patron(p);
    return 1;
}

void update_patrons(void) {
    uint8_t p, st, live = 0;

    if (next_arrival) next_arrival--;
    go_now = (intro_timer == 0);
    if (!go_now) {
        if (intro_timer) intro_timer--;
    } else {
        if (!patrons_live && spawn_timer > REFILL_FRAMES) pat_refill();   // an empty screen: the next one soon
        if (ramp_t && !--ramp_t) classic_ramp();  // CLASSIC: the in-level ramp's next step (classic.c)
        if (spawned < quota) {
            if (spawn_timer) spawn_timer--;
            else if (!try_spawn()) spawn_timer = SPAWN_RETRY;
            else spawn_timer = pat_len ? pat_done() : spawn_interval;   // (a story shift's pattern: story.c)
        }
    }

    for (p = 0; p != MAX_PATRONS; p++) {
        if ((st = patron_state[p]) == PATRON_NONE) continue;
        if (st == PATRON_WALKING) live += walking_step(p);
        else if (st == PATRON_DRINKING) {
            if (!((patron_bar[p] ^ frame_counter) & 1)) drinking_step(p);   // (a drinker whose bar's frame it is not waits a frame; one bar's drinkers keep their slot order)
            live++;                                                          // (it always returns 1)
        }
        else if (st == PATRON_PUSHED) live += pushed_step(p);
        else live += leaving_step(p);
    }
    patrons_live = live;
    if (spawned >= quota && patrons_live == 0 && mugs_live == 0) level_clear = 1;
    if (mosh_on) mosh_frame();                    // the mosh pit's counter splash (src/mosh.c)
}
