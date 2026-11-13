// The title's BONUS > BOSS RUSH (owner 2026-10-12: "a boss rush mode in the BONUS section, that can be unlockable, but
// will also help us in play testing the bosses. Options: play all, or choose a boss").
//
// Screens (the MINI GAMES list's style: light HUD glyphs and the story font's punctuation on the dark band, the HUD
// palette; row 0 the title, row 1 a panel line, rows 13-16 the details between panel lines 12 and 17; the list is the one-line style), all run as
// GS_STORY with story_phase STORY_PHASE_RUSH (story_update hands the frame here: no ROM0 case):
//   MENU    ALL / CHOOSE (rows 4 / 6, the mug cursor). ALL needs 2 bosses unlocked ("ALL LOCKED" and A does nothing
//           until then). B: the title's BONUS submenu, the cursor on BOSS RUSH.
//   LIST    (CHOOSE) every built boss in chapter order, in the one-line style of src/oneline.h: "< BOSS NAME >" on the selection line, his fight sprite
//           centred in a window under it, his venue and "BEST m:ss" (a boss not unlocked: a silhouette on Color, "??" on a DMG, "LOCKED"; A does
//           nothing). LEFT / RIGHT one boss (wrapping, hold-to-repeat), UP / DOWN five. B: the menu, on CHOOSE.
//   NEXT    (ALL) before each fight: FIGHT n OF m, NEXT: <BOSS>, his venue, the lives, score and time so far; A / START
//           or NEXT_FRAMES and the fight starts.
//   RESULT  YOU WIN / YOU LOSE (CHOOSE) or ALL CLEAR / GAME OVER (ALL), the time, the score, the best (NEW BEST);
//           A RETRY (the same boss, or ALL from the first), B BACK (the list on that boss, or the menu on ALL).
// A fight (story.c rush_fight) is the venue's boss step exactly as the story plays it (his banner, the regulars, the
// perfect pour, the HUD meter; a lost life restarts him with his damage kept) with MODE_RUSH: no story progress, no
// tune unlocks (save_lock 1), no top 5, no extra lives by score. CHOOSE: 3 lives, the score from 0. ALL: 3 lives at
// the start, carried from fight to fight; a won fight gives one back (+1, never above START_LIVES: with three lives
// for up to ten bosses a run would otherwise end at the third or fourth boss for a strong player, and a refill to 3
// would take the rush's edge away), the score totalled. Lives out: GAME OVER over the frozen fight (story.c), then the
// result. The time is the fights' PLAYING frames (the banners, freezes and outros not counted).
//
// Which bosses: the built ones, read from the same data the story plays (build/story.h's step table: a chapter whose
// boss step is not STEP_SKIP, i.e. tools/gen_story.py BUILT_SLOTS["BOSS"]), so a boss added later appears here with
// no edit to this file. Unlocked: beaten in STORY or ARCADE (save.c boss_beaten; a debug-select run records nothing).
// The DEBUG_MENU build (`make`) lists every built boss unlocked (for play testing); `make release` the real rule.
// Saved (save.c, the Practice block's rush part; written only by a won fight or a finished run): each boss's fastest
// rush win (CHOOSE or a fight of ALL), ALL's best score with that run's time and bosses beaten.
#pragma bank 255
#include <gb/gb.h>
#include <stdint.h>

#include "game.h"
#include "music.h"
#include "story.h"
#include "boss.h"
#include "rush.h"
#include "oneline.h"
#include "rush_portraits.h"   // static const uint8_t rush_body[], rush_quest[], uint16_t rush_colour[]: the list's window tiles (tools/gen_rush_portraits.py)
#include <gb/cgb.h>

extern uint8_t overlay_on, score_digits[6], story_phase, joy;
extern uint32_t score;
#if RUSH_TOP != STORY_SCRATCH - BOSS_SCRATCH_N
#error "rush.h RUSH_TOP must be where boss.h's BOSS_SCRATCH starts"
#endif

#define RGB15(r, g, b) ((uint16_t)((r) | ((g) << 5) | ((b) << 10)))

#define ROW_HEAD        0
#define ROW_BOX        12       // the menu's panel; the info lines 13-16; panel 17
#define INFO_LINES      4
#define MENU_ROW0       4       // the menu's lines: rows 4 and 6, the text at column 7
#define MENU_COL        7
#define NEXT_FRAMES   180       // the NEXT card stays 3 s (or until A / START)
#define ROW(k)        (story_scratch + (uint8_t)(k) * 20)   // row buffer k of the menu or the list
#define T_MAX      0xFFFFu

#define ROWS_PER_FRAME  2       // menu rows built and queued a frame (~15k cycles each: a quick scroll with 4 ran the frame past its VBlank)
// The ten planned bosses by venue (docs/minigames_bosses.md section 3; the list shows only the built ones)
static const char *const boss_name[BOSS_COUNT] = {
    "BIG TEX", "THE MASCOT", "SASQUATCH", "THE CRITIC", "THE YETI", "PROTOTYPE", "DUKE", "SUMO CHAMP",
    "LEO THE LION", "MOTHERSHIP",
};
static const char *const venue_name[BOSS_COUNT] = {
    "THE SALOON", "THE STADIUM", "THE LUMBER LODGE", "THE BISTRO", "THE IGLOO", "THE ROBOT FACTORY",
    "THE CHROME COW", "THE TEAHOUSE", "THE JUNGLE ZOO", "THE SPACE LOUNGE",
};
static const char locked_name[] = "? ? ?";
// ---- the bosses -------------------------------------------------------------------------------------------------
static uint8_t built(uint8_t v) {                // (the mask: rush_enter; a table, not a 16-bit shift: the list asks a dozen times a frame)
    static const uint8_t bit[8] = { 1, 2, 4, 8, 16, 32, 64, 128 };
    return ((v < 8 ? (uint8_t)RUSH->built : (uint8_t)(RUSH->built >> 8)) & bit[v & 7]) != 0;
}

static uint8_t scan_built(uint8_t v) {           // venue v's boss fight is built (it follows Last call: build/story.h BOSS_BUILT_MASK)
    return (BOSS_BUILT_MASK >> v) & 1;
}

static uint8_t unlocked(uint8_t v) {
    if (!built(v)) return 0;
#ifdef DEBUG_MENU
    return 1;
#else
    return (((uint16_t)RUSH->save[RSV_BITS] | ((uint16_t)RUSH->save[RSV_BITS + 1] << 8)) >> v) & 1;
#endif
}

static uint8_t nth_built(uint8_t k) {            // the venue of the list's line k (BOSS_COUNT: none)
    uint8_t v;
    for (v = 0; v < BOSS_COUNT; v++) if (built(v) && !k--) return v;
    return BOSS_COUNT;
}

static uint8_t lines(void) { return RUSH->nlines; }   // the list's lines (the built bosses, counted once in rush_enter)

static uint8_t count_unlocked(void) {
    uint8_t v, n = 0;
    for (v = 0; v < BOSS_COUNT; v++) n += unlocked(v);
    return n;
}

static uint8_t next_unlocked(uint8_t v) {        // the first unlocked boss from venue v (BOSS_COUNT: none)
    for (; v < BOSS_COUNT; v++) if (unlocked(v)) return v;
    return BOSS_COUNT;
}

static uint16_t get16(uint8_t i) { return RUSH->save[i] | ((uint16_t)RUSH->save[i + 1] << 8); }
static void put16(uint8_t i, uint16_t v) { RUSH->save[i] = (uint8_t)v; RUSH->save[i + 1] = (uint8_t)(v >> 8); }
static uint32_t all_score(void) {
    return RUSH->save[RSV_ALL_SCORE] | ((uint32_t)RUSH->save[RSV_ALL_SCORE + 1] << 8)
         | ((uint32_t)RUSH->save[RSV_ALL_SCORE + 2] << 16);
}

static char *cat(char *d, const char *s) {       // append s at d (WRAM), return the end
    while (*s) *d++ = *s++;
    *d = 0;
    return d;
}

static char *num(char *d, uint8_t v) {            // v (0..99) without leading zero
    if (v >= 10) { *d++ = '0' + v / 10; v %= 10; }
    *d++ = '0' + v;
    *d = 0;
    return d;
}

static char *mmss(char *d, uint16_t f) {         // frames as M:SS (16 bits of frames: at most 18:12)
    uint16_t s = f / 60;
    d = num(d, (uint8_t)(s / 60));
    s %= 60;
    *d++ = ':';
    *d++ = '0' + (uint8_t)s / 10; *d++ = '0' + (uint8_t)s % 10;
    *d = 0;
    return d;
}

static char *six(char *d, uint32_t v) {          // a score's six digits
    uint8_t g[6], i;
    split6(g, v);
    for (i = 0; i < 6; i++) *d++ = '0' + g[i];
    *d = 0;
    return d;
}

static void line_at(uint8_t y, uint8_t x, const char *s) {  // LCD off: a text row
    ol_blank(row_buf);
    ol_put(row_buf, x, s);
    set_bkg_tiles(0, y, 20, 1, row_buf);
    music_pump();                                // (a screen's build is several frames: the tune ticks on)
}

static void frame_begin(uint8_t scr) {           // LCD off: a blank band with the title, its panels, HUD attributes
    TRANS_MENU();                                // (src/trans.c: the quick white fade between the menu, the list and the result)
    DISPLAY_OFF;
    if (scr != RS_NEXT) {                        // the menu, the list and the result play the title tune (left alone when it
        music_play(TUNE_TITLE);                  // already plays; after a fight its patterns are copied back now and the
        music_load_now();                        // pumps below tick it through the rebuild)
    }
    music_pump();
    RUSH->scr = scr;
    overlay_on = 0; HIDE_WIN; LYC_REG = BANNER_LYC;
    vq_reset(); hud_dirty = 0; vram_pending = 0; life_lost = 0;
    clear_dirty();
    clear_patrons(); clear_mugs();
    tip_timer = 0; show_timer = 0;
    hide_all_sprites();
    story_on = 0;                                // (the rush's screens are not a story; a fight sets it again)
    story_font_load();                           // the punctuation (over the patron range: a fight's load puts it back)
    music_pump();
    list_frame(scr == RS_LIST ? OL_SEP : ROW_BOX);   // (the wood wall, src/mg_list.c: the header band, the panel)
    music_pump();
    line_at(ROW_HEAD, 255, "BOSS RUSH");
    RUSH->t = 0; RUSH->dirty = 0;
    story_phase = STORY_PHASE_RUSH;
    game_state = GS_STORY;
}

static void run_start(uint8_t mode);
static void list_open(void);

// ---- MENU: ALL / CHOOSE with the mug cursor, the details below ----------------------------------------------------------
#define MENU_LINES      2

static void build_menu(uint8_t k, uint8_t *r) {
    char b[20], *d;
    uint8_t all_ok = count_unlocked() >= 2;
    ol_blank(r);
    if (k < MENU_LINES) {
        ol_put(r, MENU_COL, k ? "CHOOSE" : "ALL");
        if (!k && !all_ok) ol_put(r, MENU_COL + 4, "LOCKED");
        return;
    }
    k -= MENU_LINES;
    if (RUSH->sel) {                             // CHOOSE
        static const char *const ci[INFO_LINES] = { "ONE BOSS ALONE", "3 LIVES", "", "A PICK  B BACK" };
        ol_put(r, 255, ci[k]);
        return;
    }
    if (!all_ok) {
        static const char *const li[INFO_LINES] = { "LOCKED", "BEAT 2 BOSSES IN", "STORY OR ARCADE", "B BACK" };
        ol_put(r, 255, li[k]);
        return;
    }
    switch (k) {
    case 0: ol_put(r, 255, "EVERY BOSS IN A ROW"); break;
    case 1:
        if (!all_score()) { ol_put(r, 255, "NO BEST YET"); break; }
        d = cat(b, "BEST ");
        six(d, all_score());
        ol_put(r, 255, b);
        break;
    case 2:
        if (!all_score()) break;
        d = num(b, RUSH->save[RSV_ALL_N]);
        d = cat(d, RUSH->save[RSV_ALL_N] == 1 ? " BOSS " : " BOSSES ");
        mmss(d, get16(RSV_ALL_TIME));
        ol_put(r, 255, b);
        break;
    default: ol_put(r, 255, "A PLAY  B BACK");
    }
}

static uint8_t menu_row(uint8_t k) {             // the screen row of the menu's row buffer k
    return k < MENU_LINES ? MENU_ROW0 + 2 * k : ROW_BOX + 1 + k - MENU_LINES;
}

static void cursor(void) {
    OAM_item_t *o = shadow_OAM;
    o->y = menu_row(RUSH->sel) * 8 - 7 + 16;     // the mug stands on the line (as the title's cursor)
    o->x = (MENU_COL - 1) * 8 + 8;
    o->tile = OBJ_MUG; o->prop = is_cgb ? OBJPAL_MUG_FULL : 0;
}

static void menu_open(uint8_t s) {               // LCD off
    uint8_t k;
    RUSH->sel = s;
    frame_begin(RS_MENU);
    mug_cursor_load();                           // (a fight borrowed the mug's tiles and palettes)
    music_pump();
    for (k = 0; k < MENU_LINES + INFO_LINES; k++) {
        build_menu(k, ROW(k));
        set_bkg_tiles(0, menu_row(k), 20, 1, ROW(k));
        if (!(k & 3)) music_pump();
    }
    cursor();
    DISPLAY_ON;
}

// ---- LIST: one boss at a time in the one-line style (src/oneline.h) ---------------------------------------------------------
// Rows (row buffer k and its screen row): 0 the selection line (3), 1 the header with the counter (0), 2-7 the window (6-11), 8 his venue (12), 9 his best time or
// LOCKED (13), 10 the hint row (16). The window is 8 x 6 tiles: a border, six columns and four rows of backdrop inside, a border; the picture is his fight sprite
// (pose 0), 12 BG tiles (6 columns x 2 rows) for each built boss, ids RL_T0 up (tile_base), loaded once when the screen opens. They are made at build time
// (tools/gen_rush_portraits.py, build/rush_portraits.h): his body shifted right by whole pixels so that the middle of what is DRAWN falls on the middle of the
// window, on the window's two middle rows, which his 16 rows fill (all ten land within half a pixel, both ways).
// Moving to another boss streams nothing: the window's two body rows go through the VBlank queue and the one CGB palette (BG 1: the backdrop and his three
// colours) is written the frame after, when the rows are on screen. A boss not unlocked: on Color the same tiles in one dark colour (a silhouette); on a DMG
// his slot holds a "??" (the story font's question mark, centred the same way).
#define RL_K_NAME       0
#define RL_K_HEAD       1
#define RL_K_WIN        2        // 2-7
#define RL_K_VENUE      8
#define RL_K_BEST       9
#define RL_K_HINT       10
#define RL_ROWS         11
#define RL_WIN_COL      6
#define RL_WIN_ROW      6
#define RL_WIN_W        8
#define RL_WIN_H        6
#define RL_BODY         2        // the window row (0-5) of the body's upper tile row; the lower one is the next
#define RL_COLS         6        // the backdrop's width in tiles
#define RL_TILES        (RL_COLS * 2)
#define RL_T0           136      // BG ids of the portraits, RL_TILES for each built boss: 136-255 for ten
#ifdef RUSHPIC_A                 // PROPOSAL A (docs/dev/concepts/rush_portraits_2026-11-13): the whole figure, content-packed tiles + a map a boss
#define RL_PIC_MASK     (15 << (RL_K_WIN + 1))   // the window's four backdrop rows (window rows 1-4) are the picture's
#endif
#define RL_NONE         0xFF
#define RL_PER_FRAME    2        // rows built and queued a frame (a row is ~10k cycles: three ran the frame past its VBlank when mashed)
#define LIST_JUMP       5        // UP / DOWN: this many bosses
#define RL_BACK         RGB15(27, 22, 14)
#define RL_SILHOUETTE   RGB15(3, 1, 1)
#define RL_PAL          1        // the window's BG palette (the wall look uses 2-7)
#ifdef RUSHPIC_A
typedef char rl_fits[(RL_T0 + RUSH_TILE_N <= 256 && RUSH_PORTRAITS == BOSS_COUNT && RUSH_MAP_W == 4 * RL_COLS) ? 1 : -1];
#else
typedef char rl_fits[(RL_T0 + RL_TILES * BOSS_COUNT <= 256 && RUSH_PORTRAITS == BOSS_COUNT) ? 1 : -1];

static uint8_t tile_base(uint8_t v) {            // the first of boss v's window tiles
    uint8_t u, n = 0;
    for (u = 0; u < v; u++) n += built(u);
    return RL_T0 + RL_TILES * n;
}
#endif

static void list_pal(uint8_t v) {                // CGB BG palette RL_PAL: the backdrop and his three colours (a silhouette when locked)
    uint16_t p[4];
    uint8_t i;
    if (!is_cgb) return;
    p[0] = RL_BACK;
    for (i = 0; i < 3; i++) p[1 + i] = unlocked(v) ? rush_colour[3 * v + i] : RL_SILHOUETTE;
    set_bkg_palette(RL_PAL, 1, p);
}

#ifdef RUSHPIC_A
static void list_pic(uint8_t k, uint8_t v) {     // PROPOSAL A: picture row k (window rows 1-4): the 6 backdrop tiles from his map (0: the plain backdrop)
    const uint8_t *m = rush_map + RUSH_MAP_W * (is_cgb || unlocked(v) ? v : RUSH_PORTRAITS) + RL_COLS * (k - RL_K_WIN - 1);
    uint8_t *r = ROW(k) + RL_WIN_COL + 1, i;
    for (i = 0; i < RL_COLS; i++) r[i] = m[i] ? RL_T0 - 1 + m[i] : OL_T_BACK;
}
#endif

static void list_build(uint8_t k, uint8_t v) {   // row buffer k for the selected boss, whose venue is v
    uint8_t *r = ROW(k), ok = unlocked(v), br, i, t;
    char b[22];
    uint16_t f;
    ol_blank(r);
    if (v >= BOSS_COUNT) return;
    f = get16(RSV_BEST + 2 * v);
    switch (k) {
    case RL_K_NAME: ol_arrows(r); ol_put(r, 255, ok ? boss_name[v] : locked_name); return;
    case RL_K_HEAD:
        ol_put(r, 1, "BOSS RUSH");
        ol_counter(b, RUSH->list_sel + 1, lines());
        ol_put(r, 254, b);
        return;
    case RL_K_HINT: ol_hint(r, ok ? OL_A_PLAY : OL_A_NONE); return;
    case RL_K_VENUE: ol_put(r, 255, ok ? venue_name[v] : "LOCKED"); return;
    case RL_K_BEST:
        if (!ok) ol_put(r, 255, "STORY OR ARCADE");
        else if (!f) ol_put(r, 255, "BEST --:--");
        else { mmss(cat(b, "BEST "), f); ol_put(r, 255, b); }
        return;
    }
    br = k - RL_K_WIN;                           // a row of the window
    r[RL_WIN_COL] = br == 0 ? OL_T_BOX : br == RL_WIN_H - 1 ? OL_T_BOX + 5 : OL_T_BOX + 3;
    r[RL_WIN_COL + RL_WIN_W - 1] = br == 0 ? OL_T_BOX + 2 : br == RL_WIN_H - 1 ? OL_T_BOX + 7 : OL_T_BOX + 4;
    for (i = 1; i <= RL_COLS; i++) r[RL_WIN_COL + i] = br == 0 ? OL_T_BOX + 1 : br == RL_WIN_H - 1 ? OL_T_BOX + 6 : OL_T_BACK;
#ifdef RUSHPIC_A
    if (br >= 1 && br <= RL_WIN_H - 2) list_pic(k, v);
#else
    if (br == RL_BODY || br == RL_BODY + 1) {
        t = tile_base(v);
        for (i = 0; i < RL_COLS; i++) r[RL_WIN_COL + 1 + i] = t + 2 * i + (br - RL_BODY);
    }
#endif
}

static uint8_t list_row(uint8_t k) {             // the screen row of the list's row buffer k
    switch (k) {
    case RL_K_NAME: return OL_ROW_BAND;
    case RL_K_HEAD: return 0;
    case RL_K_VENUE: return RL_WIN_ROW + RL_WIN_H;
    case RL_K_BEST: return RL_WIN_ROW + RL_WIN_H + 1;
    case RL_K_HINT: return OL_ROW_HINT;
    }
    return RL_WIN_ROW + (k - RL_K_WIN);
}

static void list_open(void) {                    // LCD off
    uint8_t k, v, i;
    frame_begin(RS_LIST);
    ol_load();
    ol_band(SKIN_PAL_BTN);
    music_pump();
#ifdef RUSHPIC_A
    for (k = 0; k < RUSH_TILE_N; k += 32) {      // every picture tile of every boss (and the "??"), once, packed by content
        set_bkg_data(RL_T0 + k, RUSH_TILE_N - k < 32 ? RUSH_TILE_N - k : 32, rush_tiles + 16 * (uint16_t)k);
        music_pump();
    }
#else
    for (v = 0; v < BOSS_COUNT; v++) {           // every built boss's window tiles, once (a locked boss on a DMG: the "??")
        if (!built(v)) continue;
        set_bkg_data(tile_base(v), RL_TILES, is_cgb || unlocked(v) ? rush_body + RL_TILES * 16 * v : rush_quest);
        music_pump();
    }
#endif
    if (RUSH->list_sel >= lines()) RUSH->list_sel = 0;
    RUSH->pal_for = RL_NONE;
    v = nth_built(RUSH->list_sel);
    for (k = 0; k < RL_ROWS; k++) {
        list_build(k, v);
        set_bkg_tiles(0, list_row(k), 20, 1, ROW(k));
        if (!(k & 3)) music_pump();
    }
    if (is_cgb) {                                // the window's backdrop and body in RL_PAL, the border and the rest the wall's
        list_pal(v);
        for (i = 0; i < 20; i++) row_buf[i] = i > RL_WIN_COL && i < RL_WIN_COL + RL_WIN_W - 1 ? RL_PAL : SKIN_PAL_WALL;
        VBK_REG = VBK_BANK_1;
        for (k = RL_WIN_ROW + 1; k < RL_WIN_ROW + RL_WIN_H - 1; k++) set_bkg_tiles(0, k, 20, 1, row_buf);
        VBK_REG = VBK_BANK_0;
    }
    DISPLAY_ON;
}

static uint8_t list_update(uint8_t pressed) {
    uint8_t n = lines(), s = RUSH->list_sel, old = s, key = ol_key(pressed, joy), k, q = 0, v;
    if (RUSH->pal_for != RL_NONE) { list_pal(RUSH->pal_for); RUSH->pal_for = RL_NONE; }   // (the body rows queued last frame are on screen now)
    if (key == J_LEFT) s = ol_wrap(s, n, -1);
    else if (key == J_RIGHT) s = ol_wrap(s, n, 1);
    else if (key == J_UP) s = ol_wrap(s, n, -LIST_JUMP);
    else if (key == J_DOWN) s = ol_wrap(s, n, LIST_JUMP);
    if (ol_tick()) RUSH->dirty |= 1 << RL_K_NAME;
    v = nth_built(s);
    if (s != old) {
        RUSH->list_sel = s;
#ifdef RUSHPIC_A
        RUSH->dirty |= (1 << RL_K_NAME) | (1 << RL_K_HEAD) | RL_PIC_MASK | (1 << RL_K_VENUE) | (1 << RL_K_BEST);
#else
        RUSH->dirty |= (1 << RL_K_NAME) | (1 << RL_K_HEAD) | (3 << (RL_K_WIN + RL_BODY)) | (1 << RL_K_VENUE) | (1 << RL_K_BEST);
#endif
        if (unlocked(v) != unlocked(nth_built(old))) RUSH->dirty |= 1 << RL_K_HINT;
    }
    if (pressed & (J_A | J_START)) {
        if (unlocked(v)) { run_start(RM_CHOOSE); return 1; }
    } else if (pressed & J_B) {
        menu_open(1);
        return 1;
    }
#ifdef RUSHPIC_A
    if (RUSH->dirty & RL_PIC_MASK) {             // his picture first, the four rows in one frame, the 6 tiles of each (the palette follows next frame)
        for (k = RL_K_WIN + 1; k <= RL_K_WIN + RL_WIN_H - 2; k++) {
            list_pic(k, v);
            vq_add(0, ROW(k) + RL_WIN_COL + 1, RL_WIN_COL + 1, list_row(k), RL_COLS);
        }
        RUSH->dirty &= ~RL_PIC_MASK;
        RUSH->pal_for = v;
        q = 2;
    }
#else
    if (RUSH->dirty & (3 << (RL_K_WIN + RL_BODY))) {   // his body first, both rows in one frame (the palette follows next frame)
        for (k = RL_K_WIN + RL_BODY; k <= RL_K_WIN + RL_BODY + 1; k++) { list_build(k, v); vq_add(0, ROW(k), 0, list_row(k), 20); }
        RUSH->dirty &= ~(3 << (RL_K_WIN + RL_BODY));
        RUSH->pal_for = v;
        q = 2;
    }
#endif
    for (k = 0; k < RL_ROWS && q < RL_PER_FRAME; k++) {
        if (!(RUSH->dirty & (1 << k))) continue;
        RUSH->dirty &= ~(1 << k);
        list_build(k, v);
        vq_add(0, ROW(k), 0, list_row(k), 20);
        q++;
    }
    return 0;
}

// From the title's BONUS submenu: the menu (LCD off)
void rush_enter(void) BANKED {
    uint8_t v;
    rush_load(RUSH->save);
    RUSH->built = 0;
    RUSH->nlines = 0;
    for (v = 0; v < BOSS_COUNT; v++) if (scan_built(v)) { RUSH->built |= (uint16_t)1 << v; RUSH->nlines++; }
    RUSH->list_sel = 0;
    menu_open(0);
}

// The pause menu's QUIT TO MENU in a fight (src/pause.c): back to the menu, nothing recorded (no time, no best)
void rush_quit(void) BANKED {
    boss_set(BOSS_NONE);
    menu_open(0);
}

// ---- a run ------------------------------------------------------------------------------------------------------
static void run_reset(void) {
    uint8_t i;
    score = 0;
    for (i = 0; i < 6; i++) score_digits[i] = 0;
    lives = START_LIVES;
    RUSH->won = 0; RUSH->total_t = 0; RUSH->result = 0; RUSH->best = 0;
}

static void fight(void) {                        // the fight with RUSH->boss (LCD off from here: story.c)
    RUSH->scr = RS_FIGHT; RUSH->fight_t = 0;
    rush_fight(RUSH->boss);
}

static void next_card(void) {                    // ALL: before fight RUSH->won + 1 (LCD off)
    char b[22], *d;
    uint8_t v = RUSH->boss;
    frame_begin(RS_NEXT);
    d = cat(b, "FIGHT ");
    d = num(d, RUSH->won + 1);
    d = cat(d, " OF ");
    num(d, RUSH->n);
    line_at(3, 255, b);
    d = cat(b, "NEXT: ");
    cat(d, boss_name[v]);
    line_at(6, 255, b);
    line_at(8, 255, venue_name[v]);
    d = cat(b, "LIVES ");
    num(d, lives);
    line_at(ROW_BOX + 1, 255, b);
    six(cat(b, "SCORE "), score);
    line_at(ROW_BOX + 2, 255, b);
    mmss(cat(b, "TIME "), RUSH->total_t);
    line_at(ROW_BOX + 3, 255, b);
    line_at(ROW_BOX + 4, 255, "A GO");
    DISPLAY_ON;
}

static void run_start(uint8_t mode) {            // A on ALL (or RETRY): 3 lives, the score from 0, the first fight
    RUSH->mode = mode;
    run_reset();
    if (mode == RM_ALL) {
        RUSH->n = count_unlocked();
        RUSH->boss = next_unlocked(0);
        next_card();
    } else {
        RUSH->n = 1;
        RUSH->boss = nth_built(RUSH->list_sel);
        fight();
    }
}

static void result_show(void) {                  // LCD off: the run's result
    char b[22], *d;
    uint8_t all = RUSH->mode == RM_ALL;
    uint16_t f = all ? RUSH->total_t : RUSH->fight_t;
    frame_begin(RS_RESULT);
    line_at(3, 255, all ? (RUSH->result ? "ALL CLEAR" : "GAME OVER") : (RUSH->result ? "YOU WIN" : "YOU LOSE"));
    if (all) {
        d = num(b, RUSH->won);
        d = cat(d, " OF ");
        d = num(d, RUSH->n);
        cat(d, " BOSSES");
        line_at(5, 255, b);
    } else line_at(5, 255, boss_name[RUSH->boss]);
    mmss(cat(b, "TIME "), f);
    line_at(7, 255, b);
    six(cat(b, "SCORE "), score);
    line_at(9, 255, b);
    if (RUSH->best) line_at(ROW_BOX + 1, 255, "NEW BEST");
    else if (all && all_score()) { six(cat(b, "BEST "), all_score()); line_at(ROW_BOX + 1, 255, b); }
    else if (!all && get16(RSV_BEST + 2 * RUSH->boss)) {
        mmss(cat(b, "BEST "), get16(RSV_BEST + 2 * RUSH->boss));
        line_at(ROW_BOX + 1, 255, b);
    }
    line_at(ROW_BOX + 3, 255, "A RETRY  B BACK");
    DISPLAY_ON;
}

static void all_record(void) {                   // ALL is over: its best (the highest score), saved when it is one
    if (score <= all_score()) return;
    RUSH->save[RSV_ALL_SCORE] = (uint8_t)score; RUSH->save[RSV_ALL_SCORE + 1] = (uint8_t)(score >> 8);
    RUSH->save[RSV_ALL_SCORE + 2] = (uint8_t)(score >> 16);
    put16(RSV_ALL_TIME, RUSH->total_t);
    RUSH->save[RSV_ALL_N] = RUSH->won;
    RUSH->best = 1;
    rush_store(RUSH->save);
}

// story_level_done in MODE_RUSH (GS_LEVEL_CLEAR is over, LCD on): the fight was won
void rush_won(void) BANKED {
    uint8_t i = RSV_BEST + 2 * RUSH->boss;
    uint16_t f = RUSH->fight_t, b = get16(i);
    RUSH->won++;
    RUSH->total_t = (uint16_t)(T_MAX - RUSH->total_t) < f ? T_MAX : RUSH->total_t + f;
    if (!b || f < b) {                           // his fastest rush win (CHOOSE or a fight of ALL)
        put16(i, f);
        if (RUSH->mode == RM_CHOOSE) RUSH->best = 1;
        rush_store(RUSH->save);
    }
    if (RUSH->mode == RM_ALL) {
        RUSH->boss = next_unlocked(RUSH->boss + 1);
        if (RUSH->boss < BOSS_COUNT) {
            if (lives < START_LIVES) lives++;    // a won fight gives a life back (never above 3)
            next_card();
            return;
        }
        RUSH->result = 1;
        all_record();
        result_show();
        return;
    }
    RUSH->result = 1;
    result_show();
}

// story SP_FAIL in MODE_RUSH (GAME OVER over the frozen fight is over): out of lives
void rush_lost(void) BANKED {
    boss_set(BOSS_NONE);
    RUSH->total_t = (uint16_t)(T_MAX - RUSH->total_t) < RUSH->fight_t ? T_MAX : RUSH->total_t + RUSH->fight_t;
    RUSH->result = 0;
    if (RUSH->mode == RM_ALL) all_record();
    result_show();
}

// ---- frames -----------------------------------------------------------------------------------------------------
static uint8_t menu_update(uint8_t pressed) {
    uint8_t s = RUSH->sel, old = s, k, q;
    if (pressed & J_UP) s = s ? s - 1 : MENU_LINES - 1;
    else if (pressed & J_DOWN) s = s == MENU_LINES - 1 ? 0 : s + 1;
    if (s != old) {
        RUSH->sel = s;
        RUSH->dirty |= ((1 << INFO_LINES) - 1) << MENU_LINES;   // (the info lines: the keys line included)
    } else if (pressed & (J_A | J_START)) {
        if (s) { list_open(); return 1; }
        if (count_unlocked() >= 2) { run_start(RM_ALL); return 1; }
    } else if (pressed & J_B) {
        title_back = TM_BONUS; title_back_sel = 3;   // the BONUS submenu, the cursor on BOSS RUSH
        title_enter();
        return 1;
    }
    for (k = 0, q = 0; k < MENU_LINES + INFO_LINES && q < ROWS_PER_FRAME; k++) {
        if (!(RUSH->dirty & (1 << k))) continue;
        RUSH->dirty &= ~(1 << k);
        build_menu(k, ROW(k));
        vq_add(0, ROW(k), 0, menu_row(k), 20);
        q++;
    }
    cursor();
    return 0;
}

// story_update, every frame of a rush screen (GS_STORY). 1: the screen changed.
uint8_t rush_update(uint8_t pressed) BANKED {
    if (RUSH->t != 255) RUSH->t++;
    switch (RUSH->scr) {
    case RS_MENU:
        return menu_update(pressed);
    case RS_LIST:
        return list_update(pressed);
    case RS_NEXT:
        if ((pressed & (J_A | J_START)) || RUSH->t >= NEXT_FRAMES) { fight(); return 1; }
        return 0;
    case RS_RESULT:
        if (pressed & (J_A | J_START)) { run_start(RUSH->mode); return 1; }
        if (pressed & J_B) {
            if (RUSH->mode == RM_ALL) menu_open(0); else list_open();
            return 1;
        }
        return 0;
    }
    return 0;
}
