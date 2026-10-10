// Perfect pour (story mode, every shift; owner Q6, docs/minigames_bosses.md section 8). Arcade runs none of this:
// pour_frame / perfect_catch are only called when story_on, and pour_q stays 0 (start_new_game clears it).
//
// The window (owner, rounds 2 and 3: "too easy"): fill_timer (main.c, ROM0, unchanged) stops at FILL_FRAMES as in
// arcade; pour_frame (after the frame's sprites) keeps pour_t = the fill frames counted on past it while A is held:
// FILL_FRAMES on the frame the drink is full, +1 a frame up to the window's end.
//   16..31 (FILL_FRAMES..POUR_WIN_START-1)  full, settling: the plain full drink; a release is ordinary, no overflow
//   32..36 (POUR_WIN_START, pour_win 5)      the sparkle frame in his hand; a release is PERFECT (pour_q 1)
//   37..                                     the overflow frame; ordinary
// The next frame's release launches the drink with that pour_q (spawn_mug stores it in the full mug's mug_timer,
// unused while a full mug slides). A full drink carried to another bar (A held through Up/Down) jumps to the
// overflow at once: ordinary. pour_win is set to POUR_WIN_LEN by pour_load (every shift start); Practice's HARD toggle
// writes POUR_WIN_HARD after it (same start, a narrower window).
// The catch: patrons.c caught() calls perfect_catch in story mode; a perfect drink scores PERFECT_MULT x the venue's
// serve_score on the spot, counts in perfect_n, and the cue shows to the right of the caught mug for CUE_FRAMES,
// blinking for the last CUE_BLINK. The serve (the patron pushed out) still scores serve_score as always; regulars
// take any drink.
// The cue (round 3, owner: "can it say perfect"): the word PERFECT over the x2 badge, 32x16 = 4 entries in a row on
// the caught mug's 16 lines: OAM_CUE (26, free since the door puff) and OAM_DANCERS..+2 (28-30: the show's, written
// by render.c only while a show runs or to hide them once after it, so they are free whenever show_timer is 0).
// Sprites per line: each frame cue_frame counts every other OAM entry touching any of the cue's 16 lines (an upper
// bound for each line) and draws the full cue only if that count + 4 <= LINE_OBJ_MAX and no show runs, else the x2
// badge alone (1 entry, OAM_CUE, where the full cue's badge is) if the count + 1 fits, else nothing that frame. So the
// cue is never an 11th object on a line. cue_mode: 2 full, 1 short, 0 not drawn (tests / the drop rate).
#pragma bank 255
#include <gb/gb.h>
#include <stdint.h>

#include "game.h"
#include "pour_art.h"        // this bank's own data (tools/gen_pour.py)

#define PERFECT_MULT  2       // a perfect drink scores 2 x serve_score at the catch
#define CUE_FRAMES   48
#define CUE_BLINK    16

uint8_t pour_q;               // the drink launched next is perfect (spawn_mug -> mug_timer)
uint8_t pour_t;               // story: the fill frames counted past FILL_FRAMES (0 while not full)
uint8_t pour_win;             // the sparkle window's length (pour_load: POUR_WIN_LEN; Practice HARD: POUR_WIN_HARD)
uint8_t cue_t;                // frames the cue has left (0: none)
uint8_t cue_x, cue_y;         // its OAM x / y
uint8_t perfect_n;            // perfect drinks caught (tests)
uint8_t cue_mode;             // this frame's cue: 2 PERFECT + x2 (4 entries), 1 the x2 alone, 0 none
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
    cue_x = mug_x[i] + 16;                                   // the word starts right of the caught mug (OAM x)
}

static void put(uint8_t k, uint8_t x, uint8_t t) {
    OAM_item_t *o = shadow_OAM + k;
    o->y = cue_y; o->x = x; o->tile = t; o->prop = is_cgb ? OBJPAL_MUG_FULL : 0;
}

static void draw_cue(void) {
    OAM_item_t *o = shadow_OAM;
    uint8_t k, n = 0, y = cue_y, mode = 0, mine = cue_mode == 2 && !show_timer;   // 28-30 hold last frame's word
    if (--cue_t && (cue_t > CUE_BLINK || (cue_t & 4))) {
        for (k = 0; k != 40; k++, o++) {
            if (k == OAM_CUE || (mine && (uint8_t)(k - OAM_DANCERS) < 3)) continue;
            if (o->y && (uint8_t)(o->y - y + 15) < 31) n++;
        }
        if (!show_timer && n + 4 <= LINE_OBJ_MAX) mode = 2;
        else if (n < LINE_OBJ_MAX) mode = 1;
    }
    if (mine && mode != 2)                                   // the word's borrowed entries go back
        shadow_OAM[OAM_DANCERS].y = shadow_OAM[OAM_DANCERS + 1].y = shadow_OAM[OAM_DANCERS + 2].y = 0;
    cue_mode = mode;
    if (mode == 2) {
        put(OAM_CUE, cue_x, OBJ_POUR_CUE);
        put(OAM_DANCERS, cue_x + 8, OBJ_POUR_CUE + 2);
        put(OAM_DANCERS + 1, cue_x + 16, OBJ_POUR_CUE + 4);
        put(OAM_DANCERS + 2, cue_x + 24, OBJ_POUR_CUE + 6);
    } else if (mode) put(OAM_CUE, cue_x + 12, OBJ_POUR_CUE + 8);
    else shadow_OAM[OAM_CUE].y = 0;
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
}
