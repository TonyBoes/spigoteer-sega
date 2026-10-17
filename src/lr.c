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
//   fall (NO FALLS 1000 in the outro). Medal by seconds on the log (lr_medal): GOLD 40, SILVER 34, BRONZE 25. EASY / HARD change the roll's strength, the fish and
//   the medals' seconds (lr_tune). If he is up at time up the partner topples into the river (frame 3, X-flipped, a droplet burst).
// - Sounds (no new SFX): the creak SFX_SHAKE, the fall SFX_BREAK, the hop back SFX_LAUNCH, NO FALLS SFX_CATCH.
//
// D3 (the owner's playtest, 2026-10-15): "the game needs something more", "the sasquatch just stands there".
// - FISH: one at a time a fish leaps out of the river across the log (a flat 96 px arc, 48 frames, apex over its target), told 40
//   frames early by ripple rings at its launch point (SFX_FILL) and a splash ring where it lands. Aimed at the Spigoteer (from the
//   left or the right) or, one leap in four, at the Sasquatch (from the left). The Spigoteer HOPS over it with A, B or Up (36 frames in
//   the air, 12 of rest; hop_h[]): hit while he is under LR_CLEAR px, the fish's direction kicks his velocity by 3 px a frame
//   (about 45 px of lean of the 64: a big wobble that two or three quick taps against it cure; a fall when the push helps it) and he staggers 24 frames (no hop). A dodge scores LR_PTS_DODGE.
//   The leaps come every 360 frames at the start and every 210 at the end (the first after 360) (+ 0..31): LR_GAP0 - elapsed / 16. The fish has its own
//   xorshift (fseed): mg_rand is not called, so the flips' sequence is the one the tests model. A fall ends the fish in the air.
// - The SASQUATCH (the lodge show's 4 dance frames, no new art): he treads on the log (frames 0 2 0 3 by the bark's roll phase, a 1 px
//   bob, mirrored by the roll's direction, swaying up to 3 px with the push), windmills (1 2 1 3) while a flip is being told, hops a
//   fish aimed at him half the time, and otherwise is knocked into the river, swims LR_SQ_SWIM frames and climbs back. His falls are
//   flavour: nothing about the score or the medal depends on him.
//
// Screen (the approved mock-up): pines rows 1-4, far bank 5-6, river 7-17 with two ripple tiles, the log on rows 12-13
// (columns 3-16), the meter on row 16 (columns 2-17: marker x = 76 + lean). The log's four body tiles are one of four roll
// frames (a step of the bark = 64 B copied into fixed VRAM slots by a VBlank queue entry of its own), the ripples' two
// tiles one of two frames (32 B, every 20 frames); everything else is resident (tools/gen_lr.py: 40 BG tiles from
// MG_GAME_BG, the streamed slots at BG ids 128+). The HUD: score, the falls icon + digit at columns 9-10, T + seconds.
// CGB BG palettes 2 forest, 3 river, 5 log, 6 meter, 7 bank (4 stays the medal's); OBJ 0 the Spigoteer (the bartender's),
// 5 the Sasquatch (the show's), 1 droplets, 2 marker. DMG: BGP and OBP0 as the level's (every sprite on OBP0).
// OAM: 0 marker, 1-4 droplets, 5-10 the Spigoteer (3 x 2 entries of 8x16), 11-14 the Sasquatch, 15-16 the fish, 17-18 a ring.
// Worst line 9 (the splash): the fish and the rings are never up while the Spigoteer is in the water, and a fish that knocks the
// Sasquatch in ends there.
// OBJ tiles: the first 18 entries in ids 56-91 (the mugs' and crash frames: the level load puts them back), the rest from
// the first even id above the BG tiles (166..), skipping the HUD hourglass at BG 220 (the last three entries from 222).
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
#define LR_OBJ_HI_A     ((MG_HOURGLASS - LR_OBJ_HI) / 2)   // the first run of those entries ends below the HUD hourglass (BG 220 is OBJ 220's memory)
#define LR_OBJ_HI_B     (MG_HOURGLASS + 2)                 // the rest start past it (hourglass 220, 221 left empty)
typedef char lr_fits[(LR_BG + LR_ROLL_AT >= 128 && LR_BG + LR_BG_TILES <= 256 && OBJ_MUG + 2 * LR_SLOT_ENTRIES <= OBJ_COIN
                      && LR_OBJ_HI_A > 0 && LR_OBJ_HI_A < LR_OBJ_HI_N && LR_OBJ_HI_B + 2 * (LR_OBJ_HI_N - LR_OBJ_HI_A) <= OBJ_POUR && LR_ENTRIES > LR_SLOT_ENTRIES) ? 1 : -1];
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
// the fish and the hops (frames, px)
#define LR_WARN          40                     // frames of ripples before a leap
#define LR_FLY           48                     // frames of the leap (2 px a frame: 96 px)
#define LR_LAND          12                     // frames of the landing ring
#define LR_HALF          48                     // half the leap's span: the launch point is this far from the target's x
#define LR_HIT_W         10                     // a fish is on its target while |fish x - target x| < this
#define LR_CLEAR         14                     // a hop this high (px) clears a fish
#define LR_KICK         262144L                 // a hit's velocity kick, 4 px a frame (about 64 px of lean unless he leans back: the edge is 64)
#define LR_STUN          24
#define LR_LOCK          12                     // the first frames of the stagger ignore Left / Right (he cannot lean back yet)
#define LR_HOP_LEN       36                     // frames in the air
#define LR_HOP_END       48                     // ... then 12 of rest before the next hop
#define LR_FISH_FIRST   360                     // frames to the first leap's ripples
#define LR_GAP0         360                     // the gap between leaps at the start (6 s); elapsed / 16 shorter (210 = 3.5 s at the end)
// The tuning per difficulty (indexed by MG_DIFF: NORMAL, HARD, EASY; STORY and ARCADE play NORMAL), TUNING.md: the drift's start (the ramp's rise is
// the same), the frames to the first fish and the gap between fish at the start, the frames between the roll's flips (min + 0..range - 1) and the
// medals (seconds on the log).
static const struct lr_tune lr_tune[MG_DIFFS] = {
    { LR_DRIFT0, LR_FISH_FIRST, LR_GAP0, LR_FLIP_MIN, LR_FLIP_RANGE, LR_GOLD, LR_SILVER, LR_BRONZE },
    { 2500, 280, 220, 70, 91, 40, 30, 22 },             // HARD: a stronger roll (0.038; the ramp's m stays under 3856), flips every 70 - 160 frames, fish sooner and more often
    { 1100, 480, 480, 160, 121, 40, 36, 28 },             // EASY: a gentler roll (0.017), flips every 160 - 280, fish later and further apart
};
#define LRT             (S.tn)
#define TUNE_LOAD()     { const uint8_t *tl_s = (const uint8_t *)&lr_tune[MG_DIFF]; uint8_t *tl_d = (uint8_t *)&S.tn, tl_k; for (tl_k = 0; tl_k < sizeof(S.tn); tl_k++) tl_d[tl_k] = tl_s[tl_k]; }

#define LR_FISH_LAST     90                     // no ripples with fewer frames than this left
#define LR_PTS_DODGE    150
#define LR_FISH_BASE_Y  118                     // the water line the arc starts on (the fish's centre)
#define LR_SQ_HOP_K      12                     // the leap's frame the Sasquatch starts his hop
#define LR_SQ_SWIM      150                     // frames in the river after a hit (top_t counts), then 12 of climbing
#define LR_SQ_UP_LEN     12
#define LR_SPIG_CX      104                     // the Spigoteer's and the Sasquatch's centres
#define LR_SQ_CX         52
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
#define LR_HUD_ICON_COL  10
#define LR_HUD_DIGIT_COL 11
#define LR_PAL_DROP       1                     // CGB OBJ palettes
#define LR_PAL_MARK       2
#define LR_PAL_FISH       3
// OAM
#define OAM_MARK         0
#define OAM_DROPS        1
#define OAM_SPIG         5
#define OAM_SQ          11
#define OAM_FISH        15
#define OAM_RING        17
#define OAM_N           19
// the shifts that stand in for divides below hold for exactly these numbers
typedef char lr_divs[(LR_RAMP_FRAMES == 30 && LR_RIPPLE_EVERY == 20 && LR_TOPPLE == 16 && LR_WATER_Y - LR_SQ_Y == 28
                      && LR_WATER_Y - LR_SPIG_Y == 28 && LR_FALL_LEN - LR_HOP_AT == 12) ? 1 : -1];
enum { LS_RUN, LS_WATER, LS_OVER };             // S.st: on the log; in the water; the outro
enum { SQ_LOG, SQ_SWIM, SQ_END };               // S.sq_st: standing on the log; knocked in by a fish; toppled by the outro
enum { BAND_KEEP, BAND_FOREST, BAND_HUD };      // S.band[]: a banner row's pending change
enum { P_CA, P_CB, P_L1, P_L2, P_SPLASH, P_CLIMB };   // poses (tools/gen_lr.py POSES)

// a droplet's launch velocities, 1/128 px a frame (the mock-up's, x 0.9)
// the Spigoteer's / Sasquatch's hop height by frame (t (36 - t) / 9) and the fish's arc by frame (28 x 4 k (48 - k) / 48^2): tables, no multiply
static const uint8_t hop_h[LR_HOP_LEN + 1] = { 0, 3, 7, 11, 14, 17, 20, 22, 24, 27, 28, 30, 32, 33, 34, 35, 35, 35, 36, 35, 35, 35, 34, 33, 32, 30,
                                               28, 27, 24, 22, 20, 17, 14, 11, 7, 3, 0 };
static const uint8_t fish_arc[LR_FLY] = { 0, 2, 4, 7, 9, 10, 12, 14, 16, 17, 18, 20, 21, 22, 23, 24, 25, 26, 26, 27, 27, 28, 28, 28, 28, 28, 28, 28, 27, 27,
                                          26, 26, 25, 24, 23, 22, 21, 20, 18, 17, 16, 14, 12, 10, 9, 7, 4, 2 };
static const uint8_t tread_f[4] = { 0, 2, 0, 3 }, flail_f[4] = { 1, 2, 1, 3 };   // the Sasquatch's dance frames: treading, windmilling
static const uint8_t ring_seq[8] = { 0, 1, 2, 0, 1, 2, 1, 2 };
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
    if (qv_cost <= VQ_DRAIN_BUDGET) qv_cost += n + 3;
    e->n = n; e->bank = 0; e->src = src; e->dst = tile_addr(id);
    return 1;
}

static uint8_t otile(uint8_t e) {               // an OBJ entry's (even) tile number
    if (e < LR_SLOT_ENTRIES) return OBJ_MUG + 2 * e;
    e -= LR_SLOT_ENTRIES;
    return e < LR_OBJ_HI_A ? LR_OBJ_HI + 2 * e : LR_OBJ_HI_B + 2 * (e - LR_OBJ_HI_A);
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
    return LRT.drift0 + ((uint16_t)hi << 5) + ((uint16_t)hi << 1) + hi + ((((uint16_t)lo << 5) + ((uint16_t)lo << 1) + lo) >> 6);
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
    S.flip_in = LRT.flip_min + mg_rand() % LRT.flip_range;
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
    TUNE_LOAD();
    set_bkg_data(LR_BG, LR_BG_TILES, lr_bg_tiles);
    set_sprite_data(OBJ_MUG, 2 * LR_SLOT_ENTRIES, lr_obj_tiles);
    set_sprite_data((uint8_t)LR_OBJ_HI, (uint8_t)(2 * LR_OBJ_HI_A), lr_obj_tiles + (uint16_t)2 * LR_SLOT_ENTRIES * 16);
    set_sprite_data((uint8_t)LR_OBJ_HI_B, (uint8_t)(2 * (LR_OBJ_HI_N - LR_OBJ_HI_A)), lr_obj_tiles + (uint16_t)2 * (LR_SLOT_ENTRIES + LR_OBJ_HI_A) * 16);
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
        set_sprite_palette(LR_PAL_FISH, 1, lr_pal_obj + 8);
    }
    for (k = 0; k < 20; k++) S.hud_attr[k] = BGPAL_HUD;
    // the HUD: the falls icon and its digit at columns 10-11 (the lives stay at 7-8)
    row_buf[0] = LR_BG + LRB_HUD; row_buf[1] = TILE_GLYPH_0;
    vram_put(LR_HUD_ICON_COL, HUD_ROW, row_buf, 2);
    // the state
    S.lean = 0; S.vel = 0; S.drift = 0; S.on = 0; S.elapsed = 0; S.roll = 0; S.st = LS_RUN; S.falls = 0; S.fall_t = 0;
    S.s60 = 0; S.roll_f = 0; S.roll_vis = 0; S.rip_f = 0; S.rip_vis = 0; S.anim = 0; S.started = 0; S.ended = 0;
    S.top_t = 0; S.drop_t = 0; S.drop_x = 0; S.band[0] = S.band[1] = BAND_KEEP; S.digit = TILE_GLYPH_0;
    S.fish_in = LRT.fish_first; { uint16_t v = mg_seed ^ 0x5A5A; S.fseed = v ? v : 0xACE1; }   // (mg_seed read, not advanced)
    S.fish_t = 0; S.fish_done = 0; S.hop_t = 0; S.stun = 0; S.dodged = S.hits = 0; S.sq_st = SQ_LOG; S.sq_hop = 0; S.sq_dodge = 0;
    S.tsgn = (mg_rand() & 1) ? 1 : -1;
    S.tell = S.dsr = S.tsgn * LR_RAMP_FRAMES; S.fdelay = 0;
    S.flip_in = LRT.flip_min + mg_rand() % LRT.flip_range;
    S.drift = ramped(mag(), S.dsr);
    mg_timer = LR_TIME_S * 60;
    lr_update(0);                                // the sprites (the update draws them; no play before MG_PLAY)
}

uint8_t lr_medal(void) BANKED {
    uint8_t s = S.on / 60;
    return s >= LRT.gold ? MEDAL_GOLD : s >= LRT.silver ? MEDAL_SILVER : s >= LRT.bronze ? MEDAL_BRONZE : MEDAL_NONE;
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

static void pair(uint8_t i, uint8_t cx, uint8_t y, const uint8_t *e, uint8_t flip, uint8_t pal) {   // two 8x16 entries side by side, centred on screen x cx
    OAM_item_t *o = shadow_OAM + i;
    uint8_t prop = (is_cgb ? pal : 0) | (flip ? S_FLIPX : 0);
    o->y = y + 16; o->x = cx; o->tile = otile(e[flip]); o->prop = prop; o++;
    o->y = y + 16; o->x = cx + 8; o->tile = otile(e[1 - flip]); o->prop = prop;
}

static uint8_t spig_h(void) { return S.hop_t && S.hop_t <= LR_HOP_LEN ? hop_h[S.hop_t] : 0; }
static uint8_t sq_h(void) { return S.sq_hop && S.sq_hop <= LR_HOP_LEN ? hop_h[S.sq_hop] : 0; }

static void hide(uint8_t i) { shadow_OAM[i].y = 0; shadow_OAM[i + 1].y = 0; }

static void draw_fish(void) {                   // the fish (OAM 15-16) and a ring (17-18)
    uint8_t k, rf;
    int16_t fx;
    hide(OAM_FISH); hide(OAM_RING);
    if (!S.fish_t || S.st == LS_WATER) return;
    if (S.fish_t <= LR_WARN) {                  // the ripples at the launch point, repeating
        pair(OAM_RING, S.fish_x0, LR_FISH_BASE_Y - 4, lr_ring_e + (ring_seq[(S.fish_t >> 2) & 7] << 1), 0, LR_PAL_DROP);
    } else if (S.fish_t <= LR_WARN + LR_FLY) {
        k = S.fish_t - LR_WARN - 1;
        fx = S.fish_dir > 0 ? S.fish_x0 + (k << 1) : S.fish_x0 - (k << 1);
        rf = k < 16 ? 0 : k < 32 ? 1 : 2;
        pair(OAM_FISH, (uint8_t)fx, LR_FISH_BASE_Y - fish_arc[k] - 8, lr_fish_e + (rf << 1), S.fish_dir > 0, LR_PAL_FISH);
    } else {                                    // the landing ring grows
        k = S.fish_t - (LR_WARN + LR_FLY);
        fx = S.fish_dir > 0 ? S.fish_x0 + 2 * LR_FLY : S.fish_x0 - 2 * LR_FLY;
        pair(OAM_RING, (uint8_t)fx, LR_FISH_BASE_Y - 4, lr_ring_e + ((k < 5 ? 0 : k < 9 ? 1 : 2) << 1), 0, LR_PAL_DROP);
    }
}

static int16_t vt(int16_t v, uint8_t t) {      // v x t (t < 64) without the library's multiply: |v| x t by its bits
    uint16_t p = 0, a = v < 0 ? -v : v;
    for (; t; t >>= 1, a <<= 1) if (t & 1) p += a;
    return v < 0 ? -(int16_t)p : (int16_t)p;
}

static void draw(void) {
    uint8_t k, f = P_CA, flip = 0, y = LR_SPIG_Y, sq = 0, t, shape, h, sx, sy, sflip;
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
        h = spig_h();
        if (h) { f = P_CA; y = LR_SPIG_Y - h; }                      // a hop: arms out
        if (S.stun) { f = P_L2; flip = S.hit_dir > 0; }              // a fish hit him: the hard lean, away from where it came
    }
    spigoteer(y, f, flip);
    // the partner: on the log, startled by a fall, or tumbling into the river at the end
    if (S.top_t) {
        t = S.top_t > LR_TOPPLE ? LR_TOPPLE : S.top_t;
        sx = LR_SQ_X + (t >> 2); sy = LR_SQ_Y + (uint8_t)((t * 7) >> 2);   // 4 t / 16, 28 t / 16
        if (S.sq_st == SQ_SWIM && S.top_t > LR_SQ_SWIM) {            // climbing back out of the river
            t = S.top_t - LR_SQ_SWIM;
            sx = LR_SQ_X + ((LR_SQ_UP_LEN - t) >> 2); sy = LR_WATER_Y - (uint8_t)((((uint16_t)t * 7) * 171) >> 9);   // x 28 / 12
        }
        partner(sx, sy, 3, 1);
    } else {
        sx = LR_SQ_X; sy = LR_SQ_Y;
        if (S.st == LS_WATER && S.fall_t < LR_SQ_REACT) sq = 3;
        else if (S.stun || (S.fish_t && S.fish_t <= LR_WARN + 30 && S.fish_tgt && !S.sq_hop)) sq = 3;   // startled: he was hit, or a fish is coming for him
        else if (S.sq_hop) { sq = 1; sy -= sq_h(); }                 // his hop: arms up
        else {
            a = S.tell < 0 ? -S.tell : S.tell;
            if (a < 12) sq = flail_f[(S.anim >> 2) & 3];             // the bark is stopping to turn: he windmills
            else {                                                   // treading, a step to each of the bark's phases
                t = (uint8_t)(S.roll >> 14);
                sq = tread_f[t];
                sy += t & 1;
            }
        }
        a = S.dsr < 0 ? -S.dsr : S.dsr;                              // he sways with the push, up to 3 px
        sx += S.dsr < 0 ? -(a >> 3) : (a >> 3);
        sflip = S.tell < 0;
        partner(sx, sy, sq, sflip);
    }
    draw_fish();
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
        if (stream((uint8_t)(LR_BG + LR_ROLL_AT), S.roll_buf, 64)) S.roll_vis = S.roll_f;
    }
    if (S.rip_vis != S.rip_f && q_room(32, 1)) {
        memcpy(S.rip_buf, lr_rip + (uint16_t)S.rip_f * 32, 32);
        if (stream((uint8_t)(LR_BG + LR_RIP_AT), S.rip_buf, 32)) S.rip_vis = S.rip_f;
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

static uint8_t frand(void) {                    // the fish's xorshift (mg_rand's, on its own seed)
    uint16_t v = S.fseed;
    v ^= v << 7; v ^= v >> 9; v ^= v << 8;
    S.fseed = v;
    return (uint8_t)v;
}

static void fish_tell(void) {                   // the ripples begin; the leap's side and target are chosen now
    uint8_t r = frand();
    S.fish_tgt = (r & 3) == 0 && S.sq_st == SQ_LOG;          // one in four is the Sasquatch's, never while he is in the river
    S.fish_dir = S.fish_tgt || (r & 4) ? 1 : -1;
    S.fish_x0 = S.fish_tgt ? LR_SQ_CX - LR_HALF : S.fish_dir > 0 ? LR_SPIG_CX - LR_HALF : LR_SPIG_CX + LR_HALF;
    S.sq_dodge = (r & 8) != 0;
    S.fish_t = 1; S.fish_done = 0;
    SFX(SFX_FILL);
}

static void sq_fall(void) {                     // a fish knocks the Sasquatch into the river
    S.sq_st = SQ_SWIM; S.top_t = 1; S.sq_hop = 0;
    SFX(SFX_BREAK);
}

// One frame of the fish (a play frame): the schedule, the leap's frames, and the hit test while it is over its target.
static void fish_step(void) {
    uint8_t k, tx;
    int16_t fx, d;
    if (S.fish_in) S.fish_in--;
    if (!S.fish_t) {
        if (!S.fish_in && S.st == LS_RUN && mg_timer > LR_FISH_LAST) {
            fish_tell();
            S.fish_in = LRT.gap0 - (S.elapsed >> 4) + (frand() & 31);
        }
        return;
    }
    if (++S.fish_t > LR_WARN + LR_FLY + LR_LAND) { S.fish_t = 0; return; }
    if (S.fish_t == LR_WARN + 1) SFX(SFX_WHOOSH);
    if (S.fish_t <= LR_WARN || S.fish_t > LR_WARN + LR_FLY || S.fish_done) return;
    k = S.fish_t - LR_WARN - 1;
    if (S.fish_tgt && k == LR_SQ_HOP_K && S.sq_dodge) S.sq_hop = 1;
    tx = S.fish_tgt ? LR_SQ_CX : LR_SPIG_CX;
    fx = S.fish_dir > 0 ? S.fish_x0 + (k << 1) : S.fish_x0 - (k << 1);
    d = S.fish_dir > 0 ? fx - tx : tx - fx;                  // < 0 before the target, > 0 past it
    if (d <= -LR_HIT_W) return;
    if (d < LR_HIT_W) {                                      // over it: a hop must be high enough
        if (S.fish_tgt) {
            if (sq_h() >= LR_CLEAR) return;
            S.fish_done = 1;
            sq_fall();
            S.fish_t = 0;                                    // stopped by him
        } else {
            if (spig_h() >= LR_CLEAR) return;
            S.fish_done = 1; S.hits++;
            if (S.fish_dir > 0) S.vel = (S.vel > 0 ? S.vel : 0) + LR_KICK;   // always the fish's way: a lean the other way is cancelled first
            else S.vel = (S.vel < 0 ? S.vel : 0) - LR_KICK;
            S.stun = LR_STUN; S.hit_dir = S.fish_dir;
            SFX(SFX_BREAK);
        }
        return;
    }
    S.fish_done = 1;                                         // past it with no hit
    if (!S.fish_tgt) {
        if (S.dodged < 255) S.dodged++;
        mg_points(LR_PTS_DODGE);
        SFX(SFX_COIN);
    }
}

static void fall(void) {
    S.st = LS_WATER; S.fall_t = 0;
    S.lean = 0; S.vel = 0;
    S.fish_t = 0; S.hop_t = 0; S.stun = 0;                   // the fish in the air dives; no hop in the river
    if (S.falls < 255) S.falls++;
    S.digit = TILE_GLYPH_0 + (S.falls > 9 ? 9 : S.falls);
    put(LR_HUD_DIGIT_COL, HUD_ROW, &S.digit, 1);
    burst(LR_SPLASH_X);
    SFX(SFX_BREAK);
}

static void on_log(uint8_t pressed) {
    int16_t px;
    if (S.stun <= LR_STUN - LR_LOCK) {
        if (pressed & J_LEFT) S.vel -= LR_ONE;
        if (pressed & J_RIGHT) S.vel += LR_ONE;
    }
    if (!S.stun) S.vel += S.drift;                // (the roll's push waits out the stagger: the kick wins)
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
    if (S.sq_hop && ++S.sq_hop > LR_HOP_LEN) S.sq_hop = 0;
    if (mg_phase == MG_PLAY || mg_phase == MG_END) {
        if (S.sq_st == SQ_SWIM) {                // knocked in by a fish: the topple's splash, the swim, the climb back
            if (++S.top_t == LR_TOPPLE) burst(LR_TOPPLE_X);
            if (S.top_t >= LR_SQ_SWIM + LR_SQ_UP_LEN) { S.top_t = 0; S.sq_st = SQ_LOG; }
        }
        if (!S.started) { S.started = 1; S.band[0] = S.band[1] = BAND_FOREST; }
        if (S.st == LS_WATER) {                  // in the river: SPLASH, CLIMB, the hop
            if (++S.fall_t >= LR_FALL_LEN) { S.st = LS_RUN; S.lean = 0; S.vel = 0; SFX(SFX_LAUNCH); }
        }
    }
    if (mg_phase == MG_PLAY) {
        S.elapsed++;
        if (S.stun) S.stun--;
        if (S.hop_t) { if (++S.hop_t > LR_HOP_END) S.hop_t = 0; }
        else if ((pressed & (J_A | J_B | J_UP)) && S.st == LS_RUN && !S.stun) { S.hop_t = 1; SFX(SFX_LAUNCH); }
        if (S.flip_in && !--S.flip_in) new_flip();
        ramps();
        m = mag();
        S.drift = ramped(m, S.dsr);
        S.roll -= (uint16_t)ramped(m, S.tell);   // the bark leads the push by 30 frames
        fish_step();
        if (S.st == LS_RUN) on_log(pressed);
        if (mg_timer == 1) S.band[0] = BAND_HUD;     // TIME UP comes this frame (mg.c): its colours
    } else if (mg_phase == MG_END) {
        if (!S.ended) {
            S.ended = 1;
            S.fish_t = 0;                            // (no fish in the outro)
            if (S.st == LS_RUN && S.sq_st == SQ_LOG) { S.top_t = 1; S.sq_st = SQ_END; }   // up at time up: the partner topples in
            if (!S.falls) {
                mg_points(LR_PTS_CLEAN);
                S.band[1] = BAND_HUD;
                mg_say(MG_TEXT_B, "NO FALLS 1000");
                SFX(SFX_CATCH);
            }
        } else if (S.top_t && S.sq_st == SQ_END) {
            if (S.top_t < 250 && ++S.top_t == LR_TOPPLE) burst(LR_TOPPLE_X);
        }
        if (mg_t == LR_BAND_OFF) S.band[0] = S.band[1] = BAND_FOREST;
    }
    tiles();
    band();
    draw();
}
