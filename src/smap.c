// The story map (owner 2026-10-18, Q59-Q70: build 1 of the approved v14 art): the screen between a story's chapters. One full 160x144 picture
// (176 BG tiles, 8 CGB palettes, built by tools/gen_smap.py from assets/story_map/), eleven stops on one ring: the ten venues (stop c = chapter c) and the
// town / fountain square (stop 10, always open). Sal (a 16x16 map sprite) SNAPS from stop to stop with the D-pad along the ring (assets: the v14 snap
// table; LOCKED stops, the venues past the story's progress, are skipped); gold arrows beside him show where the D-pad leads. A short name tag
// (venue and chapter) comes up on the window layer for 90 frames on each arrival, BG palette 0.
//
//   A at the next uncleared venue     its PRE scene and the chapter, as before (story.c story_map_venue)
//   A at a cleared venue              a panel: PLAY <its mini-game> / BACK and the best medal; PLAY runs that mini-game alone (MG_PRACTICE | MG_MAP,
//                                     mg.c: never the boss, no story progress, the story's score untouched), a better medal upgrades the venue's saved medal
//   A at the town                     a panel: FESTIVAL GAMES / THE POUR-OFF. FESTIVAL: Shake Up, Perfect Pour, Tip Shower with their medals, unlocked
//                                     by chapters 2, 4 and 7; a new one not yet played shows the gold "!" over the tent. THE POUR-OFF is greyed until all ten
//                                     venues are cleared, then FINALE_A and the Pour-Off (Dregs's one-page nudge first with fewer than 3 festival golds).
//   START                             a panel: RESUME / QUIT TO TITLE (the map block is saved, CONTINUE returns to this stop); B or START resumes
//   B                                 nothing
//
// Festival lives (owner Q59c-d): the Pour-Off starts with 3 + the festival GOLDS won in the current story run (NORMAL or HARD; at most 3 games, so at most
// +3). They are not spent from any bank: smap_flags bits 4-6 (one per game), saved with the map block (save.c "SM", 6 bytes at 0x1E).
//
// State (no more WRAM than these two bytes): smap_stop, smap_flags; the panels and the tag live in story_scratch (no scene or mini-game runs meanwhile).
// The screen runs as GS_STORY with story_phase STORY_PHASE_MAP (story_update hands the frame here: no ROM0 case). Palettes: the map uses all eight BG
// palettes and OBJ palettes 1-4, 6, 7 (never 0, the bartender's, nor 5, the coin's); the HUD palette (BG 1) is put back by smap_pal_back, which the
// screens after the map call once their LCD is off (story.c scene_enter / shift_start, mg.c prelude). Window layer: row 0 the tag, rows 0-6 a panel
// (the window map's row r is map row 32 + r); both reach the screen through the VBlank queue, three rows a frame at most.
#pragma bank 255
#include <gb/gb.h>
#include <gb/cgb.h>
#include <stdint.h>

#include "game.h"
#include "music.h"
#include "story.h"
#include "mg.h"
#include "smap_art.h"

BANKREF_EXTERN(art_tiles)
extern const uint8_t bar_tiles[];
extern uint8_t overlay_on, story_phase, story_chapter, save_lock, score_digits[6], play_mode;
extern uint32_t score;
extern uint8_t win_rows[5][20];
void story_map_venue(uint8_t c) BANKED;       // src/story.c
void story_map_pouroff(void) BANKED;

uint8_t smap_stop;                            // 0..10: the stop Sal stands at (venue = chapter, 10 the town)
uint8_t smap_flags;                           // bits 0-2: festival game k was played since it unlocked (its "!" is gone); bits 4-6: it won GOLD in this story run;
                                              // bit 7: the HUD palette is borrowed (smap_pal_back); bit 3 free
#define F_PLAYED(k)  (1 << (k))
#define F_GOLD(k)    (0x10 << (k))
#define F_PALS       0x80
#define F_SAVED      0x77

#define NSTOPS       11
#define TOWN         10
#define NIL          255
#define FEST_N       3
#define OB           56                       // the map's OBJ tiles start at this id (0-55 are the bartender's, the mugs' and the coin: boot-time tiles)
#define BANG_X       72                       // the "!" over the tent
#define BANG_Y       56
#define TAG_FRAMES   90
#define LYC_NONE     255                      // the window runs to the screen's bottom: no raster interrupt wanted

// ---- the stops (tile coordinates of the dots) and the snap table: U, D, L, R ----------------------------------------------------------------------------
static const uint8_t stop_x[NSTOPS] = { 2, 0, 3, 10, 17, 16, 16, 17, 9, 6, 11 };
static const uint8_t stop_y[NSTOPS] = { 12, 5, 3, 3, 3, 8, 13, 17, 17, 16, 11 };
static const uint8_t snap[NSTOPS][4] = {
    { 1, NIL, NIL, 10 },     // 0 saloon
    { 2, 0, NIL, NIL },      // 1 stadium
    { NIL, 1, NIL, 3 },      // 2 lodge
    { NIL, NIL, 2, 4 },      // 3 bistro
    { NIL, 5, 3, NIL },      // 4 igloo
    { 4, 6, NIL, NIL },      // 5 factory
    { 5, 7, NIL, NIL },      // 6 The Chrome Cow
    { 6, NIL, 8, NIL },      // 7 teahouse
    { NIL, NIL, 9, 7 },      // 8 zoo
    { 10, NIL, NIL, 8 },     // 9 space lounge
    { NIL, 9, 0, NIL },      // 10 town
};
static const char *const tag_name[NSTOPS] = {
    "CH1 THE SALOON", "CH2 THE STADIUM", "CH3 LUMBER LODGE", "CH4 THE BISTRO", "CH5 THE IGLOO", "CH6 ROBOT FACTORY",
    "CH7 THE CHROME COW", "CH8 THE TEAHOUSE", "CH9 THE JUNGLE ZOO", "CH10 SPACE LOUNGE", "FESTIVAL SQUARE" };
static const char *const game_name[10] = {    // each venue's mini-game (mg.c mg_name)
    "QUICK DRAW", "SHIRT CANNON", "LOG ROLL", "ORDER UP!", "MARSHMALLOW DROP", "BATTERY SORT", "MILK RUN", "TAIKO POUR", "MONKEY BUSINESS", "ASTEROIDS" };
static const char *const fest_name[FEST_N] = { "SHAKE UP", "PERFECT POUR", "TIP SHOWER" };
static const uint8_t fest_at[FEST_N] = { 2, 4, 7 };     // the chapters cleared before each festival game opens
static const char *const medal_long[4] = { "NONE", "BRONZE", "SILVER", "GOLD" };
static const char *const medal_short[4] = { "----", "BRNZ", "SLVR", "GOLD" };
static const char dim_set[SMAP_DIM_N + 1] = "THEPOURF-";   // the letters of the one greyed line (THE POUR-OFF)

// ---- story_scratch: the row buffers and the screen's variables --------------------------------------------------------------------------------------------
#define ROWS_MAX     7
#define ROWBUF(r)    (story_scratch + (uint8_t)(r) * 20)    // the panel's rows, then (140..) the attribute rows and the tag
#define ATTR_PANEL   (story_scratch + 140)                  // 20 x palette 5 (the fountain's: cream text, light blue and gold rim on the dark band)
#define ATTR_TAG     (story_scratch + 160)                  // 20 x palette 0 (snow)
#define TAGROW       (story_scratch + 180)
#define V(n)         (story_scratch[400 + (n)])
enum { V_PANEL, V_SEL, V_ROWS, V_STEP, V_TAG, V_BOTTOM, V_TOP, V_ATTR, V_WY, V_WH, V_DONE, V_PREV };
enum { P_NONE, P_TOWN, P_VENUE, P_FEST, P_NUDGE, P_MENU };
#define PAL_PANEL    5
#define PAL_TAG      0

static void fill(uint8_t *d, uint8_t v, uint8_t n) { while (n--) *d++ = v; }

static uint8_t open_stop(uint8_t s) { return s == TOWN || s <= story_progress; }

static uint8_t popcount3(uint8_t v) { return (v & 1) + ((v >> 1) & 1) + ((v >> 2) & 1); }

static uint8_t golds(void) { return popcount3(smap_flags >> 4); }

static uint8_t fest_open(uint8_t k) { return story_progress >= fest_at[k]; }

static uint8_t bang_wanted(void) {            // an unlocked festival game that has not been played yet
    uint8_t k;
    for (k = 0; k < FEST_N; k++) if (fest_open(k) && !(smap_flags & F_PLAYED(k))) return 1;
    return 0;
}

// ---- movement: one hop along the ring in direction d, over locked stops --------------------------------------------------------------------------------------
static uint8_t hop(uint8_t from, uint8_t d) {
    uint8_t t = snap[from][d], prev = from, nx, k;
    while (t != NIL && !open_stop(t)) {           // a locked stop is passed: on to the ring's next stop the way we are going
        nx = NIL;
        for (k = 0; k < 4; k++) if (snap[t][k] != NIL && snap[t][k] != prev) nx = snap[t][k];
        prev = t; t = nx;
    }
    return t == NIL ? from : t;
}

// ---- text ----------------------------------------------------------------------------------------------------------------------------------------------------------
static uint8_t gl(char c, uint8_t dim) {
    uint8_t i;
    if (dim) for (i = 0; i < SMAP_DIM_N; i++) if (dim_set[i] == c) return SMAP_DIM_BASE + i;
    if (c >= 'A' && c <= 'Z') return glyph_az[c - 'A'];
    if (c >= '0' && c <= '9') return TILE_GLYPH_0 + (c - '0');
    switch (c) {
    case '.': return ST_GLYPH_PERIOD; case ',': return ST_GLYPH_COMMA; case '!': return ST_GLYPH_EXCL;
    case '?': return ST_GLYPH_QUEST; case '\'': return ST_GLYPH_APOS; case '-': return ST_GLYPH_HYPHEN;
    case ':': return ST_GLYPH_COLON;
    }
    return TILE_HUD_BLANK;
}

static void put_text(uint8_t *row, uint8_t col, const char *s, uint8_t dim) {
    while (*s && col < 20) row[col++] = gl(*s++, dim);
}

static void centre_text(uint8_t *row, const char *s) {
    uint8_t n = 0;
    while (s[n]) n++;
    put_text(row, n >= 20 ? 0 : (20 - n) >> 1, s, 0);
}

static uint8_t *blank_row(uint8_t r) { fill(ROWBUF(r), TILE_HUD_BLANK, 20); return ROWBUF(r); }

// ---- the sprites -----------------------------------------------------------------------------------------------------------------------------------------------
// OBJ palettes (CGB): sal 1, ufo 2, open dot 3, locked dot 4, arrow 6, bang 7 (smap_art.h's order is sal, ufo, open, locked, arrow, bang). DMG: OBP0 for all.
#define PAL_SAL    1
#define PAL_UFO    2
#define PAL_OPEN   3
#define PAL_LOCKED 4
#define PAL_ARROW  6
#define PAL_BANG   7
#define OAM_ARROWS 0       // 0-1: the two direction arrows
#define OAM_SAL    2       // 2-3
#define OAM_BANG   4
#define OAM_DOTS   5       // 5..15
#define OAM_UFO    16      // 16-18
#define OAM_CURSOR 19      // the panel's selection arrow

// px, py: the top-left of the 8-px column's art on screen (may be off the left / top edge); vh: its visible height (8 or 16). A sprite the window layer covers is not drawn.
static void put(uint8_t i, int16_t px, int16_t py, uint8_t tile, uint8_t pal, uint8_t flip, uint8_t vh) {
    OAM_item_t *o = shadow_OAM + i;
    uint8_t wy = V(V_WY), wh = V(V_WH);
    if (px + 8 <= 0 || px >= 160 || py + vh <= 0 || py >= 144 || (i != OAM_CURSOR && wh && py < (int16_t)wy + wh && py + vh > (int16_t)wy)) { o->y = 0; return; }
    o->y = (uint8_t)(py + 16); o->x = (uint8_t)(px + 8);
    o->tile = OB + tile;
    o->prop = (is_cgb ? pal : 0) | flip;
}

static void sal_pos(int16_t *sx, int16_t *sy) {
    uint8_t s = smap_stop;
    if (s == 6) { *sx = stop_x[s] * 8 - 24; *sy = stop_y[s] * 8 - 12; }      // The Chrome Cow: beside the dot, the building is right above the door
    else { *sx = stop_x[s] * 8 - 8; *sy = stop_y[s] * 8 - 14; }
}

static void draw(void) {
    uint8_t s, d, n = 0, t;
    int16_t sx, sy, ax, ay;
    uint8_t panel = V(V_PANEL);
    sal_pos(&sx, &sy);
    for (d = 0; d < 4; d++) {                      // the arrows: where each button leads (none while a panel is up)
        if (panel || hop(smap_stop, d) == smap_stop || n >= 2) continue;
        ax = sx + 4; ay = sy - 9; t = SOB_ARROW_U0;
        if (d == 1) { ay = sy + 17; t = SOB_ARROW_D0; }
        else if (d == 2) { ax = sx - 9; ay = sy + 4; t = SOB_ARROW_R0; }
        else if (d == 3) { ax = sx + 17; ay = sy + 4; t = SOB_ARROW_R0; }
        put(OAM_ARROWS + n++, ax, ay, t, PAL_ARROW, d == 2 ? S_FLIPX : 0, 8);
    }
    for (; n < 2; n++) shadow_OAM[OAM_ARROWS + n].y = 0;
    put(OAM_SAL, sx, sy, SOB_SAL0, PAL_SAL, 0, 16);
    put(OAM_SAL + 1, sx + 8, sy, SOB_SAL1, PAL_SAL, 0, 16);
    if (bang_wanted()) put(OAM_BANG, BANG_X, BANG_Y, SOB_BANG0, PAL_BANG, 0, 8);
    else shadow_OAM[OAM_BANG].y = 0;
    for (s = 0; s < NSTOPS; s++)
        put(OAM_DOTS + s, stop_x[s] * 8, stop_y[s] * 8, open_stop(s) ? SOB_DOT_OPEN0 : SOB_DOT_LOCKED0, open_stop(s) ? PAL_OPEN : PAL_LOCKED, 0, 8);
    put(OAM_UFO, 0, 104, SOB_UFO0, PAL_UFO, 0, 16);
    put(OAM_UFO + 1, 8, 104, SOB_UFO1, PAL_UFO, 0, 16);
    put(OAM_UFO + 2, 16, 104, SOB_UFO2, PAL_UFO, 0, 16);
    if (panel && V(V_DONE) && panel != P_NUDGE) {  // the selection arrow, at the selected line's left
        s = V(V_PANEL) == P_VENUE ? 2 : 1;
        put(OAM_CURSOR, 8, V(V_WY) + (s + V(V_SEL)) * 8, SOB_ARROW_R0, PAL_ARROW, 0, 8);
    } else shadow_OAM[OAM_CURSOR].y = 0;
}

// ---- the window layer -----------------------------------------------------------------------------------------------------------------------------------------
static void win_show(uint8_t y, uint8_t h, uint8_t lyc) {   // the window over lines y .. y + h - 1; lyc: where the LCD interrupt cuts it (LYC_NONE: at the screen's end)
    WX_REG = 7; WY_REG = y; LYC_REG = lyc;
    V(V_WY) = y; V(V_WH) = h;
    overlay_on = 3;                                // (1 would hide the sprites over the banner, 2 is a note: main.c)
}

static void win_hide(void) {
    overlay_on = 0; HIDE_WIN;
    WY_REG = BANNER_WY; LYC_REG = BANNER_LYC;      // (the banner window's own place again)
    V(V_WH) = 0; V(V_TAG) = 0;
}

static void tag_show(void) {                       // the name tag of the stop Sal stands at: queued now, shown from the next frame
    fill(TAGROW, TILE_HUD_BLANK, 20);
    centre_text(TAGROW, tag_name[smap_stop]);
    vq_add(0, TAGROW, 0, 32, 20);
    if (is_cgb) { vq_add(1, ATTR_TAG, 0, 32, 20); V(V_ATTR) &= ~1; }
    V(V_BOTTOM) = stop_y[smap_stop] < 4;           // Sal in the top rows: the tag goes along the bottom edge
    V(V_TAG) = TAG_FRAMES + 1;
}

static void tag_tick(void) {
    uint8_t t = V(V_TAG);
    if (!t) return;
    V(V_TAG) = --t;
    if (t == TAG_FRAMES) { if (V(V_BOTTOM)) win_show(136, 8, LYC_NONE); else win_show(0, 8, 7); }   // (the glyphs are 7 lines tall: the cut at line 7, as show_note)
    else if (!t) win_hide();
}

// ---- panels -----------------------------------------------------------------------------------------------------------------------------------------------------------
static uint8_t pour_off_open(void) { return story_progress >= STORY_CHAPTERS; }

static void panel_rows(uint8_t kind) {             // compose the panel's rows into the buffers; V_ROWS
    uint8_t k, g, n;
    char b[20];
    fill(ROWBUF(0), TILE_PANEL_TOP, 20);
    switch (kind) {
    case P_TOWN:
        put_text(blank_row(1), 3, "FESTIVAL GAMES", 0);
        put_text(blank_row(2), 3, "THE POUR-OFF", !pour_off_open());
        centre_text(blank_row(3), pour_off_open() ? "" : "CLEAR ALL VENUES");
        if (pour_off_open()) {
            b[0] = 'G'; b[1] = 'O'; b[2] = 'L'; b[3] = 'D'; b[4] = 'S'; b[5] = ':'; b[6] = ' '; b[7] = '0' + golds(); b[8] = 0;
            centre_text(ROWBUF(3), b);
        }
        n = 5;
        break;
    case P_VENUE:
        g = smap_stop;
        centre_text(blank_row(1), game_name[g]);
        put_text(blank_row(2), 3, "PLAY", 0);
        put_text(blank_row(3), 3, "BACK", 0);
        b[0] = 'B'; b[1] = 'E'; b[2] = 'S'; b[3] = 'T'; b[4] = ':'; b[5] = ' ';
        for (k = 0; (b[6 + k] = medal_long[mg_best[g] & 3][k]) != 0; k++) ;
        centre_text(blank_row(4), b);
        n = 6;
        break;
    case P_FEST:
        for (k = 0; k < FEST_N; k++) {
            blank_row(1 + k);
            if (fest_open(k)) {
                put_text(ROWBUF(1 + k), 3, fest_name[k], 0);
                put_text(ROWBUF(1 + k), 15, medal_short[bonus_best(k, MG_D_NORMAL)], 0);
            } else put_text(ROWBUF(1 + k), 3, "? ? ?", 0);
        }
        centre_text(blank_row(4), "GOLD: 1 LIFE");
        n = 6;
        break;
    case P_MENU:                                   // START: RESUME / QUIT TO TITLE
        put_text(blank_row(1), 3, "RESUME", 0);
        put_text(blank_row(2), 3, "QUIT TO TITLE", 0);
        n = 4;
        break;
    default:                                       // P_NUDGE: Dregs, text only (wording: proposed, pending the owner)
        centre_text(blank_row(1), "DREGS");
        centre_text(blank_row(2), "WARM UP FIRST, KID!");
        centre_text(blank_row(3), "FESTIVAL GOLDS GIVE");
        centre_text(blank_row(4), "YOU EXTRA LIVES.");
        n = 6;
        break;
    }
    fill(ROWBUF(n - 1), TILE_PANEL_BOT, 20);
    V(V_ROWS) = n;
}

static void panel_open(uint8_t kind, uint8_t sel) {
    win_hide();
    V(V_PANEL) = kind; V(V_SEL) = sel; V(V_STEP) = 0; V(V_DONE) = 0;
    panel_rows(kind);
    V(V_TOP) = stop_y[smap_stop] >= 9;
}

static void panel_close(void) {
    win_hide();
    V(V_PANEL) = P_NONE; V(V_DONE) = 0;
}

// Queue the panel's rows, at most three entries (tile rows, and attribute rows where the window map does not hold the panel's palette yet) a frame
// (the VBlank list's room: 3 x (20 + 3) bytes); when everything has gone, the window comes up on the next frame.
static void panel_pump(void) {
    uint8_t n = 0, s = V(V_STEP), r, rows = V(V_ROWS);
    if (s >= 2 * rows) {
        if (!V(V_DONE)) {
            V(V_DONE) = 1;
            if (V(V_TOP)) win_show(0, rows * 8, rows * 8 - 2);
            else win_show(144 - rows * 8, rows * 8, LYC_NONE);
        }
        return;
    }
    while (n < 3 && s < 2 * rows) {
        r = s >> 1;
        if (!(s & 1)) {                            // an attribute row (CGB)
            if (is_cgb && !((V(V_ATTR) >> r) & 1)) { vq_add(1, ATTR_PANEL, 0, 32 + r, 20); V(V_ATTR) |= 1 << r; n++; }
        } else { vq_add(0, ROWBUF(r), 0, 32 + r, 20); n++; }
        s++;
    }
    V(V_STEP) = s;
}

// ---- leaving ---------------------------------------------------------------------------------------------------------------------------------------------------------
static void leave(void) {                          // before any other screen: the window and its interrupt as the game keeps them, the map block saved
    win_hide();
    sm_put(smap_stop, smap_flags & F_SAVED);
}

static uint8_t press_a(void) {                     // A with no panel up. 1: the screen was left
    uint8_t s = smap_stop;
    if (s == TOWN) { panel_open(P_TOWN, 0); return 0; }
    if (s < story_progress) { panel_open(P_VENUE, 0); return 0; }
    if (s > story_progress) return 0;              // (a locked stop: the D-pad never lands on one)
    leave();                                       // the next uncleared venue
    story_map_venue(s);
    return 1;
}

static uint8_t panel_a(void) {                     // A in a panel. 1: the screen was left
    uint8_t k, kind = V(V_PANEL), sel = V(V_SEL);
    if (kind == P_TOWN) {
        if (sel == 0) { panel_open(P_FEST, 0); return 0; }
        if (!pour_off_open()) return 0;            // (greyed)
        if (golds() < FEST_N) { panel_open(P_NUDGE, 0); return 0; }
        leave(); story_map_pouroff();
        return 1;
    }
    if (kind == P_NUDGE) { leave(); story_map_pouroff(); return 1; }
    if (kind == P_MENU) {
        if (!sel) { panel_close(); return 0; }
        leave();                                   // (the map block is saved: CONTINUE comes back to this stop) then as pause.c's quit of a story run
        story_phase = 0; story_on = 0; story_arc = 0;
        smap_flags &= ~F_PALS;
        hud_pal_reset();
        title_enter();
        return 1;
    }
    if (kind == P_VENUE) {
        if (sel) { panel_close(); return 0; }
        leave();
        mg_enter(mg_of_venue(smap_stop), MG_PRACTICE | MG_MAP);
        return 1;
    }
    k = sel;                                       // P_FEST
    if (!fest_open(k)) return 0;
    smap_flags |= F_PLAYED(k);                      // (its "!" goes)
    leave();
    mg_enter(MG_SHAKEUP + k, MG_PRACTICE | MG_MAP);
    return 1;
}

static void panel_input(uint8_t pressed) {
    uint8_t kind = V(V_PANEL), sel = V(V_SEL), n = kind == P_TOWN || kind == P_VENUE || kind == P_MENU ? 2 : kind == P_FEST ? FEST_N : 1;
    if (!V(V_DONE)) return;
    if ((pressed & J_UP) && sel) V(V_SEL) = sel - 1;
    else if ((pressed & J_DOWN) && sel + 1 < n) V(V_SEL) = sel + 1;
    if (V(V_SEL) != sel) SFX(SFX_KA);
}

// ---- the screen -------------------------------------------------------------------------------------------------------------------------------------------------------
// One frame (story.c story_update, STORY_PHASE_MAP). 1: the screen was left (the next one is up).
uint8_t smap_update(uint8_t pressed) BANKED {
    uint8_t d, t;
    if (V(V_PANEL)) {
        panel_pump();
        panel_input(pressed);
        if (V(V_DONE) && (pressed & J_A) && panel_a()) return 1;
        if (V(V_DONE) && (pressed & J_START) && V(V_PANEL) == P_MENU) panel_close();
        else if (V(V_DONE) && (pressed & J_B)) {
            if (V(V_PANEL) == P_FEST) panel_open(P_TOWN, 0);
            else if (V(V_PANEL) == P_NUDGE) panel_open(P_TOWN, 1);
            else panel_close();
        }
        draw();
        return 0;
    }
    if (V(V_PREV)) { V(V_PREV) = 0; tag_show(); }
    tag_tick();
    d = (pressed & J_UP) ? 0 : (pressed & J_DOWN) ? 1 : (pressed & J_LEFT) ? 2 : (pressed & J_RIGHT) ? 3 : 4;
    if (d < 4) {
        t = hop(smap_stop, d);
        if (t != smap_stop) { smap_stop = t; tag_show(); SFX(SFX_DON); }
    } else if ((pressed & J_A) && press_a()) return 1;
    else if (pressed & J_START) panel_open(P_MENU, 0);
    draw();
    return 0;
}

// the greyed letters: copies of the glyphs with the text colour (index 0) turned into colour 1 (lo plane all ones), LCD off
static void dim_load(void) {
    uint8_t i, j, id;
    volatile uint8_t *src, *dst;
    for (i = 0; i < SMAP_DIM_N; i++) {
        id = gl(dim_set[i], 0);
        src = (volatile uint8_t *)(0x9000 + (uint16_t)id * 16);
        dst = (volatile uint8_t *)(0x8800 + (uint16_t)(SMAP_DIM_BASE + i - 128) * 16);
        for (j = 0; j < 16; j += 2) { dst[j] = 0xFF; dst[j + 1] = src[j + 1]; }
    }
}

// the screen, LCD off. quick: back from a mini-game (the quick white fade); else the story's own change (a scene ended, CONTINUE)
void smap_enter(uint8_t quick) BANKED {
    uint8_t r;
    if (quick) TRANS_MENU(); else TRANS_WANT();
    DISPLAY_OFF;
    overlay_on = 0; HIDE_WIN; WY_REG = BANNER_WY; LYC_REG = BANNER_LYC; SCX_REG = 0; SCY_REG = 0;
    vq_reset(); hud_dirty = 0; vram_pending = 0; life_lost = 0;
    clear_dirty();
    clear_patrons(); clear_mugs();
    tip_timer = 0; show_timer = 0;
    hide_all_sprites();
    win_rows[0][4] = 0;                            // (Dregs's gag state, src/dgag.c: a POST scene skipped mid-gag leaves none running)
    music_fast = 0;
    music_play(TUNE_TITLE);
    bkg_data_far(TILE_GENERIC_BASE, GENERIC_TILE_COUNT, bar_tiles, BANK(art_tiles));
    story_font_load();                             // (the font first: the picture's tiles take the ids around it)
    for (r = 0; r < SMAP_NRANGES; r++) set_bkg_data(smap_range[r][0], smap_range[r][2], smap_tiles + (uint16_t)smap_range[r][1] * 16);
    dim_load();
    set_bkg_tiles(0, 0, 20, 18, smap_map);
    set_sprite_data(OB, SMAP_OBJ_TILES, smap_obj_tiles);
    fill(ATTR_PANEL, PAL_PANEL, 20);
    fill(ATTR_TAG, PAL_TAG, 20);
    if (is_cgb) {
        VBK_REG = VBK_BANK_1;
        set_bkg_tiles(0, 0, 20, 18, smap_attr);
        VBK_REG = VBK_BANK_0;
        set_bkg_palette(0, 8, smap_bg_pal[0]);
        set_sprite_palette(PAL_SAL, 4, smap_obj_pal[0]);
        set_sprite_palette(PAL_ARROW, 2, smap_obj_pal[4]);
        smap_flags |= F_PALS;
    } else OBP0_REG = 0xD0;                        // (OBP0 as boot sets it: colour 1 white, 2 light grey, 3 black)
    for (r = 0; r < 12; r++) V(r) = 0;
    if (smap_stop >= NSTOPS || !open_stop(smap_stop)) smap_stop = story_progress < NSTOPS - 1 ? story_progress : TOWN;
    V(V_PREV) = 1;                                 // (the arrival tag is queued by the first frame: the transition's reveal has put the window rows back by then)
    story_phase = STORY_PHASE_MAP;
    game_state = GS_STORY;
    draw();
    DISPLAY_ON;
}

// A mini-game that the map started is over (mg.c, LCD off) or was quit (pause.c): the map again, the story's score as the map left it (a replay's points are
// not the story's: the medal's upgrade is, in save.c)
void smap_back(void) BANKED {
    score = venue_score_get(story_progress);
    split6(score_digits, score);
    smap_enter(1);
}

// a new story run: Sal at the saloon, no festival game played or won yet
void smap_new_run(void) BANKED {
    smap_stop = 0; smap_flags &= F_PALS;
}

// CONTINUE: the saved map block (stop, played / gold flags), else Sal at the next venue
void smap_continue(void) BANKED {
    uint8_t d[2];
    sm_get(d);
    smap_flags = (smap_flags & F_PALS) | d[1];
    smap_stop = d[0];                              // (smap_enter takes a stop that is not open back to the next venue)
    smap_enter(0);
}

// a festival game (k 0..2) won GOLD in a map play: 1 when it is a new life for the Pour-Off (this story run, NORMAL or HARD, not yet counted)
uint8_t smap_gold(uint8_t k) BANKED {
    if (!story_on || play_mode != MODE_STORY || RUN_DIFF == DIFF_EASY || (smap_flags & F_GOLD(k))) return 0;
    smap_flags |= F_GOLD(k);
    sm_put(smap_stop, smap_flags & F_SAVED);
    return 1;
}

// the Pour-Off's lives: 3 + this run's festival golds (po.c)
uint8_t smap_po_lives(void) BANKED {
    return story_on && play_mode == MODE_STORY ? golds() : 0;
}

// the screens after the map, LCD off: the HUD palette (BG 1, which the picture used) as the game keeps it, tinted as the run's difficulty tints it (main_cold.c)
void smap_pal_back(void) BANKED {
    uint16_t p[4];
    if (!(smap_flags & F_PALS)) return;
    smap_flags &= ~F_PALS;
    if (!is_cgb) return;
    p[0] = (31) | (29 << 5) | ((uint16_t)22 << 10);
    p[1] = (24) | (20 << 5) | ((uint16_t)10 << 10);
    p[2] = (29) | (20 << 5) | ((uint16_t)4 << 10);
    p[3] = (3) | (2 << 5) | ((uint16_t)8 << 10);
    if (story_on && play_mode == MODE_STORY && RUN_DIFF)
        p[2] = RUN_DIFF == DIFF_EASY ? (6 | (24 << 5) | ((uint16_t)8 << 10)) : (30 | (5 << 5) | ((uint16_t)5 << 10));
    set_bkg_palette(BGPAL_HUD, 1, p);
}
