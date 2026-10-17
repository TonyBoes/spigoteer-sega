// M10b arcade screens: the initials entry after a game over that made the top 5, and the top-5 table (after every
// game over, after the story's credits, and from the title after TITLE_IDLE_FRAMES without a key: title.c, which
// cycles the three tables). The three modes: one table per mode, save.c score_tbl says which; its header names the
// mode ("ARCADE HIGH SCORES", "STORY HIGH SCORES", "CLASSIC HIGH SCORES"). The tables and their SRAM copies are
// save.c's. Both screens are the HUD's style: light HUD glyphs on the dark band (BG palette 1 on CGB, BGP on
// DMG), a panel line above and below, every line centred on the 20 columns.
// LCD off to enter; afterwards every tilemap change goes through the VBlank queue (vq_add) from WRAM buffers.
// Initials: Up / Down change the letter (A..Z, then a space), Left / Right move between the three, A (or START)
// saves them and shows the table. The table stays SCORES_FRAMES, or until A / B / START; then the title.
#pragma bank 255
#include <gb/gb.h>
#include <stdint.h>

#include "game.h"
#include "music.h"

extern uint8_t overlay_on, game_state, new_rank;
extern uint32_t score;

#define ROW_HEAD        3       // "HIGH SCORES" / "NEW HIGH SCORE"
#define ROW_FIRST       6       // the table: rows 6, 8, .. 14
#define ROW_SCORE       5       // initials screen: the score
#define ROW_ENTER       8       // "ENTER INITIALS"
#define ROW_INITIALS   11       // the three letters at columns INI_COL, +2, +4
#define ROW_CURSOR     12       // the cursor bar under the current letter
#define INI_COL         8
#define TABLE_COL       4       // "1 ABC 012345": 12 characters at columns 4..15
#define SCORES_FRAMES 300       // the table stays 5 s

uint8_t  ini_name[3];           // the initials being entered (ASCII)
uint8_t  ini_pos;               // 0..2: the letter being changed
uint16_t scores_timer;          // frames the table has been shown

static uint8_t ini_row[20], cur_row[20];

static const uint8_t alpha[26] = {
    TILE_GLYPH_A, TILE_GLYPH_B, TILE_GLYPH_C, TILE_GLYPH_D, TILE_GLYPH_E, TILE_GLYPH_F, TILE_GLYPH_G, TILE_GLYPH_H,
    TILE_GLYPH_I, TILE_GLYPH_J, TILE_GLYPH_K, TILE_GLYPH_L, TILE_GLYPH_M, TILE_GLYPH_N, TILE_GLYPH_O, TILE_GLYPH_P,
    TILE_GLYPH_Q, TILE_GLYPH_R, TILE_GLYPH_S, TILE_GLYPH_T, TILE_GLYPH_U, TILE_GLYPH_V, TILE_GLYPH_W, TILE_GLYPH_X,
    TILE_GLYPH_Y, TILE_GLYPH_Z,
};

static uint8_t tile_of(uint8_t c) {
    if (c >= 'A' && c <= 'Z') return alpha[c - 'A'];
    if (c >= '0' && c <= '9') return TILE_GLYPH_0 + (c - '0');
    return TILE_HUD_BLANK;
}

static void blank_row(uint8_t *r) {
    uint8_t i;
    for (i = 0; i < 20; i++) r[i] = TILE_HUD_BLANK;
}

// LCD off: a string at column x of row y (x 255: centred)
static void text_at(uint8_t y, uint8_t x, const char *s) {
    uint8_t n = 0, i;
    while (s[n]) n++;
    if (x == 255) x = (20 - n) >> 1;
    blank_row(row_buf);
    for (i = 0; i < n; i++) row_buf[x + i] = tile_of(s[i]);
    set_bkg_tiles(0, y, 20, 1, row_buf);
}

static void six_digits(char *d, uint32_t v) {
    uint8_t i;
    split6((uint8_t *)d, v);                         // (save.c: no 32-bit division, ~1 frame per score before)
    for (i = 0; i < 6; i++) d[i] += '0';
}

// LCD off: the dark band everywhere, a panel line at rows 1 and 16, the HUD palette
static void screen_begin(void) {
    uint8_t y;
    DISPLAY_OFF;
    overlay_on = 0; HIDE_WIN; vq_reset(); hud_dirty = 0; vram_pending = 0; life_lost = 0;
    clear_dirty();
    hide_all_sprites();
    music_pump();
    blank_row(row_buf);
    for (y = 0; y < 18; y++) set_bkg_tiles(0, y, 20, 1, row_buf);
    for (y = 0; y < 20; y++) row_buf[y] = TILE_PANEL_TOP;
    set_bkg_tiles(0, 1, 20, 1, row_buf);
    for (y = 0; y < 20; y++) row_buf[y] = TILE_PANEL_BOT;
    set_bkg_tiles(0, 16, 20, 1, row_buf);
    if (is_cgb) {
        VBK_REG = VBK_BANK_1;
        for (y = 0; y < 20; y++) row_buf[y] = BGPAL_HUD;
        for (y = 0; y < 18; y++) set_bkg_tiles(0, y, 20, 1, row_buf);
        VBK_REG = VBK_BANK_0;
    }
    music_pump();
}

// ---- the table --------------------------------------------------------------------------------
static const char *const tbl_head[TOP_TABLES] = { "ARCADE HIGH SCORES", "STORY HIGH SCORES", "CLASSIC HIGH SCORES" };

// the mark of the entry whose initials are n[0..2]: bit 7 of the first (save.c) HARD, of the second EASY
static char mark_of(const uint8_t *n) {
    return n[0] & 0x80 ? 'H' : n[1] & 0x80 ? 'E' : ' ';
}

// table score_tbl (MODE_*), its header naming the mode
void scores_table(void) BANKED {
    uint8_t i, k, *nm = top_names + score_tbl * (TOP_N * 3);
    uint32_t *sc = top_scores + score_tbl * TOP_N;
    char s[15];
    screen_begin();
    text_at(ROW_HEAD, 255, tbl_head[score_tbl]);
    s[1] = ' '; s[5] = ' '; s[12] = ' '; s[14] = 0;
    for (i = 0; i < TOP_N; i++) {
        s[0] = '1' + i;
        for (k = 0; k < 3; k++) s[2 + k] = nm[i * 3 + k] & 0x7F;
        six_digits(s + 6, sc[i]);
        s[13] = mark_of(nm + i * 3);               // (STORY's table: H after a HARD score, E after an EASY one; every other entry unmarked)
        text_at(ROW_FIRST + 2 * i, TABLE_COL, s);
        music_pump();
    }
    scores_timer = 0;
    game_state = GS_SCORES;
    music_pump();                       // (the title tune plays on through the switch: music.c)
    DISPLAY_ON;
}

// ---- the initials -------------------------------------------------------------------------------
static void ini_draw(void) {        // the letters and the cursor into their buffers, queued
    uint8_t i;
    blank_row(ini_row); blank_row(cur_row);
    for (i = 0; i < 3; i++) ini_row[INI_COL + 2 * i] = tile_of(ini_name[i]);
    cur_row[INI_COL + 2 * ini_pos] = HUD_CURSOR_BG;
}

static void initials_enter(void) {
    char d[10];
    uint8_t *n = top_names + score_tbl * (TOP_N * 3) + new_rank * 3, pct, i;
    const char *w;
    screen_begin();
    hud_icon_load(HUD_CURSOR_BG, HUD_ICON_CURSOR);
    // (the cursor is no generic tile: see assets/tiles/bar.txt hud_flag)
    text_at(ROW_HEAD, 255, "NEW HIGH SCORE");
    six_digits(d, score); d[6] = 0;
    text_at(ROW_SCORE, 255, d);
    text_at(ROW_ENTER, 255, "ENTER INITIALS");
    ini_name[0] = ini_name[1] = ini_name[2] = 'A';
    ini_pos = 0;
    ini_draw();
    set_bkg_tiles(0, ROW_INITIALS, 20, 1, ini_row);
    set_bkg_tiles(0, ROW_CURSOR, 20, 1, cur_row);
    game_state = GS_INITIALS;
    DISPLAY_ON;
}

// After the GAME OVER banner: the initials when the game made the top 5 (game over put it in as "AAA"), else the table.
void scores_after_game(void) BANKED {
    if (new_rank < TOP_N) initials_enter(); else scores_table();
}

static uint8_t next_letter(uint8_t c, uint8_t up) {     // A..Z, space, A..
    if (up) return c == ' ' ? 'A' : c == 'Z' ? ' ' : c + 1;
    return c == ' ' ? 'Z' : c == 'A' ? ' ' : c - 1;
}

// One frame of either screen. 1: done, back to the title.
uint8_t scores_update(uint8_t pressed) BANKED {
    uint8_t *c;
    if (game_state == GS_SCORES) {
        if ((pressed & (J_A | J_B | J_START)) || ++scores_timer >= SCORES_FRAMES) return 1;
        return 0;
    }
    if (pressed & (J_A | J_START)) {                    // save the initials, then the table
        c = top_names + score_tbl * (TOP_N * 3) + new_rank * 3;
        c[0] = ini_name[0] | (c[0] & 0x80); c[1] = ini_name[1] | (c[1] & 0x80); c[2] = ini_name[2];   // (the entry's mark stays)
        hi_save();
        scores_table();
        return 0;
    }
    if (!(pressed & (J_UP | J_DOWN | J_LEFT | J_RIGHT))) return 0;
    if (pressed & (J_UP | J_DOWN)) ini_name[ini_pos] = next_letter(ini_name[ini_pos], pressed & J_UP);
    else if (pressed & J_LEFT) ini_pos = ini_pos ? ini_pos - 1 : 2;
    else ini_pos = ini_pos == 2 ? 0 : ini_pos + 1;
    ini_draw();
    vq_add(0, ini_row, 0, ROW_INITIALS, 20);
    vq_add(0, cur_row, 0, ROW_CURSOR, 20);
    return 0;
}
