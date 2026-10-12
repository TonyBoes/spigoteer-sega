// The title's BONUS > MINI GAMES (Practice, docs/minigames_bosses.md 2.3; owner 2026-10-11: BONUS's second item): the
// mini-games that are built, each playable once STORY or ARCADE has reached it (save.c's Practice block at SRAM 0x40).
//
// Screen (the soundtrack player's style: light HUD glyphs and the story font's punctuation on the dark band, HUD
// palette): row 0 "MINI GAMES", row 1 a panel line; rows 2.. the games, one a line: the name at columns 1-11, the best
// medal's word at columns 13-18; the mug cursor (OAM 0) left of the name; row 12 a panel line, rows 13-16 the selected
// game: its name, its venue, its best medal, the keys; row 17 a panel line. A game not reached yet lists as "? ? ?"
// (as SOUNDTRACK's locked tunes) and its details read "? ? ?", LOCKED, REACH IT IN STORY, OR ARCADE.
// Up / Down select (wrapping); A or START plays the selected game in MG_PRACTICE (score from 0; its result offers
// "A RETRY B MENU", and B comes back here: src/mg.c); a locked one does nothing. B goes back to the title's BONUS
// submenu with the cursor on MINI GAMES.
// The list: every built game. The DEBUG_MENU build (`make`) lists them all unlocked, the stub GREEN LIGHT included, so
// the owner can test; `make release` lists Quick Draw (the stub is not in it) and applies the unlock rule.
// LCD off to enter; afterwards the rows go through the VBlank queue from WRAM buffers (story_scratch: no cut-scene and
// no mini-game runs while this screen shows; mg_enter rewrites it).
#pragma bank 255
#include <gb/gb.h>
#include <stdint.h>

#include "game.h"
#include "music.h"
#include "story.h"
#include "mg.h"

extern uint8_t overlay_on;

#define ML_ROW_HEAD     0
#define ML_ROW_LIST     2
#define ML_ROW_BOX     12       // panel; the info lines 13-16; panel 17
#define ML_INFO_LINES   4
#define ML_COL_NAME     1
#define ML_COL_MEDAL   13
#define ML_ROWS_PER_FRAME 4     // 20-byte rows queued a frame (as mg_say)
#ifdef DEBUG_MENU
#define ML_N            2
static const uint8_t ml_game[ML_N] = { MG_QUICKDRAW, MG_STUB };
#else
#define ML_N            1
static const uint8_t ml_game[ML_N] = { MG_QUICKDRAW };
#endif
typedef char ml_fits[(ML_N <= ML_ROW_BOX - ML_ROW_LIST) ? 1 : -1];   // (no scrolling yet: 10 lines)
#define ML_INFO_BITS  (((1 << ML_INFO_LINES) - 1) << ML_N)
#define ML_ROW(k)     (story_scratch + (uint8_t)(k) * 20)   // row buffer k: list line k < ML_N, else info line k - ML_N

uint8_t ml_sel;                 // the selected line
uint8_t ml_n;                   // lines listed (tests)
static uint8_t ml_dirty;        // bit k: row buffer k to redraw

static const char locked_name[] = "? ? ?";
static const char *const locked_info[ML_INFO_LINES] = { locked_name, "LOCKED", "REACH IT IN STORY", "OR ARCADE" };
static const char *const medal_name[4] = { "", "BRONZE", "SILVER", "GOLD" };

#ifdef DEBUG_MENU
static const char *game_name(uint8_t g) {
    return g == MG_QUICKDRAW ? "QUICK DRAW" : "GREEN LIGHT";
}

static const char *game_where(uint8_t g) {
    return g == MG_QUICKDRAW ? "THE SALOON" : "THE TEST STUB";
}
#else
#define game_name(g)  "QUICK DRAW"
#define game_where(g) "THE SALOON"
#endif

static uint8_t ml_glyph(char c) {
    switch (c) {
    case '.': return ST_GLYPH_PERIOD; case '?': return ST_GLYPH_QUEST; case '-': return ST_GLYPH_HYPHEN;
    }
    return glyph_for(c);
}

static void blank(uint8_t *r) {
    uint8_t i;
    for (i = 0; i < 20; i++) r[i] = TILE_HUD_BLANK;
}

static void put(uint8_t *r, uint8_t x, const char *s) {   // a string (this bank) at column x (255: centred)
    uint8_t n = 0;
    while (s[n]) n++;
    if (x == 255) x = (20 - n) >> 1;
    while (*s) r[x++] = ml_glyph(*s++);
}

static uint8_t unlocked(uint8_t g) {
#ifdef DEBUG_MENU
    (void)g;
    return 1;
#else
    return g < MG_PLANNED && ((mg_unlocked >> g) & 1);
#endif
}

static uint8_t best(uint8_t g) {
    return g < MG_PLANNED ? mg_best[g] : MEDAL_NONE;
}

static void build(uint8_t k) {
    uint8_t g, n, *r = ML_ROW(k);
    const char *w;
    blank(r);
    if (k >= ML_N) {                            // an info line of the selected game
        k -= ML_N;
        g = ml_game[ml_sel];
        if (!unlocked(g)) { put(r, 255, locked_info[k]); return; }
        switch (k) {
        case 0: put(r, 255, game_name(g)); break;
        case 1: put(r, 255, game_where(g)); break;
        case 2:                                 // "BEST GOLD" centred, or NO MEDAL YET
            if (!best(g)) { put(r, 255, "NO MEDAL YET"); break; }
            w = medal_name[best(g)];
            for (n = 5; w[n - 5]; n++) ;
            n = (20 - n) >> 1;
            put(r, n, "BEST ");
            put(r, n + 5, w);
            break;
        default: put(r, 255, "A PLAY  B BACK");
        }
        return;
    }
    g = ml_game[k];
    if (!unlocked(g)) { put(r, ML_COL_NAME, locked_name); return; }
    put(r, ML_COL_NAME, game_name(g));
    put(r, ML_COL_MEDAL, medal_name[best(g)]);
}

static uint8_t screen_row(uint8_t k) {
    return k < ML_N ? ML_ROW_LIST + k : ML_ROW_BOX + 1 + k - ML_N;
}

static void cursor(void) {
    OAM_item_t *o = shadow_OAM;
    o->y = (ML_ROW_LIST + ml_sel) * 8 - 7 + 16;  // the mug stands on the line (as the title's cursor)
    o->x = 8;
    o->tile = OBJ_MUG; o->prop = is_cgb ? OBJPAL_MUG_FULL : 0;
}

void mg_list_enter(void) BANKED {
    uint8_t y;
    DISPLAY_OFF;
    overlay_on = 0; HIDE_WIN; vq_reset(); hud_dirty = 0; vram_pending = 0;
    hide_all_sprites();
    story_on = 0;                               // (Practice is never a story)
    music_play(TUNE_TITLE);                     // (left alone when it already plays: from the title)
    story_font_load();                          // the punctuation (over the title's lettering: title_enter reloads it)
    if (ml_sel >= ML_N) ml_sel = 0;
    ml_n = ML_N; ml_dirty = 0;
    blank(row_buf);
    for (y = 0; y < 18; y++) set_bkg_tiles(0, y, 20, 1, row_buf);
    put(row_buf, 255, "MINI GAMES");
    set_bkg_tiles(0, ML_ROW_HEAD, 20, 1, row_buf);
    for (y = 0; y < 20; y++) row_buf[y] = TILE_PANEL_TOP;
    set_bkg_tiles(0, ML_ROW_HEAD + 1, 20, 1, row_buf);
    set_bkg_tiles(0, ML_ROW_BOX, 20, 1, row_buf);
    for (y = 0; y < 20; y++) row_buf[y] = TILE_PANEL_BOT;
    set_bkg_tiles(0, ML_ROW_BOX + ML_INFO_LINES + 1, 20, 1, row_buf);
    for (y = 0; y < ML_N + ML_INFO_LINES; y++) {
        build(y);
        set_bkg_tiles(0, screen_row(y), 20, 1, ML_ROW(y));
    }
    if (is_cgb) {
        VBK_REG = VBK_BANK_1;
        for (y = 0; y < 20; y++) row_buf[y] = BGPAL_HUD;
        for (y = 0; y < 18; y++) set_bkg_tiles(0, y, 20, 1, row_buf);
        VBK_REG = VBK_BANK_0;
    }
    cursor();
    game_state = GS_MGLIST;
    DISPLAY_ON;
}

// One frame. 1: the screen changed (a game started, or B went back to the title).
uint8_t mg_list_update(uint8_t pressed) BANKED {
    uint8_t old = ml_sel, k, n;
    if (pressed & J_UP) ml_sel = ml_sel ? ml_sel - 1 : ML_N - 1;
    else if (pressed & J_DOWN) ml_sel = ml_sel == ML_N - 1 ? 0 : ml_sel + 1;
    if (ml_sel != old) ml_dirty |= ML_INFO_BITS;
    if (pressed & (J_A | J_START)) {
        if (unlocked(ml_game[ml_sel])) { mg_enter(ml_game[ml_sel], MG_PRACTICE); return 1; }
    } else if (pressed & J_B) {
        title_back = TM_BONUS; title_back_sel = 1;   // the BONUS submenu, the cursor on MINI GAMES
        title_enter();
        return 1;
    }
    for (k = 0, n = 0; k < ML_N + ML_INFO_LINES && n < ML_ROWS_PER_FRAME; k++) {
        if (!(ml_dirty & (1 << k))) continue;
        ml_dirty &= ~(1 << k);
        build(k);
        vq_add(0, ML_ROW(k), 0, screen_row(k), 20);
        n++;
    }
    cursor();
    return 0;
}
