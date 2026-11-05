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
//   A at the venue whose shift was quit (pause.c QUIT TO MAP; smap_flags SMAP_RESUME): a panel RESUME / ENTER / BACK. RESUME restarts that shift (or mini-game)
//                                     from its start with the lives and the score it began with (story.c story_resume); ENTER starts the venue over as A does
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

#include "asm_cfg.h"
#include "game.h"
#include "music.h"
#include "story.h"
#include "mg.h"
#include "palettes.h"
#include "smap_art.h"
#include "smap_priv.h"
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
                                              // bit 7: the HUD palette is borrowed (smap_pal_back); bit 3: SMAP_RESUME
#define F_PLAYED(k)  (1 << (k))
#define F_GOLD(k)    (0x10 << (k))
#define F_PALS       0x80
#define F_SAVED      0x77                          // (SMAP_RESUME, game.h, is bit 3: a quit shift can be restarted; never saved)


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
static uint8_t walk_pic(void) { return pic_seq[((g16(V_FX) + g16(V_FY)) >> 2) & 3]; }   // (the feet follow the ground: a picture per 4 px, at any pace)

// A sprite entry written inline (a call with seven arguments costs more than the entry's four stores): px, py the top-left of the 8-px column's art on screen
// (it may lie off an edge: then the entry is hidden), vh its visible height; entries the window layer (wh lines from wy) covers are hidden too.
#define SPR(i, px, py, tl, pl, fl, vh) do { \
        OAM_item_t *o_ = shadow_OAM + (i); \
        if ((uint16_t)((px) + 7) < 167 && (uint16_t)((py) + (vh) - 1) < (uint16_t)(143 + (vh)) && !(wh && (py) < wend && (py) + (vh) > wy)) { \
            o_->y = (uint8_t)((py) + 16); o_->x = (uint8_t)((px) + 8); o_->tile = (tl); o_->prop = cgbp ? ((pl) | (fl)) : (fl); \
        } else o_->y = 0; } while (0)

// The same for the still sprites (the bang, the dots, the UFO): with no window up an entry stays live 16 px beyond the screen's edges (its y at least 1: 0 means hidden), because on
// the frames between two redraws oam_shift moves it with the camera and it slides in by itself.
#define SPRM(i, px, py, tl, pl, fl, vh) do { \
        OAM_item_t *o_ = shadow_OAM + (i); \
        if (wh ? ((uint16_t)((px) + 7) < 167 && (uint16_t)((py) + (vh) - 1) < (uint16_t)(143 + (vh)) && !((py) < wend && (py) + (vh) > wy)) \
               : ((uint16_t)((px) + 16) < 192 && (uint16_t)((py) + 15) < 175)) { \
            o_->y = (uint8_t)((py) + 16); o_->x = (uint8_t)((px) + 8); o_->tile = (tl); o_->prop = cgbp ? ((pl) | (fl)) : (fl); \
        } else o_->y = 0; } while (0)

// The camera moved by less than a cell: the live still sprites (entries OAM_BANG .. OAM_UFO + 2) move with it. dx, dy: how far they go on the screen.
// (The C twin is the loop below the #else.) A live entry never becomes 0 (hidden).
#if ASM_SMAP
static void oam_shift(int8_t dx, int8_t dy) __naked {
    (void)dx; (void)dy;
__asm
    ld   c, a
    ld   b, e
    ld   hl, #_shadow_OAM + 28              ; OAM_BANG * 4
    ld   e, #15                             ; the bang, 11 dots, the UFO's 3
1$:
    ld   a, (hl)
    or   a, a
    jr   z, 2$
    add  a, b
    jr   nz, 3$
    inc  a
3$:
    ld   (hl+), a
    ld   a, (hl)
    add  a, c
    ld   (hl+), a
    inc  hl
    inc  hl
    jr   4$
2$:
    inc  hl
    inc  hl
    inc  hl
    inc  hl
4$:
    dec  e
    jr   nz, 1$
    ret
__endasm;
}
#else
static void oam_shift(int8_t dx, int8_t dy) {
    uint8_t k, y;
    OAM_item_t *o = shadow_OAM + OAM_BANG;
    for (k = 0; k < 15; k++, o++) {
        y = o->y;
        if (!y) continue;
        y += dy;
        o->y = y ? y : 1;
        o->x += dx;
    }
}
#endif

// The dots' quick cull. a = the camera's cell column + 4 px, e = its row: bc = a mask (bit 5 + s set when stop s lies within the cull window, 21 + 2 + 2 cells wide and 19 + 2 + 2 tall);
// the entries of the others are hidden. (The C twin is the loop in draw_still. Asm: the compiler's 16-bit arithmetic made that loop 25 lines of the frame.)
#if ASM_SMAP
typedef char smap_dots_offsets[(OAM_DOTS == 8 && NSTOPS == 11) ? 1 : -1];
static uint16_t dots_near(uint8_t ccx, uint8_t ccy) __naked {
    (void)ccx; (void)ccy;
__asm
    ld   b, a
    ld   c, e
    ld   de, #0
    ld   hl, #_smapw_stopc
    ld   a, #32                             ; OAM_DOTS * 4: the low byte of the first dot's entry (shadow_OAM is at 0xC000)
    ld   (_story_scratch + 449), a          ; V_BCAP: the entry's low byte (free: the burst keeps no state in it)
1$:
    ld   a, (hl+)
    sub  a, b
    add  a, #2
    cp   a, #25
    jr   nc, 3$
    ld   a, (hl+)
    sub  a, c
    add  a, #2
    cp   a, #23
    jr   nc, 4$
    scf
    jr   5$
3$:
    inc  hl
4$:
    push hl
    ld   a, (_story_scratch + 449)
    ld   l, a
    ld   h, #0xC0
    ld   (hl), #0
    pop  hl
    or   a, a
5$:
    rr   d
    rr   e
    ld   a, (_story_scratch + 449)
    add  a, #4
    ld   (_story_scratch + 449), a
    cp   a, #76                             ; (OAM_DOTS + NSTOPS) * 4
    jr   nz, 1$
    ld   b, d
    ld   c, e
    ret
__endasm;
}
#endif

// The sprites that stand in the world, not on Sal: the bang over the tent, the stops' dots, the UFO. They only move when the camera does (or a window covers them): their entries stay
// in the shadow OAM between those frames.
static void draw_still(uint8_t wh, int16_t wy, int16_t wend) {
    uint8_t s, p = V(V_STATE), ccx, ccy, cgbp = is_cgb, tk = V(V_TICK);
    uint16_t near;
    int16_t ax, ay, cx = (int16_t)g16(V_CAMX), cy = (int16_t)g16(V_CAMY);
    const uint16_t *sp = &smapw_stop[0][0];
    const uint8_t *q = &smapw_stopc[0][0];
    OAM_item_t *o = shadow_OAM + OAM_DOTS;
    V(V_DOTS) = 0;
    if ((uint16_t)(SMAPW_BANG_X - cx + 16) < 192 && bang_wanted()) { ax = SMAPW_BANG_X - cx; ay = SMAPW_BANG_Y - cy; SPRM(OAM_BANG, ax, ay, OB + SOB_BANG0, PAL_BANG, 0, 8); }
    else shadow_OAM[OAM_BANG].y = 0;
    cx += 4; cy += 8;
    ccx = (uint8_t)(cx >> 3); ccy = (uint8_t)(cy >> 3);
#if ASM_SMAP
    near = dots_near(ccx, ccy) >> 5;
#else
    near = 0;
    for (s = 0; s < NSTOPS; s++, q += 2) {          // (the quick cull in cells: well off the screen)
        if ((uint8_t)(q[0] - ccx + 2) > 24 || (uint8_t)(q[1] - ccy + 2) > 22) o[s].y = 0; else near |= 1 << s;
    }
#endif
    for (s = 0; s < NSTOPS; s++, sp += 2, o++, near >>= 1) {   // the dots: green where Sal may go (the stops before the next, and the town), red at the next stop (on the cloud's edge); none beyond
        if (!(near & 1) || (s > p && s != TOWN)) continue;     // (their entries stay hidden: smap_enter)
        ax = (int16_t)sp[0] - cx;
        ay = (int16_t)sp[1] - cy;
        if (wh ? ((uint16_t)(ax + 7) >= 167 || (uint16_t)(ay + 7) >= 151 || (ay < wend && ay + 8 > wy)) : ((uint16_t)(ax + 16) >= 192 || (uint16_t)(ay + 15) >= 175)) { o->y = 0; continue; }
        o->y = (uint8_t)(ay + 16); o->x = (uint8_t)(ax + 8);
        if (s < p || s == TOWN) { o->tile = OB + SOB_DOT_OPEN0; o->prop = cgbp ? PAL_OPEN : 0; }
        else { o->tile = OB + SOB_DOT_LOCKED0; o->prop = cgbp ? PAL_LOCKED : 0; }
    }
    cx -= 4; cy -= 8;
    if (p >= 10 && (uint16_t)(SMAPW_UFO_X - cx + 40) < 216) {   // the UFO over the space lounge, once that is open (bobbing 1 px)
        ax = SMAPW_UFO_X - cx; ay = SMAPW_UFO_Y + ((tk >> 5) & 1) - cy;
        SPRM(OAM_UFO, ax, ay, OB + SOB_UFO0, PAL_UFO, 0, 16);
        ax += 8;
        SPRM(OAM_UFO + 1, ax, ay, OB + SOB_UFO1, PAL_UFO, 0, 16);
        ax += 8;
        SPRM(OAM_UFO + 2, ax, ay, OB + SOB_UFO2, PAL_UFO, 0, 16);
    } else if (p >= 10) { shadow_OAM[OAM_UFO].y = 0; shadow_OAM[OAM_UFO + 1].y = 0; shadow_OAM[OAM_UFO + 2].y = 0; }
}

static void draw(void) {
    uint8_t s, d, n = 0, t, ccx, ccy, p = V(V_STATE), pic = 0, nudge, panel = V(V_PANEL), wh = V(V_WH), cgbp = is_cgb, tk = V(V_TICK);
    int16_t sx, sy, ax, ay, cx = (int16_t)g16(V_CAMX), cy = (int16_t)g16(V_CAMY), wy = V(V_WY), wend = (int16_t)V(V_WY) + wh;
    const uint16_t *sp = &smapw_stop[0][0];
    sx = (int16_t)g16(V_FX) - 8 - cx;               // Sal's top-left on the screen
    sy = (int16_t)g16(V_FY) - 24 - cy;
    nudge = (tk >> 4) & 1;                          // (the arrows bob 1 px every 16 frames, the UFO every 32)
    if (V(V_WALK)) pic = walk_pic();
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
    V(V_FULL) = 0;
    if (V(V_DOTS) || wh) draw_still(wh, wy, wend);
    if (panel && V(V_DONE) && panel != P_NUDGE) {  // the selection arrow, at the selected line's left
        s = V(V_PANEL) == P_VENUE ? 2 : 1;
        put(OAM_CURSOR, 8, V(V_WY) + (s + V(V_SEL)) * 8, OB + SOB_ARROW_R0, PAL_ARROW, 0, 8);
    } else shadow_OAM[OAM_CURSOR].y = 0;
}

// A walking frame on which the camera did not move and no window is up: only Sal's four entries change (the rest of the sprites keep their place in the shadow OAM)
static void draw_walk(void) {
    uint8_t t = walk_pic() * BARTENDER_TILES_PER_FRAME, cgbp = is_cgb, wh = 0;
    int16_t sx = (int16_t)g16(V_FX) - 8 - (int16_t)g16(V_CAMX), sy = (int16_t)g16(V_FY) - 24 - (int16_t)g16(V_CAMY), ay, wy = 0, wend = 0;
    SPR(OAM_SAL, sx, sy, t, OBJPAL_BARTENDER, 0, 16);
    SPR(OAM_SAL + 1, sx + 8, sy, t + 2, OBJPAL_BARTENDER, 0, 16);
    ay = sy + 16;
    SPR(OAM_SAL + 2, sx, ay, t + 4, OBJPAL_BARTENDER, 0, 8);
    SPR(OAM_SAL + 3, sx + 8, ay, t + 6, OBJPAL_BARTENDER, 0, 8);
    if (V(V_DOTS)) draw_still(0, 0, 0);
}

// the UFO's bob (draw_still: its y is one px lower in the odd 32-frame spans of the tick): its live entries move 1 px, nothing is drawn again
static void ufo_bob(void) {
    uint8_t k, up = (V(V_TICK) >> 5) & 1;
    OAM_item_t *o = shadow_OAM + OAM_UFO;
    for (k = 0; k < 3; k++, o++) if (o->y) o->y = up ? o->y + 1 : o->y - 1;
}

// ---- the window layer ---------------------------------------------------------------------------------------------------------------------------------------
static void win_show(uint8_t y, uint8_t h, uint8_t lyc) {   // the window over lines y .. y + h - 1; lyc: where the LCD interrupt cuts it (LYC_NONE: at the screen's end)
    WX_REG = 7; WY_REG = y; LYC_REG = lyc;
    V(V_WY) = y; V(V_WH) = h; V(V_DOTS) = V(V_FULL) = 1;
    overlay_on = 3;                                // (1 would hide the sprites over the banner, 2 is a note: main.c)
}

static void win_hide(void) {
    overlay_on = 0; HIDE_WIN;
    WY_REG = BANNER_WY; LYC_REG = BANNER_LYC;      // (the banner window's own place again)
    WX_REG = 7;
    V(V_WH) = 0; V(V_TAG) = 0; V(V_DOTS) = V(V_FULL) = 1;
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
    case P_RESUME:                                 // a shift was quit from the pause menu (pause.c QUIT TO MAP): restart it, the venue over, or nothing
        put_text(blank_row(ROW(1)), 3, "RESUME", 0);
        put_text(blank_row(ROW(2)), 3, "ENTER", 0);
        put_text(blank_row(ROW(3)), 3, "BACK", 0);
        n = 5;
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

// ---- the camera, the region, the walk ------------------------------------------------------------------------------------------------------------------------------------

static void stretch_init(void);
static void start_walk(uint8_t d) {
    uint8_t t = smapw_exit[smap_stop][d], e = smapw_exit_leg[smap_stop][d], leg = e & 0x7F, rev = e >> 7;
    if (t == NIL || !open_stop(t)) return;
    V(V_LEG) = leg; V(V_REV) = rev; V(V_DEST) = t;
    V(V_WK) = rev ? smapw_leg_n[leg] - 2 : 1;        // the waypoint after the one Sal stands on
    V(V_WALK) = 1; V(V_LAG) = 0; V(V_RATE) = is_cgb ? 16 : 2; V(V_DOTS) = V(V_FULL) = 1;
    stretch_init();
    if (V(V_TAG)) V(V_TAG) = 1;                      // (the name tag goes when Sal sets off: a frame that runs late would drop the window for a frame: a flicker)
    SFX(SFX_DON);
}

// ---- the walk ------------------------------------------------------------------------------------------------------------------------------------------------------------
// The state of the stretch Sal is on lives in a few bytes (nothing is looked up again each frame): V_WT the px walked on it, V_LEN its length, and the flags in V_LAG:
//   bit 0 a hold (Sal waited this frame: ly_ok lifts its line), 1 the camera may cross a cell line this frame, 2 the stretch runs along x, 3 toward larger coordinates,
//   4 it is the leg's first, 5 its last, 6 / 7 the next stretch runs along x / toward larger coordinates.
#define F_HOLD  1
#define F_CROSS 2
#define F_HZ    4
#define F_UP    8
#define F_FIRST 16
#define F_LAST  32
#define F_NHZ   64
#define F_NUP   128

// the stretch that ends at waypoint V_WK (Sal stands at the one before it)
static void stretch_init(void) {
    uint8_t leg = V(V_LEG), k = V(V_WK), rev = V(V_REV), ln = smapw_leg_n[leg], f = V(V_LAG) & F_HOLD, hz;
    const uint16_t *p = smapw_leg_pt[leg][k], *s = smapw_leg_pt[leg][rev ? k + 1 : k - 1], *q;
    uint16_t a, b;
    hz = p[0] != s[0];
    a = hz ? s[0] : s[1]; b = hz ? p[0] : p[1];
    if (hz) f |= F_HZ;
    if (b > a) { f |= F_UP; V(V_LEN) = (uint8_t)(b - a); } else V(V_LEN) = (uint8_t)(a - b);
    if (rev ? k == ln - 2 : k == 1) f |= F_FIRST;
    if (rev ? !k : k + 1 == ln) f |= F_LAST;
    else {
        q = smapw_leg_pt[leg][rev ? k - 1 : k + 1];
        if (q[1] == p[1]) { f |= F_NHZ; if (q[0] > p[0]) f |= F_NUP; }
        else if (q[1] > p[1]) f |= F_NUP;
    }
    V(V_LAG) = f;
    V(V_WT) = 0;
}

// the region loads ahead in the direction of the stretch (the camera may still stand: the world's edge, the first frames); the other axis keeps its lead, and bit 2 of the
// vertical direction asks for the rows first
static void walk_dirs(void) {
    uint8_t f = V(V_LAG);
    if (f & F_HZ) { V(V_DIRX) = f & F_UP ? 2 : 1; V(V_DIRY) &= 3; }
    else V(V_DIRY) = (f & F_UP ? 2 : 1) | 4;
    if (V(V_LEN) - V(V_WT) <= WALK_AHEAD && !(f & F_LAST)) {   // the stretch after this one: its direction too, so that its first line is loaded when Sal turns
        if (f & F_NHZ) V(V_DIRX) = f & F_NUP ? 2 : 1;      // (the lines of this stretch come first: a vertical one keeps its rows-first bit)
        else V(V_DIRY) = (V(V_DIRY) & 4) | (f & F_NUP ? 2 : 1);
    }
    V(V_LAG) = (f & ~F_CROSS) | (((f & F_HZ ? V(V_CAMX) : V(V_CAMY)) & 6) == 6 ? F_CROSS : 0);   // (a camera 6 or 7 px into a cell may cross its line: the still sprites are all drawn again: ly_ok)
}

// One step of the walk, after this frame's region work (smap_update): as fast as the stream allows. 2 px, or 1 or 1 in 2 or 1 in 4 frames where the line the camera will want
// is not loaded yet and the cells it still needs, at the rate the job has been going, would not be done in time; none when not even the next px is covered (a hold, which ly_ok
// reads: the work then ignores its line). The first and the last WALK_EASE px of a leg go at 1.
void walk_step(void) {
    uint8_t f = V(V_LAG), n = WALK_SPD, r, hz = f & F_HZ, d = V(V_LEN) - V(V_WT), rem, kr, wt = V(V_WT);
    uint16_t pos = g16(hz ? V_FX : V_FY), w, sl;
    if (((f & F_FIRST) && wt < WALK_EASE) || ((f & F_LAST) && d <= WALK_EASE)) n = 1;
    if (n > d) n = d;
    r = smap_room(hz, f & F_UP, pos);
    if (d <= WALK_AHEAD && !(f & F_LAST)) {          // a corner ahead: the room is what Sal can walk before either line he needs is missing (the stretch after: from the corner)
        w = smap_room((f & F_NHZ) != 0, f & F_NUP, g16(hz ? V_FY : V_FX));
        if (w + d < r) r = (uint8_t)(w + d);
    }
    f = f & ~F_HOLD;
    if (!r) f |= F_HOLD;
    V(V_LAG) = f;
    if (!r) return;                                  // (a hold)
    if (n > r) n = r;
    // the cells the line being loaded still needs (rem) at the rate the job has been going (kr cells a frame, V_RATE), against the px of room (r) at the pace, WALK_S frames to spare
    rem = V(V_JK) ? V(V_JN) - V(V_JP) : 0;           // (the job's cells left: a line of the other axis, loaded for the next stretch, goes first and then the line this stretch wants:)
    if (V(V_JK) != (hz ? J_COL : J_ROW) ? r < 8 : 0) rem += WALK_LINE;
    else if (!V(V_JK) && r < 8) rem = WALK_LINE;
    if (rem) {
        kr = V(V_RATE) ? V(V_RATE) : 1;
        w = (uint16_t)r * kr;
        sl = (uint16_t)kr * (is_cgb ? WALK_SC : WALK_S);
        if (n > 1 && w < ((uint16_t)rem << 1) + (sl << 1)) n = 1;
        if (n == 1 && w < rem + sl && (V(V_TICK) & 1)) return;
        if (n == 1 && w + w < rem + sl && (V(V_TICK) & 2)) return;
        if (n == 1 && (w << 2) < rem + sl && (V(V_TICK) & 4)) return;
    }
    s16(hz ? V_FX : V_FY, f & F_UP ? pos + n : pos - n);
    V(V_WT) = wt + n;
    if (n != d) return;
    if (f & F_LAST) {                                // the last waypoint: Sal is there
        smap_stop = V(V_DEST);
        V(V_WALK) = 0; V(V_DOTS) = V(V_FULL) = 1;
        tag_show();
    } else { V(V_WK) = V(V_REV) ? V(V_WK) - 1 : V(V_WK) + 1; stretch_init(); }
}

// ---- leaving ---------------------------------------------------------------------------------------------------------------------------------------------------------
static void leave(void) {                          // before any other screen: the window and its interrupt as the game keeps them, the scroll back, the map block saved
    win_hide();
    if (TRANS & TR_OFF) { SCX_REG = 0; SCY_REG = 0; }   // (else the scene change's cover shows the map as it stands and the scroll goes home once the LCD is off: src/trans.c)
    sm_put(smap_stop, smap_flags & F_SAVED);
}

static uint8_t press_a(void) {                     // A with no panel up. 1: the screen was left
    uint8_t s = smap_stop;
    if (s == TOWN) { panel_open(P_TOWN, 0); return 0; }
    if ((smap_flags & SMAP_RESUME) && s == story_chapter && s == map_progress()) { panel_open(P_RESUME, 0); return 0; }   // (a shift of this venue was quit)
    if (s < map_progress()) { panel_open(P_VENUE, 0); return 0; }
    if (s > map_progress()) return 0;              // (a locked stop: Sal never stands on one)
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
        leave(); smap_flags &= ~SMAP_RESUME; story_map_pouroff();
        return 1;
    }
    if (kind == P_NUDGE) { leave(); smap_flags &= ~SMAP_RESUME; story_map_pouroff(); return 1; }
    if (kind == P_RESUME) {
        if (sel == 2) { panel_close(); return 0; }
        leave();
        smap_flags &= ~SMAP_RESUME;
        if (sel) story_map_venue(smap_stop);       // ENTER: the venue over, as A at the next venue
        else story_resume();                       // RESUME: the shift that was quit, from its start
        return 1;
    }
    if (kind == P_MENU) {
        if (!sel) { panel_close(); return 0; }
        leave();                                   // (the map block is saved: CONTINUE comes back to this stop) then as pause.c's quit of a story run
        story_phase = 0; story_on = 0; story_arc = 0;
        smap_flags &= ~F_PALS;
        hud_pal_reset();
        if (save_lock == SAVE_LOCK_DEBUG) story_chapter |= DEBUG_RESUME;   // a debug-select run saved nothing: CONTINUE resumes it (story_begin)
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
    uint8_t kind = V(V_PANEL), sel = V(V_SEL), n = kind == P_TOWN || kind == P_VENUE || kind == P_MENU ? 2 : kind == P_FEST || kind == P_RESUME ? 3 : 1;
    if (!V(V_DONE)) return;
    if ((pressed & J_UP) && sel) V(V_SEL) = sel - 1;
    else if ((pressed & J_DOWN) && sel + 1 < n) V(V_SEL) = sel + 1;
    if (V(V_SEL) != sel) SFX(SFX_KA);
}

// ---- the screen -------------------------------------------------------------------------------------------------------------------------------------------------------
// One frame (story.c story_update, STORY_PHASE_MAP). 1: the screen was left (the next one is up).
uint8_t smap_update(uint8_t pressed) BANKED {
    uint8_t d;
    uint16_t ocx, ocy;
    V(V_NSTG) = 0; V(V_PALQ) = 0; V(V_SLOW) = 0; V(V_TICK)++;
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
    if (!V(V_WALK)) {
        d = (pressed & J_UP) ? 0 : (pressed & J_DOWN) ? 1 : (pressed & J_LEFT) ? 2 : (pressed & J_RIGHT) ? 3 : 4;
        if (d < 4) start_walk(d);
        else if ((pressed & J_A) && press_a()) return 1;
        else if (pressed & J_START) panel_open(P_MENU, 0);
    }
    if (!V(V_PANEL) && !vq_held) {
        if (V(V_WALK)) walk_dirs();
        smap_region_work();                                  // (first: a line that is done this frame lets the camera step into it this frame, Sal never waits on a camera that was blocked a frame ago)
        if (V(V_WALK)) walk_step();
        ocx = g16(V_CAMX); ocy = g16(V_CAMY);
        if (smap_camera_step()) {
            SC(S_T + T_CAM)[0] = (uint8_t)g16(V_CAMY); SC(S_T + T_CAM)[1] = (uint8_t)g16(V_CAMX);
            qraw(0, SC(S_T + T_CAM), 0xFF42, 2);
            if ((ocx >> 3) != (g16(V_CAMX) >> 3) || (ocy >> 3) != (g16(V_CAMY) >> 3) || V(V_WH)) V(V_DOTS) = 1;      // (another cell: all the still sprites are looked at again)
            else oam_shift((int8_t)(ocx - g16(V_CAMX)), (int8_t)(ocy - g16(V_CAMY)));
        }
        if (!(V(V_TICK) & 31) && V(V_STATE) >= 10) ufo_bob();            // (the UFO bobs 1 px every 32 frames)
    }
    if (V(V_WALK) && !V(V_FULL) && !V(V_WH)) draw_walk();
    else { if (!V(V_WALK)) V(V_DOTS) = 1; draw(); }          // (standing still: the bang, the dots and the UFO follow the progress and the tick)
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
    if (smap_stop >= NSTOPS || !open_stop(smap_stop)) smap_stop = map_progress() < NSTOPS - 1 ? map_progress() : TOWN;
    V(V_STATE) = map_progress() < 9 ? map_progress() + 1 : 10;
    s16(V_FX, smapw_stop[smap_stop][0]); s16(V_FY, smapw_stop[smap_stop][1]);
    smap_cam_target(&tx, &ty);
    s16(V_CAMX, tx); s16(V_CAMY, ty);
    V(V_C0) = tx >> 3; V(V_C1) = V(V_C0) - 1;      // the view's cells, column by column (no lines ahead yet: the walk asks for them)
    V(V_R0) = ty >> 3; V(V_R1) = (ty + 143) >> 3;
    smap_pin_town();                               // (Color: the town palette is held for good: it is the window layer's)
    smap_fill_view((uint8_t)(tx >> 3), (uint8_t)((tx + 159) >> 3));
    SCX_REG = (uint8_t)tx; SCY_REG = (uint8_t)ty;
    V(V_DOTS) = V(V_FULL) = 1;
    V(V_PREV) = 1;                                 // (the arrival tag is queued by the first frame: the transition's reveal has put the window rows back by then)
    story_phase = STORY_PHASE_MAP;
    game_state = GS_STORY;
    draw();
    DISPLAY_ON;
}

// A mini-game that the map started is over (mg.c, LCD off) or was quit (pause.c): the map again, the story's score as the map left it (a replay's points are
// not the story's: the medal's upgrade is, in save.c)
void smap_back(void) BANKED {
    score = save_lock ? 0 : venue_score_get(story_progress);   // (a debug-select run saves none: it was entered with 0)
    split6(score_digits, score);
    smap_enter(1);
}

// a new story run: Sal at the town, no festival game played or won yet
void smap_new_run(void) BANKED {
    smap_stop = TOWN; smap_flags &= F_PALS;
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
