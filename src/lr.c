// LOG ROLL, the lumber lodge's mini-game (docs/minigames_bosses.md 4.3; art approved by the owner 2026-10-12: look A, the
// daytime river scene; the Spigoteer's 24x24 poses; the lodge show's Sasquatch as the partner, reused as is).
//
// The Spigoteer and a Sasquatch stand on a log that rolls on the river. The roll pushes him off balance: tap Left / Right to
// lean against it, for 40 seconds. A fall is not game over: 3 seconds in the water and climbing back, the timer runs on.
//
// Rules (the spec's numbers; lean in 1/65536 px, "fall beyond +-64 px"):
// - Each frame: a press of Left / Right is vel -= / += 1.0 (a hold does nothing more; both together cancel), then
//   vel += drift, vel -= vel / 16, lean += vel. One tap moves the lean about 15 px in all; two quick taps over-correct.
// - The drift's size ramps from 0.025 to 0.045 px a frame squared over the 40 seconds; its sign flips every 120-240 frames
//   (mg_rand). A flip is TOLD 30 frames before it bites: the log's bark slows, stops and rolls back (the same ramp of 30
//   frames) and a creak sounds; the push itself follows the bark's ramp 30 frames later. 1.5 taps a second hold the
//   centre at the start, 2.7 at the end.
// - A fall (|lean| > 64): the splash and the droplets, LR_FALL_LEN = 180 frames in the water (SPLASH, then CLIMB, then a
//   hop back up), lean 0 on the log again. Only time on the log scores: 100 each second on it (lr_on / 60), +1000 with no
//   fall (NO FALLS 1000 in the outro). Medal by seconds on the log (lr_medal): GOLD 40, SILVER 34, BRONZE 25. One setting
//   (no HARD). If he is up at time up the partner topples into the river (frame 3, X-flipped, a droplet burst).
// - Sounds (no new SFX): the creak SFX_SHAKE, the fall SFX_BREAK, the hop back SFX_LAUNCH, NO FALLS SFX_CATCH.
//
// Screen (the approved mock-up): pines rows 1-4, far bank 5-6, river 7-17 with two ripple tiles, the log on rows 12-13
// (columns 3-16), the meter on row 16 (columns 2-17: marker x = 76 + lean). The log's four body tiles are one of four roll
// frames (a step of the bark = 64 B copied into fixed VRAM slots by a VBlank queue entry of its own), the ripples' two
// tiles one of two frames (32 B, every 20 frames); everything else is resident (tools/gen_lr.py: 40 BG tiles from
// MG_GAME_BG, the streamed slots at BG ids 128+). The HUD: score, the falls icon + digit at columns 9-10, T + seconds.
// CGB BG palettes 2 forest, 3 river, 5 log, 6 meter, 7 bank (4 stays the medal's); OBJ 0 the Spigoteer (the bartender's),
// 5 the Sasquatch (the show's), 1 droplets, 2 marker. DMG: BGP and OBP0 as the level's (every sprite on OBP0).
// OAM: 0 marker, 1-4 droplets, 5-10 the Spigoteer (3 x 2 entries of 8x16), 11-14 the Sasquatch. Worst line 9 (the splash).
// OBJ tiles: the first 18 entries in ids 56-91 (the mugs' and crash frames: the level load puts them back), the rest from
// the first even id above the BG tiles (166..).
#pragma bank 255
#include <gb/gb.h>
#include <gb/cgb.h>
#include <stdint.h>
#include <string.h>

#include "game.h"
#include "music.h"
#include "mg.h"
#include "lr_art.h"         // this bank's own art (assets/art/logroll/*.txt)

#define S               (MG->lr)
#define LR_BG           MG_GAME_BG
#define LR_OBJ_HI       ((LR_BG + LR_BG_TILES + 1) & ~1)   // the entries past the first LR_SLOT_ENTRIES
#define LR_OBJ_HI_N     (LR_ENTRIES - LR_SLOT_ENTRIES)
typedef char lr_fits[(LR_BG + LR_ROLL_AT >= 128 && LR_BG + LR_BG_TILES <= 256 && OBJ_MUG + 2 * LR_SLOT_ENTRIES <= OBJ_COIN
                      && LR_OBJ_HI + 2 * LR_OBJ_HI_N <= OBJ_POUR && LR_ENTRIES > LR_SLOT_ENTRIES) ? 1 : -1];
#define LR_TIME_S       40
#define LR_ONE          65536L                  // 1 px (1.0 px a frame for a press)
#define LR_FALL_PX      64
#define LR_DRIFT0       1638                    // 0.025 (1/65536 px a frame squared); the ramp adds 0.020 over the 40 s
#define LR_RAMP_FRAMES  30                      // a flip's ramp, and how much the bark leads the push
#define LR_FLIP_MIN     120
#define LR_FLIP_RANGE   121                     // 120..240
#define LR_FALL_LEN     180
#define LR_SPLASH_LEN    90                     // SPLASH, then CLIMB
#define LR_HOP_AT       168                     // the last frames of the climb rise onto the log
#define LR_SQ_REACT      60                     // the partner's frame 3 after a fall
#define LR_TOPPLE        16                     // frames of the partner's fall into the river
#define LR_DROPS         44                     // frames of a droplet burst
#define LR_PTS_SEC      100
#define LR_PTS_CLEAN   1000
#define LR_GOLD          40                     // seconds on the log
#define LR_SILVER        34
#define LR_BRONZE        25
#define LR_HIDE_AT       57                     // MG_END frame the figures below the result window's edge go
#define LR_BAND_OFF      40                     // MG_END frame the banner rows go back to the forest
#define LR_RIPPLE_EVERY  20
// the layout
#define LR_SPIG_X        92
#define LR_SPIG_Y        72
#define LR_WATER_Y      100
#define LR_SQ_X          44
#define LR_SQ_Y          72
#define LR_METER_Y      120                     // the marker's top; its centre x is 76 (meter columns 2-17: 128 px)
#define LR_MARK_X0       76
#define LR_DROP_Y        98
#define LR_SPLASH_X     100                     // the splash's droplet origin
#define LR_TOPPLE_X      52
#define LR_HUD_ICON_COL   9
#define LR_HUD_DIGIT_COL 10
#define LR_PAL_DROP       1                     // CGB OBJ palettes
#define LR_PAL_MARK       2
// OAM
#define OAM_MARK         0
#define OAM_DROPS        1
#define OAM_SPIG         5
#define OAM_SQ          11
#define OAM_N           15
// the shifts that stand in for divides below hold for exactly these numbers
typedef char lr_divs[(LR_RAMP_FRAMES == 30 && LR_RIPPLE_EVERY == 20 && LR_TOPPLE == 16 && LR_WATER_Y - LR_SQ_Y == 28
                      && LR_WATER_Y - LR_SPIG_Y == 28 && LR_FALL_LEN - LR_HOP_AT == 12) ? 1 : -1];
enum { LS_RUN, LS_WATER, LS_OVER };             // S.st: on the log; in the water; the outro
enum { BAND_KEEP, BAND_FOREST, BAND_HUD };      // S.band[]: a banner row's pending change
enum { P_CA, P_CB, P_L1, P_L2, P_SPLASH, P_CLIMB };   // poses (tools/gen_lr.py POSES)

// a droplet's launch velocities, 1/128 px a frame (the mock-up's, x 0.9)
static const int16_t drop_vx[4] = { -150, -57, 69, 161 };
static const int16_t drop_vy[4] = { -414, -507, -484, -392 };

// the VBlank queue's entry (src/render.c vq_entry_t): a tile copy needs an address vq_add cannot name (it is a map address)
struct vq_raw { uint8_t n, bank; const uint8_t *src; uint8_t *dst; uint8_t pad[2]; };
extern struct vq_raw vq[];
extern uint8_t vq_count;
#define VQ_MAX_RAW      24                      // render.c VQ_MAX

static void put(uint8_t col, uint8_t row, uint8_t *t, uint8_t n) {
    if (LCDC_REG & LCDCF_ON) vq_add(0, t, col, row, n); else vram_put(col, row, t, n);
}

static uint8_t *tile_addr(uint8_t id) {         // BG id -> VRAM (ids >= 128 are the 0x8800 block, shared with OBJ)
    return (uint8_t *)((id < 128 ? 0x9000u : 0x8000u) + (uint16_t)id * 16);
}

static uint8_t stream(uint8_t id, const uint8_t *src, uint8_t n) {   // src: WRAM (the ISR copies it later); 0: queue full
    struct vq_raw *e;
    if (vq_count >= VQ_MAX_RAW) return 0;
    e = &vq[vq_count++];
    e->n = n; e->bank = 0; e->src = src; e->dst = tile_addr(id);
    return 1;
}

static uint8_t otile(uint8_t e) {               // an OBJ entry's (even) tile number
    return e < LR_SLOT_ENTRIES ? OBJ_MUG + 2 * e : LR_OBJ_HI + 2 * (e - LR_SLOT_ENTRIES);
}

static void fill_attr_rows(uint8_t first, uint8_t last) {   // LCD off, CGB: the scene's attributes (rows first..last)
    uint8_t r;
    VBK_REG = VBK_BANK_1;
    for (r = first; r <= last; r++) vram_put(0, r, lr_attr + (r - 1) * 20, 20);
    VBK_REG = VBK_BANK_0;
}

// ---- the physics ----
// No 32-bit multiply or divide anywhere here: the library routines would land in ROM0 (486 B). The ramps are 16-bit.
static int16_t mag(void) {                      // the push's size now: 0.025 + 0.020 x elapsed / 2400 (x 35 / 64); x 35 = shifts
    uint8_t hi = S.elapsed >> 6, lo = S.elapsed & 63;
    return LR_DRIFT0 + ((uint16_t)hi << 5) + ((uint16_t)hi << 1) + hi + ((((uint16_t)lo << 5) + ((uint16_t)lo << 1) + lo) >> 6);
}

static uint16_t mul5(uint16_t v, uint8_t a) {   // v x a, a < 32 (the library's multiply is a 16-step loop; this is five)
    uint16_t p = 0;
    if (a & 1) p += v;
    v <<= 1; if (a & 2) p += v;
    v <<= 1; if (a & 4) p += v;
    v <<= 1; if (a & 8) p += v;
    v <<= 1; if (a & 16) p += v;
    return p;
}

// m x s / 30 (truncated toward 0) without overflowing 16 bits, and without the library's divide or multiply (the divide is
// about 3000 cycles; two calls a frame made the physics most of the frame). m = 30 q + r: q by x17 >> 9 (one short at most,
// mended), then q x |s| + r x |s| / 30 (the last by x69 >> 11: one too many at most, mended). Exact for m < 3856 (the
// game's top is 2950).
static int16_t ramped(uint16_t m, int8_t s) {
    uint8_t a = s < 0 ? -s : s, r;
    uint16_t q = ((m << 4) + m) >> 9, x, j;
    r = m - ((q << 5) - (q << 1));
    if (r >= 30) { r -= 30; q++; }
    x = mul5(r, a);
    j = ((x << 6) + (x << 2) + x) >> 11;
    if (((j << 5) - (j << 1)) > x) j--;
    x = mul5(q, a) + j;
    return s < 0 ? -(int16_t)x : (int16_t)x;
}

static void new_flip(void) {
    S.tsgn = -S.tsgn;
    S.fdelay = LR_RAMP_FRAMES;
    S.flip_in = LR_FLIP_MIN + mg_rand() % LR_FLIP_RANGE;
    SFX(SFX_SHAKE);
}

static void ramps(void) {                       // the bark's ramp turns first, the push's follows 30 frames later
    int8_t goal = S.tsgn * LR_RAMP_FRAMES;
    if (S.tell < goal) S.tell++; else if (S.tell > goal) S.tell--;
    if (S.fdelay) { S.fdelay--; return; }
    if (S.dsr < goal) S.dsr++; else if (S.dsr > goal) S.dsr--;
}

void lr_enter(void) BANKED {
    uint8_t k, r;
    set_bkg_data(LR_BG, LR_BG_TILES, lr_bg_tiles);
    set_sprite_data(OBJ_MUG, 2 * LR_SLOT_ENTRIES, lr_obj_tiles);
    set_sprite_data(LR_OBJ_HI, 2 * LR_OBJ_HI_N, lr_obj_tiles + (uint16_t)2 * LR_SLOT_ENTRIES * 16);
    // the scene: map rows 1-17 (rows 2-3 are the banner's until the first play frame)
    for (r = 1; r <= 17; r++) {
        for (k = 0; k < 20; k++) row_buf[k] = LR_BG + lr_map[(r - 1) * 20 + k];
        vram_put(0, r, row_buf, 20);
    }
    if (is_cgb) {
        fill_attr_rows(1, 1);
        fill_attr_rows(4, 17);
        for (k = 0; k < 5; k++) set_bkg_palette(k < 2 ? 2 + k : 3 + k, 1, lr_pal_bg + 4 * k);   // 2 3 5 6 7
        set_sprite_palette(LR_PAL_DROP, 1, lr_pal_obj);
        set_sprite_palette(LR_PAL_MARK, 1, lr_pal_obj + 4);
    }
    for (k = 0; k < 20; k++) S.hud_attr[k] = BGPAL_HUD;
    // the HUD: no lives; the falls icon and its digit
    row_buf[0] = TILE_HUD_BLANK; row_buf[1] = TILE_HUD_BLANK; row_buf[2] = LR_BG + LRB_HUD; row_buf[3] = TILE_GLYPH_0;
    row_buf[4] = TILE_HUD_BLANK;
    vram_put(LR_HUD_ICON_COL - 1, HUD_ROW, row_buf, 1);
    vram_put(LR_HUD_ICON_COL, HUD_ROW, row_buf + 2, 1);
    vram_put(LR_HUD_DIGIT_COL, HUD_ROW, row_buf + 3, 1);
    vram_put(LR_HUD_DIGIT_COL + 1, HUD_ROW, row_buf + 4, 1);
    // the state
    S.lean = 0; S.vel = 0; S.drift = 0; S.on = 0; S.elapsed = 0; S.roll = 0; S.st = LS_RUN; S.falls = 0; S.fall_t = 0;
    S.s60 = 0; S.roll_f = 0; S.roll_vis = 0; S.rip_f = 0; S.rip_vis = 0; S.anim = 0; S.started = 0; S.ended = 0;
    S.top_t = 0; S.drop_t = 0; S.drop_x = 0; S.band[0] = S.band[1] = BAND_KEEP; S.digit = TILE_GLYPH_0;
    S.tsgn = (mg_rand() & 1) ? 1 : -1;
    S.tell = S.dsr = S.tsgn * LR_RAMP_FRAMES; S.fdelay = 0;
    S.flip_in = LR_FLIP_MIN + mg_rand() % LR_FLIP_RANGE;
    S.drift = ramped(mag(), S.dsr);
    mg_timer = LR_TIME_S * 60;
    lr_update(0);                                // the sprites (the update draws them; no play before MG_PLAY)
}

uint8_t lr_medal(void) BANKED {
    uint8_t s = S.on / 60;
    return s >= LR_GOLD ? MEDAL_GOLD : s >= LR_SILVER ? MEDAL_SILVER : s >= LR_BRONZE ? MEDAL_BRONZE : MEDAL_NONE;
}

static int16_t lean_px(void) {                  // whole px, truncated toward 0 (the same reach to both sides)
    int16_t hi = ((int16_t *)&S.lean)[1];       // (little endian: the floor in whole px; a negative one with a fraction is 1 more)
    return hi < 0 && ((uint16_t *)&S.lean)[0] ? hi + 1 : hi;
}

// ---- the sprites ----
static void ent(uint8_t i, uint8_t x, uint8_t y, uint8_t tile, uint8_t prop) {   // screen px of the top-left
    OAM_item_t *o = shadow_OAM + i;
    o->y = y + 16; o->x = x + 8; o->tile = tile; o->prop = prop;
}

static void spigoteer(uint8_t y, uint8_t f, uint8_t flip) {
    const uint8_t *e = lr_pose_e + (f << 2) + (f << 1);
    OAM_item_t *o = (OAM_item_t *)shadow_OAM + OAM_SPIG;
    uint8_t r, c, x, yy = y + 16, x0 = LR_SPIG_X + 8 + (flip ? 16 : 0), fl = flip ? S_FLIPX : 0, dx = flip ? -8 : 8;
    for (r = 0; r < 2; r++, yy += 16)
        for (x = x0, c = 0; c < 3; c++, x += dx, o++, e++) { o->y = yy; o->x = x; o->tile = otile(*e); o->prop = fl; }
}

static void partner(uint8_t x, uint8_t y, uint8_t f, uint8_t flip) {   // the show's performer, frame f: 4 entries
    const uint8_t *w = venue.show_tile[f];
    OAM_item_t *o = (OAM_item_t *)shadow_OAM + OAM_SQ;
    uint8_t pal = (is_cgb ? OBJPAL_DANCER : 0) | (flip ? S_FLIPX : 0), xa = x + (flip ? 16 : 8), xb = x + (flip ? 8 : 16);
    o->y = y + 16; o->x = xa; o->tile = OBJ_DANCER + w[0]; o->prop = pal; o++;
    o->y = y + 16; o->x = xb; o->tile = OBJ_DANCER + w[1]; o->prop = pal; o++;
    o->y = y + 32; o->x = xa; o->tile = OBJ_DANCER + w[2]; o->prop = pal; o++;
    o->y = y + 32; o->x = xb; o->tile = OBJ_DANCER + w[3]; o->prop = pal;
}

static int16_t vt(int16_t v, uint8_t t) {      // v x t (t < 64) without the library's multiply: |v| x t by its bits
    uint16_t p = 0, a = v < 0 ? -v : v;
    for (; t; t >>= 1, a <<= 1) if (t & 1) p += a;
    return v < 0 ? -(int16_t)p : (int16_t)p;
}

static void draw(void) {
    uint8_t k, f = P_CA, flip = 0, y = LR_SPIG_Y, sq = 0, t, shape;
    int16_t a, x, dy, m, tt;
    for (k = OAM_DROPS; k < OAM_SPIG; k++) shadow_OAM[k].y = 0;   // (the rest are all written below)
    // the marker
    m = lean_px();
    if (m > LR_FALL_PX) m = LR_FALL_PX; else if (m < -LR_FALL_PX) m = -LR_FALL_PX;
    ent(OAM_MARK, LR_MARK_X0 + m, LR_METER_Y, otile(LRO_MARKER), is_cgb ? LR_PAL_MARK : 0);
    // the Spigoteer
    if (S.st == LS_WATER) {
        f = S.fall_t < LR_SPLASH_LEN ? P_SPLASH : P_CLIMB;
        y = LR_WATER_Y;
        if (S.fall_t >= LR_HOP_AT) y = LR_WATER_Y - (uint8_t)((((uint16_t)(S.fall_t - LR_HOP_AT) * 7) * 171) >> 9);   // x 28 / 12 = x 7 / 3
    } else {
        a = m < 0 ? -m : m;
        f = a < 14 ? ((S.anim >> 3) & 1 ? P_CB : P_CA) : a < 40 ? P_L1 : P_L2;
        flip = S.lean > 0 && a >= 14;
    }
    spigoteer(y, f, flip);
    // the partner: on the log, startled by a fall, or tumbling into the river at the end
    if (S.top_t) {
        t = S.top_t > LR_TOPPLE ? LR_TOPPLE : S.top_t;
        partner(LR_SQ_X + (t >> 2), LR_SQ_Y + (uint8_t)((t * 7) >> 2), 3, 1);   // 4 t / 16, 28 t / 16
    } else {
        if (S.st == LS_WATER && S.fall_t < LR_SQ_REACT) sq = 3;
        partner(LR_SQ_X, LR_SQ_Y, sq, 0);
    }
    // the droplets of a burst: four, from the origin, shape by age
    if (S.drop_t) {
        t = S.drop_t;
        shape = t < 14 ? 0 : t < 28 ? 1 : 2;
        tt = (int16_t)(((uint16_t)t * t * 27) >> 8);   // the fall's share, the same for the four
        for (k = 0; k < 4; k++) {
            x = S.drop_x + 4 * (k - 1) - 2 + (vt(drop_vx[k], t) >> 7);
            dy = LR_DROP_Y + (vt(drop_vy[k], t) >> 7) + tt;
            if (x < 0 || x >= 150 || dy < 0 || dy >= 140) continue;
            f = (k & 1) ? (shape < 2 ? shape + 1 : 3) : shape;
            ent(OAM_DROPS + k, (uint8_t)x, (uint8_t)dy, otile(lr_drop_e[f]), is_cgb ? LR_PAL_DROP : 0);
        }
    }
    // the result window (48 px from BANNER_WY) is about to cover the river: mg.c hides the sprites that start inside it, so the
    // lower rows of a figure standing in the water would be left showing under its edge; they go with the rest
    if (mg_phase == MG_END && mg_t >= LR_HIDE_AT)
        for (k = OAM_DROPS; k < OAM_N; k++) if (shadow_OAM[k].y >= BANNER_WY + 64) shadow_OAM[k].y = 0;   // (the window ends at y 112: OAM y 128)
}

// ---- the streamed tiles and the HUD ----
// A drain runs ~40 cycles a byte from the start of VBlank and must end before line 0 (a copy that runs on into the picture is
// ignored by the hardware: the rest of the list is lost and, with it, the banner rows put back: the "black bars in the sky").
// The bark's 64 B, the ripples' 32 B and a banner row (20 B tiles + 20 B colours on CGB) together came to 136 B. A frame
// therefore takes what fits under LR_Q_MAX bytes (entry overhead counted as 2 B each, the framework's own entries included),
// and what does not waits for the next frame; nothing is queued while last frame's list still waits (vq_held: its sources
// would be overwritten under it).
#define LR_Q_MAX        76                      // ~12 DIV ticks of the ~17 a VBlank has (render.c: drain_ticks_max)
extern uint8_t vq_held;

static uint8_t q_room(uint8_t n, uint8_t entries) {   // 1: n more bytes in `entries` more entries fit this frame
    uint8_t i;
    uint16_t used = 0;
    if (vq_held || vq_count + entries > VQ_MAX_RAW) return 0;
    for (i = 0; i < vq_count; i++) used += vq[i].n + 2;
    return used + n + 2 * entries <= LR_Q_MAX;
}

static void tiles(void) {
    uint8_t f;
    f = (uint8_t)(S.roll >> 14);
    S.roll_f = f;
    S.rip_f = ((((uint16_t)S.anim * 205) >> 12) & 1);   // anim / 20 without the divide (exact for 0..255)
    if (S.roll_vis != S.roll_f && q_room(64, 1)) {
        memcpy(S.roll_buf, lr_roll + (uint16_t)S.roll_f * 64, 64);
        if (stream(LR_BG + LR_ROLL_AT, S.roll_buf, 64)) S.roll_vis = S.roll_f;
    }
    if (S.rip_vis != S.rip_f && q_room(32, 1)) {
        memcpy(S.rip_buf, lr_rip + (uint16_t)S.rip_f * 32, 32);
        if (stream(LR_BG + LR_RIP_AT, S.rip_buf, 32)) S.rip_vis = S.rip_f;
    }
}

// the banner rows: a row a frame (tiles and colours together), the forest back or the HUD band; a row is done when its copy
// is in the list (it waits, a frame at a time, until there is room)
static void band(void) {
    uint8_t r, k;
    for (r = 0; r < 2; r++) {
        if (S.band[r] == BAND_KEEP) continue;
        if (S.band[r] == BAND_FOREST) {
            if (!q_room(is_cgb ? 40 : 20, is_cgb ? 2 : 1)) return;
            for (k = 0; k < 20; k++) { S.brow[k] = LR_BG + lr_map[(1 + r) * 20 + k]; S.battr[k] = lr_attr[(1 + r) * 20 + k]; }
            if (is_cgb) vq_add(1, S.battr, 0, MG_TEXT_A + r, 20);
            vq_add(0, S.brow, 0, MG_TEXT_A + r, 20);
        } else if (is_cgb) {
            if (!q_room(20, 1)) return;
            vq_add(1, S.hud_attr, 0, MG_TEXT_A + r, 20);
        }
        S.band[r] = BAND_KEEP;
        return;
    }
}

// ---- the rules ----
static void burst(uint8_t x) { S.drop_t = 1; S.drop_x = x; }

static void fall(void) {
    S.st = LS_WATER; S.fall_t = 0;
    S.lean = 0; S.vel = 0;
    if (S.falls < 255) S.falls++;
    S.digit = TILE_GLYPH_0 + (S.falls > 9 ? 9 : S.falls);
    put(LR_HUD_DIGIT_COL, HUD_ROW, &S.digit, 1);
    burst(LR_SPLASH_X);
    SFX(SFX_BREAK);
}

static void on_log(uint8_t pressed) {
    int16_t px;
    if (pressed & J_LEFT) S.vel -= LR_ONE;
    if (pressed & J_RIGHT) S.vel += LR_ONE;
    S.vel += S.drift;
    S.vel -= S.vel >> 4;
    S.lean += S.vel;
    S.on++;
    if (++S.s60 == 60) { S.s60 = 0; mg_points(LR_PTS_SEC); }
    px = lean_px();
    if (px > LR_FALL_PX || px < -LR_FALL_PX) fall();
}

void lr_update(uint8_t pressed) BANKED {
    int16_t m;
    S.anim++;
    if (S.drop_t && ++S.drop_t > LR_DROPS) S.drop_t = 0;
    if (mg_phase == MG_PLAY || mg_phase == MG_END) {
        if (!S.started) { S.started = 1; S.band[0] = S.band[1] = BAND_FOREST; }
        if (S.st == LS_WATER) {                  // in the river: SPLASH, CLIMB, the hop
            if (++S.fall_t >= LR_FALL_LEN) { S.st = LS_RUN; S.lean = 0; S.vel = 0; SFX(SFX_LAUNCH); }
        }
    }
    if (mg_phase == MG_PLAY) {
        S.elapsed++;
        if (S.flip_in && !--S.flip_in) new_flip();
        ramps();
        m = mag();
        S.drift = ramped(m, S.dsr);
        S.roll -= (uint16_t)ramped(m, S.tell);   // the bark leads the push by 30 frames
        if (S.st == LS_RUN) on_log(pressed);
        if (mg_timer == 1) S.band[0] = BAND_HUD;     // TIME UP comes this frame (mg.c): its colours
    } else if (mg_phase == MG_END) {
        if (!S.ended) {
            S.ended = 1;
            if (S.st == LS_RUN) S.top_t = 1;         // up at time up: the partner topples in
            if (!S.falls) {
                mg_points(LR_PTS_CLEAN);
                S.band[1] = BAND_HUD;
                mg_say(MG_TEXT_B, "NO FALLS 1000");
                SFX(SFX_CATCH);
            }
        } else if (S.top_t) {
            if (S.top_t < 250 && ++S.top_t == LR_TOPPLE) burst(LR_TOPPLE_X);
        }
        if (mg_t == LR_BAND_OFF) S.band[0] = S.band[1] = BAND_FOREST;
    }
    tiles();
    band();
    draw();
}
