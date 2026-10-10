// Mugs: the pool and its rules (a full mug slides left until a patron catches it or it falls off the left
// end; an empty slides right until the bartender catches it or it falls off the tap end; a breaking glass
// plays out), and their sprites (one OAM entry per mug, two per breaking glass, the fill glass in his hand).
//
// Structure-of-arrays like the patrons (the tests read mug_state[] etc. by name); the loops walk the arrays
// with pointers and use tables for everything SDCC would multiply or divide.
#include <gb/gb.h>
#include <stdint.h>

#include "game.h"
#include "music.h"

uint8_t  mug_state[MAX_MUGS];   // MUG_FREE / MUG_FULL / MUG_EMPTY / MUG_BREAKING / MUG_HELD
uint8_t  mug_bar[MAX_MUGS];
uint8_t  mug_x[MAX_MUGS];       // pixel x of the mug's left edge
uint8_t  mug_timer[MAX_MUGS];   // frames since breaking began; an empty's frames on the counter (it moves on even ones)
uint8_t  mug_patron[MAX_MUGS];  // MUG_HELD: the patron holding it
uint8_t  mugs_live;             // number of non-free slots
uint8_t  oam_used = OAM_FILL + 1;   // OAM entries the mugs (and the fill glass) occupied last frame
uint8_t  mug_events;            // M13b: counts new mugs and breaking glasses (lift.c recounts the mugs per bar when it moves)
// Tile and attribute of the mug sprites (lift.c lift_level_init, M13a): CGB the venue's ids and palettes; DMG OBP0 with the
// bit-plane-swapped copies (OBP1 belongs to the lifted patrons now; the glass shards show their light shades swapped).
uint8_t  spr_full_t, spr_full_p, spr_empty_t, spr_empty_p, spr_hempty_t, spr_hempty_p;

uint8_t spawn_mug(uint8_t b, uint8_t x, uint8_t state) {
    // walks mug_state / mug_bar with pointers (indexed, SDCC computes two 16-bit addresses per slot)
    const uint8_t *st = mug_state, *mb = mug_bar;
    uint8_t i, n = 0, slot = MAX_MUGS;
    for (i = 0; i != MAX_MUGS; i++, st++, mb++) {
        if (*st == MUG_FREE) { if (slot == MAX_MUGS) slot = i; }
        else if (*mb == b) n++;
    }
    if (n >= MUGS_PER_BAR || slot == MAX_MUGS) return 0;
    mug_state[slot] = state;
    mug_bar[slot] = b;
    mug_x[slot] = x;
    mug_timer[slot] = 0;
    mugs_live++;
    mug_events++;
    return 1;
}

void launch_mug(void) {
    spawn_mug(bar, MUG_START_X, MUG_FULL);
    SFX(SFX_LAUNCH);
}

void clear_mugs(void) {
    uint8_t i;
    for (i = 0; i < MAX_MUGS; i++) mug_state[i] = MUG_FREE;
    mugs_live = 0;
}

// The per-state rules, one small function each: SDCC keeps the slot number in a register in a function this
// size, so each mug_xxx[i] is a 16-bit add and a load. (In one big loop body it spills everything to the
// stack, and a pointer kept per array is worse still.) Each returns 1 while the slot stays in use.
static void break_mug(uint8_t i) {
    mug_state[i] = MUG_BREAKING;
    mug_timer[i] = 0;
    mug_events++;
    SFX(SFX_BREAK);
    lose_life();
}

static uint8_t full_step(uint8_t i) {
    uint8_t x = mug_x[i] - MUG_SPEED_FULL;
    mug_x[i] = x;
    if (x < catch_lim[mug_bar[i] & (NUM_BARS - 1)] && catch_full(i)) return 1;   // (catch_lim: see patrons.c)
    if (x < MUG_END_X) break_mug(i);                    // fell off the left end
    return 1;
}

static uint8_t empty_step(uint8_t i) {
    uint8_t x = mug_x[i];
    if (!(++mug_timer[i] & 1)) mug_x[i] = ++x;          // 0.5 px per frame: d px take exactly 2d frames
    // His span reaches the bar end when he stands at TAP_X (his furthest position): an empty at x >= TAP_X is his.
    if (x >= bartender_x && ((uint8_t)(x - bartender_x) < 16 || bartender_x == TAP_X) && mug_bar[i] == bar) {
        mug_state[i] = MUG_FREE;                        // caught
        add_score(EMPTY_SCORE);
        SFX(SFX_CATCH);
        catch_pose = CATCH_POSE_FRAMES;
        return 0;
    }
    if (x > MUG_RIGHT_END) break_mug(i);                // fell off the right end
    return 1;
}

static uint8_t glass_step(uint8_t i) {
    if (++mug_timer[i] < GLASS_FRAMES * GLASS_FRAME_TIME) return 1;
    mug_state[i] = MUG_FREE;
    return 0;
}

static uint8_t held_step(uint8_t i) {                   // its patron is gone (or never held it): let it go
    uint8_t q = mug_patron[i];
    if (patron_state[q] != PATRON_NONE && patron_mug[q] == i) return 1;
    mug_state[i] = MUG_FREE;
    return 0;
}

void update_mugs(void) {
    uint8_t i, st, live = 0;
    if (mugs_live == 0) return;
    begin_catch_frame();
    for (i = 0; i != MAX_MUGS; i++) {
        st = mug_state[i];
        if (st == MUG_FREE) continue;
        if (st == MUG_FULL) live += full_step(i);
        else if (st == MUG_EMPTY) live += empty_step(i);
        else if (st == MUG_BREAKING) live += glass_step(i);
        else if (st == MUG_HELD) live += held_step(i);
        else live++;
    }
    mugs_live = live;
}

// glass pieces keep falling while the rest of the picture is frozen
void update_glass(void) {
    uint8_t i, st, live = 0;
    for (i = 0; i != MAX_MUGS; i++) {
        st = mug_state[i];
        if (st == MUG_FREE) continue;
        if (st == MUG_BREAKING) live += glass_step(i);
        else live++;
    }
    mugs_live = live;
}

// OAM 4: the glass the bartender holds under the spout while filling (hidden otherwise).
// It sits where the launched mug will start (MUG_START_X = SPOUT_X, the counter-top row).
void draw_fill(void) {
    OAM_item_t *o = shadow_OAM + OAM_FILL;
    if (!fill_timer) { o->y = 0; return; }
    o->y = bar_oam_y[bar] + MUG_DY; o->x = (uint8_t)(MUG_START_X + 8);
    o->tile = OBJ_MUG_FILL + fill_stage * 2; o->prop = is_cgb ? OBJPAL_MUG_FULL : 0;   // DMG: OBP0 (beer light grey) shows on the white wall; OBP1 would make it white
}

// Held-mug pose by drinking time (index = patron_timer / 4): 0..22 while he drinks (and, M8d, sips on while he
// waits to send the empty: the timer loops over 6..22), the mug rising from the hand to the mouth, then tilted and
// tipped; 24..31 the wind-up (timer WINDUP_T0..): the empty is lowered to the hand and drawn back to the left (poses 24-27,
// dx 8 -> 4), held a beat (28-29), then swung forward (30-31) to where it is launched (his right edge, dx 16). dx is the
// sprite's offset from the drawn patron x, dy from the bar's top pixel row (art is in sprite rows 2-12, so dy 1 puts
// a tilted mug at face height and dy 6 at the hand, always inside the bar's 24 lines). Pose 32: carried back while
// he is pushed, upright and full at the hand.
#define HELD_POSES 33
static const uint8_t pose_dx[HELD_POSES]   = { 9,9,8, 8,8,8,8,8,8,8,8, 8,8,8,8,8,8,8,8,8,8,8,8, 8,
                                               8,6,4,4, 4,4,10,14, 9 };
static const uint8_t pose_dy[HELD_POSES]   = { 5,3,2, 1,1,1,1,1,1,1,1, 1,1,1,1,1,1,1,1,1,1,1,1, 1,
                                               2,4,6,6, 6,6,6,6, 6 };
static const uint8_t pose_tile[HELD_POSES] = {
#define PT(f) (OBJ_MUG_DRINK + (f) * 2)
    PT(0),PT(0),PT(0), PT(1),PT(1),PT(1),PT(1),PT(1),PT(1),PT(1),PT(1),
    PT(2),PT(2),PT(2),PT(2),PT(2),PT(2),PT(2),PT(2),PT(2),PT(2),PT(2),PT(2), PT(2),
    PT(3),PT(3),PT(3),PT(3), PT(3),PT(3),PT(3),PT(3), PT(0)
#undef PT
};
#define POSE_CARRY 32
#define TILE_DRINK_EMPTY (OBJ_MUG_DRINK + 3 * 2)
#if WINDUP_T0 / 4 != 24 || (WINDUP_T0 + WINDUP_FRAMES - 1) / 4 > 31 || (DRINK_FRAMES - 1) / 4 > 23
#error "mug pose table: drinking 0..23, wind-up 24..31"
#endif

// OAM 5.. : one entry per mug, two per breaking glass. Entries used last frame
// but not this one are hidden (y = 0). The entries are written through oam_next by small writers (SDCC keeps
// the pointer in a register while it stores the four bytes); oam_left counts the entries still free.
static uint8_t *oam_next;
static uint8_t oam_left;
static uint8_t prop_full_held;

static void oam_put(uint8_t y, uint8_t x, uint8_t tile, uint8_t prop) {
    uint8_t *o = oam_next;
    *o++ = y; *o++ = x; *o++ = tile; *o++ = prop;
    oam_next = o;
}

static void draw_full(uint8_t i) {
    uint8_t *o = oam_next;
    *o++ = bar_oam_y[mug_bar[i]] + MUG_DY;
    *o++ = mug_x[i] + 8;
    *o++ = spr_full_t;
    *o++ = spr_full_p;
    oam_next = o;
}

static void draw_empty(uint8_t i) {
    uint8_t *o = oam_next;
    *o++ = bar_oam_y[mug_bar[i]] + MUG_DY;
    *o++ = mug_x[i] + 8;
    *o++ = spr_empty_t;
    *o++ = spr_empty_p;
    oam_next = o;
}

// The breaking drink (gen_art crash_frames, loaded with the venue): its own tilted pose, on its side (two entries), the
// shards. Left end: a full drink in its full palette; right end: an empty, mirrored (S_FLIPX; gen_art stores the empty
// on its side with its two columns swapped for that), in its empty palette. DMG: OBP0, the tiles plane-swapped (lift.c).
// The second entry stays hidden (y 0) on one-entry frames: draw_mugs counts two per breaking glass.
static const uint8_t glass_tile[GLASS_FRAMES] = { GLASS_TIP, GLASS_FALL_FULL, GLASS_SHATTER, GLASS_SETTLE };
static const uint8_t glass_dx[GLASS_FRAMES] = { 16, 8, 12, 12 };     // OAM x from the end's 16 px cell

static void draw_glass(uint8_t i) {
    uint8_t t = mug_timer[i], y, x, p, f;
    y = bar_oam_y[mug_bar[i]] + MUG_DY + (t >> 2);         // falls a little as it breaks
    f = t >> 3;                                              // t / GLASS_FRAME_TIME
    x = glass_dx[f];
    t = OBJ_GLASS + glass_tile[f];
    p = spr_full_p;
    if (mug_x[i] > 80) {                                     // the tap end
        x += GLASS_X_RIGHT;
        p = spr_empty_p | S_FLIPX;
        if (f == 1) t += GLASS_FALL_EMPTY - GLASS_FALL_FULL;
    }
    oam_put(y, x, t, p);
    oam_put(f == 1 ? y : 0, x + 8, t + 2, p);
}

static void draw_held(uint8_t i) {
    uint8_t g = mug_patron[i], t, x;
    t = patron_state[g] == PATRON_DRINKING ? patron_timer[g] >> 2 : 255;
    if (t >= POSE_CARRY) t = POSE_CARRY;                     // being carried back: upright, full, at the hand
    x = pose_dx[t];
    // M13b, DMG: between sprites the lower X wins, so a lifted holder's own entries would cover the mug wherever it
    // starts left of his right entry: dx 8 (level with it; the lower OAM index wins the tie), 16 for the last throw pose.
    if (!is_cgb && patron_lift[g]) x = t == WINDUP_T0 / 4 + 7 ? 16 : 8;
    x += patron_draw[g];
    if (patron_lift[g] == LIFT_EDGE) x -= patron_aux[g];     // (a served patron sliding out past the left edge takes it along)
    mug_x[i] = x;
    g = pose_tile[t];
    // DMG: the held full mug uses OBP0 (beer light grey, foam white) like the fill glass so it shows on the
    // white wall; the empty one looks like every empty mug (spr_hempty_*). CGB: the full / empty OBJ palette.
    if (g == TILE_DRINK_EMPTY) oam_put(bar_oam_y[mug_bar[i]] + pose_dy[t], x + 8, spr_hempty_t, spr_hempty_p);
    else oam_put(bar_oam_y[mug_bar[i]] + pose_dy[t], x + 8, g, prop_full_held);
}

void draw_mugs(void) {
    uint8_t i, st, n;
    oam_next = (uint8_t *)(shadow_OAM + OAM_FILL + 1);
    oam_left = OAM_MUG_END - (OAM_FILL + 1) - 2 * lift_total;   // M13a: lifted patrons use the top entries
    if (mugs_live) {
        prop_full_held = is_cgb ? OBJPAL_MUG_FULL : 0;
        for (i = 0; i != MAX_MUGS; i++) {
            st = mug_state[i];
            if (st == MUG_FREE) continue;
            if (st == MUG_BREAKING) {
                if (oam_left < 2) continue;
                oam_left -= 2;
                draw_glass(i);
                continue;
            }
            if (oam_left == 0) continue;
            oam_left--;
            if (st == MUG_HELD) draw_held(i);
            else if (st == MUG_EMPTY) draw_empty(i);
            else draw_full(i);
        }
    }
    n = OAM_MUG_END - 2 * lift_total - oam_left;                 // first entry not used by a mug
    for (i = n; i < oam_used; i++) shadow_OAM[i].y = 0;       // hide what is no longer used
    oam_used = n;
}
