// The debug menu (owner 2026-10-16): a full-screen menu in the look of the other lists (header, panel lines, the lines on every other row,
// the mug cursor, an info line and the keys line with the A, B and D-pad buttons). It is in every build (release included) but LOCKED
// until the unlock is saved (save.c "DU": debug_unlocked); a -DDEBUG_UNLOCKED build is always unlocked. -DDEBUG_MENU alone is the playtest
// build `make` makes: every boss and mini-game listed (rush.c, mg_list.c), the menu itself locked like the release's (tests unlock it).
//
// OPENING (main.c update calls debug_gesture while SELECT is held): hold SELECT and tap START three times, each within DBG_WINDOW frames of the
// first tap (a slower third tap starts the count again). It works on the title, in play and in a level's pause (not in a mini-game's), only
// when unlocked; the three START taps are swallowed (they would pause the game or choose a menu line). The title's SELECT toggles the music
// as ever, on the press; when the gesture opens the menu that toggle is undone, so opening it never leaves the music changed. Also
// SETTINGS > DEBUG MENU on the title (a line that is there once unlocked: title.c).
// UNLOCKING: konami_step, below: the title's input runs it on every press (title.c); Up Up Down Down Left Right Left Right B A saves
// the unlock. THIS IS THE ONE PLACE TO CHANGE THE TRIGGER (the table, KONAMI_DONE = its length); ERASE DATA locks the menu again with the rest of the save.
//
// THE SCREEN is the window map over the whole screen (WY 0, LYC off: the pause card's way, src/mg_card.c), so the game or the title underneath
// is untouched and comes back as it was: B closes it. The sprites are cleared (oam_touched: the game redraws its own), the mug cursor is OAM 0.
// The three button tiles of the keys line go over the story font's frame tiles and come back (kept in the window map's rows 28-30, off screen,
// with LYC in row 31).
// Lines (the menu is mode-aware: it opens in the mode it was opened in, the MODE line switches):
//   MODE     LEVEL / STORY / ARCADE / CLASSIC (Left / Right)
//   LEVEL    "LEVEL nn", the old 10-level rotation = the test harness (MODE_LEVEL): Left / Right change nn (1..DEBUG_LEVELS, wrapping); A starts it from
//            scratch (start_new_game). Opened in its play, or on the title with the cursor on any item but STORY / CONTINUE / ARCADE / CLASSIC.
//            BARS: the bars' directions, CLASSIC's eight layouts (level_dirs: LLLL, RRRR, RRLL, LLRR, RLLR, LRRL, RLRL, LRLR, top bar first;
//            Left / Right on its line, or SELECT on any line), kept for every later level of the run (until the title)
//   STORY / ARCADE: CHAPTER c (1..10, wrapping) and STEP (PRE scene, the story's playable steps, POST scene; ARCADE has no scenes): A starts it with the
//            story's rules (story_debug_start, src/story.c: a fresh score, the venue's 3 lives, its goals; a POST scene goes on to the next
//            chapter as usual). Opened in story (ARCADE) play, or on the title with PLAY's cursor on STORY / CONTINUE (the saved chapter) / ARCADE.
//            Such a run writes nothing to SRAM (save.c save_lock, cleared by the title): no progress, no unlocks, so a playtest never unlocks what was not earned.
//   CLASSIC  "LEVEL nn" (1..CLASSIC_ROWS, wrapping): A starts a CLASSIC game there (3 lives, a fresh score, the table's directions); no BARS or BAR CHANGE.
//   BAR CHANGE (every mode but CLASSIC): SNAP (default: Up/Down snaps the bartender to the tap with a dust puff and a soft swish; CLASSIC always) or
//            KEEP (he keeps his x): level_dirs bit 7, KEEP_POS, the bit SETTINGS > BAR CHANGE (src/title.c) sets and saves; here it is for the session only.
// Up / Down move the cursor, Left / Right change the line's value, A or START starts, B closes (back to the title, or into the game).
#pragma bank 255
#include <gb/gb.h>
#include <gb/cgb.h>
#include <stdint.h>

#include "game.h"
#include "music.h"
#include "story.h"
#include "list_keys.h"          // static const uint8_t list_key_tiles[]: the keys line's A, B and right buttons (assets/art/list_keys.txt)

#define DEBUG_LEVELS       20
#define POS_POST          (STORY_STEPS + 1)    // positions: 0 PRE, 1..STORY_STEPS the steps, POS_POST
#define DBG_WINDOW         72                  // frames from the first START tap to the third
#define DBG_SAVE_ROW       28                  // the window map's off-screen rows: the saved tiles (28-30) and LYC (31)
#define SKIN_SAVE_ROW      18                  // rows 18-22: the wood wall's four tiles (src/mg_list.c list_skin_load); in the attribute map the six palettes' bytes
#define SKIN_SAVE_N         4
#define SKIN_PALS           6

extern uint8_t overlay_on, level, story_chapter, story_step, state_timer;
uint8_t debug_menu_open;
uint8_t debug_level;               // LEVEL's / CLASSIC's level
uint8_t debug_from_title;
uint8_t debug_sel;                 // open: the cursor's line. Before it: bit 0 the title's SELECT toggled the music, bits 1-2 the START taps so far
uint8_t debug_timer;               // the gesture's frames left
uint8_t debug_story;               // 1: the menu selects a story position, 2: an ARCADE one (0: a level)
uint8_t debug_chapter;             // its chapter (0..STORY_CHAPTERS-1)
uint8_t debug_pos;                 // its position (0 PRE, 1..STORY_STEPS step pos-1, POS_POST)
uint8_t debug_classic;             // 1: the menu is CLASSIC's (debug_level is its level, 1..CLASSIC_ROWS)
void story_debug_start(uint8_t ch, uint8_t pos, uint8_t arc) BANKED;   // src/story.c

// ---- the unlock's trigger ----------------------------------------------------------------------------------------------------
static const uint8_t konami[KONAMI_DONE] = { J_UP, J_UP, J_DOWN, J_DOWN, J_LEFT, J_RIGHT, J_LEFT, J_RIGHT, J_B, J_A };

// The code's progress i (0..KONAMI_DONE - 1) after a frame whose new presses are `pressed`; KONAMI_DONE when it is complete.
uint8_t konami_step(uint8_t i, uint8_t pressed) BANKED {
    uint8_t p = pressed & (J_UP | J_DOWN | J_LEFT | J_RIGHT | J_A | J_B);
    if (!pressed) return i;
    if (p == konami[i]) return ++i;
    return p == konami[0];                       // (a wrong key starts over, or is the first Up)
}

// ---- the opening gesture ------------------------------------------------------------------------------------------------------
void debug_open(void) BANKED;

// main.c update, while SELECT is held: `pressed` back with the START taps taken out when they belong to the gesture
uint8_t debug_gesture(uint8_t pressed) BANKED {
    uint8_t n = debug_sel >> 1;
    if (game_state != GS_TITLE && game_state != GS_PLAYING && (game_state != GS_PAUSED || (state_timer & 0x80))) return pressed;   // (not in a mini-game's pause)
    if (pressed & J_SELECT) { debug_sel = game_state == GS_TITLE; debug_timer = 0; n = 0; }   // (a new hold: the music toggle to undo, no taps yet)
    if (debug_timer && !--debug_timer) n = 0;                // (too slow: the count starts again)
    if (pressed & J_START) {
        if (!debug_unlocked()) return pressed;
        pressed &= ~J_START;
        if (!n) debug_timer = DBG_WINDOW;
        if (++n == 3) {
            if (debug_sel & 1) title_music_toggle();         // (the SELECT that began the hold toggled it)
            debug_open();
            return pressed;
        }
    }
    debug_sel = (debug_sel & 1) | (n << 1);
    return pressed;
}

// ---- the lines ----------------------------------------------------------------------------------------------------------------
enum { DL_MODE, DL_LEVEL, DL_CHAPTER, DL_STEP, DL_BARS, DL_CHANGE };
enum { DM_LEVEL, DM_STORY, DM_ARCADE, DM_CLASSIC };

static uint8_t dmode(void) { return debug_classic ? DM_CLASSIC : debug_story ? DM_STORY - 1 + debug_story : DM_LEVEL; }

// the kind of each line of the mode shown into k[]; the number of lines
static uint8_t lines(uint8_t *k) {
    uint8_t n = 0;
    k[n++] = DL_MODE;
    if (debug_classic) k[n++] = DL_LEVEL;
    else if (debug_story) { k[n++] = DL_CHAPTER; k[n++] = DL_STEP; k[n++] = DL_CHANGE; }
    else { k[n++] = DL_LEVEL; k[n++] = DL_BARS; k[n++] = DL_CHANGE; }
    return n;
}

static const char *const step_label[4] = { "OPEN", "HAPPY", "LAST", "" };   // a shift's index (STEP_INDEX)
static const char *const mode_name[4] = { "LEVEL", "STORY", "ARCADE", "CLASSIC" };
static const char *const info_text[4] = { "LEVEL TEST RUN", "NOTHING IS SAVED", "NOTHING IS SAVED", "CLASSIC 1983 RUN" };

// 1: position p of chapter ch can be started
static uint8_t pos_ok(uint8_t ch, uint8_t p) {
    if (p == 0 || p == POS_POST) return debug_story == 1;   // (ARCADE has no scenes)
    return !(story_step_get(ch, p - 1) & STEP_SKIP) || ((story_unskip >> (p - 1)) & 1);
}

// the next position from p in direction d (+1 / -1, wrapping) that can be started
static uint8_t pos_next(uint8_t ch, uint8_t p, int8_t d) {
    do p = d > 0 ? (p == POS_POST ? 0 : p + 1) : (p == 0 ? POS_POST : p - 1);
    while (!pos_ok(ch, p));
    return p;
}

// P3: the bars' directions the LEVEL mode steps through (bit b: bar b, the top one 0, is R)
#define DIR_LAYOUTS 8
static const uint8_t dir_layout[DIR_LAYOUTS] = { 0x0, 0xF, 0x3, 0xC, 0x9, 0x6, 0x5, 0xA };

// ---- drawing ------------------------------------------------------------------------------------------------------------------
#define KEY_A  ST_FRAME_TL      // the keys line's buttons: the story font's three frame tiles (as src/mg_list.c)
#define KEY_B  (ST_FRAME_TL + 1)
#define KEY_R  (ST_FRAME_TL + 2)
#define COL_LABEL  1
#define COL_VALUE  12
#define ROW_LINE0  2            // line i on row 2 + 2 * i (a blank row between: as the lists)
#define ROW_SEP    14
#define ROW_INFO   15
#define ROW_KEYS   16

static uint8_t glyph(char c) {
    switch (c) {
    case '@': return KEY_A; case '$': return KEY_B; case '>': return KEY_R;
    }
    return glyph_for(c);
}

static void blank(uint8_t *r) {
    uint8_t i;
    for (i = 0; i < 20; i++) r[i] = TILE_HUD_BLANK;
}

static void put(uint8_t *r, uint8_t x, const char *s) {   // a string at column x (255: centred)
    uint8_t n = 0;
    while (s[n]) n++;
    if (x == 255) x = (20 - n) >> 1;
    while (*s) r[x++] = glyph(*s++);
}

static void put2(uint8_t *r, uint8_t x, uint8_t v) {      // two digits
    r[x] = glyph('0' + v / 10); r[x + 1] = glyph('0' + v % 10);
}

// the row of line `kind`
static void line_row(uint8_t kind, uint8_t *r) {
    uint8_t k, i;
    blank(r);
    switch (kind) {
    case DL_MODE: put(r, COL_LABEL, "MODE"); put(r, COL_VALUE, mode_name[dmode()]); break;
    case DL_LEVEL: put(r, COL_LABEL, "LEVEL"); put2(r, COL_VALUE, debug_level); break;
    case DL_CHAPTER:
        put(r, COL_LABEL, "CHAPTER");
        if (debug_chapter >= 9) { r[COL_VALUE] = glyph('1'); r[COL_VALUE + 1] = glyph('0' + debug_chapter - 9); }   // chapter 10
        else r[COL_VALUE] = glyph('1' + debug_chapter);
        break;
    case DL_STEP: {
        const char *n;
        put(r, COL_LABEL, "STEP");
        if (debug_pos == 0) n = "PRE";
        else if (debug_pos == POS_POST) n = "POST";
        else {
            k = story_step_get(debug_chapter, debug_pos - 1);
            n = (k & STEP_KIND) == STEP_MINI ? "MINI" : (k & STEP_KIND) == STEP_BOSS ? "BOSS" : step_label[k & 3];
        }
        put(r, COL_VALUE, n);
        break;
    }
    case DL_BARS:
        put(r, COL_LABEL, "BARS");
        for (i = 0; i < NUM_BARS; i++) r[COL_VALUE + i] = glyph((level_dirs >> i) & 1 ? 'R' : 'L');   // top bar first
        break;
    default: put(r, COL_LABEL, "BAR CHANGE"); put(r, COL_VALUE + 1, (level_dirs & KEEP_POS) ? "KEEP" : "SNAP");
    }
}

static void win_row(uint8_t y, const uint8_t *r) {
    set_win_tiles(0, y, 20, 1, r);
}

static void fill_win(uint8_t y, uint8_t t) {
    uint8_t r[20], i;
    for (i = 0; i < 20; i++) r[i] = t;
    win_row(y, r);
}


static void draw_line(uint8_t i) {                       // line slot i (0..5): its row, or a blank one past the last line
    uint8_t k[5], r[20], n = lines(k);
    if (i < n) line_row(k[i], r); else blank(r);
    win_row(ROW_LINE0 + 2 * i, r);
}

static void cursor(void) {
    OAM_item_t *o = shadow_OAM;
    o->y = (ROW_LINE0 + 2 * debug_sel) * 8 - 7 + 16;     // the mug stands on the line (as the lists' cursors)
    o->x = 8;
    o->tile = OBJ_MUG; o->prop = is_cgb ? OBJPAL_MUG_FULL : 0;
}

// the whole screen into the window map (the LCD is off)
static void draw_all(void) {
    uint8_t r[20], i;
    blank(r);
    put(r, COL_LABEL, "DEBUG MENU");
    win_row(0, r);
    fill_win(1, SKIN_TILE_EDGE);
    for (i = 0; i < 6; i++) {                                // six line slots on rows 2, 4 .. 12, a blank row after each (3, 5 .. 13)
        draw_line(i);
        fill_win(ROW_LINE0 + 2 * i + 1, TILE_HUD_BLANK);
    }
    fill_win(ROW_SEP, TILE_PANEL_TOP);
    blank(r); put(r, 255, info_text[dmode()]); win_row(ROW_INFO, r);
    blank(r); put(r, 255, "@ GO $ BACK > EDIT"); win_row(ROW_KEYS, r);
    fill_win(17, TILE_PANEL_BOT);
    music_pump();
}

static uint8_t vget(const volatile uint8_t *a) {
    while (STAT_REG & 2) ;
    return *a;
}

// ---- open and close -----------------------------------------------------------------------------------------------------------
void debug_open(void) BANKED {
    uint8_t k, i, b[20];
    if (game_state == GS_PAUSED) pause_close();      // opened from the pause menu: its window and the sound go back first
    debug_from_title = game_state == GS_TITLE;
    debug_story = 0; debug_classic = 0;
    if (debug_from_title) {
        debug_level = 1;
        k = title_items[title_sel];
        if (k == K_STORY) { debug_story = 1; debug_chapter = 0; debug_pos = 0; }
        else if (k == K_CLASSIC) debug_classic = 1;
        else if (k == K_ARCADE) { debug_story = 2; debug_chapter = 0; debug_pos = pos_next(0, 0, 1); }
        else if (k == K_CONTINUE) {                  // as CONTINUE starts it (story.c story_begin)
            debug_story = 1;
            debug_chapter = story_progress < STORY_CHAPTERS ? story_progress : STORY_CHAPTERS - 1;
            debug_pos = story_reached ? pos_next(debug_chapter, 0, 1) : 0;
        }
    } else if (story_on) {                           // in story (ARCADE) play: where the story (the run) is
        debug_story = (story_arc & 1) ? 2 : 1;
        debug_chapter = story_chapter;
        debug_pos = story_step + 1;
        if (!pos_ok(debug_chapter, debug_pos)) debug_pos = pos_next(debug_chapter, debug_pos, 1);
    } else if (play_mode == MODE_CLASSIC) {          // in CLASSIC play: its level (a repeat past wave 2: its row's)
        debug_classic = 1;
        for (k = level; k > CLASSIC_ROWS; k -= 13) ;
        debug_level = k;
    } else debug_level = level < DEBUG_LEVELS ? level : DEBUG_LEVELS;
    end_note();                                      // (WY and LYC back where the menu saves them)
    TRANS_MENU();                                    // (src/trans.c: the quick white fade)
    DISPLAY_OFF;
    overlay_on = 0; HIDE_WIN;
    typedef char keys_in_9000_block[KEY_A + 3 <= 128 ? 1 : -1];   // BG ids 0-127: VRAM 0x9000 + id * 16
    for (i = 0; i < 3; i++) {                        // the three button tiles' place is kept, the buttons go in
        const volatile uint8_t *t = (const volatile uint8_t *)(0x9000 + (uint16_t)(KEY_A + i) * 16);
        for (k = 0; k < 16; k++) b[k] = vget(t + k);
        set_win_tiles(0, DBG_SAVE_ROW + i, 16, 1, b);
    }
    b[0] = LYC_REG;
    set_win_tiles(0, DBG_SAVE_ROW + 3, 1, 1, b);
    for (i = 0; i < SKIN_SAVE_N; i++) {              // the wood wall's four tiles (over the stage ids 0-4) and, CGB, its six palettes: kept in the window map's off-screen rows
        const volatile uint8_t *t = (const volatile uint8_t *)(0x9000 + (uint16_t)i * 16);
        for (k = 0; k < 16; k++) b[k] = vget(t + k);
        set_win_tiles(0, SKIN_SAVE_ROW + i, 16, 1, b);
    }
    if (is_cgb) {
        VBK_REG = VBK_BANK_1;                        // (the attribute map's bytes hold the palettes' 8 bytes each)
        for (i = 0; i < SKIN_PALS; i++) {
            for (k = 0; k < 8; k++) { BCPS_REG = (SKIN_PAL_WALL + i) * 8 + k; b[k] = BCPD_REG; }
            set_win_tiles(0, SKIN_SAVE_ROW + i, 8, 1, b);
        }
        VBK_REG = VBK_BANK_0;
    }
    music_pump();
    list_skin_load();
    set_bkg_data(KEY_A, 3, list_key_tiles);
    if (is_cgb) {                                    // the window map's attributes: the wall's palettes (header, edge, lines, panel), the buttons' on the keys row
        VBK_REG = VBK_BANK_1;
        for (i = 0; i < 18; i++) {
            for (k = 0; k < 20; k++) b[k] = i == 0 ? SKIN_PAL_HEAD : i == 1 ? SKIN_PAL_EDGE : i >= ROW_SEP ? SKIN_PAL_FOOT : SKIN_PAL_WALL;
            if (i == ROW_KEYS) b[1] = b[6] = b[13] = SKIN_PAL_BTN;      // ("@ GO $ BACK > EDIT": the three buttons)
            set_win_tiles(0, i, 20, 1, b);
        }
        VBK_REG = VBK_BANK_0;
    }
    debug_sel = 1;                                   // (the first value line: Left / Right change the level at once)
    draw_all();
    for (i = 0; i < 40; i++) shadow_OAM[i].y = 0;
    cursor();
    oam_touched();
    WY_REG = 0; LYC_REG = 255;
    overlay_on = 1;
    game_state = GS_DEBUG;
    debug_menu_open = 1;
    DISPLAY_ON;
    SHOW_WIN;
}

// everything the menu moved comes back: the button tiles, LYC and WY, the banner rows, the sprites
static void close_menu(void) {
    uint8_t i, k, b[20];
    TRANS_MENU();                                    // (src/trans.c: the quick white fade)
    DISPLAY_OFF;                                     // (the tiles and palettes go back unseen: the game under the window shows them as soon as the window goes)
    overlay_on = 0; HIDE_WIN;
    debug_menu_open = 0;
    debug_sel = 0; debug_timer = 0;                  // (the gesture's count starts clean)
    for (i = 0; i < 3; i++) {
        const volatile uint8_t *r = (const volatile uint8_t *)(0x9C00 + (DBG_SAVE_ROW + i) * 32);
        for (k = 0; k < 16; k++) b[k] = vget(r + k);
        set_bkg_data(KEY_A + i, 1, b);
    }
    for (i = 0; i < SKIN_SAVE_N; i++) {              // the wood wall's tiles and palettes go back
        const volatile uint8_t *r = (const volatile uint8_t *)(0x9C00 + (SKIN_SAVE_ROW + i) * 32);
        for (k = 0; k < 16; k++) b[k] = vget(r + k);
        set_bkg_data(i, 1, b);
    }
    if (is_cgb) {
        for (i = 0; i < SKIN_PALS; i++) {
            const volatile uint8_t *r = (const volatile uint8_t *)(0x9C00 + (SKIN_SAVE_ROW + i) * 32);
            VBK_REG = VBK_BANK_1;
            for (k = 0; k < 8; k++) b[k] = vget(r + k);
            VBK_REG = VBK_BANK_0;
            set_bkg_palette(SKIN_PAL_WALL + i, 1, (uint16_t *)b);
        }
    }
    LYC_REG = vget((const volatile uint8_t *)(0x9C00 + (DBG_SAVE_ROW + 3) * 32));
    WY_REG = BANNER_WY;
    fill_win(0, TILE_PANEL_TOP);                     // (win_init's banner: panel, a blank text row, panel)
    fill_win(1, TILE_HUD_BLANK);
    fill_win(2, TILE_PANEL_BOT);
    for (i = 0; i < 40; i++) shadow_OAM[i].y = 0;
    oam_touched();
}

// the bars' directions: the next layout of dir_layout (back: the one before), the KEEP bit kept
static void bars_step(uint8_t back) {
    uint8_t j = 0, e = level_dirs & 0x3F;        // (e in a local: SDCC 4.5 kept j in L and loaded HL with &level_dirs inside the loop)
    for (; j < DIR_LAYOUTS - 1; j++) if (dir_layout[j] == e) break;
    j = back ? (j ? j - 1 : DIR_LAYOUTS - 1) : (j == DIR_LAYOUTS - 1 ? 0 : j + 1);   // (a layout not in the table counts as the last: the first follows)
    level_dirs = dir_layout[j] | (level_dirs & KEEP_POS);
}

// ---- a frame ------------------------------------------------------------------------------------------------------------------
static void set_mode(uint8_t m) {
    debug_story = m == DM_STORY ? 1 : m == DM_ARCADE ? 2 : 0;
    debug_classic = m == DM_CLASSIC;
    debug_level = 1;
    debug_chapter = 0;
    debug_pos = debug_story == 2 ? pos_next(0, 0, 1) : 0;    // (STORY: its PRE scene; ARCADE: the first step it can play)
    DISPLAY_OFF;
    draw_all();
    DISPLAY_ON;
    SHOW_WIN;
}

// 1: A started a game (the frame is over)
uint8_t debug_step(uint8_t pressed) BANKED {
    uint8_t k[5], n = lines(k), d = 0, c = debug_chapter, p = debug_pos, l = debug_level, top = debug_classic ? CLASSIC_ROWS : DEBUG_LEVELS, old = debug_sel, kind, m;
    if (pressed & J_UP) debug_sel = debug_sel ? debug_sel - 1 : n - 1;
    else if (pressed & J_DOWN) debug_sel = debug_sel == n - 1 ? 0 : debug_sel + 1;
    if (pressed & J_RIGHT) d = 1;
    else if (pressed & J_LEFT) d = 2;
    kind = k[old];
    if ((pressed & J_SELECT) && dmode() == DM_LEVEL) {                // P3: the next layout of the bars' directions
        bars_step(0);
        draw_line(2);                                                // (LEVEL mode: MODE, LEVEL, BARS, BAR CHANGE)
    }
    if (d) switch (kind) {
    case DL_MODE:
        m = dmode();
        m = d == 1 ? (m == DM_CLASSIC ? DM_LEVEL : m + 1) : (m == DM_LEVEL ? DM_CLASSIC : m - 1);
        set_mode(m);
        if (debug_sel >= lines(k)) debug_sel = 0;
        break;
    case DL_LEVEL:
        l = d == 1 ? (l == top ? 1 : l + 1) : (l == 1 ? top : l - 1);
        debug_level = l;
        draw_line(old);
        break;
    case DL_CHAPTER:
        c = d == 1 ? (c == STORY_CHAPTERS - 1 ? 0 : c + 1) : (c == 0 ? STORY_CHAPTERS - 1 : c - 1);
        if (!pos_ok(c, p)) p = pos_next(c, p, 1);
        debug_chapter = c; debug_pos = p;
        draw_line(old); draw_line(old + 1);
        break;
    case DL_STEP:
        debug_pos = pos_next(c, p, d == 1 ? 1 : -1);
        draw_line(old);
        break;
    case DL_BARS:
        bars_step(d == 2);                                           // (Left / Right: the layouts in order, as SELECT)
        draw_line(old);
        break;
    default:                                                         // BAR CHANGE: SNAP <-> KEEP
        level_dirs ^= KEEP_POS;
        draw_line(old);
    }
    if (debug_sel != old) cursor();
    if (pressed & (J_A | J_START)) {
        close_menu();
        if (debug_story) { save_lock = SAVE_LOCK_DEBUG; story_debug_start(debug_chapter, debug_pos, debug_story == 2); }
        else { play_mode = debug_classic ? MODE_CLASSIC : MODE_LEVEL; start_new_game(debug_level); }
        return 1;
    }
    if (pressed & J_B) {
        close_menu();
        game_state = debug_from_title ? GS_TITLE : GS_PLAYING;
        DISPLAY_ON;
    }
    return 0;
}

#ifdef AUTO_CARD                        // test-only (tests/test_fade_hw.py, never in a release): boot -> BOSS RUSH's first fight (as rush.c starts it) -> START 300 frames in -> DOWN, A: the
extern uint8_t frame_counter;
extern uint32_t score;
uint8_t auto_card(void) BANKED {         // HOW TO PLAY card -> (AUTO_CARD 1: B, 100 frames later, back to the menu; 2: the card stays open); the pause fades or the LCD-off cut (-DCARD_FADE=0). Returns joy.
    static uint16_t ac_t;
    uint8_t j = 0;
    if (game_state == GS_TITLE) {
        if (frame_counter == 100) { score = 0; lives = START_LIVES; rush_fight(0); }
    } else if (game_state == GS_GOAL) {
        if (!(++ac_t & 15)) j = J_A;
    } else if (game_state == GS_PLAYING || game_state == GS_PAUSED) {
        ac_t++;
        if (ac_t == 300) j = J_START;
        if (ac_t == 320) j = J_DOWN;
        if (ac_t == 340) j = J_A;
#if AUTO_CARD == 1
        if (ac_t == 440) j = J_B;
#endif
    }
    return j;
}
#endif

#ifdef AUTO_NOTE                        // test-only (tests/test_fade_hw.py, never in a release): a note shown at frame 100 of play is cut off at 110 the way a life lost or a scene change cuts it (overlay_on cleared, WY and LYC left on the note), START at 120. Returns joy.
uint8_t auto_note(void) BANKED {
    static uint8_t an_t;
    uint8_t j = 0;
    if (game_state == GS_PLAYING || game_state == GS_PAUSED) {
        if (an_t < 121) an_t++;
        if (an_t == 100) show_note("CLEAR THE BAR");
        if (an_t == 110) { overlay_on = 0; HIDE_WIN; }
        if (an_t == 120) j = J_START;
    }
    return j;
}
#endif
