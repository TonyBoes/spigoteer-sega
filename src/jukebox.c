// The title's BONUS > SOUNDTRACK: the soundtrack player (the title's submenus: src/title.c; BONUS's second item, MINI GAMES, is src/mg_list.c).
//
// Screen, in the one-line style of src/oneline.h (the wood wall of src/mg_list.c list_frame; light HUD glyphs and the story font's punctuation):
//   row 0 "SOUNDTRACK" and the counter "5 / 15" at the right   row 3 the selection line "< GALOP INFERNAL >" in the panel's band (rows 2-4)
//   row 6 the composer and year   row 7 where the game plays it   rows 10-13 the four channels' bars, stacked with no gap (a channel icon at column 2, a bar of
//   15 tiles = 120 px from column 4)   row 15 a panel line   row 16 "(A) PLAY (B) BACK" (A reads STOP while the selected tune is the one playing)
// LEFT / RIGHT select the previous / next tune (wrapping, hold-to-repeat), UP / DOWN five tunes; selecting never starts a tune. A plays the selected tune from the
// top; A on the tune that is playing stops it; B always leaves for the BONUS submenu (the title's own tune takes over). A locked tune shows "? ? ?" and does
// not play (the hint row then has no A). The names come from tools/songs.py SOUNDTRACK (build/jukebox_names.h), sized by TUNE_COUNT.
// MUSIC OFF: a tune chosen here plays all the same (the player turns the music on); leaving puts it off again.
// The unlocks are save.c's (tune_unlocked, SRAM v5): the title tune always, the rest as the story is played.
//
// The bars. Color: the sound chip's own PCM12 / PCM34 registers (the channels' digital outputs, 4 bits each), read once a frame: a bar jumps to the highest value
// seen and falls CGB_FALL px a frame. DMG (no such registers): a note-start meter read from the driver's own state, with no hook in it and nothing added to
// music_tick: when hUGE_row has changed, each channel's pattern cell for that row (the four pattern pointers sit in the 8 bytes before hUGE_ticks_per_row)
// says whether a note starts (channels 2-4; the pattern pointers of channel 1 are not read: it is src/music.c's harmony voice, which the driver never plays, so its
// bar follows music.c's harmony pointer: a new event that sounds is a start); that channel's bar jumps to full and falls DMG_FALL px a frame. The drum groove, which
// src/music.c plays outside the patterns, kicks the noise bar through g_step. All of it runs in this screen's update.
// LCD off to enter; afterwards the rows go through the VBlank queue from WRAM buffers (story_scratch: no cut-scene runs while this screen shows), at most
// JB_ROWS_PER_FRAME a frame, and a bar that moved is queued as the run of its tiles that changed (a fall is two or three).
#pragma bank 255
#include <gb/gb.h>
#include <gb/cgb.h>
#include <stdint.h>

#include "game.h"
#include "music.h"
#include "story.h"
#include "oneline.h"
#include "palettes.h"
#include "jukebox_names.h"

extern uint8_t overlay_on, joy, g_step;
extern unsigned char hUGE_ticks_per_row, hUGE_row;
extern const uint8_t *h_ptr;                     // src/music.c: the harmony track's next event
extern uint8_t h_sound;                          // 1: a harmony note sounds on channel 1

#define RGB15(r, g, b) ((uint16_t)((r) | ((g) << 5) | ((b) << 10)))
#define PCM12 (*(volatile uint8_t *)0xFF76)     // CGB: channels 1 (low nibble) and 2 (high) digital output
#define PCM34 (*(volatile uint8_t *)0xFF77)     // CGB: channels 3 and 4

// The row buffers (in story_scratch) and their screen rows
#define JB_R_NAME      0
#define JB_R_CREDIT    1
#define JB_R_WHERE     2
#define JB_R_HEAD      3
#define JB_R_BAR       4        // 4-7: the four channels' bars
#define JB_R_HINT      8
#define JB_ROWS        9
#define JB_ROW(k) (story_scratch + (uint8_t)(k) * 20)
#define JB_ROWS_PER_FRAME  1    // rows built and queued a frame (a row is ~10k cycles, and the bars cost as much again on a DMG)
#define JB_BAR_ROW     10       // the bars' screen rows, stacked
#define JB_BAR_COL      4
#define JB_BAR_W       15
#define JB_BAR_PX      (JB_BAR_W * 8)
#define JB_ICON_COL     2
#define JB_JUMP         5       // UP / DOWN: this many tunes
#define PCM_PX         12       // a PCM level (0-15) in px (saturates at 10: the music's own volumes rarely go higher)
#define CGB_FALL        4
#define DMG_FALL        8

// The meter's state, after the row buffers
struct jb_meter {
    uint8_t level[4];           // each bar's length in px (0-120) as drawn
    uint8_t peak[4];            // DMG: a note start's level (JB_BAR_PX), falling DMG_FALL a frame
    uint8_t row;                // DMG: the driver's row as of the last frame
    uint8_t step;               // DMG: g_step as of the last frame
    const uint8_t *hptr;        // DMG: music.c's harmony pointer (its next event) as of the last frame: it moves on at each harmony note start
};
#define JB ((struct jb_meter *)(story_scratch + JB_ROWS * 20))
typedef char jb_scratch_fits[(JB_ROWS * 20 + sizeof(struct jb_meter) <= STORY_SCRATCH) ? 1 : -1];

uint8_t jb_sel;                    // the selected tune (TUNE_*)
uint8_t jb_forced;                 // 1: MUSIC was off and a tune was played here: off again on the way out
uint8_t jb_shown;                  // cur_tune as of the last frame (TUNE_NONE: none): the hint row's A word is built for it
static uint16_t jb_dirty;          // bit k: row buffer k to redraw

static const char locked_name[] = "? ? ?";
static const uint16_t bar_pal[4][4] = {      // c0 the bar, c1 its top highlight, c2 its shade and the groove, c3 the wall
    { RGB15(31, 12, 6),  RGB15(31, 22, 14), RGB15(16, 5, 3),  RGB15(7, 3, 2) },    // square 1: red
    { RGB15(31, 26, 5),  RGB15(31, 31, 16), RGB15(17, 13, 2), RGB15(7, 3, 2) },    // square 2: yellow
    { RGB15(10, 26, 8),  RGB15(20, 31, 16), RGB15(4, 14, 3),  RGB15(7, 3, 2) },    // wave: green
    { RGB15(8, 18, 31),  RGB15(18, 26, 31), RGB15(3, 9, 17),  RGB15(7, 3, 2) },    // noise: blue
};
static const uint8_t bar_slot[4] = { 0, 1, 3, 4 };   // the BG palettes they take (the wall look keeps 2, 5, 6, 7; 3 and 4 are its medal and button palettes, unused here)
#define ARROW_PAL  1                                  // the arrows' gold: the yellow bar's palette

static uint8_t unlocked(uint8_t t) {
#ifdef TUNES_ALL                                      // playtest builds (make TUNES=ALL): every tune listed and playable
    (void)t;
    return 1;
#else
    return (uint8_t)(tune_unlocked >> t) & 1;
#endif
}

static void bar_fill(uint8_t i, uint8_t px, uint8_t a, uint8_t b) {   // bar i's row buffer, tiles a..b of its 15, for a length of px (0-120)
    uint8_t *r = JB_ROW(JB_R_BAR + i) + JB_BAR_COL + a, v = a * 8;
    for (; a <= b; a++, v += 8) *r++ = px >= (uint8_t)(v + 8) ? OL_T_FILL + 8 : px > v ? OL_T_FILL + (px - v) : OL_T_FILL;
}

static void bar_row(uint8_t i, uint8_t px) {    // bar i's whole row buffer: its icon, then its 15 tiles
    JB_ROW(JB_R_BAR + i)[JB_ICON_COL] = OL_T_ICON + i;
    bar_fill(i, px, 0, JB_BAR_W - 1);
}

static void build(uint8_t k) {
    uint8_t *r = JB_ROW(k), v = jb_sel, ok = unlocked(v);
    char b[8];
    ol_blank(r);
    switch (k) {
    case JB_R_NAME: ol_arrows(r); ol_put(r, 255, ok ? jb_name[v] : locked_name); break;
    case JB_R_CREDIT: ol_put(r, 255, ok ? jb_info[v][2] : "LOCKED"); break;
    case JB_R_WHERE: ol_put(r, 255, ok ? jb_info[v][3] : "PLAY STORY MODE"); break;
    case JB_R_HEAD:
        ol_put(r, 1, "SOUNDTRACK");
        ol_counter(b, v + 1, TUNE_COUNT);
        ol_put(r, 254, b);
        break;
    case JB_R_HINT: ol_hint(r, !ok ? OL_A_NONE : jb_shown == v ? OL_A_STOP : OL_A_PLAY); break;
    default: bar_row(k - JB_R_BAR, JB->level[k - JB_R_BAR]);
    }
}

static uint8_t screen_row(uint8_t k) {
    switch (k) {
    case JB_R_NAME: return OL_ROW_BAND;
    case JB_R_CREDIT: return 6;
    case JB_R_WHERE: return 7;
    case JB_R_HEAD: return 0;
    case JB_R_HINT: return OL_ROW_HINT;
    }
    return JB_BAR_ROW + (k - JB_R_BAR);
}

void jukebox_enter(void) BANKED {
    uint8_t y, i, x;
    TRANS_MENU();                              // (src/trans.c: the quick white fade)
    DISPLAY_OFF;
    music_pump();                              // (the tick this pass is due: the rebuild runs several frames)
    overlay_on = 0; HIDE_WIN; vq_reset(); hud_dirty = 0; vram_pending = 0;
    hide_all_sprites();
    music_pump();                              // (the title tune plays on through the rebuild, then silence until a tune is chosen)
    story_font_load();                         // the punctuation (over the title's lettering: title_enter reloads it)
    ol_load();
    music_pump();
    jb_sel = 0; jb_forced = 0; jb_shown = TUNE_NONE; jb_dirty = 0;
    for (i = 0; i < sizeof(struct jb_meter); i++) ((uint8_t *)JB)[i] = 0;
    list_frame(OL_SEP);                        // (the wood wall, src/mg_list.c: tiles, palettes, the header band, the panel)
    ol_band(ARROW_PAL);
    for (y = 0; y < JB_ROWS; y++) {
        build(y);
        set_bkg_tiles(0, screen_row(y), 20, 1, JB_ROW(y));
        if (!(y & 3)) music_pump();
    }
    if (is_cgb) {                              // each bar's palette on its row: its icon and 15 tiles
        for (i = 0; i < 4; i++) {
            set_bkg_palette(bar_slot[i], 1, (uint16_t *)bar_pal[i]);
            for (x = 0; x < 20; x++) row_buf[x] = x == JB_ICON_COL || (x >= JB_BAR_COL && x < JB_BAR_COL + JB_BAR_W) ? bar_slot[i] : SKIN_PAL_WALL;
            VBK_REG = VBK_BANK_1;
            set_bkg_tiles(0, JB_BAR_ROW + i, 20, 1, row_buf);
            VBK_REG = VBK_BANK_0;
        }
    }
    music_pump();
    game_state = GS_JUKEBOX;
    music_stop();                              // silence until a tune is chosen
    DISPLAY_ON;
}

// The bars, one frame: Color reads the PCM registers, a DMG the driver's note starts. A bar that moved is queued as the run of its tiles that changed.
static void meters(void) {
    struct jb_meter *m = JB;
    uint8_t i, v, t, a, b, row, step;
    uint16_t px;
    const uint16_t *pat;
    if (!is_cgb) {
        row = hUGE_row; step = g_step;
        if (cur_tune != TUNE_NONE) {
            pat = (const uint16_t *)((const uint8_t *)&hUGE_ticks_per_row - 8);   // pattern1 .. pattern4: the driver's current patterns (3 bytes a row, the note first)
            if (row != m->row) {
                for (i = 1; i < 4; i++) if (pat[i] >= 0xC000 && *(const uint8_t *)(pat[i] + 3 * (uint16_t)row) < 72) m->peak[i] = JB_BAR_PX;
            }
            if (step && !m->step) m->peak[3] = JB_BAR_PX;
            if (h_ptr != m->hptr && h_sound) m->peak[0] = JB_BAR_PX;         // channel 1 is src/music.c's harmony voice (the driver never plays it): h_ptr steps on at each event
            m->hptr = h_ptr;                                                    // (a note straight after a note leaves NR12 as it was: the envelope register showed no start)
        }
        m->row = row; m->step = step;
    }
    for (i = 0; i < 4; i++) {
        if (is_cgb) {
            v = i & 2 ? PCM34 : PCM12;
            if (i & 1) v >>= 4;
            px = (uint16_t)(v & 15) * PCM_PX;
            if (px > JB_BAR_PX) px = JB_BAR_PX;
        } else {
            px = m->peak[i];
            m->peak[i] = px > DMG_FALL ? px - DMG_FALL : 0;
        }
        t = m->level[i];
        v = t;
        t = t > (is_cgb ? CGB_FALL : DMG_FALL) ? t - (is_cgb ? CGB_FALL : DMG_FALL) : 0;
        if (px > t) t = (uint8_t)px;
        if (t == v) continue;
        m->level[i] = t;
        a = (t < v ? t : v) >> 3;                // only the tiles between the old length and the new one change
        b = (t < v ? v : t) >> 3;
        if (b >= JB_BAR_W) b = JB_BAR_W - 1;
        bar_fill(i, t, a, b);
        vq_add(0, JB_ROW(JB_R_BAR + i) + JB_BAR_COL + a, JB_BAR_COL + a, JB_BAR_ROW + i, b - a + 1);
    }
}

// One frame. 1: B went back to the title (the screen changed).
uint8_t jukebox_update(uint8_t pressed) BANKED {
    uint8_t old = jb_sel, key = ol_key(pressed, joy), k, n;
    if (key == J_LEFT) jb_sel = ol_wrap(jb_sel, TUNE_COUNT, -1);
    else if (key == J_RIGHT) jb_sel = ol_wrap(jb_sel, TUNE_COUNT, 1);
    else if (key == J_UP) jb_sel = ol_wrap(jb_sel, TUNE_COUNT, -JB_JUMP);
    else if (key == J_DOWN) jb_sel = ol_wrap(jb_sel, TUNE_COUNT, JB_JUMP);
    if (ol_tick()) jb_dirty |= 1 << JB_R_NAME;
    if (jb_sel != old) jb_dirty |= (1 << JB_R_NAME) | (1 << JB_R_CREDIT) | (1 << JB_R_WHERE) | (1 << JB_R_HEAD) | (1 << JB_R_HINT);   // (no tune starts)
    if (pressed & (J_A | J_START)) {
        if (cur_tune == jb_sel) music_stop();                 // A on the tune that plays: stop it
        else if (unlocked(jb_sel)) {
            if (!sound_on) { jb_forced = 1; sound_on = 1; }   // MUSIC OFF: a tune chosen here plays all the same
            music_stop();
            music_play(jb_sel);
        }
    } else if (pressed & J_B) {                               // B always leaves
        if (jb_forced) music_set_on(0);
        title_enter();
        return 1;
    }
    if (cur_tune != jb_shown) { jb_shown = cur_tune; jb_dirty |= 1 << JB_R_HINT; }   // (a jingle ends by itself)
    for (k = 0, n = 0; k < JB_ROWS && n < JB_ROWS_PER_FRAME; k++) {
        if (!(jb_dirty & ((uint16_t)1 << k))) continue;
        jb_dirty &= ~((uint16_t)1 << k);
        build(k);
        vq_add(0, JB_ROW(k), 0, screen_row(k), 20);
        n++;
    }
    meters();
    return 0;
}
