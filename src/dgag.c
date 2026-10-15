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
// Every gag is a closed-form function of its frame number. The common opening: Dregs dashes in from the right (whoosh), reaches for
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

#define SPK_DREGS 1                 // the speaker index of DREGS (tools/gen_story.py SPEAKERS; SPK_NARRATOR is in story.h)
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

static void dust(uint8_t *st, uint8_t te) {         // the puff at the left edge, te frames after the crash (4 video frames a picture)
    uint8_t f = te >> 2;
    if (f > 2) return;
    ent(st, 0, 42, T_DUST + f * 2, 0); ent(st, 6, 50, T_DUST + f * 2, 0);
}

// ---- the common opening: the dash in and the reach. 1 while it plays (t < OPEN) -------------------------------------------------------
#define OPEN     36
static uint8_t opening(uint8_t *st, uint8_t t) {
    int16_t x = XD, y = LANE;
    if (t >= OPEN) return 0;
    if (t == 0) SFX(SFX_WHOOSH);
    if (t < 20) { x = XD + (20 - t) * 4; y = LANE + ((t >> 1) & 1); }     // the dash, bobbing
    else if (t >= 28 && t < 34) y = LANE - 4;                             // one hop as he grabs
    dregs(st, x, y, t >= 22, 0);
    return 1;
}

// ---- the gags: 1 while running ------------------------------------------------------------------------------------------------------
// The generic way out (every venue, until it has its own): thrown in an arc as a tumbling ball, rolling off the left edge.
static uint8_t gag_toss(uint8_t *st, uint8_t t) {
    uint8_t u;
    int16_t x, y;
    if (opening(st, t)) return 1;
    u = t - OPEN;
    x = XD - u * 3;
    y = u < 12 ? LANE + 4 - (u * (12 - u)) / 4 : LANE + 4;
    if (x > -17) { ball(st, x, y, u); return 1; }
    u = (uint8_t)(-(x + 17)) / 3;                    // frames since he left the screen
    if (u == 0) SFX(SFX_BREAK);
    dust(st, u);
    return u < 20;
}

// ---- dispatch ---------------------------------------------------------------------------------------------------------------------
static void spr_pal(uint8_t slot, const uint16_t *p) { if (is_cgb) set_sprite_palette(slot, 1, p); }

void dg_load(uint8_t *st, uint8_t v) BANKED {
    st[4] = 0;
    set_sprite_data(T_A, DG_A_TILES, dg_a);
    spr_pal(1, pal_dregs);
    if (!is_cgb) OBP1_REG = OBP1_PLAY;
    (void)v;
}

void dg_page(uint8_t *st, uint8_t scene, uint8_t prev, uint8_t spk) BANKED {
    uint8_t ph = 255, i;
    if (st[4]) {                                    // the last page's gag (or its held last picture) goes
        for (i = OAM0; i < 40; i++) shadow_OAM[i].y = 0;
        st[4] = 0;
    }
    if (spk != SPK_NARRATOR || (scene & 1)) return;
    if (prev == SPK_DREGS) ph = 0;
    if (ph == 255) return;
    st[0] = 0; st[2] = (scene - SC_POST_SALOON) >> 1; st[3] = ph; st[4] = 1;
}

void dg_frame(uint8_t *st) BANKED {
    uint8_t t = st[0], i, run = 1;
    st[1] = OAM0;
    switch (st[2]) {
    default: run = gag_toss(st, t);
    }
    for (i = st[1]; i < 40; i++) shadow_OAM[i].y = 0;
    if (!run) st[4] = 0;
    else st[0] = t + 1;
}
