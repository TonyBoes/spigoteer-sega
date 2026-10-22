// The one-line menu style shared by BONUS > SOUNDTRACK (src/jukebox.c), MINI GAMES (src/mg_list.c) and BOSS RUSH's list (src/rush.c): a header with the
// title and a counter, one selection line "< NAME >" in the panel's reddish band with gold arrows that bob and kick, a screen of its own below it, and a
// hint row "(A) PLAY (B) BACK". The pieces they share are in src/oneline.c (banked; the strings of each screen stay in its own bank).
//
// Layout of every one of the three (20 x 18 tiles, the wood wall of src/mg_list.c list_frame):
//   row 0 header (title at column 1, counter at the right)   row 1 the header's edge   rows 2-4 the band (the name on row 3)   rows 5-14 the screen's own
//   row 15 the panel's top line   row 16 the hint row   row 17 the panel's bottom line
// Keys: LEFT / RIGHT one entry (wrapping, hold-to-repeat: first repeat after OL_DELAY frames, then every OL_RATE), UP / DOWN a jump (ol_key returns the key).
#ifndef ONELINE_H
#define ONELINE_H
#include <stdint.h>
#include "game.h"
#include "scratch.h"
#include "story.h"

// BG tile ids, OL_T + n (the order of assets/art/ol_tiles.txt then ol_icons.txt; tools/gen_ol_tiles.py). They sit over the stage ids, below the HUD glyphs.
#define OL_T        4
#define OL_T_FILL   (OL_T + 4)      // + 0..8: a visualiser bar with that many pixels filled
#define OL_T_BOX    (OL_T + 13)     // + 0..7: the illustration frame's top-left, top, top-right, left, right, bottom-left, bottom, bottom-right
#define OL_T_BACK   (OL_T + 21)     // a plain backdrop (colour 0)
#define OL_T_SLASH  (OL_T + 22)
#define OL_T_ICON   (OL_T + 23)     // + 0..3: square 1, square 2, wave, noise
#define OL_KEY_A    ST_FRAME_TL     // the hint row's A and B buttons: the story font's frame tiles, loaded over by ol_load (the frame is not on these screens)
#define OL_KEY_B    (ST_FRAME_TL + 1)

#define OL_ROW_BAND  3              // the selection line's row
#define OL_ROW_HINT  16
#define OL_SEP       15             // list_frame's separator row

enum { OL_A_PLAY, OL_A_STOP, OL_A_NONE };   // ol_hint: the A button's word (OL_A_NONE: a locked entry, no A)

struct ol_state {                   // over story_scratch (SCR_OL_AT, src/scratch.h): alive while one of the three screens shows
    uint8_t hold;                   // frames until a held LEFT / RIGHT repeats
    uint8_t flash;                  // frames the arrow stays kicked out after a press
    uint8_t key;                    // the key that kicked it (J_LEFT / J_RIGHT / J_UP / J_DOWN)
    uint8_t bob;                    // 1 while the arrows are out by a pixel
    uint8_t t;                      // frames on the screen (the bob's clock)
};
#define OL ((struct ol_state *)(story_scratch + SCR_OL_AT))

void ol_load(void) BANKED;                                  // LCD off, after story_font_load: the shared tiles, the A and B buttons; resets the arrows' state
uint8_t ol_glyph(char c) BANKED;                            // the HUD / story font tile of a character the three screens use ('/' included)
void ol_arrows(uint8_t *r) BANKED;                          // a row buffer: the selection line's two arrows (columns 0 and 19), for the state now
void ol_hint(uint8_t *r, uint8_t a) BANKED;                 // a row buffer: "(A) PLAY (B) BACK" (OL_A_*)
void ol_band(uint8_t arrow_pal) BANKED;                     // LCD off, after list_frame: the band's rows 2-4 (tiles and CGB attributes); the arrows take arrow_pal
uint8_t ol_key(uint8_t pressed, uint8_t held) BANKED;       // J_LEFT / J_RIGHT / J_UP / J_DOWN (a repeat counts), or 0
uint8_t ol_tick(void) BANKED;                               // each frame: 1 when the band's name row must be sent again (the arrows moved)
char *ol_counter(char *d, uint8_t i, uint8_t n) BANKED;     // "i / n" (WRAM) at d, 0-terminated; returns its end
uint8_t ol_wrap(uint8_t s, uint8_t n, int8_t d) BANKED;     // s + d, wrapping in 0..n-1

static void ol_blank(uint8_t *r) {
    uint8_t i;
    for (i = 0; i < 20; i++) r[i] = TILE_HUD_BLANK;
}

#ifndef ONELINE_C
// A string of the caller's bank into a row buffer at column x (255: centred, 254: its last letter in column 18).
static void ol_put(uint8_t *r, uint8_t x, const char *s) {
    uint8_t n = 0;
    while (s[n]) n++;
    if (x == 255) x = (20 - n) >> 1;
    else if (x == 254) x = 19 - n;
    while (*s && x < 20) r[x++] = ol_glyph(*s++);
}
#endif
#endif
