// MARSHMALLOW DROP, the igloo's mini-game (docs/minigames_bosses.md 4.5; art approved by the owner 2026-10-12: the hybrid with
// Tin cups, the hoist-pail dropper, Aurora in the serving hatch, the ice bricks and A's COCOA BAR sign; aurora window W1).
// Cocoa cups ride a conveyor to the right under a pail that slides along a rail; A drops a marshmallow straight down. Three
// make a perfect cocoa; a fourth splashes.
//
// Rules (the spec's numbers, 1/8 px units in the code):
// - The pail slides between x 16 and 136 at 1.0 px/f (0-15 s), 1.25 (15-30 s), 1.5 (30-45 s), reversing at the ends.
// - A drops a marshmallow from the pail (its top-left at the pail's x + 4, y 51) at 2 px/f: it reaches the cups' rim (y 95)
//   22 frames later. One in the air at a time; the next is loaded 24 frames after the last one landed (a press before that does
//   nothing): a drop every 46 frames at best, the spec's "at most ~58 drops" (counted from the drop it would be 112, and a mash
//   would earn a silver medal).
// - Cups ride right at 0.5 px/f (0-15 s), 0.75, 1.0, 48-72 px apart (seeded, never under 48: at most 4 cups share the screen,
//   a partly visible one counts, so a cup line has at most 8 cup entries + the falling marshmallow = 9 of the 10).
// - A hit: the marshmallow's centre within the cup's 12 px opening (cup x - 1 .. cup x + 11 for the marshmallow's left edge...
//   precisely: -1 <= marshmallow x - cup x <= 11, the marshmallow 8 px wide, the opening centred 8.5 px into the 16 px cup).
//   Cups hold 0-3. +100 for each marshmallow that lands, +300 for the third ("PERFECT COCOA": a pop, the HUD tally +1). A
//   fourth into a cup splashes it: -100 (never below what this game earned); that cup takes nothing more.
//   (Changed from the spec's text, following the approved mock-up: points are banked as the marshmallows land, not when the
//   cup leaves, so every drop pays at once; the totals are the same for every cup that leaves.)
// - 45 s. Medal by score (spec): GOLD >= 6000, SILVER >= 4000, BRONZE >= 2000. One setting (the spec has no HARD).
//
// Screen (the approved mock-up): HUD row 0 (score; the perfect tally: a marshmallow icon, X and 2 digits at columns 9-12; the
// timer at 16-19); the ice-brick wall rows 1-13 with the aurora window at columns 1-6, rows 1-4 (CGB BG palettes 6 green and
// 7 magenta; it shimmers 0 1 2 1 every 10 frames: the 3 frames' tiles are all in VRAM and each step rewrites the 24 map
// cells), the COCOA BAR / 3 PERFECT sign (HUD glyphs on the HUD panel) at columns 8-19, rows 1-4 (the framework's banner text
// covers the window and the sign's rows 2-3 until the first play frame), the wooden beam on row 5, Aurora's serving hatch at
// columns 17-19 rows 8-10, the conveyor row 14 (2 phases, the map row swaps), the wood panel row 15 and the floor rows 16-17.
// OAM: 0-3 the pops, 4 the falling marshmallow, 5 the loaded one, 6-7 the pail, 8-17 the cups (5 x 2 entries). CGB OBJ
// palettes 1 cups, 2 pail, 3 marshmallows and pops. DMG: cups and pail on OBP1 (set here, 0xE0), marshmallows and pops on OBP0.
// Tiles: BG MM_BG (MG_GAME_BG, ids 125-219 of 256), OBJ OBJ_MUG.. (18 entries) and OBJ_DANCER.. (the rest); all put back by
// the next level load.
#pragma bank 255
#include <gb/gb.h>
#include <gb/cgb.h>
#include <stdint.h>

#include "game.h"
#include "music.h"
#include "mg.h"
#include "mm_art.h"         // this bank's own art (assets/art/marshmallow/*.txt)

#define S               (MG->mm)
#define MM_BG           MG_GAME_BG
#define MM_LO           ((OBJ_COIN - OBJ_MUG) / 2)      // 8x16 entries that fit in the 56-91 block (18)
typedef char mm_fits[(MM_BG + MM_BG_TILES <= 256 && (OBJ_MUG & 1) == 0 && (OBJ_DANCER & 1) == 0
                      && MM_OBJ_ENTRIES >= MM_LO && 2 * (MM_OBJ_ENTRIES - MM_LO) <= 128 - OBJ_DANCER
                      && sizeof(struct mm_state) <= STORY_SCRATCH) ? 1 : -1];
#define MM_TIME_S      45
#define MM_PAIL_MIN   (16 * 8)
#define MM_PAIL_MAX   (136 * 8)
#define MM_PAIL_Y      40
#define MM_PUFF_Y0     51                   // the marshmallow's top at the drop; + 2 a frame
#define MM_FALL        22                   // frames to the rim
#define MM_RELOAD      24
#define MM_CUP_Y       96
#define MM_POP_Y       80
#define MM_POP_LEN     40
#define MM_SPAWN_X    (-16)
#define MM_END_X       160
#define MM_GAP_MIN     48
#define MM_SPLASH_SLOW 24
#define MM_PTS_HIT    100
#define MM_PTS_PERFECT 300
#define MM_PTS_SPLASH 100
#define OAM_POP         0
#define OAM_FALL        4
#define OAM_HELD        5
#define OAM_PAIL        6
#define OAM_CUP         8
#define OPAL_CUP        1
#define OPAL_PAIL       2
#define OPAL_PUFF       3
#define MM_ROW_BELT    14
#define MM_WIN_COL      1
#define MM_WIN_ROW      1
extern uint32_t score;
extern uint8_t score_digits[6];
#define RGB15(r, g, b) ((uint16_t)((r) | ((g) << 5) | ((b) << 10)))
#define HEX(v)  RGB15(((v) >> 19) & 31, ((v) >> 11) & 31, ((v) >> 3) & 31)

static const uint16_t pal_brick[4] = { HEX(0x484078UL), HEX(0x554C8CUL), HEX(0x90C8E8UL), HEX(0x285080UL) };
static const uint16_t pal_wood[4]  = { HEX(0xF0D8A8UL), HEX(0xC89860UL), HEX(0x8A5A30UL), HEX(0x40240FUL) };
static const uint16_t pal_belt[4]  = { HEX(0xFFF4E0UL), HEX(0xF0D8C8UL), HEX(0x5A98C0UL), HEX(0x141830UL) };
static const uint16_t pal_green[4] = { HEX(0xE8F8FFUL), HEX(0x40E090UL), HEX(0x17805AUL), HEX(0x0A1230UL) };
static const uint16_t pal_mag[4]   = { HEX(0xE8F8FFUL), HEX(0xF060D0UL), HEX(0x8A2C9CUL), HEX(0x0A1230UL) };
static const uint16_t pal_cup[4]   = { 0, HEX(0xFFFFFFUL), HEX(0x58A8E8UL), HEX(0x2A1830UL) };
static const uint16_t pal_pail[4]  = { 0, HEX(0xFFF4E0UL), HEX(0xB86038UL), HEX(0x301810UL) };
static const uint16_t pal_puff[4]  = { 0, HEX(0xFFFFFFUL), HEX(0xF890B8UL), HEX(0x4A2840UL) };
static const uint8_t shimmer[4] = { 0, 1, 2, 1 };                 // the window frames in order
static const char sign_a[] = "COCOA BAR", sign_b[] = "3 PERFECT";  // columns 9-17, rows 2 and 3

static void put(const uint8_t *t, uint8_t col, uint8_t row, uint8_t n) {   // LCD on: the queue; off: at once
    if (LCDC_REG & LCDCF_ON) { vq_add(0, t, col, row, n); return; }
    vram_put(col, row, t, n);
}

static uint8_t cell(uint8_t r, uint8_t c) {         // the BG tile id of map row r (1-17), column c: the sign's panel is a glyph
    uint8_t m = mm_map[(r - 1) * 20 + c];
    if (m != 255) return MM_BG + m;
    if (r == 2 && c >= 9 && c < 9 + sizeof(sign_a) - 1) return glyph_for(sign_a[c - 9]);
    if (r == 3 && c >= 9 && c < 9 + sizeof(sign_b) - 1) return glyph_for(sign_b[c - 9]);
    return glyph_for(' ');
}

static void row_tiles(uint8_t r, uint8_t *dst) {
    uint8_t c;
    for (c = 0; c < 20; c++) dst[c] = cell(r, c);
}

static uint8_t otile(uint8_t e) {                   // OBJ tile id of 8x16 entry e (two blocks of VRAM)
    return e < MM_LO ? OBJ_MUG + 2 * e : OBJ_DANCER + 2 * (e - MM_LO);
}

static uint8_t cgb(uint8_t pal) { return is_cgb ? pal : S_PALETTE; }   // an OBJ prop: CGB palette, DMG OBP1
static uint8_t cgb0(uint8_t pal) { return is_cgb ? pal : 0; }          // (DMG OBP0)

static void obj(uint8_t oam, int16_t x, uint8_t y, uint8_t e, uint8_t prop) {   // one 8x16 entry, px top-left; off-screen: hidden
    OAM_item_t *o = shadow_OAM + oam;
    if (x < -7 || x >= 160) { o->y = 0; return; }
    o->y = y + 16; o->x = (uint8_t)(x + 8); o->tile = otile(e); o->prop = prop;
}

static void obj2(uint8_t oam, int16_t x, uint8_t y, const uint8_t *e, uint8_t prop) {   // a 16x16: two entries
    obj(oam, x, y, e[0], prop);
    obj(oam + 1, x + 8, y, e[1], prop);
}

static void hide(uint8_t oam) { shadow_OAM[oam].y = 0; }

static void hud_tally(void) {
    uint8_t p = S.perfect, t = 0;
    if (p > 99) p = 99;
    while (p >= 10) { p -= 10; t++; }
    S.hud[0] = TILE_GLYPH_0 + t; S.hud[1] = TILE_GLYPH_0 + p;
    put(S.hud, 11, HUD_ROW, 2);
}

static void new_cup(int16_t x) {
    uint8_t k;
    for (k = 0; k < MM_MUGS; k++)
        if (!S.on[k]) {
            S.on[k] = 1; S.n[k] = 0; S.spl[k] = 0; S.pop[k] = 0; S.cx[k] = x * 8; S.lead = k;
            return;
        }
}

static uint8_t gap(void) { return MM_GAP_MIN + mg_rand() % 25; }       // 48..72

static void sprites(void) {
    uint8_t k, f, np = 0;
    int16_t x;
    // the pail (swings every 6 frames) and the loaded marshmallow
    x = S.dx >> 3;
    obj2(OAM_PAIL, x, MM_PAIL_Y, mm_pail + 2 * ((S.anim / 6) & 1), cgb(OPAL_PAIL));
    if (!S.air && !S.load && mg_phase <= MG_PLAY) obj(OAM_HELD, x + 4, MM_PUFF_Y0, mm_puff[0], cgb0(OPAL_PUFF));
    else hide(OAM_HELD);
    if (S.air) obj(OAM_FALL, S.ax, MM_PUFF_Y0 + 2 * S.t, mm_puff[(S.t >> 1) & 1], cgb0(OPAL_PUFF));
    else hide(OAM_FALL);
    hide(OAM_POP); hide(OAM_POP + 1); hide(OAM_POP + 2); hide(OAM_POP + 3);
    for (k = 0; k < MM_MUGS; k++) {
        if (!S.on[k]) { hide(OAM_CUP + 2 * k); hide(OAM_CUP + 2 * k + 1); continue; }
        x = S.cx[k] >> 3;
        if (S.spl[k]) f = 4 + (S.spl[k] < MM_SPLASH_SLOW ? (S.spl[k] >> 2) & 1 : 1);
        else f = S.n[k];
        obj2(OAM_CUP + 2 * k, x, MM_CUP_Y, mm_cup + 2 * f, cgb(OPAL_CUP));
        if (S.pop[k] && np < 2) {
            obj2(OAM_POP + 2 * np, x, MM_POP_Y, mm_pop + 2 * (((MM_POP_LEN - S.pop[k]) / 6) & 1), cgb0(OPAL_PUFF));
            np++;
        }
    }
}

static void penalty(void) {                              // -100, never below what this game earned
    uint16_t n = mg_score < MM_PTS_SPLASH ? mg_score : MM_PTS_SPLASH;
    mg_score -= n;
    score -= n;
    split6(score_digits, score);
    hud_dirty |= HUD_SCORE;
    prep_hud();
}

static void win_rows(uint8_t f) {                        // the aurora window's frame f: the 4 map rows of 6 tiles
    uint8_t r, c;
    for (r = 0; r < 4; r++) {
        for (c = 0; c < 6; c++) S.win[r][c] = MM_BG + mm_win[f * 24 + r * 6 + c];
        put(S.win[r], MM_WIN_COL, MM_WIN_ROW + r, 6);
    }
}

static void belt_row(uint8_t ph) {
    put(S.belt[ph], 1, MM_ROW_BELT, 18);
}

void mm_enter(void) BANKED {
    uint8_t r, c;
    int16_t x;
    set_bkg_data(MM_BG, MM_BG_TILES, mm_bg_tiles);
    set_sprite_data(OBJ_MUG, 2 * MM_LO, mm_obj_tiles);
    set_sprite_data(OBJ_DANCER, MM_OBJ_TILES - 2 * MM_LO, mm_obj_tiles + 32 * MM_LO);
    for (r = 1; r <= 17; r++) {                           // the screen, row by row (the framework drew its own backdrop)
        row_tiles(r, row_buf);
        vram_put(0, r, row_buf, 20);
    }
    if (is_cgb) {
        VBK_REG = VBK_BANK_1;
        for (r = 1; r <= 17; r++) {
            if (r == 2 || r == 3) continue;                   // (the banner's: the HUD colours, until the first play frame)
            for (c = 0; c < 20; c++) row_buf[c] = mm_pal[(r - 1) * 20 + c];
            vram_put(0, r, row_buf, 20);
        }
        VBK_REG = VBK_BANK_0;
        set_bkg_palette(2, 1, pal_brick);
        set_bkg_palette(3, 1, pal_wood);
        set_bkg_palette(5, 1, pal_belt);
        set_bkg_palette(6, 1, pal_green);
        set_bkg_palette(7, 1, pal_mag);
        set_sprite_palette(OPAL_CUP, 1, pal_cup);
        set_sprite_palette(OPAL_PAIL, 1, pal_pail);
        set_sprite_palette(OPAL_PUFF, 1, pal_puff);
    } else OBP1_REG = 0xE0;                               // cups, pail: white, dark grey, black (the level load puts 0xE4 back)
    // the HUD tally: the icon, X, two digits at columns 9-12
    row_buf[0] = MM_BG + MMB_ICON; row_buf[1] = TILE_GLYPH_X;
    vram_put(9, HUD_ROW, row_buf, 2);
    S.perfect = 0;
    hud_tally();
    // the belt's two phases (columns 1-18 of row 14) and the banner rows' scene (restored at the first play frame)
    for (c = 0; c < 18; c++) { S.belt[0][c] = MM_BG + MMB_BELT0; S.belt[1][c] = MM_BG + MMB_BELT1; }
    row_tiles(2, S.wall[0]); row_tiles(3, S.wall[1]);
    for (c = 0; c < 20; c++) { S.wattr[0][c] = mm_pal[20 + c]; S.wattr[1][c] = mm_pal[40 + c]; }
    // the game
    mg_timer = MM_TIME_S * 60;
    S.dx = 76 * 8; S.dir = 1; S.air = 0; S.load = 0; S.t = 0; S.ax = 0; S.anim = 0; S.started = 0; S.wstep = 0; S.bph = 0;
    S.drops = 0; S.hits = 0; S.splashes = 0; S.gone = 0;
    for (c = 0; c < MM_MUGS; c++) S.on[c] = 0;
    x = 88;                                               // a first cup mid-belt, the rest behind it at 48-72 px
    for (;;) {
        new_cup(x);
        S.gapn = gap();
        if (x - S.gapn < MM_SPAWN_X) break;
        x -= S.gapn;
    }
    sprites();
}

static void exits(void) {                                 // cups past the right edge are gone
    uint8_t k;
    for (k = 0; k < MM_MUGS; k++)
        if (S.on[k] && (S.cx[k] >> 3) >= MM_END_X) { S.on[k] = 0; S.gone++; }
}

static void land(void) {                                  // the marshmallow at the rim: hits a cup (or the belt)
    uint8_t k;
    int16_t d;
    S.air = 0; S.load = MM_RELOAD;                        // the next is loaded 24 frames after this one lands
    for (k = 0; k < MM_MUGS; k++) {
        if (!S.on[k] || S.spl[k]) continue;
        d = S.ax - (S.cx[k] >> 3);
        if (d < -1 || d > 11) continue;
        S.hits++;
        if (S.n[k] == 3) {                                // the fourth: a splash
            S.spl[k] = 1; S.splashes++;
            penalty();
            SFX(SFX_BREAK);
            return;
        }
        S.n[k]++;
        mg_points(MM_PTS_HIT);
        if (S.n[k] == 3) {                                // PERFECT COCOA
            mg_points(MM_PTS_PERFECT);
            S.perfect++;
            S.pop[k] = MM_POP_LEN;
            hud_tally();
            SFX(SFX_COIN);
        } else SFX(SFX_CATCH);
        return;
    }
}

void mm_update(uint8_t pressed) BANKED {
    uint8_t k, st, want, spd;
    uint16_t el;
    if (!S.started) {                                     // the first frame: the banner rows (the framework's text) are the scene again
        S.started = 1;
        vq_add(0, S.wall[0], 0, 2, 20); vq_add(0, S.wall[1], 0, 3, 20);
        if (is_cgb) { vq_add(1, S.wattr[0], 0, 2, 20); vq_add(1, S.wattr[1], 0, 3, 20); }
    }
    S.anim++;
    if (mg_phase == MG_PLAY) {
        el = MM_TIME_S * 60 - mg_timer;                   // frames played: the speed steps at 15 s and 30 s
        st = el >= 1800 ? 2 : (el >= 900 ? 1 : 0);
        spd = 8 + 2 * st;                                  // the pail: 1.0, 1.25, 1.5 px a frame (1/8 px)
        S.dx += S.dir * spd;
        if (S.dx >= MM_PAIL_MAX) { S.dx = MM_PAIL_MAX; S.dir = -1; }
        if (S.dx <= MM_PAIL_MIN) { S.dx = MM_PAIL_MIN; S.dir = 1; }
        spd = 4 + 2 * st;                                  // the cups: 0.5, 0.75, 1.0
        for (k = 0; k < MM_MUGS; k++) {
            if (!S.on[k]) continue;
            S.cx[k] += spd;
            if (S.spl[k] && S.spl[k] < 255) S.spl[k]++;
            if (S.pop[k]) S.pop[k]--;
        }
        exits();
        if (S.on[S.lead] && S.cx[S.lead] >= (int16_t)(MM_SPAWN_X + S.gapn) * 8) {   // room for the next cup
            new_cup(MM_SPAWN_X);
            S.gapn = gap();
        }
        if (S.load) S.load--;
        if (S.air) {                                       // falling
            S.t++;
            if (S.t >= MM_FALL) land();
        } else if ((pressed & J_A) && !S.load) {           // drop
            S.air = 1; S.t = 0; S.ax = (S.dx >> 3) + 4; S.drops++;
            SFX(SFX_LAUNCH);
        }
    }
    want = shimmer[(S.anim / 10) & 3];                     // the aurora (every 10 frames, even frames; the belt's step is on odd ones)
    if (!(S.anim % 10) && want != S.wstep) { S.wstep = want; win_rows(want); }
    if (((S.anim + 3) & 7) == 0) { S.bph ^= 1; belt_row(S.bph); }
    sprites();
}
