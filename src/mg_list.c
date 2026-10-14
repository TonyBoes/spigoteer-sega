// The title's BONUS > MINI GAMES (Practice, docs/minigames_bosses.md 2.3; owner 2026-10-11: BONUS's second item): the
// mini-games that are built, each playable once STORY or ARCADE has reached it (save.c's Practice block at SRAM 0x40).
//
// Screen (the soundtrack player's style: light HUD glyphs and the story font's punctuation on the dark band, HUD
// palette): row 0 "MINI GAMES", row 1 a panel line; rows 2.. the games, one a line: the name at columns 1-12, the best
// medal's word at columns 14-19; the mug cursor (OAM 0) left of the name; row 12 a panel line, rows 13-16 the selected
// game: its name, its venue, its best medal, the keys; row 17 a panel line. A game not reached yet lists as "? ? ?"
// (as SOUNDTRACK's locked tunes) and its details read "? ? ?", LOCKED, REACH IT IN STORY, OR ARCADE.
// SELECT (or LEFT / RIGHT) flips NORMAL / HARD (owner Q7; the flag lives in bit 7 of ml_dirty, so it outlasts a game): the
// header's right side names the mode in force for the selected game, the list's medal column and the "BEST" line show that
// mode's best (save.c keeps a HARD medal apart: bits 2-3 of the game's mg_best byte). Only the games that read MG_HARD
// (hard_game: Milk Run, and the debug stub) take it; on any other the toggle does nothing, the header says NORMAL and the
// last info line says NORMAL ONLY. Playing starts with MG_PRACTICE | MG_HARD when HARD is in force.
// Up / Down select (wrapping); A or START plays the selected game in MG_PRACTICE (score from 0; its result offers
// "A RETRY B MENU", and B comes back here: src/mg.c); a locked one does nothing. B goes back to the title's BONUS
// submenu with the cursor on MINI GAMES.
// The list: every built game. The DEBUG_MENU build (`make`) lists them all unlocked, the stub GREEN LIGHT included, so
// the owner can test; `make release` lists Quick Draw, Order Up!, Battery Sort, Milk Run, Log Roll, Asteroids, Taiko Pour and Shirt Cannon (the stub is not in it) and applies
// the unlock rule.
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
#define ML_COL_NAME     1
#define ML_COL_MEDAL   14       // (BATTERY SORT is 12 letters: columns 1-12)
#define ML_ROWS_PER_FRAME 4     // 20-byte rows queued a frame (as mg_say)
// chapter order (docs/story.md: saloon, stadium, lodge, bistro, igloo, robot factory, Chrome Cow, teahouse, zoo, space lounge)
#ifdef DEBUG_MENU
#define ML_N            11
static const uint8_t ml_game[ML_N] = { MG_QUICKDRAW, MG_TSHIRT, MG_LOGROLL, MG_ORDERUP, MG_MARSHMALLOW, MG_BATTERY, MG_MILKRUN, MG_TAIKO, MG_MONKEY, MG_ASTEROID, MG_STUB };
#else
#define ML_N            10
static const uint8_t ml_game[ML_N] = { MG_QUICKDRAW, MG_TSHIRT, MG_LOGROLL, MG_ORDERUP, MG_MARSHMALLOW, MG_BATTERY, MG_MILKRUN, MG_TAIKO, MG_MONKEY, MG_ASTEROID };
#endif
// The panel sits one blank row under the last line (the Boss Rush list's fix, cfc9b38): list rows 2..ML_N+1, a blank row, the
// separator, the info lines up to row 16, the panel's bottom on 17. The cursor's line shows the game's name, so the info lines
// are the venue, the best medal and (when the screen has the room: 10 lines, not the debug build's 11) the keys.
#define ML_ROW_BOX     (ML_ROW_LIST + ML_N + 1)
#define ML_INFO_LINES  (16 - ML_ROW_BOX)
typedef char ml_fits[(ML_INFO_LINES >= 2) ? 1 : -1];   // (no scrolling yet: up to 11 lines)
#define ML_HEAD_K     (ML_N + ML_INFO_LINES)          // the header's buffer / dirty bit (after the info lines)
#define ML_HARD       0x80                            // ml_dirty's bit 7: HARD is on (kept; the dirty bits are 0..ML_INFO_LINES)
#define ML_DIRTY_BITS ((1 << (ML_INFO_LINES + 1)) - 1)
#define ML_COL_MODE   13                              // the header's mode word ("MINI GAMES" is columns 1-10)
#define ML_ROW(k)     (story_scratch + (uint8_t)(k) * 20)   // row buffer k: list line k < ML_N, else info line k - ML_N

uint8_t ml_sel;                 // the selected line
uint8_t ml_n;                   // lines listed (tests)
static uint8_t ml_dirty;        // bit k: the info line k (row buffer ML_N + k) to redraw; bit ML_INFO_LINES the header; bit 7 HARD

static const char locked_name[] = "? ? ?";
static const char *const locked_info[3] = { "LOCKED", "REACH IT IN STORY", "OR ARCADE" };
static const char *const medal_name[4] = { "", "BRONZE", "SILVER", "GOLD" };

static const char *game_name(uint8_t g) {
    if (g == MG_QUICKDRAW) return "QUICK DRAW";
    if (g == MG_ORDERUP) return "ORDER UP";      // (no '!': the list has no tile for it)
    if (g == MG_BATTERY) return "BATTERY SORT";
    if (g == MG_MILKRUN) return "MILK RUN";
    if (g == MG_LOGROLL) return "LOG ROLL";
    if (g == MG_ASTEROID) return "ASTEROIDS";
    if (g == MG_TAIKO) return "TAIKO POUR";
    if (g == MG_MARSHMALLOW) return "MARSHMALLOWS";
    if (g == MG_MONKEY) return "MONKEY BIZ";      // (the list's name column ends at 13: the details line has the whole name)
    if (g == MG_TSHIRT) return "SHIRT CANNON";
#ifdef DEBUG_MENU
    return "GREEN LIGHT";
#else
    return "";
#endif
}

static const char *game_where(uint8_t g) {
    if (g == MG_QUICKDRAW) return "THE SALOON";
    if (g == MG_ORDERUP) return "THE BISTRO";
    if (g == MG_BATTERY) return "THE ROBOT FACTORY";
    if (g == MG_MILKRUN) return "THE CHROME COW";
    if (g == MG_LOGROLL) return "THE LUMBER LODGE";
    if (g == MG_ASTEROID) return "THE SPACE LOUNGE";
    if (g == MG_TAIKO) return "THE TEAHOUSE";
    if (g == MG_MARSHMALLOW) return "THE IGLOO";
    if (g == MG_MONKEY) return "THE JUNGLE ZOO";
    if (g == MG_TSHIRT) return "THE STADIUM";
#ifdef DEBUG_MENU
    return "THE TEST STUB";
#else
    return "";
#endif
}

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

static uint8_t hard_game(uint8_t g) {             // the games that read MG_HARD (PLAN.md "Practice HARD toggle")
#ifdef DEBUG_MENU
    if (g == MG_STUB) return 1;
#endif
    return g == MG_MILKRUN;
}

static uint8_t hard_for(uint8_t g) {              // the mode in force for g
    return (ml_dirty & ML_HARD) && hard_game(g);
}

static uint8_t best(uint8_t g) {
    return g < MG_PLANNED ? (mg_best[g] >> (hard_for(g) ? 2 : 0)) & 3 : MEDAL_NONE;
}

static void build(uint8_t k) {
    uint8_t g, n, *r = ML_ROW(k);
    const char *w;
    blank(r);
    if (k == ML_HEAD_K) {                       // the header: the title and the mode in force for the selected game
        put(r, 1, "MINI GAMES");
        put(r, ML_COL_MODE, hard_for(ml_game[ml_sel]) ? "HARD" : "NORMAL");
        return;
    }
    if (k >= ML_N) {                            // an info line of the selected game
        k -= ML_N;
        g = ml_game[ml_sel];
        if (!unlocked(g)) { put(r, 255, locked_info[k]); return; }
        switch (k) {
        case 0: put(r, 255, game_where(g)); break;
        case 1:                                 // "BEST GOLD" centred, or NO MEDAL YET
            if (!best(g)) { put(r, 255, "NO MEDAL YET"); break; }
            w = medal_name[best(g)];
            for (n = 5; w[n - 5]; n++) ;
            n = (20 - n) >> 1;
            put(r, n, "BEST ");
            put(r, n + 5, w);
            break;
        default: put(r, 255, hard_game(g) ? "A PLAY  B BACK  SEL" : "NORMAL ONLY  B BACK");
        }
        return;
    }
    g = ml_game[k];
    if (!unlocked(g)) { put(r, ML_COL_NAME, locked_name); return; }
    put(r, ML_COL_NAME, game_name(g));
    put(r, ML_COL_MEDAL, medal_name[best(g)]);
}

static uint8_t screen_row(uint8_t k) {
    return k == ML_HEAD_K ? ML_ROW_HEAD : k < ML_N ? ML_ROW_LIST + k : ML_ROW_BOX + 1 + k - ML_N;
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
    music_pump();                               // (the tick this pass is due: the rebuild runs several frames)
    overlay_on = 0; HIDE_WIN; vq_reset(); hud_dirty = 0; vram_pending = 0;
    hide_all_sprites();
    story_on = 0;                               // (Practice is never a story)
    music_play(TUNE_TITLE);                     // (left alone when it already plays: from the title; after a game its patterns are
    music_load_now();                           // copied back now, and the pumps below tick it through the rebuild)
    music_pump();
    mug_cursor_load();                          // (a game borrowed the mug's tiles and palettes)
    music_pump();
    story_font_load();                          // the punctuation (over the title's lettering: title_enter reloads it)
    music_pump();
    if (ml_sel >= ML_N) ml_sel = 0;
    ml_n = ML_N; ml_dirty &= ML_HARD;
    blank(row_buf);
    for (y = 0; y < 18; y++) { set_bkg_tiles(0, y, 20, 1, row_buf); if (!(y & 3)) music_pump(); }
    for (y = 0; y < 20; y++) row_buf[y] = TILE_PANEL_TOP;
    set_bkg_tiles(0, ML_ROW_HEAD + 1, 20, 1, row_buf);
    set_bkg_tiles(0, ML_ROW_BOX, 20, 1, row_buf);
    for (y = 0; y < 20; y++) row_buf[y] = TILE_PANEL_BOT;
    set_bkg_tiles(0, ML_ROW_BOX + ML_INFO_LINES + 1, 20, 1, row_buf);
    for (y = 0; y <= ML_HEAD_K; y++) {
        build(y);
        set_bkg_tiles(0, screen_row(y), 20, 1, ML_ROW(y));
        if (!(y & 3)) music_pump();
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
    uint8_t old = ml_sel, k, n, g;
    if (pressed & J_UP) ml_sel = ml_sel ? ml_sel - 1 : ML_N - 1;
    else if (pressed & J_DOWN) ml_sel = ml_sel == ML_N - 1 ? 0 : ml_sel + 1;
    if (ml_sel != old) ml_dirty |= ML_DIRTY_BITS;
    if ((pressed & (J_SELECT | J_LEFT | J_RIGHT)) && hard_game(ml_game[ml_sel])) {   // (inert on the other games)
        ml_dirty ^= ML_HARD;
        ml_dirty |= ML_DIRTY_BITS;
        for (k = 0; k < ML_N; k++) {            // the medal column of the games that have a HARD best
            g = ml_game[k];
            if (!hard_game(g) || !unlocked(g)) continue;
            build(k);
            vq_add(0, ML_ROW(k), 0, ML_ROW_LIST + k, 20);
        }
    }
    if (pressed & (J_A | J_START)) {
        g = ml_game[ml_sel];
        if (unlocked(g)) { mg_enter(g, hard_for(g) ? MG_PRACTICE | MG_HARD : MG_PRACTICE); return 1; }
    } else if (pressed & J_B) {
        title_back = TM_BONUS; title_back_sel = 1;   // the BONUS submenu, the cursor on MINI GAMES
        title_enter();
        return 1;
    }
    for (k = ML_N, n = 0; k <= ML_HEAD_K && n < ML_ROWS_PER_FRAME; k++) {
        if (!(ml_dirty & (1 << (k - ML_N)))) continue;
        ml_dirty &= ~(1 << (k - ML_N));
        build(k);
        vq_add(0, ML_ROW(k), 0, screen_row(k), 20);
        n++;
    }
    cursor();
    return 0;
}
