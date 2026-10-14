// Perfect pour (story mode, every shift; owner Q6, docs/minigames_bosses.md section 8). Arcade runs none of this:
// pour_frame / perfect_catch are only called when story_on, and pour_q stays 0 (start_new_game clears it).
//
// The window (owner, rounds 2 and 3: "too easy"): fill_timer (main.c, ROM0, unchanged) stops at FILL_FRAMES as in
// arcade; pour_frame (after the frame's sprites) keeps pour_t = the fill frames counted on past it while A is held:
// FILL_FRAMES on the frame the drink is full, +1 a frame up to the window's end.
//   16..26 (FILL_FRAMES..POUR_WIN_START-1)  full, settling: the plain full drink; a release is ordinary, no overflow
//   27..31 (POUR_WIN_START, pour_win 5)      the sparkle frame in his hand; a release is PERFECT (pour_q 1)
//   32..                                     the overflow frame; ordinary
// The next frame's release launches the drink with that pour_q (spawn_mug stores it in the full mug's mug_timer,
// unused while a full mug slides). A full drink carried to another bar (A held through Up/Down) jumps to the
// overflow at once: ordinary. pour_win is set to POUR_WIN_LEN by pour_load (every shift start); Practice's HARD toggle
// writes POUR_WIN_HARD after it (same start, a narrower window).
// The catch: patrons.c caught() calls perfect_catch in story mode; a perfect drink scores PERFECT_MULT x the venue's
// serve_score on the spot, counts in perfect_n, and the cue shows to the right of the caught mug for CUE_FRAMES,
// blinking for the last CUE_BLINK. The serve (the patron pushed out) still scores serve_score as always; regulars
// take any drink.
// The cue (OAM_CUE 26, free since the door puff; one 8x16 entry: the "x2" badge alone in its lower half, the owner's
// pick after a twinkle over it, a redrawn badge and a PERFECT word) sits on the caught mug's 16 lines. Sprites per line: each frame draw_cue
// counts every other OAM entry touching any of those lines (an upper bound for each line) and leaves the cue out on a
// frame where that count is LINE_OBJ_MAX or more, so the cue is never an 11th object on a line.
#pragma bank 255
#include <gb/gb.h>
#include <stdint.h>

#include "game.h"
#include "music.h"
#include "pour_art.h"        // this bank's own data (tools/gen_pour.py)

#define PERFECT_MULT  2       // a perfect drink scores 2 x serve_score at the catch
#define CUE_FRAMES   48
#define CUE_BLINK    16

extern uint8_t frame_t0;      // main.c: (uint8_t)sys_time when this frame began
uint8_t pour_q;               // the drink launched next is perfect (spawn_mug -> mug_timer)
uint8_t pour_t;               // story: the fill frames counted past FILL_FRAMES (0 while not full)
uint8_t pour_win;             // the sparkle window's length (pour_load: POUR_WIN_LEN; Practice HARD: POUR_WIN_HARD)
uint8_t cue_t;                // frames the cue has left (0: none)
uint8_t cue_x, cue_y;         // its OAM x / y
uint8_t perfect_n;            // perfect drinks caught (tests)
static uint8_t pour_bar;      // the bar of the last frame (a change while full = carried)

// LCD off (a story shift's start): venue t's sparkle + overflow to OBJ_POUR.., the cue to OBJ_POUR_CUE
void pour_load(uint8_t t) BANKED {
    pour_win = POUR_WIN_LEN;
    set_sprite_data(OBJ_POUR, 4, pour_venue_tiles[t]);
    set_sprite_data(OBJ_POUR_CUE, POUR_CUE_TILES, pour_cue_tiles);
}

void perfect_catch(uint8_t i) BANKED {
    if (mug_timer[i] != 1) return;                           // an ordinary drink
    add_score((uint16_t)serve_score * PERFECT_MULT);
    perfect_n++;
    cue_t = CUE_FRAMES;
    cue_y = bar_oam_y[mug_bar[i] & (NUM_BARS - 1)] + MUG_DY;
    cue_x = mug_x[i] + 16;                                   // right of the caught mug (OAM x = screen x + 8)
}

// The dust puff of a bar change (mode B, and CLASSIC always): the same OAM 26 entry and the same lines count as the cue.
// cue_t bit 7 marks it (the cue's frames stay below 64): its low bits count DUST_FRAMES * DUST_STEP video frames down.
// The cue wins if both want the entry: a puff is not started while the cue shows (the whoosh still plays).
#define DUST_FRAMES  3
#define DUST_STEP    4          // video frames per dust frame
#define DUST_LATEST_LY 143        // the puff is left out on a frame that has run into the next VBlank (it is late already; the count costs ~10 lines)
#define DUST_DY      8          // the entry's OAM y below the bar's top: his lower 16 lines, the height of his legs

void dust_load(void) BANKED {
    set_sprite_data(OBJ_DUST, DUST_FRAMES * 2, dust_tiles);
}

// An Up/Down press (main.c play_frame): he came from bar b, bartender_x is still his place there and tap_now the new bar's.
// Mode A (KEEP_POS, the debug box's START; never in CLASSIC): he keeps his place on screen, up to the new tap (a bar's
// local x is mirrored between an L and an R bar, screen x = 144 - x for his left edge); pouring needs the tap, so he walks
// back to it. Mode B (the default, and CLASSIC always): he snaps to the tap, a puff where he stood and a whoosh.
void bar_change(uint8_t b) BANKED {
    uint8_t x = bartender_x, t = tap_now;
    facing = 0;
    if ((level_dirs & KEEP_POS) && play_mode != MODE_CLASSIC) {
        if (((bar_dirs >> b) ^ (bar_dirs >> bar)) & 1) x = 144 - x;
        bartender_x = x > t ? t : x < LEFT_LIMIT ? LEFT_LIMIT : x;
        return;
    }
    bartender_x = t;
    x += 12;                                                 // the puff's centre: his 16 px (OAM x = screen x + 8)
    SFX(SFX_WHOOSH);
    if (cue_t) return;
    if (bar_dirs & bar_bit[b]) x = 168 - x;                  // an R bar draws mirrored (mirror.c)
    cue_x = x; cue_y = bar_oam_y[b] + DUST_DY;
    cue_t = 0x80 | (DUST_FRAMES * DUST_STEP);
}

// The entries OAM 0..28 (bartender, fill, mugs, lifted patrons, the coin, the boss's topper at 28; the dancers 29..39 are
// on the stage) that touch any of the 16 lines from OAM y cue_y (an upper bound for each line), counted into the y byte of
// entry OAM_CUE (the caller has zeroed it; no WRAM of its own). Hand-written: the puff counts every frame it shows, and C
// costs three times as much.
#if OAM_DANCERS != 28 || OAM_CUE != 26
#error "dust_count: the topper is OAM 28, the cue 26 (104 bytes in)"
#endif
static void dust_count(void) __naked {
__asm
    push bc
    ld   hl, #_shadow_OAM
    ld   a, (_cue_y)
    ld   e, a
    ld   bc, #0x1D00                ; b: 29 entries, c: the count
1$:
    ld   a, (hl)                    ; y
    or   a, a
    jr   z, 3$                      ; (hidden)
    sub  a, e
    add  a, #15
    cp   a, #31
    jr   nc, 3$                     ; (clear of the lines)
    inc  c
3$:
    inc  hl
    inc  hl
    inc  hl
    inc  hl
    dec  b
    jr   nz, 1$
    ld   a, c
    ld   (_shadow_OAM + 104), a
    pop  bc
    ret
__endasm;
}

void draw_cue(void) BANKED {
    OAM_item_t *o = shadow_OAM + OAM_CUE;
    uint8_t y = cue_y, t = cue_t, tile = OBJ_POUR_CUE, show;
    if (t & 0x80) {
        t &= 0x7F;
        tile = OBJ_DUST + ((2 - ((t - 1) >> 2)) << 1);       // (t: 12..1 -> frames 0, 1, 2)
        show = t != 0;                                       // (0: its entry goes this frame)
        cue_t = show ? cue_t - 1 : 0;
        if (LY_REG > DUST_LATEST_LY || (uint8_t)sys_time != frame_t0) show = 0;   // a frame that ran into the next VBlank: no puff (the line count costs ~10 lines)
    } else show = --cue_t && (cue_t > CUE_BLINK || (cue_t & 4));
    if (show) {
        o->y = 0;                                            // (not counting its own entry)
        dust_count();
        if (o->y < LINE_OBJ_MAX) {
            o->y = y; o->x = cue_x; o->tile = tile; o->prop = is_cgb ? (tile == OBJ_POUR_CUE ? OBJPAL_MUG_FULL : OBJPAL_BARTENDER) : 0;
            return;
        }
    }
    o->y = 0;
}

void pour_frame(void) BANKED {
    OAM_item_t *o;
    uint8_t end = POUR_WIN_START + pour_win;                 // the first overflow frame
    if (fill_timer < FILL_FRAMES) pour_t = 0;
    else if (bar != pour_bar) pour_t = end;                  // carried to another bar: never perfect
    else if (!pour_t) pour_t = FILL_FRAMES;
    else if (pour_t < end) pour_t++;
    pour_bar = bar;
    pour_q = pour_t >= POUR_WIN_START && pour_t < end;
    if (pour_t >= POUR_WIN_START) {                          // over draw_fill's full drink (OAM_FILL): sparkle / overflow
        // DMG: OBP1 (the fill glass uses OBP0): the drink darkens in his hand, and the light shades show on the wall
        o = shadow_OAM + OAM_FILL;
        o->tile = pour_q ? OBJ_POUR : OBJ_POUR + 2;
        o->prop = is_cgb ? OBJPAL_MUG_FULL : S_PALETTE;
    }
    if (cue_t) draw_cue();
    if (boss_on) boss_draw();                                // a boss fight: his topper (last: it counts the lines)
}
