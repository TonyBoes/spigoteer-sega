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
#include "asm_cfg.h"

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
    mug_timer[slot] = pour_q;           // a full mug's quality: 1 a story perfect pour (src/pour.c), else 0
    mugs_live++;
    mug_events++;
    return 1;
}

void launch_mug(void) {
    spawn_mug(bar, tap_now + (SPOUT_X - TAP_X), MUG_FULL);   // (under his bar's spout: P6 slanted bars, game.h)
    if (pour_q) SFX(SFX_PERFECT);                           // (a story perfect pour: the chime, not the launch's sweep; src/pour.c)
    else SFX(SFX_LAUNCH);
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
    // His span reaches the bar end when he stands at the tap (his furthest position, bar_tap: P6): an empty past it is his.
    if (x >= bartender_x && ((uint8_t)(x - bartender_x) < 16 || bartender_x == tap_now) && mug_bar[i] == bar) {
        mug_state[i] = MUG_FREE;                        // caught
        add_score(EMPTY_SCORE);
        SFX(SFX_CATCH);
        catch_pose = CATCH_POSE_FRAMES;
        return 0;
    }
    if (x > MUG_RIGHT_END - 8 * 3 * TAPER_MAX && x > BAR_MUG_END(mug_bar[i] & (NUM_BARS - 1))) break_mug(i);   // off the tap end
                                                        // (the first test spares most empties the bar's lookup)
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

#if ASM_UPDATE_MUGS
// The slot loop of update_mugs, hand-written (the C loop reads every one of the 20 slots, ~13 of them free in a crowd's frame, at
// ~80 T-cycles a free slot against ~50 here). A used slot is stepped by its state's C step, called through HL with the live count
// and the slot kept (the steps are static C functions, `sdcccall(1)`: slot in A, 1 in A while it stays). States past 4 (the boss's
// mugs, boss.h) stay as they are. Returns the number of slots that stay in use.
#if MAX_MUGS != 20
#error "update_mugs_loop: the constants written into the asm"
#endif
typedef char update_mugs_enums[(MUG_FREE == 0 && MUG_FULL == 1 && MUG_EMPTY == 2 && MUG_BREAKING == 3 && MUG_HELD == 4) ? 1 : -1];
static uint8_t update_mugs_loop(void) __naked {
__asm
    push bc
    ld   b, #0              ; b = 0 (add hl, bc), c = slot, d = slots that stay
    ld   c, #0
    ld   d, #0
    ld   hl, #_mug_state
1$:
    ld   a, (hl+)
    or   a, a
    jr   z, 8$              ; (free)
    cp   a, #4              ; MUG_HELD, the commonest first: still in his patron hand?
    jr   nz, 2$
    ld   hl, #_mug_patron
    add  hl, bc
    ld   a, (hl)
    push bc
    ld   c, a               ; c = patron
    ld   hl, #_patron_state
    add  hl, bc
    ld   a, (hl)
    or   a, a
    jr   z, 4$              ; (PATRON_NONE: the C step lets it go)
    ld   hl, #_patron_mug
    add  hl, bc
    ld   a, (hl)
    pop  bc
    cp   a, c
    jr   nz, 3$             ; (he holds another: the C step)
    inc  d
    jr   7$
4$:
    pop  bc
3$:
    ld   hl, #_held_step
    jr   5$
2$:
    cp   a, #2              ; MUG_EMPTY
    ld   hl, #_empty_step
    jr   z, 5$
    cp   a, #1              ; MUG_FULL
    ld   hl, #_full_step
    jr   z, 5$
    cp   a, #3              ; MUG_BREAKING
    ld   hl, #_glass_step
    jr   z, 5$
    inc  d                  ; (any other state stays)
    jr   7$
5$:
    push bc
    push de
    ld   de, #6$
    push de
    ld   a, c
    jp   (hl)
6$:
    pop  de
    pop  bc
    add  a, d
    ld   d, a
7$:
    ld   hl, #_mug_state + 1
    add  hl, bc
8$:
    inc  c
    ld   a, c
    cp   a, #20             ; MAX_MUGS
    jr   nz, 1$
    ld   a, d
    pop  bc
    ret
__endasm;
}

void update_mugs(void) {
    if (mugs_live == 0) return;
    begin_catch_frame();
    mugs_live = update_mugs_loop();
}
#else
void update_mugs(void) {
    uint8_t i, st, live = 0;
    if (mugs_live == 0) return;
    begin_catch_frame();
    for (i = 0; i != MAX_MUGS; i++) {
        st = mug_state[i];
        if (st == MUG_FREE) continue;
        if (st == MUG_HELD) live += held_step(i);          // (the commonest first: a drinker's mug, 5-7 of a crowd's ~10)
        else if (st == MUG_EMPTY) live += empty_step(i);
        else if (st == MUG_FULL) live += full_step(i);
        else if (st == MUG_BREAKING) live += glass_step(i);
        else live++;
    }
    mugs_live = live;
}

#endif

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
// It sits where the launched mug will start (under the bar's spout, BAR_SPOUT, the counter-top row).
// Per venue the glass held under the spout hangs a few px (0-3) lower than a sliding mug, its tap's spout tip ends that far
// lower (owner's per-venue cup heights): tools/gen_art.py FILL_DY, packed into venue.show_band bits 1-2 (no ROM0 table, no WRAM).
void draw_fill(void) {
    OAM_item_t *o = shadow_OAM + OAM_FILL;
    if (!fill_timer) { o->y = 0; return; }
    o->y = bar_oam_y[bar] + MUG_DY + (venue.show_band >> 1); o->x = (uint8_t)(tap_now + (SPOUT_X - TAP_X + 8));
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
#if !ASM_DRAW_HELD
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
#else
// The same three tables interleaved (dx, dy, tile; the asm reads one 3-byte row): poses 0-2 the lift to the mouth ..., see above.
#define PT(f) (OBJ_MUG_DRINK + (f) * 2)
#define P8(n, dx, dy, f) n(dx, dy, f) n(dx, dy, f) n(dx, dy, f) n(dx, dy, f) n(dx, dy, f) n(dx, dy, f) n(dx, dy, f) n(dx, dy, f)
#define R(dx, dy, f) dx, dy, PT(f),
static const uint8_t pose_tab[HELD_POSES * 3] = {
    R(9,5,0) R(9,3,0) R(8,2,0)
    P8(R, 8,1,1)                                        // 3..10
    P8(R, 8,1,2) R(8,1,2) R(8,1,2) R(8,1,2) R(8,1,2)   // 11..22
    R(8,1,2)                                            // 23
    R(8,2,3) R(6,4,3) R(4,6,3) R(4,6,3) R(4,6,3) R(4,6,3) R(10,6,3) R(14,6,3)   // 24..31
    R(9,6,0)                                            // 32
};
#undef R
#undef P8
#undef PT
#endif
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
        x += BAR_GLASS_X(mug_bar[i] & (NUM_BARS - 1));
        p = spr_empty_p | S_FLIPX;
        if (f == 1) t += GLASS_FALL_EMPTY - GLASS_FALL_FULL;
    }
    oam_put(y, x, t, p);
    oam_put(f == 1 ? y : 0, x + 8, t + 2, p);
}

#if !ASM_DRAW_HELD
static void draw_held(uint8_t i) {
    uint8_t g = mug_patron[i], t, x, l = patron_lift[g], *o = oam_next;   // (the entry is written here, not through oam_put: a call is dear)
    t = patron_state[g] == PATRON_DRINKING ? patron_timer[g] >> 2 : 255;
    if (t >= POSE_CARRY) t = POSE_CARRY;                     // being carried back: upright, full, at the hand
    x = pose_dx[t];
    // M13b, DMG: between sprites the lower X wins, so a lifted holder's own entries would cover the mug wherever it
    // starts left of his right entry: dx 8 (level with it; the lower OAM index wins the tie), 16 for the last throw pose.
    if (!is_cgb && l) x = t == WINDUP_T0 / 4 + 7 ? 16 : 8;
    x += patron_draw[g];
    if (l == LIFT_EDGE) x -= patron_aux[g];                  // (a served patron sliding out past the left edge takes it along)
    mug_x[i] = x;
    g = pose_tile[t];
    *o++ = bar_oam_y[mug_bar[i]] + pose_dy[t];
    *o++ = x + 8;
    // DMG: the held full mug uses OBP0 (beer light grey, foam white) like the fill glass so it shows on the
    // white wall; the empty one looks like every empty mug (spr_hempty_*). CGB: the full / empty OBJ palette.
    if (g == TILE_DRINK_EMPTY) { *o++ = spr_hempty_t; *o++ = spr_hempty_p; }
    else { *o++ = g; *o++ = prop_full_held; }
    oam_next = o;
}
#endif

// The per-slot loop of draw_mugs, hand-written (the C loop and writers cost ~25 DIV ticks a frame with a crowd): a full or an
// empty mug is one OAM entry written here; a breaking glass or a mug in a patron's hand goes to draw_glass / draw_held (C),
// called with oam_next in step. oam_left counts the entries still free (a glass takes 2); the bar's y is looked up without a mask.
#if MAX_MUGS != 20 || MUG_DY != 4
#error "draw_mugs_loop: the constants written into the asm"
#endif
typedef char draw_mugs_enums[(MUG_FREE == 0 && MUG_FULL == 1 && MUG_EMPTY == 2 && MUG_BREAKING == 3 && MUG_HELD == 4) ? 1 : -1];
static void draw_mugs_loop(void) __naked {
__asm
    push bc
    ld   a, (_oam_next)
    ld   e, a
    ld   a, (_oam_next + 1)
    ld   d, a               ; de: the next OAM entry
    ld   b, #0              ; b = 0 (add hl, bc), c = slot
    ld   c, #0
    ld   hl, #_mug_state
1$:
    ld   a, (hl+)
    or   a, a
    jr   z, 9$              ; (free)
    cp   a, #3              ; MUG_BREAKING
    jp   z, 20$
    ld   hl, #_oam_left
    ld   a, (hl)
    or   a, a
    jr   z, 8$              ; (no entry left)
    dec  (hl)
    ld   hl, #_mug_state
    add  hl, bc
    ld   a, (hl)
    cp   a, #4              ; MUG_HELD
    jp   z, 30$
    ld   hl, #_mug_bar      ; y: bar_oam_y[mug_bar[i]] + MUG_DY
    add  hl, bc
    ld   a, (hl)
    ld   hl, #_bar_oam_y
    add  a, l
    ld   l, a
    jr   nc, 2$
    inc  h
2$:
    ld   a, (hl)
    add  a, #4
    ld   (de), a
    inc  de
    ld   hl, #_mug_x        ; x: mug_x[i] + 8
    add  hl, bc
    ld   a, (hl)
    add  a, #8
    ld   (de), a
    inc  de
    ld   hl, #_mug_state
    add  hl, bc
    ld   a, (hl)
    cp   a, #2              ; MUG_EMPTY (anything else draws as a full one)
    jr   z, 3$
    ld   a, (_spr_full_t)
    ld   (de), a
    inc  de
    ld   a, (_spr_full_p)
    jr   4$
3$:
    ld   a, (_spr_empty_t)
    ld   (de), a
    inc  de
    ld   a, (_spr_empty_p)
4$:
    ld   (de), a
    inc  de
8$:
    ld   hl, #_mug_state + 1
    add  hl, bc
9$:
    inc  c
    ld   a, c
    cp   a, #20             ; MAX_MUGS
    jr   nz, 1$
    pop  bc
    ret
    ; ---- a breaking glass: 2 entries, draw_glass (C, with oam_next in step)
20$:
    ld   hl, #_oam_left
    ld   a, (hl)
    cp   a, #2
    jr   c, 8$
    sub  a, #2
    ld   (hl), a
    ld   a, e
    ld   (_oam_next), a
    ld   a, d
    ld   (_oam_next + 1), a
    push bc
    ld   a, c
    call _draw_glass
    pop  bc
    ld   a, (_oam_next)
    ld   e, a
    ld   a, (_oam_next + 1)
    ld   d, a
    jp   8$
#if ASM_DRAW_HELD
    ; ---- a mug in a patron hand (draw_held in C): in c = slot, b = 0, de = the next entry; out de advanced
30$:
    ld   hl, #_mug_patron
    add  hl, bc
    ld   a, (hl)
    push bc                 ; (slot)
    push de                 ; (entry)
    ld   c, a               ; c = g, his patron (b = 0)
    ld   hl, #_patron_state ; t = the pose: timer / 4 while he drinks, else 255; at most POSE_CARRY
    add  hl, bc
    ld   a, (hl)
    cp   a, #3              ; PATRON_DRINKING
    ld   a, #255
    jr   nz, 31$
    ld   hl, #_patron_timer
    add  hl, bc
    ld   a, (hl)
    srl  a
    srl  a
31$:
    cp   a, #POSE_CARRY
    jr   c, 32$
    ld   a, #POSE_CARRY
32$:
    ld   d, a               ; d = t
    add  a, a
    add  a, d               ; 3 t
    ld   hl, #_pose_tab
    add  a, l
    ld   l, a
    jr   nc, 33$
    inc  h
33$:
    ld   e, (hl)            ; e = x = dx
    ld   hl, #_patron_lift
    add  hl, bc
    ld   a, (hl)            ; a = his lift
    or   a, a
    jr   z, 36$             ; (not lifted)
    ld   h, a               ; h = lift
    ld   a, (_is_cgb)       ; DMG, lifted holder: 8 (16 for the last throw pose, WINDUP_T0 / 4 + 7)
    or   a, a
    jr   nz, 35$
    ld   e, #8
    ld   a, d
    cp   a, #(WINDUP_T0 / 4 + 7)
    jr   nz, 35$
    ld   e, #16
35$:
    ld   a, h
    cp   a, #2              ; LIFT_EDGE: (a served patron sliding out past the left edge takes it along)
    jr   nz, 36$
    ld   hl, #_patron_aux
    add  hl, bc
    ld   a, e
    sub  a, (hl)
    ld   e, a
36$:
    ld   hl, #_patron_draw  ; x += his drawn x
    add  hl, bc
    ld   a, (hl)
    add  a, e
    ld   e, a               ; (the aux, if any, was taken off before: the sum is the same mod 256)
    ldhl sp, #2
    ld   c, (hl)            ; c = the slot again (b = 0)
    ld   hl, #_mug_x
    add  hl, bc
    ld   (hl), e            ; mug_x[i] = x
    ld   hl, #_mug_bar      ; y = bar_oam_y[mug_bar[i]] + pose_dy[t]
    add  hl, bc
    ld   a, (hl)
    ld   hl, #_bar_oam_y
    add  a, l
    ld   l, a
    jr   nc, 37$
    inc  h
37$:
    ld   b, (hl)            ; b = bar_oam_y
    ld   a, d
    add  a, a
    add  a, d
    ld   hl, #(_pose_tab + 1)
    add  a, l
    ld   l, a
    jr   nc, 38$
    inc  h
38$:
    ld   a, (hl+)
    add  a, b
    ld   b, a               ; b = y
    ld   a, (hl)            ; the tile
    cp   a, #TILE_DRINK_EMPTY
    jr   z, 39$
    ld   c, a
    ld   a, (_prop_full_held)
    jr   40$
39$:
    ld   a, (_spr_hempty_t) ; the empty in his hand: its own look
    ld   c, a
    ld   a, (_spr_hempty_p)
40$:
    ld   d, a               ; d = attributes
    pop  hl                 ; the entry
    ld   (hl), b
    inc  hl
    ld   a, e
    add  a, #8
    ld   (hl+), a
    ld   (hl), c
    inc  hl
    ld   (hl), d
    inc  hl
    ld   d, h
    ld   e, l
    pop  bc                 ; the slot (b = 0)
    jp   8$
#else
    ; ---- a mug in a patron hand: draw_held (C, with oam_next in step)
30$:
    ld   a, e
    ld   (_oam_next), a
    ld   a, d
    ld   (_oam_next + 1), a
    push bc
    ld   a, c
    call _draw_held
    pop  bc
    ld   a, (_oam_next)
    ld   e, a
    ld   a, (_oam_next + 1)
    ld   d, a
    jp   8$
#endif
__endasm;
}

void draw_mugs(void) {
    uint8_t i, n;
    oam_next = (uint8_t *)(shadow_OAM + OAM_FILL + 1);
    oam_left = OAM_MUG_END - (OAM_FILL + 1) - 2 * lift_total;   // M13a: lifted patrons use the top entries
    if (mugs_live) {
        prop_full_held = is_cgb ? OBJPAL_MUG_FULL : 0;
        draw_mugs_loop();
    }
    n = OAM_MUG_END - 2 * lift_total - oam_left;                 // first entry not used by a mug
    for (i = n; i < oam_used; i++) shadow_OAM[i].y = 0;       // hide what is no longer used
    oam_used = n;
}
