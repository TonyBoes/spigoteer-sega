// MARSHMALLOW DROP, the igloo's mini-game (docs/minigames_bosses.md 4.5; art approved by the owner 2026-10-12: the hybrid with
// Tin cups, the hoist-pail dropper, Aurora in the serving hatch, the ice bricks and A's COCOA BAR sign; aurora window W1).
// REWORKED 2026-10-15 (batch D2, the owner's playtest: "significantly harder than the others"): the player steers the pail.
//
// Rules (1/8 px units in the code):
// - LEFT / RIGHT steer the pail along the rail, x 16..136: +3/8 px a frame^2 up to 2.0 px a frame, friction 4/8 a frame when no key
//   is held (a little momentum), stops dead at the ends. A drops a marshmallow straight down from the pail (top-left at the pail's
//   x + 4, y 51) at 2 px a frame: 22 frames to the cups' rim (y 95). One in the air at a time; the next is loaded 12 frames after.
// - MM_MUGS (6) cups ride the belt to the right at 0.5 px a frame, 48 px apart, and LOOP: a cup leaving at the right comes back at the
//   left with what it holds. At most 4 share the screen: a cup line has at most 8 cup entries + the falling marshmallow = 9 of the 10.
// - The supply is MM_MUGS x 3 + 1 = 19 marshmallows (HUD: the icon at column 11, what is left at 12-13). A hit: -1 <= marshmallow x -
//   cup x <= 11 (the 12 px opening). +100 for each marshmallow that lands, +300 for the third (the cup is FULL: the 3-marshmallow frame,
//   copper on CGB, a pop; it takes nothing more). Any other marshmallow, a full cup included, is a MISS: it falls on to the belt (y 112),
//   SFX_BREAK, and lies there as a splat that rides right, blinks and is gone.
// - Ends: every cup full ("ALL MUGS FULL"), the supply used up and the last one down ("OUT OF MARSHMALLOWS"), or 60 s (the framework's
//   TIME UP). Medal by score (mg.c medal_at): GOLD 3600 = all 6 full (18 hits: at most 1 miss), SILVER 2400, BRONZE 1200. EASY / HARD: mm_tune (the belt's speed,
//   the opening, the supply) and the medal rows of mg.c.
//
// Screen (the approved mock-up): HUD row 0 (score; the supply: a marshmallow icon at 11, 2 digits at 12-13; the timer at 17-19);
// the ice-brick wall rows 1-13 with the aurora window at columns 1-6, rows 1-4 (CGB BG palettes 6 green and 7 magenta; it shimmers
// 0 1 2 1 every 10 frames: the 3 frames' tiles are all in VRAM and each step rewrites the 24 map cells), the COCOA BAR / 3 PERFECT sign
// (HUD glyphs on the HUD panel) at columns 8-19, rows 1-4 (the framework's banner text covers the window and the sign's rows 2-3 until
// the first play frame), the wooden beam on row 5, Aurora's serving hatch at columns 17-19 rows 8-10, the conveyor row 14 (2 phases, the
// map row swaps), the wood panel row 15 and the floor rows 16-17.
// OAM: 0-3 the pops, 4 the falling marshmallow, 5 the loaded one, 6-7 the pail, 8-19 the cups (6 x 2 entries), 20-25 the splats (3 x 2,
// on the belt's scanlines 112-119, which no cup reaches). CGB OBJ palettes 1 cups, 2 pail and full cups, 3 marshmallows, pops and splats.
// DMG: cups and pail on OBP1 (set here, 0xE0), marshmallows, pops and splats on OBP0.
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
#define MM_TIME_S      60
#define MM_ARM_MIN    (16 * 8)
#define MM_ARM_MAX    (136 * 8)
#define MM_ARM_SPEED   16                   // the pail's top speed, 1/8 px a frame (2.0 px)
#define MM_ARM_ACC      3                   // a key adds this a frame
#define MM_ARM_FRIC     4                   // no key takes this off a frame
#define MM_PAIL_Y      40
#define MM_PUFF_Y0     51                   // the marshmallow's top at the drop; + MM_DROP_V a frame
#define MM_DROP_V       2                   // (owner 2026-10-15: slower first; was 3)
#define MM_FALL        22                   // frames to the rim (y 95 at 2 px a frame)
#define MM_BELT_T      27                   // frames to the belt (a miss splats there)
#define MM_RELOAD      12
#define MM_CUP_Y       96
#define MM_POP_Y       80
#define MM_POP_LEN     40
#define MM_BELT        4                    // the belt's speed, 1/8 px a frame
#define MM_SPACING     48                   // px between cups
#define MM_LOOP        (MM_MUGS * MM_SPACING * 8)   // one lap, 1/8 px
#define MM_END_X       160
#define MM_START_X     120                  // cup 0's x at the start (the others 48 px apart behind it)
#define MM_SPLAT_Y     112
#define MM_SPLAT_LIFE  150
#define MM_PTS_HIT    100
#define MM_PTS_FULL   300
// The tuning per difficulty (indexed by MG_DIFF: NORMAL, HARD, EASY; STORY and ARCADE play NORMAL), TUNING.md: the belt's speed (1/8 px a frame), the
// hit window (the marshmallow's x - the cup's x from lo to hi, px) and the supply; the medals are in mg.c.
static const struct mm_tune mm_tune[MG_DIFFS] = {
    { MM_BELT, -1, 11, MM_SUPPLY },
    { 6, 1, 9, 18 },                            // HARD: 0.75 px a frame, a 9 px opening, 18 marshmallows (all 6 cups full = 18 hits)
    { 3, -2, 12, 20 },                          // EASY: 0.375 px a frame, a 15 px opening, 20 marshmallows
};
#define MMT             (S.tn)
#define TUNE_LOAD()     { const uint8_t *tl_s = (const uint8_t *)&mm_tune[MG_DIFF]; uint8_t *tl_d = (uint8_t *)&S.tn, tl_k; for (tl_k = 0; tl_k < sizeof(S.tn); tl_k++) tl_d[tl_k] = tl_s[tl_k]; }

#define OAM_POP         0
#define OAM_FALL        4
#define OAM_HELD        5
#define OAM_PAIL        6
#define OAM_CUP         8
#define OAM_SPLAT      (OAM_CUP + 2 * MM_MUGS)
#define OPAL_CUP        1
#define OPAL_PAIL       2
#define OPAL_PUFF       3
#define OPAL_FULL       OPAL_PAIL           // a full cup is drawn in the pail's copper (the level load restores palettes 1-3 only)
#define MM_ROW_BELT    14
#define MM_WIN_COL      1
#define MM_WIN_ROW      1
extern uint8_t joy;
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


static void hud_supply(void) {                      // what is left of the supply, 2 digits at columns 12-13
    uint8_t p = S.supply, t = 0;
    while (p >= 10) { p -= 10; t++; }
    S.hud[0] = TILE_GLYPH_0 + t; S.hud[1] = TILE_GLYPH_0 + p;
    put(S.hud, 12, HUD_ROW, 2);
}

static uint8_t pop_f(uint8_t k) {                      // (k / 6) & 1 for k < 40: the odd sixes are 6-11, 18-23, 30-35
    return (uint8_t)(k - 6) < 6 || (uint8_t)(k - 18) < 6 || (uint8_t)(k - 30) < 6;
}

static void sprites(void) {
    uint8_t k, f, np = 0;
    int16_t x;
    // the pail (swings every 6 frames) and the loaded marshmallow
    x = S.dx >> 3;
    obj2(OAM_PAIL, x, MM_PAIL_Y, mm_pail + 2 * S.p6, cgb(OPAL_PAIL));
    if (!S.air && !S.load && S.supply && mg_phase <= MG_PLAY) obj(OAM_HELD, x + 4, MM_PUFF_Y0, mm_puff[0], cgb0(OPAL_PUFF));
    else hide(OAM_HELD);
    if (S.air) obj(OAM_FALL, S.ax, MM_PUFF_Y0 + MM_DROP_V * S.t, mm_puff[(S.t >> 1) & 1], cgb0(OPAL_PUFF));
    else hide(OAM_FALL);
    hide(OAM_POP); hide(OAM_POP + 1); hide(OAM_POP + 2); hide(OAM_POP + 3);
    for (k = 0; k < MM_MUGS; k++) {
        x = S.cx[k] >> 3;
        f = S.n[k];
        obj2(OAM_CUP + 2 * k, x, MM_CUP_Y, mm_cup + 2 * f, f == 3 && is_cgb ? OPAL_FULL : cgb(OPAL_CUP));
        if (S.pop[k] && np < 2 && x >= -8 && x < 160) {
            obj2(OAM_POP + 2 * np, x, MM_POP_Y, mm_pop + 2 * pop_f(MM_POP_LEN - S.pop[k]), cgb0(OPAL_PUFF));
            np++;
        }
    }
    for (k = 0; k < MM_SPLATS; k++) {                // splats: fresh, settling, flat; they blink out in the last 30 frames
        uint8_t a = S.sage[k];
        if (!a || (a > MM_SPLAT_LIFE - 30 && (a & 4))) { hide(OAM_SPLAT + 2 * k); hide(OAM_SPLAT + 2 * k + 1); continue; }
        obj2(OAM_SPLAT + 2 * k, S.sx[k] >> 3, MM_SPLAT_Y, mm_splat + 2 * (a < 6 ? 0 : (a < 14 ? 1 : 2)), cgb0(OPAL_PUFF));
    }
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
    TUNE_LOAD();
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
    // the HUD supply: the icon at column 11, two digits at 12-13 (the lives at 7-8, the goal area of the story)
    row_buf[0] = (uint8_t)(MM_BG + MMB_ICON);
    vram_put(11, HUD_ROW, row_buf, 1);
    S.supply = MMT.supply;
    hud_supply();
    // the belt's two phases (columns 1-18 of row 14) and the banner rows' scene (restored at the first play frame)
    for (c = 0; c < 18; c++) { S.belt[0][c] = (uint8_t)(MM_BG + MMB_BELT0); S.belt[1][c] = (uint8_t)(MM_BG + MMB_BELT1); }
    row_tiles(2, S.wall[0]); row_tiles(3, S.wall[1]);
    for (c = 0; c < 20; c++) { S.wattr[0][c] = mm_pal[20 + c]; S.wattr[1][c] = mm_pal[40 + c]; }
    // the game
    mg_timer = MM_TIME_S * 60;
    S.dx = 76 * 8; S.vx = 0; S.air = 0; S.miss = 0; S.load = 0; S.t = 0; S.ax = 0; S.anim = 0; S.a6 = S.a10 = S.p6 = S.p10 = 0; S.started = 0; S.wstep = 0; S.bph = 0;
    S.drops = 0; S.hits = 0; S.misses = 0; S.full = 0;
    for (c = 0; c < MM_MUGS; c++) { S.cx[c] = (MM_START_X - MM_SPACING * c) * 8; S.n[c] = 0; S.pop[c] = 0; }
    for (c = 0; c < MM_SPLATS; c++) S.sage[c] = 0;
    sprites();
}

static void splat(void) {                                 // a miss reaches the belt: a splat at the marshmallow's x (the oldest slot if all are used)
    uint8_t k, best = 0;
    for (k = 0; k < MM_SPLATS; k++) {
        if (!S.sage[k]) { best = k; break; }
        if (S.sage[k] > S.sage[best]) best = k;
    }
    S.sage[best] = 1; S.sx[best] = (S.ax - 4) * 8;
    SFX(SFX_BREAK);
}

static void settle(void) {                                // a marshmallow is done: reload, and the end of the game
    S.air = 0; S.miss = 0; S.load = MM_RELOAD;
    if (S.full == MM_MUGS) { mg_say(MG_TEXT_A, "ALL MUGS FULL"); mg_finish(); }
    else if (!S.supply) { mg_say(MG_TEXT_A, "OUT OF MARSHMALLOWS"); mg_finish(); }
}

static void land(void) {                                  // the marshmallow at the rim: a cup that can take it, or a miss
    uint8_t k;
    int16_t d;
    for (k = 0; k < MM_MUGS; k++) {
        d = S.ax - (S.cx[k] >> 3);
        if (d < MMT.lo || d > MMT.hi) continue;
        if (S.n[k] == 3) break;                           // a full cup: it bounces off (a miss)
        S.hits++;
        S.n[k]++;
        mg_points(MM_PTS_HIT);
        if (S.n[k] == 3) {                                // a full cup
            mg_points(MM_PTS_FULL);
            S.full++;
            S.pop[k] = MM_POP_LEN;
            SFX(SFX_COIN);
        } else SFX(SFX_CATCH);
        settle();
        return;
    }
    S.misses++;                                           // on: it falls to the belt
    S.miss = 1;
}

void mm_update(uint8_t pressed) BANKED {
    uint8_t k, want;
    if (!S.started) {                                     // the first frame: the banner rows (the framework's text) are the scene again
        S.started = 1;
        vq_add(0, S.wall[0], 0, 2, 20); vq_add(0, S.wall[1], 0, 3, 20);
        if (is_cgb) { vq_add(1, S.wattr[0], 0, 2, 20); vq_add(1, S.wattr[1], 0, 3, 20); }
    }
    if (!++S.anim) S.a6 = S.a10 = S.p6 = S.p10 = 0;       // (the counters follow anim, wrap included: no divides)
    else {
        if (++S.a6 == 6) { S.a6 = 0; S.p6 ^= 1; }
        if (++S.a10 == 10) { S.a10 = 0; S.p10 = (S.p10 + 1) & 3; }
    }
    if (mg_phase >= MG_PLAY && mg_phase <= MG_END) {      // the belt rides on through the outro
        for (k = 0; k < MM_MUGS; k++) {                   // the cups loop: past the right edge they come back at the left
            S.cx[k] += MMT.belt;
            if (S.cx[k] >= MM_END_X * 8) S.cx[k] -= MM_LOOP;
            if (S.pop[k]) S.pop[k]--;
        }
        for (k = 0; k < MM_SPLATS; k++) {
            if (!S.sage[k]) continue;
            S.sx[k] += MMT.belt;
            if (++S.sage[k] > MM_SPLAT_LIFE || S.sx[k] >= MM_END_X * 8) S.sage[k] = 0;
        }
    }
    if (mg_phase == MG_PLAY) {
        if (joy & J_LEFT) { S.vx -= MM_ARM_ACC; if (S.vx < -MM_ARM_SPEED) S.vx = -MM_ARM_SPEED; }
        else if (joy & J_RIGHT) { S.vx += MM_ARM_ACC; if (S.vx > MM_ARM_SPEED) S.vx = MM_ARM_SPEED; }
        else if (S.vx > 0) { S.vx -= MM_ARM_FRIC; if (S.vx < 0) S.vx = 0; }
        else if (S.vx < 0) { S.vx += MM_ARM_FRIC; if (S.vx > 0) S.vx = 0; }
        S.dx += S.vx;
        if (S.dx >= MM_ARM_MAX) { S.dx = MM_ARM_MAX; S.vx = 0; }
        if (S.dx <= MM_ARM_MIN) { S.dx = MM_ARM_MIN; S.vx = 0; }
        if (S.load) S.load--;
        if (S.air) {                                       // falling
            S.t++;
            if (S.t == MM_FALL) land();
            else if (S.miss && S.t >= MM_BELT_T) { splat(); settle(); }
        } else if ((pressed & J_A) && !S.load && S.supply) {   // drop
            S.air = 1; S.t = 0; S.ax = (S.dx >> 3) + 4; S.drops++;
            S.supply--;
            hud_supply();
            SFX(SFX_LAUNCH);
        }
    }
    want = shimmer[S.p10];                     // the aurora (every 10 frames, even frames; the belt's step is on odd ones)
    // (the aurora is frozen in the outro: the banner's text is on rows 2-3, over the window)
    if (mg_phase <= MG_PLAY && !S.a10 && want != S.wstep) { S.wstep = want; win_rows(want); }
    if (((S.anim + 3) & 7) == 0) { S.bph ^= 1; belt_row(S.bph); }
    sprites();
}
