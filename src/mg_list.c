// The title's BONUS > MINI GAMES (Practice, docs/minigames_bosses.md 2.3; owner 2026-10-11: BONUS's second item): the
// mini-games that are built, each playable once STORY or ARCADE has reached it (save.c's Practice block at SRAM 0x40).
//
// Screen (the soundtrack player's style: light HUD glyphs and the story font's punctuation on the dark band, HUD
// palette): row 0 "MINI GAMES", row 1 a panel line; rows 2.. the games, one a line: the name at columns 1-12, the best
// medal's word at columns 14-19 (muted on CGB); the games stand on every other row; the mug cursor (OAM 0) left of the name; row 14 a panel line, rows 15-16 the selected
// game: its best medal, the keys (A, B and D-pad buttons); row 17 a panel line. A game not reached yet lists as "? ? ?"
// (as SOUNDTRACK's locked tunes) and its details read "? ? ?", LOCKED, REACH IT IN STORY, OR ARCADE.
// LEFT / RIGHT (or SELECT, forward) cycle the difficulty EASY / NORMAL / HARD (owner 2026-10-15; in bits 6-7 of ml_dirty, so it outlasts a
// game and the title): it applies to every game in the list and to the next one played. The header's right side names it; the list's medal
// column and the "<MODE> BEST" info line show the selected mode's best medal (save.c keeps a medal per game per mode: mg_best's bits 0-1
// NORMAL, 2-3 HARD, 4-5 EASY, and the bonus rounds' "MD" block). The last info line says the keys. Playing starts with
// MG_PRACTICE | the mode's bit (mg.h); every game plays the same in the three for now (owner: the playtest notes come later).
// Up / Down select (wrapping); A or START plays the selected game in MG_PRACTICE (score from 0; its result offers
// "A RETRY B MENU", and B comes back here: src/mg.c); a locked one does nothing. B goes back to the title's BONUS
// submenu with the cursor on MINI GAMES.
// The list: every built game, the ten venues' mini-games in chapter order and then the three old bonus rounds (CAN SHAKE-UP, PERFECT POUR,
// TIP SHOWER: owner 2026-10-14; ARCADE and CLASSIC play them, here they play in the framework, src/bonus.c bonus_practice). The DEBUG_MENU build
// (`make`) lists them all unlocked, the stub GREEN LIGHT included, so the owner can test; `make release` lists the thirteen (the stub is not in it)
// and applies the unlock rule: a venue's game once STORY or ARCADE reached it, a bonus round once ARCADE or CLASSIC played it (save.c "MGB1").
// The list shows ML_VIS lines and scrolls: Up / Down move the cursor, the lines slide when it leaves the window (the cursor wraps from the last
// to the first). The panel under it is always the same: a blank row, the separator, two info lines (the best medal, the keys).
// The scroll arrows: see ML_ARROW_UP below.
// LCD off to enter; afterwards the rows go through the VBlank queue from WRAM buffers (story_scratch: no cut-scene and
// no mini-game runs while this screen shows; mg_enter rewrites it).
#pragma bank 255
#include <gb/gb.h>
#include <stdint.h>

#include "game.h"
#include "music.h"
#include "story.h"
#include "mg.h"
#include "list_arrows.h"        // static const uint8_t list_arrow_tiles[]: the up and down arrow (assets/art/list_arrows.txt)
#include "list_keys.h"          // static const uint8_t list_key_tiles[]: the keys line's A, B and right buttons (assets/art/list_keys.txt)
#include <gb/cgb.h>
#include "palettes.h"

extern uint8_t overlay_on;

#define ML_ROW_HEAD     0
#define ML_ROW_LIST     2
#define ML_COL_NAME     1
#define ML_COL_MEDAL   14       // (BATTERY SORT is 12 letters: columns 1-12)
#define ML_ROWS_PER_FRAME 4     // 20-byte rows queued a frame (as mg_say)
// chapter order (docs/story.md: saloon, stadium, lodge, bistro, igloo, robot factory, Chrome Cow, teahouse, zoo, space lounge)
#ifdef DEBUG_MENU
#define ML_N            14
static const uint8_t ml_game[ML_N] = { MG_QUICKDRAW, MG_TSHIRT, MG_LOGROLL, MG_ORDERUP, MG_MARSHMALLOW, MG_BATTERY, MG_MILKRUN, MG_TAIKO, MG_MONKEY, MG_ASTEROID,
                                       MG_SHAKEUP, MG_FILLLINE, MG_TIPS, MG_STUB };
#else
#define ML_N            13
static const uint8_t ml_game[ML_N] = { MG_QUICKDRAW, MG_TSHIRT, MG_LOGROLL, MG_ORDERUP, MG_MARSHMALLOW, MG_BATTERY, MG_MILKRUN, MG_TAIKO, MG_MONKEY, MG_ASTEROID,
                                       MG_SHAKEUP, MG_FILLLINE, MG_TIPS };
#endif
// The panel sits one blank row under the last visible line (the Boss Rush list's fix, cfc9b38): list rows 2..ML_VIS+1, a blank row, the
// separator, the info lines up to row 16, the panel's bottom on 17. The window shows ML_VIS of the ML_N games (ml_top is the first); the cursor's
// line shows the game's name, so the info lines are the best medal and the keys.
// Owner 2026-10-15: the venue line is gone (two info lines) and the games stand on every other row, a blank row between them (the capitals
// touched): ML_VIS games on rows 2, 4 .. 12, the blank row 13, the separator 14, the info lines 15-16.
#define ML_VIS         6
#define ML_ROW_BOX     (ML_ROW_LIST + 2 * ML_VIS)
#define ML_INFO_LINES  (16 - ML_ROW_BOX)
typedef char ml_fits[(ML_INFO_LINES == 2 && ML_N >= ML_VIS && ML_N - ML_VIS < 16) ? 1 : -1];
#define ML_HEAD_K     (ML_VIS + ML_INFO_LINES)        // the header's buffer / dirty bit (after the info lines)
#define ML_DIFF_BITS  0xC0                            // ml_dirty's bits 6-7: the difficulty (mg.h MG_D_*; kept; the dirty bits are 0..ML_INFO_LINES)
#define ml_diff       (ml_dirty >> 6)
#define ML_DIRTY_BITS ((1 << (ML_INFO_LINES + 1)) - 1)
#define ML_COL_MODE   13                              // the header's mode word ("MINI GAMES" is columns 1-10)
#define ML_ROW(k)     (story_scratch + (uint8_t)(k) * 20)   // row buffer k: window line k < ML_VIS, else info line k - ML_VIS, the header last
// The window's state lives in story_scratch after the row buffers (no WRAM of its own): the first line shown, and how many of the window's
// lines the scroll has sent to the screen so far (ML_VIS: all; the list is redrawn ML_ROWS_PER_FRAME lines a frame)
#define ml_top        (story_scratch[(ML_HEAD_K + 1) * 20])
#define ml_sent       (story_scratch[(ML_HEAD_K + 1) * 20 + 1])
#define ml_t          (story_scratch[(ML_HEAD_K + 1) * 20 + 2])   // frames on this screen (the arrows' bob)
#define ml_attr       (story_scratch + (ML_HEAD_K + 1) * 20 + 4)  // the keys line's CGB attribute row (20 bytes: the buttons' palette)
typedef char ml_scratch_fits[(ML_HEAD_K + 1) * 20 + 24 <= STORY_SCRATCH ? 1 : -1];
#define ML_PAL_MEDAL  (BGPAL_PATRON + 1)    // CGB: the medal words' muted palette, columns 14-19 of the list lines (palette 3: the title sets it again)
#define ML_PAL_BTN    (BGPAL_PATRON + 2)    // CGB: the keys line's buttons (palette 4)
// Scroll arrows (owner 2026-10-14): two 8x16 OBJ sprites (OAM 1 and 2) at the right edge, column 19: the up arrow on the separator line under the header
// when games are listed above the window (ml_top > 0), the down arrow on the blank row under the window when games are listed below it. They bob
// one pixel (the up one up, the down one down) every ML_BOB_FRAMES frames. Tiles at the dancer's OBJ ids (the title and the games reload them).
#define ML_ARROW_UP   OBJ_DANCER
#define ML_ARROW_DOWN (OBJ_DANCER + 2)      // (8x16 entries: the up arrow in the upper half of OBJ_DANCER, the down arrow in the lower half of the next pair)
typedef char ml_arrow_even[(OBJ_DANCER & 1) ? -1 : 1];
#define ML_ARROW_X    (19 * 8 + 8)
#define ML_BOB_FRAMES 16

uint8_t ml_sel;                 // the selected line
uint8_t ml_n;                   // lines listed (tests)
static uint8_t ml_dirty;        // bit k: the info line k (row buffer ML_N + k) to redraw; bit ML_INFO_LINES the header; bits 6-7 the difficulty

static const char locked_name[] = "? ? ?";
static const char *const locked_info[2] = { "REACH IT IN STORY", "OR ARCADE" };
static const char *const locked_bonus[2] = { "PLAY IT IN ARCADE", "OR CLASSIC" };   // a bonus round: played there once (the pour and the tips: ARCADE only)
// The keys line's buttons: the story font's three frame tiles (TL, T, TR: this screen has no frame) hold A, B and the D-pad's right press.
#define KEY_A  ST_FRAME_TL
#define KEY_B  (ST_FRAME_TL + 1)
#define KEY_R  (ST_FRAME_TL + 2)

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
    if (g == MG_SHAKEUP) return "CAN SHAKE-UP";
    if (g == MG_FILLLINE) return "PERFECT POUR";
    if (g == MG_TIPS) return "TIP SHOWER";
#ifdef DEBUG_MENU
    return "GREEN LIGHT";
#else
    return "";
#endif
}

static uint8_t ml_glyph(char c) {
    switch (c) {
    case '.': return ST_GLYPH_PERIOD; case '?': return ST_GLYPH_QUEST; case '-': return ST_GLYPH_HYPHEN;
    case '@': return KEY_A; case '$': return KEY_B; case '>': return KEY_R;   // (the buttons: frame tiles, loaded over in mg_list_enter)
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

static uint8_t is_bonus(uint8_t g) { return g >= MG_SHAKEUP && g < MG_SHAKEUP + MG_BONUS_N; }

static uint8_t unlocked(uint8_t g) {
#ifdef DEBUG_MENU
    (void)g;
    return 1;
#else
    if (is_bonus(g)) return bonus_info(g - MG_SHAKEUP) & 1;     // (played in ARCADE or CLASSIC: save.c's own block)
    return g < MG_PLANNED && ((mg_unlocked >> g) & 1);
#endif
}

static const char *const diff_name[MG_DIFFS] = { "NORMAL", "HARD", "EASY" };   // (by MG_D_*)
static const uint8_t diff_ui[MG_DIFFS] = { 1, 2, 0 };      // MG_D_* -> its place in the cycle EASY, NORMAL, HARD
static const uint8_t ui_diff[MG_DIFFS] = { MG_D_EASY, MG_D_NORMAL, MG_D_HARD };

static uint8_t best(uint8_t g) {                  // g's best medal in the difficulty shown
    if (is_bonus(g)) return bonus_best(g - MG_SHAKEUP, ml_diff);
    return g < MG_PLANNED ? (mg_best[g] >> (ml_diff * 2)) & 3 : MEDAL_NONE;
}

static char *cat(char *d, const char *s) {        // s after d's end; the new end
    while (*s) *d++ = *s++;
    *d = 0;
    return d;
}

static void build(uint8_t k) {
    uint8_t g, *r = ML_ROW(k);
    char *w, buf[24];
    blank(r);
    if (k == ML_HEAD_K) {                       // the header: the title and the mode in force for the selected game
        put(r, 1, "MINI GAMES");
        put(r, ML_COL_MODE, diff_name[ml_diff]);
        return;
    }
    if (k >= ML_VIS) {                          // an info line of the selected game
        k -= ML_VIS;
        g = ml_game[ml_sel];
        if (!unlocked(g)) { put(r, 255, (is_bonus(g) ? locked_bonus : locked_info)[k]); return; }
        switch (k) {
        case 0:                                 // "HARD BEST GOLD" centred, or "HARD NO MEDAL YET": the medal of the mode in force
            w = cat(buf, diff_name[ml_diff]);
            w = cat(w, best(g) ? " BEST " : " NO MEDAL YET");
            cat(w, medal_name[best(g)]);
            put(r, 255, buf);
            break;
        default: put(r, 255, "@ GO $ BACK > MODE");   // (@ the A button, $ the B button, > D-pad right)
        }
        return;
    }
    g = ml_game[ml_top + k];
    if (!unlocked(g)) { put(r, ML_COL_NAME, locked_name); return; }
    put(r, ML_COL_NAME, game_name(g));
    put(r, ML_COL_MEDAL, medal_name[best(g)]);
}

static uint8_t screen_row(uint8_t k) {
    return k == ML_HEAD_K ? ML_ROW_HEAD : k < ML_VIS ? ML_ROW_LIST + 2 * k : ML_ROW_BOX + 1 + k - ML_VIS;
}

static void cursor(void) {
    OAM_item_t *o = shadow_OAM;
    o->y = (ML_ROW_LIST + 2 * (ml_sel - ml_top)) * 8 - 7 + 16;  // the mug stands on the line (as the title's cursor)
    o->x = 8;
    o->tile = OBJ_MUG; o->prop = is_cgb ? OBJPAL_MUG_FULL : 0;
}

static void keys_attr(void) {                   // the keys row's attributes: the buttons' palette under the three button tiles, the HUD's elsewhere
    uint8_t x, t, *r = ML_ROW(ML_HEAD_K - 1);
    for (x = 0; x < 20; x++) { t = r[x]; ml_attr[x] = t >= KEY_A && t <= KEY_R ? ML_PAL_BTN : BGPAL_HUD; }
}

// The scroll arrows, shared with the boss rush's list (src/rush.c): the sprite tiles, and OAM 1 / 2 (up shown, down shown, frame count for the bob)
void list_arrows_load(void) BANKED { set_sprite_data(ML_ARROW_UP, 4, list_arrow_tiles); }

void list_arrows_show(uint8_t up, uint8_t down, uint8_t t) BANKED {
    OAM_item_t *u = shadow_OAM + 1, *d = shadow_OAM + 2;
    uint8_t p = (t / ML_BOB_FRAMES) & 1;
    u->y = (uint8_t)(up ? (ML_ROW_HEAD + 1) * 8 + 16 - p : 0);
    d->y = (uint8_t)(down ? (ML_ROW_BOX - 1) * 8 + 8 + p : 0);
    u->x = ML_ARROW_X; d->x = ML_ARROW_X;
    u->tile = ML_ARROW_UP; d->tile = ML_ARROW_DOWN;
    u->prop = d->prop = is_cgb ? OBJPAL_MUG_FULL : 0;
}

static void arrows(void) { list_arrows_show(ml_top != 0, ml_top + ML_VIS < ML_N, ml_t); }

void mg_list_enter(void) BANKED {
    uint8_t y, x;
    DISPLAY_OFF;
    music_pump();                               // (the tick this pass is due: the rebuild runs several frames)
    overlay_on = 0; HIDE_WIN; vq_reset(); hud_dirty = 0; vram_pending = 0;
    hide_all_sprites();
    story_on = 0;                               // (Practice is never a story)
    music_play(TUNE_TITLE);                     // (left alone when it already plays: from the title; after a game its patterns are
    music_load_now();                           // copied back now, and the pumps below tick it through the rebuild)
    music_pump();
    mug_cursor_load();                          // (a game borrowed the mug's tiles and palettes)
    list_arrows_load();
    music_pump();
    story_font_load();                          // the punctuation (over the title's lettering: title_enter reloads it)
    set_bkg_data(KEY_A, 3, list_key_tiles);     // (the frame is not on this screen)
    music_pump();
    if (ml_sel >= ML_N) ml_sel = 0;
    ml_n = ML_N; ml_dirty &= ML_DIFF_BITS;
    ml_top = ml_sel >= ML_VIS ? ml_sel - ML_VIS + 1 : 0;   // (the window that shows the cursor's game, as it comes back from one)
    ml_sent = ML_VIS; ml_t = 0;
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
        palette_t p;                            // (the HUD palette's slots: 0 text, 3 the band)
        p[0] = (uint16_t)(20 | (16 << 5) | (10 << 10)); p[1] = p[0]; p[2] = p[0]; p[3] = (uint16_t)(3 | (2 << 5) | (8 << 10));
        set_bkg_palette(ML_PAL_MEDAL, 1, p);    // the medal words: a muted dusty gold under the menu text's cream
        p[0] = (uint16_t)(31 | (23 << 5) | (6 << 10)); p[1] = (uint16_t)(24 | (17 << 5) | (4 << 10)); p[2] = (uint16_t)(18 | (12 << 5) | (3 << 10));
        set_bkg_palette(ML_PAL_BTN, 1, p);      // the buttons: gold
        keys_attr();
        music_pump();
        VBK_REG = VBK_BANK_1;
        for (y = 0; y < 18; y++) {              // the HUD palette everywhere, the medal column's on the game rows, the buttons' on the keys row
            for (x = 0; x < 20; x++) row_buf[x] = y >= ML_ROW_LIST && y < ML_ROW_BOX - 1 && !(y & 1) && x >= ML_COL_MEDAL ? ML_PAL_MEDAL : BGPAL_HUD;
            set_bkg_tiles(0, y, 20, 1, y == screen_row(ML_HEAD_K - 1) ? ml_attr : row_buf);
            if (!(y & 3)) music_pump();
        }
        VBK_REG = VBK_BANK_0;
    }
    cursor();
    arrows();
    game_state = GS_MGLIST;
    DISPLAY_ON;
}

// One frame. 1: the screen changed (a game started, or B went back to the title).
uint8_t mg_list_update(uint8_t pressed) BANKED {
    uint8_t old = ml_sel, k, n, g, top = ml_top;
    if (pressed & J_UP) ml_sel = ml_sel ? ml_sel - 1 : ML_N - 1;
    else if (pressed & J_DOWN) ml_sel = ml_sel == ML_N - 1 ? 0 : ml_sel + 1;
    if (ml_sel != old) {
        ml_dirty |= ML_DIRTY_BITS;
        if (ml_sel < top) top = ml_sel;                     // the cursor left the window: it slides one line (a wrap: to the other end)
        else if (ml_sel >= top + ML_VIS) top = ml_sel - ML_VIS + 1;
        if (top != ml_top) { ml_top = top; ml_sent = 0; }   // (the window's lines are rebuilt and sent a few a frame)
    }
    if (pressed & (J_SELECT | J_LEFT | J_RIGHT)) {   // the difficulty: EASY, NORMAL, HARD, round (LEFT back, RIGHT and SELECT forward), for every game
        k = diff_ui[ml_diff];
        if (pressed & J_LEFT) k = k ? k - 1 : MG_DIFFS - 1;
        else k = k == MG_DIFFS - 1 ? 0 : k + 1;
        ml_dirty = ML_DIRTY_BITS | (ui_diff[k] << 6);   // (the header and the info lines again)
        ml_sent = 0;                            // and the medal column: the window's lines, a few a frame
    }
    if (pressed & (J_A | J_START)) {
        g = ml_game[ml_sel];
        if (unlocked(g)) { mg_enter(g, MG_PRACTICE | (ml_diff << 1)); return 1; }
    } else if (pressed & J_B) {
        title_back = TM_BONUS; title_back_sel = 1;   // the BONUS submenu, the cursor on MINI GAMES
        title_enter();
        return 1;
    }
    for (n = 0; ml_sent < ML_VIS && n < ML_ROWS_PER_FRAME; n++, ml_sent++) {   // a scroll: the window's lines again
        build(ml_sent);
        vq_add(0, ML_ROW(ml_sent), 0, ML_ROW_LIST + 2 * ml_sent, 20);
    }
    for (k = ML_VIS; k <= ML_HEAD_K && n < ML_ROWS_PER_FRAME; k++) {
        if (!(ml_dirty & (1 << (k - ML_VIS)))) continue;
        ml_dirty &= ~(1 << (k - ML_VIS));
        build(k);
        vq_add(0, ML_ROW(k), 0, screen_row(k), 20);
        if (is_cgb && k == ML_HEAD_K - 1) { keys_attr(); vq_add(1, ml_attr, 0, screen_row(k), 20); }
        n++;
    }
    ml_t++;
    cursor();
    arrows();
    return 0;
}
