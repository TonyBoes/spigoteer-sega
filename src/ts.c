// T-SHIRT CANNON, the stadium's mini-game (docs/minigames_bosses.md 4.2; look A, the night game, approved by the owner 2026-10-12: the tripod
// air cannon, red and blue fans, two floodlight banks with masts, 8 pennant flags in a swag between the masts). Reworked 2026-10-15 (Batch D, the
// owner's playtest: "looks great, but isn't fun"): a golf-style power meter, fans who raise their hands, an OOPS for too short or too far.
// The field is a baseball field (the chalk line on the grass is the foul line).
//
// The Spigoteer mans the T-shirt cannon on the field; the stands rise to the right. Up / Down aim the barrel (4 angles: 45, 52, 60, 68 degrees,
// the four barrel looks; the owner wanted the aim kept, 2026-10-15), then the golf-style power meter sets the speed.
//
// Rules (8.8 fixed point; tools/cannon_table.py simulates the same integer physics and checks the fairness rule):
// - 10 shirts. Up / Down step the angle (once a press, repeating every 8 frames held; also while reloading); A starts the power meter (a marker
//   sweeps 0..63 and back on the bar at the left of the sky, one step every 2 frames, the angle is locked); A again locks the power and fires. It
//   never stops by itself. After a shot lands 40 frames of reload.
// - Flight: from the muzzle of the barrel look, speed v = 224 + 13 p (8.8 px/f) split by the angle: with vh = v >> 3, vx = (vh cos) >> 5,
//   vy = -((vh sin) >> 5) (ts_cosk / ts_sink = 256 cos / 256 sin), gravity 1/16 px/f^2: each frame x += vx, y += vy, vy += 16, then the shirt's
//   centre is looked up.
// - Stands: 11 fan columns (map columns 9-19), 8x16, the top row of column c is 11 - (c - 9) / 2. The shirt hits the CROWD when its centre is in a
//   column at or below the fan's top and above the ad boards (y < 104); it is SHORT at the ad boards or down at y 124 (the grass), OVER past x 168.
//   What each angle changes: the landing barely moves with it (a column's window shifts 3-8 power steps), but a FLAT shot (45) crosses the stand
//   while still rising, and a rising shirt cannot be caught; the lobs (52 and up) are falling everywhere, fly longer (47 .. 93 frames) and have a
//   bigger short zone. The meter's red ends are the powers that are OOPS at every angle; the marker turns hollow (red on the CGB) in the powers
//   that are OOPS at the aimed angle (ts_short / ts_over).
// - The crowd: random fans raise their hands (arms up, hands open, the two frames alternating every 8 frames: they pop up and down) for
//   120-151 frames (2.0-2.5 s), at most 3 at once, a new one every 50-81 frames (and at once when none is up). A fan with raised hands
//   reaches one column each side: a hit in column c with a raised fan in c-1, c or c+1 AND a falling shirt is a PERFECT CATCH, 300 points (the fan
//   holds its hands up 40 frames more). A rising shirt that hit near a raised fan is TOO FLAT, 30; any other hit of the crowd: 30 points (the
//   pittance). Short or over: OOPS, 0 points.
// - 45 s on the framework's timer (the HUD's T + seconds at columns 16-19): time up ends the round. Medal on the score (mg.c medal_at):
//   GOLD >= 2700, SILVER >= 2100, BRONZE >= 1500 (tests/test_mg_tshirt.py: the bots behind them).
// - Sounds (no new SFX): fire LAUNCH, a hit CATCH, a perfect catch COIN too.
//
// Screen: the whole stage is a precomposed map (tools/gen_ts.py ts_map / ts_attr, rows 1-17 over the framework's backdrop): sky and stars,
// floodlight banks on row 1 (columns 5-9, 14-18) with masts at columns 7 and 16, the bunting on rows 3-4 between the masts, the power meter's
// bar at column 1 (rows 3-10: 64 pixel rows, one a power step, red at both ends), the stands rising to the right with the fans on top of
// their seats, the ad boards on row 13, the grass on rows 14-17. HUD row 0: the score, the shirt icon and shirts left at columns 8-10,
// T + seconds at 16-19. The framework's banner rows 2-3 cover the stage during the intro and the count: their tiles and attributes are saved at
// entry and put back on the first play frame (the HUD colours hold the banner until then). The outcome's message (OOPS! TOO SHORT, OOPS! TOO
// FAR, PERFECT CATCH!, TOO FLAT! 30, CROWD 30) takes row 2 in the HUD colours for 70 frames, then row 2 is the stage again.
// CGB BG palettes 0 (sky, red flags, the meter), 2 / 3 (the fans, blue flags), 5 (stands), 6 (grass), 7 (floodlights); 4 is left to the medal.
// OBJ: 0 the Spigoteer, 1 puff and the marker (2 for its hollow look), 2 shirt, 3 cannon. DMG: BGP the boot's, OBP0 the boot's (Spigoteer, shirt, puff, marker), OBP1 =
// OBP1_PLAY (the cannon).
// OAM 0-3 the Spigoteer, 4-5 the cannon, 6 the puff, 7 the shirt, 8 the marker: worst line 8 of 10.
// Tiles: BG MG_GAME_BG.. (45), OBJ 56-73.
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
// tuning (a later difficulty table can drive these)
#define TS_SHOTS        10
#define TS_RELOAD       40
#define TS_SPENT_LEN    60                  // frames after the last shirt lands, before the result
#define TS_TIME_S       45
#define TS_REPEAT        8                  // frames before the aim repeats while Up / Down is held
#define TS_STEP          2                  // frames a meter step takes (126 frames up, 126 down)
#define TS_UP_FRAMES   120                  // a fan keeps its hands up 120 + (rand & TS_UP_RAND) frames (2.0 - 2.5 s)
#define TS_UP_RAND      31
#define TS_UP_MAX        3                  // fans with their hands up at once
#define TS_SPAWN        50                  // frames to the next fan: 50 + (rand & TS_SPAWN_RAND)
#define TS_SPAWN_RAND   31
#define TS_POP           8                  // frames a raised fan holds each of its two hands-up frames
#define TS_HOLD         40                  // a fan that caught the shirt keeps its hands up at least this long
#define TS_PTS_PERFECT 300
#define TS_PTS_CROWD    30                  // the pittance: 10 %
#define TS_MSG_LEN      70
#define TS_POSE_LEN     30
#define TS_FIRE_POSE    12
#define TS_PUFF_LEN     12
#define TS_FANS         11
#define TS_FAN_COL       9
#define TS_BOARD_Y     104
#define TS_LAND_Y      124
#define TS_OUT_X       168
#define TS_GRAV         16
#define SPIG_X          12
#define SPIG_Y          96
#define CANNON_X        32
#define CANNON_Y       104
#define METER_COL        1
#define METER_ROW        3
#define METER_TOP       24                  // the bar's top pixel row (power TS_PMAX); one pixel row a power step
#define HUD_SHOTS_COL   10
#define MAP_FIRST        1                  // ts_map's first map row
#define MAP_ROWS        17
// OAM
#define OAM_SPIG         0
#define OAM_CANNON       4
#define OAM_PUFF         6
#define OAM_SHIRT        7
#define OAM_MARK         8
// state
enum { TSS_AIM, TSS_METER, TSS_FLY, TSS_RELOAD, TSS_SPENT, TSS_OUT };
// the last shot's result
enum { TSR_NONE, TSR_SHORT, TSR_OVER, TSR_CROWD, TSR_PERFECT };
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

// ---- the stage -------------------------------------------------------------------------------------------------------
static void qput(uint8_t col, uint8_t row, uint8_t tile) {   // one tile, each with its own byte (the VBlank queue reads it later)
    if (!(LCDC_REG & LCDCF_ON)) { vram_put(col, row, &tile, 1); return; }
    if (S.qn >= sizeof(S.qb)) return;
    S.qb[S.qn] = tile;
    vq_add(0, &S.qb[S.qn], col, row, 1);
    S.qn++;
}

static void fan_draw(uint8_t i, uint8_t state) {   // fan column i (map column 9 + i): 0 sitting, 1 / 2 hands up
    uint8_t base = 2 * ((i & 1 ? 3 : 0) + state);  // (cap fans on the odd map columns 9, 11 ..: i even)
    uint8_t row = 11 - (i >> 1);
    qput(TS_FAN_COL + i, row, TS_BGID + ts_fan[base]);
    qput(TS_FAN_COL + i, row + 1, TS_BGID + ts_fan[base + 1]);
}

static uint8_t fan_want(uint8_t i) {            // the frame fan i should show: sitting, or the hands-up frame of this beat
    return S.up[i] ? 1 + (((S.anim >> 3) + i) & 1) : 0;
}

static void fans_sync(uint8_t limit) {
    uint8_t i, want, n = 0;
    for (i = 0; i < TS_FANS; i++) {
        want = fan_want(i);
        if (want == S.fshown[i]) continue;
        S.fshown[i] = want;
        fan_draw(i, want);
        if (++n == limit) return;
    }
}

static void hud_shots(void) {                   // columns 10-12: the shirt icon, the shirts left (2 digits)
    uint8_t n = TS_SHOTS - S.shots;
    S.hbuf[0] = TS_BGID + ts_hud[0];
    S.hbuf[1] = TILE_GLYPH_0 + (n >= 10 ? 1 : 0);
    S.hbuf[2] = TILE_GLYPH_0 + (n >= 10 ? n - 10 : n);
    ts_put(0, S.hbuf, HUD_SHOTS_COL, HUD_ROW, 3);
}

static void say(const char *s) {                // a message on row 2 in the HUD colours (mg_say: the text; the attributes: bank 1)
    if (is_cgb) vq_add(1, S.hattr, 0, MG_TEXT_A, 20);
    mg_say(MG_TEXT_A, s);
    S.msg_t = TS_MSG_LEN;
}

static void unsay(void) {                       // row 2 is the stage again
    if (is_cgb) vq_add(1, S.wattr[0], 0, MG_TEXT_A, 20);
    vq_add(0, S.wall[0], 0, MG_TEXT_A, 20);
}

static void draw(void);
static void raise_fan(void);

void ts_enter(void) BANKED {
    uint8_t k, r, c, tb[20], ta[20], *z = (uint8_t *)&S;
    for (k = 0; k < sizeof(struct ts_state); k++) z[k] = 0;
    set_bkg_data(TS_BGID, TS_BG_TILES, ts_bg_tiles);
    set_sprite_data(TS_OBJ, TS_OBJ_TILES, ts_obj_tiles);
    say_bang = TS_BGID + ts_hud[1];             // mg_say's '!' (OOPS! PERFECT CATCH!); mg_leave clears it
    if (is_cgb) {
        set_bkg_palette(0, 1, ts_pal_bg);
        set_bkg_palette(2, 2, ts_pal_bg + 4);                  // 2, 3
        set_bkg_palette(5, 3, ts_pal_bg + 12);                 // 5, 6, 7
        set_sprite_palette(OPAL_FX, 3, ts_pal_obj);            // 1, 2, 3
    } else OBP1_REG = OBP1_CANNON;
    S.num = 1; S.last = 255;
    S.angle = TS_START_ANGLE; S.rep = 1;
    for (k = 0; k < 20; k++) S.hattr[k] = BGPAL_HUD;
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
    raise_fan(); raise_fan();                    // two fans have their hands up from the start
    S.spawn = TS_SPAWN;
    for (k = 0; k < TS_FANS; k++) S.fshown[k] = 0;   // (the map has them all sitting)
    fans_sync(TS_FANS);
    hud_shots();
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
    uint8_t k, f = 0, left = 0, show = 1;
    for (k = OAM_CANNON; k <= OAM_MARK; k++) shadow_OAM[k].y = 0;
    obj(OAM_CANNON, CANNON_X, CANNON_Y, ts_cannon[2 * S.angle], OPAL_CANNON | S_PALETTE);
    obj(OAM_CANNON + 1, CANNON_X + 8, CANNON_Y, ts_cannon[2 * S.angle + 1], OPAL_CANNON | S_PALETTE);
    if (S.puff) obj(OAM_PUFF, ts_mx[S.angle] - 3, ts_my[S.angle] - 4, ts_puff[S.puff > TS_PUFF_LEN / 2 ? 0 : 1], OPAL_FX);
    if (S.st == TSS_FLY) obj(OAM_SHIRT, (int16_t)(S.x >> 8) - 4, (int16_t)(S.y >> 8) - 4, ts_shirt[(S.t >> 2) & 3], OPAL_SHIRT);
    if (S.st == TSS_AIM) show = (S.anim >> 4) & 1;                 // waiting for A: the marker blinks at the bottom
    else if (S.st == TSS_RELOAD || S.st == TSS_SPENT) show = 0;
    else if (S.st == TSS_FLY) show = (S.t >= 24) || ((S.t >> 2) & 1);   // the lock: it blinks for a moment, then holds the locked power
    if (show && S.st != TSS_OUT) {
        k = S.st != TSS_AIM && (S.power <= ts_short[S.angle] || S.power >= ts_over[S.angle]);   // the powers that are OOPS at this angle: hollow, red
        obj(OAM_MARK, 0, METER_TOP + TS_PMAX - S.power - 3, ts_marker[k], k ? OPAL_SHIRT : OPAL_FX);
    }
    if (S.pose == TSP_FIRE) { f = 3; left = 1; }
    else if (S.pose == TSP_CHEER) { f = 5; left = 1; }
    else if (S.pose == TSP_MISS) f = 6;
    mg_spigoteer(SPIG_X, SPIG_Y, f, left, OAM_SPIG);
}

// ---- the crowd -------------------------------------------------------------------------------------------------------
static void raise_fan(void) {                    // a random sitting fan raises its hands (at most TS_UP_MAX are up)
    uint8_t i = mg_rand() % TS_FANS, k, n = 0;
    for (k = 0; k < TS_FANS; k++) if (S.up[k]) n++;
    if (n >= TS_UP_MAX) return;
    for (k = 0; k < TS_FANS; k++, i = (i + 1 == TS_FANS) ? 0 : i + 1)
        if (!S.up[i]) { S.up[i] = TS_UP_FRAMES + (mg_rand() & TS_UP_RAND); return; }
}

static void crowd_step(void) {
    uint8_t k, n = 0;
    for (k = 0; k < TS_FANS; k++) if (S.up[k]) { S.up[k]--; n++; }
    if (!n || !--S.spawn) {                      // (some fan always has his hands up)
        raise_fan();
        S.spawn = TS_SPAWN + (mg_rand() & TS_SPAWN_RAND);
    }
}

// ---- play ------------------------------------------------------------------------------------------------------------------
static void fire(void) {
    uint8_t vh = (uint8_t)((TS_V0 + (uint16_t)TS_DV * S.power) >> 3);   // the speed / 8, at most 130
    S.lastpow = S.power;
    S.st = TSS_FLY; S.t = 0; S.shots++;
    S.x = (uint16_t)ts_mx[S.angle] << 8; S.y = (int16_t)((uint16_t)ts_my[S.angle] << 8);
    S.vx = (int16_t)((vh * ts_cosk[S.angle]) >> 5);
    S.vy = -(int16_t)((vh * ts_sink[S.angle]) >> 5);
    S.puff = TS_PUFF_LEN;
    S.pose = TSP_FIRE; S.pose_t = TS_FIRE_POSE;
    hud_shots();
    SFX(SFX_LAUNCH);
}

static void land(uint8_t res, uint8_t col, uint8_t fall) {     // the shirt is down: TSR_SHORT / TSR_OVER, or the crowd's column `col` (fall: it was falling)
    uint8_t f = 255;
    S.result = res; S.last = res >= TSR_CROWD ? col : 255;
    S.pose = TSP_MISS;
    if (res >= TSR_CROWD) {
        if (S.up[col]) f = col;                  // a raised pair of hands catches it: the fan hit, else the one each side
        else if (col && S.up[col - 1]) f = col - 1;
        else if (col + 1 < TS_FANS && S.up[col + 1]) f = col + 1;
        SFX(SFX_CATCH);
        if (f != 255 && fall) {
            res = S.result = TSR_PERFECT;
            if (S.up[f] < TS_HOLD) S.up[f] = TS_HOLD;
            mg_points(TS_PTS_PERFECT); SFX(SFX_COIN);
            say("PERFECT CATCH!");
            S.pose = TSP_CHEER;
        } else {
            mg_points(TS_PTS_CROWD);
            say(f != 255 ? "TOO FLAT! 30" : "CROWD 30");
            S.pose = TSP_IDLE;
        }
    } else say(res == TSR_SHORT ? "OOPS! TOO SHORT" : "OOPS! TOO FAR");
    S.pose_t = TS_POSE_LEN;
    S.st = S.shots >= TS_SHOTS ? TSS_SPENT : TSS_RELOAD;
    S.reload = S.st == TSS_SPENT ? TS_SPENT_LEN : TS_RELOAD;
}

static void flight(void) {
    uint8_t c, px, top;
    int16_t py;                                  // (negative: above the screen)
    S.x += S.vx; S.y += S.vy;
    S.vy += TS_GRAV;
    S.t++;
    px = S.x >> 8; py = S.y >> 8;
    c = px >> 3;
    if (c >= TS_FAN_COL && c < TS_FAN_COL + TS_FANS) {
        top = (11 - ((c - TS_FAN_COL) >> 1)) << 3;
        if (py >= top && py < TS_BOARD_Y) { land(TSR_CROWD, c - TS_FAN_COL, S.vy > 0); return; }
        if (py >= TS_BOARD_Y) { land(TSR_SHORT, 0, 0); return; }
    }
    if (px >= TS_OUT_X) land(TSR_OVER, 0, 0);
    else if (py >= TS_LAND_Y) land(TSR_SHORT, 0, 0);
}

static void aim(void) {                          // Up steeper, Down flatter: once a press, then every TS_REPEAT frames held
    uint8_t held = joy & (J_UP | J_DOWN);
    if (held != J_UP && held != J_DOWN) { S.rep = 1; return; }
    if (--S.rep) return;
    S.rep = TS_REPEAT;
    if (held == J_UP) { if (S.angle < TS_ANGLES - 1) S.angle++; }
    else if (S.angle) S.angle--;
}

static void meter_step(void) {                   // the marker: a step every TS_STEP frames, up to TS_PMAX and back
    if (--S.pt) return;
    S.pt = TS_STEP;
    S.power += S.pdir;
    if (S.power >= TS_PMAX) S.pdir = -1;
    else if (S.power == 0) S.pdir = 1;
}

static void outro_begin(void) {
    S.st = TSS_OUT; S.t = 0;
    S.pose = TSP_IDLE; S.puff = 0;
}

void ts_update(uint8_t pressed) BANKED {
    if (mg_phase == MG_END && S.st != TSS_OUT) outro_begin();   // (time up, or the shots are spent)
    if (!S.started) {                            // the first frame: the banner rows (the framework's text) become the stage again
        S.started = 1;
        vq_add(0, S.wall[0], 0, 2, 20); vq_add(0, S.wall[1], 0, 3, 20);
        if (is_cgb) { vq_add(1, S.wattr[0], 0, 2, 20); vq_add(1, S.wattr[1], 0, 3, 20); }
    }
    S.qn = 0;
    S.anim++;
    crowd_step();
    fans_sync(2);
    if (S.puff) S.puff--;
    if (S.pose_t && !--S.pose_t) S.pose = TSP_IDLE;
    if (S.msg_t && S.st != TSS_OUT && !--S.msg_t) unsay();
    switch (S.st) {
    case TSS_AIM:
        aim();
        if (pressed & J_A) { S.st = TSS_METER; S.power = 0; S.pdir = 1; S.pt = TS_STEP; }
        break;
    case TSS_METER:
        if (pressed & J_A) fire();
        else meter_step();
        break;
    case TSS_FLY:
        flight();
        break;
    case TSS_RELOAD:
        aim();
        if (!--S.reload) { S.num++; S.st = TSS_AIM; S.power = 0; }
        break;
    case TSS_SPENT:                              // the last shirt has landed: the message, then the result
        if (!--S.reload) mg_finish();
        break;
    default:
        break;
    }
    draw();
}
