// ASTEROID DELIVERY, the space lounge's mini-game (docs/minigames_bosses.md 4.8; look approved by the owner 2026-10-12:
// look A's stage ("clean starfield": black-navy sky, sparse stars, dotted lane lines, round brass-ring portholes, steel
// counter, the HUD beaker icon) with look B's asteroids (blue faceted rocks, light rim); the beaker keeps its glow halo).
//
// Zizz's three guests wait in portholes at the top. The beaker (the space drink) stands on the bar; thrust it up through
// five lanes of drifting asteroids with the D-pad and hand it gently to the alien whose porthole is lit.
//
// Rules (the spec's numbers; 8.8 fixed point):
// - Thrust: each held D-pad axis adds 1/32 px a frame (8 in 8.8), drag v -= v / 32 a frame (a speed under 1/8 px loses 1 (1/256 px) a
//   frame instead, so the beaker really stops), each axis capped at 1.25 px a frame; then it moves. Opposite keys cancel. The play field is
//   x 4..156 (the beaker's centre), y 28 (24 over a lit porthole's dock) .. 120 (the bar); a wall stops that axis. No gravity.
//   (The spec's "about 1 s to half speed" and "v -= v / 32" disagree: half speed takes 22 frames at 1/32. The formula is
//   built; the drag is the knob, with the speed cap, if it needs a playtest.)
// - Asteroids (16x16) drift horizontally in 5 lanes (the lanes' tops y 32 + 16 k), 2 a lane, wrapping over a 176 px loop;
//   speeds 0.25, 0.375, 0.5, 0.375, 0.25 px a frame, directions alternating (lane 1 right); x1.5 from the 3rd delivery,
//   x2 from the 6th. In a lane the two rocks are 56..120 px apart (seeded), so a gap is always >= 40 px. A rock never
//   leaves its lane, so no scan line ever holds the rocks of two lanes.
// - A hit (the beaker's 6 px x 12 px body against a rock's 12x12 core) spills it: 30 frames of tumble (the three turns,
//   falling), nothing else lost, a new beaker on the bar 60 frames after the hit.
// - Delivery: the lit porthole's dock is the hand zone, 16x8 px at the porthole's x + 4, y 24..31. The beaker's body
//   touching it (its top above y 28) with |vx| and |vy| both <= 0.75 px a frame: +500 and a time bonus of
//   (600 - frames since that porthole lit) / 10 when positive (a 10 s par); the next porthole lights at random (never the same
//   twice), a new beaker on the bar 30 frames later. Too fast: WHOA (a banner on row 14), the beaker bounces (v = -v / 2
//   and it is put just outside the zone), nothing lost. An unlit porthole's dock is a wall.
// - 45 s (the game's own clock, like Milk Run's), the HUD shows T + seconds. Medal by deliveries (ad_medal): GOLD 7,
//   SILVER 5, BRONZE 3 (HARD values: the NORMAL tuning block below holds today's: D6c).
// - D6c (NORMAL, owner 2026-10-15): lanes 0, 2, 4 hold ONE rock (7 rocks, the second rock of those lanes is not drawn and never hits),
//   the rocks go x1.25 from the 4th and x1.5 from the 8th delivery, the lit porthole's whole 24 px ledge is the hand zone and any touch
//   delivers at any speed (no WHOA), and a blinking arrow at the edge a rock is about to come in from shows AD_WARN (40) frames before.
// - Sounds (no new SFX): delivered SERVE (and COIN), a rock hit BREAK, WHOA SHAKE.
//
// Screen: the framework's space-lounge wall under everything; map rows 1-3 the portholes (columns 1-3, 8-10, 15-17; each 24x24
// with its alien, unlit: black ring, lit: bright ring and dock; the lit one has an arrow bobbing under its dock), rows 4-14 the
// starfield (a dotted lane line on the top edge of rows 4, 6, 8, 10, 12, 14), rows 15-16 the wall with the Spigoteer's bust,
// row 17 the counter. The HUD (row 0): the score, the beaker icon and the deliveries at columns 11-13, T + seconds at 16-19.
// The framework's banner rows 2-3 cover the portholes during the intro and the count: their tiles and attributes are saved at
// entry and put back on the first play frame. "WHOA" and "TIME UP" are written on row 14 (the launch gap) in the HUD colours,
// WHOA put back after 40 frames.
// CGB BG palettes: 2 the sky, 3 the counter, 5 / 6 / 7 the three aliens' patron palettes with colour 0 the lounge's wall
// (the venue's stage / bar_b palettes: nothing of the venue wall uses them in the rows left); 4 is left to the result's medal.
// OBJ: 0 the Spigoteer, 1 the beaker and its tumble (the venue's drink palette), 3 the rocks, 7 the arrow, 6 the puff and the
// halo (5 is the show's, unused). DMG: OBP0 the Spigoteer (boot's), OBP1 AD_OBP1 for everything else (the per-OAM palette bit).
// OAM 0-1 the beaker (its tumble's two halves), 2 the thrust puff, 3-4 the halo, 5 the arrow, 6-7 the Spigoteer's bust,
// 8-27 the ten rocks (left and right entries), 28-32 the edge arrows (one a lane): worst line 10 (a lane's 4 rock entries + its edge
// arrow + the lit porthole's arrow, beaker, halo 2, puff).
// Tiles: BG MG_GAME_BG.. (56), OBJ 58-91 and 96-97 (the venue's drink frame 0 at 56-57 is the beaker; the coin 92-95 stays).
#pragma bank 255
#include <gb/gb.h>
#include <gb/cgb.h>
#include <stdint.h>

#include "game.h"
#include "music.h"
#include "mg.h"
#include "ad_art.h"         // this bank's own art (assets/art/asteroid/*.txt)

extern uint8_t overlay_on, joy;

#define S               (MG->ad)
#define AD_BG           MG_GAME_BG
typedef char ad_fits[(AD_BG + AD_BG_TILES <= 256 && AD_OBJ_A + AD_OBJ_A_TILES <= OBJ_COIN && AD_OBJ_B + AD_OBJ_B_TILES <= 128
                      && sizeof(struct ad_state) <= STORY_SCRATCH) ? 1 : -1];
#define AD_TIME_S       45
#define AD_PAR         600                  // frames: the time bonus's par (10 s)
#define AD_PTS         500
#define AD_THRUST        8                  // 1/32 px a frame^2
#define AD_CAP         320                  // 1.25 px a frame
// ---- the tuning, NORMAL (owner 2026-10-15: "a bit too hard": too many rocks, rocks from nowhere at the edge, too little grace at the
// dock; today's first values are HARD and are noted here). A difficulty table later supplies them per level. ----
#define AD_GOLD          8                  // NORMAL medals by deliveries (HARD: 7 / 5 / 3): scripted pilots, DESIGN.md
#define AD_SILVER        6
#define AD_BRONZE        4
#define AD_SLOW        320                  // NORMAL (HARD 192 = 0.75 px a frame): the touch speed that still delivers; 320 is the cap,
                                            // so any touch of the ledge delivers and there is no WHOA
#define AD_ZONE_HALF    12                  // NORMAL (HARD 8): half the width of the hand zone on the lit porthole = the whole ledge
                                            // under the alien (the porthole is 24 px wide); the beaker's body touching it anywhere delivers
#define AD_STEP1         4                  // NORMAL (HARD 3): deliveries before the rocks go x1.25 (HARD x1.5)
#define AD_STEP2         8                  // NORMAL (HARD 6): ... and x1.5 (HARD x2)
#define AD_WARN         40                  // NORMAL: frames before a rock comes in that its edge arrow blinks (HARD: none)
#define AD_LOOP     (176u << 8)             // the rocks' loop: 160 px of screen + a rock each side
#define AD_TUMBLE       30
#define AD_SPILL_WAIT   60                  // frames from a hit to the new beaker
#define AD_DELIVER_WAIT 30
#define AD_WHOA_LEN     40
#define AD_START_X      68                  // the beaker's launch spot (centre x, top y)
#define AD_START_Y     120
#define AD_X_MIN         4
#define AD_X_MAX       156
#define AD_Y_MAX       120
#define AD_Y_MIN_DOCK   24                  // over a lit dock
#define AD_Y_MIN        28                  // elsewhere: the flask's top (art row 4) is on y 32
#define AD_LANE_TOP0    32
#define AD_BANNER_ROW   14
#define SPIG_X          44
#define SPIG_Y         120
#define SPIG_FRAME_IDLE 0
#define AD_OBP1       0xC4                  // DMG sprites but the Spigoteer (OBP1_MENU's value): idx1 light grey, idx2 white, idx3 black
// OAM
#define OAM_BEAKER       0
#define OAM_PUFF         2
#define OAM_HALO         3
#define OAM_ARROW        5
#define OAM_SPIG         6
#define OAM_ROCK         8
#define OAM_WARN        28                  // 5 entries, one a lane: the edge arrows
#define OAM_N           33
// palettes
#define PAL_SKY          2
#define PAL_COUNTER      3
#define PAL_ALIEN        5                  // 5, 6, 7
#define OPAL_BEAKER      1
#define OPAL_ROCK        3
#define OPAL_ARROW       7                  // (not 4: the level load only rewrites it for an enhanced group, so it would linger)
#define OPAL_FX          6
enum { AS_FLY, AS_TUMBLE, AS_GAP, AS_OUT };
#define RGB15(r, g, b) ((uint16_t)((r) | ((g) << 5) | ((b) << 10)))

static const uint8_t porthole_col[3] = { 1, 8, 15 };
static const uint8_t porthole_cx[3]  = { 20, 76, 132 };      // the docks' centres (x)
// rock speeds, 8.8 px a frame: lane 0..4 at x1, then NORMAL x1.25, x1.5 (HARD: x1.5 = { 96, 144, 192, 144, 96 }, x2 = { 128, 192, 256, 192, 128 })
static const uint16_t lane_speed[3][5] = {
    {  64,  96, 128,  96,  64 },
    {  80, 120, 160, 120,  80 },
    {  96, 144, 192, 144,  96 },
};
// rocks in a lane, NORMAL (HARD: 2 in every lane, 10): the second rock of a lane with 1 is not drawn and never hits
static const uint8_t lane_rocks[5] = { 1, 2, 1, 2, 1 };
static uint8_t rock_on(uint8_t k) { return (k & 1) < lane_rocks[k >> 1]; }

static void ad_put(uint8_t bank, uint8_t *t, uint8_t col, uint8_t row, uint8_t n) {
    if (LCDC_REG & LCDCF_ON) { vq_add(bank, t, col, row, n); return; }
    if (bank) VBK_REG = VBK_BANK_1;
    vram_put(col, row, t, n);
    VBK_REG = VBK_BANK_0;
}

// ---- the screen ------------------------------------------------------------------------------------------------------
// The mock-up's star hash h = (7 c + 13 r + (c r) % 5) % 11 (a star variant 1-4 at h = 0, 3, 6, 9), kept running along the
// row so no division runs (a division loop costs the enter several frames: tests' mg_enter gives it 20).
static void sky_row(uint8_t r, uint8_t *t, uint8_t *a) {
    uint8_t c, v, h, k, rb = 0, rm = r, ca = 0, cm = 0;
    for (k = 0; k < r; k++) { rb += 2; if (rb >= 11) rb -= 11; }          // 13 r % 11
    while (rm >= 5) rm -= 5;                                              // r % 5
    for (c = 0; c < 20; c++) {
        h = ca + rb + cm;
        while (h >= 11) h -= 11;
        v = h == 0 ? 1 : h == 3 ? 2 : h == 6 ? 3 : h == 9 ? 4 : 0;
        t[c] = AD_BG + ((r & 1) ? ad_sky[v] : ad_sep[v]);     // the lane line on the top edge of the even rows 4..14
        a[c] = PAL_SKY;
        ca += 7; if (ca >= 11) ca -= 11;
        cm += rm; if (cm >= 5) cm -= 5;
    }
}

static void porthole_buf(uint8_t p, uint8_t lit, uint8_t *b) {   // its 9 tiles row-major
    uint8_t k;
    for (k = 0; k < 9; k++) b[k] = AD_BG + ad_port[p * 18 + lit * 9 + k];
}

static void put_porthole(uint8_t p, uint8_t lit, uint8_t slot) {  // queued (or at once with the LCD off)
    uint8_t *b = S.pbuf[slot], r;
    porthole_buf(p, lit, b);
    for (r = 0; r < 3; r++) ad_put(0, b + 3 * r, porthole_col[p], 1 + r, 3);
}

static void hud_deliveries(void) {               // HUD columns 11-13: the beaker icon, the count (no X: owner 2026-10-15)
    S.dbuf[0] = AD_BG + ADB_HUDI;
    S.dbuf[1] = S.delivered >= 10 ? TILE_GLYPH_0 + S.delivered / 10 : TILE_HUD_BLANK;
    S.dbuf[2] = TILE_GLYPH_0 + S.delivered % 10;
}

static void hud_time(void) {                     // the hourglass + seconds (2 digits) at columns 17-19 (column 16 blank), as the framework's timer
    uint8_t s = S.secs, t = 0;
    while (s >= 10) { s -= 10; t++; }
    S.tbuf[0] = TILE_HUD_BLANK; S.tbuf[1] = MG_HOURGLASS; S.tbuf[2] = TILE_GLYPH_0 + t; S.tbuf[3] = TILE_GLYPH_0 + s;
}

// seconds shown = ceil(t / 60): the last value stands while t is inside its 60-frame band (no divide per frame)
static uint8_t secs_left(uint8_t s, uint16_t t) {
    uint16_t hi = ((uint16_t)s << 6) - ((uint16_t)s << 2);   // 60 * s
    if (t <= hi && t + 60 > hi) return s;
    return (uint8_t)((t + 59) / 60);
}

static void draw(void);

void ad_enter(void) BANKED {
    uint8_t k, r, c, *z = (uint8_t *)&S, *v = (uint8_t *)0x9800, tb[20], ta[20];
    for (k = 0; k < sizeof(struct ad_state); k++) z[k] = 0;
    set_bkg_data(AD_BG, AD_BG_TILES, ad_bg_tiles);
    set_sprite_data(AD_OBJ_A, AD_OBJ_A_TILES, ad_obj_a_tiles);
    if (AD_OBJ_B_TILES) set_sprite_data(AD_OBJ_B, AD_OBJ_B_TILES, ad_obj_b_tiles);
    if (is_cgb) {
        set_bkg_palette(PAL_SKY, 1, ad_pal_bg);
        set_bkg_palette(PAL_COUNTER, 1, ad_pal_bg + 4);
        set_bkg_palette(PAL_ALIEN, 3, ad_pal_bg + 8);          // 5, 6, 7
        set_sprite_palette(OPAL_ROCK, 1, ad_pal_obj);
        set_sprite_palette(OPAL_ARROW, 1, ad_pal_obj + 4);
        set_sprite_palette(OPAL_FX, 1, ad_pal_obj + 8);
    } else OBP1_REG = AD_OBP1;
    // the state
    S.time = AD_TIME_S * 60; S.secs = AD_TIME_S;
    S.lit = mg_rand() % 3;
    for (k = 0; k < 5; k++) {                    // 2 rocks a lane, 56..120 px apart
        r = mg_rand();
        S.rx[2 * k] = (uint16_t)((r % 176) << 8) | (mg_rand());
        c = 56 + mg_rand() % 65;
        S.rx[2 * k + 1] = S.rx[2 * k] + ((uint16_t)c << 8);
        if (S.rx[2 * k + 1] >= AD_LOOP) S.rx[2 * k + 1] -= AD_LOOP;
    }
    S.x = (uint16_t)AD_START_X << 8; S.y = (uint16_t)AD_START_Y << 8;
    // the screen: the framework's wall stays on rows 1-3 and 15-16; the stage over it
    if (is_cgb) for (r = 2; r < 4; r++) {        // rows 2-3: the venue wall's attributes (the framework put the HUD colours there)
        for (c = 0; c < 20; c++) ta[c] = venue.bar_attr[(r & 1) * 20 + 2 + (c < 15 ? c : c - 15)];
        ad_put(1, ta, 0, r, 20);
    }
    for (r = 4; r < 15; r++) {
        sky_row(r, tb, ta);
        ad_put(0, tb, 0, r, 20);
        if (is_cgb) ad_put(1, ta, 0, r, 20);
        if (r == AD_BANNER_ROW) for (k = 0; k < 20; k++) { S.r14[k] = tb[k]; S.r14a[k] = ta[k]; }
    }
    for (c = 0; c < 20; c++) { tb[c] = AD_BG + ad_counter[(c >> 1) & 1]; ta[c] = PAL_COUNTER; }
    ad_put(0, tb, 0, 17, 20);
    if (is_cgb) ad_put(1, ta, 0, 17, 20);
    for (k = 0; k < 3; k++) {
        put_porthole(k, k == S.lit, 0);
        if (is_cgb) {
            for (r = 0; r < 3; r++) { ta[0] = ta[1] = ta[2] = PAL_ALIEN + k; ad_put(1, ta, porthole_col[k], 1 + r, 3); }
        }
    }
    for (k = 0; k < 20; k++) S.hattr[k] = BGPAL_HUD;
    for (k = 0; k < 20; k++) {                   // map rows 2-3: the banner rows' place
        S.wall[0][k] = v[2 * 32 + k]; S.wall[1][k] = v[3 * 32 + k];
    }
    if (is_cgb) {
        VBK_REG = VBK_BANK_1;
        for (k = 0; k < 20; k++) { S.wattr[0][k] = v[2 * 32 + k]; S.wattr[1][k] = v[3 * 32 + k]; }
        VBK_REG = VBK_BANK_0;
        ad_put(1, S.hattr, 0, 2, 20);            // the intro text rows (the name, the instructions) in the HUD colours, as the other
        ad_put(1, S.hattr, 0, 3, 20);            // mini-games' banners (the portholes' palettes made them unreadable)
    }
    hud_deliveries(); hud_time();
    vram_put(11, HUD_ROW, S.dbuf, 3);
    vram_put(16, HUD_ROW, S.tbuf, 4);
    if (is_cgb) {                                // the HUD's attributes are the row's already
        for (k = 0; k < 3; k++) ta[k] = BGPAL_HUD;
        VBK_REG = VBK_BANK_1;
        vram_put(11, HUD_ROW, ta, 3);
        VBK_REG = VBK_BANK_0;
    }
    draw();                                      // the beaker on the bar, the rocks at rest (no play before MG_PLAY)
}

// ---- the sprites -----------------------------------------------------------------------------------------------------
static void obj(uint8_t i, int16_t x, int16_t y, uint8_t tile, uint8_t prop) {   // screen px of the top-left
    OAM_item_t *o = shadow_OAM + i;
    if (x <= -8 || x >= 160 || tile == 0xFF) { o->y = 0; return; }
    o->y = (uint8_t)(y + 16); o->x = (uint8_t)(x + 8); o->tile = tile; o->prop = prop;
}

// The edge warning: a lane's arrow blinks at the edge a rock is about to come in from, from AD_WARN frames before it enters. The rocks
// run round a 176 px ring and are off screen (core x < 0 or >= 160) only for u in [174, 2) (4 px), so a rock "comes in" at the far
// edge the moment it goes out at the near one: the time left is the distance to the near edge. Right-moving lanes (0, 2, 4) come in
// at the left edge (u = 2), left-moving ones at the right edge (u = 174).
static uint8_t warn_lane(uint8_t lane) {
    uint8_t j, k;
    uint16_t u, dist;
    for (j = 0; j < 2; j++) {
        k = 2 * lane + j;
        if (!rock_on(k)) continue;
        u = S.rx[k];
        if (!(lane & 1)) dist = u < (2u << 8) ? (2u << 8) - u : (178u << 8) - u;
        else dist = u > (174u << 8) ? u - (174u << 8) : u + (2u << 8);
        if (dist <= (uint16_t)AD_WARN * lane_speed[S.spd][lane]) return 1;
    }
    return 0;
}

static void draw(void) {
    uint8_t k, f, lane, prop;
    int16_t bx = S.x >> 8, by = S.y >> 8, x;
    OAM_item_t *o;
    for (k = OAM_BEAKER; k < OAM_ROCK; k++) shadow_OAM[k].y = 0;
    if (S.st == AS_FLY || S.st == AS_OUT) {
        obj(OAM_BEAKER, bx - 4, by, OBJ_MUG, OPAL_BEAKER | S_PALETTE);
        f = (S.anim >> 3) & 1;
        obj(OAM_HALO, bx - 8, by, ad_halo[2 * f], OPAL_FX | S_PALETTE);
        obj(OAM_HALO + 1, bx, by, ad_halo[2 * f + 1], OPAL_FX | S_PALETTE);
        if (S.st == AS_FLY && (S.tx || S.ty)) {  // the thrust puff, on the side the beaker is pushed away from
            x = bx - 4 - S.tx * (S.ty ? 4 : 8);
            obj(OAM_PUFF, x, S.ty > 0 ? by - 10 : S.ty < 0 ? by + 14 : by + 4, ad_puff[(S.anim >> 2) & 1],
                OPAL_FX | S_PALETTE);
        }
    } else if (S.st == AS_TUMBLE) {              // the three turns, falling
        f = (S.t / 5) % 3;
        obj(OAM_BEAKER, bx - 8, by + ((S.t * 5) >> 3), ad_tumble[2 * f], OPAL_BEAKER | S_PALETTE);
        obj(OAM_BEAKER + 1, bx, by + ((S.t * 5) >> 3), ad_tumble[2 * f + 1], OPAL_BEAKER | S_PALETTE);
    }
    for (lane = 0; lane < 5; lane++) {           // the edge arrows (blinking 4 frames on, 4 off)
        k = OAM_WARN + lane;
        if (S.st != AS_OUT && ((S.anim >> 2) & 1) && warn_lane(lane))
            obj(k, (lane & 1) ? 152 : 0, AD_LANE_TOP0 + 16 * lane, ad_edge[0], OPAL_ARROW | S_PALETTE | ((lane & 1) ? 0x20 : 0));
        else shadow_OAM[k].y = 0;
    }
    f = (S.anim / 10) & 1;                       // the arrow under the lit dock, bobbing 2 px
    obj(OAM_ARROW, porthole_cx[S.lit] - 4, AD_LANE_TOP0 + (f ? 2 : 0), ad_arrow[f], OPAL_ARROW | S_PALETTE);
    o = shadow_OAM + OAM_SPIG;                   // the Spigoteer's bust: his idle frame's top two entries
    o->y = SPIG_Y + 16; o->x = SPIG_X + 8; o->tile = SPIG_FRAME_IDLE * BARTENDER_TILES_PER_FRAME; o->prop = 0; o++;
    o->y = SPIG_Y + 16; o->x = SPIG_X + 16; o->tile = SPIG_FRAME_IDLE * BARTENDER_TILES_PER_FRAME + 2; o->prop = 0;
    for (k = 0; k < AD_ROCKS; k++) {             // a rock's two halves
        lane = k >> 1;
        if (!rock_on(k)) { shadow_OAM[OAM_ROCK + 2 * k].y = shadow_OAM[OAM_ROCK + 2 * k + 1].y = 0; continue; }
        f = (lane + k) & 1;                      // the two shapes alternate along a lane and across lanes
        x = (int16_t)(S.rx[k] >> 8) - 16;
        prop = OPAL_ROCK | S_PALETTE;
        obj(OAM_ROCK + 2 * k, x, AD_LANE_TOP0 + 16 * lane, ad_rock[2 * f], prop);
        obj(OAM_ROCK + 2 * k + 1, x + 8, AD_LANE_TOP0 + 16 * lane, ad_rock[2 * f + 1], prop);
    }
}

// ---- play ------------------------------------------------------------------------------------------------------------------
static void banner(const char *s) {              // row 14 in the HUD colours
    mg_say(AD_BANNER_ROW, s);
    if (is_cgb) vq_add(1, S.hattr, 0, AD_BANNER_ROW, 20);
}

static void banner_off(void) {                   // row 14 is sky again
    vq_add(0, S.r14, 0, AD_BANNER_ROW, 20);
    if (is_cgb) vq_add(1, S.r14a, 0, AD_BANNER_ROW, 20);
}

static void spawn(void) {
    S.st = AS_FLY; S.t = 0;
    S.x = (uint16_t)AD_START_X << 8; S.y = (uint16_t)AD_START_Y << 8;
    S.vx = S.vy = 0;
}

static int16_t drag(int16_t v) {                 // v -= v / 32 (towards 0); under 32 (1/8 px) it loses 1 a frame so it stops
    int16_t d = v > 0 ? v >> 5 : (-v) >> 5;
    if (!d && v) d = 1;
    return v > 0 ? v - d : v + d;
}

static int16_t axis(int16_t v, int8_t t) {       // thrust, cap, drag
    if (t) {
        v += t * AD_THRUST;
        if (v > AD_CAP) v = AD_CAP; else if (v < -AD_CAP) v = -AD_CAP;
    }
    return drag(v);
}

static uint16_t absv(int16_t v) { return v < 0 ? -v : v; }

static void hit_test(void) {                     // the beaker's body against the 10 rocks' cores
    uint8_t k;
    int16_t bx = S.x >> 8, by = S.y >> 8, rx, ry;
    for (k = 0; k < AD_ROCKS; k++) {
        if (!rock_on(k)) continue;
        ry = AD_LANE_TOP0 + 16 * (k >> 1);
        if (by + 3 >= ry + 14 || by + 15 <= ry + 2) continue;
        rx = (int16_t)(S.rx[k] >> 8) - 16;
        if (bx + 3 <= rx + 2 || bx - 3 >= rx + 14) continue;
        S.st = AS_TUMBLE; S.t = 0; S.spills++;
        S.vx = S.vy = 0;
        S.spawn = AD_SPILL_WAIT;
        SFX(SFX_BREAK);
        return;
    }
}

static void deliver(void) {
    uint16_t pts = AD_PTS;
    uint8_t next;
    if (S.clk < AD_PAR) pts += (AD_PAR - S.clk) / 10;
    mg_points(pts);
    S.delivered++;
    if (S.delivered == AD_STEP1) S.spd = 1; else if (S.delivered == AD_STEP2) S.spd = 2;
    hud_deliveries();
    vq_add(0, S.dbuf, 11, HUD_ROW, 3);
    put_porthole(S.lit, 0, 0);                   // this one goes dark, another lights (never the same twice)
    next = (S.lit + 1 + mg_rand() % 2) % 3;
    S.lit = next;
    put_porthole(next, 1, 1);
    S.clk = 0;
    S.st = AS_GAP; S.t = 0; S.spawn = AD_DELIVER_WAIT;
    SFX(SFX_SERVE);
    SFX(SFX_COIN);
}

static void whoa(void) {                         // too fast at the hand zone: it bounces, nothing lost
    S.vx = -(S.vx >> 1);
    S.vy = S.vy < 0 ? -(S.vy >> 1) : (S.vy >> 1);
    S.y = (uint16_t)AD_Y_MIN << 8;
    S.bounced++;
    S.whoa = AD_WHOA_LEN;
    banner("WHOA");
    SFX(SFX_SHAKE);
}

static void beaker(void) {                       // the thrust, the walls, the dock, the rocks
    uint16_t zx = (uint16_t)porthole_cx[S.lit] - AD_ZONE_HALF, ymin;
    uint8_t bx;
    if (S.st == AS_OUT) S.tx = S.ty = 0;         // (the outro: the beaker drifts to a stop)
    else {
        S.tx = ((joy & J_RIGHT) ? 1 : 0) - ((joy & J_LEFT) ? 1 : 0);
        S.ty = ((joy & J_DOWN) ? 1 : 0) - ((joy & J_UP) ? 1 : 0);
    }
    S.vx = axis(S.vx, S.tx);
    S.vy = axis(S.vy, S.ty);
    S.x += S.vx; S.y += S.vy;                    // (4 <= x <= 156 px and 24 <= y <= 120 px: no wrap)
    if (S.x < ((uint16_t)AD_X_MIN << 8)) { S.x = (uint16_t)AD_X_MIN << 8; S.vx = 0; }
    else if (S.x > ((uint16_t)AD_X_MAX << 8)) { S.x = (uint16_t)AD_X_MAX << 8; S.vx = 0; }
    bx = S.x >> 8;
    ymin = (bx + 3 > zx && bx < zx + 2 * AD_ZONE_HALF + 3) ? AD_Y_MIN_DOCK : AD_Y_MIN;      // over the lit dock the way is open
    if (S.y > ((uint16_t)AD_Y_MAX << 8)) { S.y = (uint16_t)AD_Y_MAX << 8; S.vy = 0; }
    else if (S.y < (ymin << 8)) { S.y = ymin << 8; S.vy = 0; }
    if (S.st != AS_FLY) return;
    if (S.y < ((uint16_t)AD_Y_MIN << 8)) {       // the flask's top is on the dock: soft enough, or WHOA
        if (absv(S.vx) <= AD_SLOW && absv(S.vy) <= AD_SLOW) deliver();
        else whoa();
        return;
    }
    hit_test();
}

static void outro_begin(void) {
    S.st = AS_OUT; S.t = 0; S.whoa = 0;
    banner("TIME UP");
}

void ad_update(uint8_t pressed) BANKED {
    uint8_t k, s;
    uint16_t sp;
    (void)pressed;
    if (mg_phase == MG_END && S.st != AS_OUT) outro_begin();   // (also when a test ends the game early)
    if (!S.started) {                            // the first frame: the banner rows (the framework's text) become portholes again
        S.started = 1;
        vq_add(0, S.wall[0], 0, 2, 20); vq_add(0, S.wall[1], 0, 3, 20);
        if (is_cgb) { vq_add(1, S.wattr[0], 0, 2, 20); vq_add(1, S.wattr[1], 0, 3, 20); }
    }
    S.anim++;
    if (S.t < 255) S.t++;
    for (k = 0; k < AD_ROCKS; k++) {             // the rocks drift (lane 0 right, then alternating)
        sp = lane_speed[S.spd][k >> 1];
        if (!((k >> 1) & 1)) {
            S.rx[k] += sp;
            if (S.rx[k] >= AD_LOOP) S.rx[k] -= AD_LOOP;
        } else {
            if (S.rx[k] < sp) S.rx[k] += AD_LOOP;
            S.rx[k] -= sp;
        }
    }
    if (S.st != AS_OUT && S.clk < 65535) S.clk++;
    switch (S.st) {
    case AS_FLY: case AS_OUT: beaker(); break;
    case AS_TUMBLE:
        if (S.spawn) S.spawn--;
        if (S.t >= AD_TUMBLE) { S.st = AS_GAP; S.t = 0; }
        break;
    default:                                     // no beaker: a new one is coming
        if (S.spawn) S.spawn--;
        if (!S.spawn) spawn();
        break;
    }
    if (S.whoa && S.st != AS_OUT && !--S.whoa) banner_off();
    if (S.st != AS_OUT) {
        if (S.time) S.time--;
        s = secs_left(S.secs, S.time);
        if (s != S.secs) { S.secs = s; hud_time(); vq_add(0, S.tbuf, 16, HUD_ROW, 4); }
        if (!S.time) { mg_finish(); outro_begin(); }
    }
    draw();
}

uint8_t ad_medal(void) BANKED {
    return S.delivered >= AD_GOLD ? MEDAL_GOLD : S.delivered >= AD_SILVER ? MEDAL_SILVER
         : S.delivered >= AD_BRONZE ? MEDAL_BRONZE : MEDAL_NONE;
}
