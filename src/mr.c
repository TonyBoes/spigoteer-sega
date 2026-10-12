// MILK RUN, The Chrome Cow's mini-game (docs/minigames_bosses.md 4.10; art approved by the owner 2026-10-12: the R7a bike
// and rider, the DMG look V1 of round 8, the V1 verge, the road, boxes, cones, potholes, crates, stars and PERFECT pop).
//
// Granny's motorcycle, seen from above and in front, rides a three-lane street that scrolls past. Potholes and traffic
// cones come in gates (one or two lanes blocked, never all three); milk boxes stand on the kerbs. Up / Down change lane
// (8 frames, a press during a change is queued), A tosses a crate to the kerb beside the bike's lane (lane 1 up, lane 3
// down; in lane 2 he shrugs, nothing lost). 12 crates, 45 seconds.
//
// Rules (the spec's numbers; fixed point 1/16 px):
// - The street scrolls at 1.5 px a frame, +0.25 every 10 s (2.5 from 40 s); a crash drops one step (not below 1.5).
//   HARD (Practice): it starts at 2.0 and a crash does not drop it below 2.0 (a spec gap: the spec has no HARD setting).
// - A crate flies 16 frames from the bike (screen x 34, the centre of the crate) to the kerb while the street moves under
//   it, so it lands where the box has come to. Within 8 px of a box's centre: PERFECT, 500; within 16: delivered, 300;
//   anywhere else (or on a full box) it is lost on the pavement. Two crates at most in the air. No tosses in a wobble.
// - A crash (the bike's 16x12 hit box touches an obstacle): the bike wobbles 30 frames with stars, one crate falls off
//   (lost), the speed drops one step, then 60 frames of blinking invulnerability.
// - At time up each crate left is +100. Medal by deliveries (mr_medal): GOLD 10, SILVER 7, BRONZE 4.
// - The gates: the next gate is at least v x (8 x L + 20 + 12) px ahead of the last (v 2.5 px, the fastest the street
//   goes), L the lanes the bike must cross between a free lane of one and of the next; potholes or cones at random. A box
//   is never from GATE_BEFORE columns before to GATE_AFTER after a gate that blocks its kerb's lane (the bike can be in that
//   lane for a toss and leave it again; whichever of the two was made later gives way): a clean run, tosses and all,
//   exists at every seed (tests/test_mg_milkrun.py plays it with a bot). 12 boxes, one every 34-65 columns (about 3.5 s),
//   sides at random. All from mg_rand, so a seed gives one street.
// - Sounds (no new SFX): toss LAUNCH, delivered COIN, PERFECT SERVE, crash BREAK.
//
// Screen: the HUD (score; the crates-left icon and count at columns 9-11; T + seconds at 16-19) is the framework's row 0
// and does not scroll: lcd_isr (src/main.c) splits the frame at line MR_SPLIT_LY, setting SCX there and putting it back at
// the end of the frame, and mr_vbl writes the next map column (17 tiles and, on CGB, 17 attributes, 36 bytes at
// the start of the state) in VBlank. Map rows 1-3 the top verge (houses, trees, lawn, hedge), 4-5 the top kerb (a milk
// box is 2x2 over them), 6-11 the three lanes (the bike's top at y 48 / 64 / 80), 12-13 the bottom kerb, 14-17 the
// bottom verge. A column is generated 21 ahead of the scroll and written when it is due, never two in a frame.
// The banner rows 2-3 are the framework's: the street's tiles there are saved at entry and put back when play starts.
// "TIME UP" is a window banner (rows 32-34, the framework's panel) since the street scrolls under the banner rows.
// CGB BG palettes: 0 road and kerb (and the pothole), 2 / 6 houses (cream and red, white and slate), 3 milk boxes, 5
// greenery, 7 cones (not 4: the result window's medal takes it over while the street still shows); OBJ 0 the Spigoteer,
// 1 the bike and the crates, 2 stars and pop. DMG: BGP 0xE4; the rider on OBP0 = 0xC0 (white skin), the bike, crates, stars and
// pop on OBP1 = 0xE0 (the per-OAM palette bit). OBP0 is set once at boot (0xD0): mg.c puts it back when a mini-game is left.
// OAM 0-2 the bike, 3 the rider, 4-5 stars, 6-7 crates in the air, 8 the lost crate, 9-10 the pop; worst line 4 + 2 + 2 + 1
// = 9. Tiles: BG MG_GAME_BG.. (47), OBJ 56-89 (the mug tiles of the level load come back with it).
#pragma bank 255
#include <gb/gb.h>
#include <gb/cgb.h>
#include <stdint.h>

#include "game.h"
#include "music.h"
#include "mg.h"
#include "mr_art.h"         // this bank's own art (assets/art/milkrun/*.txt)

extern uint8_t overlay_on;

#define S               (MG->mr)
#define MR_BG           MG_GAME_BG
#define MR_OBJ          OBJ_MUG                  // 56..89
typedef char mr_fits[(MR_OBJ + MR_OBJ_TILES <= OBJ_COIN && MR_BG + MR_BG_TILES <= 256) ? 1 : -1];
typedef char mr_offsets[(__builtin_offsetof(struct mr_state, ctile) == 2 && __builtin_offsetof(struct mr_state, cattr) == 19
                         && __builtin_offsetof(struct mr_state, colq) == 36 && __builtin_offsetof(struct mr_state, scx) == 37) ? 1 : -1];
#define MR_TIME_S       45
#define MR_CRATES       12
#define MR_BOXES        12
#define MR_SPEED0       24                       // 1.5 px a frame, in 1/16 px
#define MR_SPEED_STEP    4                       // 0.25
#define MR_STEPS_MAX     4                       // 2.5 px from 40 s
#define MR_STEP_FRAMES 600                       // 10 s
#define MR_HARD_STEPS    2                       // HARD: from 2.0 px a frame, and no slower
#define MR_LANE_FRAMES   8
#define MR_LANE_PX       2                       // a lane change moves 2 px a frame (16 px)
#define MR_FLIGHT       16                       // frames a crate is in the air
#define MR_AIR           2                       // crates in the air at once
#define MR_PERFECT       8                       // px from a box's centre
#define MR_DELIVERED    16
#define MR_PTS_DELIVERED 300
#define MR_PTS_PERFECT   500
#define MR_PTS_CRATE     100                     // each crate left at the end
#define MR_WOBBLE       30
#define MR_BLINK        60
#define MR_GOLD         10
#define MR_SILVER        7
#define MR_BRONZE        4
#define MR_POP_LEN      50
#define MR_BANNER_OFF   54                       // MG_END frame the TIME UP banner goes (the result is at 60)
#define MR_BANNER_ROW   33                       // the window's text row
// the layout
#define BIKE_X          24
#define BIKE_HIT_X       4                       // the hit box: x + 4 .. +20, y + 2 .. +14
#define BIKE_HIT_W      16
#define BIKE_HIT_Y       2
#define BIKE_HIT_H      12
#define LANE_TOP0       48                       // the lanes' tops (map rows 6, 8, 10)
#define LANE_H          16
#define CRATE_DX         6                       // the crate's x from the bike's (its centre is at x + 10 = 34)
#define CRATE_CX        34
#define TOSS_Y1_TOP     24                       // the crate sprite's top as it lands on the top box / the bottom box
#define TOSS_Y1_BOT     88
#define POP_Y_TOP       28                       // the pop's y over the top box, under the bottom box
#define POP_Y_BOT      116
#define LEAD            21                       // columns streamed ahead of the scroll's column
#define GATE_BEFORE      9                       // a gate from this many columns before a box to GATE_AFTER after it must leave the box's kerb lane free
#define GATE_AFTER       4
#define COUNT_COL        9                       // HUD: blank at 8, the crate icon at 9, two digits
#define HUD_PAL_COLS    20
#define MR_STREET_W     32                       // map columns
#define GATE            0x80
#define BOX             0x40
#define FULL            0x02
#define BOTTOM          0x01
#define NO_BOX          0xFFFF
// OAM
#define OAM_BIKE         0
#define OAM_RIDER        3
#define OAM_STARS        4
#define OAM_CRATE        6
#define OAM_LOST         8
#define OAM_POP          9
#define OAM_N           11
// CGB palettes
#define PAL_ROAD         0
#define PAL_HOUSE_A      2
#define PAL_BOX          3
#define PAL_GREEN        5
#define PAL_HOUSE_B      6
#define PAL_CONE         7
#define OPAL_BIKE        1
#define OPAL_FX          2
enum { MS_RIDE, MS_OUT };
enum { F_ABOVE, F_BELOW };

static const uint8_t lane_top[3] = { LANE_TOP0, LANE_TOP0 + LANE_H, LANE_TOP0 + 2 * LANE_H };

// ---- the street ---------------------------------------------------------------------------------------------------
static uint8_t crossing(uint8_t prev, uint8_t mask) {   // lanes to cross from a free lane of `prev` to one of `mask`
    uint8_t a, b, d, best = 2;
    for (a = 0; a < 3; a++) {
        if ((prev >> a) & 1) continue;
        for (b = 0; b < 3; b++) {
            if ((mask >> b) & 1) continue;
            d = a > b ? a - b : b - a;
            if (d < best) best = d;
        }
    }
    return best;
}

static uint8_t near_col(uint16_t g, uint16_t b) {       // a gate at column g and a box at b share a zone
    return g + GATE_BEFORE >= b && g <= b + GATE_AFTER;
}

static void gen_gate(uint16_t prev, uint8_t prev_kind) {   // the next gate after one at `prev` with kind byte prev_kind
    uint8_t mask = 1 + mg_rand() % 6, pot = mg_rand() & 7, l = crossing(prev_kind & 7, mask);
    uint16_t col = prev + ((20 * l + 87) >> 3) + (mg_rand() & 15);   // v x (8 L + 32) px at 2.5 px a frame, in columns
    if (S.bcol != NO_BOX && near_col(col, S.bcol)) mask &= ~(S.bside ? 4 : 1);   // the pending box's kerb lane stays free
    S.gcol = col;
    S.gkind = mask ? (GATE | (pot << 3) | mask) : 0;
}

static uint8_t box_hits(uint16_t col, uint8_t side) {
    return S.gkind && near_col(S.gcol, col) && ((S.gkind >> (side ? 2 : 0)) & 1);
}

static void gen_box(uint16_t prev) {
    uint16_t col = prev + 34 + (mg_rand() & 31);
    uint8_t side = mg_rand() & 1;
    while (box_hits(col, side)) {
        if (!box_hits(col, side ^ 1)) side ^= 1; else col += 6;
    }
    S.bcol = col; S.bside = side;
    S.boxes_made++;
}

static void push(uint16_t col, uint8_t kind) {
    uint8_t i;
    for (i = 0; i < MR_FT; i++)
        if (!S.fkind[i]) { S.fcol[i] = col; S.fkind[i] = kind; return; }
}

// the column c of the street into S.ctile / S.cattr (rows 1-17); the features that have come to it join the live ones
static void make_column(uint16_t c) {
    uint8_t *t = S.ctile, *a = S.cattr, i, k, r, e, lane, d, p;
    while (S.gcol <= c) {                        // the next gate has come: it is live, and the one after it is made
        uint16_t g = S.gcol;
        k = S.gkind;
        if (k) push(g, k);
        gen_gate(g, k);
    }
    while (S.bcol <= c) {
        push(S.bcol, BOX | (S.bside ? BOTTOM : 0));
        if (S.boxes_made < MR_BOXES) gen_box(S.bcol); else S.bcol = NO_BOX;
    }
    p = S.ti * 3;                                // the top verge, map rows 1-3
    for (i = 0; i < 3; i++) { t[i] = MR_BG + mr_top_t[p + i]; a[i] = mr_top_a[p + i]; }
    if (++S.ti == MR_TOP_N) S.ti = 0;
    t[3] = MR_BG + MRB_SLAB; t[4] = MR_BG + MRB_KERB_TOP;                       // rows 4-5: the top kerb
    for (i = 5; i < 11; i++) t[i] = MR_BG + MRB_ROAD0;                          // rows 6-11: the lanes
    if (!(c & 1)) { t[7] = MR_BG + MRB_ROAD1; t[9] = MR_BG + MRB_ROAD1; }       // the lane lines' dashes
    t[11] = MR_BG + MRB_KERB_BOT; t[12] = MR_BG + MRB_SLAB;                     // rows 12-13: the bottom kerb
    for (i = 3; i < 13; i++) a[i] = PAL_ROAD;
    p = S.bi * 4;                                // the bottom verge, rows 14-17
    for (i = 0; i < 4; i++) { t[13 + i] = MR_BG + mr_bot_t[p + i]; a[13 + i] = mr_bot_a[p + i]; }
    if (++S.bi == MR_BOT_N) S.bi = 0;
    for (e = 0; e < MR_FT; e++) {
        k = S.fkind[e];
        if (!k) continue;
        d = (uint8_t)(c - S.fcol[e]);
        if (c < S.fcol[e] || d > 1) continue;
        if (k & GATE) {
            for (lane = 0; lane < 3; lane++) {
                if (!((k >> lane) & 1)) continue;
                r = 5 + 2 * lane;
                if ((k >> (3 + lane)) & 1) { t[r] = MR_BG + MRB_POT + d; t[r + 1] = MR_BG + MRB_POT + 2 + d; }
                else {
                    t[r] = MR_BG + MRB_CONE; t[r + 1] = MR_BG + MRB_CONE + 1;
                    a[r] = a[r + 1] = PAL_CONE;
                }
            }
        } else {                                 // a milk box over the kerb's two rows
            r = (k & BOTTOM) ? 11 : 3;
            i = MR_BG + MRB_BOX + 4 * (((k & BOTTOM) ? 2 : 0) + ((k & FULL) ? 1 : 0));
            t[r] = i + d; t[r + 1] = i + 2 + d;
            a[r] = a[r + 1] = PAL_BOX;
        }
    }
}

static void put_column_now(uint16_t c) {         // LCD off: the column c as it is in S.ctile / S.cattr
    uint8_t x = c & (MR_STREET_W - 1);
    set_bkg_tiles(x, 1, 1, MR_COL_ROWS, S.ctile);
    if (is_cgb) {
        VBK_REG = VBK_BANK_1;
        set_bkg_tiles(x, 1, 1, MR_COL_ROWS, S.cattr);
        VBK_REG = VBK_BANK_0;
    }
}

static void stream(void) {                       // play: the next column, when it is due and the last one is written
    uint16_t c = S.next_col;
    if (S.colq || c >= (S.px >> 3) + LEAD + 1) return;
    make_column(c);
    S.dst = 0x9800 + 32 + (c & (MR_STREET_W - 1));
    S.colq = 1;
    S.next_col = c + 1;
}

// ---- screen --------------------------------------------------------------------------------------------------------
static void put(uint8_t bank, uint8_t *t, uint8_t col, uint8_t row, uint8_t n) {
    vq_add(bank, t, col, row, n);
}

static void hud_crates(void) {                   // HUD columns 8-11: blank, the crate icon, the count
    S.cbuf[0] = TILE_HUD_BLANK; S.cbuf[1] = MR_BG + MRB_HUDC;
    S.cbuf[2] = TILE_GLYPH_0 + S.crates / 10; S.cbuf[3] = TILE_GLYPH_0 + S.crates % 10;
}

static void hud_time(void) {                     // 'T' + seconds (3 digits) at columns 16-19, as the framework's timer
    uint8_t s = S.secs, h = 0, t = 0;
    while (s >= 100) { s -= 100; h++; }
    while (s >= 10) { s -= 10; t++; }
    S.tbuf[0] = TILE_GLYPH_T; S.tbuf[1] = TILE_GLYPH_0 + h; S.tbuf[2] = TILE_GLYPH_0 + t; S.tbuf[3] = TILE_GLYPH_0 + s;
}

static uint8_t secs_left(void) { return (uint8_t)((S.time + 59) / 60); }

static void draw(void);

void mr_enter(void) BANKED {
    uint16_t p[4];
    uint8_t k, *v = (uint8_t *)0x9800;
    uint8_t *z = (uint8_t *)&S;
    for (k = 0; k < sizeof(struct mr_state); k++) z[k] = 0;
    CRITICAL {                                   // (mg_enter has put the normal handlers back: a retry has no mg_leave)
        remove_LCD(lcd_isr);
        add_LCD(mr_lcd_isr);                     // the raster split (main.c)
        add_VBL(mr_vbl);                         // the street's next column, in VBlank (main.c)
    }
    set_bkg_data(MR_BG, MR_BG_TILES, mr_bg_tiles);
    set_sprite_data(MR_OBJ, MR_OBJ_TILES, mr_obj_tiles);
    if (is_cgb) {
        p[0] = RGB8(232, 224, 208); p[1] = RGB8(120, 112, 136); p[2] = RGB8(168, 168, 192); p[3] = RGB8(32, 24, 32);
        set_bkg_palette(PAL_ROAD, 1, p);         // road and kerb: slab / lane dash, asphalt, kerb steel, dark
        p[0] = RGB8(240, 224, 184); p[1] = RGB8(120, 184, 72); p[2] = RGB8(192, 80, 56);
        set_bkg_palette(PAL_HOUSE_A, 1, p);      // houses: cream wall, lawn, red roof
        p[0] = RGB8(224, 232, 240); p[2] = RGB8(72, 104, 168);
        set_bkg_palette(PAL_HOUSE_B, 1, p);      // white wall, slate roof
        p[0] = RGB8(248, 248, 232); p[2] = RGB8(44, 120, 64);
        set_bkg_palette(PAL_GREEN, 1, p);        // greenery: picket, lawn, leaf
        p[0] = RGB8(232, 224, 208); p[1] = RGB8(208, 56, 72); p[2] = RGB8(168, 168, 192);
        set_bkg_palette(PAL_BOX, 1, p);          // milk boxes: slab, crate red, steel (the kerb)
        p[0] = RGB8(248, 248, 240); p[1] = RGB8(120, 112, 136); p[2] = RGB8(240, 120, 40);
        set_bkg_palette(PAL_CONE, 1, p);         // cones: white band, asphalt, orange
        p[0] = 0; p[1] = RGB8(248, 248, 240); p[2] = RGB8(208, 56, 72); p[3] = RGB8(32, 32, 48);
        set_sprite_palette(OPAL_BIKE, 1, p);     // the bike and the crates: chrome white, Granny red, dark
        p[2] = RGB8(248, 208, 56);
        set_sprite_palette(OPAL_FX, 1, p);       // the stars and the pop: white, yellow, dark
    } else {
        OBP0_REG = 0xC0;                         // the rider: idx2 (skin) white (round 8's V1); mg.c puts 0xD0 back
        OBP1_REG = 0xE0;                         // the bike, crates, stars, pop: idx2 dark grey
    }
    // the state
    S.steps = (mg_mode & MG_HARD) ? MR_HARD_STEPS : 0;
    S.lane = 1; S.y = lane_top[1]; S.crates = MR_CRATES; S.time = MR_TIME_S * 60; S.secs = MR_TIME_S;
    S.bcol = NO_BOX;
    gen_gate(24, 0);                             // the first gate after column 24; then the first box
    gen_box(0xFFFC);
    // the street's first columns, and the HUD's
    for (k = 0; k < 22; k++) { make_column(k); put_column_now(k); }
    S.next_col = 22;
    for (k = 0; k < 20; k++) {                   // map rows 2-3: the banner rows' place
        S.wall[0][k] = v[2 * 32 + k]; S.wall[1][k] = v[3 * 32 + k];
    }
    for (k = 0; k < 12; k++) row_buf[k] = TILE_HUD_BLANK;
    vram_put(20, HUD_ROW, row_buf, 12);          // the HUD row's other columns (the split's last line shows them)
    hud_crates(); hud_time();
    vram_put(COUNT_COL - 1, HUD_ROW, S.cbuf, 4);
    vram_put(16, HUD_ROW, S.tbuf, 4);
    if (is_cgb) {
        VBK_REG = VBK_BANK_1;
        for (k = 0; k < 20; k++) { S.wattr[0][k] = v[2 * 32 + k]; S.wattr[1][k] = v[3 * 32 + k]; }
        for (k = 0; k < 12; k++) row_buf[k] = BGPAL_HUD;
        vram_put(20, HUD_ROW, row_buf, 12);
        VBK_REG = VBK_BANK_0;
    }
    draw();                                      // the bike at rest (no play before MG_PLAY)
}

// ---- the sprites -------------------------------------------------------------------------------------------------------
static void obj(uint8_t i, int16_t x, uint8_t y, uint8_t tile, uint8_t prop) {   // screen px of the top-left
    OAM_item_t *o = shadow_OAM + i;
    if (x <= -8 || x >= 160) { o->y = 0; return; }
    o->y = y + 16; o->x = (uint8_t)(x + 8); o->tile = tile; o->prop = prop;
}

static void draw(void) {
    uint8_t k, f, y, t;
    int16_t y0, y1;
    for (k = OAM_BIKE; k < OAM_N; k++) shadow_OAM[k].y = 0;
    if (!(S.inv && S.inv <= MR_BLINK && ((S.inv >> 2) & 1))) {     // (blinking: every other 4 frames, nothing drawn)
        f = S.inv > MR_BLINK ? 2 : (S.anim >> 3) & 1;                 // wobble, or ride A / B
        for (k = 0; k < 3; k++)
            obj(OAM_BIKE + k, BIKE_X + 8 * k, S.y, MR_OBJ + mr_bike_t[f * 3 + k], OPAL_BIKE | S_PALETTE);
        obj(OAM_RIDER, BIKE_X + (f == 2 ? 5 : 6), S.y - 2,
            MR_OBJ + (f == 2 ? MRO_RIDER_W : f ? MRO_RIDER_B : MRO_RIDER_A), 0);   // the rider: OBJ 0, OBP0
    }
    if (S.inv > MR_BLINK) {                      // the stars circle his head (the second X-flipped)
        obj(OAM_STARS, BIKE_X + 6, S.y - 10, MR_OBJ + MRO_STARS, OPAL_FX | S_PALETTE);
        obj(OAM_STARS + 1, BIKE_X + 14, S.y - 6, MR_OBJ + MRO_STARS, OPAL_FX | S_PALETTE | S_FLIPX);
    }
    for (k = 0; k < MR_AIR; k++) {               // a crate in the air: its shadow keeps the bottom of the sprite
        t = S.toss[k].t;
        if (!t || t > MR_FLIGHT) continue;
        y0 = (int16_t)S.toss[k].y0 - 2;
        y1 = S.toss[k].side ? TOSS_Y1_BOT : TOSS_Y1_TOP;
        y = (uint8_t)(y0 + ((y1 - y0) * t) / MR_FLIGHT);
        obj(OAM_CRATE + k, BIKE_X + CRATE_DX, y, MR_OBJ + (t >= 4 && t <= 11 ? MRO_CRATE_HI : MRO_CRATE_LO),
            OPAL_BIKE | S_PALETTE);
    }
    if (S.lost_t)                                // the crate that fell off, left on the street behind him
        obj(OAM_LOST, (int16_t)(S.lost_x - S.px), S.lost_y, MR_OBJ + MRO_CRATE_LO, OPAL_BIKE | S_PALETTE);
    if (S.pop_t) {                               // PERFECT over its box, rising 4 px
        y = S.pop_y - (MR_POP_LEN - S.pop_t) / 12;
        y0 = (int16_t)(S.pop_x - S.px);
        obj(OAM_POP, y0, y, MR_OBJ + MRO_POP_L, OPAL_FX | S_PALETTE);
        obj(OAM_POP + 1, y0 + 8, y, MR_OBJ + MRO_POP_R, OPAL_FX | S_PALETTE);
    }
}

// ---- play --------------------------------------------------------------------------------------------------------------
static void put_hud_crates(void) {
    hud_crates();
    vq_add(0, S.cbuf, COUNT_COL - 1, HUD_ROW, 4);
}

static void lane_press(int8_t d) {
    if (S.y != lane_top[S.lane]) { S.queued = d; return; }        // during a change: queued (the last one)
    d += S.lane;
    if ((uint8_t)d <= 2) S.lane = d;
}

static void crash(void) {
    S.inv = MR_WOBBLE + MR_BLINK;
    if (S.steps > ((mg_mode & MG_HARD) ? MR_HARD_STEPS : 0)) S.steps--;
    if (S.crates) {                              // one crate falls off
        S.crates--;
        put_hud_crates();
        S.lost_t = 1; S.lost_x = S.px + BIKE_X + CRATE_DX; S.lost_y = S.y + 2;
    }
    SFX(SFX_BREAK);
}

static void hit_test(void) {
    uint8_t e, k, lane, hy = S.y + BIKE_HIT_Y;
    uint16_t hx = S.px + BIKE_X + BIKE_HIT_X, gx;
    for (e = 0; e < MR_FT; e++) {
        k = S.fkind[e];
        if (!(k & GATE)) continue;
        gx = S.fcol[e] * 8;
        if (gx >= hx + BIKE_HIT_W || gx + 16 <= hx) continue;
        for (lane = 0; lane < 3; lane++)
            if (((k >> lane) & 1) && hy < lane_top[lane] + LANE_H && hy + BIKE_HIT_H > lane_top[lane]) {
                crash();
                return;
            }
    }
}

static void land(struct mr_toss *c) {            // the crate comes down: on a box, or lost on the pavement
    uint8_t e, k, row, f;
    int16_t d;
    uint16_t x = S.px + CRATE_CX;
    for (e = 0; e < MR_FT; e++) {
        k = S.fkind[e];
        if (!(k & BOX) || (k & FULL) || ((k & BOTTOM) ? 1 : 0) != c->side) continue;
        d = (int16_t)(x - (S.fcol[e] * 8 + 8));
        if (d < 0) d = -d;
        if (d > MR_DELIVERED) continue;
        S.fkind[e] |= FULL;                      // the box's two top tiles: the crate in it
        row = c->side ? 12 : 4;
        f = MR_BG + MRB_BOX + 4 * (c->side * 2 + 1);
        S.boxbuf[0] = f; S.boxbuf[1] = f + 1;
        vq_add(0, S.boxbuf, S.fcol[e] & (MR_STREET_W - 1), row, 1);
        vq_add(0, S.boxbuf + 1, (S.fcol[e] + 1) & (MR_STREET_W - 1), row, 1);
        S.delivered++;
        if (d <= MR_PERFECT) {
            S.perfect++;
            mg_points(MR_PTS_PERFECT);
            S.pop_t = MR_POP_LEN; S.pop_x = S.fcol[e] * 8; S.pop_y = c->side ? POP_Y_BOT : POP_Y_TOP;
            SFX(SFX_SERVE);
        } else {
            mg_points(MR_PTS_DELIVERED);
            SFX(SFX_COIN);
        }
        break;
    }
    c->t = 0;
}

static void outro_begin(void) {
    S.st = MS_OUT; S.clk = 0; S.queued = 0;
    if (S.crates) mg_points(MR_PTS_CRATE * S.crates);
    mg_say(MR_BANNER_ROW, "TIME UP");
    overlay_on = 1;
}

void mr_update(uint8_t pressed) BANKED {
    uint8_t k, e, s;
    uint16_t spd;
    if (mg_phase == MG_END && S.st == MS_RIDE) outro_begin();   // (also when a test ends the game early)
    if (!S.started) {                            // the first frame: the banner rows (the framework's text) become street again
        S.started = 1;
        vq_add(0, S.wall[0], 0, 2, 20); vq_add(0, S.wall[1], 0, 3, 20);
        if (is_cgb) { vq_add(1, S.wattr[0], 0, 2, 20); vq_add(1, S.wattr[1], 0, 3, 20); }
    }
    if (S.st == MS_RIDE) {
        if (pressed & J_UP) lane_press(-1);
        if (pressed & J_DOWN) lane_press(1);
        if (++S.clk >= MR_STEP_FRAMES) { S.clk = 0; if (S.steps < MR_STEPS_MAX) S.steps++; }
    }
    // the bike changes lane, 2 px a frame; a queued press starts the next change when it has arrived
    k = lane_top[S.lane];
    if (S.y < k) S.y += MR_LANE_PX; else if (S.y > k) S.y -= MR_LANE_PX;
    if (S.y == k && S.queued) {
        k = S.lane + S.queued; S.queued = 0;
        if (k <= 2) S.lane = k;
    }
    // the street scrolls (the outro slows it to a stop)
    spd = MR_SPEED0 + MR_SPEED_STEP * S.steps;
    if (S.st == MS_OUT) { spd = spd > S.clk ? spd - S.clk : 0; if (S.clk < 255) S.clk++; }
    S.frac += (uint8_t)spd;
    S.px += S.frac >> 4; S.frac &= 15;
    S.scx = (uint8_t)S.px;
    for (e = 0; e < MR_FT; e++)                  // features that have gone off the left edge
        if (S.fkind[e] && (uint16_t)(S.fcol[e] * 8 + 16) < S.px) S.fkind[e] = 0;
    stream();
    if (S.inv) S.inv--;
    S.anim++;
    if (S.lost_t) {
        if (S.lost_t < 10) { S.lost_t++; S.lost_y += 2; }
        if ((int16_t)(S.lost_x - S.px) <= -8) S.lost_t = 0;
    }
    if (S.pop_t) S.pop_t--;
    for (k = 0; k < MR_AIR; k++)                 // crates in the air
        if (S.toss[k].t && ++S.toss[k].t > MR_FLIGHT) land(&S.toss[k]);
    if (S.st == MS_RIDE) {
        if (!S.inv) hit_test();
        if ((pressed & J_A) && S.inv <= MR_BLINK && S.crates && S.lane != 1)
            for (k = 0; k < MR_AIR; k++)
                if (!S.toss[k].t) {
                    S.toss[k].t = 1; S.toss[k].side = S.lane == 2; S.toss[k].y0 = S.y;
                    S.crates--;
                    put_hud_crates();
                    SFX(SFX_LAUNCH);
                    break;
                }
        if (S.time) S.time--;
        s = secs_left();
        if (s != S.secs) { S.secs = s; hud_time(); vq_add(0, S.tbuf, 16, HUD_ROW, 4); }
        if (!S.time) { mg_finish(); outro_begin(); }
    } else if (mg_t >= MR_BANNER_OFF) overlay_on = 0;
    draw();
}

uint8_t mr_medal(void) BANKED {
    return S.delivered >= MR_GOLD ? MEDAL_GOLD : S.delivered >= MR_SILVER ? MEDAL_SILVER
         : S.delivered >= MR_BRONZE ? MEDAL_BRONZE : MEDAL_NONE;
}
