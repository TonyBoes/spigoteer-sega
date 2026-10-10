// Perfect pour (story mode, every shift; owner Q6, docs/minigames_bosses.md section 8). Arcade runs none of this:
// pour_frame / perfect_catch are only called when story_on, and pour_q stays 0 (start_new_game clears it).
//
// The window: fill_timer (main.c, ROM0, unchanged) stops at FILL_FRAMES as in arcade; pour_frame (after the frame's
// sprites) keeps pour_t = the fill frames counted on past it while A is held: FILL_FRAMES on the frame the drink is
// full, +1 a frame up to PERFECT_END. pour_t FILL_FRAMES..PERFECT_END-1: the sparkle frame in his hand, pour_q 1;
// PERFECT_END: the overflow frame, pour_q 0. The next frame's release launches the drink with that pour_q (spawn_mug
// stores it in the full mug's mug_timer, unused while a full mug slides), so a release with pour_t 16..27 is
// PERFECT and one at 28 is ordinary. A full drink carried to another bar (A held through Up/Down) gets pour_t =
// PERFECT_END at once: ordinary, and shown running over.
// The catch: patrons.c caught() calls perfect_catch in story mode; a perfect drink scores PERFECT_MULT x the venue's
// serve_score on the spot, counts in perfect_n, and the cue (OAM_CUE: a twinkle over an "x2" badge) shows to the
// right of the caught mug for CUE_FRAMES, blinking for the last CUE_BLINK. The serve (the patron pushed out) still
// scores serve_score as always; regulars take any drink.
// Sprites per line: the cue is one 8x16 entry on the caught mug's 16 lines. pour_frame counts every other OAM entry
// that touches any of those lines (an upper bound for each line) and leaves the cue out on a frame where that count
// is LINE_OBJ_MAX or more, so the cue is never an 11th object on a line.
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
uint8_t cue_t;                // frames the cue has left (0: none)
uint8_t cue_x, cue_y;         // its OAM x / y
uint8_t perfect_n;            // perfect drinks caught (tests)
static uint8_t pour_bar;      // the bar of the last frame (a change while full = carried)

// LCD off (a story shift's start): venue t's sparkle + overflow to OBJ_POUR.., the cue to OBJ_POUR_CUE
void pour_load(uint8_t t) BANKED {
    set_sprite_data(OBJ_POUR, 4, pour_venue_tiles[t]);
    set_sprite_data(OBJ_POUR_CUE, 2, pour_cue_tiles);
}

void perfect_catch(uint8_t i) BANKED {
    if (mug_timer[i] != 1) return;                           // an ordinary drink
    add_score((uint16_t)serve_score * PERFECT_MULT);
    perfect_n++;
    cue_t = CUE_FRAMES;
    cue_y = bar_oam_y[mug_bar[i] & (NUM_BARS - 1)] + MUG_DY;
    cue_x = mug_x[i] + 16;                                   // right of the caught mug (OAM x = screen x + 8)
}

static void draw_cue(void) {
    OAM_item_t *o = shadow_OAM;
    uint8_t k, n = 0, y = cue_y;
    if (--cue_t && (cue_t > CUE_BLINK || (cue_t & 4))) {
        for (k = 0; k != 40; k++, o++)
            if (k != OAM_CUE && o->y && (uint8_t)(o->y - y + 15) < 31) n++;
        if (n < LINE_OBJ_MAX) {
            o = shadow_OAM + OAM_CUE;
            o->y = y; o->x = cue_x; o->tile = OBJ_POUR_CUE; o->prop = is_cgb ? OBJPAL_MUG_FULL : 0;
            return;
        }
    }
    shadow_OAM[OAM_CUE].y = 0;
}

void pour_frame(void) BANKED {
    OAM_item_t *o;
    if (fill_timer < FILL_FRAMES) pour_t = 0;
    else if (bar != pour_bar) pour_t = PERFECT_END;           // carried to another bar: never perfect
    else if (!pour_t) pour_t = FILL_FRAMES;
    else if (pour_t < PERFECT_END) pour_t++;
    pour_bar = bar;
    pour_q = pour_t && pour_t < PERFECT_END;
    if (pour_t) {                                            // over draw_fill's full drink (OAM_FILL): sparkle / overflow
        // DMG: OBP1 (the fill glass uses OBP0): the drink darkens in his hand, and the light shades show on the wall
        o = shadow_OAM + OAM_FILL;
        o->tile = pour_t < PERFECT_END ? OBJ_POUR : OBJ_POUR + 2;
        o->prop = is_cgb ? OBJPAL_MUG_FULL : S_PALETTE;
    }
    if (cue_t) draw_cue();
}
