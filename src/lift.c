// M13a: lifted patrons, the plumbing (docs/overlap_design.md). A patron is a BG picture (render.c) until he is lifted:
// then he is drawn as two 8x16 sprites from his own shift-0 BG tiles (the tiles are stored column by column, the
// shift-0 poses at even ids >= 128, see tools/gen_art.py) and his BG footprint shows plain wall. No rule lifts anyone
// yet (that is M13b); the test hook below does, and this file keeps the lifted set legal every frame:
//   - lift: the sprite shows at once and the BG copy is erased in the same VBlank (bg_urgent); never while last
//     frame's copy list still waits (vq_held) or his BG copy is not on screen yet (bg_pending).
//   - drop: the BG copy is put back first (queued at once when possible) and the sprite stays until that copy has gone
//     out (one more frame at least), so no frame shows him missing or twice.
//   - budget: at most LIFT_PER_BAR per bar and LIFT_MAX in all (OAM 18-25); a lift needs room for 2 more objects on
//     the bar's patron lines (estimate below, at most LINE_OBJ_MAX) and in OAM next to the mugs (which never lose an
//     entry); when either goes over, lifted patrons are dropped (forced drops go at once: BG copy and sprite swap in
//     one VBlank).
// Banked (bank 1 and 2 are full); lift_frame / draw_lifted are only called while someone is lifted or the hook is set.
#pragma bank 5
#include <gb/gb.h>
#include <gb/cgb.h>
#include <stdint.h>

#include "game.h"
#include "palettes.h"

uint8_t patron_lift[MAX_PATRONS];   // LIFT_BG / LIFT_OBJ / LIFT_BEHIND, | LIFT_DROP while dropping
uint8_t lift_n[NUM_BARS];           // patrons of the bar drawn as sprites (lifted or dropping)
uint8_t lift_total;                 // all of them (the mugs end at OAM_MUG_END - 2 * lift_total)
uint8_t lift_oam_n;                 // patrons draw_lifted() wrote last frame
uint8_t lift_load[NUM_BARS];        // the per-bar estimate of objects on the patron lines after the last lift_frame (tests)
uint8_t lift_mug_oam;               // OAM entries the mugs need this frame
uint8_t lift_forced;                // forced drops so far (tests read it)
uint8_t spr_puff_t, spr_puff_p;     // the door puff's first tile and attribute (render.c draws it)
// Test hook: lift_hook_p = slot, lift_hook_op = HOOK_*; lift_frame() does it as soon as it may (lift_hook_res = 1, op
// cleared) or refuses it (res 2, op cleared). A lift waits while vq_held / his BG copy is pending.
uint8_t lift_hook_op, lift_hook_p, lift_hook_res;
enum { HOOK_NONE, HOOK_LIFT, HOOK_BEHIND, HOOK_DROP };
enum { RES_NONE, RES_DONE, RES_REFUSED };

#define OAM_LIFT_TOP   (OAM_MUG_END - 1)                  // 25: lifted patrons count down from here
#define MUG_OAM_ALL    (OAM_MUG_END - (OAM_FILL + 1))     // 21 entries for mugs and lifted patrons together
#define OAM_SPARE      2                                  // kept free for this frame's new mug / breaking glass

static const uint8_t lift_pal[4] = { OBJPAL_PATRON_A, OBJPAL_PATRON_B, OBJPAL_PATRON_C, OBJPAL_PATRON_A };
static const uint8_t lift_tile[4] = { PATRON_OBJ_BASE, PATRON_OBJ_BASE + 6, PATRON_OBJ_BASE + 12, PATRON_OBJ_BASE };

// n OBJ tiles src -> dst with the two bit planes swapped (colours 1 and 2 trade places). LCD off.
static void swap_copy(uint8_t src, uint8_t dst, uint8_t n) {
    const uint8_t *s = (const uint8_t *)(0x8000u + (uint16_t)src * 16u);
    uint8_t *d = (uint8_t *)(0x8000u + (uint16_t)dst * 16u), k, a;
    for (k = n * 8; k; k--) { a = s[0]; d[0] = s[1]; d[1] = a; s += 2; d += 2; }
}

// Level load, LCD off, after load_venue / the patron tiles: nobody lifted; CGB the patrons' OBJ palettes (colours 1-3 of
// their BG palettes); DMG OBP1 for the patrons and OBP0 copies for what used OBP1. Sets the mug / glass / puff looks.
void lift_level_init(uint8_t g) BANKED {
    uint8_t v, i;
    palette_t p;
    for (v = 0; v < MAX_PATRONS; v++) patron_lift[v] = LIFT_BG;
    for (v = 0; v < NUM_BARS; v++) lift_n[v] = 0;
    lift_total = 0; lift_oam_n = 0; lift_hook_op = HOOK_NONE;
    pal5_cur = 2;                                 // load_venue put the show's palette in slot 5
    if (is_cgb) {
        for (v = 0; v < 3; v++) {
            p[0] = 0;
            for (i = 1; i < 4; i++) p[i] = palettes[patron_pal_ids[g][v]][i];
            set_sprite_palette(lift_pal[v], 1, p);
        }
        spr_full_t = OBJ_MUG;                spr_full_p = S_PALETTE | OBJPAL_MUG_FULL;
        spr_empty_t = OBJ_MUG + 2;           spr_empty_p = S_PALETTE | OBJPAL_MUG_EMPTY;
        spr_hempty_t = OBJ_MUG_DRINK + 6;    spr_hempty_p = S_PALETTE | OBJPAL_MUG_EMPTY;
        spr_glass_p = S_PALETTE | OBJPAL_GLASS;
        spr_puff_t = OBJ_PUFF;               spr_puff_p = S_PALETTE | OBJPAL_GLASS;
        return;
    }
    OBP1_REG = OBP1_PLAY;
    swap_copy(OBJ_MUG, OBJ_DMG_COPY, 4);                 // sliding full, sliding empty
    swap_copy(OBJ_MUG_DRINK + 6, OBJ_DMG_COPY + 4, 2);   // the empty in a patron's hand
    swap_copy(OBJ_PUFF, OBJ_DMG_COPY + 6, PUFF_FRAMES * 2);
    spr_full_t = OBJ_DMG_COPY;      spr_full_p = 0;
    spr_empty_t = OBJ_DMG_COPY + 2; spr_empty_p = 0;
    spr_hempty_t = OBJ_DMG_COPY + 4; spr_hempty_p = 0;
    spr_glass_p = 0;                                     // the shards: original tiles on OBP0 (light / white swapped)
    spr_puff_t = OBJ_DMG_COPY + 6;  spr_puff_p = 0;
}

static uint8_t col_of(uint8_t p) { return (patron_draw[p] & ~DRAW_BACK) >> 3; }

static void recount(void) {
    uint8_t p, b;
    lift_n[0] = lift_n[1] = lift_n[2] = lift_n[3] = 0;
    lift_total = 0;
    for (p = 0; p < MAX_PATRONS; p++) {
        if (!patron_lift[p]) continue;
        if (patron_state[p] == PATRON_NONE || patron_draw[p] == 255) { patron_lift[p] = LIFT_BG; continue; }
        b = patron_bar[p] & (NUM_BARS - 1);
        lift_n[b]++;
        lift_total++;
    }
}

// Objects on bar b's patron lines (its top 16 lines), counted generously: the bartender's top pair on his bar and his
// bottom pair on the bar below (it covers the heads), the fill glass, every mug (a breaking glass is 2 entries and
// falls 3 lines into the bar below), the coin, the puff, and 2 per patron drawn as sprites.
static uint8_t ld[NUM_BARS];
static void estimate(void) {
    uint8_t i, st, b, m = 0;
    for (b = 0; b < NUM_BARS; b++) ld[b] = lift_n[b] << 1;
    b = bar & (NUM_BARS - 1);
    ld[b] += fill_timer ? 3 : 2;
    if (b < NUM_BARS - 1) ld[b + 1] += 2;
    for (i = 0; i < MAX_MUGS; i++) {
        st = mug_state[i];
        if (st == MUG_FREE) continue;
        b = mug_bar[i] & (NUM_BARS - 1);
        if (st == MUG_BREAKING) {
            ld[b] += 2; m += 2;
            if (b < NUM_BARS - 1) ld[b + 1] += 2;
        } else { ld[b]++; m++; }
    }
    if (tip_timer) ld[tip_bar & (NUM_BARS - 1)]++;
    if (puff_timer) ld[puff_bar & (NUM_BARS - 1)]++;
    lift_mug_oam = m;
}

// Drop p: his BG copy goes back first (at the head of this frame's list when possible); the sprite stays until it
// is on screen (finish_drops).
static void begin_drop(uint8_t p) {
    uint8_t b = patron_bar[p] & (NUM_BARS - 1), c = col_of(p);
    patron_lift[p] |= LIFT_DROP;
    if (!bg_urgent(b, c)) mark_dirty(b, c, c + 3);
}

// A forced drop: BG copy queued at the head of this frame's list and the sprite gone with the same VBlank, so the
// over-full lines are never drawn. If this frame's list cannot take it (vq_held), an ordinary drop.
static void force_drop(uint8_t p) {
    uint8_t b = patron_bar[p] & (NUM_BARS - 1);
    lift_forced++;
    if (!bg_urgent(b, col_of(p))) { begin_drop(p); return; }
    patron_lift[p] = LIFT_BG;
    lift_n[b]--;
    lift_total--;
}

static void finish_drops(void) {
    uint8_t p;
    if (vq_held) return;                                  // last frame's list (maybe his copy) has not gone out
    for (p = 0; p < MAX_PATRONS; p++) {
        if (!(patron_lift[p] & LIFT_DROP) || bg_pending(p)) continue;
        patron_lift[p] = LIFT_BG;                         // his BG copy is on screen: the sprite goes this frame
        lift_n[patron_bar[p] & (NUM_BARS - 1)]--;
        lift_total--;
    }
}

// A lifted (not dropping) patron of bar b (b = NUM_BARS: any bar), the last slot first; NO_SLOT if none.
static uint8_t pick_lifted(uint8_t b) {
    uint8_t p = MAX_PATRONS;
    while (p--) {
        if (!LIFT_OFF_BG(patron_lift[p])) continue;
        if (b == NUM_BARS || (patron_bar[p] & (NUM_BARS - 1)) == b) return p;
    }
    return NO_SLOT;
}

static void forced_drops(void) {
    uint8_t b, p;
    for (b = 0; b < NUM_BARS; b++)
        while (ld[b] > LINE_OBJ_MAX && (p = pick_lifted(b)) != NO_SLOT) { force_drop(p); ld[b] -= 2; }
    // OAM: the mugs keep every entry they need (and OAM_SPARE more for this frame's newcomers)
    while (lift_mug_oam + (lift_total << 1) > MUG_OAM_ALL - OAM_SPARE && (p = pick_lifted(NUM_BARS)) != NO_SLOT) {
        force_drop(p);
        if (patron_lift[p]) break;                        // an ordinary drop: its sprite stays a frame; next frame again
    }
}

// The hook's lift: 0 refused, 1 done, 2 not this frame.
static uint8_t try_lift(uint8_t p, uint8_t mode) {
    uint8_t b = patron_bar[p] & (NUM_BARS - 1), d = patron_draw[p];
    if (patron_state[p] == PATRON_NONE || patron_lift[p] || d == 255 || (d & DRAW_BACK) || patron_dist[p]) return 0;
    if (lift_total >= LIFT_MAX || lift_n[b] >= LIFT_PER_BAR) return 0;
    if (lift_mug_oam + ((lift_total + 1) << 1) > MUG_OAM_ALL - OAM_SPARE) return 0;
    if (ld[b] + 2 > LINE_OBJ_MAX) return 0;
    if (vq_held || bg_pending(p) || !bg_urgent(b, d >> 3)) return 2;   // sprite now, BG erased in the same VBlank
    patron_lift[p] = mode;
    lift_n[b]++;
    lift_total++;
    ld[b] += 2;
    return 1;
}

static void hook(void) {
    uint8_t p = lift_hook_p & (MAX_PATRONS - 1), r;
    if (lift_hook_op == HOOK_DROP) {
        if (!LIFT_OFF_BG(patron_lift[p])) r = 0;
        else { begin_drop(p); r = 1; }
    } else r = try_lift(p, lift_hook_op == HOOK_BEHIND ? LIFT_BEHIND : LIFT_OBJ);
    if (r == 2) return;                                   // try again next frame
    lift_hook_res = r ? RES_DONE : RES_REFUSED;
    lift_hook_op = HOOK_NONE;
}

// Every frame while someone is lifted (or the hook is set), after the rules and before queue_vram().
void lift_frame(void) BANKED {
    uint8_t p;
    recount();
    finish_drops();
    for (p = 0; p < MAX_PATRONS; p++)                     // never lifted in a back view: he turns round on the BG
        if (LIFT_OFF_BG(patron_lift[p]) && ((patron_draw[p] & DRAW_BACK) || patron_dist[p])) begin_drop(p);
    estimate();
    forced_drops();
    if (lift_hook_op) hook();
    for (p = 0; p < NUM_BARS; p++) lift_load[p] = ld[p];   // (after this frame's drops and lifts)
}

// OAM 25 down: two 8x16 entries per patron drawn as a sprite (his shift-0 pose; OAM x gives every pixel position and
// the sway). Entries used last frame but not now are hidden unless the mugs took them this frame.
void draw_lifted(void) BANKED {
    uint8_t p, v, n = 0, d, x, y, t, pr, i;
    OAM_item_t *o = shadow_OAM + OAM_LIFT_TOP;
    for (p = 0; p < MAX_PATRONS && n < LIFT_MAX; p++) {
        v = patron_lift[p] & 3;
        if (!v || (d = patron_draw[p]) == 255) continue;
        x = (d & ~DRAW_BACK) + 8;
        y = bar_oam_y[patron_bar[p] & (NUM_BARS - 1)];
        i = patron_variant[p] & 3;
        t = lift_tile[i];
        pr = is_cgb ? lift_pal[i] : S_PALETTE;
        if (v == LIFT_BEHIND) pr |= S_PRIORITY;
        o->y = y; o->x = x;     o->tile = t;     o->prop = pr; o--;
        o->y = y; o->x = x + 8; o->tile = t + 2; o->prop = pr; o--;
        n++;
    }
    for (i = OAM_LIFT_TOP + 1 - (lift_oam_n << 1); i < (uint8_t)(OAM_LIFT_TOP + 1 - (n << 1)); i++)
        if (i >= oam_used) shadow_OAM[i].y = 0;
    lift_oam_n = n;
}
