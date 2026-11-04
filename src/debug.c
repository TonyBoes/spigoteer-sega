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
//   MIXED (LEVEL and CLASSIC): A or B, the DMG's mixed levels (level_dirs bit 6, MIXED_B; session only): A 2 px steps, B 1 px steps, variant C on R bars only.
//   BAR CHANGE (every mode but CLASSIC): SNAP (default: Up/Down snaps the bartender to the tap with a dust puff and a soft swish; CLASSIC always) or
//            KEEP (he keeps his x): level_dirs bit 7, KEEP_POS, the bit SETTINGS > BAR CHANGE (src/title.c) sets and saves; here it is for the session only.
// Up / Down move the cursor, Left / Right change the line's value, A or START starts, B closes (back to the title, or into the game).
#pragma bank 255
#include <gb/gb.h>
#include <gb/cgb.h>
#include <stdint.h>

#include "game.h"
#include "music.h"
#include "mg.h"
#include "story.h"
#include "list_keys.h"          // static const uint8_t list_key_tiles[]: the keys line's A, B and right buttons (assets/art/list_keys.txt)

#define DEBUG_LEVELS       20
#define POS_POST          (STORY_STEPS + 1)    // positions: 0 PRE, 1..STORY_STEPS the steps, POS_POST
#define DBG_WINDOW         72                  // frames from the first START tap to the third
#define DBG_SAVE_ROW       28                  // the window map's off-screen rows: the saved tiles (28-30) and LYC (31)
#define SKIN_SAVE_ROW      18                  // rows 18-22: the wood wall's four tiles (src/mg_list.c list_skin_load); in the attribute map the six palettes' bytes
#define SKIN_SAVE_N         4
#define SKIN_PALS           6

extern uint8_t overlay_on, level, story_chapter, story_step, state_timer, boss_on;
uint8_t debug_menu_open;
uint8_t debug_level;               // LEVEL's / CLASSIC's level
uint8_t debug_from_title;          // bit 0: opened on the title. DEBUG_MENU builds: bits 1-2 the STRESS run in play (1 SPACE, 2 CLASSIC, 3 ARCADE; 0 none), kept while the menu is closed.
                                   // Bits 3-6 and 7: the TUNING page's values (below), session only, 0 = the game's own default; debug_open and title_enter leave them alone
uint8_t debug_sel;                 // open: the cursor's line. Before it: bit 0 the title's SELECT toggled the music, bits 1-2 the START taps so far
uint8_t debug_timer;               // the gesture's frames left
uint8_t debug_story;               // 1: the menu selects a story position, 2: an ARCADE one, 3 (DEBUG_MENU builds): a STRESS case in debug_pos (0: a level)
uint8_t debug_chapter;             // its chapter (0..STORY_CHAPTERS-1)
uint8_t debug_pos;                 // its position (0 PRE, 1..STORY_STEPS step pos-1, POS_POST)
uint8_t debug_classic;             // 1: the menu is CLASSIC's (debug_level is its level, 1..CLASSIC_ROWS); 2: the TUNING page
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
enum { DL_MODE, DL_LEVEL, DL_CHAPTER, DL_STEP, DL_BARS, DL_CHANGE, DL_FPS, DL_MIXED, DL_PEAK, DL_TUNE };   // (DL_TUNE + i: the TUNING page's knob i)
enum { DM_LEVEL, DM_STORY, DM_ARCADE, DM_CLASSIC, DM_TUNE, DM_STRESS };
#define FROM_TITLE (debug_from_title & 1)
#ifdef DEBUG_MENU
#define DM_LAST DM_STRESS                                // the playtest builds add STRESS: the automated perf scenarios' crowds (below)
#define STRESS_MENU (debug_story == 3)
#else
#define DM_LAST DM_TUNE
#define STRESS_MENU 0
#endif

#ifdef DEBUG_MENU
static uint8_t dmode(void) {
    if (STRESS_MENU) return DM_STRESS;
    return debug_classic ? DM_CLASSIC - 1 + debug_classic : debug_story ? DM_STORY - 1 + debug_story : DM_LEVEL;
}
#else
static uint8_t dmode(void) { return debug_classic ? DM_CLASSIC - 1 + debug_classic : debug_story ? DM_STORY - 1 + debug_story : DM_LEVEL; }
#endif


// ---- the TUNING page (owner 2026-11-03): single-number knobs to change while testing; session only (nothing saved, power-on resets them) ----------------------------
// ONE ENTRY PER KNOB in tune_knob[] (name, number of values, the labels, get / set of the value's index); the page's lines, the drawing and Left / Right follow
// the table, TUNE_N is its length. The values live in debug_from_title's bits 3-7 (no WRAM global), stored so that 0 is the game's own default (a power-on
// needs no setting): COINS bits 3-6 (the list's index xor 6: "1 IN 8" is index 6), GUS bit 7 (1: he rolls like the others). Other code reads them
// through tip_tuned() (boss.c restores tip_chance with it when a fight ends) and the bit TUNE_GUS_ROLLS (game.h; tip.c maybe_tip).
#define COIN_N 11
static const char *const coin_label[COIN_N] = { "OFF", "1 IN 2", "1 IN 3", "1 IN 4", "1 IN 5", "1 IN 6", "1 IN 8", "1 IN 10", "1 IN 12", "1 IN 16", "ALWAYS" };
static const uint8_t coin_val[COIN_N] = { 0, 128, 85, 64, 51, 43, 32, 26, 21, 16, 255 };   // tip_chance (out of 256) of each
static const char *const onoff_label[2] = { "ON", "OFF" };

// COINS: the index. Setting it also applies it at once (not during a boss fight: its no-tips stays until it ends and boss.c restores tip_tuned())
static uint8_t coin_get(void) { return ((debug_from_title >> 3) & 15) ^ 6; }
static void coin_set(uint8_t i) {
    debug_from_title = (debug_from_title & ~0x78) | ((i ^ 6) << 3);
    if (!boss_on) tip_chance = coin_val[i];
}
static uint8_t gus_get(void) { return debug_from_title >> 7; }                              // 0 ON (always tips), 1 OFF
static void gus_set(uint8_t i) { debug_from_title = (debug_from_title & 0x7F) | (i << 7); }

struct knob { const char *name; uint8_t n; const char *const *label; uint8_t (*get)(void); void (*set)(uint8_t); };
static const struct knob tune_knob[] = {
    { "COINS",      COIN_N, coin_label,  coin_get, coin_set },
    { "GUS ALWAYS", 2,      onoff_label, gus_get,  gus_set },
};
#define TUNE_N (sizeof tune_knob / sizeof tune_knob[0])

uint8_t tip_tuned(void) BANKED { return coin_val[coin_get()]; }                   // the COINS value (boss.c: a fight's end)

// the kind of each line of the mode shown into k[]; the number of lines
static uint8_t lines(uint8_t *k) {
    uint8_t n = 0, i;
    k[n++] = DL_MODE;
    if (debug_classic == 2) { for (i = 0; i < TUNE_N; i++) k[n++] = DL_TUNE + i; return n; }
    if (debug_classic) k[n++] = DL_LEVEL;
#ifdef DEBUG_MENU
    else if (STRESS_MENU) k[n++] = DL_PEAK;
#endif
    else if (debug_story) { k[n++] = DL_CHAPTER; k[n++] = DL_STEP; k[n++] = DL_CHANGE; }
    else { k[n++] = DL_LEVEL; k[n++] = DL_BARS; k[n++] = DL_CHANGE; }
    k[n++] = DL_FPS;
    if (!debug_story) k[n++] = DL_MIXED;
    return n;
}

static const char *const step_label[4] = { "OPEN", "HAPPY", "LAST", "" };   // a shift's index (STEP_INDEX)
#ifdef DEBUG_MENU
static const char *const mode_name[6] = { "LEVEL", "STORY", "ARCADE", "CLASSIC", "TUNING", "STRESS" };
static const char *const info_text[6] = { "LEVEL TEST RUN", "NOTHING IS SAVED", "NOTHING IS SAVED", "CLASSIC 1983 RUN", "THIS SESSION ONLY", "WORST CASE CROWD" };
static const char *const peak_name[3] = { "SPACE", "CLASSIC", "ARCADE" };
#else
static const char *const mode_name[5] = { "LEVEL", "STORY", "ARCADE", "CLASSIC", "TUNING" };
static const char *const info_text[5] = { "LEVEL TEST RUN", "NOTHING IS SAVED", "NOTHING IS SAVED", "CLASSIC 1983 RUN", "THIS SESSION ONLY" };
#endif

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
#ifdef DEBUG_MENU
    case DL_PEAK: put(r, COL_LABEL, "PEAK"); put(r, COL_VALUE, peak_name[debug_pos]); break;
#endif
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
    case DL_FPS:                                         // the DMG's 30 fps mode (src/half.c): AUTO (the levels measured too heavy), FORCE ON, FORCE OFF; the CGB never
        put(r, COL_LABEL, "30 FPS");
        k = (HALF >> HALF_FORCE_SHIFT) & 3;
        put(r, COL_VALUE, is_cgb ? "NO CGB" : k == 1 ? "ON" : k == 2 ? "OFF" : "AUTO");
        break;
    case DL_MIXED:                                       // the DMG's mixed levels: A (2 px steps, both directions at even shifts) or B (1 px, looks split by direction)
        put(r, COL_LABEL, "MIXED"); put(r, COL_VALUE + 1, is_cgb ? "NO CGB" : (level_dirs & MIXED_B) ? "B" : "A");
        break;
    default:
        if (kind >= DL_TUNE) { const struct knob *t = &tune_knob[kind - DL_TUNE]; put(r, COL_LABEL, t->name); put(r, COL_VALUE, t->label[t->get()]); break; }
        put(r, COL_LABEL, "BAR CHANGE"); put(r, COL_VALUE + 1, (level_dirs & KEEP_POS) ? "KEEP" : "SNAP");
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
    uint8_t k[6], r[20], n = lines(k);
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
#ifdef DEBUG_MENU
    debug_from_title = (debug_from_title & ~1) | (game_state == GS_TITLE);   // (the STRESS run's bits and the TUNING values stay)
#else
    debug_from_title = (debug_from_title & ~1) | (game_state == GS_TITLE);
#endif
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
    b[0] = WIN_LYC_NOW;
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
    SET_WY(0); SET_LYC(255);
    overlay_on = 1;
    game_state = GS_DEBUG;
    debug_menu_open = 1;
    SHOW_WIN;                                        // (before the LCD comes on: the quick fade's reveal runs inside DISPLAY_ON, and a window shown after it let it fade in the title's screen under the menu)
    DISPLAY_ON;
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
            (set_bkg_palette)(SKIN_PAL_WALL + i, 1, (uint16_t *)b);   // (raw: b was read back from palette RAM, already lifted when SCREEN is BRIGHT)
        }
    }
    SET_LYC(vget((const volatile uint8_t *)(0x9C00 + (DBG_SAVE_ROW + 3) * 32)));
    SET_WY(BANNER_WY);
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
    level_dirs = dir_layout[j] | (level_dirs & (KEEP_POS | MIXED_B));
}

// ---- a frame ------------------------------------------------------------------------------------------------------------------
static void set_mode(uint8_t m) {
#ifdef DEBUG_MENU
    debug_story = m == DM_STORY ? 1 : m == DM_ARCADE ? 2 : m == DM_STRESS ? 3 : 0;
#else
    debug_story = m == DM_STORY ? 1 : m == DM_ARCADE ? 2 : 0;
#endif
    debug_classic = m == DM_CLASSIC ? 1 : m == DM_TUNE ? 2 : 0;
    debug_level = 1;
    debug_chapter = 0;
    debug_pos = debug_story == 2 ? pos_next(0, 0, 1) : 0;    // (STORY: its PRE scene; ARCADE: the first step it can play)
    DISPLAY_OFF;
    draw_all();
    DISPLAY_ON;
    SHOW_WIN;
}

#ifdef DEBUG_MENU
// ---- STRESS (owner 2026-10-28; DEBUG_MENU builds only): the automated perf scenarios' worst cases, to feel on a phone or a cart ------------------------------
// The scenarios (tests/perf_helpers.py RealisticPeak / ClassicPeak, test_perf.py, test_perf_arcade.py) start a level and keep its crowd at a target by
// making the next arrival due at once; this does the same with the game's own spawn code (patrons.c try_spawn: its bar caps, its 1-in-4 hurried
// share): src/story.c pat_done, which patrons.c calls after each arrival while an arrival pattern runs (pat_len), sets the bars' caps (the crowd's size),
// a short wait to the next arrival and a quota that never ends the level, and costs the normal play not one cycle. The player plays normally and can lose (the scenarios top up lives and push walkers back; this does not, and has no second bartender's mugs:
// the player's own pours and the drinkers' empties are the mugs). The run lives in debug_from_title's bits 1-2 (no WRAM global); the title clears it.
//   SPACE    LEVEL 10, the space lounge (the fastest row), every bar L: 10 patrons
//   CLASSIC  CLASSIC level 12 (R L R L, every bar's cap 4): 16 patrons
//   ARCADE   ARCADE chapter 10, loop 4, Last call (level 40): 10 patrons
void story_stress_start(void) BANKED;                            // src/story.c
extern uint8_t pat_pos, pat_buf[STORY_PAT_MAX];                // (story.c)
static void stress_start(uint8_t c) {
    uint8_t arc = c == 2;
    save_lock = SAVE_LOCK_DEBUG;
    if (arc) story_stress_start();
    else {
        level_dirs &= KEEP_POS;                                  // (every bar L, no mixed levels)
        play_mode = c ? MODE_CLASSIC : MODE_LEVEL;
        start_new_game(c ? 12 : 10);
        pat_len = 1; pat_pos = 0; pat_buf[0] = 0;               // a pattern of one entry: patrons.c then calls story.c pat_done after every arrival (ARCADE: the shift's own pattern runs, pat_done is the hook too)
        spawn_timer = 1;
    }
    debug_from_title = (c + 1) << 1;
}
#endif

// 1: A started a game (the frame is over)
uint8_t debug_step(uint8_t pressed) BANKED {
    uint8_t k[6], n = lines(k), d = 0, c = debug_chapter, p = debug_pos, l = debug_level, top = debug_classic ? CLASSIC_ROWS : DEBUG_LEVELS, old = debug_sel, kind, m;
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
        m = d == 1 ? (m == DM_LAST ? DM_LEVEL : m + 1) : (m == DM_LEVEL ? DM_LAST : m - 1);
        set_mode(m);
        if (debug_sel >= lines(k)) debug_sel = 0;
        break;
    case DL_LEVEL:
        l = d == 1 ? (l == top ? 1 : l + 1) : (l == 1 ? top : l - 1);
        debug_level = l;
        draw_line(old);
        break;
#ifdef DEBUG_MENU
    case DL_PEAK:
        debug_pos = d == 1 ? (p == 2 ? 0 : p + 1) : (p == 0 ? 2 : p - 1);
        draw_line(old);
        break;
#endif
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
    case DL_FPS:                                                     // AUTO -> ON -> OFF (Right), back (Left); at once for the level being played
        if (!is_cgb) {
            m = (HALF >> HALF_FORCE_SHIFT) & 3;
            m = d == 1 ? (m == 2 ? 0 : m + 1) : (m == 0 ? 2 : m - 1);
            HALF = (HALF & ~(3 << HALF_FORCE_SHIFT)) | (m << HALF_FORCE_SHIFT);
            half_decide();
            draw_line(old);
        }
        break;
    case DL_MIXED:                                                   // A <-> B (for the next mirror_load)
        level_dirs ^= MIXED_B;
        draw_line(old);
        break;
    default:
        if (kind >= DL_TUNE) {                                       // a TUNING knob: its next / previous value
            const struct knob *t = &tune_knob[kind - DL_TUNE];
            m = t->get();
            t->set(d == 1 ? (m == t->n - 1 ? 0 : m + 1) : (m ? m - 1 : t->n - 1));
            draw_line(old);
            break;
        }
        level_dirs ^= KEEP_POS;                                      // BAR CHANGE: SNAP <-> KEEP
        draw_line(old);
    }
    if (debug_sel != old) cursor();
    if ((pressed & (J_A | J_START)) && debug_classic != 2) {
        close_menu();
#ifdef DEBUG_MENU
        debug_from_title &= 1;                                       // (a plain start ends a STRESS run)
        if (STRESS_MENU) { stress_start(debug_pos); return 1; }
#endif
        if (debug_story) { save_lock = SAVE_LOCK_DEBUG; story_debug_start(debug_chapter, debug_pos, debug_story == 2); }
        else { play_mode = debug_classic ? MODE_CLASSIC : MODE_LEVEL; start_new_game(debug_level); }
        return 1;
    }
    if (pressed & (J_B | J_A | J_START)) {                           // (A and START on the TUNING page: nothing to start, they close it as B does)
        close_menu();
        game_state = FROM_TITLE ? GS_TITLE : GS_PLAYING;
        DISPLAY_ON;
    }
    return 0;
}

#ifdef AUTO_CARD                        // test-only (tests/test_fade_hw.py, never in a release): boot -> BOSS RUSH's first fight (as rush.c starts it) -> START 300 frames in -> DOWN, A: the
extern uint8_t frame_counter;
extern uint32_t score;
void boss_card_mark(uint8_t v) BANKED;
uint8_t auto_card(void) BANKED {         // HOW TO PLAY card -> (AUTO_CARD 1: B, 100 frames later, back to the menu; 2: the card stays open); the pause fades or the LCD-off cut (-DCARD_FADE=0). Returns joy.
    static uint16_t ac_t;
    uint8_t j = 0;
    if (game_state == GS_TITLE) {
        if (frame_counter == 100) { score = 0; lives = START_LIVES; boss_card_mark(0); rush_fight(0); }   // (his card marked seen: the first-encounter card would pause the game by itself)
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

#ifdef AUTO_MR                          // test-only (tests/test_double_speed.py, never in a release): boot -> Milk Run's practice round at frame 100 (its card marked seen), no input after. Returns joy.
extern uint8_t frame_counter;
void card_mark(uint8_t id) BANKED;
void mg_enter(uint8_t id, uint8_t mode) BANKED;
uint8_t auto_mr(void) BANKED {
    if (game_state == GS_TITLE && frame_counter == 100) { card_mark(6); mg_enter(6, 1); }
    return 0;
}
#endif

#ifdef AUTO_BOSS                        // test-only (tests/test_fade_hw.py, never in a release): boot -> STORY chapter 1's Last call (as the debug select starts it) -> its quota poked met at
extern uint8_t frame_counter, boss_on, boss_state, boss_step, boss_hp;   // frame 60 of play -> the bars poked empty -> the level turns into Big Tex's fight (cover, banner, entrance) ->
extern uint8_t story_goal[], rng_state, pat_buf[];             // (AUTO_BOSS 1: his first-encounter card opens by itself, A turns and closes it; 2: his card marked seen first: no card) -> 120 frames into the fight everything
extern uint32_t score;                   // is frozen (no arrivals, no walkers, no stomp), so the last frame is a still picture whatever the fades took. A on every banner. Returns joy.
uint8_t auto_boss(void) BANKED {
    static uint16_t ab_t, ab_f;
    static uint8_t ab_p;
    uint8_t j = 0, p;
    if (game_state == GS_TITLE) {
        if (frame_counter == (uint8_t)(100 + (*(const volatile uint8_t *)0x3FFF == 0xFF ? 0 : *(const volatile uint8_t *)0x3FFF))) {   // (the byte at 0x3FFF, free ROM0 padding, is a start delay in frames: tests/boss_capture.py patches it to catch every frame of the entrance on a whole-second SameBoy run)
            score = 0; lives = START_LIVES; rng_state = 0xA7;
#if AUTO_BOSS == 2
            boss_card_mark(0);
#endif
            story_debug_start(0, 4, 0);
        }
    } else if (game_state == GS_GOAL) {
        if (!(++ab_t & 15)) j = J_A;
    } else if (game_state == GS_PAUSED) {            // (the card: A turns its page, A on the last one closes it)
        ab_p++;
        if (ab_p == 120 || ab_p == 240 || ab_p == 360) j = J_A;
    } else if (game_state == GS_PLAYING) {
        if (!boss_on) {
            if (++ab_t == 60) served = story_goal[1];
            if (ab_t > 70) {
                for (p = 0; p < MAX_PATRONS; p++) patron_state[p] = 0;
                patrons_live = 0; lists_dirty = 1;
                clear_mugs(); mugs_live = 0;
            }
        } else if (boss_state >= 6) {                 // (BS_WARM / ENTER / WALKIN: the streaming of his tiles and his entrance: the regulars' order and every draw after it the same in every run, as the fades and the card take different numbers of next_rand calls)
            rng_state = 0x3D;
            for (p = 0; p < STORY_PAT_MAX; p++) pat_buf[p] = p % 3 ? 2 + (p % 3 - 1) : 0;   // (bars 0, 2, 3: never Tex's, bar 1)
        } else if (boss_state == 0 && boss_hp) {      // (BS_WALK: the fight itself is on)
            if (ab_f == 0) rng_state = 0x5C;               // (which regular comes where is random: the same draw in every run)
            if (++ab_f == 120) {
                patron_speed = 0; hurry_speed = 0; spawn_timer = 0xFFFF; boss_step = 0;
                sa_hold = 255;
            }
        }
    }
    return j;
}
#endif

#ifdef AUTO_MG                          // test-only (tools/mg_capture.py, never in a release): boot -> mini-game `id` at frame 100 + delay, then a fixed button pattern. The settings are the free ROM0 bytes
extern uint8_t frame_counter;                   // (patched into the ROM: 3FF8 non-zero: through the MINI GAMES list, 3FFF delay (0xFF none), 3FFD game id, 3FFC mode, 3FFB frames/4 of play before the timer is forced out (0xFF never), 3FFA score/16 given then, 3FF9 non-zero: the full card)
extern uint32_t score;
void card_mark(uint8_t id) BANKED;
void mg_enter(uint8_t id, uint8_t mode) BANKED;
extern uint8_t ml_sel, story_unskip;
uint8_t auto_mg(void) BANKED {
    static uint16_t am_t, am_p, am_r;
    static uint8_t am_on;
    const volatile uint8_t *c = (const volatile uint8_t *)0x3FF8;
    uint8_t j = 0, d = c[7] == 0xFF ? 0 : c[7];
    if (game_state == GS_TITLE) {
        if (!am_on && ++am_t == (uint16_t)(100 + d)) {
            am_on = 1;
            if (!c[1]) card_mark(c[5]);
            if (c[0] == 2) { story_unskip = 255; story_debug_start(c[5], 3, 0); }   // (3FF8 2: the story's mini-game step of chapter 3FFD, a game id 0-9)
            else if (c[0]) mg_list_enter(); else mg_enter(c[5], c[4]);   // (3FF8 1: through BONUS > MINI GAMES, the way a player goes)
        }
        return 0;
    }
    if (game_state == GS_MGLIST) {
        if (!++am_p) am_p = 1;
        ml_sel = c[5] > 11 ? c[5] - 2 : c[5];
        if (am_p == 40) j = J_A;
        return j;
    }
    if (game_state != GS_MINI) return 0;
    if (mg_phase == MG_CARD) { if (!(++am_p & 255)) j = J_A; }
    else if (mg_phase == MG_INTRO || mg_phase == MG_COUNT) { }
    else if (mg_phase == MG_RESULT) { if (c[0] == 1 && ++am_r == 200) j = J_B; }   // (from the list: B, back to it)
    else if (mg_phase == MG_PLAY) {
        am_p++;
        j = (am_p & 8) ? ((am_p & 16) ? J_A : J_B) : ((am_p & 32) ? J_RIGHT : J_LEFT);
        if (c[3] != 0xFF && am_p >= (uint16_t)c[3] * 4) { mg_timer = 1; mg_score = (uint16_t)c[2] * 16; }
    }
    return j;
}
#endif

#ifdef AUTO_NOTE                       // test-only (tests/test_fade_hw.py, never in a release): a note shown at frame 100 of play is cut off at 110 the way a life lost or a scene change cuts it (overlay_on cleared, WY and LYC left on the note), START at 120. Returns joy.
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
