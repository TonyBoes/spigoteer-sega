// Title screen (M10a): the SPIGOTEER logo fills with beer letter by letter (bottom-up, a frothy head, drips),
// then sparkles once; a menu with a mug cursor and the HI score on row 0 (the in-game HUD's row), every line
// centred to the pixel (tools/gen_art.py pre-renders the text: an odd-length line sits 4 px right inside one more
// tile); below it a looping bar scene on the bottom counter: the bartender slides a mug to a patron, who drinks
// and sends the empty back. Foam bubbles drift up past the logo now and then.
//
// The menu (owner 2026-10-11: "a sub menu scheme. Top level - play, bonus, settings"): the top level PLAY / BONUS /
// SETTINGS; A (or START) opens the item's submenu in the same place: PLAY [CONTINUE] / STORY / ARCADE / CLASSIC
// (CONTINUE when a story save exists: M11b; the three modes, owner 2026-10-11: CLASSIC starts the 1983 table's level 1,
// src/classic.c, with its own top 5), BONUS SOUNDTRACK (the soundtrack player, src/jukebox.c) / MINI GAMES (Practice: the
// mini-games reached, src/mg_list.c) / BOSS RUSH (src/rush.c), SETTINGS MUSIC ON-OFF. B in a submenu goes back to the top level, the cursor on the item it came from. SELECT
// toggles the music anywhere on the title (as before). A submenu's lines replace the menu's text over a few frames
// (menu_frame: within the VBlank drain's budget, 2-5 frames).
//
// LCD off to enter. Afterwards every tilemap change goes through the VBlank queue (vq_add) from WRAM buffers.
// BG ids (title only; the level load restores them): menu text over the venue pool's stage ids (0..19: no stage on
// the title; the saloon's bar ids sit at the top of the pool, above them) and after the logo fill states; the
// lettering, its fill states and the scene's patron over the patron range (72..227). OBJ: the effects over the
// show performers' tiles (OBJ_DANCER, reloaded by load_venue); the bartender (permanent) and the saloon's drink
// frames (load_venue(0)).
// OAM: bartender 0-3, scene mug 4, cursor 5, sparkle 6, drip 7, bubbles 8-9. Per scanline at most 4 (scene 3).
#pragma bank 255
#include <gb/gb.h>
#include <gb/cgb.h>
#include <stdint.h>

#include "game.h"
#include "palettes.h"
#include "music.h"
#include "title_art.h"      // this bank's own art data (static const)
#include "story.h"

extern uint8_t overlay_on, hi_digits[6];
extern const uint8_t bar_tiles[];
BANKREF_EXTERN(art_tiles)
BANKREF_EXTERN(patron_tiles_cowboys)
extern const uint8_t patron_tiles_cowboys[];
void bkg_data_far(uint8_t first, uint8_t n, const uint8_t *d, uint8_t bank);

#define WALL_RGB_T (venue.pal[VENUE_PAL_BAR][0])   // the saloon's wall: colour 0 of every title BG palette
#define RGB15(r, g, b) ((uint16_t)((r) | ((g) << 5) | ((b) << 10)))

// ---- layout ----
#define LOGO_ROW        2       // the logo: rows 2-3, columns 1..18
#define ROW_HI          0       // the HI line (the HUD's row in play)
// The menu column, one item every other row, centred on row 9: 1 item row 9, 2 rows 8-10, 3 rows 7-11, 4 rows 6-12.
// K_*, TM_*: game.h.
#define MENU_MAX        4
#define MENU_ROW(n)   (10 - (n))
#define HARD_ROW        5       // the difficulty prompt: its lines on rows 5, 8, 11, the captions on 6, 9, 12
#define MENU_FIRST_ROW  5       // the rows a menu can use: 5..12
#define MENU_LAST_ROW  12
#define MENU_COPIES_PER_FRAME 2 // a submenu's redraw: 20-byte rows (tiles or CGB attributes) queued per frame
#define SCENE_BAR       3       // the scene stands on bar 3's rows (14-15 wall, 16 counter): draw_bartender() places him
#define SCENE_TOP_Y   (BAR_TOP_Y(SCENE_BAR) + 16)   // OAM y of the scene's wall top
#define PATRON_COL      3       // the patron: BG tiles at columns 3-4 of rows 14-15 (x 24..39)
#define PATRON_PX      24
#define CATCH_X        40       // a full mug's left edge here: the patron catches it
#define BT_X          124       // the bartender's x
#define LAUNCH_X      116       // where his mug starts (and the empty comes back to)
#define BGPAL_LOGO      BGPAL_PATRON       // 2
#define BGPAL_TEXT      3
#define BGPAL_TEXT_SEL  4
#define BGPAL_TPATRON   BGPAL_STAGE        // 5 (no stage on the title)
#define OBJPAL_FX       6
#define OBJ_FX          OBJ_DANCER
#define FX_BUBBLE       (OBJ_FX + 0)       // small, big
#define FX_SPARKLE      (OBJ_FX + 4)       // small, big
#define FX_DRIP         (OBJ_FX + 8)       // forming, falling
#define OAM_TMUG        4
#define OAM_CURSOR      5
#define OAM_SPARKLE     6
#define OAM_DRIP        7
#define OAM_BUBBLE      8

// ---- logo timing (frames since the title appeared) ----
#define LOGO_T0         6       // first letter starts filling
#define LOGO_STAGGER    8       // next letter this much later
#define LOGO_STEP       4       // frames per fill state
#define LOGO_LETTERS    9
#define LOGO_FILLED   (LOGO_T0 + (LOGO_LETTERS - 1) * LOGO_STAGGER + (TT_LOGO_STATES - 1) * LOGO_STEP)
#define SPARKLE_T0    (LOGO_FILLED + 6)
#define SPARKLE_EACH    6       // frames on each letter
#define LOGO_DONE_T   (SPARKLE_T0 + LOGO_LETTERS * SPARKLE_EACH)
#define DRIP_LEN       22
#define TITLE_IDLE_FRAMES 1200  // 20 s

enum { SC_IDLE, SC_SLIDE, SC_DRINK, SC_WINDUP, SC_RETURN, SC_CATCH };
#define SC_IDLE_FRAMES   40
#define SC_SLIDE_POSE     8
#define SC_DRINK_FRAMES  96
#define SC_WINDUP_FRAMES 24
#define SC_CATCH_FRAMES  14

// ---- state (globals => symbols the tests read) ----
uint16_t title_t;               // frames since the title appeared
uint8_t  title_menu;            // TM_* (game.h): the top level, or the submenu of top item title_menu - 1
uint8_t  title_back;            // the menu title_enter opens (the soundtrack player goes back to BONUS); then TM_TOP
uint8_t  title_back_sel;        // ... and the line its cursor starts on (then 0)
uint8_t  title_sel;             // the selected line of the shown menu (top: 0 PLAY, 1 BONUS, 2 SETTINGS; PLAY: [CONTINUE],
                                // STORY, ARCADE, CLASSIC; BONUS: SOUNDTRACK; SETTINGS: MUSIC, BAR CHANGE)
uint8_t  title_hi;              // the top 5 the HI line shows (MODE_*): the one under PLAY's cursor, else ARCADE's
uint8_t  attract_n;             // the idle title's next table (attract_tbl index)
uint8_t  title_items[MENU_MAX]; // K_* per menu line (game.h)
uint8_t  title_n;               // menu lines
uint8_t  title_rows[MENU_MAX];  // their screen rows
uint16_t title_dirty;           // menu rows (bit = screen row) still to be redrawn through the VBlank queue
uint8_t  title_go;              // test hook: a level number (1..99) written here starts the LEVEL harness (MODE_LEVEL, the
                                // old 10-level rotation) from that level on the next title frame (tests/conftest.py);
                                // with bit 7 set (0x80 | level), CLASSIC from that level (MODE_CLASSIC)
uint16_t title_idle;            // M10b: frames without a key; at TITLE_IDLE_FRAMES the top-5 table shows (scores.c)
uint8_t  logo_state[LOGO_LETTERS];   // fill state per letter: 0 empty .. TT_LOGO_STATES-1 the final art
uint8_t  logo_done;             // filled and sparkled
uint8_t  tscene_phase, tscene_timer, tscene_mug_x, tscene_loops;
uint8_t  bubble_y[2], bubble_x[2], bubble_timer;   // bubble_y 0: free (else screen y + 16, in 1/2 px: see below)
static uint8_t bubble_half;
static uint8_t t_rng = 0x5D;    // the title's own random numbers (the game's sequence must not depend on the title)

static uint8_t logo_buf[LOGO_LETTERS][4];
static uint8_t hi_buf[6];
static const uint8_t attract_tbl[TOP_TABLES] = { MODE_ARCADE, MODE_STORY, MODE_CLASSIC };   // the idle title cycles them
static uint8_t menu_buf[MENU_MAX][20], row_blank[20], attr_txt[20], attr_sel[20];

static uint8_t trand(void) {
    t_rng ^= t_rng << 7;
    t_rng ^= t_rng >> 5;
    t_rng ^= t_rng << 3;
    return t_rng;
}

// a 20-wide row: blank, then the string (column, count, ids) at its column
static void build_row(uint8_t *row, const uint8_t *s) {
    uint8_t i;
    for (i = 0; i < 20; i++) row[i] = TT_BLANK;
    for (i = 0; i < s[1]; i++) row[s[0] + i] = s[2 + i];
}

// per K_* (game.h order): the line's text and the screen x of its first text pixel (MUSIC: by sound_on)
static const uint8_t *const k_text[] = { tt_arcade, tt_story, tt_music_on, tt_continue, tt_bonus, tt_play, tt_settings,
                                         tt_soundtrack, tt_classic, tt_minigames, tt_bossrush, tt_erase, tt_debug, tt_erase_q, tt_no, tt_yes,
                                         tt_bar_snap, tt_bar_keep, tt_credits, tt_easy, tt_normal, tt_hard, tt_cap_easy, tt_cap_normal, tt_cap_hard };
static const uint8_t k_left[] = { TT_X_ARCADE, TT_X_STORY, TT_X_MUSIC_ON, TT_X_CONTINUE, TT_X_BONUS, TT_X_PLAY,
                                  TT_X_SETTINGS, TT_X_SOUNDTRACK, TT_X_CLASSIC, TT_X_MINIGAMES, TT_X_BOSSRUSH, TT_X_ERASE, TT_X_DEBUG, TT_X_ERASE_Q, TT_X_NO, TT_X_YES,
                                  TT_X_BAR_SNAP, TT_X_BAR_KEEP, TT_X_CREDITS, TT_X_EASY, TT_X_NORMAL, TT_X_HARD, TT_X_CAP_EASY, TT_X_CAP_NORMAL, TT_X_CAP_HARD };
#define IS_BAR(k) ((k) == K_BARCHANGE || (k) == K_BARKEEP)   // SETTINGS' BAR line (the items after K_BARKEEP are the difficulty prompt's)

static void build_item(uint8_t i) {
    uint8_t k = title_items[i];
    build_row(menu_buf[i], k == K_MUSIC && !sound_on ? tt_music_off : k_text[k]);
}

static uint8_t text_left(uint8_t i) {           // screen x of the first text pixel of menu line i 
    uint8_t k = title_items[i];
    return k == K_MUSIC && !sound_on ? TT_X_MUSIC_OFF : k_left[k];
}

static void set_sel_attr(uint8_t sel, uint8_t on) {
    if (is_cgb) vq_add(1, on ? attr_sel : attr_txt, 0, title_rows[sel], 20);
}

// menu m (TM_*) into title_items / title_n / title_rows and the line buffers, the cursor on line sel. The rows of the
// old and the new menu are marked for the redraw (menu_frame; title_enter draws them at once with the LCD off).
static void menu_open(uint8_t m, uint8_t sel) {
    uint8_t i;
    for (i = 0; i < title_n; i++) title_dirty |= (uint16_t)1 << title_rows[i] | (title_menu == TM_HARD ? (uint16_t)2 << title_rows[i] : 0);   // (the prompt's captions too)
    title_menu = m;
    title_n = 0;
    switch (m) {
    case TM_TOP:
        title_items[title_n++] = K_PLAY;
        title_items[title_n++] = K_BONUS;
        title_items[title_n++] = K_SETTINGS;
        break;
    case TM_PLAY:     // M11b: CONTINUE when a story is saved part way (a shift or a chapter cleared, not all ten)
        if ((story_progress || story_reached) && story_progress < STORY_CHAPTERS) title_items[title_n++] = K_CONTINUE;
        title_items[title_n++] = K_STORY;
        title_items[title_n++] = K_ARCADE;
        title_items[title_n++] = K_CLASSIC;
        break;
    case TM_BONUS:    // the soundtrack (its songs unlock as the story is played: save.c); the mini-games (Practice);
        title_items[title_n++] = K_SOUNDTRACK;   // the boss rush (src/rush.c)
        title_items[title_n++] = K_MINIGAMES;
        title_items[title_n++] = K_BOSSRUSH;
        title_items[title_n++] = K_CREDITS;      // the credits roll (src/credits.c)
        break;
    case TM_ERASE:    // SETTINGS > ERASE DATA: "ERASE ALL DATA" (a label: the cursor skips it), NO, YES; the cursor starts on NO
        title_items[title_n++] = K_ERASEQ;
        title_items[title_n++] = K_NO;
        title_items[title_n++] = K_YES;
        break;
    case TM_HARD:     // PLAY > STORY (a new one): EASY, NORMAL, HARD, each with its caption on the row below (menu_frame); the cursor starts on NORMAL
        title_items[title_n++] = K_EASY;
        title_items[title_n++] = K_NORMAL;
        title_items[title_n++] = K_HARD;
        break;
    default:
        title_items[title_n++] = K_MUSIC;
        title_items[title_n++] = K_BARCHANGE + (level_dirs >> 7);   // (two items, K_BARKEEP follows: the line's wording is its item)
        title_items[title_n++] = K_ERASE;
        if (debug_unlocked()) title_items[title_n++] = K_DEBUG;     // (the debug menu, once unlocked: src/debug.c)
    }
    for (i = 0; i < title_n; i++) {
        title_rows[i] = m == TM_HARD ? HARD_ROW + 3 * i : MENU_ROW(title_n) + 2 * i;
        title_dirty |= (uint16_t)1 << title_rows[i] | (m == TM_HARD ? (uint16_t)2 << title_rows[i] : 0);
        build_item(i);
    }
    title_sel = sel;
}

// the redraw: dirty rows, each the line that is on it now (or blank), at most MENU_COPIES_PER_FRAME 20-byte copies a
// frame (the VBlank drain's budget: as much as a cursor move's two attribute rows). CGB: a line's row also gets its
// attributes; a blank row does not need them (the blank tile is colour 0, the wall, in either text palette).
// Returns the copies queued.
static uint8_t menu_frame(void) {
    uint8_t r, i, n = 0, need, k;
    for (r = MENU_FIRST_ROW; r < MENU_LAST_ROW + 1 && title_dirty; r++) {
        if (!(title_dirty & ((uint16_t)1 << r))) continue;
        k = 255;
        for (i = 0; i < title_n; i++) if (title_rows[i] == r) k = i;
        if (k == 255 && title_menu == TM_HARD && (r - HARD_ROW) % 3 == 1) {      // the prompt's caption: one a frame (they share menu_buf[3])
            if (n) continue;
            title_dirty &= ~((uint16_t)1 << r);
            build_row(menu_buf[3], k_text[title_items[(r - HARD_ROW) / 3] + 3]);
            vq_add(0, menu_buf[3], 0, r, 20);
            if (is_cgb) vq_add(1, attr_txt, 0, r, 20);
            n = MENU_COPIES_PER_FRAME;
            continue;
        }
        need = (is_cgb && k != 255) ? 2 : 1;
        if (n + need > MENU_COPIES_PER_FRAME) continue;          // next frame (a cheaper row may still fit)
        title_dirty &= ~((uint16_t)1 << r);
        n += need;
        vq_add(0, k == 255 ? row_blank : menu_buf[k], 0, r, 20);
        if (need == 2) vq_add(1, k == title_sel ? attr_sel : attr_txt, 0, r, 20);
    }
    return n;
}

// the HI line's table: in PLAY the one of the mode under the cursor (CONTINUE: STORY), elsewhere ARCADE's
static uint8_t hi_want(void) {
    uint8_t k = title_items[title_sel];
    if (title_menu != TM_PLAY) return MODE_ARCADE;
    return k == K_ARCADE ? MODE_ARCADE : k == K_CLASSIC ? MODE_CLASSIC : MODE_STORY;
}

// the HI line's digits for table title_hi (hi_buf; hi_score / hi_digits: save.c hi_pick)
static void hi_build(void) {
    uint8_t i;
    hi_pick(title_hi);
    for (i = 0; i < 6; i++) hi_buf[i] = tt_digit[hi_digits[i]];
}

void title_music_toggle(void) BANKED {
    uint8_t i;
    music_set_on(!sound_on);
    for (i = 0; i < title_n; i++)
        if (title_items[i] == K_MUSIC) { build_item(i); title_dirty |= (uint16_t)1 << title_rows[i]; }
}

// SETTINGS > BAR CHANGE (A, START, LEFT or RIGHT on its line): SNAP <-> KEEP (level_dirs bit 7), kept in the save; CLASSIC snaps whatever it says
static void bar_mode_toggle(void) {
    level_dirs ^= KEEP_POS;
    title_items[title_sel] ^= K_BARCHANGE ^ K_BARKEEP;
    build_item(title_sel); title_dirty |= (uint16_t)1 << title_rows[title_sel];
    bar_mode_save();
}

static void logo_put(uint8_t i) {               // letter i's current state into its buffer (LCD off: straight to VRAM)
    const uint8_t *q = tt_logo[tt_word[i]][logo_state[i]];
    logo_buf[i][0] = q[0]; logo_buf[i][1] = q[1]; logo_buf[i][2] = q[2]; logo_buf[i][3] = q[3];
}

void title_enter(void) BANKED {
    uint8_t i, r;
    palette_t p;
    DISPLAY_OFF;
    TUNE_FLUSH();                                     // (a tune unlock heard in the story and not saved yet: a quit, a game over)
    music_pump();                                     // (the tick this pass is due: the load below runs several frames)
    overlay_on = 0; HIDE_WIN; vq_reset(); hud_dirty = 0;
    music_fast = 0;                                   // (the jukebox plays every tune at its own pace)
    music_play(TUNE_TITLE);                           // (before the long load: its patterns, if a game or the soundtrack player
    music_load_now();                                 // overwrote them, are copied at once and the pumps below tick the tune)
    music_pump();
    hide_all_sprites();
    mirror_load(0); level_dirs &= KEEP_POS;                   // every bar L (the scene's bartender; P3: CLASSIC may mirror bars)
    if (!is_cgb) OBP1_REG = OBP1_MENU;               // (play used OBP1_PLAY)
    // (music_pump between the steps: this load takes several frames and the title tune plays on through it)
    bkg_data_far(TILE_GENERIC_BASE, GENERIC_TILE_COUNT, bar_tiles, BANK(art_tiles));
    music_pump();
    load_venue(0);                                    // the title stands in the saloon (and its drink frames)
    music_pump();
    set_bkg_data(BAR_TILE_COUNT, TITLE_TILE_COUNT, title_tiles);   // lettering over the patron ids; the level load puts them back
    music_pump();
    for (i = 0; i < TT_EXTRA_COUNT; i += 14) {        // (2 KB: in slices, the music ticking between them)
        set_bkg_data(TT_EXTRA_BASE + i, TT_EXTRA_COUNT - i < 14 ? TT_EXTRA_COUNT - i : 14, tt_extra_tiles + i * 16);
        music_pump();
    }
    set_bkg_data(0, TT_LOW_COUNT, tt_low_tiles);
    music_pump();
    for (r = 0; r < 2; r++)                           // the patron: cowboys variant 0, unshifted, 2x2 of its 3x2 tiles
        for (i = 0; i < 2; i++)                       // (M13a: stored column by column, the shift-0 poses at PATRON_SHIFT0_OFS)
            bkg_data_far(TT_PATRON_BASE + r * 2 + i, 1, patron_tiles_cowboys + (PATRON_SHIFT0_OFS + i * 2 + r) * 16, BANK(patron_tiles_cowboys));
    set_sprite_data(OBJ_FX, TT_FX_TILES, tt_fx_tiles);
    music_pump();
    if (is_cgb) {
        p[0] = WALL_RGB_T; p[1] = RGB15(31, 30, 24); p[2] = RGB15(29, 19, 4); p[3] = RGB15(10, 3, 2);   // logo: foam, beer, outline
        set_bkg_palette(BGPAL_LOGO, 1, p);
        p[1] = RGB15(2, 3, 8); p[2] = RGB15(22, 19, 12); p[3] = RGB15(31, 29, 22);   // text: shadow, muted (HI), cream
        set_bkg_palette(BGPAL_TEXT, 1, p);
        p[3] = RGB15(31, 25, 6);                                                     // the selected item: gold
        set_bkg_palette(BGPAL_TEXT_SEL, 1, p);
        patron_pal_get(0, 0, p);
        p[0] = WALL_RGB_T;
        set_bkg_palette(BGPAL_TPATRON, 1, p);
        p[1] = RGB15(31, 31, 27); p[2] = RGB15(30, 20, 4); p[3] = RGB15(12, 5, 2);  // effects: foam, beer, dark
        set_sprite_palette(OBJPAL_FX, 1, p);
    }
    venue_backdrop(0, 16);                            // wall rows 0-15, counter row 16, floor 17 (tiles + attributes)
    music_pump();

    // logo: every letter empty
    for (i = 0; i < LOGO_LETTERS; i++) {
        logo_state[i] = 0;
        logo_put(i);
    }
    for (r = 0; r < 2; r++) {                         // (the logo's two rows, 18 tiles each: a call a letter ran the rebuild a tick late)
        for (i = 0; i < LOGO_LETTERS; i++) { row_buf[2 * i] = logo_buf[i][2 * r]; row_buf[2 * i + 1] = logo_buf[i][2 * r + 1]; }
        set_bkg_tiles(1, LOGO_ROW + r, 18, 1, row_buf);
    }
    // the menu block, rows 4-13: plain wall (the text's blank tile is colour 0, the wall colour; no specks), text centred
    for (i = 0; i < 20; i++) { row_blank[i] = TT_BLANK; attr_txt[i] = BGPAL_TEXT; attr_sel[i] = BGPAL_TEXT_SEL; }
    music_pump();
    save_lock = 0;                     // (a debug-select story run ends here: save.c)
    title_n = 0;
    menu_open(title_back, title_back_sel);   // the top level (or the submenu the soundtrack / the list was opened from)
    music_pump();
    title_back = TM_TOP; title_back_sel = 0;
    title_dirty = 0;                   // drawn here, with the LCD off
    for (r = LOGO_ROW + 2; r < BAR_TOP_ROW(SCENE_BAR); r++) {   // (the block's rows: a menu line, else the plain wall; a fourth line made the rebuild a tick late)
        for (i = 0; i < title_n && title_rows[i] != r; i++) ;
        set_bkg_tiles(0, r, 20, 1, i < title_n ? menu_buf[i] : row_blank);
    }
    music_pump();
    for (i = 0; i < 20; i++) row_buf[i] = TT_BLANK;
    row_buf[6] = TT_HI;
    title_hi = hi_want(); hi_build();
    for (i = 0; i < 6; i++) row_buf[8 + i] = hi_buf[i];
    row_buf[17] = tt_digit[VERSION_MAJOR]; row_buf[18] = TT_DOT; row_buf[19] = tt_digit[VERSION_MINOR];   // the version, top right (the Makefile's VERSION)
    set_bkg_tiles(0, ROW_HI, 20, 1, row_buf);
    music_pump();
    // the scene's patron
    row_buf[0] = (uint8_t)TT_PATRON_BASE; row_buf[1] = (uint8_t)(TT_PATRON_BASE + 1); row_buf[2] = (uint8_t)(TT_PATRON_BASE + 2); row_buf[3] = (uint8_t)(TT_PATRON_BASE + 3);
    set_bkg_tiles(PATRON_COL, BAR_TOP_ROW(SCENE_BAR), 2, 1, row_buf);
    set_bkg_tiles(PATRON_COL, BAR_TOP_ROW(SCENE_BAR) + 1, 2, 1, row_buf + 2);
    if (is_cgb) {
        VBK_REG = VBK_BANK_1;
        for (i = 0; i < 20; i++) row_buf[i] = BGPAL_LOGO;
        set_bkg_tiles(1, LOGO_ROW, 18, 1, row_buf); set_bkg_tiles(1, LOGO_ROW + 1, 18, 1, row_buf);
        for (i = 0; i < title_n; i++) set_bkg_tiles(0, title_rows[i], 20, 1, i == title_sel ? attr_sel : attr_txt);   // (the gold line is the cursor's: it may come back on line 1 or 2)
        set_bkg_tiles(0, ROW_HI, 20, 1, attr_txt);
        for (i = 0; i < 2; i++) row_buf[i] = BGPAL_TPATRON;
        set_bkg_tiles(PATRON_COL, BAR_TOP_ROW(SCENE_BAR), 2, 1, row_buf);
        set_bkg_tiles(PATRON_COL, BAR_TOP_ROW(SCENE_BAR) + 1, 2, 1, row_buf);
        VBK_REG = VBK_BANK_0;
    }
    title_t = 0; logo_done = 0; title_idle = 0;
    tscene_phase = SC_IDLE; tscene_timer = 0; tscene_mug_x = 0; tscene_loops = 0;
    bubble_y[0] = bubble_y[1] = 0; bubble_timer = 90;
    bar = SCENE_BAR; bartender_x = BT_X; bt_bob = 0; facing = 0; bartender_frame = BT_IDLE;
    game_state = GS_TITLE;
    music_pump();
    while (TIMA_REG < (TMA_REG & 0xFC) + 34) ;   // (the loop's tick, due as this pass ends, is refused until half a frame has passed since the pump's: wait that out here, LCD off, so the first title frame ticks)
    DISPLAY_ON;
}

// ---- the logo -------------------------------------------------------------------------------
// letters 0: a frame whose drain is already full (a cursor move's two rows, or two menu copies): the letters' new
// fill states wait a frame (they follow title_t, so they catch up on the next one)
static void logo_frame(uint8_t letters) {
    uint8_t i, s;
    int16_t d;
    OAM_item_t *o;
    if (logo_done) return;
    for (i = 0; letters && i < LOGO_LETTERS; i++) {
        d = (int16_t)title_t - LOGO_T0 - i * LOGO_STAGGER;
        if (d < 0) break;
        s = d >= (TT_LOGO_STATES - 1) * LOGO_STEP ? TT_LOGO_STATES - 1 : (uint16_t)(uint8_t)d / LOGO_STEP;
        if (s != logo_state[i]) {
            logo_state[i] = s;
            logo_put(i);
            vq_add(0, logo_buf[i], 1 + 2 * i, LOGO_ROW, 2);
            vq_add(0, logo_buf[i] + 2, 1 + 2 * i, LOGO_ROW + 1, 2);
        }
    }
    // drips under P, O and the second E as they fill up
    o = shadow_OAM + OAM_DRIP;
    o->y = 0;
    for (i = 1; i < LOGO_LETTERS; i += 3) {
        d = (int16_t)title_t - (LOGO_T0 + i * LOGO_STAGGER + (TT_LOGO_STATES - 2) * LOGO_STEP);
        if (d >= 0 && d < DRIP_LEN) {
            o->x = 8 + 16 * i + 3 + 8;                // under the letter's left stem (every letter has one)
            if (d < 8) { o->y = (LOGO_ROW + 2) * 8 - 3 + 16; o->tile = FX_DRIP; }
            else       { o->y = (LOGO_ROW + 2) * 8 - 4 + (uint8_t)d + 16; o->tile = FX_DRIP + 2; }
            o->prop = is_cgb ? OBJPAL_FX : 0;
        }
    }
    // one sparkle across the letters once they are all full
    o = shadow_OAM + OAM_SPARKLE;
    o->y = 0;
    if (title_t >= SPARKLE_T0) {
        d = (int16_t)title_t - SPARKLE_T0;
        i = (uint8_t)d / SPARKLE_EACH;
        if (i < LOGO_LETTERS) {
            s = (uint8_t)d % SPARKLE_EACH;
            o->y = LOGO_ROW * 8 - 2 + 16; o->x = 8 + 16 * i + 11 + 8;      // centred on the letter's top-right corner
            o->tile = (s && s < SPARKLE_EACH - 1) ? FX_SPARKLE + 2 : FX_SPARKLE;
            o->prop = is_cgb ? OBJPAL_FX : S_PALETTE;
        }
    }
    if (title_t >= LOGO_DONE_T) logo_done = 1;
}

// ---- bubbles: now and then one rises from below the logo to the top of the screen ----------------
static void bubbles_frame(void) {
    uint8_t i, y;
    OAM_item_t *o = shadow_OAM + OAM_BUBBLE;
    bubble_half ^= 1;
    if (title_t > LOGO_FILLED && !--bubble_timer) {
        bubble_timer = 50 + (trand() & 63);
        i = bubble_y[0] ? 1 : 0;
        if (!bubble_y[i]) {
            bubble_y[i] = (LOGO_ROW + 2) * 8 + 16;                  // OAM y: just under the logo
            bubble_x[i] = 12 + (trand() & 127) + 8;
        }
    }
    for (i = 0; i < 2; i++, o++) {
        y = bubble_y[i];
        if (y && bubble_half && !--y) y = 0;                        // 0.5 px per frame; gone above the screen
        if (y < 4) y = 0;
        bubble_y[i] = y;
        if (!y) { o->y = 0; continue; }
        o->y = y;
        o->x = bubble_x[i] + ((y >> 3) & 1);                        // a little wobble
        o->tile = y < LOGO_ROW * 8 + 16 ? FX_BUBBLE + 2 : FX_BUBBLE;
        o->prop = is_cgb ? OBJPAL_FX : S_PALETTE;
    }
}

// ---- the bar scene on the bottom counter -----------------------------------------------------------
// held-mug poses while the patron drinks: (frame of the drink art, dx from the patron, dy from the wall top)
static void scene_frame(void) {
    OAM_item_t *o = shadow_OAM + OAM_TMUG;
    uint8_t t = ++tscene_timer, full = is_cgb ? OBJPAL_MUG_FULL : 0, f;
    bartender_frame = BT_IDLE;
    o->y = 0;
    switch (tscene_phase) {
    case SC_IDLE:
        if (t >= SC_IDLE_FRAMES) { tscene_phase = SC_SLIDE; tscene_timer = 0; tscene_mug_x = LAUNCH_X; }
        break;
    case SC_SLIDE:                                  // the full mug slides left, 2 px per frame
        if (t <= SC_SLIDE_POSE) bartender_frame = BT_SLIDE;
        tscene_mug_x -= 2;
        o->y = (uint8_t)(SCENE_TOP_Y + MUG_DY); o->x = tscene_mug_x + 8; o->tile = OBJ_MUG; o->prop = S_PALETTE | OBJPAL_MUG_FULL;
        if (tscene_mug_x <= CATCH_X) { tscene_phase = SC_DRINK; tscene_timer = 0; }
        break;
    case SC_DRINK:                                  // at the hand, up to the mouth, tilted
        f = t < 12 ? 0 : t < 40 ? 1 : 2;
        o->y = SCENE_TOP_Y + (f ? 1 : 5); o->x = PATRON_PX + (f ? 8 : 9) + 8;
        o->tile = OBJ_MUG_DRINK + f * 2; o->prop = full;
        tscene_mug_x = PATRON_PX + 8;
        if (t >= SC_DRINK_FRAMES) { tscene_phase = SC_WINDUP; tscene_timer = 0; }
        break;
    case SC_WINDUP:                                 // the empty lowered, drawn back, swung forward
        f = t < 8 ? 8 - (t >> 1) : t < 18 ? 4 : 14;
        o->y = (uint8_t)(SCENE_TOP_Y + 6); o->x = PATRON_PX + f + 8;
        o->tile = OBJ_MUG_DRINK + 3 * 2; o->prop = S_PALETTE | OBJPAL_MUG_EMPTY;
        if (t >= SC_WINDUP_FRAMES) { tscene_phase = SC_RETURN; tscene_timer = 0; tscene_mug_x = CATCH_X; }
        break;
    case SC_RETURN:                                 // the empty slides back, 1 px per frame
        tscene_mug_x++;
        o->y = (uint8_t)(SCENE_TOP_Y + MUG_DY); o->x = tscene_mug_x + 8; o->tile = OBJ_MUG + 2; o->prop = S_PALETTE | OBJPAL_MUG_EMPTY;
        if (tscene_mug_x >= LAUNCH_X) { tscene_phase = SC_CATCH; tscene_timer = 0; }
        break;
    case SC_CATCH:
        bartender_frame = BT_CATCH;
        if (t >= SC_CATCH_FRAMES) { tscene_phase = SC_IDLE; tscene_timer = 0; tscene_loops++; }
        break;
    }
    draw_bartender();
}

// ---- the menu ---------------------------------------------------------------------------------
static void cursor_frame(void) {
    OAM_item_t *o = shadow_OAM + OAM_CURSOR;
    o->y = title_rows[title_sel] * 8 - 7 + 16;
    o->x = text_left(title_sel) - 13 - ((title_t >> 4) & 1) + 8;
    o->tile = OBJ_MUG; o->prop = is_cgb ? OBJPAL_MUG_FULL : 0;     // DMG: OBP0 like the held mug (shows on the white wall)
}

// One title frame. 2: no key for TITLE_IDLE_FRAMES (the table).
// ARCADE (and the test hook title_go) start a game, STORY / CONTINUE the story mode from here (src/story.c), SOUNDTRACK the soundtrack player (src/jukebox.c): the
// screen changes, 0 is returned. A top-level item opens its submenu; B in a submenu goes back to the top level.
uint8_t title_update(uint8_t pressed) BANKED {
    uint8_t old = title_sel, last = title_n - 1, full = 1;
    if (title_go) {
        old = title_go; title_go = 0;
        play_mode = old & 0x80 ? MODE_CLASSIC : MODE_LEVEL;
        start_new_game(old & 0x7F);
        return 0;
    }
    title_t++;
    if (pressed) {
        title_idle = 0;
        title_back_sel = konami_step(title_back_sel, pressed);   // the debug unlock's trigger (src/debug.c konami_step: the one place to change it)
        if (title_back_sel == KONAMI_DONE) {
            title_back_sel = 0;
            pressed &= ~J_A;                         // (the code's last A is not a menu choice)
            if (!debug_unlocked()) {
                debug_unlock();
                SFX(SFX_EXTRA);                      // (the code's B left any submenu: SETTINGS lists DEBUG MENU when it is opened next)
            }
        }
        if ((pressed & (J_LEFT | J_RIGHT)) && IS_BAR(title_items[title_sel])) bar_mode_toggle();
    }
    else if (++title_idle >= TITLE_IDLE_FRAMES) {    // the attract: the next of the three tables
        score_tbl = attract_tbl[attract_n];
        if (++attract_n == TOP_TABLES) attract_n = 0;
        return 2;
    }
    if (pressed & J_SELECT) title_music_toggle();
    if (pressed & J_UP) title_sel = title_sel ? title_sel - 1 : last;
    else if (pressed & J_DOWN) title_sel = title_sel == last ? 0 : title_sel + 1;
    if (title_items[title_sel] == K_ERASEQ) title_sel = (pressed & J_UP) ? last : 1;   // (a prompt's label is no choice)
    if (title_sel != old) { set_sel_attr(old, 0); set_sel_attr(title_sel, 1); }
    else if (pressed & (J_A | J_START)) {
        switch (title_items[title_sel]) {
        case K_ARCADE: arcade_begin(); return 0;
        case K_CLASSIC: play_mode = MODE_CLASSIC; start_new_game(1); return 0;   // CLASSIC's level 1 (classic.c)
        case K_STORY: menu_open(TM_HARD, 1); break;                            // (a new story asks "HOW HARD", the cursor on NORMAL; CONTINUE does not: the save holds it)
        case K_EASY: story_begin(DIFF_EASY << 1); return 0;
        case K_NORMAL: story_begin(DIFF_NORMAL << 1); return 0;
        case K_HARD: story_begin(DIFF_HARD << 1); return 0;
        case K_CONTINUE: story_begin(1); return 0;
        case K_SOUNDTRACK: title_back = TM_BONUS; jukebox_enter(); return 0;   // (B there comes back to BONUS)
        case K_MINIGAMES: mg_list_enter(); return 0;                           // (its B: BONUS, on MINI GAMES)
        case K_CREDITS: credits_enter(0); return 0;                            // (its end / B: BONUS, on CREDITS)
        case K_BOSSRUSH: rush_enter(); return 0;                               // (its B: BONUS, on BOSS RUSH)
        case K_PLAY: menu_open(TM_PLAY, 0); break;
        case K_BONUS: menu_open(TM_BONUS, 0); break;
        case K_SETTINGS: menu_open(TM_SETTINGS, 0); break;
        case K_ERASE: menu_open(TM_ERASE, 1); break;                           // ("ERASE ALL DATA", the cursor on NO)
        case K_NO: menu_open(TM_SETTINGS, 2); break;
        case K_YES: save_erase(); title_hi = 0xFF; menu_open(TM_TOP, 2); break;   // a blank cartridge; the title again (the HI line follows on a quiet frame)
        case K_DEBUG: debug_open(); return 0;                                  // (full-screen over the title; B closes it)
        default: if (IS_BAR(title_items[title_sel])) bar_mode_toggle(); else title_music_toggle();
        }
    } else if ((pressed & J_B) && title_menu != TM_TOP) {
        if (title_menu == TM_ERASE) menu_open(TM_SETTINGS, 2);
        else if (title_menu == TM_HARD) menu_open(TM_PLAY, (story_progress || story_reached) && story_progress < STORY_CHAPTERS);   // (STORY's line: after CONTINUE when it is shown)
        else menu_open(TM_TOP, title_menu - 1);
    }
    if (title_sel == old) {                        // (a cursor move already queued its two attribute rows)
        full = menu_frame() == MENU_COPIES_PER_FRAME;
        if (!title_dirty && hi_want() != title_hi) {   // a quiet frame: the HI line follows the cursor's mode
            title_hi = hi_want(); hi_build();
            vq_add(0, hi_buf, 8, ROW_HI, 6);
        }
    }
    logo_frame(!full);
    bubbles_frame();
    scene_frame();
    cursor_frame();
    return 0;
}
