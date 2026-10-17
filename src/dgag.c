// DREGS'S LATE-ARRIVAL GAGS (G17; docs/story.md running gag 1, "Dregs is always one scene late"; design: docs/story.md "Dregs's exits").
// In every POST scene the narrator page right after Dregs's own page says how the venue threw him out. This file plays it: a short
// OBJ-sprite gag over the venue's stage and bar 0 (the bars have no doors on screen: he goes off the LEFT edge, a door just out of
// view, and the dust puff and the crash sound sell it), while the narrator's text types. src/story.c calls three things:
//   dg_load(st, v)            scene start (LCD off), POST scenes only: the gag's tiles and palettes for venue v, no gag running
//   dg_page(st, scene, prev, spk)  every page turn: the running gag is cleaned up, a new one starts when this page is its page
//   dg_frame(st)              every frame of a scene while st[4] is 1 (the gag runs): draws; A does not turn the page meanwhile
// All state is `st`, story.c's win_rows (the goal banner's 100 bytes, unused in a scene): no WRAM of its own.
//   st[0] frame of the gag (a gag is at most 255 frames), st[1] next OAM entry while drawing, st[2] venue, st[3] phase,
//   st[4] 0 idle, 1 running, 2 finished but still on screen (Dregs standing: the punks' chord page waits for the blast page).
// Phases: 0 the exit; 1 the punks' second page (blast); 2 the space lounge's "came down" page (beam down).
// Every gag is a closed-form function of its frame number. The common opening (OPEN = 48 frames): Dregs dashes in from the right (whoosh), reaches for
// the prize (arm out, one hop), then the venue's way out; the common ending: dust and a crash at the left edge.
// OAM 20-39 (the Spigoteer 0-3, Sadie's accent 4..): at most 10 sprites a line (checked in tests/test_dregs_gag.py).
// OBJ tiles 56-87 Dregs's set (+ the dust), 88-91 and 98-127 the venue's props and patron poses (OBJ 92-95 are the coin, loaded once
// at boot; 96-97 hold Sadie's accent in her scenes): all loaded here, the next level load / scene puts everything else back.
// Palettes: CGB OBJ 1 Dregs, 2 the venue's props, 5 / 6 / 7 the patron variants (and the monkeys / the beam); DMG OBP1 0xE4.
#pragma bank 255
#include <gb/gb.h>
#include <gb/cgb.h>
#include <stdint.h>

#include "game.h"
#include "music.h"
#include "palettes.h"
#include "story.h"
#include "dgag_art.h"

BANKREF_EXTERN(patron_tiles_cowboys)
BANKREF_EXTERN(patron_tiles_sports)
extern const uint8_t patron_tiles_cowboys[], patron_tiles_sports[];
void spr_data_far(uint8_t first, uint8_t n, const uint8_t *d, uint8_t bank);   // src/main.c (ROM0)

#define SPK_SPIGOTEER 0             // speaker indices (tools/gen_story.py SPEAKERS; SPK_NARRATOR is in story.h)
#define SPK_DREGS 1
#define OAM0     20
#define T_A      56
#define T_DUST   (T_A + 0)          // 3 frames x one 8x16 entry
#define T_BALL   (T_A + 6)          // 16x16: 2 entries
#define T_LY     (T_A + 10)         // 24x16: 3 entries
#define T_UP     (T_A + 16)         // 16x24 in the Spigoteer's layout: 8 tiles
#define T_REACH  (T_A + 24)
#define T_B      88                 // 88-91: the venue's first prop
#define T_P      98                 // patron poses: 6 tiles a variant
#define T_X      116                // 116-127: a second prop
typedef char dg_set_a_fits[(DG_A_TILES == 32 && T_A + DG_A_TILES == T_B) ? 1 : -1];

#define XD       96                 // where Dregs stands to grab (his left edge); bar 0's lane: top y 40, feet on y 64
#define LANE     40
#define RGB15(r, g, b) ((uint16_t)((r) | ((g) << 5) | ((b) << 10)))
#define PD       (is_cgb ? 1 : S_PALETTE)           // Dregs
#define PP       (is_cgb ? 2 : S_PALETTE)           // the venue's props

static const uint16_t pal_dregs[4] = { 0, RGB15(30, 27, 20), RGB15(22, 20, 23), RGB15(4, 3, 5) };   // as the Pour-Off's

// ---- drawing --------------------------------------------------------------------------------------------------------------------
static void ent(uint8_t *st, int16_t x, int16_t y, uint8_t tile, uint8_t prop) {   // one 8x16 entry; off the screen it is hidden
    OAM_item_t *o;
    uint8_t n = st[1];
    if (n >= 40) return;
    st[1] = n + 1;
    o = shadow_OAM + n;
    if (x < -7 || x > 159 || y < -15 || y > 143) { o->y = 0; return; }
    o->y = (uint8_t)(y + 16); o->x = (uint8_t)(x + 8); o->tile = tile; o->prop = prop;
}

// two 8x16 entries side by side (tiles t, t + 2); fl bit 0 mirrors it left-right, bit 1 top-bottom
static void two(uint8_t *st, int16_t x, int16_t y, uint8_t t, uint8_t prop, uint8_t fl) {
    uint8_t a = t, b = t + 2, p = prop | ((fl & 1) ? S_FLIPX : 0) | ((fl & 2) ? S_FLIPY : 0);
    if (fl & 1) { a = b; b = t; }
    ent(st, x, y, a, p); ent(st, x + 8, y, b, p);
}

static void dregs(uint8_t *st, int16_t x, int16_t y, uint8_t reach, uint8_t fx) {   // upright, 16x24
    uint8_t t = T_UP + (reach ? 8 : 0);
    two(st, x, y, t, PD, fx); two(st, x, y + 16, t + 4, PD, fx);
}

static void lying(uint8_t *st, int16_t x, int16_t y, uint8_t fx) {                  // flat, 24x16, head left
    uint8_t p = PD | (fx ? S_FLIPX : 0);
    ent(st, x, y, T_LY + (fx ? 4 : 0), p); ent(st, x + 8, y, T_LY + 2, p); ent(st, x + 16, y, T_LY + (fx ? 0 : 4), p);
}

static void ball(uint8_t *st, int16_t x, int16_t y, uint8_t t) {                    // a tumbling ball: flipped four ways, 4 frames each
    two(st, x, y, T_BALL, PD, (t >> 2) & 3);
}

// ---- the common opening: the dash in and the reach. 1 while it plays (t < OPEN) -------------------------------------------------------
#define OPEN     48
static uint8_t opening(uint8_t *st, uint8_t t) {
    int16_t x = XD, y = LANE;
    if (t >= OPEN) return 0;
    if (t == 0) SFX(SFX_WHOOSH);
    if (t < 20) { x = XD + (20 - t) * 4; y = LANE + ((t >> 1) & 1); }     // the dash, bobbing
    else if (t >= 28 && t < 34) y = LANE - 4;                             // one hop as he grabs
    else if (t >= 34) x += (t >> 1) & 1;                                   // then he fidgets, greedy
    dregs(st, x, y, t >= 22, 0);
    return 1;
}


// ---- more pieces ----------------------------------------------------------------------------------------------------------------------
// The venue's patrons are its shift-0 poses (facing right in the art): flipped, they face Dregs at the left.
#define PPAT(v)  (is_cgb ? 5 + (v) : S_PALETTE)
#define PAT_Y    40                 // a patron's play depth: the two wall rows above the counter row (y 56): behind the bar, never over it
static void pat(uint8_t *st, int16_t x, int16_t y, uint8_t v) { two(st, x, y, T_P + v * 6, PPAT(v), 1); }

static void puff(uint8_t *st, int16_t x, int16_t y, uint8_t f) { ent(st, x, y, T_DUST + (f % 3) * 2, 0); }   // a dust picture anywhere

// the end at the left edge: te frames after he went off it (negative: not yet). The crash on the first, then the puff at height y.
static uint8_t edge(uint8_t *st, int16_t te, int16_t y) {
    if (te < 0) return 1;
    if (te == 0) SFX(SFX_BREAK);
    if (te < 12) { puff(st, 0, y, te >> 2); puff(st, 6, y + 8, te >> 2); }
    return te < 16;
}

static const int8_t orb[16] = { 18, 17, 13, 7, 0, -7, -13, -17, -18, -17, -13, -7, 0, 7, 13, 17 };   // 18 cos(k 22.5 deg)

static void arc(uint8_t *st, int16_t x, int16_t y, uint8_t fx) { ent(st, x, y, T_B, PP | (fx ? S_FLIPX : 0)); }   // a sound arc, 8x16

// ---- the gags: 1 while running (2: finished, left on screen) ---------------------------------------------------------------------------
// 1 SALOON. Two cowboys run in behind him, step up, hoist him and lay him on the counter; he slides down the bar faster and faster
// and out at the left end while they cheer.
static uint8_t gag_saloon(uint8_t *st, uint8_t t) {
    int16_t u = (int16_t)t - OPEN, a = t < 20 ? (20 - t) * 4 : 0, v, ca, y;
    ca = 106 + a - (u > 0 ? (u < 8 ? u : 8) : 0);
    y = PAT_Y - (u >= 16 ? ((t >> 2) & 1) * 2 : 0);
    if (opening(st, t)) { }
    else if (u < 16) dregs(st, XD, LANE - 6 + ((u >> 1) & 1) * 2, 1, 0);          // hoisted, kicking
    else {
        v = u - 16;
        if (v < 28) lying(st, XD - (v * v) / 8 - v, 46, 0);                        // sliding down the bar
        else edge(st, v - 28, 42);
    }
    pat(st, ca, y, 0); pat(st, ca + 16, y, 1);
    return u < 94;
}

// 2 STADIUM. Three fans run in behind him, get under him, hoist him up flat and crowd-surf him left, off the edge.
static uint8_t gag_stadium(uint8_t *st, uint8_t t) {
    int16_t u = (int16_t)t - OPEN, a = t < 20 ? (20 - t) * 4 : 0, sh = u < 16 ? 0 : (uint16_t)((u - 16) * 3) / 2, bx;
    uint8_t i;
    if (opening(st, t)) { }
    else if (u < 10) dregs(st, XD, LANE, 1, 0);
    else if (u < 95) lying(st, XD - 2 - sh, 26 + ((t >> 2) & 1) * 2, (t >> 4) & 1);
    else edge(st, u - 95, 42);
    for (i = 0; i < 3; i++) {
        bx = XD + 20 + 14 * i + a;
        if (u > 0) bx = XD + 20 + 14 * i - (u < 15 ? u * 2 : 30) - sh;
        pat(st, bx, PAT_Y - (((t >> 3) + i) & 1), i);
    }
    return u < 115;
}

// 3 LUMBER. He freezes, spots the Sasquatch, and bolts so fast he leaves his boots standing where he was; a dust trail behind him.
// The boots stay a beat, then pop away.
static uint8_t gag_lumber(uint8_t *st, uint8_t t) {
    int16_t u = (int16_t)t - OPEN, w = u - 20, x;
    if (opening(st, t)) { }
    else if (w < 0) dregs(st, XD + ((u >> 1) & 1) * 2 - 1, LANE, 1, 0);           // frozen, shaking
    else {
        x = XD - w * 5;
        if (x > -17) { dregs(st, x, LANE + ((w >> 1) & 1), 0, 0); puff(st, x + 14, 50, w >> 2); }
        else edge(st, w - 23, 42);
    }
    if (w >= 1 && w < 63) { ent(st, XD + 2, 56, T_B, PD); ent(st, XD + 10, 56, T_B, PD); }
    else if (w >= 63 && w < 75) puff(st, XD + 6, 48, (w - 63) >> 2);
    return w < 75;
}

// 4 BISTRO. Three plates start orbiting him, he spins (mirrored every 3 frames), then the plates carry him off left, still spinning.
static uint8_t gag_bistro(uint8_t *st, uint8_t t) {
    int16_t u = (int16_t)t - OPEN, x = XD, k;
    uint8_t i;
    if (u >= 60) x = XD - (u - 60) * 4;
    if (opening(st, t)) { }
    else if (x > -17) dregs(st, x, LANE, (u >> 2) & 1, (u / 3) & 1);
    else edge(st, u - 89, 42);
    if (u >= 0 && x > -30)
        for (i = 0; i < 3; i++) {
            k = (u >> 1) + i * 5;
            ent(st, x + 4 + orb[k & 15], LANE + 4 + orb[(k + 12) & 15] / 2, T_B, PP);
        }
    return u < 108;
}

// 5 IGLOO. He skids on the ice (whoa-whoa), falls flat and slides the bar flat out to its left end, the tunnel mouth, then rolls
// downhill out of it as a ball: down and left, a snow puff at the lip.
static uint8_t gag_igloo(uint8_t *st, uint8_t t) {
    int16_t u = (int16_t)t - OPEN, v = u - 16, w = v - 20, x;
    if (opening(st, t)) { }
    else if (u < 16) dregs(st, XD + (((u >> 1) & 1) ? 3 : -3), LANE, (u >> 2) & 1, (u >> 3) & 1);
    else if (w < 0) lying(st, XD - (v * v) / 10 - 2 * v, 46, 0);
    else {
        x = 16 - (uint16_t)(w * 3) / 2;
        if (x > -17) ball(st, x, 46 + (uint16_t)(w * 3) / 2, w);
        else edge(st, w - 22, 70);
        if (w < 12) puff(st, 8, 42, w >> 2);
    }
    return w < 38;
}

// 6 ROBOT. The belt takes him flat along the bar (the conveyor) to a returns box at its left end, which swallows him (a boot waves
// out of it), hops, and rides off the left edge on the belt.
static uint8_t gag_robot(uint8_t *st, uint8_t t) {
    int16_t u = (int16_t)t - OPEN, w = u - 68, cx = 24, cy = 46;
    if (w >= 20) cx = 24 - (w - 20) * 2;
    else if (w >= 0) cy = 46 - ((w >> 2) & 1) * 2;
    two(st, cx, cy, T_B, PP, 0);
    if (opening(st, t)) { }
    else if (w < 0) lying(st, XD - u, 46 + ((u >> 3) & 1), 0);
    if (w >= 0 && cx > -16) ent(st, cx + 5, cy - 8 - ((w >> 1) & 1) * 2, T_X, PD);   // a boot waving out of the box
    if (w >= 40) edge(st, w - 40, 42);
    return w < 56;
}

// 7 PUNKS, two pages. The chord page: sound arcs sweep in from the right (a drum and a hit), he shakes, and waits. The next page, the
// blast: the arcs catch him, he is blown left as a ball, faster and faster, arcs chasing him.
static uint8_t gag_punks(uint8_t *st, uint8_t t, uint8_t ph) {
    int16_t u = (int16_t)t - OPEN, x = XD, w, s;
    uint8_t i;
    if (ph == 0) {
        if (opening(st, t)) return 1;
        if (u >= 14) x += (u & 1) ? 1 : -1;
        dregs(st, x, LANE, 1, 0);
        if (u == 4) SFX(SFX_DON);
        if (u == 24) SFX(SFX_KA);
        for (i = 0; i < 3; i++) { s = 150 - u * 3 + i * 22; if (u >= 0 && s > -8) arc(st, s, LANE + 2, 1); }
        return u < 70 ? 1 : 2;
    }
    w = (int16_t)t - 30;
    if (t == 0) SFX(SFX_WHOOSH);
    if (w == 0) { SFX(SFX_DON); SFX(SFX_KA); }
    if (w < 0) {
        dregs(st, XD + ((t & 1) ? 2 : -2), LANE, 1, 0);
        for (i = 0; i < 3; i++) { s = 150 - t * 4 + i * 22; if (s > -8) arc(st, s, LANE + 2, 1); }
        return 1;
    }
    s = XD - w * 3 - (w * w) / 6;
    if (s > -17) {
        ball(st, s, LANE + 4, w);
        for (i = 0; i < 3; i++) arc(st, s + 22 + i * 14, LANE + 2, 1);
    } else edge(st, w - 19, 42);
    return w < 38;
}

// 8 TEAHOUSE. One mighty beat (a drum, a shock ring round him), then he tumbles out: a ball bouncing three times across the floor.
static uint8_t gag_tea(uint8_t *st, uint8_t t) {
    int16_t u = (int16_t)t - OPEN, w = u - 12, p, x;
    if (opening(st, t)) return 1;
    if (u == 6) SFX(SFX_DON);
    if (w < 0) {
        dregs(st, XD, LANE, 1, 0);
        if (u >= 6) { arc(st, XD - 6 - (u - 6) * 3, LANE + 2, 1); arc(st, XD + 16 + (u - 6) * 3, LANE + 2, 0); }
        return 1;
    }
    x = XD - 2 * w;
    p = w % 24;
    if (p == 0 && w) SFX(SFX_KA);
    if (x > -17) ball(st, x, LANE + 4 - (p * (24 - p)) / 6, w);
    else edge(st, w - 57, 42);
    return w < 73;
}

// 9 ZOO. Two monkeys run in after him and snatch a boot, the other boot and his hat in turn (they fly off in arcs); he runs off left
// in his socks with the monkeys on his heels.
static uint8_t gag_zoo(uint8_t *st, uint8_t t) {
    int16_t u = (int16_t)t - OPEN, w = u - 24, dx = XD, m, f;
    uint8_t pm = is_cgb ? 5 : S_PALETTE, fr = ((t >> 2) & 1) * 4;
    if (w > 0) dx = XD - w * 4;
    if (opening(st, t)) { }
    else if (dx > -17) dregs(st, dx, LANE + (w > 0 ? ((w >> 1) & 1) : 0), 0, 0);
    else edge(st, w - 29, 42);
    f = u - 2;                                                                    // the left boot
    if (f >= 0 && f < 26) ent(st, XD + 2 + f * 2, 56 - (f * (26 - f)) / 4, T_B, PD | ((f >> 2) & 1 ? S_FLIPY : 0));
    f = u - 10;                                                                   // the right boot
    if (f >= 0 && f < 26) ent(st, XD + 10 + f * 2, 56 - (f * (26 - f)) / 4, T_B, PD | ((f >> 2) & 1 ? S_FLIPX : 0));
    f = u - 16;                                                                   // the hat
    if (f >= 0 && f < 20) ent(st, XD + 4 + f, LANE - (f * (20 - f)) / 3, T_B + 2, PD);
    m = 170 - ((int16_t)t - 10) * 3;                                              // the monkeys: in from the right, then after him
    if (m < XD + 20) m = XD + 20;
    if (w > 0) m = dx + 20;
    if (t >= 10) { two(st, m, 48, T_X + fr, pm, 0); two(st, m + 18, 48, T_X + fr, pm, 0); }
    return w < 46;
}

// 10 SPACE. Page 1: a saucer drops in, its beam comes down on him and he floats up, wriggling, into it (a sparkle), the beam goes and
// the saucer leaves. Page 2 ("came down"): the saucer is back, the beam sets him down, in the souvenir T-shirt (CGB: his jacket goes
// pink), he waves and trots off left.
static void saucer(uint8_t *st, int16_t sx, uint8_t rows, uint8_t t) {
    uint8_t r;
    for (r = 0; r < rows; r++) {
        ent(st, XD, 24 + r * 16, T_X + ((t >> 2) & 1) * 2, is_cgb ? 5 : S_PALETTE);
        ent(st, XD + 8, 24 + r * 16, T_X + ((t >> 2) & 1) * 2, (is_cgb ? 5 : S_PALETTE) | S_FLIPX);
    }
    two(st, sx, 8, T_B, PP, 0);
}

static uint8_t gag_space(uint8_t *st, uint8_t t, uint8_t ph) {
    int16_t u = (int16_t)t - OPEN, w, sx, y;
    uint8_t rows;
    if (ph == 0) {
        sx = u < 14 ? XD + (14 - u) * 5 : XD;
        w = u - 44;
        rows = u < 14 ? 0 : u < 18 ? 1 : u < 22 ? 2 : 3;
        if (w >= 0) { rows = w < 4 ? 3 : w < 8 ? 2 : w < 12 ? 1 : 0; if (w >= 16) sx = XD + (w - 16) * 6; }
        if (opening(st, t)) { }
        else if (u < 18) dregs(st, XD, LANE, 1, 0);
        else if (w < 0) {
            y = LANE - (u - 18);
            dregs(st, XD, y, (u >> 2) & 1, (u >> 3) & 1);
        }
        else if (w < 12) puff(st, XD + 4, 14, w >> 2);
        if (w == 0) SFX(SFX_COIN);
        if (u == 0) SFX(SFX_WHOOSH);
        if (u >= 0 && sx < 160) saucer(st, sx, rows, t);
        return w < 28;
    }
    sx = t < 14 ? XD + (14 - t) * 5 : XD;                                         // page 2
    w = (int16_t)t - 116;
    if (t == 0) SFX(SFX_WHOOSH);
    rows = t < 14 ? 0 : t < 18 ? 1 : t < 22 ? 2 : 3;
    if (t >= 104) { rows = t < 108 ? 3 : t < 112 ? 2 : t < 116 ? 1 : 0; }
    if (w >= 0) sx = XD + w * 6;
    if (t >= 26 && t < 74) dregs(st, XD, 16 + (uint16_t)(t - 26) / 2, (t >> 2) & 1, (t >> 3) & 1);
    else if (t >= 74 && t < 116) dregs(st, XD, LANE, (t >> 2) & 1, 0);
    else if (w >= 0) dregs(st, XD - w * 3, LANE + ((w >> 1) & 1), 0, 0);
    if (t >= 26 && t < 74) puff(st, XD + ((t >> 2) & 1) * 14 - 2, 24 + ((t >> 3) & 3) * 12, (t >> 1) % 3);   // the T-shirt's sparkle
    if (sx < 160) saucer(st, sx, rows, t);
    return w < 40;
}

// ---- dispatch ---------------------------------------------------------------------------------------------------------------------
static void spr_pal(uint8_t slot, const uint16_t *p) { if (is_cgb) set_sprite_palette(slot, 1, p); }

static const uint16_t pal_tee[4]    = { 0, RGB15(30, 27, 20), RGB15(31, 13, 19), RGB15(4, 3, 5) };    // his souvenir T-shirt: pink for the jacket
static const uint16_t pal_plate[4]  = { 0, RGB15(30, 30, 28), RGB15(8, 16, 28), RGB15(3, 3, 10) };    // rim, blue band
static const uint16_t pal_crate[4]  = { 0, RGB15(28, 22, 13), RGB15(20, 13, 6), RGB15(6, 3, 1) };     // cardboard, tape, outline
static const uint16_t pal_chord[4]  = { 0, 0, 0, RGB15(30, 10, 22) };                                 // the punks' sound arcs: hot pink
static const uint16_t pal_beat[4]   = { 0, 0, 0, RGB15(30, 24, 6) };                                  // the taiko's: gold
static const uint16_t pal_saucer[4] = { 0, RGB15(26, 28, 31), RGB15(18, 16, 28), RGB15(6, 4, 14) };
static const uint16_t pal_beam[4]   = { 0, RGB15(18, 31, 31), 0, 0 };
static const uint16_t pal_monkey[4] = { 0, RGB15(29, 24, 18), RGB15(17, 10, 5), RGB15(5, 3, 1) };    // Monkey Business's

static void pats(uint8_t g, uint8_t n) {           // the group's n variants' shift-0 poses to OBJ T_P.., their palettes to OBJ 5..
    uint16_t p[4];
    uint8_t v;
    if (g) spr_data_far(T_P, n * 6, patron_tiles_sports + PATRON_SHIFT0_OFS * 16, BANK(patron_tiles_sports));
    else   spr_data_far(T_P, n * 6, patron_tiles_cowboys + PATRON_SHIFT0_OFS * 16, BANK(patron_tiles_cowboys));
    for (v = 0; v < n && is_cgb; v++) { patron_pal_get(g, v, p); p[0] = 0; set_sprite_palette(5 + v, 1, p); }
}

void dg_load(uint8_t *st, uint8_t v) BANKED {
    st[4] = 0;
    set_sprite_data(T_A, DG_A_TILES, dg_a);
    spr_pal(1, pal_dregs);
    if (!is_cgb) OBP1_REG = OBP1_PLAY;
    switch (v) {
    case 0: pats(0, 2); break;
    case 1: pats(1, 3); break;
    case 2: set_sprite_data(T_B, 2, dg_boots); break;
    case 3: set_sprite_data(T_B, 2, dg_plate); spr_pal(2, pal_plate); break;
    case 5: set_sprite_data(T_B, 4, dg_crate); set_sprite_data(T_X, 2, dg_boots); spr_pal(2, pal_crate); break;
    case 6: set_sprite_data(T_B, 2, dg_arc); spr_pal(2, pal_chord); break;
    case 7: set_sprite_data(T_B, 2, dg_arc); spr_pal(2, pal_beat); break;
    case 8: set_sprite_data(T_B, 2, dg_boots); set_sprite_data(T_B + 2, 2, dg_hat); set_sprite_data(T_X, 8, dg_monkey); spr_pal(5, pal_monkey); break;
    case 9: set_sprite_data(T_B, 4, dg_saucer); set_sprite_data(T_X, 4, dg_beam); spr_pal(2, pal_saucer); spr_pal(5, pal_beam); break;
    }
}

void dg_page(uint8_t *st, uint8_t scene, uint8_t prev, uint8_t spk) BANKED {
    uint8_t ph = 255, i, v = (scene - SC_POST_SALOON) >> 1;
    if (st[4]) {                                    // the last page's gag (or its held last picture) goes
        for (i = OAM0; i < 40; i++) shadow_OAM[i].y = 0;
        st[4] = 0;
        if (st[3] == 2) spr_pal(1, pal_dregs);
    }
    if (spk != SPK_NARRATOR || (scene & 1)) return;
    if (prev == SPK_DREGS) ph = 0;
    else if (prev == SPK_NARRATOR && v == 6) ph = 1;               // the punks' blast page
    else if (prev == SPK_SPIGOTEER && v == 9) ph = 2;              // the space lounge's "came down" page
    if (ph == 255) return;
    if (ph == 2) spr_pal(1, pal_tee);
    st[0] = 0; st[2] = v; st[3] = ph; st[4] = 1;
}

void dg_frame(uint8_t *st) BANKED {
    uint8_t t = st[0], i, run = 1, ph = st[3];
    st[1] = OAM0;
    switch (st[2]) {
    case 0: run = gag_saloon(st, t); break;
    case 1: run = gag_stadium(st, t); break;
    case 2: run = gag_lumber(st, t); break;
    case 3: run = gag_bistro(st, t); break;
    case 4: run = gag_igloo(st, t); break;
    case 5: run = gag_robot(st, t); break;
    case 6: run = gag_punks(st, t, ph); break;
    case 7: run = gag_tea(st, t); break;
    case 8: run = gag_zoo(st, t); break;
    default: run = gag_space(st, t, ph);
    }
    for (i = run ? st[1] : OAM0; i < 40; i++) shadow_OAM[i].y = 0;   // (a gag that ends leaves nothing)
    if (run == 2) st[4] = 2;                        // done, left standing
    else if (!run) { st[4] = 0; if (ph == 2) spr_pal(1, pal_dregs); }   // (the T-shirt's colours go back)
    else st[0] = t + 1;
}
