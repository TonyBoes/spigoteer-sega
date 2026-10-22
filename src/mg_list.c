// The title's BONUS > MINI GAMES (Practice, docs/minigames_bosses.md 2.3; owner 2026-10-11: BONUS's second item): the mini-games that are built, each playable
// once STORY or ARCADE has reached it (save.c's Practice block at SRAM 0x40), and the wood-wall look the full-screen lists share (list_frame below).
//
// Screen, in the one-line style of src/oneline.h (owner Q38-Q45; light HUD glyphs and the story font's punctuation on the wall):
//   row 0 "MINI GAMES" and the mode word at column 13   row 3 the selection line "< ORDER UP >" in the panel's band (rows 2-4)
//   rows 6-13, columns 1-10: the illustration frame (80 x 64 px)   right of it, from column 12: row 7 the counter "4 / 14", row 9 the best medal's icon, row 11 its
//   word (GOLD / SILVER / BRONZE / NO MEDAL), a blank row between   row 15 a panel line   row 16 "(A) PLAY (B) BACK"
// No instructions text: the HOW TO PLAY cards and the pause menu cover the controls.
// LEFT / RIGHT select the previous / next game (wrapping, hold-to-repeat). UP / DOWN jump between the two groups, the venues' games and the bonus rounds (DOWN
// to the first of the next group, UP to the first of this group, then of the one before). SELECT cycles the mode EASY / NORMAL / HARD (it applies to every game
// in the list and to the next one played; kept in ml_mode, so it outlasts a game and the title): the header names it, the medal shown is the selected game's
// best in that mode (save.c keeps a medal per game per mode: mg_best's bits 0-1 NORMAL, 2-3 HARD, 4-5 EASY, and the bonus rounds' "MD" block). A or START plays
// the selected game in MG_PRACTICE | the mode's bit (mg.h; score from 0; its result offers "A RETRY B MENU", and B comes back here: src/mg.c); a locked one
// does nothing. B goes back to the title's BONUS submenu with the cursor on MINI GAMES.
// A game not reached yet lists as "? ? ?" with LOCKED in place of the medal and no A on the hint row.
// The list: every built game, the ten venues' mini-games in chapter order and then the three old bonus rounds (CAN SHAKE-UP, PERFECT POUR, TIP SHOWER: owner
// 2026-10-14; ARCADE and CLASSIC play them, here they play in the framework, src/bonus.c bonus_practice). The DEBUG_MENU build (`make`) lists them all
// unlocked, the stub GREEN LIGHT included, so the owner can test; `make release` lists the thirteen (the stub is not in it) and applies the unlock rule: a
// venue's game once STORY or ARCADE reached it, a bonus round once ARCADE or CLASSIC played it (save.c "MGB1").
//
// THE ILLUSTRATION. Until the owner's art arrives (after Saturday) the frame is empty. It is the 10 x 8 tiles of ML_ART_*: the one-tile border (OL_T_BOX) and
// the 8 x 6 tile interior (a 64 x 48 px picture; art that draws its own border takes the full 80 x 64 px). The art is one 80 x 64 px indexed PNG a game in
// assets/art/practice/<game>.png (<game> in the order of ml_game: quickdraw, shirtcannon, logroll, orderup, marshmallows, batterysort, milkrun, taikopour,
// monkeybusiness, asteroids, shakeup, perfectpour, tipshower), 4 colours (one CGB palette; the DMG shades by index), at most 80 unique tiles (aim 56): see
// assets/art/practice/README.md. The screen's side of it is fixed: the frame's cells (rows 6-13, columns 1-10), BG tile ids ML_ART_T..255 and a CGB palette of
// the art's own are reserved and drawn by nothing else. What is still to write when the first picture exists: a generator for build/practice_art.h (tiles,
// tilemap, colours per game) and the stream that puts the selected game's tiles into VRAM a few a frame (boss.c ld_step does it for the bosses' tiles), which
// is code for that day: there is nothing to stream before it, and a loader nothing exercises would be untested code.
//
// LCD off to enter; afterwards the rows go through the VBlank queue from WRAM buffers (story_scratch: no cut-scene and no mini-game runs while this screen
// shows; mg_enter rewrites it).
#pragma bank 255
#include <gb/gb.h>
#include <stdint.h>

#include "game.h"
#include "music.h"
#include "story.h"
#include "mg.h"
#include "oneline.h"
#include "list_skin.h"          // static const uint8_t list_skin_tiles[]: the wood-wall look's seam, header edge and medal icons (assets/art/list_skin.txt)
#include <gb/cgb.h>
#include "palettes.h"

#define RGB15(r, g, b) ((uint16_t)((r) | ((g) << 5) | ((b) << 10)))

extern uint8_t overlay_on, joy;

// chapter order (docs/story.md: saloon, stadium, lodge, bistro, igloo, robot factory, Chrome Cow, teahouse, zoo, space lounge), then the bonus rounds
#ifdef DEBUG_MENU
#define ML_N            14
static const uint8_t ml_game[ML_N] = { MG_QUICKDRAW, MG_TSHIRT, MG_LOGROLL, MG_ORDERUP, MG_MARSHMALLOW, MG_BATTERY, MG_MILKRUN, MG_TAIKO, MG_MONKEY, MG_ASTEROID,
                                       MG_SHAKEUP, MG_FILLLINE, MG_TIPS, MG_STUB };
#else
#define ML_N            13
static const uint8_t ml_game[ML_N] = { MG_QUICKDRAW, MG_TSHIRT, MG_LOGROLL, MG_ORDERUP, MG_MARSHMALLOW, MG_BATTERY, MG_MILKRUN, MG_TAIKO, MG_MONKEY, MG_ASTEROID,
                                       MG_SHAKEUP, MG_FILLLINE, MG_TIPS };
#endif
#define ML_GROUP        10      // the first bonus round's place in the list: UP / DOWN jump between 0 and this

// The screen's rows: row buffer k and the screen row it is drawn on
#define ML_K_NAME       0
#define ML_K_ART        1       // 1-8: the illustration frame's rows (screen rows 6-13), with the counter, the medal and its word right of it
#define ML_K_HINT       9
#define ML_K_HEAD       10
#define ML_ROWS         11
#define ML_ART_ROW      6
#define ML_ART_H        8       // tile rows of the frame
#define ML_ART_COL      1
#define ML_ART_W        10      // tile columns of the frame
#define ML_ART_T        176     // the illustration's tile ids (80) are 176-255 (nothing else of this screen uses them)
#define ML_COL_RIGHT    12      // the counter, the medal and its word
#define ML_COL_MODE     13      // the header's mode word ("MINI GAMES" is columns 1-10)
#define ML_ROW(k)       (story_scratch + (uint8_t)(k) * 20)
#define ml_d            (*(uint16_t *)(story_scratch + ML_ROWS * 20))   // bit k: row buffer k to redraw and send
typedef char ml_scratch_fits[(ML_ROWS * 20 + 2 <= STORY_SCRATCH && ML_ART_W * ML_ART_H == 80 && ML_ART_T + 80 == 256) ? 1 : -1];

uint8_t ml_sel;                 // the selected game (its place in the list)
uint8_t ml_n;                   // games listed (tests)
static uint8_t ml_mode;         // the mode (mg.h MG_D_*), kept across a game and the title

static const char locked_name[] = "? ? ?";
static const char *const medal_name[4] = { "NO MEDAL", "BRONZE", "SILVER", "GOLD" };

static const char *game_name(uint8_t g) {
    if (g == MG_QUICKDRAW) return "QUICK DRAW";
    if (g == MG_ORDERUP) return "ORDER UP";      // (no '!': the list has no tile for it)
    if (g == MG_BATTERY) return "BATTERY SORT";
    if (g == MG_MILKRUN) return "MILK RUN";
    if (g == MG_LOGROLL) return "LOG ROLL";
    if (g == MG_ASTEROID) return "ASTEROIDS";
    if (g == MG_TAIKO) return "TAIKO POUR";
    if (g == MG_MARSHMALLOW) return "MARSHMALLOWS";
    if (g == MG_MONKEY) return "MONKEY BUSINESS";
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

static uint8_t best(uint8_t g) {                  // g's best medal in the mode shown
    if (is_bonus(g)) return bonus_best(g - MG_SHAKEUP, ml_mode);
    return g < MG_PLANNED ? (mg_best[g] >> (ml_mode * 2)) & 3 : MEDAL_NONE;
}

static void build(uint8_t k) {
    uint8_t *r = ML_ROW(k), g = ml_game[ml_sel], ok = unlocked(g), br, m;
    char buf[8];
    ol_blank(r);
    switch (k) {
    case ML_K_NAME: ol_arrows(r); ol_put(r, 255, ok ? game_name(g) : locked_name); return;
    case ML_K_HINT: ol_hint(r, ok ? OL_A_PLAY : OL_A_NONE); return;
    case ML_K_HEAD: ol_put(r, 1, "MINI GAMES"); ol_put(r, ML_COL_MODE, diff_name[ml_mode]); return;
    }
    br = k - ML_K_ART;                          // a row of the frame (0-7), and what stands right of it
    r[ML_ART_COL] = br == 0 ? OL_T_BOX : br == ML_ART_H - 1 ? OL_T_BOX + 5 : OL_T_BOX + 3;
    r[ML_ART_COL + ML_ART_W - 1] = br == 0 ? OL_T_BOX + 2 : br == ML_ART_H - 1 ? OL_T_BOX + 7 : OL_T_BOX + 4;
    if (br == 0 || br == ML_ART_H - 1)
        for (m = 1; m < ML_ART_W - 1; m++) r[ML_ART_COL + m] = br == 0 ? OL_T_BOX + 1 : OL_T_BOX + 6;
    if (br == 1) { ol_counter(buf, ml_sel + 1, ML_N); ol_put(r, ML_COL_RIGHT, buf); }
    if (br == 3 && ok && best(g)) r[ML_COL_RIGHT] = SKIN_TILE_MEDAL + best(g);     // (the icon: ids SKIN_TILE_MEDAL + MEDAL_BRONZE .. GOLD)
    if (br == 5) ol_put(r, ML_COL_RIGHT, ok ? medal_name[best(g)] : "LOCKED");
}

static uint8_t screen_row(uint8_t k) {
    switch (k) {
    case ML_K_NAME: return OL_ROW_BAND;
    case ML_K_HINT: return OL_ROW_HINT;
    case ML_K_HEAD: return 0;
    }
    return ML_ART_ROW + (k - ML_K_ART);
}

// The wood-wall look of the full-screen lists (owner 2026-10-17: v1 of the tavern mock-ups without the shelves and the bottles). LCD off: loads the tiles over the
// stage ids and the CGB palettes 2-7, then all 18 rows: row 0 the header's text row (the caller writes its text over it), row 1 the band's edge (SKIN_TILE_EDGE),
// the wall with a board seam in the blank rows (`seams`: the odd rows 3.. above the panel, the seam shifting two tiles every other row), the panel's top line on
// `sep`, its info rows, its bottom line on 17. CGB: the header on a gold band with dark text (the text row's tiles have the letters on tile rows 1-7: with the
// edge row's first gold pixel row the text has 1 px of band above and below), the wall dark wood, the panel a darker reddish band. DMG: the wall stays the
// darkest shade (the letters' tiles have colour 3 for the ground), the edge row is two light lines under the header.
static const uint16_t skin_pal[6][4] = {
    { RGB15(31, 29, 22), RGB15(14, 9, 4), RGB15(3, 1, 1), RGB15(7, 3, 2) },       // SKIN_PAL_WALL: cream text, -, the seams' gap, the wall
    { RGB15(31, 25, 6), RGB15(26, 28, 30), RGB15(22, 12, 5), RGB15(7, 3, 2) },    // SKIN_PAL_MEDAL: gold, silver, bronze, the wall
    { RGB15(31, 23, 6), RGB15(24, 17, 4), RGB15(18, 12, 3), RGB15(11, 4, 3) },    // SKIN_PAL_BTN: the buttons' golds on the panel
    { RGB15(5, 2, 1), RGB15(5, 2, 1), RGB15(5, 2, 1), RGB15(30, 24, 10) },        // SKIN_PAL_HEAD: dark text on the gold band
    { RGB15(31, 29, 22), RGB15(24, 18, 8), RGB15(15, 9, 4), RGB15(11, 4, 3) },    // SKIN_PAL_FOOT: cream text, the panel's lines, the panel
    { RGB15(30, 24, 10), RGB15(15, 9, 2), RGB15(0, 0, 0), RGB15(7, 3, 2) },       // SKIN_PAL_EDGE: the band's last gold row, its shadow, the wall
};

void list_skin_load(void) BANKED {            // the tiles and palettes alone (LCD off; the debug menu's window map uses them too, src/debug.c)
    set_bkg_data(0, 4, list_skin_tiles);
    if (is_cgb) set_bkg_palette(SKIN_PAL_WALL, 6, (uint16_t *)skin_pal);
}

void list_frame(uint8_t sep) BANKED {
    uint8_t y, x;
    list_skin_load();
    music_pump();
    for (y = 0; y < 18; y++) {
        for (x = 0; x < 20; x++)
            row_buf[x] = y == 1 ? SKIN_TILE_EDGE : y == sep ? TILE_PANEL_TOP : y == 17 ? TILE_PANEL_BOT
                       : TILE_HUD_BLANK;
        set_bkg_tiles(0, y, 20, 1, row_buf);
        if (is_cgb) {
            for (x = 0; x < 20; x++) row_buf[x] = y == 0 ? SKIN_PAL_HEAD : y == 1 ? SKIN_PAL_EDGE : y >= sep ? SKIN_PAL_FOOT : SKIN_PAL_WALL;
            VBK_REG = VBK_BANK_1;
            set_bkg_tiles(0, y, 20, 1, row_buf);
            VBK_REG = VBK_BANK_0;
        }
        if (!(y & 1)) music_pump();
    }
}


void mg_list_enter(void) BANKED {
    uint8_t y;
    TRANS_MENU();                               // (src/trans.c: the quick white fade, from the title's BONUS and back from a game)
    DISPLAY_OFF;
    music_pump();                               // (the tick this pass is due: the rebuild runs several frames)
    overlay_on = 0; HIDE_WIN; vq_reset(); hud_dirty = 0; vram_pending = 0;
    hide_all_sprites();
    story_on = 0;                               // (Practice is never a story)
    music_play(TUNE_TITLE);                     // (left alone when it already plays: from the title; after a game its patterns are
    music_load_now();                           // copied back now, and the pumps below tick it through the rebuild)
    music_pump();
    story_font_load();                          // the punctuation (over the title's lettering: title_enter reloads it)
    ol_load();
    music_pump();
    if (ml_sel >= ML_N) ml_sel = 0;
    ml_n = ML_N; ml_d = 0;
    list_frame(OL_SEP);                         // (the wood wall: tiles, palettes, the header band, the panel)
    ol_band(SKIN_PAL_BTN);
    for (y = 0; y < ML_ROWS; y++) {
        build(y);
        set_bkg_tiles(0, screen_row(y), 20, 1, ML_ROW(y));
        if (!(y & 3)) music_pump();
    }
    if (is_cgb) {                               // the medal icon's palette
        row_buf[0] = SKIN_PAL_MEDAL;
        VBK_REG = VBK_BANK_1;
        set_bkg_tiles(ML_COL_RIGHT, screen_row(ML_K_ART + 3), 1, 1, row_buf);
        VBK_REG = VBK_BANK_0;
    }
    game_state = GS_MGLIST;
    DISPLAY_ON;
}

// One frame. 1: the screen changed (a game started, or B went back to the title).
uint8_t mg_list_update(uint8_t pressed) BANKED {
    uint8_t old = ml_sel, k, n, key = ol_key(pressed, joy), g;
    if (key == J_LEFT) ml_sel = ol_wrap(ml_sel, ML_N, -1);
    else if (key == J_RIGHT) ml_sel = ol_wrap(ml_sel, ML_N, 1);
    else if (key == J_DOWN) ml_sel = ml_sel >= ML_GROUP ? 0 : ML_GROUP;                       // the next group's first game
    else if (key == J_UP) ml_sel = ml_sel > ML_GROUP ? ML_GROUP : ml_sel > 0 ? 0 : ML_GROUP;  // this group's first game, then the one before
    if (ol_tick()) ml_d |= 1 << ML_K_NAME;
    if (ml_sel != old) {
        ml_d |= (1 << ML_K_NAME) | (1 << (ML_K_ART + 1)) | (1 << (ML_K_ART + 3)) | (1 << (ML_K_ART + 5));   // name, counter, medal icon and word
        g = ml_game[old]; n = ml_game[ml_sel];
        if (unlocked(g) != unlocked(n)) ml_d |= 1 << ML_K_HINT;
    }
    if (pressed & J_SELECT) {                   // the mode: EASY, NORMAL, HARD, round
        k = diff_ui[ml_mode];
        k = k == MG_DIFFS - 1 ? 0 : k + 1;
        ml_mode = ui_diff[k];
        ml_d |= (1 << ML_K_HEAD) | (1 << (ML_K_ART + 3)) | (1 << (ML_K_ART + 5));
    }
    if (pressed & (J_A | J_START)) {
        g = ml_game[ml_sel];
        if (unlocked(g)) { mg_enter(g, MG_PRACTICE | (ml_mode << 1)); return 1; }
    } else if (pressed & J_B) {
        title_back = TM_BONUS; title_back_sel = 2;   // the BONUS submenu, the cursor on MINI GAMES
        title_enter();
        return 1;
    }
    for (k = 0, n = 0; ml_d && k < ML_ROWS && n < 2; k++) {   // two rows a frame (a row's build is ~15k cycles)
        if (!(ml_d & ((uint16_t)1 << k))) continue;
        ml_d &= ~((uint16_t)1 << k);
        build(k);
        vq_add(0, ML_ROW(k), 0, screen_row(k), 20);
        n++;
    }
    return 0;
}
