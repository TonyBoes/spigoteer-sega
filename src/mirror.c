// P3/P4 (CLASSIC): bars whose patrons come from the right (game.h bar_dirs; the drawing itself: render.c, mugs.c,
// lift.c). Everything here runs at a level load with the LCD off: the per-bar sprite tables, the patron tile tables
// (st_tab) and, on the DMG (no BG flip attribute), the flipped tile data.
//
// DMG tile schemes (an R bar draws every tile flipped, so the DMG needs the flipped pixels in VRAM):
//   - every bar L: nothing (the tiles as loaded).
//   - every bar R (the whole screen flips): the group's 156 patron tiles are bit-reversed in place; the shift-0 poses are
//     then flipped as OBJ tiles too, so a lifted patron needs no OAM flip there (bar_pf 0).
//   - mixed (both directions on screen): owner option (a): patrons are drawn at even x only (draw_mask 0xFE: 2 px
//     steps), so each direction needs shifts 0, 2, 4, 6. The L set keeps its ids; the R set (flipped copies of the even
//     shifts) goes into the odd shifts' slots (R shift s at the slot of L shift s + 1). Back views are shared, drawn
//     unmirrored on an R bar (mir_bswap). A lifted patron on an R bar is the L shift-0 pose with the OAM flip.
//   - mixed, option (b) (level_dirs bit 6, MIXED_B: the debug box's MIXED line; DMG only; option (a) is the default): 1 px
//     steps (draw_mask 0xFF). The looks are split between the directions: variants A and B only on L bars (tiles as
//     loaded), variant C only on R bars (add_patron picks it; its 42 shifted tiles, its shift-0 pose and its back view
//     are bit-reversed in place, so a lifted C needs no OAM flip and its back view no swap). No tile is added.
//     (mixed_b sets it up after option (a)'s tables: the CGB's and the title's loads, whose pumps are timed, run as before.)
//   - any R bar: the keg, spout and counter tiles of the bar rows get flipped copies in free BG ids (FREE_IDS); a tile
//     that is its own mirror image keeps its id. mir_short counts tiles left unflipped for want of an id (tests: 0).
// CGB: the X-flip attribute does all of it (tiles, keg, patrons, back views), and the OAM flip the sprites.
#pragma bank 255
#include <gb/gb.h>
#include <gb/cgb.h>
#include <stdint.h>
#include <string.h>

#include "game.h"
#include "music.h"

uint8_t level_dirs;                 // the LEVEL harness's directions for its next level load (test hook, debug box)
uint8_t draw_mask;                  // patron_draw = x & draw_mask (0xFE: a DMG mixed level)
uint8_t mir_short;                  // DMG: bar-row tiles left unflipped this level (no free id left)
uint8_t ctr_all[4][BASE_W];         // the counter row: tiles, attributes (load_venue), an R bar's in screen order (venue.c draw_venue)
uint8_t bar_tap[NUM_BARS] = { TAP_X, TAP_X, TAP_X, TAP_X };   // P6: bar b's fill position (game.h)
uint8_t bar_bofs[NUM_BARS];         // P6: bar b's window into base_all / ctr_all
uint8_t bar_sfp[2 * NUM_BARS];      // OAM attribute toggle of bar b's mugs, glass, fill and coin [b], lifted patrons [4 + b]
static uint8_t mo_tm[16], mo_tp[16];   // mirror_oam: the toggle by (OAM Y - 52) >> 3: bartender, fill, mugs, coin / lifted

// bit-reversed bytes: one row of 8 pixels mirrored (both bit planes)
#define R2(n) n, (uint8_t)(n + 2 * 64), (uint8_t)(n + 1 * 64), (uint8_t)(n + 3 * 64)
#define R4(n) R2(n), R2(n + 2 * 16), R2(n + 1 * 16), R2(n + 3 * 16)
#define R6(n) R4(n), R4(n + 2 * 4), R4(n + 1 * 4), R4(n + 3 * 4)
static const uint8_t rev[256] = { R6(0), R6(2), R6(1), R6(3) };

// VRAM of BG tile id t (signed mode, LCDC bit 4 clear: 0..127 at 0x9000, 128..255 at 0x8800)
static uint8_t *tile_at(uint8_t t) {
    return (uint8_t *)((t < 128 ? 0x9000u : 0x8000u) + ((uint16_t)t << 4));
}

static void flip_copy(uint8_t src, uint8_t dst) {   // tile src mirrored into tile dst (may be the same)
    uint8_t *s = tile_at(src), *d = tile_at(dst), k;
    for (k = 16; k; k--) *d++ = rev[*s++];
}

// first tile of variant v's pose at shift s (the M13a layout; render.c / gen_art.py)
static uint8_t pose(uint8_t v, uint8_t s) {
    return s ? PATRON_TILE_BASE + v * 42u + (s - 1u) * 6u : PATRON_OBJ_BASE + v * 6u;
}

// DMG mixed level (option (a)): R shift s (even) = L shift s flipped, in the slot of shift s + 1
// DMG mixed level, option (b): all of variant C's tiles flipped in place (42 shifted, 6 shift-0, 4 back); st_tab the same for
// both directions at every shift; lifted patrons need no OAM flip
static void mixed_b(void) {
    uint8_t k, v, s;
    for (k = 0; k < 42; k++) flip_copy(pose(2, 1) + k, pose(2, 1) + k);
    for (k = 0; k < 6; k++) flip_copy(pose(2, 0) + k, pose(2, 0) + k);
    for (k = 0; k < 4; k++) flip_copy(PATRON_BACK_BASE + 8 + k, PATRON_BACK_BASE + 8 + k);
    for (v = 0; v < 4; v++)
        for (s = 0; s < 8; s++) st_tab[32 | (v << 3) | s] = st_tab[(v << 3) | s] = pose(v == 3 ? 0 : v, s);
    for (v = 0; v < NUM_BARS; v++) bar_sfp[NUM_BARS + v] = 0;
    for (v = 0; v < 16; v++) mo_tp[v] &= 0x80;
    mir_bswap = MIX_B;
    draw_mask = 0xFF;
}

static void dmg_mixed(void) {
    uint8_t v, s, k, a, d;
    for (v = 0; v < 3; v++)
        for (s = 0; s < 8; s += 2) {
            a = pose(v, s); d = pose(v, s + 1);
            for (k = 0; k < 6; k++) flip_copy(a + k, d + k);
        }
}

// Free BG ids in play outside the story (game.h: 77 unused; 246-251 the old door puff; 252-255 the story's boss HUD;
// 234-239 the story's perfect pour), for the flipped keg / spout / counter tiles
#define FREE_N 17
static const uint8_t free_ids[FREE_N] = { 246, 247, 248, 249, 250, 251, 77, 252, 253, 254, 255, 234, 235, 236, 237, 238, 239 };
#define FMAP_N 24
static uint8_t fm_src[FMAP_N], fm_dst[FMAP_N], fm_n, fm_used;

// The id that shows tile t mirrored (DMG)
static uint8_t flip_id(uint8_t t) {
    uint8_t k, *s, d, same = 1, buf[16];
    for (k = 0; k < fm_n; k++) if (fm_src[k] == t) return fm_dst[k];
    s = tile_at(t);
    for (k = 0; k < 16; k++) if ((buf[k] = rev[s[k]]) != s[k]) same = 0;
    d = t;
    if (!same) {
        if (fm_used < FREE_N) { d = free_ids[fm_used++]; memcpy(tile_at(d), buf, 16); }
        else mir_short++;
    }
    if (fm_n < FMAP_N) { fm_src[fm_n] = t; fm_dst[fm_n] = d; fm_n++; }
    return d;
}

// An R bar's rows in screen order (BASE_W wide, P6): tiles reversed (DMG: flipped copies), attributes reversed with the X
// flip toggled
// alt: the lettering swap (gen_art.py LETTER_BOX): n, then n pairs (L tile, the free id holding its pre-mirrored twin; on the
// DMG the twin is already flipped). The tap's lettering (POP, MOO) is drawn mirrored in the twins, so the flip shows it the
// right way round.
static void mirror_row(uint8_t *dt, uint8_t *da, const uint8_t *st, const uint8_t *sa, const uint8_t *alt) {
    uint8_t c, t, k, found;
    for (c = 0; c < BASE_W; c++) {
        t = st[c];
        found = 0;
        for (k = 0; k < alt[0]; k++) if (t == alt[1 + 2 * k]) { t = alt[2 + 2 * k]; found = 1; break; }
        if (!is_cgb && !found) t = flip_id(t);
        dt[BASE_W - 1 - c] = t;
        da[BASE_W - 1 - c] = sa[c] ^ S_FLIPX;
    }
}

// dirs: bit b = bar b is R; bits 4-5 (P6) the taper: bar b's tap end (3 - b) * taper columns in (0: straight bars)
void mirror_load(uint8_t dirs) BANKED {
    uint8_t b, v, s, mixed, se, l, k, alt[9], hdr[5];
    k = (dirs >> 4) & 3;
    if (k > TAPER_MAX) k = TAPER_MAX;
    dirs &= 0x0F;
    for (b = 0; b < NUM_BARS; b++) {              // (P6) bar b's tap and its window into the base rows
        s = (uint8_t)(k * (3 - b));
        bar_tap[b] = TAP_X - (uint8_t)(s << 3);
        bar_bofs[b] = (dirs & bar_bit[b]) ? 2 * 2 * BASE_W + 3 * TAPER_MAX - s : s;
    }
    mixed = dirs && dirs != 0x0F;
    bar_dirs = dirs;
    for (b = 0; b < NUM_BARS; b++) {
        l = !(dirs & bar_bit[b]);
        bar_sfp[b] = l ? 0 : S_FLIPX;
        bar_sfp[NUM_BARS + b] = l || (!is_cgb && !mixed) ? 0 : S_FLIPX;   // (DMG, every bar R: the tiles are flipped)
    }
    for (b = 0; b < 16; b++) {                    // (mirror_oam: an entry at OAM Y 55 + 24 k .. 72 + 24 k is on bar k = (Y - 52) / 24)
        l = b < 3 ? 0 : b < 6 ? 1 : b < 9 ? 2 : 3;
        se = (dirs & bar_bit[l]) ? 0x80 : 0;      // (bit 7: an R bar; the rest the attribute toggle, 0 for a lifted
        mo_tm[b] = se | bar_sfp[l]; mo_tp[b] = se | bar_sfp[NUM_BARS + l];   // patron on the DMG with every bar R)
    }
    mir_attr = is_cgb ? S_FLIPX : 0;
    mixed = mixed && !is_cgb;                     // from here: the DMG's mixed scheme
    mir_bswap = mixed;
    draw_mask = mixed ? 0xFE : 0xFF;
    for (v = 0; v < 4; v++) {
        for (s = 0; s < 8; s++) {
            se = mixed ? s & 6 : s;
            l = pose(v == 3 ? 0 : v, se);
            st_tab[(v << 3) | s] = l;
            st_tab[32 | (v << 3) | s] = mixed ? pose(v == 3 ? 0 : v, se + 1) : l;
        }
        music_pump();                             // (the pose maths takes half a frame in all, LCD off in a screen's load: the tune ticks between its rows)
    }
    mir_short = 0;
    if (!dirs) return;
    if (!is_cgb) {
        if (mixed) { if (level_dirs & MIXED_B) mixed_b(); else dmg_mixed(); }
        else for (s = 0; s < PATRON_GROUP_TILES; s++) flip_copy(PATRON_TILE_BASE + s, PATRON_TILE_BASE + s);
        fm_n = fm_used = 0;
    }
    if (is_cgb) fm_n = fm_used = 0;
    far_copy(hdr, venue.bar_tiles + (uint16_t)venue.bar_n * 16, 5, venue_bank);   // the lettering twins (gen_art.py)
    alt[0] = hdr[0];
    for (k = 0; k < hdr[0]; k++) {
        l = free_ids[fm_used++];
        far_copy(tile_at(l), venue.bar_tiles + (uint16_t)venue.bar_n * 16 + 5 + k * 16, 16, venue_bank);
        if (!is_cgb) flip_copy(l, l);
        alt[1 + 2 * k] = hdr[1 + k]; alt[2 + 2 * k] = l;
    }
    mirror_row(base_rtile[0], base_rattr[0], base_tile[0], base_attr[0], alt);
    mirror_row(base_rtile[1], base_rattr[1], base_tile[1], base_attr[1], alt);
    mirror_row(ctr_all[2], ctr_all[3], ctr_all[0], ctr_all[1], alt);
}

// Every drawn play frame on a level with an R bar (main.c, OAM DMA off, after the sprites): the bartender, fill glass,
// mugs, breaking glasses, lifted patrons and the coin were written at bar-local X; an entry of an R bar goes to its
// mirrored place, X -> 168 - X, its attributes toggled (S_FLIPX; a lifted patron's: bar_sfp[4 + b]). Each of them lies
// between 1 line above and 16 lines below its bar's bar_oam_y (56 + 24 b), so its bar is (Y - 52) / 24 and mo_tm /
// mo_tp (mirror_load) give the toggle by (Y - 52) / 8. Only the entries in use are looked at: OAM 0..oam_used-1 (the
// bartender's 0-3 only when draw_bartender rewrote them, bt_new: they are cached), the lifted ones, the coin. Each is
// rewritten (or hidden, Y 0) every frame it is looked at, so none is mirrored twice.
#if BAR_TOP_Y(0) + 16 != 56 || BAR_ROW_STRIDE != 3 || OAM_FILL != 4 || OAM_MUG_END != 26 || OAM_COIN != 27
#error "mirror_oam: the bars at OAM y 56 + 24 b, OAM 0-3 bartender, 4 fill, mugs, .. 25 lifted, 27 coin"
#endif
static uint8_t *mo_p, *mo_t, mo_n;     // mo_range: mo_n entries from mo_p, toggles from mo_t

static void mo_range(void) __naked {
__asm
    push bc
    ld   a, (_mo_n)
    or   a, a
    jr   z, 9$
    ld   c, a
    ld   hl, #_mo_t
    ld   a, (hl+)
    ld   e, a
    ld   d, (hl)                    ; de: the toggle table
    ld   hl, #_mo_p
    ld   a, (hl+)
    ld   h, (hl)
    ld   l, a                       ; hl: the entry
1$:
    ld   a, (hl)                    ; y
    or   a, a
    jr   z, 8$                      ; (hidden)
    sub  a, #52
    rrca
    rrca
    rrca
    and  a, #0x0F
    push hl
    add  a, e
    ld   l, a
    ld   a, d
    adc  a, #0
    ld   h, a
    ld   b, (hl)                    ; its bar: bit 7 R, bits 0-6 the attribute toggle (0: an L bar)
    pop  hl
    ld   a, b
    or   a, a
    jr   z, 8$
    inc  hl
    ld   a, #168
    sub  a, (hl)
    ld   (hl+), a                   ; x = 168 - x
    inc  hl
    ld   a, (hl)
    res  7, b
    xor  a, b
    ld   (hl-), a                   ; attributes ^ the toggle
    dec  hl
    dec  hl
8$:
    inc  hl
    inc  hl
    inc  hl
    inc  hl
    dec  c
    jr   nz, 1$
9$:
    pop  bc
    ret
__endasm;
}

extern uint8_t bt_new;

void mirror_oam(void) BANKED {
    uint8_t f = bt_new ? 0 : OAM_FILL;
    bt_new = 0;
    mo_t = mo_tm; mo_p = (uint8_t *)(shadow_OAM + f); mo_n = oam_used - f; mo_range();
    if (lift_oam_n) {
        f = OAM_MUG_END - (lift_oam_n << 1);
        mo_t = mo_tp; mo_p = (uint8_t *)(shadow_OAM + f); mo_n = lift_oam_n << 1; mo_range();
    }
    mo_t = mo_tm; mo_p = (uint8_t *)(shadow_OAM + OAM_COIN); mo_n = 1; mo_range();
}

// A quick redraw (render.c queue_quick) of patron p, front view at d, on an R bar: his 6 tile ids mirrored into the
// shadow rows (they hold the screen picture), local columns c..c+2 at screen columns 19-c..17-c. Returns 17 - c, the
// first screen column; render.c queues the two rows from the shadow.
uint8_t quick_mirror(uint8_t p, uint8_t d) BANKED {
    uint8_t t = st_tab[32 | ((patron_variant[p] & 3) << 3) | (d & 7)], *r;
    d = 17 - (d >> 3);
    r = &sh_rows[0][(patron_bar[p] & (NUM_BARS - 1)) << 1][d];
    r[0] = t + 4; r[1] = t + 2; r[2] = t;
    r[32] = t + 5; r[33] = t + 3; r[34] = t + 1;
    return d;
}
