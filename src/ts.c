// T-SHIRT CANNON, the stadium's mini-game (docs/minigames_bosses.md 4.2; look A, the night game, approved by the owner 2026-10-12: the tripod
// air cannon, red and blue fans holding up signs, two floodlight banks with masts and a windsock, plus A1: 8 pennant flags in a swag
// between the floodlight masts, alternating the two teams' red and blue).
//
// The Spigoteer mans the T-shirt cannon on the field; the stands rise to the right and the crowd does the wave. Aim with Up / Down, read
// the windsock, fire with A so the shirt lands in the standing section.
//
// Rules (the spec's numbers; 8.8 fixed point; tools/cannon_table.py simulates the same integer physics):
// - 12 shirts. After a shot lands (or is lost) 40 frames of reload; the new wind shows when the reload ends (the windsock and the HUD).
// - Aim: 11 angles, 10 to 60 degrees in 5 degree steps (S.angle 0..10); Up / Down steps once a press and repeats every 8 frames held. A
//   3-dot preview shows the first 18 frames of the arc without wind (dots at 6, 12, 18 frames) while a shot can be fired. The barrel look
//   (4 sprite looks: 15 / 30 / 45 / 60 degrees) and its muzzle follow the angle: <= 20, <= 35, <= 50, else.
// - Flight: from the muzzle of the barrel look, speed 3.0 px/f, gravity 1/16 px/f^2, wind k/256 px/f^2 horizontal, k in -2..2: each frame x += vx,
//   y += vy, vy += 16, vx += k, then the shirt's centre is looked up. Wind: shots 1-3 calm; 4-8 k in -1..1; 9-12 k in -2..2 (mg_rand).
//   (The muzzle is the barrel tip of the cannon standing on the grass, 5-12 px lower than the spec's (40, 100): tools/cannon_table.py.)
// - Stands: 11 fan columns (map columns 9-19, S.shown bit 0..10), 8x16, the top row of column c is 11 - (c - 9) / 2. A shirt is caught when its
//   centre enters a fan's box; it is lost past x 168 or down at y 124 (the grass).
// - The wave: 3 adjacent columns standing (S.wave is the centre 1..9); it moves one column every 20 frames (shots 1-4), 16 (5-8), 12 (9-12),
//   ping-pong across the 11 columns. A catch: in the wave 300, next to it (the column each side of its three) 100, elsewhere 0 (the fan still
//   cheers); a catching fan stands for 30 frames.
// - 45 s on the framework's timer (the HUD's T + seconds at columns 16-19): time up ends the round. Medal on the score (mg.c medal_at):
//   GOLD >= 3000, SILVER >= 2000, BRONZE >= 1000.
// - Sounds (no new SFX): fire LAUNCH, a catch CATCH, a catch in the wave COIN too.
//
// Screen: the whole stage is a precomposed map (tools/gen_ts.py ts_map / ts_attr, rows 1-17 over the framework's backdrop): sky and stars,
// floodlight banks on row 1 (columns 5-9, 14-18) with masts at columns 7 and 16, the bunting on rows 3-4 between the masts, the windsock at
// columns 1-3 (rows 3-4) on its pole, the stands rising to the right with the fans on top of their seats, the ad boards on row 13, the grass on rows
// 14-17. HUD row 0: the score, the shirt icon and shirts left at columns 8-10, the wind chevron and its strength at columns 13-14, T + seconds at
// 16-19. The framework's banner rows 2-3 cover the stage during the intro and the count: their tiles and attributes are saved at entry and put
// back on the first play frame (the HUD colours hold the banner until then).
// CGB BG palettes 0 (sky, red flags), 2 / 3 (the fans, blue flags), 5 (stands), 6 (grass), 7 (windsock, floodlights); 4 is left to the medal.
// OBJ: 0 the Spigoteer, 1 puff and dots, 2 shirt, 3 cannon. DMG: BGP the boot's, OBP0 the boot's (Spigoteer, shirt, puff, dots), OBP1 = OBP1_PLAY
// (the cannon).
// OAM 0-3 the Spigoteer, 4-5 the cannon, 6 the puff, 7 the shirt, 8-10 the preview dots: worst line 9 of 10.
// Tiles: BG MG_GAME_BG.. (56), OBJ 56-85.
#pragma bank 255
#include <gb/gb.h>
#include <gb/cgb.h>
#include <stdint.h>

#include "game.h"
#include "music.h"
#include "mg.h"
#include "ts_art.h"         // this bank's own art (assets/art/tshirt/*.txt) and tables

extern uint8_t overlay_on, joy;

#define S               (MG->ts)
#define TS_BGID         MG_GAME_BG
typedef char ts_fits[(TS_BGID + TS_BG_TILES <= 240 && TS_OBJ + TS_OBJ_TILES <= OBJ_COIN && sizeof(struct ts_state) <= STORY_SCRATCH) ? 1 : -1];
#define TS_SHOTS        12
#define TS_RELOAD       40
#define TS_TIME_S       45
#define TS_REPEAT        8
#define TS_CHEER        30
#define TS_POSE_LEN     30
#define TS_FIRE_POSE    12
#define TS_PUFF_LEN     12
#define TS_START_ANGLE   7                  // 45 degrees
#define TS_PTS_WAVE    300
#define TS_PTS_NEAR    100
#define TS_FANS         11
#define TS_FAN_COL       9
#define TS_LAND_Y      124
#define TS_OUT_X       168
#define TS_GRAV         16
#define TS_DOT_FIRST     6                  // frames of the preview's dots
#define TS_DOT_STEP      6
#define SPIG_X          12
#define SPIG_Y          96
#define CANNON_X        32
#define CANNON_Y       104
#define SOCK_COL         1
#define SOCK_ROW         3
#define HUD_SHOTS_COL    8
#define HUD_WIND_COL    13
#define MAP_FIRST        1                  // ts_map's first map row
#define MAP_ROWS        17
// OAM
#define OAM_SPIG         0
#define OAM_CANNON       4
#define OAM_PUFF         6
#define OAM_SHIRT        7
#define OAM_DOT          8
// state
enum { TSS_AIM, TSS_FLY, TSS_RELOAD, TSS_SPENT, TSS_OUT };
// poses (the Spigoteer's bartender frames)
enum { TSP_IDLE, TSP_FIRE, TSP_CHEER, TSP_MISS };
#define OBP1_CANNON  OBP1_PLAY              // the cannon's DMG shades: the boot's ramp
#define OPAL_FX          1
#define OPAL_SHIRT       2
#define OPAL_CANNON      3

static void ts_put(uint8_t bank, const uint8_t *t, uint8_t col, uint8_t row, uint8_t n) {   // queued (or at once with the LCD off)
    if (LCDC_REG & LCDCF_ON) { vq_add(bank, t, col, row, n); return; }
    if (bank) VBK_REG = VBK_BANK_1;
    vram_put(col, row, t, n);
    VBK_REG = VBK_BANK_0;
}

static uint8_t look_of(uint8_t a) {         // the barrel look of angle a (0..10): <= 20 degrees, <= 35, <= 50, else
    return a <= 2 ? 0 : a <= 5 ? 1 : a <= 8 ? 2 : 3;
}

static uint8_t wave_int(void) {
    return S.num <= 4 ? 20 : S.num <= 8 ? 16 : 12;
}

// ---- the stage -------------------------------------------------------------------------------------------------------
static void qput(uint8_t col, uint8_t row, uint8_t tile) {   // one tile, each with its own byte (the VBlank queue reads it later)
    if (!(LCDC_REG & LCDCF_ON)) { vram_put(col, row, &tile, 1); return; }
    if (S.qn >= sizeof(S.qb)) return;
    S.qb[S.qn] = tile;
    vq_add(0, &S.qb[S.qn], col, row, 1);
    S.qn++;
}

static void fan_draw(uint8_t i, uint8_t up) {   // fan column i (map column 9 + i), sitting or standing
    uint8_t base = 2 * ((i & 1 ? 2 : 0) + up);  // (cap fans on the odd map columns 9, 11 ..: i even)
    uint8_t row = 11 - (i >> 1);
    qput(TS_FAN_COL + i, row, TS_BGID + ts_fan[base]);
    qput(TS_FAN_COL + i, row + 1, TS_BGID + ts_fan[base + 1]);
}

static uint8_t standing(uint8_t i) {            // is fan i in the wave, or cheering
    return (i + 1 >= S.wave && i <= S.wave + 1) || S.cheer[i];
}

static void fans_sync(uint8_t limit) {
    uint8_t i, want, n = 0;
    for (i = 0; i < TS_FANS; i++) {
        want = standing(i);
        if (want == ((S.shown >> i) & 1)) continue;
        if (want) S.shown |= (uint16_t)1 << i; else S.shown &= ~((uint16_t)1 << i);
        fan_draw(i, want);
        if (++n == limit) return;
    }
}

static uint8_t sock_look(int8_t k) {            // calm, +1, +2, -1, -2
    return k >= 0 ? (uint8_t)k : (uint8_t)(2 - k);
}

static void hud_shots(void) {                   // columns 8-11: the shirt icon, the shirts left (2 digits), a blank
    uint8_t n = TS_SHOTS - S.shots;
    S.hbuf[0] = TS_BGID + ts_hud[0];
    S.hbuf[1] = TILE_GLYPH_0 + (n >= 10 ? 1 : 0);
    S.hbuf[2] = TILE_GLYPH_0 + (n >= 10 ? n - 10 : n);
    S.hbuf[3] = TILE_HUD_BLANK;                  // (the framework's lives, columns 9-11, are not shown in a mini-game)
    ts_put(0, S.hbuf, HUD_SHOTS_COL, HUD_ROW, 4);
}

static void hud_wind(void) {                    // columns 13-14: the chevron (> >> < <<, a dash for calm) and the strength
    int8_t k = S.wind;
    S.wbuf[0] = TS_BGID + ts_hud[3 + k];
    S.wbuf[1] = TILE_GLYPH_0 + (k < 0 ? -k : k);
    ts_put(0, S.wbuf, HUD_WIND_COL, HUD_ROW, 2);
}

static void put_sock(void) {                    // the windsock's look for the wind (3 x 2 tiles at columns 1-3, rows 3-4)
    uint8_t i, l = sock_look(S.wind);
    for (i = 0; i < 6; i++) S.sock[i] = TS_BGID + ts_sock[l * 6 + i];
    ts_put(0, S.sock, SOCK_COL, SOCK_ROW, 3);
    ts_put(0, S.sock + 3, SOCK_COL, SOCK_ROW + 1, 3);
}

static void dots_calc(void) {                    // the arc's first 18 frames without wind: after t steps x = x0 + t vx, y = y0 + t vy + 8 t (t - 1)
    uint8_t k, l = look_of(S.angle), t;
    int16_t vx = (int16_t)ts_vx[S.angle], vy = (int16_t)ts_vy[S.angle];
    for (k = 0; k < 3; k++) {
        t = TS_DOT_FIRST + TS_DOT_STEP * k;
        S.dots[2 * k] = ts_mx[l] + (uint8_t)((int16_t)(vx * t) >> 8);
        S.dots[2 * k + 1] = ts_my[l] + (uint8_t)((int16_t)(vy * t + 8 * t * (t - 1)) >> 8);
    }
}

static void draw(void);

void ts_enter(void) BANKED {
    uint8_t k, r, c, tb[20], ta[20], *z = (uint8_t *)&S;
    for (k = 0; k < sizeof(struct ts_state); k++) z[k] = 0;
    set_bkg_data(TS_BGID, TS_BG_TILES, ts_bg_tiles);
    set_sprite_data(TS_OBJ, TS_OBJ_TILES, ts_obj_tiles);
    if (is_cgb) {
        set_bkg_palette(0, 1, ts_pal_bg);
        set_bkg_palette(2, 2, ts_pal_bg + 4);                  // 2, 3
        set_bkg_palette(5, 3, ts_pal_bg + 12);                 // 5, 6, 7
        set_sprite_palette(OPAL_FX, 3, ts_pal_obj);            // 1, 2, 3
    } else OBP1_REG = OBP1_CANNON;
    S.angle = TS_START_ANGLE;
    S.num = 1; S.wave = 1; S.wdir = 1; S.wt = 20;
    S.last = 255; S.rep = TS_REPEAT;
    for (r = 0; r < MAP_ROWS; r++) {             // map rows 1-17
        for (c = 0; c < 20; c++) {
            tb[c] = TS_BGID + ts_map[r * 20 + c];
            ta[c] = ts_attr[r * 20 + c];
        }
        vram_put(0, MAP_FIRST + r, tb, 20);
        if (r == 1 || r == 2) {                  // map rows 2-3: kept for the first play frame (the banner covers them until then)
            for (c = 0; c < 20; c++) { S.wall[r - 1][c] = tb[c]; S.wattr[r - 1][c] = ta[c]; }
            if (is_cgb) for (c = 0; c < 20; c++) ta[c] = BGPAL_HUD;
        }
        if (is_cgb) {
            VBK_REG = VBK_BANK_1;
            vram_put(0, MAP_FIRST + r, ta, 20);
            VBK_REG = VBK_BANK_0;
        }
    }
    S.shown = 0;
    fans_sync(TS_FANS);                          // the wave's first three fans stand
    hud_shots(); hud_wind();
    mg_timer = TS_TIME_S * 60;
    draw();
}

// ---- the sprites -----------------------------------------------------------------------------------------------------
static void obj(uint8_t i, int16_t x, int16_t y, uint8_t tile, uint8_t prop) {   // screen px of the top-left
    OAM_item_t *o = shadow_OAM + i;
    if (x <= -8 || x >= 160 || y <= -16 || y >= 144) { o->y = 0; return; }
    o->y = (uint8_t)(y + 16); o->x = (uint8_t)(x + 8); o->tile = tile; o->prop = prop;
}

static void draw(void) {
    uint8_t k, l = look_of(S.angle), f = 0, left = 0;
    for (k = OAM_CANNON; k <= OAM_DOT + 2; k++) shadow_OAM[k].y = 0;
    obj(OAM_CANNON, CANNON_X, CANNON_Y, ts_cannon[2 * l], OPAL_CANNON | S_PALETTE);
    obj(OAM_CANNON + 1, CANNON_X + 8, CANNON_Y, ts_cannon[2 * l + 1], OPAL_CANNON | S_PALETTE);
    if (S.puff) obj(OAM_PUFF, ts_mx[l] - 3, ts_my[l] - 4, ts_puff[S.puff > TS_PUFF_LEN / 2 ? 0 : 1], OPAL_FX);
    if (S.st == TSS_FLY) obj(OAM_SHIRT, (int16_t)(S.x >> 8) - 4, (int16_t)(S.y >> 8) - 4, ts_shirt[(S.t >> 2) & 3], OPAL_SHIRT);
    if (S.st == TSS_AIM) {
        dots_calc();
        for (k = 0; k < 3; k++) obj(OAM_DOT + k, (int16_t)S.dots[2 * k] - 3, (int16_t)S.dots[2 * k + 1] - 3, TS_DOT, OPAL_FX);
    }
    if (S.pose == TSP_FIRE) { f = 3; left = 1; }
    else if (S.pose == TSP_CHEER) { f = 5; left = 1; }
    else if (S.pose == TSP_MISS) f = 6;
    mg_spigoteer(SPIG_X, SPIG_Y, f, left, OAM_SPIG);
}

// ---- play ------------------------------------------------------------------------------------------------------------------
static void new_wind(void) {                     // the next shot's wind
    if (S.num <= 3) S.wind = 0;
    else if (S.num <= 8) S.wind = (int8_t)(mg_rand() % 3) - 1;
    else S.wind = (int8_t)(mg_rand() % 5) - 2;
    hud_wind();
    put_sock();
}

static void fire(void) {
    uint8_t l = look_of(S.angle);
    S.st = TSS_FLY; S.t = 0; S.shots++;
    S.x = (uint16_t)ts_mx[l] << 8; S.y = (uint16_t)ts_my[l] << 8;
    S.vx = (int16_t)ts_vx[S.angle]; S.vy = (int16_t)ts_vy[S.angle];
    S.puff = TS_PUFF_LEN;
    S.pose = TSP_FIRE; S.pose_t = TS_FIRE_POSE;
    hud_shots();
    SFX(SFX_LAUNCH);
}

static void land(uint8_t i) {                    // fan i caught the shirt (255: lost)
    uint8_t pts = 0;
    S.last = i;
    if (i != 255) {
        S.cheer[i] = TS_CHEER;
        if (i + 1 >= S.wave && i <= S.wave + 1) pts = 3;
        else if (i + 2 == S.wave || i == S.wave + 2) pts = 1;
        SFX(SFX_CATCH);
        if (pts == 3) { mg_points(TS_PTS_WAVE); SFX(SFX_COIN); }
        else if (pts) mg_points(TS_PTS_NEAR);
    }
    S.lastpts = pts;
    S.pose = pts ? TSP_CHEER : TSP_MISS; S.pose_t = TS_POSE_LEN;
    S.st = S.shots >= TS_SHOTS ? TSS_SPENT : TSS_RELOAD;
    S.reload = TS_RELOAD;
}

static void flight(void) {
    uint8_t c, px, py, top;
    S.x += S.vx; S.y += S.vy;
    S.vy += TS_GRAV; S.vx += S.wind;
    S.t++;
    px = S.x >> 8; py = S.y >> 8;
    c = px >> 3;
    if (c >= TS_FAN_COL && c < TS_FAN_COL + TS_FANS) {
        top = (11 - ((c - TS_FAN_COL) >> 1)) << 3;
        if (py >= top && py < top + 16) { land(c - TS_FAN_COL); return; }
    }
    if (px >= TS_OUT_X || py >= TS_LAND_Y) land(255);
}

static void aim(uint8_t pressed) {
    uint8_t held = joy & (J_UP | J_DOWN), want = 0;
    if (pressed & J_UP) { want = J_UP; S.rep = TS_REPEAT; }
    else if (pressed & J_DOWN) { want = J_DOWN; S.rep = TS_REPEAT; }
    else if (held == J_UP || held == J_DOWN) {
        if (--S.rep == 0) { want = held; S.rep = TS_REPEAT; }
    } else S.rep = TS_REPEAT;
    if (want == J_UP && S.angle < TS_ANGLES - 1) S.angle++;
    else if (want == J_DOWN && S.angle > 0) S.angle--;
}

static void wave_step(void) {
    if (--S.wt) return;
    S.wt = wave_int();
    S.wave += S.wdir;
    if (S.wave >= 9) S.wdir = -1;
    else if (S.wave <= 1) S.wdir = 1;
}

static void outro_begin(void) {
    S.st = TSS_OUT; S.t = 0;
    S.pose = TSP_IDLE; S.puff = 0;
}

void ts_update(uint8_t pressed) BANKED {
    uint8_t k;
    if (mg_phase == MG_END && S.st != TSS_OUT) outro_begin();   // (time up, or the shots are spent)
    if (!S.started) {                            // the first frame: the banner rows (the framework's text) become the stage again
        S.started = 1;
        vq_add(0, S.wall[0], 0, 2, 20); vq_add(0, S.wall[1], 0, 3, 20);
        if (is_cgb) { vq_add(1, S.wattr[0], 0, 2, 20); vq_add(1, S.wattr[1], 0, 3, 20); }
    }
    S.qn = 0;
    S.anim++;
    wave_step();
    for (k = 0; k < TS_FANS; k++) if (S.cheer[k]) S.cheer[k]--;
    fans_sync(2);
    if (S.puff) S.puff--;
    if (S.pose_t && !--S.pose_t) S.pose = TSP_IDLE;
    switch (S.st) {
    case TSS_AIM:
        aim(pressed);
        if (pressed & J_A) fire();
        break;
    case TSS_FLY:
        flight();
        break;
    case TSS_RELOAD:
        aim(pressed);
        if (!--S.reload) {
            S.num++;
            S.st = TSS_AIM;
            new_wind();
        }
        break;
    case TSS_SPENT:                              // the last shirt has landed: the cheer, then the result
        if (!--S.reload) mg_finish();
        break;
    default:
        break;
    }
    draw();
}
