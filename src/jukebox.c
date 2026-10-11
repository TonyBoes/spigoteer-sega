// The title's BONUS: the soundtrack player. BONUS goes straight here while the soundtrack is the only extra (a one-line
// submenu would be one press for nothing); a second extra turns BONUS into a list with SOUNDTRACK first.
//
// Screen (the scores table's style: light HUD glyphs and the story font's punctuation on the dark band, HUD palette):
//   row 0 "SOUNDTRACK", row 1 a panel line; rows 2-11 the tunes in music.h order (JB_VISIBLE at a time, scrolling),
//   the name at columns 1-18, the mug cursor (a sprite) left of it, the playing tune's mug icon at column 19 (it
//   blinks); row 12 a panel line, rows 13-16 the selected tune: its full title (2 lines), the credit, where the game
//   plays it; row 17 a panel line. A locked tune shows "? ? ?" and does not play.
// Up / Down select (wrapping), A or START plays (from the top), B stops the tune, or with none playing goes back to
// the title. The names come from tools/songs.py SOUNDTRACK (build/jukebox_names.h), sized by TUNE_COUNT.
// MUSIC OFF: a tune chosen here plays all the same (the player turns the music on); leaving puts it off again.
// The unlocks are save.c's (tune_unlocked, SRAM v5): the title tune always, the rest as the story is played.
// LCD off to enter; afterwards the rows go through the VBlank queue, JB_ROWS_PER_FRAME a frame, from WRAM buffers
// (story_scratch: no cut-scene runs while this screen shows). OAM: the cursor, entry 0.
#pragma bank 255
#include <gb/gb.h>
#include <stdint.h>

#include "game.h"
#include "music.h"
#include "story.h"
#include "jukebox_names.h"

extern uint8_t overlay_on;

#define JB_ROW_HEAD        0
#define JB_ROW_LIST        2
#define JB_VISIBLE        10
#define JB_ROW_BOX        12       // panel; the info lines 13-16; panel 17
#define JB_INFO_LINES      4
#define JB_COL_PLAY       19
#define JB_ROWS_PER_FRAME  4       // 20-byte rows queued a frame (as mg_say)
#define JB_INFO_BITS     (((1 << JB_INFO_LINES) - 1) << JB_VISIBLE)
#define JB_BLINK          16       // the playing icon: frames on, frames off

uint8_t jb_sel;                    // the selected tune (TUNE_*)
uint8_t jb_top;                    // the first tune shown
uint8_t jb_forced;                 // 1: MUSIC was off and a tune was played here: off again on the way out
uint8_t jb_shown;                  // the tune whose playing icon is drawn (TUNE_NONE: none)
uint8_t jb_t;                      // frames on the screen
static uint16_t jb_dirty;          // bit k < JB_VISIBLE: list line k; the next JB_INFO_LINES bits: the info lines
#define JB_ROW(k) (story_scratch + (uint8_t)(k) * 20)   // row buffer k of JB_VISIBLE + JB_INFO_LINES

static const char locked_name[] = "? ? ?";
static const char *const locked_info[JB_INFO_LINES] = { locked_name, "", "LOCKED", "PLAY STORY MODE" };

static uint8_t jb_glyph(char c) {
    switch (c) {
    case '.': return ST_GLYPH_PERIOD; case ',': return ST_GLYPH_COMMA; case '!': return ST_GLYPH_EXCL;
    case '?': return ST_GLYPH_QUEST; case '\'': return ST_GLYPH_APOS; case '-': return ST_GLYPH_HYPHEN;
    case ':': return ST_GLYPH_COLON;
    }
    return glyph_for(c);
}

static void blank(uint8_t *r) {
    uint8_t i;
    for (i = 0; i < 20; i++) r[i] = TILE_HUD_BLANK;
}

// a string (this bank) into a blank row at column x (255: centred)
static void put(uint8_t *r, uint8_t x, const char *s) {
    uint8_t n = 0;
    blank(r);
    while (s[n]) n++;
    if (x == 255) x = (20 - n) >> 1;
    while (*s) r[x++] = jb_glyph(*s++);
}

static uint8_t unlocked(uint8_t t) {
    return (uint8_t)(tune_unlocked >> t) & 1;
}

// row buffer k: list line k (the tune jb_top + k), or info line k - JB_VISIBLE of the selected tune
static void build(uint8_t k) {
    uint8_t t, *r = JB_ROW(k);
    if (k >= JB_VISIBLE) {
        k -= JB_VISIBLE;
        put(r, 255, unlocked(jb_sel) ? jb_info[jb_sel][k] : locked_info[k]);
        return;
    }
    t = jb_top + k;
    if (t >= TUNE_COUNT) { blank(r); return; }
    put(r, 1, unlocked(t) ? jb_name[t] : locked_name);
    if (t == cur_tune && !(jb_t & JB_BLINK)) r[JB_COL_PLAY] = TILE_HUD_MUG;
}

static uint8_t screen_row(uint8_t k) {
    return k < JB_VISIBLE ? JB_ROW_LIST + k : JB_ROW_BOX + 1 + k - JB_VISIBLE;
}

static void mark_tune(uint8_t t) {             // the list line of tune t, if it is on screen
    if (t >= jb_top && t < jb_top + JB_VISIBLE) jb_dirty |= (uint16_t)1 << (t - jb_top);
}

static void cursor(void) {
    OAM_item_t *o = shadow_OAM;
    o->y = (JB_ROW_LIST + jb_sel - jb_top) * 8 - 7 + 16;     // the mug stands on the line (as the title's cursor)
    o->x = 8;
    o->tile = OBJ_MUG; o->prop = is_cgb ? OBJPAL_MUG_FULL : 0;
}

void jukebox_enter(void) BANKED {
    uint8_t y;
    DISPLAY_OFF;
    overlay_on = 0; HIDE_WIN; vq_reset(); hud_dirty = 0; vram_pending = 0;
    hide_all_sprites();
    music_stop();                              // silence until a tune is chosen (B then goes straight back)
    story_font_load();                         // the punctuation (over the title's lettering: title_enter reloads it)
    jb_sel = 0; jb_top = 0; jb_forced = 0; jb_shown = TUNE_NONE; jb_t = 0; jb_dirty = 0;
    blank(row_buf);
    for (y = 0; y < 18; y++) set_bkg_tiles(0, y, 20, 1, row_buf);
    put(row_buf, 255, "SOUNDTRACK");
    set_bkg_tiles(0, JB_ROW_HEAD, 20, 1, row_buf);
    for (y = 0; y < 20; y++) row_buf[y] = TILE_PANEL_TOP;
    set_bkg_tiles(0, JB_ROW_HEAD + 1, 20, 1, row_buf);
    set_bkg_tiles(0, JB_ROW_BOX, 20, 1, row_buf);
    for (y = 0; y < 20; y++) row_buf[y] = TILE_PANEL_BOT;
    set_bkg_tiles(0, JB_ROW_BOX + JB_INFO_LINES + 1, 20, 1, row_buf);
    for (y = 0; y < JB_VISIBLE + JB_INFO_LINES; y++) {
        build(y);
        set_bkg_tiles(0, screen_row(y), 20, 1, JB_ROW(y));
    }
    if (is_cgb) {
        VBK_REG = VBK_BANK_1;
        for (y = 0; y < 20; y++) row_buf[y] = BGPAL_HUD;
        for (y = 0; y < 18; y++) set_bkg_tiles(0, y, 20, 1, row_buf);
        VBK_REG = VBK_BANK_0;
    }
    cursor();
    game_state = GS_JUKEBOX;
    DISPLAY_ON;
}

// One frame. 1: B went back to the title (the screen changed).
uint8_t jukebox_update(uint8_t pressed) BANKED {
    uint8_t old = jb_sel, top = jb_top, k, n;
    jb_t++;
    if (pressed & J_UP) jb_sel = jb_sel ? jb_sel - 1 : TUNE_COUNT - 1;
    else if (pressed & J_DOWN) jb_sel = jb_sel == TUNE_COUNT - 1 ? 0 : jb_sel + 1;
    if (jb_sel != old) {
        if (jb_sel < jb_top) jb_top = jb_sel;
        else if (jb_sel >= jb_top + JB_VISIBLE) jb_top = jb_sel - (JB_VISIBLE - 1);
        if (jb_top != top) jb_dirty |= (1 << JB_VISIBLE) - 1;
        jb_dirty |= JB_INFO_BITS;
    }
    if (pressed & (J_A | J_START)) {
        if (unlocked(jb_sel)) {
            if (!sound_on) { jb_forced = 1; sound_on = 1; }   // MUSIC OFF: a tune chosen here plays all the same
            music_stop();                                    // (from the top, even the tune already playing)
            music_play(jb_sel);
        }
    } else if (pressed & J_B) {
        if (cur_tune != TUNE_NONE) music_stop();
        else {
            if (jb_forced) music_set_on(0);
            title_enter();
            return 1;
        }
    }
    // the playing icon follows cur_tune (a jingle ends by itself) and blinks
    if (cur_tune != jb_shown) { mark_tune(jb_shown); mark_tune(cur_tune); jb_shown = cur_tune; }
    else if (cur_tune != TUNE_NONE && !(jb_t & (JB_BLINK - 1))) mark_tune(cur_tune);
    for (k = 0, n = 0; k < JB_VISIBLE + JB_INFO_LINES && n < JB_ROWS_PER_FRAME; k++) {
        if (!(jb_dirty & ((uint16_t)1 << k))) continue;
        jb_dirty &= ~((uint16_t)1 << k);
        build(k);
        vq_add(0, JB_ROW(k), 0, screen_row(k), 20);
        n++;
    }
    cursor();
    return 0;
}
