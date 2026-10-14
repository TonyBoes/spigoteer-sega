// BATTERY SORT, the robot factory's mini-game (docs/minigames_bosses.md 4.6; art approved by the owner 2026-10-12:
// the gauge cells (option A: the factory drink's own full / empty frames), the light steel bins, the belt, the diverter,
// the chute lid, the strike lamps, the broken battery, the spark and the WRONG cross; the Spigoteer in his approved
// bartender poses).
//
// Batteries roll along a belt to a diverter. The front one waits on its flap for at most D frames: Left sends it to the
// CHARGE bin (a charged one), Right to RECYCLE (a dead one), and from the 16th battery Down to the SCRAP chute (a broken
// one). A wrong bin, or D running out, is a strike; three strikes or 45 seconds end it.
//
// Rules (the spec's numbers):
// - D = 120 frames, -8 every 4 correct sorts, never under 40. The belt (it refills the queue): 0.75 px a frame,
//   +0.125 every 6 correct sorts, at most 2.0 (BS speed in 1/8 px); batteries enter 24 px apart and queue 16 px apart,
//   the next five in view.
// - Charged / dead 50 / 50 (mg_rand); the 16th battery is broken (it brings in the chute), and from the 17th 20% are.
//   When the first broken one reaches the flap the chute's lid slides away and the banner SCRAP CHUTE OPEN / BROKEN
//   ONES DOWN shows for BS_BANNER_LEN frames: the belt, the wait and the timer stop meanwhile. Down does nothing while
//   the chute is closed.
// - A right sort counts at once (the next battery's D, the belt's speed); its points and the streak come when it lands.
// - A sort: the battery drops into the diverter (BS_FLY_DROP frames, behind its tiles), comes out of the port its
//   arrow shows and arcs into the bin (BS_FLY_ARC frames; DOWN falls straight through the mouth into the chute), sinks
//   behind the bin's front (4 frames) and is judged when it lands (frame BS_FLY_LEN): right, 100 + 10 x the streak (the
//   bonus at most 200) and a burst of sparks over the bin; wrong, a strike, the streak back to 0, the WRONG cross
//   blinking over the bin and the battery spat out onto the floor. Running out of D: a strike, the cross over the
//   diverter, and the battery drops into it (gone). Up to BS_FLY batteries are in the air at once.
// - Medal (mg.c's medal_at on mg_score): GOLD >= 6000, SILVER >= 4000, BRONZE >= 2000. One setting for story and
//   practice (no HARD).
// - Sounds (no new SFX): a sort SFX_LAUNCH, a right bin SFX_CATCH, a strike SFX_BREAK, the chute opening SFX_SHAKE, the
//   third strike SFX_LIFE.
//
// Screen (the approved mock-up): the framework's factory backdrop, its counter row 11 replaced by wall; the banner rows
// 2-3 are the wall too while no banner shows (put back a row a frame through the VBlank queue). The belt on row 8,
// columns 0-8 (one tile, 4 frames stepped with the belt); the diverter at columns 9-10, rows 8-10 (flap, the arrow
// screen, the base with its ports and mouth; CGB BG palette 2); the bins on rows 12-16: CHARGE columns 1-4 (BG palette
// 3, lime), the SCRAP chute 8-11 (palette 2, its lid closed until the first broken battery), RECYCLE 15-18 (BG palette
// 5, red: not 4, which the result window's medal takes over while the bins still show under it). The strike lamps at
// HUD columns 10-12 (beside the lives at 7-8), the timer T045. The Spigoteer (x 100, y 112) beside the machine:
// IDLE, FILL for Left (X-flipped for Right), SLIDE for Down, CATCH for a right bin, FAIL for a strike; the outro FAIL
// after three strikes, CATCH at time up.
// Batteries: OBJ 8x16 standing on the belt (top y 49), the front one at x 76; charged OBJ 56 (CGB OBJ palette 1),
// dead 58 (palette 2), both the drink's tiles from the level load, DMG OBP0; broken, spark and cross OBJ 60-67 (CGB OBJ
// palettes 3, 4, 5; DMG OBP1 0xE4). A spat cell lies on the floor as the drink's lying frames (OBJ 86 / 88). A battery
// not on the screen yet (x <= -8) is parked at y 0. Only the front-most broken battery on the belt sparks.
// OAM: 0-3 the Spigoteer, 4-5 the cross, 6-7 the bin's sparks, 8 the spat battery, 9-11 the flying batteries, 12 the
// belt spark, 13-20 the queue. Worst line 8 (the belt: 6 queued, 1 dropping into the diverter, the spark).
// Tiles: BG BS_BG.. (MG_GAME_BG: 44, ids 125-168), OBJ 60-67 (over the crash frames: the level load puts them back).
#pragma bank 255
#include <gb/gb.h>
#include <gb/cgb.h>
#include <stdint.h>

#include "game.h"
#include "music.h"
#include "mg.h"
#include "bs_art.h"         // this bank's own art (assets/art/battery/*.txt)

#define S               (MG->bs)
#define BS_BG           MG_GAME_BG
#define BS_OBJ          OBJ_GLASS                // 60..67: broken, spark x 2, cross (the crash frames come back with the level)
typedef char bs_obj_fits[(BS_OBJ + BS_OBJ_TILES <= OBJ_MUG_DRINK && BS_BG + BS_BG_TILES <= 256) ? 1 : -1];
#define BS_TIME_S       45
#define BS_WIN0        120                      // D: frames the front battery waits
#define BS_WIN_STEP      8
#define BS_WIN_EVERY     4                      // correct sorts per step
#define BS_WIN_MIN      40
#define BS_SPEED0        6                      // the belt, 1/8 px a frame (0.75)
#define BS_SPEED_EVERY   6
#define BS_SPEED_MAX    16                      // 2.0
#define BS_GAP_IN       24                      // px between batteries entering
#define BS_GAP          16                      // px between batteries queued
#define BS_Q             8                      // the queue's places
#define BS_START_N       3                      // batteries on the belt at the start (the intro shows them)
#define BS_BROKEN_FROM  16                      // the first broken battery (always broken), then BS_BROKEN_P / 256
#define BS_BROKEN_P     51                      // 20%
#define BS_PTS         100
#define BS_STREAK_PTS   10
#define BS_STREAK_MAX  200
#define BS_STRIKES       3
#define BS_BANNER_LEN   60
#define BS_FLY           3                      // batteries in the air at once
#define BS_FLY_DROP      4                      // frames into the diverter
#define BS_FLY_ARC      16                      // frames of the arc out of the port
#define BS_FLY_LEN      24                      // the frame it lands on (4 sinking behind the bin's front)
#define BS_SCREEN_LEN   16                      // the diverter's arrow shows this long
#define BS_POSE_SORT    16
#define BS_POSE_CATCH   14
#define BS_POSE_FAIL    30
#define BS_SPARK_LEN    14
#define BS_CROSS_LEN    40                      // blinking: on 6 frames, off 4
#define BS_SPIT_ARC     12
#define BS_BAND_OFF     40                      // MG_END frame the banner rows go back to the wall
// the layout
#define BELT_ROW         8
#define BELT_N           9                      // columns 0-8
#define DIV_COL          9                      // the diverter: columns 9-10, rows 8 (flap), 9 (screen), 10 (base)
#define DIV_ROW          8
#define BIN_ROW         12                      // the bins: rows 12-16, 4 columns each
#define CHARGE_COL       1
#define CHUTE_COL        8
#define RECYCLE_COL     15
#define STRIKE_COL      10                      // HUD columns 10-12 (the lives at 7-8)
#define FRONT_X         76                      // the front battery's x on the flap
#define BAT_Y           49                      // a battery's top on the belt
#define SPIG_X         100
#define SPIG_Y         112
#define PORT_L          68                      // where a battery leaves the diverter's ports (top-left)
#define PORT_R          84
#define PORT_Y          76
#define SINK_Y          96                      // the arc's end: the bin's rim
#define CROSS_Y        100                      // the cross over a bin; over the diverter (timeout):
#define CROSS_DIV_X     72
#define CROSS_DIV_Y     30
#define SPARK_Y         88
#define LIE_Y          125                      // a spat cell lying on the floor (the drink's lying frame)
#define LIE_BROKEN_Y   120                      // a spat broken one stands
#define DIV_PAL          2                      // CGB BG palettes: the diverter and the chute
#define CHARGE_PAL       3
#define RECYCLE_PAL      5
#define PAL_BROKEN       3                      // CGB OBJ palettes
#define PAL_SPARK        4
#define PAL_CROSS        5
// OAM
#define OAM_SPIG         0
#define OAM_CROSS        4
#define OAM_SPARKS       6
#define OAM_SPIT         8
#define OAM_FLY          9
#define OAM_BELT_SPARK  12
#define OAM_QUEUE       13
#define OAM_N           21
enum { BS_RUN, BS_SCRAP, BS_OVER };             // S.st: playing; the chute's banner (all paused); over
enum { BT_CHARGED, BT_DEAD, BT_BROKEN };        // battery types
enum { DIR_NONE, DIR_LEFT, DIR_RIGHT, DIR_DOWN, DIR_DROP };   // a flight (DIR_DROP: timed out); screen states 0-3
enum { BR_NONE, BR_RIGHT, BR_WRONG, BR_LATE };  // S.last: the last outcome
enum { BAND_KEEP, BAND_WALL, BAND_HUD };        // S.band[]: a banner row's pending change

static const uint8_t arc_y[BS_FLY_ARC] = { 76, 75, 75, 74, 75, 75, 76, 76, 78, 79, 81, 82, 85, 87, 90, 92 };
static const uint8_t bin_x[4] = { 0, 16, 128, 72 };          // a bin's centre - 8 (the cross, the sparks), by DIR_*
static const uint8_t spit_x0[4] = { 0, 40, 112, 88 };        // a spat battery's way out of the bin
static const uint8_t spit_x1[4] = { 0, 48, 104, 96 };

static void put(uint8_t col, uint8_t row, uint8_t *t, uint8_t n) {
    if (LCDC_REG & LCDCF_ON) vq_add(0, t, col, row, n); else vram_put(col, row, t, n);
}

static void fill_attr(uint8_t col, uint8_t row, uint8_t w, uint8_t h, uint8_t pal) {   // LCD off, CGB
    uint8_t k;
    for (k = 0; k < 20; k++) row_buf[k] = pal;
    VBK_REG = VBK_BANK_1;
    while (h--) vram_put(col, row++, row_buf, w);
    VBK_REG = VBK_BANK_0;
}

// a bin (LCD off): its 4x5 tiles, the sign at its columns 1-2, rows 1-2; the chute under its lid
static void draw_bin(uint8_t col, uint8_t sign, uint8_t lid) {
    uint8_t r, c, m, *t = row_buf;
    for (r = 0; r < 5; r++) {
        for (c = 0; c < 4; c++) {
            m = bs_bin_map[r * 4 + c];
            if (m == 255) t[c] = BS_BG + BSB_SIGN + sign * 4 + (r - 1) * 2 + (c - 1);
            else t[c] = BS_BG + BSB_BIN + (r == 0 && lid ? bs_lid_map[c] : m);
        }
        vram_put(col, BIN_ROW + r, t, 4);
    }
}

static void lamps(void) {                       // HUD columns 10-12: the strikes lit from the left
    uint8_t k;
    for (k = 0; k < 3; k++) S.lamps[k] = BS_BG + BSB_STRIKE + (k < S.strikes ? 1 : 0);
    put(STRIKE_COL, HUD_ROW, S.lamps, 3);
}

static void screen(uint8_t st) {                // the diverter's screen: DIR_NONE (idle), LEFT, RIGHT, DOWN
    S.scr[0] = BS_BG + BSB_SCREEN + 2 * st; S.scr[1] = S.scr[0] + 1;
    put(DIV_COL, DIV_ROW + 1, S.scr, 2);
}

static void belt_row(void) {
    uint8_t k;
    for (k = 0; k < BELT_N; k++) S.belt_row[k] = BS_BG + BSB_BELT + S.belt_f;
    put(0, BELT_ROW, S.belt_row, BELT_N);
}

static uint8_t new_type(void) {
    if (S.made < 255) S.made++;
    if (S.made == BS_BROKEN_FROM) return BT_BROKEN;
    if (S.made > BS_BROKEN_FROM && mg_rand() < BS_BROKEN_P) return BT_BROKEN;
    return mg_rand() & 1;
}

static uint8_t window_now(void) {
    uint8_t d = S.sorted / BS_WIN_EVERY;
    return d >= (BS_WIN0 - BS_WIN_MIN) / BS_WIN_STEP ? BS_WIN_MIN : BS_WIN0 - d * BS_WIN_STEP;
}

static uint8_t speed_now(void) {
    uint8_t s = BS_SPEED0 + S.sorted / BS_SPEED_EVERY;
    return s > BS_SPEED_MAX ? BS_SPEED_MAX : s;
}

// LCD off, after the framework's screen
void bs_enter(void) BANKED {
    uint16_t p[4];
    uint8_t k, *v = (uint8_t *)0x9800;
    set_bkg_data(BS_BG, BS_BG_TILES, bs_bg_tiles);
    set_sprite_data(BS_OBJ, BS_OBJ_TILES, bs_obj_tiles);
    // the wall: the counter row 11 becomes wall (row 9's pattern); rows 4 / 5 kept for the banner rows 2 / 3
    for (k = 0; k < 20; k++) {
        row_buf[k] = v[9 * 32 + k];
        S.wall[0][k] = v[4 * 32 + k]; S.wall[1][k] = v[5 * 32 + k];
        S.hud_attr[k] = BGPAL_HUD;
    }
    vram_put(0, MG_COUNTER_ROW, row_buf, 20);
    if (is_cgb) {
        VBK_REG = VBK_BANK_1;
        for (k = 0; k < 20; k++) {
            row_buf[k] = v[9 * 32 + k];
            S.wattr[0][k] = v[4 * 32 + k]; S.wattr[1][k] = v[5 * 32 + k];
        }
        vram_put(0, MG_COUNTER_ROW, row_buf, 20);
        VBK_REG = VBK_BANK_0;
        p[0] = RGB8(80, 48, 40);                 // the factory wall (the bins' outline sits on it)
        p[1] = RGB8(168, 184, 200); p[2] = RGB8(248, 216, 72); p[3] = RGB8(16, 24, 40);
        set_bkg_palette(DIV_PAL, 1, p);          // the diverter, the chute: light steel, hazard yellow, dark
        p[2] = RGB8(160, 248, 96); p[3] = RGB8(40, 48, 56);
        set_bkg_palette(CHARGE_PAL, 1, p);       // CHARGE: the charged cell's lime
        p[2] = RGB8(248, 88, 56);
        set_bkg_palette(RECYCLE_PAL, 1, p);      // RECYCLE: the dead cell's red
        p[0] = 0;
        p[1] = RGB8(216, 240, 88); p[2] = RGB8(160, 168, 176); p[3] = RGB8(32, 24, 32);
        set_sprite_palette(PAL_BROKEN, 1, p);    // the broken battery: acid, grey case, dark
        p[1] = RGB8(248, 248, 240); p[2] = RGB8(248, 216, 72); p[3] = RGB8(208, 112, 40);
        set_sprite_palette(PAL_SPARK, 1, p);     // the spark: white, yellow, orange
        p[2] = RGB8(224, 40, 32); p[3] = RGB8(32, 24, 32);
        set_sprite_palette(PAL_CROSS, 1, p);     // the cross: white rim, red
        fill_attr(DIV_COL, DIV_ROW, 2, 3, DIV_PAL);
        fill_attr(CHUTE_COL, BIN_ROW, 4, 5, DIV_PAL);
        fill_attr(CHARGE_COL, BIN_ROW, 4, 5, CHARGE_PAL);
        fill_attr(RECYCLE_COL, BIN_ROW, 4, 5, RECYCLE_PAL);
    } else OBP1_REG = OBP1_PLAY;                 // broken, spark, cross (OBP1 0xE4; the title leaves 0xC4)
    // the machine
    S.belt = 0; S.belt_f = 0;
    belt_row();
    S.scr[0] = BS_BG + BSB_FLAP; S.scr[1] = BS_BG + BSB_FLAP + 1;
    vram_put(DIV_COL, DIV_ROW, S.scr, 2);
    S.scr[0] = BS_BG + BSB_BASE; S.scr[1] = BS_BG + BSB_BASE + 1;
    vram_put(DIV_COL, DIV_ROW + 2, S.scr, 2);
    screen(DIR_NONE);
    draw_bin(CHARGE_COL, 0, 0);
    draw_bin(CHUTE_COL, 2, 1);
    draw_bin(RECYCLE_COL, 1, 0);
    // the state
    S.st = BS_RUN; S.wait = 0; S.strikes = 0; S.sorted = 0; S.streak = 0; S.made = 0; S.chute = 0;
    S.banner = 0; S.last = BR_NONE; S.screen_t = 0; S.pose = BT_IDLE; S.pose_t = 0; S.flip = 0; S.anim = 0;
    S.started = 0; S.band[0] = S.band[1] = BAND_KEEP;
    S.spark_t = 0; S.cross_t = 0; S.spit_t = 0;
    for (k = 0; k < BS_FLY; k++) S.fly[k].dir = DIR_NONE;
    S.window = window_now(); S.speed = speed_now();
    for (k = 0; k < BS_START_N; k++) {
        S.queue[k] = new_type();
        S.qx[k] = (int16_t)(FRONT_X - BS_GAP * k) * 8;
    }
    S.n = BS_START_N;
    lamps();
    mg_timer = BS_TIME_S * 60;
    bs_update(0);                                // the sprites (the update draws them; no play before MG_PLAY)
}

// ---- the sprites ----
static uint8_t cell_tile(uint8_t type) {
    return type == BT_BROKEN ? BS_OBJ + BSO_BROKEN : type == BT_DEAD ? OBJ_MUG + 2 : OBJ_MUG;
}

static uint8_t cell_prop(uint8_t type) {
    if (is_cgb) return type == BT_BROKEN ? PAL_BROKEN : type == BT_DEAD ? OBJPAL_MUG_EMPTY : OBJPAL_MUG_FULL;
    return type == BT_BROKEN ? S_PALETTE : 0;
}

static void obj(uint8_t i, uint8_t x, uint8_t y, uint8_t tile, uint8_t prop) {   // screen px of the top-left
    OAM_item_t *o = shadow_OAM + i;
    o->y = y + 16; o->x = x + 8; o->tile = tile; o->prop = prop;
}

static void fx_obj(uint8_t i, uint8_t x, uint8_t y, uint8_t tile, uint8_t pal) {   // spark / cross: OBP1 on DMG
    obj(i, x, y, BS_OBJ + tile, is_cgb ? pal : S_PALETTE);
}

static void draw(void) {
    uint8_t k, x, y, t, b, sparked = 0;
    for (k = OAM_CROSS; k < OAM_N; k++) shadow_OAM[k].y = 0;
    mg_spigoteer(SPIG_X, SPIG_Y, S.pose, S.flip, OAM_SPIG);
    // the queue on the belt (x <= -8: not on the screen yet, parked at y 0)
    for (k = 0; k < S.n; k++) {
        if (S.qx[k] <= -64) continue;
        x = (uint8_t)((S.qx[k] + 64) >> 3) - 8;
        obj(OAM_QUEUE + k, x, BAT_Y, cell_tile(S.queue[k]), cell_prop(S.queue[k]));
        if (S.queue[k] == BT_BROKEN && !sparked) {   // only the front-most broken one sparks
            sparked = 1;
            fx_obj(OAM_BELT_SPARK, x + 1, BAT_Y - 7, BSO_SPARK + 2 * ((S.anim >> 3) & 1), PAL_SPARK);
        }
    }
    // the batteries in the air
    for (k = 0; k < BS_FLY; k++) {
        b = S.fly[k].dir;
        if (b == DIR_NONE) continue;
        t = S.fly[k].t;
        x = FRONT_X; y = BAT_Y + 3 * t;          // into the diverter (and DOWN: on through the mouth)
        if (b == DIR_DROP) { if (t >= BS_FLY_DROP) continue; }
        else if (b != DIR_DOWN && t >= BS_FLY_DROP) {
            if (t < BS_FLY_DROP + BS_FLY_ARC) {
                t -= BS_FLY_DROP;
                x = b == DIR_LEFT ? PORT_L - 3 * t : PORT_R + 3 * t;
                y = arc_y[t];
            } else {                             // sinking behind the bin's front
                x = b == DIR_LEFT ? PORT_L - 3 * BS_FLY_ARC : PORT_R + 3 * BS_FLY_ARC;
                y = SINK_Y + 3 * (t - BS_FLY_DROP - BS_FLY_ARC);
            }
        }
        t = cell_prop(S.fly[k].type);
        if (b == DIR_DOWN || b == DIR_DROP || S.fly[k].t < BS_FLY_DROP || y > SINK_Y - 4) t |= S_PRIORITY;
        obj(OAM_FLY + k, x, y, cell_tile(S.fly[k].type), t);
    }
    // a right bin's sparks
    if (S.spark_t) {
        t = (S.spark_t & 7) < 4;
        fx_obj(OAM_SPARKS, S.spark_x - 2, SPARK_Y, BSO_SPARK + 2 * t, PAL_SPARK);
        fx_obj(OAM_SPARKS + 1, S.spark_x + 10, SPARK_Y + 4, BSO_SPARK + 2 * (1 - t), PAL_SPARK);
    }
    // WRONG: the cross (blinking) and the spat battery
    if (S.cross_t && (uint8_t)(BS_CROSS_LEN - S.cross_t) % 10 < 6) {   // on 6 frames, off 4, from its first
        fx_obj(OAM_CROSS, S.cross_x, S.cross_y, BSO_CROSS, PAL_CROSS);
        fx_obj(OAM_CROSS + 1, S.cross_x + 8, S.cross_y, BSO_CROSS, PAL_CROSS);
        shadow_OAM[OAM_CROSS + 1].prop |= S_FLIPX;
    }
    if (S.spit_t) {
        t = BS_CROSS_LEN - S.spit_t;             // its age
        b = S.spit_dir;
        if (t < BS_SPIT_ARC) {
            y = S.spit_type == BT_BROKEN ? LIE_BROKEN_Y : LIE_Y;
            x = spit_x0[b] + (int8_t)((int8_t)(spit_x1[b] - spit_x0[b]) * (int8_t)t / BS_SPIT_ARC);
            y = 92 + (int16_t)((int16_t)t * (t - 6) * (y - 92)) / 72;
            obj(OAM_SPIT, x, y, cell_tile(S.spit_type), cell_prop(S.spit_type));
        } else if (S.spit_type == BT_BROKEN) {
            obj(OAM_SPIT, spit_x1[b], LIE_BROKEN_Y, cell_tile(BT_BROKEN), cell_prop(BT_BROKEN));
        } else {                                 // the drink's lying frames: full OBJ 86, empty 88
            obj(OAM_SPIT, spit_x1[b], LIE_Y, OBJ_MUG_DRINK + 2 + 2 * S.spit_type, cell_prop(S.spit_type));
        }
    }
}

// ---- the rules ----
static void set_pose(uint8_t pose, uint8_t t, uint8_t flip) { S.pose = pose; S.pose_t = t; S.flip = flip; }

static void strike(void) {
    S.streak = 0;
    if (S.strikes >= BS_STRIKES) return;         // (a battery landing after the third: the game is over already)
    S.strikes++;
    lamps();
    set_pose(BT_FAIL, BS_POSE_FAIL, 0);
    SFX(SFX_BREAK);
    if (S.strikes < BS_STRIKES || mg_phase != MG_PLAY) return;
    S.st = BS_OVER;
    mg_say(MG_TEXT_A, "THREE STRIKES");
    S.band[0] = BAND_HUD;                        // (its colours: the text is queued already)
    SFX(SFX_LIFE);
    mg_finish();
}

static void land(uint8_t k) {                   // flight k lands in its bin
    uint8_t d = S.fly[k].dir, ty = S.fly[k].type;
    S.fly[k].dir = DIR_NONE;
    if (d == ty + 1) {                           // DIR_LEFT charged, DIR_RIGHT dead, DIR_DOWN broken
        S.last = BR_RIGHT;
        if (S.streak < 255) S.streak++;
        mg_points(BS_PTS + (S.streak >= BS_STREAK_MAX / BS_STREAK_PTS ? BS_STREAK_MAX : S.streak * BS_STREAK_PTS));
        S.spark_t = BS_SPARK_LEN; S.spark_x = bin_x[d];
        set_pose(BT_CATCH, BS_POSE_CATCH, 0);
        SFX(SFX_CATCH);
    } else {
        S.last = BR_WRONG;
        S.cross_t = BS_CROSS_LEN; S.cross_x = bin_x[d]; S.cross_y = CROSS_Y;
        S.spit_t = BS_CROSS_LEN; S.spit_type = ty; S.spit_dir = d;
        strike();
    }
}

static uint8_t fly_slot(void) {
    uint8_t k;
    for (k = 0; k < BS_FLY; k++) if (S.fly[k].dir == DIR_NONE) return k;
    return 255;
}

static void pop_front(uint8_t dir) {            // the front battery leaves the flap: into the diverter
    uint8_t k = fly_slot();
    if (k != 255) { S.fly[k].dir = dir; S.fly[k].type = S.queue[0]; S.fly[k].t = 0; }
    for (k = 1; k < S.n; k++) { S.queue[k - 1] = S.queue[k]; S.qx[k - 1] = S.qx[k]; }
    S.n--;
    S.wait = 0;
}

static void belt(void) {
    uint8_t k, f;
    int16_t lim;
    S.belt += S.speed;
    f = (S.belt >> 3) & 3;
    if (f != S.belt_f) { S.belt_f = f; belt_row(); }
    for (k = 0; k < S.n; k++) {
        lim = (int16_t)(FRONT_X - BS_GAP * k) * 8;
        if (k && S.qx[k - 1] - BS_GAP * 8 < lim) lim = S.qx[k - 1] - BS_GAP * 8;
        S.qx[k] += S.speed;
        if (S.qx[k] > lim) S.qx[k] = lim;
    }
    if (S.n < BS_Q && (!S.n || S.qx[S.n - 1] >= (BS_GAP_IN - 8) * 8)) {   // the next one comes in BS_GAP_IN px behind
        S.queue[S.n] = new_type();
        S.qx[S.n] = -64;
        S.n++;
    }
    if (S.n && !S.wait && S.qx[0] == FRONT_X * 8) {   // the front one reaches the flap
        S.wait = S.window;
        if (S.queue[0] == BT_BROKEN && !S.chute) {   // the first broken one: the chute opens, the banner, all paused
            S.chute = 1;
            S.st = BS_SCRAP; S.banner = BS_BANNER_LEN;
            S.band[0] = S.band[1] = BAND_HUD;
            for (k = 0; k < 4; k++) S.lid[k] = BS_BG + BSB_BIN + bs_bin_map[k];
            put(CHUTE_COL, BIN_ROW, S.lid, 4);
            SFX(SFX_SHAKE);
        }
    }
}

// the banner rows: a row a frame (tiles and colours together), the wall back or the HUD band with its text
static void band(void) {
    uint8_t r;
    for (r = 0; r < 2; r++) {
        if (S.band[r] == BAND_KEEP) continue;
        if (S.band[r] == BAND_WALL) {
            if (is_cgb) vq_add(1, S.wattr[r], 0, MG_TEXT_A + r, 20);
            vq_add(0, S.wall[r], 0, MG_TEXT_A + r, 20);
        } else {
            if (is_cgb) vq_add(1, S.hud_attr, 0, MG_TEXT_A + r, 20);
            if (S.st == BS_SCRAP) mg_say(MG_TEXT_A + r, r ? "BROKEN ONES DOWN" : "SCRAP CHUTE OPEN");
        }
        S.band[r] = BAND_KEEP;
        return;
    }
}

void bs_update(uint8_t pressed) BANKED {
    uint8_t k, d;
    S.anim++;
    if (mg_phase == MG_PLAY || mg_phase == MG_END) {
        if (!S.started) { S.started = 1; S.band[0] = S.band[1] = BAND_WALL; }   // the banner's rows: the wall again
        for (k = 0; k < BS_FLY; k++) {           // the batteries in the air
            if (S.fly[k].dir == DIR_NONE) continue;
            if (++S.fly[k].t >= (S.fly[k].dir == DIR_DROP ? BS_FLY_DROP : BS_FLY_LEN)) {
                if (S.fly[k].dir == DIR_DROP) S.fly[k].dir = DIR_NONE; else land(k);
            }
        }
        if (S.spark_t) S.spark_t--;
        if (S.cross_t) S.cross_t--;
        if (S.spit_t) S.spit_t--;
        if (S.screen_t && !--S.screen_t) screen(DIR_NONE);
        if (S.pose_t && !--S.pose_t) set_pose(BT_IDLE, 0, 0);
    }
    if (mg_phase == MG_PLAY) {
        if (S.st == BS_SCRAP) {                  // the chute's banner: the belt, the wait and the timer stop
            mg_timer++;
            if (!--S.banner) { S.st = BS_RUN; S.band[0] = S.band[1] = BAND_WALL; }
        } else if (S.st == BS_RUN) {
            d = DIR_NONE;
            if (pressed & J_LEFT) d = DIR_LEFT;
            else if (pressed & J_RIGHT) d = DIR_RIGHT;
            else if ((pressed & J_DOWN) && S.chute) d = DIR_DOWN;
            if (d && S.wait && fly_slot() != 255) {     // a sort (a right one counts now: the next D, the belt's speed)
                if (d == S.queue[0] + 1 && S.sorted < 255) {
                    S.sorted++;
                    S.window = window_now(); S.speed = speed_now();
                }
                pop_front(d);
                S.screen_t = BS_SCREEN_LEN; screen(d);
                set_pose(d == DIR_DOWN ? BT_SLIDE : BT_FILL, BS_POSE_SORT, d == DIR_RIGHT);
                SFX(SFX_LAUNCH);
            } else if (S.wait && !--S.wait) {    // too late: a strike, the cross over the diverter, the battery drops in
                S.last = BR_LATE;
                S.cross_t = BS_CROSS_LEN; S.cross_x = CROSS_DIV_X; S.cross_y = CROSS_DIV_Y;
                pop_front(DIR_DROP);
                strike();
            }
            if (S.st == BS_RUN) belt();
            if (mg_timer == 1 && S.st == BS_RUN) S.band[0] = BAND_HUD;   // TIME UP comes this frame (mg.c): its colours
        }
    } else if (mg_phase == MG_END) {
        S.st = BS_OVER;                          // the outro: dazed after three strikes, cheering at time up
        if (!S.pose_t) set_pose(S.strikes >= BS_STRIKES ? BT_FAIL : BT_CATCH, 0, 0);
        if (mg_t == BS_BAND_OFF) S.band[0] = S.band[1] = BAND_WALL;
    }
    band();
    draw();
}
