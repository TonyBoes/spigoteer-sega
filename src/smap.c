// The story map (owner 2026-11-04, Q76 "definitely the right direction", Q78 "yes"; before it the v14 one-screen map of 2026-10-18, Q59-Q70): the screen
// between a story's chapters. One scrolling world of 64 x 48 cells (512 x 384 px, built by tools/gen_smap_world.py from the hand-typed pieces of
// tools/smap_world/): eleven stops (the ten venues, stop c = chapter c, and the town / fountain square, stop 10, always open) on 16 px roads. Sal walks
// the roads at his full in-game size (the bartender's front frames, OBJ tiles 0-23 and palette 0, always facing the camera); the D-pad sends him along the
// leg to the neighbour on that side (gold arrows show the exits that exist and are open) and the camera glides after him. Cloud hides the zones that are
// not open yet; the next stop shows as a red dot on the cloud's edge, the open ones as green dots. A short name tag (venue and chapter) slides in on the
// window layer for 90 frames on each arrival.
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
// State (no more WRAM than these two bytes): smap_stop, smap_flags; everything else lives in story_scratch (no scene or mini-game runs meanwhile):
// the camera, Sal, the walk, the loaded region, the tile tables (src/scratch.h and tests/test_scratch_map.py list the bytes).
// The screen runs as GS_STORY with story_phase STORY_PHASE_MAP (story_update hands the frame here: no ROM0 case).
//
// THE WORLD ON THE HARDWARE.  The 32 x 32 BG map holds a wrapped window of the world: cell (cx, cy) is at map (cx & 31, cy & 31); SCX / SCY are the
// camera's low 8 bits, set through the VBlank copy list (an entry that writes 0xFF42-3) so that the scroll, the new cells and the new tiles all land
// in one VBlank. The REGION is the rectangle of cells [c0, c1] x [r0, r1] whose map cells are valid and whose tiles are resident: it holds what the
// camera shows (at most 21 x 19 cells) and one line ahead on each axis in the direction of travel (at most 22 x 20). Lines are added one at a time
// (a JOB: a column or a row, a few cells a frame within the VBlank drain budget) and dropped when the camera has left them. The camera moves only
// where the region already covers the view (it holds a frame when a line is not loaded yet; Sal waits when the camera is far behind).
//   Color: a STATIC slot plan (a tile has one of 352 VRAM slots, two tiles share one only if no 22 x 20 window holds both): a cell needs its tile's slot to
//          hold that tile's variant (4 bits per slot in story_scratch), else the tile is loaded. BG palettes are shared by reference counts: the 18 palettes
//          of the world take the 8 hardware slots as cells enter and leave the region (a palette is written when its first cell enters).
//   DMG:   a DYNAMIC allocator in 176 slots: a table of the 10-bit tile id in each slot, a use count per slot, a hint slot per tile (ROM); a tile that is
//          not resident takes its hint slot when no cell uses it, else the next unused slot after a rotating pointer. No slot free: the job waits.
#pragma bank 255
#include <gb/gb.h>
#include <gb/cgb.h>
#include <stdint.h>

#include "game.h"
#include "music.h"
#include "story.h"
#include "mg.h"
#include "palettes.h"
#include "smap_art.h"
#define SMAPW_GEOMETRY
#include "smap_world.h"
extern void spr_data_far(uint8_t first, uint8_t n, const uint8_t *d, uint8_t bank);

BANKREF_EXTERN(art_tiles)
extern const uint8_t bar_tiles[];
extern const uint8_t bartender_tiles[];
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
#define TAG_FRAMES   90
#define TAG_SLIDE    12                       // frames the tag takes to slide in from the right (and out)
#define LYC_NONE     255                      // the window runs to the screen's bottom: no raster interrupt wanted

// ---- the stops (feet positions and the legs: build/smap_world.h) ----------------------------------------------------------------------------------------------
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

// ---- story_scratch: the whole of it is the map's while the map is up -----------------------------------------------------------------------------------------
#define SC(o)        (story_scratch + (o))
// region A, 0..395: the tile tables (the two models lay theirs over each other)
#define A_TBL        0       // DMG: 220 bytes: 176 low bytes of the tile id in each slot, then 44 bytes of the 2-bit highs (0x3FF: free)
#define A_CNT        220     // DMG: 176 use counts (cells of the region that show the slot's tile)
#define A_NIB        0       // Color: 176 bytes: the variant resident in each of the 352 slots, a nibble each (15: none)
#define A_PCNT       176     // Color: 18 x u16: the cells of the region in each palette
#define A_PSLOT      212     // Color: 18 bytes: the hardware slot of each palette (255: none)
#define A_PUSE       230     // Color: 8 bytes: the palette in each hardware slot (255: free)
#define A_ATTR_UI    240     // Color: 20 bytes: the window layer's attribute row (the town palette's slot)
#define A_IDA        260     // Color: 22 bytes: the attribute bytes of the cells being written
#define A_PSTG       282     // Color: 9 bytes: the palette write (BCPS, then 8 colour bytes)
#define S_V          396     // the variables (V_N <= 68)
#define S_T          464     // 56 bytes: tile staging (2 tiles) | the line's tile ids (22) | SCY, SCX; the panel's two rolling rows and the name tag's row lie over the first 40
#define T_TILES      0
#define T_IDS        32
#define T_CAM        54
#define V(n)         (story_scratch[S_V + (n)])
enum { V_PANEL, V_SEL, V_ROWS, V_STEP, V_TAG, V_BOTTOM, V_TOP, V_ATTR, V_WY, V_WH, V_DONE, V_PREV,
       V_CAMX = 12, V_CAMY = 14, V_FX = 16, V_FY = 18,                         // the camera's and Sal's feet's pixel positions in the world (16 bit each)
       V_WALK = 20, V_LEG, V_REV, V_WK, V_DEST, V_TICK,                        // the walk: on, the leg, walked backwards, the waypoint heading for, the stop heading for
       V_C0, V_C1, V_R0, V_R1,                                                 // the region (cells; V_C1 = V_C0 - 1: no columns yet)
       V_JK, V_JI, V_JA, V_JN, V_JP,                                           // the add job: none / column / row, the line's index, its first cell, its length, the next cell
       V_DK, V_DI, V_DA, V_DN, V_DP,                                           // the drop job: the same
       V_STATE, V_DIRECT, V_NSTG, V_RES, V_RESE, V_STALL, V_RR, V_UIPAL, V_PALQ, V_DIRX, V_DIRY, V_WXB, V_N };
typedef char smap_scratch_fits[(S_V + V_N <= S_T && S_T + 56 <= STORY_SCRATCH && A_IDA + 22 <= A_PSTG && A_PSTG + 9 <= S_V
                                && A_ATTR_UI + 20 <= A_IDA && A_CNT + 176 <= S_V && T_CAM + 2 <= 56 && T_IDS + 22 <= T_CAM) ? 1 : -1];
#define PANBUF       (S_T)                                          // the panel's rolling rows (2 x 20 bytes)
#define J_NONE       0
#define J_COL        1
#define J_ROW        2
enum { P_NONE, P_TOWN, P_VENUE, P_FEST, P_NUDGE, P_MENU };

static void fill(uint8_t *d, uint8_t v, uint8_t n) { while (n--) *d++ = v; }
static uint16_t g16(uint8_t n) { return V(n) | ((uint16_t)V(n + 1) << 8); }
static void s16(uint8_t n, uint16_t v) { V(n) = (uint8_t)v; V(n + 1) = (uint8_t)(v >> 8); }

static uint8_t open_stop(uint8_t s) { return s == TOWN || s <= story_progress; }

static uint8_t popcount3(uint8_t v) { return (v & 1) + ((v >> 1) & 1) + ((v >> 2) & 1); }

static uint8_t golds(void) { return popcount3(smap_flags >> 4); }

static uint8_t fest_open(uint8_t k) { return story_progress >= fest_at[k]; }

static uint8_t bang_wanted(void) {            // an unlocked festival game that has not been played yet
    uint8_t k;
    for (k = 0; k < FEST_N; k++) if (fest_open(k) && !(smap_flags & F_PLAYED(k))) return 1;
    return 0;
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

static uint8_t *blank_row(uint8_t *r) { fill(r, TILE_HUD_BLANK, 20); return r; }

// ---- the VBlank copy list: entries the list's own vq_add cannot name (a raw address), with its tally ---------------------------------------------------------
typedef struct { uint8_t n, bank; const uint8_t *src; uint8_t *dst; uint8_t pad[2]; } vq_entry_t;   // (render.c's list entry)
extern vq_entry_t vq[];
#define VQ_USE       22                       // entries a frame may add (the list holds 24; the panel and the tag take their own through vq_add)

static void qraw(uint8_t bank, const uint8_t *src, uint16_t dst, uint8_t n) {
    vq_entry_t *e;
    if (vq_count >= VQ_USE + 2) return;       // (cannot happen: every caller checks its room first)
    e = &vq[vq_count++];
    if (qv_cost <= VQ_DRAIN_BUDGET) qv_cost += n + 3 + (bank << 1);
    e->n = n; e->bank = bank; e->src = src; e->dst = (uint8_t *)dst;
}

static uint8_t room(void) { return qv_cost >= VQ_DRAIN_BUDGET ? 0 : (uint8_t)(VQ_DRAIN_BUDGET - qv_cost); }

static uint16_t tile_addr(uint8_t id) { return id < 128 ? 0x9000 + ((uint16_t)id << 4) : 0x8800 + ((uint16_t)(id - 128) << 4); }
static uint16_t map_addr(uint8_t cx, uint8_t cy) { return 0x9800 + ((uint16_t)(cy & 31) << 5) + (cx & 31); }
static uint8_t pool_id(uint8_t i) { return i < 36 ? i : (uint8_t)(i + 57); }   // the pool: BG ids 0-35 and 93-232 (the generic tiles, the font and the dim letters stay out)

// ---- the sprites -----------------------------------------------------------------------------------------------------------------------------------------------
// OBJ palettes (CGB): Sal 0 (the bartender's), ufo 2, open dot 3, locked dot 4, arrow 6, bang 7. DMG: OBP0 for all.
#define PAL_UFO    2
#define PAL_OPEN   3
#define PAL_LOCKED 4
#define PAL_ARROW  6
#define PAL_BANG   7
#define OAM_ARROWS 0       // 0-2: the direction arrows
#define OAM_SAL    3       // 3-6: A B C D
#define OAM_BANG   7
#define OAM_DOTS   8       // 8..18
#define OAM_UFO    19      // 19-21
#define OAM_CURSOR 22      // the panel's selection arrow

// px, py: the top-left of the 8-px column's art on screen (may be off the left / top edge); vh: its visible height (8 or 16). A sprite the window layer covers is not drawn.
static void put(uint8_t i, int16_t px, int16_t py, uint8_t tile, uint8_t pal, uint8_t flip, uint8_t vh) {
    OAM_item_t *o = shadow_OAM + i;
    uint8_t wy = V(V_WY), wh = V(V_WH);
    if (px + 8 <= 0 || px >= 160 || py + vh <= 0 || py >= 144 || (i != OAM_CURSOR && wh && py < (int16_t)wy + wh && py + vh > (int16_t)wy)) { o->y = 0; return; }
    o->y = (uint8_t)(py + 16); o->x = (uint8_t)(px + 8);
    o->tile = tile;
    o->prop = (is_cgb ? pal : 0) | flip;
}

static const uint8_t pic_seq[4] = { 1, 0, 2, 0 };     // the walk: step 1, stand, step 2, stand (a picture per 4 frames)

// A sprite entry written inline (a call with seven arguments costs more than the entry's four stores): px, py the top-left of the 8-px column's art on screen
// (it may lie off an edge: then the entry is hidden), vh its visible height; entries the window layer (wh lines from wy) covers are hidden too.
#define SPR(i, px, py, tl, pl, fl, vh) do { \
        OAM_item_t *o_ = shadow_OAM + (i); \
        if ((uint16_t)((px) + 7) < 167 && (uint16_t)((py) + (vh) - 1) < (uint16_t)(143 + (vh)) && !(wh && (py) < wend && (py) + (vh) > wy)) { \
            o_->y = (uint8_t)((py) + 16); o_->x = (uint8_t)((px) + 8); o_->tile = (tl); o_->prop = cgbp ? ((pl) | (fl)) : (fl); \
        } else o_->y = 0; } while (0)

static void draw(void) {
    uint8_t s, d, n = 0, t, p = V(V_STATE), pic = 0, nudge, panel = V(V_PANEL), wh = V(V_WH), cgbp = is_cgb;
    int16_t sx, sy, ax, ay, cx = (int16_t)g16(V_CAMX), cy = (int16_t)g16(V_CAMY), wy = V(V_WY), wend = (int16_t)V(V_WY) + wh;
    sx = (int16_t)g16(V_FX) - 8 - cx;               // Sal's top-left on the screen
    sy = (int16_t)g16(V_FY) - 24 - cy;
    nudge = (V(V_TICK) / 12) & 1;
    if (V(V_WALK)) pic = pic_seq[(V(V_TICK) >> 2) & 3];
    if (!panel && !V(V_WALK))                       // the arrows: where each button leads (none while a panel is up or Sal walks)
        for (d = 0; d < 4; d++) {
            s = smapw_exit[smap_stop][d];
            if (s == NIL || !open_stop(s) || n >= 3) continue;
            ax = sx + 4; ay = sy - 9 - nudge; t = SOB_ARROW_U0;
            if (d == 1) { ay = sy + 25 + nudge; t = SOB_ARROW_D0; }
            else if (d == 2) { ax = sx - 10 - nudge; ay = sy + 8; t = SOB_ARROW_R0; }
            else if (d == 3) { ax = sx + 18 + nudge; ay = sy + 8; t = SOB_ARROW_R0; }
            SPR(OAM_ARROWS + n, ax, ay, OB + t, PAL_ARROW, d == 2 ? S_FLIPX : 0, 8);
            n++;
        }
    for (; n < 3; n++) shadow_OAM[OAM_ARROWS + n].y = 0;
    t = pic * BARTENDER_TILES_PER_FRAME;            // Sal: the bartender's front picture, four 8x16 entries
    SPR(OAM_SAL, sx, sy, t, OBJPAL_BARTENDER, 0, 16);
    SPR(OAM_SAL + 1, sx + 8, sy, t + 2, OBJPAL_BARTENDER, 0, 16);
    ay = sy + 16;
    SPR(OAM_SAL + 2, sx, ay, t + 4, OBJPAL_BARTENDER, 0, 8);
    SPR(OAM_SAL + 3, sx + 8, ay, t + 6, OBJPAL_BARTENDER, 0, 8);
    if (bang_wanted()) { ax = SMAPW_BANG_X - cx; ay = SMAPW_BANG_Y - cy; SPR(OAM_BANG, ax, ay, OB + SOB_BANG0, PAL_BANG, 0, 8); }
    else shadow_OAM[OAM_BANG].y = 0;
    for (s = 0; s < NSTOPS; s++) {                  // the dots: green where Sal may go, red at the next stop (on the cloud's edge); none beyond
        ax = (int16_t)smapw_stop[s][0] - 4 - cx;
        if ((uint16_t)(ax + 7) >= 167 || (s > p && s != TOWN) || (s != p && !open_stop(s))) { shadow_OAM[OAM_DOTS + s].y = 0; continue; }
        ay = (int16_t)smapw_stop[s][1] - 8 - cy;
        if (open_stop(s)) SPR(OAM_DOTS + s, ax, ay, OB + SOB_DOT_OPEN0, PAL_OPEN, 0, 8);
        else SPR(OAM_DOTS + s, ax, ay, OB + SOB_DOT_LOCKED0, PAL_LOCKED, 0, 8);
    }
    if (p >= 10) {                                  // the UFO over the space lounge, once that is open (bobbing 1 px)
        ax = SMAPW_UFO_X - cx; ay = SMAPW_UFO_Y + ((V(V_TICK) / 24) & 1) - cy;
        SPR(OAM_UFO, ax, ay, OB + SOB_UFO0, PAL_UFO, 0, 16);
        ax += 8;
        SPR(OAM_UFO + 1, ax, ay, OB + SOB_UFO1, PAL_UFO, 0, 16);
        ax += 8;
        SPR(OAM_UFO + 2, ax, ay, OB + SOB_UFO2, PAL_UFO, 0, 16);
    } else for (s = 0; s < 3; s++) shadow_OAM[OAM_UFO + s].y = 0;
    if (panel && V(V_DONE) && panel != P_NUDGE) {  // the selection arrow, at the selected line's left
        s = V(V_PANEL) == P_VENUE ? 2 : 1;
        put(OAM_CURSOR, 8, V(V_WY) + (s + V(V_SEL)) * 8, OB + SOB_ARROW_R0, PAL_ARROW, 0, 8);
    } else shadow_OAM[OAM_CURSOR].y = 0;
}

// ---- the window layer ---------------------------------------------------------------------------------------------------------------------------------------
static void win_show(uint8_t y, uint8_t h, uint8_t lyc) {   // the window over lines y .. y + h - 1; lyc: where the LCD interrupt cuts it (LYC_NONE: at the screen's end)
    WX_REG = 7; WY_REG = y; LYC_REG = lyc;
    V(V_WY) = y; V(V_WH) = h;
    overlay_on = 3;                                // (1 would hide the sprites over the banner, 2 is a note: main.c)
}

static void win_hide(void) {
    overlay_on = 0; HIDE_WIN;
    WY_REG = BANNER_WY; LYC_REG = BANNER_LYC;      // (the banner window's own place again)
    WX_REG = 7;
    V(V_WH) = 0; V(V_TAG) = 0;
}

static uint8_t ui_attr(void) {                     // Color: the attribute of the window layer's cells: the town palette's hardware slot (held for as long as the map is up)
    return SC(A_PSLOT)[SMAPW_PAL_TOWN] & 7;
}

static void ui_attr_row(void) {
    uint8_t a = ui_attr();
    if (a != V(V_UIPAL) || !SC(A_ATTR_UI)[0]) { fill(SC(A_ATTR_UI), a, 20); V(V_UIPAL) = a; V(V_ATTR) = 0; }
}

static void tag_show(void) {                       // the name tag of the stop Sal stands at: queued now, shown from the next frame, sliding in from the right
    fill(SC(S_T), TILE_HUD_BLANK, 20);              // (the row lies in the tile staging area: no tile is staged this frame)
    centre_text(SC(S_T), tag_name[smap_stop]);
    vq_add(0, SC(S_T), 0, 32, 20);
    V(V_NSTG) = 2;
    if (is_cgb) { ui_attr_row(); if (!(V(V_ATTR) & 1)) { vq_add(1, SC(A_ATTR_UI), 0, 32, 20); V(V_ATTR) |= 1; } }
    V(V_BOTTOM) = (int16_t)g16(V_FY) - (int16_t)g16(V_CAMY) < 40;          // Sal in the top rows: the tag goes along the bottom edge
    V(V_TAG) = TAG_FRAMES + 1;
}

static void tag_tick(void) {
    uint8_t t = V(V_TAG), e;
    if (!t) return;
    V(V_TAG) = --t;
    if (t == TAG_FRAMES) { if (V(V_BOTTOM)) win_show(136, 8, LYC_NONE); else win_show(0, 8, 7); }   // (the glyphs are 7 lines tall: the cut at line 7, as show_note)
    else if (!t) { win_hide(); return; }
    e = TAG_FRAMES + 1 - t;                         // frames shown: the tag slides in from the right in the first TAG_SLIDE
    V(V_WXB) = 7 + (e < TAG_SLIDE ? (TAG_SLIDE - e) * 13 : 0);     // (through the copy list: the window's left edge moves in VBlank)
    qraw(0, &V(V_WXB), 0xFF4B, 1);
}

// ---- panels -----------------------------------------------------------------------------------------------------------------------------------------------------------
static uint8_t pour_off_open(void) { return story_progress >= STORY_CHAPTERS; }

// compose the panel's row `want` into out (the other rows into a sink): the panel's rolling two-row buffer is all the room the DMG map has. Returns the row count.
static uint8_t panel_row(uint8_t kind, uint8_t want, uint8_t *out) {
    uint8_t k, g, n, sink[20];
#define ROW(i) ((i) == want ? out : sink)
    char b[20];
    fill(ROW(0), TILE_PANEL_TOP, 20);
    switch (kind) {
    case P_TOWN:
        put_text(blank_row(ROW(1)), 3, "FESTIVAL GAMES", 0);
        put_text(blank_row(ROW(2)), 3, "THE POUR-OFF", !pour_off_open());
        centre_text(blank_row(ROW(3)), pour_off_open() ? "" : "CLEAR ALL VENUES");
        if (pour_off_open()) {
            b[0] = 'G'; b[1] = 'O'; b[2] = 'L'; b[3] = 'D'; b[4] = 'S'; b[5] = ':'; b[6] = ' '; b[7] = '0' + golds(); b[8] = 0;
            centre_text(ROW(3), b);
        }
        n = 5;
        break;
    case P_VENUE:
        g = smap_stop;
        centre_text(blank_row(ROW(1)), game_name[g]);
        put_text(blank_row(ROW(2)), 3, "PLAY", 0);
        put_text(blank_row(ROW(3)), 3, "BACK", 0);
        b[0] = 'B'; b[1] = 'E'; b[2] = 'S'; b[3] = 'T'; b[4] = ':'; b[5] = ' ';
        for (k = 0; (b[6 + k] = medal_long[mg_best[g] & 3][k]) != 0; k++) ;
        centre_text(blank_row(ROW(4)), b);
        n = 6;
        break;
    case P_FEST:
        for (k = 0; k < FEST_N; k++) {
            blank_row(ROW(1 + k));
            if (fest_open(k)) {
                put_text(ROW(1 + k), 3, fest_name[k], 0);
                put_text(ROW(1 + k), 15, medal_short[bonus_best(k, MG_D_NORMAL)], 0);
            } else put_text(ROW(1 + k), 3, "? ? ?", 0);
        }
        centre_text(blank_row(ROW(4)), "GOLD: 1 LIFE");
        n = 6;
        break;
    case P_MENU:                                   // START: RESUME / QUIT TO TITLE
        put_text(blank_row(ROW(1)), 3, "RESUME", 0);
        put_text(blank_row(ROW(2)), 3, "QUIT TO TITLE", 0);
        n = 4;
        break;
    default:                                       // P_NUDGE: Dregs, text only (the owner's wording)
        centre_text(blank_row(ROW(1)), "DREGS");
        centre_text(blank_row(ROW(2)), "YOU'LL HAVE TO");           // (the owner's line, Q71b: "You'll have to practice hard at the festival to have a hope of beating me")
        centre_text(blank_row(ROW(3)), "PRACTICE HARD AT THE");
        centre_text(blank_row(ROW(4)), "FESTIVAL TO HAVE A");
        centre_text(blank_row(ROW(5)), "HOPE OF BEATING ME!");
        n = 7;
        break;
    }
    fill(ROW(n - 1), TILE_PANEL_BOT, 20);
    return n;
}

static void panel_open(uint8_t kind, uint8_t sel) {
    win_hide();
    V(V_PANEL) = kind; V(V_SEL) = sel; V(V_STEP) = 0; V(V_DONE) = 0;
    V(V_ROWS) = panel_row(kind, 255, SC(PANBUF));
    V(V_TOP) = (int16_t)g16(V_FY) - (int16_t)g16(V_CAMY) > 72;
    if (is_cgb) ui_attr_row();
}

static void panel_close(void) {
    win_hide();
    V(V_PANEL) = P_NONE; V(V_DONE) = 0;
}

// Queue the panel's rows, at most two entries (tile rows, and attribute rows where the window map does not hold the panel's palette yet) a frame
// (the rolling buffer holds two rows: each is composed when its turn comes); when everything has gone, the window comes up on the next frame.
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
    while (n < 2 && s < 2 * rows) {
        r = s >> 1;
        if (!(s & 1)) {                            // an attribute row (CGB)
            if (is_cgb && !((V(V_ATTR) >> r) & 1)) { vq_add(1, SC(A_ATTR_UI), 0, 32 + r, 20); V(V_ATTR) |= 1 << r; n++; }
        } else { panel_row(V(V_PANEL), r, SC(PANBUF + 20 * n)); vq_add(0, SC(PANBUF + 20 * n), 0, 32 + r, 20); n++; }
        s++;
    }
    V(V_STEP) = s;
}

// ---- the world: slots, palettes, lines ---------------------------------------------------------------------------------------------------------------------------
static uint8_t nib_get(uint16_t s) { return (SC(A_NIB)[s >> 1] >> ((s & 1) << 2)) & 15; }
static void nib_set(uint16_t s, uint8_t v) {
    uint8_t *p = SC(A_NIB) + (s >> 1);
    if (s & 1) *p = (*p & 0x0F) | (v << 4); else *p = (*p & 0xF0) | v;
}

static uint16_t tbl_get(uint8_t s) {
    return SC(A_TBL)[s] | ((uint16_t)((SC(A_TBL)[176 + (s >> 2)] >> ((s & 3) << 1)) & 3) << 8);
}
static void tbl_set(uint8_t s, uint16_t t) {
    uint8_t *h = SC(A_TBL) + 176 + (s >> 2), sh = (s & 3) << 1;
    SC(A_TBL)[s] = (uint8_t)t;
    *h = (*h & ~(3 << sh)) | ((t >> 8) << sh);
}
static uint8_t tbl_find(uint16_t t, uint8_t hint) {     // the slot holding tile t, or NIL
    uint8_t s, lo = (uint8_t)t;
    if (tbl_get(hint) == t) return hint;
    for (s = 0; s < SMAPW_POOL; s++) if (SC(A_TBL)[s] == lo && tbl_get(s) == t) return s;
    return NIL;
}

// stage a tile load (the staging area holds two a frame; the caller has checked V_NSTG and the room) and queue it, or, with the LCD off, put it in VRAM
static void tile_load(uint8_t bank, uint8_t id, uint16_t tile) {
    uint8_t *d = SC(S_T + T_TILES + (V(V_NSTG) << 4));
    if (is_cgb) smap_c_tile(tile, d); else smap_d_tile(tile, d);
    if (V(V_DIRECT)) {
        if (bank) VBK_REG = VBK_BANK_1;
        set_bkg_data(id, 1, d);
        VBK_REG = VBK_BANK_0;
        return;
    }
    qraw(bank, d, tile_addr(id), 16);
    V(V_NSTG)++;
}

// Color: palette pal takes a hardware slot (NIL: none free) and its colours are written (queued: one palette a frame, the caller checked V_PALQ and the room)
static uint8_t pal_take(uint8_t pal) {
    uint8_t s, *st = SC(A_PSTG);
    for (s = 0; s < 8; s++) if (SC(A_PUSE)[s] == NIL) break;
    if (s == 8) return NIL;
    SC(A_PUSE)[s] = pal; SC(A_PSLOT)[pal] = s;
    smap_c_palette(pal, st + 1);
    if (V(V_DIRECT)) { set_bkg_palette(s, 1, (const uint16_t *)(st + 1)); return s; }
    st[0] = 0x80 | (s << 3);                       // BCPS: auto increment from colour 0 of palette s
    qraw(0, st, 0xFF68, 1);
    for (pal = 1; pal < 9; pal++) qraw(0, st + pal, 0xFF69, 1);
    V(V_PALQ) = 1;
    return s;
}

static void pal_count(uint8_t pal, int8_t d) {          // the region's cells in palette pal change by d; the slot is free at 0
    uint8_t *c = SC(A_PCNT) + (pal << 1);
    uint16_t v = (c[0] | ((uint16_t)c[1] << 8)) + (int16_t)d;
    c[0] = (uint8_t)v; c[1] = (uint8_t)(v >> 8);
    if (!v && d < 0) { SC(A_PUSE)[SC(A_PSLOT)[pal]] = NIL; SC(A_PSLOT)[pal] = NIL; }
}

#define R_OK    0
#define R_RES   1                                   // no slot or palette free: the line waits for the camera to drop a line
#define R_ROOM  2                                   // not enough room in this frame's list: tomorrow

static uint8_t slot_of_id(uint8_t id) { return id < 36 ? id : (uint8_t)(id - 57); }      // (pool_id's inverse)

// the cells' map entries: a column's own (the map's addresses are 32 apart), a row's go out as runs when its line is flushed
static void emit_cell(uint8_t k, uint16_t addr, uint8_t cost) {
    vq_entry_t *e;
    e = &vq[vq_count++];
    e->n = 1; e->bank = 0; e->src = SC(S_T + T_IDS + k); e->dst = (uint8_t *)addr;
    if (is_cgb) {
        e = &vq[vq_count++];
        e->n = 1; e->bank = 1; e->src = SC(A_IDA + k); e->dst = (uint8_t *)addr;
    }
    if (qv_cost <= VQ_DRAIN_BUDGET) qv_cost += cost;
}

// One cell into the region: its tile (and palette) made resident, its id and attribute in the line buffers at k (a column's cell gets its map entries queued here, a row's
// are flushed by the caller). R_OK, or why not (nothing changed then).
static uint8_t add_cell(const smap_fc *f, uint8_t k, uint8_t cx, uint8_t cy, uint8_t vert) {
    uint16_t t = f->w & 0x3FF, slot9 = 0;
    uint8_t direct = V(V_DIRECT), need_t, need_p = 0, hw = 0, slot = 0, id, att = 0, pal = 0, bank = 0, var = 0, cost, ents, h, s, rr, n;
    if (is_cgb) {
        pal = (uint8_t)(f->w >> 10);
        slot9 = f->aux & 0x1FF; var = (uint8_t)(f->aux >> 9);
        need_p = SC(A_PSLOT)[pal] == NIL;
        need_t = nib_get(slot9) != var;
        bank = slot9 >= SMAPW_POOL;
    } else {
        slot = tbl_find(t, (uint8_t)f->aux);
        need_t = slot == NIL;
    }
    if (!direct) {
        if (vert) { cost = is_cgb ? 10 : 4; ents = is_cgb ? 2 : 1; } else { cost = is_cgb ? 2 : 1; ents = 0; }
        if (need_t) { if (V(V_NSTG) >= 2) return R_ROOM; cost += 19 + (bank << 1); ents++; }
        if (need_p) { if (V(V_PALQ)) return R_ROOM; cost += 36; ents += 9; }
        if (room() < (uint8_t)(cost + V(V_RES)) || (uint8_t)(vq_count + ents + V(V_RESE)) > VQ_USE) return R_ROOM;
    }
    if (is_cgb) {
        hw = SC(A_PSLOT)[pal];
        if (need_p) { hw = pal_take(pal); if (hw == NIL) return R_RES; }
        id = pool_id(bank ? (uint8_t)(slot9 - SMAPW_POOL) : (uint8_t)slot9);
        if (need_t) { nib_set(slot9, var); tile_load(bank, id, t); }
        pal_count(pal, 1);
        att = hw | (bank ? 8 : 0);
    } else {
        if (need_t) {                                // the hint slot when no cell shows what it holds, else the next such slot after the pointer
            h = (uint8_t)f->aux;
            if (SC(A_CNT)[h] == 0) s = h;
            else {
                rr = V(V_RR);
                for (n = 0; n < SMAPW_POOL; n++) { s = rr; rr = rr + 1 >= SMAPW_POOL ? 0 : rr + 1; if (SC(A_CNT)[s] == 0) break; }
                if (n == SMAPW_POOL) return R_RES;
                V(V_RR) = rr;
            }
            slot = s;
            tbl_set(slot, t);
            tile_load(0, pool_id(slot), t);
        }
        id = pool_id(slot);
        SC(A_CNT)[slot]++;
    }
    SC(S_T + T_IDS)[k] = id;
    if (is_cgb) SC(A_IDA)[k] = att;
    if (direct) {
        *(volatile uint8_t *)map_addr(cx, cy) = id;
        if (is_cgb) { VBK_REG = VBK_BANK_1; *(volatile uint8_t *)map_addr(cx, cy) = att; VBK_REG = VBK_BANK_0; }
    } else if (vert) emit_cell(k, map_addr(cx, cy), is_cgb ? 10 : 4);
    return R_OK;
}

// the next cell shows what the one before it does (the same tile and palette, already resident): no lookup, no load
static uint8_t add_same(const smap_fc *f, uint8_t k, uint8_t cx, uint8_t cy, uint8_t vert) {
    uint8_t direct = V(V_DIRECT), id = SC(S_T + T_IDS)[k - 1], att = 0;
    if (!direct) {
        if (room() < (uint8_t)((vert ? (is_cgb ? 10 : 4) : (is_cgb ? 2 : 1)) + V(V_RES)) || (uint8_t)(vq_count + (vert ? (is_cgb ? 2 : 1) : 0) + V(V_RESE)) > VQ_USE) return R_ROOM;
    }
    if (is_cgb) { att = SC(A_IDA)[k - 1]; SC(A_IDA)[k] = att; pal_count((uint8_t)(f->w >> 10), 1); }
    else SC(A_CNT)[slot_of_id(id)]++;
    SC(S_T + T_IDS)[k] = id;
    if (direct) {
        *(volatile uint8_t *)map_addr(cx, cy) = id;
        if (is_cgb) { VBK_REG = VBK_BANK_1; *(volatile uint8_t *)map_addr(cx, cy) = att; VBK_REG = VBK_BANK_0; }
    } else if (vert) emit_cell(k, map_addr(cx, cy), is_cgb ? 10 : 4);
    return R_OK;
}

// n cells that show f's tile leave the region
static void drop_cells(const smap_fc *f, uint8_t n) {
    uint8_t s;
    if (is_cgb) { pal_count((uint8_t)(f->w >> 10), -(int8_t)n); return; }
    s = tbl_find(f->w & 0x3FF, (uint8_t)f->aux);
    if (s != NIL) SC(A_CNT)[s] -= n;
}

static void fetch(uint8_t cx, uint8_t cy, uint8_t n, uint8_t vert, smap_fc *out) {
    if (is_cgb) smap_c_fetch(cx, cy, n, vert, V(V_STATE), out); else smap_d_fetch(cx, cy, n, vert, V(V_STATE), out);
}

// the row cells [a, b) of the line at map row cy, from cell column cx0, into the copy list: at most two runs (the map wraps at column 31), each with its attributes
static void flush_run(uint8_t cx0, uint8_t cy, uint8_t a, uint8_t b) {
    uint8_t n, x;
    while (a < b) {
        x = (cx0 + a) & 31;
        n = b - a;
        if (x + n > 32) n = 32 - x;
        qraw(0, SC(S_T + T_IDS + a), map_addr(cx0 + a, cy), n);
        if (is_cgb) qraw(1, SC(A_IDA + a), map_addr(cx0 + a, cy), n);
        a += n;
    }
}

// Work on the add job's line: at most cap cells now, and what is left of this frame's list. 1: the line is complete.
static uint8_t job_run(uint8_t cap) {
    uint8_t vert = V(V_JK) == J_COL, idx = V(V_JI), a = V(V_JA), n = V(V_JN), pos = V(V_JP), first = pos, m, k, r = R_OK, cx, cy;
    smap_fc fc[8];
    uint16_t pw = 0;
    V(V_RES) = 0; V(V_RESE) = 0;
    if (!vert && !V(V_DIRECT)) { V(V_RES) = is_cgb ? 16 : 6; V(V_RESE) = is_cgb ? 4 : 2; }   // (a row's entries come at the end: their overhead is kept back)
    while (pos < n && r == R_OK && cap) {
        m = n - pos; if (m > 8) m = 8;
        cx = vert ? idx : a + pos; cy = vert ? a + pos : idx;
        fetch(cx, cy, m, vert, fc);
        for (k = 0; k < m && cap; k++) {
            if (pos > first && fc[k].w == pw) r = add_same(fc + k, pos, vert ? cx : cx + k, vert ? cy + k : cy, vert);
            else r = add_cell(fc + k, pos, vert ? cx : cx + k, vert ? cy + k : cy, vert);
            if (r) break;
            pw = fc[k].w; pos++; cap--;
        }
    }
    if (!vert && !V(V_DIRECT) && pos > first) { V(V_RES) = 0; V(V_RESE) = 0; flush_run(a, idx, first, pos); }
    V(V_RES) = 0; V(V_RESE) = 0;
    V(V_JP) = pos;
    if (r == R_RES) { if (V(V_STALL) < 255) V(V_STALL)++; } else V(V_STALL) = 0;
    return pos >= n;
}

// the cells of the add job's line already added leave again (the job is given up)
static void job_abort(void) {
    uint8_t vert = V(V_JK) == J_COL, a = V(V_JA), idx = V(V_JI), pos = V(V_JP), c = 0, m, k, j;
    smap_fc fc[8];
    while (c < pos) {
        m = pos - c; if (m > 8) m = 8;
        fetch(vert ? idx : a + c, vert ? a + c : idx, m, vert, fc);
        for (k = 0; k < m; k = j) {
            for (j = k + 1; j < m && fc[j].w == fc[k].w; j++) ;
            drop_cells(fc + k, j - k);
        }
        c += m;
    }
    V(V_JK) = J_NONE; V(V_JP) = 0; V(V_STALL) = 0;
}

// the drop job's line leaves the region: at most cap cells now (its extents left the region when the job started)
static void drop_run(uint8_t cap) {
    uint8_t vert = V(V_DK) == J_COL, a = V(V_DA), idx = V(V_DI), n = V(V_DN), pos = V(V_DP), m, k, j;
    smap_fc fc[8];
    while (pos < n && cap) {
        m = n - pos; if (m > 8) m = 8;
        if (m > cap) m = cap;
        fetch(vert ? idx : a + pos, vert ? a + pos : idx, m, vert, fc);
        for (k = 0; k < m; k = j) {
            for (j = k + 1; j < m && fc[j].w == fc[k].w; j++) ;
            drop_cells(fc + k, j - k);
        }
        pos += m; cap -= m;
    }
    V(V_DP) = pos;
    if (pos >= n) V(V_DK) = J_NONE;
}

// ---- the camera, the region, the walk ------------------------------------------------------------------------------------------------------------------------------------
#define CAM_SPD  4
#define CAM_LAG  24                                   // Sal waits while the camera is further behind him than this (px, both axes together)
#define CAM_MAXX 352                                  // 512 - 160
#define CAM_MAXY 240                                  // 384 - 144
#define WALK_SPD 2
#define ADD_CAP  6                                    // cells a frame the add job and the drop job each handle
#define DROP_CAP 8

static void cam_target(int16_t *tx, int16_t *ty) {
    int16_t x = (int16_t)g16(V_FX) - 80, y = (int16_t)g16(V_FY) - 84;
    *tx = x < 0 ? 0 : x > CAM_MAXX ? CAM_MAXX : x;
    *ty = y < 0 ? 0 : y > CAM_MAXY ? CAM_MAXY : y;
}

static uint8_t cov_x(int16_t x) { return (uint8_t)(x >> 3) >= V(V_C0) && (uint8_t)((x + 159) >> 3) <= V(V_C1); }
static uint8_t cov_y(int16_t y) { return (uint8_t)(y >> 3) >= V(V_R0) && (uint8_t)((y + 143) >> 3) <= V(V_R1); }

// the camera moves toward Sal, but only where the region already covers what it will show. 1: it moved
static uint8_t camera_step(void) {
    int16_t cx = (int16_t)g16(V_CAMX), cy = (int16_t)g16(V_CAMY), tx, ty, nx, ny, d;
    cam_target(&tx, &ty);
    if (tx != cx) V(V_DIRX) = tx > cx ? 2 : 1;
    if (ty != cy) V(V_DIRY) = ty > cy ? 2 : 1;
    d = tx - cx; if (d > CAM_SPD) d = CAM_SPD; else if (d < -CAM_SPD) d = -CAM_SPD;
    nx = cx + d;
    while (nx != cx && !cov_x(nx)) nx += nx > cx ? -1 : 1;
    d = ty - cy; if (d > CAM_SPD) d = CAM_SPD; else if (d < -CAM_SPD) d = -CAM_SPD;
    ny = cy + d;
    while (ny != cy && !cov_y(ny)) ny += ny > cy ? -1 : 1;
    if (!V(V_WALK) && nx == tx && ny == ty) { V(V_DIRX) = 0; V(V_DIRY) = 0; }
    if (nx == cx && ny == cy) return 0;
    s16(V_CAMX, nx); s16(V_CAMY, ny);
    return 1;
}

// the region follows the camera: the lines it has left drop (a few cells a frame), the lines the camera will want next (one ahead on each axis in the direction of
// travel) load (a few cells a frame): one job of each kind at a time
static void region_work(void) {
    uint16_t cx = g16(V_CAMX), cy = g16(V_CAMY);
    uint8_t nc0 = (uint8_t)(cx >> 3), nc1 = (uint8_t)((cx + 159) >> 3), nr0 = (uint8_t)(cy >> 3), nr1 = (uint8_t)((cy + 143) >> 3);
    uint8_t wc0 = nc0, wc1 = nc1, wr0 = nr0, wr1 = nr1, dx = V(V_DIRX), dy = V(V_DIRY), kind = V(V_JK), i, dk, di = 0;
    if (dx == 1 && wc0) wc0--;
    if (dx == 2 && wc1 < 63) wc1++;
    if (dy == 1 && wr0) wr0--;
    if (dy == 2 && wr1 < 47) wr1++;
    i = V(V_JI);
    if ((kind == J_COL && (i < wc0 || i > wc1)) || (kind == J_ROW && (i < wr0 || i > wr1))) job_abort();
    if (V(V_PANEL) || vq_held) return;
    if (V(V_DK) == J_NONE) {                         // the next line to drop, if any: its place in the region goes now, its cells a few at a time
        dk = J_COL;
        if (V(V_C0) < wc0 && V(V_C0) < V(V_C1)) di = V(V_C0)++;
        else if (V(V_C1) > wc1 && V(V_C1) > V(V_C0)) di = V(V_C1)--;
        else {
            dk = J_ROW;
            if (V(V_R0) < wr0 && V(V_R0) < V(V_R1)) di = V(V_R0)++;
            else if (V(V_R1) > wr1 && V(V_R1) > V(V_R0)) di = V(V_R1)--;
            else dk = J_NONE;
        }
        if (dk != J_NONE) {
            if (V(V_JK) != J_NONE && V(V_JK) != dk) job_abort();     // (an add job across it would add cells of the line that leaves)
            V(V_DK) = dk; V(V_DI) = di; V(V_DP) = 0;
            if (dk == J_COL) { V(V_DA) = V(V_R0); V(V_DN) = V(V_R1) - V(V_R0) + 1; }
            else { V(V_DA) = V(V_C0); V(V_DN) = V(V_C1) - V(V_C0) + 1; }
        }
    }
    if (V(V_DK) != J_NONE) drop_run(DROP_CAP);
    if (V(V_JK) == J_NONE) {
        if (V(V_C0) > wc0) { V(V_JK) = J_COL; V(V_JI) = V(V_C0) - 1; }
        else if (V(V_C1) < wc1) { V(V_JK) = J_COL; V(V_JI) = V(V_C1) + 1; }
        else if (V(V_R0) > wr0) { V(V_JK) = J_ROW; V(V_JI) = V(V_R0) - 1; }
        else if (V(V_R1) < wr1) { V(V_JK) = J_ROW; V(V_JI) = V(V_R1) + 1; }
        else return;
        if (V(V_JK) == J_COL) { V(V_JA) = V(V_R0); V(V_JN) = V(V_R1) - V(V_R0) + 1; }
        else { V(V_JA) = V(V_C0); V(V_JN) = V(V_C1) - V(V_C0) + 1; }
        V(V_JP) = 0;
    }
    if (job_run(ADD_CAP)) {                          // complete: the line is part of the region
        if (V(V_JK) == J_COL) { if (V(V_JI) < V(V_C0)) V(V_C0) = V(V_JI); else V(V_C1) = V(V_JI); }
        else { if (V(V_JI) < V(V_R0)) V(V_R0) = V(V_JI); else V(V_R1) = V(V_JI); }
        V(V_JK) = J_NONE;
    }
}

static void start_walk(uint8_t d) {
    uint8_t t = smapw_exit[smap_stop][d], e = smapw_exit_leg[smap_stop][d], leg = e & 0x7F, rev = e >> 7;
    if (t == NIL || !open_stop(t)) return;
    V(V_LEG) = leg; V(V_REV) = rev; V(V_DEST) = t;
    V(V_WK) = rev ? smapw_leg_n[leg] - 2 : 1;        // the waypoint after the one Sal stands on
    V(V_WALK) = 1;
    SFX(SFX_DON);
}

static void walk_step(void) {
    uint8_t leg = V(V_LEG), k = V(V_WK), rev = V(V_REV);
    uint16_t fx = g16(V_FX), fy = g16(V_FY), tx = smapw_leg_pt[leg][k][0], ty = smapw_leg_pt[leg][k][1];
    int16_t ctx, cty, lx, ly;
    cam_target(&ctx, &cty);
    lx = ctx - (int16_t)g16(V_CAMX); ly = cty - (int16_t)g16(V_CAMY);
    if (lx < 0) lx = -lx;
    if (ly < 0) ly = -ly;
    if (lx + ly > CAM_LAG) return;                   // the camera is behind: Sal waits for it
    if (fx != tx) fx = fx < tx ? (tx - fx < WALK_SPD ? tx : fx + WALK_SPD) : (fx - tx < WALK_SPD ? tx : fx - WALK_SPD);
    else if (fy != ty) fy = fy < ty ? (ty - fy < WALK_SPD ? ty : fy + WALK_SPD) : (fy - ty < WALK_SPD ? ty : fy - WALK_SPD);
    s16(V_FX, fx); s16(V_FY, fy);
    V(V_TICK)++;
    if (fx != tx || fy != ty) return;
    if (rev ? !k : k + 1 == smapw_leg_n[leg]) {      // the last waypoint: Sal is there
        smap_stop = V(V_DEST);
        V(V_WALK) = 0;
        tag_show();
    } else V(V_WK) = rev ? k - 1 : k + 1;
}

// ---- leaving ---------------------------------------------------------------------------------------------------------------------------------------------------------
static void leave(void) {                          // before any other screen: the window and its interrupt as the game keeps them, the scroll back, the map block saved
    win_hide();
    SCX_REG = 0; SCY_REG = 0;
    sm_put(smap_stop, smap_flags & F_SAVED);
}

static uint8_t press_a(void) {                     // A with no panel up. 1: the screen was left
    uint8_t s = smap_stop;
    if (s == TOWN) { panel_open(P_TOWN, 0); return 0; }
    if (s < story_progress) { panel_open(P_VENUE, 0); return 0; }
    if (s > story_progress) return 0;              // (a locked stop: Sal never stands on one)
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
    uint8_t d;
    V(V_NSTG) = 0; V(V_PALQ) = 0;
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
    if (V(V_WALK)) walk_step();
    else {
        d = (pressed & J_UP) ? 0 : (pressed & J_DOWN) ? 1 : (pressed & J_LEFT) ? 2 : (pressed & J_RIGHT) ? 3 : 4;
        if (d < 4) start_walk(d);
        else if ((pressed & J_A) && press_a()) return 1;
        else if (pressed & J_START) panel_open(P_MENU, 0);
    }
    if (!V(V_PANEL) && !vq_held) {
        if (camera_step()) {
            SC(S_T + T_CAM)[0] = (uint8_t)g16(V_CAMY); SC(S_T + T_CAM)[1] = (uint8_t)g16(V_CAMX);
            qraw(0, SC(S_T + T_CAM), 0xFF42, 2);
        }
        region_work();
    }
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
    uint16_t i;
    uint8_t c;
    uint16_t p4[4];
    int16_t tx, ty;
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
    story_font_load();                             // (the font first: the world's tiles take the ids around it)
    dim_load();
    spr_data_far(OBJ_BARTENDER, BARTENDER_FRAMES * BARTENDER_TILES_PER_FRAME, bartender_tiles, BANK(art_tiles));     // Sal's pictures (a Pour-Off or a mini-game may have used the ids)
    set_sprite_data(OB, SMAP_OBJ_TILES, smap_obj_tiles);
    for (i = 0; i < STORY_SCRATCH; i++) story_scratch[i] = 0;
    if (is_cgb) {
        fill(SC(A_NIB), 0xFF, 176);
        fill(SC(A_PSLOT), NIL, SMAPW_NPAL);
        fill(SC(A_PUSE), NIL, 8);
        pal_get(PAL_BARTENDER, p4);
        set_sprite_palette(OBJPAL_BARTENDER, 1, p4);
        set_sprite_palette(PAL_UFO, 3, smap_obj_pal[0]);
        set_sprite_palette(PAL_ARROW, 2, smap_obj_pal[3]);
        smap_flags |= F_PALS;
    } else {
        fill(SC(A_TBL), 0xFF, 220);                // (every slot free: tile 0x3FF)
        OBP0_REG = 0xD0;                           // (OBP0 as boot sets it: colour 1 white, 2 light grey, 3 black)
    }
    if (smap_stop >= NSTOPS || !open_stop(smap_stop)) smap_stop = story_progress < NSTOPS - 1 ? story_progress : TOWN;
    V(V_STATE) = story_progress < 9 ? story_progress + 1 : 10;
    s16(V_FX, smapw_stop[smap_stop][0]); s16(V_FY, smapw_stop[smap_stop][1]);
    cam_target(&tx, &ty);
    s16(V_CAMX, tx); s16(V_CAMY, ty);
    V(V_C0) = tx >> 3; V(V_C1) = V(V_C0) - 1;      // the view's cells, column by column (no lines ahead yet: the walk asks for them)
    V(V_R0) = ty >> 3; V(V_R1) = (ty + 143) >> 3;
    V(V_DIRECT) = 1;
    if (is_cgb) { pal_take(SMAPW_PAL_TOWN); pal_count(SMAPW_PAL_TOWN, 1); }   // (the town palette is held for good: it is the window layer's)
    for (c = tx >> 3; c <= (uint8_t)((tx + 159) >> 3); c++) {
        V(V_JK) = J_COL; V(V_JI) = c; V(V_JA) = V(V_R0); V(V_JN) = V(V_R1) - V(V_R0) + 1; V(V_JP) = 0;
        job_run(255);
        V(V_C1) = c;
    }
    V(V_JK) = J_NONE; V(V_DIRECT) = 0;
    SCX_REG = (uint8_t)tx; SCY_REG = (uint8_t)ty;
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

// the screens after the map, LCD off: the HUD palette (BG 1, which the world borrowed) as the game keeps it, tinted as the run's difficulty tints it (main_cold.c)
void smap_pal_back(void) BANKED {
    uint16_t p[4];
    if (!(smap_flags & F_PALS)) return;
    smap_flags &= ~F_PALS;
    SCX_REG = 0; SCY_REG = 0;
    if (!is_cgb) return;
    p[0] = (31) | (29 << 5) | ((uint16_t)22 << 10);
    p[1] = (24) | (20 << 5) | ((uint16_t)10 << 10);
    p[2] = (29) | (20 << 5) | ((uint16_t)4 << 10);
    p[3] = (3) | (2 << 5) | ((uint16_t)8 << 10);
    if (story_on && play_mode == MODE_STORY && RUN_DIFF)
        p[2] = RUN_DIFF == DIFF_EASY ? (6 | (24 << 5) | ((uint16_t)8 << 10)) : (30 | (5 << 5) | ((uint16_t)5 << 10));
    set_bkg_palette(BGPAL_HUD, 1, p);
}
