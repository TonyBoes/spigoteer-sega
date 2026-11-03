// M13a/b: lifted patrons (docs/overlap_design.md). A patron is a BG picture (render.c) until he is lifted: then he is
// drawn as two 8x16 sprites from his own shift-0 BG tiles (the tiles are stored column by column, the shift-0 poses at
// even ids >= 128, see tools/gen_art.py) and his BG footprint shows plain wall. M13b: the chooser (choose_bar) lifts
// patrons so that the BG ones never share a tile column, and drops them again when clear; the test hook below can
// lift one too (he stays lifted until the hook drops him). This file keeps the lifted set legal every frame:
//   - lift: the sprite shows at once and the BG copy is erased in the same VBlank (bg_urgent: columns c-1..c+3, so a
//     patron lifted on the frame he moved a pixel leaves nothing at his old place); never while last frame's copy
//     list still waits (vq_held).
//   - drop: the BG copy is put back first (queued at once when possible) and the sprite stays until that copy has gone
//     out (one more frame at least), so no frame shows him missing or twice.
//   - budget: at most LIFT_PER_BAR per bar and LIFT_MAX in all (OAM 18-25); a lift needs room for 2 more objects on
//     the bar's patron lines (estimate below, at most LINE_OBJ_MAX) and in OAM next to the mugs (which never lose an
//     entry); when either goes over, lifted patrons are dropped (forced drops go at once: BG copy and sprite swap in
//     one VBlank).
//   - M13b chooser, per bar whose patron columns changed (ovl_dirty): the BG patrons, left to right; when one shares a
//     real column with the last one kept on the BG, the one with the higher priority is lifted (pushed > hurried walker
//     > walker > drinker; never one watching the show or in his back view, never one being dropped). A lifted patron
//     stays lifted while he shares a column with a BG patron, and drops after LIFT_CLEAR_FRAMES clear frames.
//   - when a lift cannot be done (budgets, this frame's copy list), the pair stays on the BG: the one that would have
//     been lifted is drawn last (OVL_TOP: the bar is composed in two passes), quick redraws are off for whoever they
//     would draw wrongly (OVL_SHARED), a shift-0 patron whose empty 3rd column lies on another's figure stamps only his
//     2 real columns (OVL_TWO); the lift is tried again next frame (the copy list) or RETRY_FRAMES later (budgets).
//   - the left end (no door): a patron entering from beyond the screen's left edge or leaving past it (served) is
//     LIFT_EDGE: a sprite drawn patron_aux px left of patron_x (OAM X < 8 clips him at the edge), with no BG footprint
//     at all (the wall shows behind him), never dropped while any of him is off the screen; an entering one becomes
//     LIFT_OBJ at ENTRY_X and then follows the usual rules.
//   - the chooser runs for a bar only when ovl_touch (a patron who meets someone changed columns), a drop, the show or
//     a waiting lift asks; at most one bar a frame (the start bar goes round: frame_counter), and none on a frame that
//     is already late (CHOOSER_LY_LATE), the rest next frame.
// Cost (M13b, measured; one line = 114 machine cycles): the per-frame loops (lifted_scan, est_mugs, draw_lifted_asm)
// and the chooser's (choose_bar; before ASM_CHOOSER gather_asm and choose_asm) are hand-written; the same loops in C cost 5-15 lines each.
// Banked (bank 1 and 2 are full); lift_frame / draw_lifted are only called while someone is lifted, the chooser has
// work (ovl_dirty) or the hook is set.
#pragma bank 5
#include <gb/gb.h>
#include <gb/cgb.h>
#include <stdint.h>

#include "asm_cfg.h"
#include "game.h"
#include "music.h"
#include "palettes.h"
#include "tip2.h"
extern uint8_t cur_group;

uint8_t patron_lift[MAX_PATRONS];   // LIFT_BG / LIFT_OBJ / LIFT_EDGE, | LIFT_DROP while dropping
uint8_t lift_n[NUM_BARS];           // patrons of the bar drawn as sprites (lifted or dropping)
uint8_t lift_total;                 // all of them (the mugs end at OAM_MUG_END - 2 * lift_total)
uint8_t lift_oam_n;                 // patrons draw_lifted() wrote last frame
uint8_t lift_load[NUM_BARS];        // the per-bar estimate of objects on the patron lines after the last lift_frame (tests)
uint8_t lift_mug_oam;               // OAM entries the mugs need this frame
uint8_t lift_forced;                // forced drops so far (tests read it)
uint8_t patron_ovl[MAX_PATRONS];    // M13b: OVL_SHARED / OVL_TOP / OVL_TWO (BG patrons whose footprints meet; render.c)
uint8_t ovl_bars;                   // bars with an OVL_TOP patron: composed in two passes (render.c)
uint8_t ovl_dirty;                  // bars the chooser must look at (columns changed, or a lift still waits)
// (lift_busy and lift_pin in one array, so lifted_scan finds lift_pin[p] at lift_busy + 16)
uint8_t lift_bp[2][MAX_PATRONS];
#define lift_busy lift_bp[0]        // a lifted patron shares a column with a BG one (at the chooser's last look)
#define lift_pin  lift_bp[1]        // lifted by the test hook: stays until the hook drops him
uint8_t lift_clear[MAX_PATRONS];    // ... frames he has been clear of BG patrons (drops at LIFT_CLEAR_FRAMES)
uint8_t lift_lifts;                 // lifts by the chooser so far (tests read it)
// Test hook: lift_hook_p = slot, lift_hook_op = HOOK_*; lift_frame() does it as soon as it may (lift_hook_res = 1, op
// cleared) or refuses it (res 2, op cleared). A lift waits while vq_held.
uint8_t lift_hook_op, lift_hook_p, lift_hook_res;
enum { HOOK_NONE, HOOK_LIFT, HOOK_UNUSED, HOOK_DROP };   // (2 was the M13c door's lift behind the BG)
enum { RES_NONE, RES_DONE, RES_REFUSED };

#define OAM_LIFT_TOP   (OAM_MUG_END - 1)                  // 25: lifted patrons count down from here
#define MUG_OAM_ALL    (OAM_MUG_END - (OAM_FILL + 1))     // 21 entries for mugs and lifted patrons together
#define OAM_SPARE      2                                  // kept free for this frame's new mug / breaking glass

// OBJ palette of palette instance pi (patron_variant, render.c patron_attr): INST_OBJ, 8 bytes in story_scratch that looks_insts (build/looks.c) fills at the
// level load: the legacy A, B, C (OBJ 3, 6, 7), then the Saloon's two extra sets (OBJ 4, 5) or the generated venue's own (the Factory: 4, 1, 5)
#define lift_obj INST_OBJ
typedef char lift_obj_at_254[SCR_INST_AT == 254 ? 1 : -1];   // (draw_lifted_asm reads it at _story_scratch + 254)
// shift-0 OBJ tile of look v: 0-2 the group's, 3-7 the Saloon's Color-only looks (VRAM bank 1: OAM bit 3 from patron_variant bit 6)
static const uint8_t lift_tile[8] = { (uint8_t)PATRON_OBJ_BASE, (uint8_t)(PATRON_OBJ_BASE + 4), (uint8_t)(PATRON_OBJ_BASE + 8),
    SALOON_X_S0, SALOON_X_S0 + 4, SALOON_X_S0 + 8, SALOON_X_S0 + 12, SALOON_X_S0 + 16 };
uint8_t lift_prop[4];                 // [0]: the OAM attribute bits every lifted patron has (CGB 0; DMG OBP1: S_PALETTE); the OBJ palette and the bank bit come from his variant byte (draw_lifted_asm)
static uint8_t mg_live;

// The Chrome Cow, Color (owner 2026-10-31): its empty mug and glass look are the full mug's OBJ palette 1 with the two bit planes swapped,
// kept as copies at the same tile numbers in VRAM bank 1 (OAM attribute bit 3): the shared shards and tip tiles are drawn full at one end of the bar
// and empty at the other, so they cannot be swapped in place. OBJ palette 2 is then unused in the venue. n tiles from id. LCD off.
#define VENUE_CHROME_COW 6
#define OAM_BANK1 0x08
static void swap_bank1(uint8_t id, uint8_t n) {
    const uint8_t *s = (const uint8_t *)(0x8000u + (uint16_t)id * 16u);
    uint8_t *d = (uint8_t *)s, k, a, b;
    for (k = n * 8; k; k--) {
        a = s[0]; b = s[1];
        VBK_REG = VBK_BANK_1; d[0] = b; d[1] = a; VBK_REG = VBK_BANK_0;
        s += 2; d += 2;
    }
    music_pump();
}

// n OBJ tiles src -> dst with the two bit planes swapped (colours 1 and 2 trade places). LCD off.
static void swap_copy(uint8_t src, uint8_t dst, uint8_t n) {
    const uint8_t *s = (const uint8_t *)(0x8000u + (uint16_t)src * 16u);
    uint8_t *d = (uint8_t *)(0x8000u + (uint16_t)dst * 16u), k, a;
    for (k = n * 8; k; k--) { a = s[0]; d[0] = s[1]; d[1] = a; s += 2; d += 2; }
    music_pump();                                        // (the level load runs several frames: the three copies are ~0.55 of one, and the tick due in them was a frame late)
}

// Level load, LCD off, after load_venue / the patron tiles: nobody lifted; CGB the patrons' OBJ palettes (colours 1-3 of
// their BG palettes); DMG OBP1 for the patrons and OBP0 copies for what used OBP1. Sets the mug / glass looks.
void lift_level_init(uint8_t g) BANKED {
    uint8_t v, n, m;
    palette_t p;
    for (v = 0; v < MAX_PATRONS; v++) { patron_lift[v] = LIFT_BG; patron_ovl[v] = 0; lift_pin[v] = 0; }
    ovl_bars = 0; ovl_dirty = 0;
    mg_live = 255;
    for (v = 0; v < NUM_BARS; v++) lift_n[v] = 0;
    lift_total = 0; lift_oam_n = 0; lift_hook_op = HOOK_NONE;
    pal5_cur = 2;                                 // load_venue put the show's palette in slot 5
    lift_prop[0] = S_PALETTE;
    if (is_cgb) {
        lift_prop[0] = 0;
        n = looks_insts(g, INST_OBJ, INST_BG);    // (the Saloon: 5 palette instances, the Factory 5, the others 3; the 5th is OBJ 5, which the show takes from it and gives back, render.c pal5_check)
        m = 0;
        for (v = 0; v < n; v++) {
            m |= 1 << lift_obj[v];
            if (looks_pal_get(g, v, p)) continue; // (the full-mug, empty-mug and show instances: their OBJ 1, 2, 5 hold the venue's own colours already, venue_pals)
            p[0] = 0;
            set_sprite_palette(lift_obj[v], 1, p);
            music_pump();                         // (BRIGHT: ~0.1 frame a palette's lift, LCD off)
        }
        if (n >= 5) for (v = 3; v < 8; v++) if (v != 5 && !(m & (1 << v))) set_sprite_palette(v, 1, p);   // (a generated venue's free OBJ slot, the Stadium's 3: a level start sets it, so no mini-game's colours stay in it)
        if (n < 5) set_sprite_palette(OBJPAL_PATRON_D, 1, p);   // (OBJ 4 is no patron's outside the Saloon and the generated venues: a level start sets it, so no mini-game's or story scene's colours stay in it)
        else if (OBJ5_CHAIN()) pal5_cur = 0;     // (instance 4 is OBJ 5: the patron's, the show's colours above the stage during a show, level.c show_pal5; the Space Lounge's VENUS wears the show's colours, the Zoo's 5th is OBJ 4)
        pal5_req = 0;                                 // (a request of the last level: its colours are not these)
        OBJX_F = 0;                                   // (no show: scratch.h's three-palette state is whatever the last screen left)
        spr_full_t = OBJ_MUG;                spr_full_p = S_PALETTE | OBJPAL_MUG_FULL;
        spr_empty_t = OBJ_MUG + 2;           spr_empty_p = S_PALETTE | OBJPAL_MUG_EMPTY;
        spr_hempty_t = OBJ_MUG_DRINK + 6;    spr_hempty_p = S_PALETTE | OBJPAL_MUG_EMPTY;
        if (venue_id == VENUE_CHROME_COW) {
            swap_bank1(OBJ_MUG, MUG_TILE_COUNT + GLASS_TILE_COUNT);       // the empty mug, the crash (tip, falls, shards)
            swap_bank1(OBJ_MUG_DRINK, MUG_DRINK_TILE_COUNT);              // the empty in a patron's hand
            spr_empty_p = S_PALETTE | OBJPAL_MUG_FULL | OAM_BANK1;
            spr_hempty_p = S_PALETTE | OBJPAL_MUG_FULL | OAM_BANK1;
        }
        return;
    }
    OBP1_REG = OBP1_PLAY;
    swap_copy(OBJ_MUG, OBJ_DMG_COPY, 4);                 // sliding full, sliding empty
    swap_copy((uint8_t)(OBJ_MUG_DRINK + 6), (uint8_t)(OBJ_DMG_COPY + 4), 2);   // the empty in a patron's hand
    spr_full_t = OBJ_DMG_COPY;      spr_full_p = 0;
    spr_empty_t = (uint8_t)(OBJ_DMG_COPY + 2); spr_empty_p = 0;
    spr_hempty_t = (uint8_t)(OBJ_DMG_COPY + 4); spr_hempty_p = 0;
    swap_copy(OBJ_GLASS, OBJ_GLASS, GLASS_TILE_COUNT);   // the crash in place (load_venue reloaded it): looks like the drink
}

static uint8_t col_of(uint8_t p) { return (patron_draw[p] & ~DRAW_BACK) >> 3; }


// Objects on bar b's patron lines (its top 16 lines), counted generously: the bartender's top pair on his bar and his
// bottom pair on the bar below (it covers the heads), the fill glass, every mug (a breaking glass is 2 entries and
// falls 3 lines into the bar below), the coin, and 2 per patron drawn as sprites (one at the left end included: an
// entry at OAM X 0 or 248 shows nothing but still counts on its lines).
static uint8_t ld[NUM_BARS];

// M13b: the per-frame loops are hand-written; an SDCC loop over 16-20 slots costs 5-15 lines whatever it does.
// est_mugs: every mug into ld[] (1, or 2 on its bar and 2 on the next for a breaking glass) and lift_mug_oam.
static void est_mugs(void) __naked {
__asm
    push bc
    ld   hl, #_mug_state
    ld   de, #_mug_bar
    ld   b, #20             ; MAX_MUGS
    ld   c, #0              ; OAM entries
1$:
    ld   a, (hl+)
    or   a, a
    jr   z, 5$
    push hl
    push af                 ; (its state)
    ld   a, (de)
    and  a, #3
    add  a, #<(_ld)
    ld   l, a
    ld   a, #0
    adc  a, #>(_ld)
    ld   h, a               ; &ld[its bar]
    pop  af
    cp   a, #3              ; MUG_BREAKING
    jr   z, 3$
    inc  (hl)
    inc  c
    jr   4$
3$:
    inc  (hl)
    inc  (hl)
    inc  c
    inc  c
    ld   a, (de)
    and  a, #3
    cp   a, #3
    jr   z, 4$
    inc  hl                 ; (it falls into the bar below)
    inc  (hl)
    inc  (hl)
4$:
    pop  hl
5$:
    inc  de
    dec  b
    jr   nz, 1$
    ld   a, c
    ld   (_lift_mug_oam), a
    pop  bc
    ret
__endasm;
}

// scan_nz: the indices i < scan_len with scan_src[i] != 0, into scan_buf (scan_cnt of them).
static const uint8_t *scan_src;
static uint8_t scan_len, scan_cnt, scan_buf[MAX_PATRONS];
static void scan_nz(void) __naked {
__asm
    push bc
    ld   a, (_scan_src)
    ld   l, a
    ld   a, (_scan_src + 1)
    ld   h, a
    ld   de, #_scan_buf
    ld   a, (_scan_len)
    ld   b, a
    ld   c, #0
1$:
    ld   a, (hl+)
    or   a, a
    jr   z, 2$
    ld   a, c
    ld   (de), a
    inc  de
2$:
    inc  c
    dec  b
    jr   nz, 1$
    ld   a, e
    sub  a, #<(_scan_buf)
    ld   (_scan_cnt), a
    pop  bc
    ret
__endasm;
}

// The mugs' part is counted again only when the mugs changed: one more or fewer (mugs_live; a test's poke too), a new
// one or a breaking glass (mug_events, which also catches one gone and one new in the same frame).
static uint8_t mg_ld[NUM_BARS], mg_oam, mg_ev;
static void estimate(void) {
    uint8_t b;
    if (mugs_live != mg_live || mug_events != mg_ev) {
        ld[0] = ld[1] = ld[2] = ld[3] = 0;
        est_mugs();
        mg_ld[0] = ld[0]; mg_ld[1] = ld[1]; mg_ld[2] = ld[2]; mg_ld[3] = ld[3];
        mg_oam = lift_mug_oam; mg_live = mugs_live; mg_ev = mug_events;
    }
    lift_mug_oam = mg_oam;
    ld[0] = mg_ld[0] + (lift_n[0] << 1); ld[1] = mg_ld[1] + (lift_n[1] << 1);
    ld[2] = mg_ld[2] + (lift_n[2] << 1); ld[3] = mg_ld[3] + (lift_n[3] << 1);
    b = bar & (NUM_BARS - 1);
    ld[b] += fill_timer ? 3 : 2;
    if (b < NUM_BARS - 1) ld[b + 1] += 2;
    if (tip_timer) {
        ld[tip_bar & (NUM_BARS - 1)]++;
        if (tip_pocket && TIP2->t) ld[TIP2->bar & (NUM_BARS - 1)]++;    // (the second coin: tip2.h)
    }
}

static uint8_t est_ok;                // the estimate is this frame's (lift_frame computes it only when someone needs it)
static void need_estimate(void) {
    if (est_ok) return;
    estimate();
    est_ok = 1;
}

// Drop p: his BG copy goes back first (at the head of this frame's list when possible); the sprite stays until it
// is on screen (finish_drops).
static void begin_drop(uint8_t p) {
    uint8_t b = patron_bar[p] & (NUM_BARS - 1), c = col_of(p);
    patron_lift[p] |= LIFT_DROP;
    lift_pin[p] = 0;
    ovl_dirty |= bar_bit[b];                              // (the chooser looks at the bar again: he is BG now)
    if (is_cgb) patron_ovl[p] |= OVL_SHARED;              // (until it has: he may stand over another BG patron, and a quick, tiles-only redraw of him would put his tiles over the other's attribute)
    if (!bg_urgent(b, c)) mark_dirty_attrs(b, c, c + 3);
}

// A forced drop: BG copy queued at the head of this frame's list and the sprite gone with the same VBlank, so the
// over-full lines are never drawn. M13c: if this frame's list cannot take it (vq_held: a late frame), the sprite still
// goes now and the BG copy follows with the next list (he is missing for a frame or two): an ordinary drop would keep
// 11 objects on his lines for a frame, and the hardware would then leave out whichever came last in OAM.
static void force_drop(uint8_t p) {
    uint8_t b = patron_bar[p] & (NUM_BARS - 1), c = col_of(p);
    lift_forced++;
    if (is_cgb) patron_ovl[p] |= OVL_SHARED;              // (as begin_drop)
    if (!bg_urgent(b, c)) mark_dirty_attrs(b, c, c + 3);
    patron_lift[p] = LIFT_BG;
    lift_pin[p] = 0;
    ovl_dirty |= bar_bit[b];
    lift_n[b]--;
    lift_total--;
}

// One pass over the patrons drawn as sprites, every frame while there are any: lift_n / lift_total recounted; one who
// has left is forgotten; a drop whose BG copy is on screen ends (the sprite goes this frame); one watching the show (or
// turned to it) drops at once (he turns round on the BG); one clear of every BG patron for LIFT_CLEAR_FRAMES drops
// (lift_busy is the chooser's last look; one lifted by the test hook stays).
static void lifted_one(uint8_t p, uint8_t v) {
    uint8_t b;
    if (patron_state[p] == PATRON_NONE || patron_draw[p] == 255) { patron_lift[p] = LIFT_BG; return; }
    b = patron_bar[p] & (NUM_BARS - 1);
    if (v == LIFT_EDGE) ;                                 // (at the left end: stays a sprite)
    else if (v & LIFT_DROP) {
        if (!vq_held && !bg_pending(p)) { patron_lift[p] = LIFT_BG; ovl_dirty |= bar_bit[b]; return; }
    } else if ((patron_draw[p] & DRAW_BACK) || patron_dist[p]) begin_drop(p);
    else if (!lift_busy[p] && !lift_pin[p]) {
        if (lift_clear[p] < LIFT_CLEAR_FRAMES) lift_clear[p]++;
        else if (patron_x[p] >= ENTRY_X) begin_drop(p);
    }
    lift_n[b]++;
    lift_total++;
}

static uint8_t lo_p;
static void lifted_slow(void) { lifted_one(lo_p, patron_lift[lo_p]); }

// The pass itself (hand-written): the usual cases are counted here (lift_n[bar]++, lift_total++), everything else goes to
// lifted_one: a patron at the left end (LIFT_EDGE, drawn); an ordinary lifted one (not distracted, not in his back view)
// still over a BG patron, pinned by the test hook, or clear for fewer than LIFT_CLEAR_FRAMES frames (lift_clear counts on).
#if LIFT_CLEAR_FRAMES != 8 || MAX_PATRONS != 16 || LIFT_EDGE != 2 || LIFT_DROP != 0x80
#error "lifted_scan: the constants written into the asm"
#endif
static void lifted_scan(void) __naked {
__asm
    push bc
    ld   b, #0              ; b = 0 (add hl, bc), c = slot
    ld   c, #0
    ld   hl, #_patron_lift
1$:
    ld   a, (hl+)
    or   a, a
    jr   z, 8$
    ld   e, a               ; e: his patron_lift
    bit  7, a
    jr   nz, 6$             ; (dropping)
    ld   hl, #_patron_state
    add  hl, bc
    ld   a, (hl)
    or   a, a
    jr   z, 6$              ; (gone)
    ld   hl, #_patron_draw
    add  hl, bc
    ld   a, (hl)
    ld   d, a
    inc  a
    jr   z, 6$              ; (not drawn)
    ld   a, e
    cp   a, #2              ; LIFT_EDGE: stays a sprite
    jr   z, 5$
    bit  7, d
    jr   nz, 6$             ; (back view)
    ld   hl, #_patron_dist
    add  hl, bc
    ld   a, (hl)
    or   a, a
    jr   nz, 6$             ; (watching the show)
    ld   hl, #_lift_bp
    add  hl, bc
    ld   a, (hl)            ; lift_busy
    ld   de, #16            ; lift_pin follows lift_busy (+ 16)
    add  hl, de
    or   a, (hl)
    jr   nz, 5$             ; (over a BG patron, or pinned)
    ld   hl, #_lift_clear
    add  hl, bc
    ld   a, (hl)
    cp   a, #8              ; LIFT_CLEAR_FRAMES
    jr   nc, 6$             ; (time to drop him)
    inc  (hl)
5$:
    ld   hl, #_patron_bar
    add  hl, bc
    ld   a, (hl)
    and  a, #3
    ld   hl, #_lift_n
    add  a, l
    ld   l, a
    jr   nc, 4$
    inc  h
4$:
    inc  (hl)               ; lift_n[his bar]++
    ld   hl, #_lift_total
    inc  (hl)
    jr   7$
6$:
    push bc
    ld   a, c
    ld   (_lo_p), a
    call _lifted_slow
    pop  bc
7$:
    ld   hl, #_patron_lift + 1
    add  hl, bc
8$:
    inc  c
    ld   a, c
    cp   a, #16             ; MAX_PATRONS
    jr   nz, 1$
    pop  bc
    ret
__endasm;
}

static void lifted_pass(void) {
    lift_n[0] = lift_n[1] = lift_n[2] = lift_n[3] = 0;
    lift_total = 0;
    lifted_scan();
}

// A lifted patron of bar b (b = NUM_BARS: any bar), the last slot first; NO_SLOT if none. A lifted one that is not
// dropping first (LIFT_OBJ before one at the left end, LIFT_EDGE, which goes only when there is no other); when every
// sprite of the bar is on its way to the BG already, one of those (a pushed patron who keeps sliding can stay in that
// state for many frames: his BG columns are dirty every frame, so the drop never ends). The sprite of a dropping patron
// is counted on the line like any other, so it has to be able to go when the line is over budget.
static uint8_t pick_lifted(uint8_t b) {
    uint8_t p = MAX_PATRONS, e = NO_SLOT, d = NO_SLOT, v;
    while (p--) {
        v = patron_lift[p];
        if (!v || (b != NUM_BARS && (patron_bar[p] & (NUM_BARS - 1)) != b)) continue;
        if (!LIFT_OFF_BG(v)) { if (d == NO_SLOT) d = p; continue; }
        if (v == LIFT_OBJ) return p;
        e = p;
    }
    return e != NO_SLOT ? e : d;
}

// A forced drop of one at the left end: an entering one wholly on the screen goes to the BG like anyone; one with a part
// still off the screen cannot, so he is taken back (spawned again later) and a leaving one (served already) is gone.
// One already dropping (a pushed patron, a drinker: his BG copy is on its way) only has his sprite taken away.
static void force_out(uint8_t p) {
    if ((patron_lift[p] & LIFT_DROP) || (patron_state[p] != PATRON_LEAVING && (patron_state[p] != PATRON_WALKING || !patron_aux[p]))) {
        force_drop(p);                                    // (anyone on the screen but a leaving one: a pushed patron or a drinker too)
        return;
    }
    if (patron_state[p] == PATRON_WALKING) spawned--;
    else if (patron_state[p] == PATRON_LEAVING) served_done(p);   // (he was served: it counts, off the screen or not)
    lift_forced++;
    remove_patron(p);
    lift_n[patron_bar[p] & (NUM_BARS - 1)]--;
    lift_total--;
}

static void forced_drops(void) {
    uint8_t b, p;
    for (b = 0; b < NUM_BARS; b++)
        while (ld[b] > LINE_OBJ_MAX && (p = pick_lifted(b)) != NO_SLOT) { force_out(p); ld[b] -= 2; }
    // OAM: the mugs keep every entry they need (and OAM_SPARE more for this frame's newcomers)
    while (lift_mug_oam + (lift_total << 1) > MUG_OAM_ALL - OAM_SPARE && (p = pick_lifted(NUM_BARS)) != NO_SLOT)
        force_out(p);
}

// The hook's lift: 0 refused, 1 done, 2 not this frame.
static uint8_t try_lift(uint8_t p, uint8_t mode) {
    uint8_t b = patron_bar[p] & (NUM_BARS - 1), d = patron_draw[p];
    if (patron_state[p] == PATRON_NONE || patron_lift[p] || d == 255 || (d & DRAW_BACK) || patron_dist[p]) return 0;
    if (lift_total >= LIFT_MAX || lift_n[b] >= LIFT_PER_BAR) return 0;
    if (mugs_live + ((lift_total + 1) << 1) > MUG_OAM_ALL - OAM_SPARE) return 0;   // (cheap first: mugs_live <= their entries)
    need_estimate();
    if (lift_total >= LIFT_MAX || lift_n[b] >= LIFT_PER_BAR) return 0;
    if (lift_mug_oam + ((lift_total + 1) << 1) > MUG_OAM_ALL - OAM_SPARE) return 0;
    if (ld[b] + 2 > LINE_OBJ_MAX) return 0;
    if (mode == LIFT_EDGE) mark_dirty_attrs(b, d >> 3, (d >> 3) + 3);   // (no BG footprint: the wall comes back with the
    else if (vq_held || !bg_urgent(b, d >> 3)) return 2;   // usual list) sprite now, BG erased in the same VBlank (old place too)
    patron_lift[p] = mode;
    lift_busy[p] = 1; lift_clear[p] = 0; lift_pin[p] = 0;
    lift_n[b]++;
    lift_total++;
    ld[b] += 2;
    return 1;
}

// A new patron (try_spawn, this frame) is a sprite at the left edge at once (LIFT_EDGE), counted in the budgets like any
// lift (he has nothing on the BG, so this frame's copy list never holds him back). He covers nobody yet (lift_busy 0): at
// ENTRY_X he becomes LIFT_OBJ and drops once clear, by the usual rules. 0: no room now (no spawn).
uint8_t lift_spawn(uint8_t p) BANKED {
    est_ok = 0;                                       // (this frame's estimate: lift_frame has not run yet)
    if (try_lift(p, LIFT_EDGE) != 1) return 0;
    lift_busy[p] = 0;                                 // (no chooser run: a LIFT_EDGE patron changes nobody's flags)
    return 1;
}

// A served patron (patrons.c leaving_step) slides out as a sprite. Lifted already (or being dropped): he only stops
// leaving a BG footprint (his columns are composed again: the wall); 1. On the BG: lifted now like any lift, but his BG
// copy goes with the usual copy list (the sprite covers it exactly meanwhile): 2, he waits until it is out. 0: no room
// (he goes at once).
uint8_t lift_leave(uint8_t p) BANKED {
    uint8_t b = patron_bar[p] & (NUM_BARS - 1), c = col_of(p);
    if (patron_ovl[p]) ovl_dirty |= bar_bit[b];               // (he shared columns with a BG patron: their flags change)
    if (patron_lift[p]) {
        patron_lift[p] = LIFT_EDGE;
        mark_dirty_attrs(b, c, c + 3);
        return 1;
    }
    est_ok = 0;
    if (try_lift(p, LIFT_EDGE) != 1) return 0;
    lift_busy[p] = 0;
    return 2;
}

static void hook(void) {
    uint8_t p = lift_hook_p & (MAX_PATRONS - 1), r;
    if (lift_hook_op == HOOK_DROP) {
        if (!LIFT_OFF_BG(patron_lift[p])) r = 0;
        else { begin_drop(p); r = 1; }
    } else {
        r = try_lift(p, LIFT_OBJ);
        if (r == 1) lift_pin[p] = 1;
    }
    if (r == 2) return;                                   // try again next frame
    lift_hook_res = r ? RES_DONE : RES_REFUSED;
    lift_hook_op = HOOK_NONE;
}

extern uint8_t bar_list[NUM_BARS][MAX_PATRONS], bar_n[NUM_BARS];
void build_lists(void);

// M13b: p changed columns (or between 2 and 3 real columns): the chooser (lift.c) looks at his bar if his footprint
// (3 columns, 2 in a back view) meets another patron's, if he had overlap flags, or if someone on the bar is lifted
// (whether that one still covers a BG patron may change). A lone patron costs the chooser nothing.
void ovl_touch(uint8_t p) BANKED {
    const uint8_t *q;
    uint8_t b = patron_bar[p] & (NUM_BARS - 1), n, s, d, c, e;
    if (patron_ovl[p] | lift_n[b]) goto dirty;
    d = patron_draw[p];
    c = (d & ~DRAW_BACK) >> 3;
    e = c + ((d & DRAW_BACK) ? 2 : 3);
    if (!lists_ok) build_lists();
    q = bar_list[b];
    for (n = bar_n[b]; n; n--) {
        s = *q++;
        if (s == p || (d = patron_draw[s]) == 255 || patron_state[s] == PATRON_NONE) continue;
        if (((d & ~DRAW_BACK) >> 3) < e && c < ((d & ~DRAW_BACK) >> 3) + ((d & DRAW_BACK) ? 2 : 3)) goto dirty;
    }
    return;
dirty:
    ovl_dirty |= bar_bit[b];
}

// ---- M13b: the chooser ------------------------------------------------------------------------------------------------

// The bar's drawn patrons as 4-byte records sorted by first column: [0] first column c, [1] end of his real columns
// (c + 2 at shift 0 and in a back view, else c + 3), [2] end of his footprint (c + 3; c + 2 in a back view), [3] slot |
// his patron_ovl flags (3 bits) before this pass << 4 | REC_OBJ when he is drawn as a sprite (lifted, not dropping). Walked with
// pointers: SDCC indexes arrays slowly.
#define REC_OBJ  0x80
#define REC_SLOT 0x0F
static uint8_t rec[MAX_PATRONS * 4];
static uint8_t *rec_end;
static uint8_t g_bar, g_c, g_d, g_o;  // gather_asm's bar, and the column / drawn x / old flags of the patron being filed

#if !ASM_CHOOSER
// Hand-written (the C version cost ~5 DIV ticks a patron, and the chooser runs whenever a patron changes columns):
// for each live slot s in bar_list[g_bar]: patron_ovl[s] = 0; if drawn, file his record into rec[] (insertion sort by
// column; see above), rec_end after the last one. bar_list must be current (gather() rebuilds it first).
static void gather_asm(void) __naked {
__asm
    push bc
    ld   hl, #_rec_end
    ld   a, #<(_rec)
    ld   (hl+), a
    ld   (hl), #>(_rec)
    ld   a, (_g_bar)
    ld   c, a
    swap a                  ; b * 16 (b < 4): the bar list
    add  a, #<(_bar_list)
    ld   l, a
    ld   a, #0
    adc  a, #>(_bar_list)
    ld   h, a
    push hl                 ; [sp]: q, the next list entry
    ld   hl, #_bar_n
    ld   a, l
    add  a, c
    ld   l, a
    jr   nc, 1$
    inc  h
1$:
    ld   b, (hl)            ; b: entries left
2$:
    ld   a, b
    or   a, a
    jp   z, 9$
    dec  b
    pop  hl
    ld   a, (hl+)           ; s
    push hl
    ld   c, a               ; c: s
    ld   hl, #_patron_state
    add  a, l
    ld   l, a
    jr   nc, 3$
    inc  h
3$:
    ld   a, (hl)
    or   a, a
    jr   z, 2$              ; (PATRON_NONE)
    ld   hl, #_patron_ovl
    ld   a, l
    add  a, c
    ld   l, a
    jr   nc, 4$
    inc  h
4$:
    ld   a, (hl)
    and  a, #7
    swap a
    ld   (_g_o), a          ; his flags so far, for [3] bits 4-6
    xor  a, a
    ld   (hl), a            ; patron_ovl[s] = 0
    ld   hl, #_patron_draw
    ld   a, l
    add  a, c
    ld   l, a
    jr   nc, 5$
    inc  h
5$:
    ld   a, (hl)
    cp   a, #0xFF
    jr   z, 2$              ; (not drawn yet)
    ld   (_g_d), a
    rrca
    rrca
    rrca
    and  a, #0x0F           ; his first column ((d & 0x7F) >> 3, < 16)
    ld   (_g_c), a
    ld   a, (_rec_end)
    ld   l, a
    ld   a, (_rec_end + 1)
    ld   h, a               ; hl: where his record goes, moving down past bigger columns
6$:
    ld   a, l
    cp   a, #<(_rec)
    jr   nz, 7$
    ld   a, h
    cp   a, #>(_rec)
    jr   z, 8$              ; (at the start)
7$:
    ld   d, h
    ld   e, l               ; de: r
    dec  hl
    dec  hl
    dec  hl
    dec  hl                 ; hl: r - 4
    ld   a, (_g_c)
    cp   a, (hl)
    jr   nc, 10$            ; r[-4] <= c: his place is r
    push hl
    ld   a, (hl+)           ; r[0..3] = r[-4..-1]
    ld   (de), a
    inc  de
    ld   a, (hl+)
    ld   (de), a
    inc  de
    ld   a, (hl+)
    ld   (de), a
    inc  de
    ld   a, (hl)
    ld   (de), a
    pop  hl
    jr   6$
10$:
    ld   h, d
    ld   l, e
8$:
    ld   a, (_g_c)
    ld   (hl+), a           ; [0] c
    ld   e, a
    ld   a, (_g_d)
    and  a, #7
    ld   a, e
    jr   z, 11$
    inc  a
11$:
    add  a, #2
    ld   (hl+), a           ; [1] c + 2 (shift 0, back view) or c + 3
    ld   a, (_g_d)
    rlca
    ld   a, e
    jr   c, 12$
    inc  a
12$:
    add  a, #2
    ld   (hl+), a           ; [2] c + 2 (back view) or c + 3
    push hl
    ld   hl, #_patron_lift
    ld   a, l
    add  a, c
    ld   l, a
    jr   nc, 13$
    inc  h
13$:
    ld   a, (hl)
    pop  hl
    dec  a
    cp   a, #2              ; LIFT_OFF_BG: 1 or 2
    ld   a, c
    jr   nc, 14$
    or   a, #0x80           ; REC_OBJ
14$:
    ld   e, a
    ld   a, (_g_o)
    or   a, e
    ld   (hl), a            ; [3] s | old flags << 4 (| REC_OBJ)
    ld   hl, #_rec_end
    ld   a, (hl)
    add  a, #4
    ld   (hl+), a
    jp   nc, 2$
    inc  (hl)
    jp   2$
9$:
    pop  hl
    pop  bc
    ret
__endasm;
}

static void gather(uint8_t b) {
    if (!lists_ok) build_lists();
    g_bar = b;
    gather_asm();
}

#endif

#if !ASM_CHOOSER
// Who goes up first when two BG patrons share a column: pushed 4, hurried walker 3, walker 2, drinker 1; 0: may not be
// lifted (watching the show or turning to it, in his back view, or being dropped).
static uint8_t prio(uint8_t s) {
    uint8_t st;
    if (patron_lift[s] || patron_dist[s] || (patron_draw[s] & DRAW_BACK)) return 0;
    st = patron_state[s];
    if (st == PATRON_PUSHED) return 4;
    if (st == PATRON_WALKING) return 2 + patron_hurry[s];
    return 1;
}

#endif
static uint8_t ch_retry;              // this bar's lift has to wait: 2 next frame, 1 later (budgets; see lift_frame)
static uint8_t ch_bit;                // the bar's bit
#define RETRY_FRAMES 16
#define CHOOSER_LY_LATE 56    // ... and one that has reached this one at none (an overloaded frame: next frame) ...
#define CHOOSER_LATE_MAX 4    // ... but not for more than this many frames in a row
static uint8_t ch_late;       // frames in a row the chooser left everything for later
static uint8_t retry_wait[NUM_BARS];  // frames until a budget-refused bar is looked at again

#if !ASM_CHOOSER
// Records a (left) and r share a real column: lift the one with the higher priority (ties: r, the one further right).
// Returns the record that stays on the BG and goes on as "the last one", or 0 when both stay (the fallback).
static uint8_t *conflict(uint8_t *a, uint8_t *r) {
    uint8_t pa = prio(a[3] & REC_SLOT), pr = prio(r[3] & REC_SLOT), *x, k;
    x = pr >= pa ? r : a;
    if (pa | pr) {
        k = try_lift(x[3] & REC_SLOT, LIFT_OBJ);
        if (k == 1) {
            x[3] |= REC_OBJ;
            lift_lifts++;
            return x == a ? r : a;
        }
        if (k == 2) ch_retry = 2;                         // (not this frame: the copy list / his BG copy)
        else if (!ch_retry) ch_retry = 1;                 // (the budgets: later)
    }
    patron_ovl[x[3] & REC_SLOT] |= OVL_TOP;               // both stay on the BG: the would-be lifted one covers the other
    ovl_bars |= ch_bit;
    return 0;
}

#endif

// The chooser's loops, hand-written (in C they cost ~30 DIV ticks a bar). C helpers for the rare steps, called with
// their arguments in globals.
static uint8_t *ch_l, *ch_r, *ch_x;   // conflict(): the last BG record, this one, the one that stays (0: both)
static uint8_t ch_b, s_r, s_x, md_x0, md_x1;
#if !ASM_CHOOSER
static void conflict_g(void) { ch_x = conflict(ch_l, ch_r); }
static void shared_pair(void) {       // r and x share real columns (both on the BG): the covered one(s) lose quick redraws
    uint8_t a = patron_ovl[s_r], c = patron_ovl[s_x];
    if (!(a & OVL_TOP)) patron_ovl[s_r] = a | OVL_SHARED;
    if (!(c & OVL_TOP) || (a & OVL_TOP)) patron_ovl[s_x] = c | OVL_SHARED;
}
#endif
// (Glitch hunt 2026-11-01: with the attributes. A patron whose OVL flags change is composed again, 2 columns (his 3rd stays wall, attribute too) one way and
// 3 the other; tiles alone left the 3rd column's attribute the wall's after the flags cleared, and his next 1 px step (a quick, tiles-only redraw) put his tile
// on it: a column of his body in the wall's palette until he next changed columns.)
static void md_g(void) { mark_dirty_attrs(ch_b, md_x0, md_x1); }

// Bar b: lift so that the BG patrons are column-disjoint (greedy, left to right), flag the pairs that stay on the BG,
// and note which lifted patrons still cover a BG one. ASM_CHOOSER (asm_cfg.h): the whole function is hand-written; the #else is the
// version before it (the gather and the three steps of choose_asm were already asm, the busy loop and conflict() C), the reference and the
// C build's. Both make the same decisions, whatever the state: the same changes to patron_ovl / patron_lift / lift_busy / lift_clear /
// lift_n / lift_total / lift_lifts / ovl_bars / ch_retry and to the dirty spans (tests/test_chooser_trace.py runs ~700 states of crowded
// scenes and random bars against the changes the old version made). The statics g_*, ch_*, s_*, md_* and rec are scratch, dead after the call.
// Measured on 6000 calls from the ARCADE peaks and CLASSIC 16 (T-cycles, tests/asm_rig.py): the old version 9.7k a call, this asm 6.4k;
// the cost is the gather (a patron: 4 array reads and his record, ~500 T), the passes over the records, the conflicts (~1.2k each, 3/4 of
// the calls have one: a pair that stays) and the lifted ones' busy flags.
#if ASM_CHOOSER
#if MAX_PATRONS != 16 || NUM_BARS != 4 || DRAW_BACK != 0x80 || OVL_SHARED != 1 || OVL_TOP != 2 || OVL_TWO != 4 || LIFT_OBJ != 1 || LIFT_EDGE != 2 || LIFT_MAX != 4 || LIFT_PER_BAR != 2 || REC_OBJ != 0x80 || REC_SLOT != 0x0F || (MUG_OAM_ALL - OAM_SPARE) != 19
#error "choose_bar: the constants written into the asm"
#endif
typedef char choose_enums[(PATRON_NONE == 0 && PATRON_WALKING == 1 && PATRON_PUSHED == 2) ? 1 : -1];
// Records here are { f, c, e1, e2 } (the old version's, above: { c, e1, e2, f }): f = slot | his old flags << 4 | REC_OBJ, c his first column, e1 the end of his real columns,
// e2 the end of his footprint; rec_end is only written once the bar is gathered. Scratch: g_bar (the list's end), g_o / g_c / g_d (an
// insertion), md_x0 (the largest column filed so far, then the span for md_g), ch_x[0] (the bar has lifted patrons: their busy flags
// are looked at), ch_x[1] (some patron_ovl was set this run: step 3 must read them; else they are all 0).
static void choose_bar(uint8_t b) __naked {
    (void)b;
__asm
    push bc
    ld   (_ch_b), a
    ld   c, a
    ld   b, #0
    ld   a, (_lists_ok)
    or   a, a
    jr   nz, 1$
    push bc
    call _build_lists
    pop  bc
1$:
    ld   hl, #_bar_bit
    add  hl, bc
    ld   a, (hl)
    ld   (_ch_bit), a
    cpl
    ld   hl, #_ovl_bars
    and  a, (hl)
    ld   (hl), a                ; ovl_bars &= ~bar_bit[b]
    xor  a, a
    ld   (_ch_retry), a
    ld   (_md_x0), a
    ld   (_ch_x + 1), a
    ld   a, c
    swap a                      ; 16 * b
    add  a, #<(_bar_list)
    ld   e, a
    ld   a, #>(_bar_list)
    adc  a, #0
    ld   d, a
    ld   hl, #_bar_n
    add  hl, bc
    ld   a, (hl)
    add  a, e
    ld   (_g_bar), a            ; where the list ends (low byte: 16 bytes, so it is unique)
    push de                     ; the next list entry
    ld   hl, #_rec_end
    ld   a, #<(_rec)
    ld   (hl+), a
    ld   (hl), #>(_rec)
2$:                             ; ---- gather: next slot of the list
    pop  hl
    ld   a, (_g_bar)
    cp   a, l
    jp   z, 20$
    ld   a, (hl+)
    push hl
    ld   c, a                   ; c = s
    ld   hl, #_patron_state
    add  hl, bc
    ld   a, (hl)
    or   a, a
    jr   z, 2$                  ; (PATRON_NONE)
    ld   hl, #_patron_ovl
    add  hl, bc
    ld   a, (hl)
    ld   (hl), b                ; patron_ovl[s] = 0
    and  a, #7
    swap a
    or   a, c
    ld   e, a                   ; e = s | his flags so far << 4
    ld   hl, #_patron_draw
    add  hl, bc
    ld   a, (hl)
    cp   a, #0xFF
    jr   z, 2$                  ; (not drawn yet)
    ld   d, a                   ; d = his drawn x
    ld   hl, #_patron_lift
    add  hl, bc
    ld   a, (hl)
    dec  a
    cp   a, #2
    jr   nc, 3$                 ; (LIFT_OFF_BG: 1 or 2: drawn as a sprite)
    set  7, e                   ; REC_OBJ
3$:
    ld   a, d
    rrca
    rrca
    rrca
    and  a, #0x0F               ; his first column ((d & 0x7F) >> 3)
    ld   c, a
    ld   hl, #_md_x0
    cp   a, (hl)
    jr   c, 10$                 ; before the last one filed: insertion
    ld   (hl), a
    ld   hl, #_rec_end          ; at the end
    ld   a, (hl+)
    ld   h, (hl)
    ld   l, a
    ld   a, e
    ld   (hl+), a               ; [0] f
    ld   a, c
    ld   (hl+), a               ; [1] c
    ld   a, d
    and  a, #7
    ld   a, c
    jr   z, 4$
    inc  a
4$:
    add  a, #2
    ld   (hl+), a               ; [2] e1: c + 2 (shift 0) or c + 3
    ld   a, d
    rlca
    ld   a, c
    jr   c, 5$
    inc  a
5$:
    add  a, #2
    ld   (hl+), a               ; [3] e2: c + 2 (back view) or c + 3
    ld   a, l
    ld   (_rec_end), a
    ld   a, h
    ld   (_rec_end + 1), a
    jp   2$
10$:                            ; insertion: the records with a bigger column move up by one place
    ld   a, e
    ld   (_g_o), a
    ld   a, c
    ld   (_g_c), a
    ld   a, d
    ld   (_g_d), a
    ld   hl, #_rec_end
    ld   a, (hl)
    ld   e, a
    add  a, #4
    ld   (hl+), a
    ld   d, (hl)
    jr   nc, 11$
    inc  (hl)
11$:
    ld   h, d
    ld   l, e                   ; hl = r = the old end
    ld   a, (_g_c)
    ld   b, a                   ; b = c (b is 0 again below)
12$:
    ld   a, l
    cp   a, #<(_rec)
    jr   nz, 13$
    ld   a, h
    cp   a, #>(_rec)
    jr   z, 15$                 ; at the start
13$:
    ld   d, h
    ld   e, l                   ; de = r
    dec  hl
    dec  hl
    dec  hl
    dec  hl                     ; hl = r - 4
    inc  hl
    ld   a, b
    cp   a, (hl)                ; c - r[-4].c
    dec  hl
    jr   nc, 14$                ; r[-4].c <= c: his place is r
    ld   a, (hl+)               ; r[0..3] = r[-4..-1]
    ld   (de), a
    inc  de
    ld   a, (hl+)
    ld   (de), a
    inc  de
    ld   a, (hl+)
    ld   (de), a
    inc  de
    ld   a, (hl)
    ld   (de), a
    dec  hl
    dec  hl
    dec  hl
    jr   12$
14$:
    ld   h, d
    ld   l, e
15$:
    ld   b, #0
    ld   a, (_g_o)
    ld   (hl+), a
    ld   a, (_g_c)
    ld   (hl+), a
    ld   a, (_g_d)
    and  a, #7
    ld   a, (_g_c)
    jr   z, 16$
    inc  a
16$:
    add  a, #2
    ld   (hl+), a
    ld   a, (_g_d)
    rlca
    ld   a, (_g_c)
    jr   c, 17$
    inc  a
17$:
    add  a, #2
    ld   (hl), a
    jp   2$
20$:                            ; ---- gathered: b = the number of records
    ld   a, (_rec_end)
    sub  a, #<(_rec)
    srl  a
    srl  a                      ; (the low byte of the difference is exact: at most 64)
    jr   z, 29$
    cp   a, #1
    jr   z, 21$
    ld   b, a
    jp   30$
21$:                            ; one patron: nothing to share
    ld   a, (_rec)
    bit  7, a
    jr   z, 22$
    and  a, #0x0F
    add  a, #<(_lift_bp)
    ld   l, a
    ld   a, #>(_lift_bp)
    adc  a, #0
    ld   h, a
    ld   (hl), #0               ; lift_busy[s] = 0
    ld   a, (_rec)
22$:
    and  a, #0x70
    jr   z, 29$
    ld   a, (_rec + 1)
    ld   (_md_x0), a
    ld   a, (_rec + 3)
    ld   (_md_x1), a
    call _md_g                  ; (his old flags are gone: his columns are composed again)
29$:
    pop  bc
    ret
30$:                            ; ---- 1. greedy: hl = r, b = records left, de = l, c = where l's real columns end (0: no BG record yet)
    ld   hl, #_rec
    ld   c, #0
31$:
    ld   a, (hl)
    bit  7, a
    jr   nz, 38$                ; (lifted: not on the BG)
    inc  hl
    ld   a, (hl)                ; r.c
    cp   a, c
    jr   c, 35$                 ; r.c < l.e1: a real column is shared
    ld   d, h                   ; l = r
    ld   e, l
    dec  de
    inc  hl
    ld   c, (hl)                ; c = r.e1
    inc  hl
    inc  hl                     ; the next record
    dec  b
    jr   nz, 31$
    jr   40$
38$:
    inc  hl
    inc  hl
    inc  hl
    inc  hl
    dec  b
    jr   nz, 31$
    jr   40$
35$:                            ; conflict(l, r)
    dec  hl                     ; hl = r
    push bc
    push hl
    push de
    call _cb_conf               ; de = the one that stays on the BG, 0: both
    pop  hl                     ; hl = l
    ld   a, d
    or   a, e
    jr   z, 37$
    pop  hl                     ; hl = r
    pop  bc                     ; b = records left
    inc  hl
    inc  hl
    inc  hl
    inc  hl
    inc  de
    inc  de
    ld   a, (de)
    dec  de
    dec  de
    ld   c, a                   ; l = the one that stays: c = his e1
    dec  b
    jr   nz, 31$
    jr   40$
37$:                            ; both stay: go on from the one reaching further right
    ld   d, h
    ld   e, l                   ; de = l
    pop  hl                     ; hl = r
    pop  bc                     ; b = records left, c = l.e1
    inc  hl
    inc  hl
    ld   a, (hl)                ; r.e1
    dec  hl
    dec  hl
    cp   a, c
    jr   c, 38$
    jr   z, 38$                 ; r.e1 <= l.e1: l goes on
    ld   c, a
    ld   d, h
    ld   e, l                   ; l = r
    jr   38$
40$:                            ; ---- 2. and 3.: hl = r, b = records left
    ld   a, (_ch_b)
    ld   e, a
    ld   d, #0
    ld   hl, #_lift_n
    add  hl, de
    ld   a, (hl)
    ld   (_ch_x), a             ; (someone of the bar is lifted: the busy flags are looked at)
    ld   a, (_rec_end)
    sub  a, #<(_rec)
    srl  a
    srl  a
    ld   b, a
    ld   hl, #_rec
41$:
    ld   a, (hl)
    bit  7, a
    jp   nz, 60$                ; (r lifted)
    ld   a, b
    cp   a, #1
    jp   z, 55$                 ; (the last record: nobody after him)
    push hl                     ; r
    ld   a, (hl)
    and  a, #0x0F
    ld   (_s_r), a
    inc  hl
    inc  hl
    ld   d, (hl)                ; d = r.e1
    inc  hl
    ld   e, (hl)                ; e = r.e2
    inc  hl                     ; hl = x = r + 4
    ld   a, b
    dec  a
    ld   c, a                   ; c = records after r
42$:                            ; hl = x
    inc  hl
    ld   a, (hl)                ; x.c
    cp   a, e
    jr   nc, 54$                ; x.c >= r.e2: no later record meets r (sorted)
    dec  hl
    ld   a, (hl)                ; x.f
    bit  7, a
    jr   nz, 45$                ; (x lifted)
    and  a, #0x0F
    ld   (_s_x), a
    inc  hl
    ld   a, (hl)                ; x.c
    dec  hl
    cp   a, d                   ; x.c - r.e1
    jr   nc, 46$                ; r.e1 <= x.c: only the empty column of r meets x
    push hl                     ; shared_pair(s_r, s_x): the covered one(s) lose quick redraws
    push de
    push bc
    ld   hl, #_patron_ovl
    ld   a, (_s_r)
    add  a, l
    ld   l, a
    jr   nc, 47$
    inc  h
47$:
    ld   e, (hl)                ; e = a: patron_ovl[s_r]
    push hl
    ld   hl, #_patron_ovl
    ld   a, (_s_x)
    add  a, l
    ld   l, a
    jr   nc, 48$
    inc  h
48$:
    ld   d, (hl)                ; d = c: patron_ovl[s_x]
    bit  1, d
    jr   z, 49$                 ; (c has no OVL_TOP)
    bit  1, e
    jr   z, 50$                 ; (c has it, a has not)
49$:
    ld   a, d
    or   a, #1
    ld   (hl), a                ; patron_ovl[s_x] = c | OVL_SHARED
50$:
    pop  hl
    bit  1, e
    jr   nz, 51$
    ld   a, e
    or   a, #1
    ld   (hl), a                ; patron_ovl[s_r] = a | OVL_SHARED
51$:
    ld   a, #1
    ld   (_ch_x + 1), a
    pop  bc
    pop  de
    pop  hl
    jr   45$
46$:
    push hl
    ld   hl, #_patron_ovl
    ld   a, (_s_r)
    add  a, l
    ld   l, a
    jr   nc, 52$
    inc  h
52$:
    ld   a, (hl)
    or   a, #5                  ; OVL_SHARED | OVL_TWO
    ld   (hl), a
    ld   a, #1
    ld   (_ch_x + 1), a
    pop  hl
45$:
    inc  hl
    inc  hl
    inc  hl
    inc  hl
    dec  c
    jr   nz, 42$
54$:
    pop  hl                     ; hl = r
55$:                            ; 3. his flags changed? hl = r
    ld   a, (_ch_x + 1)
    or   a, a
    ld   a, (hl)
    jr   nz, 56$
    and  a, #0x70               ; (no flag was set: patron_ovl are all 0)
    jr   z, 59$
    jr   57$
56$:
    ld   e, a                   ; e = f
    swap a
    and  a, #7
    ld   d, a                   ; d = his flags before this pass
    push hl
    ld   hl, #_patron_ovl
    ld   a, e
    and  a, #0x0F
    add  a, l
    ld   l, a
    jr   nc, 58$
    inc  h
58$:
    ld   a, (hl)
    pop  hl
    cp   a, d
    jr   z, 59$
57$:
    inc  hl
    ld   a, (hl)                ; r.c
    ld   (_md_x0), a
    inc  hl
    inc  hl
    ld   a, (hl)                ; r.e2
    ld   (_md_x1), a
    dec  hl
    dec  hl
    dec  hl
    push bc
    push hl
    call _md_g
    pop  hl
    pop  bc
59$:
    inc  hl
    inc  hl
    inc  hl
    inc  hl
    dec  b
    jp   nz, 41$
    jp   29$
60$:                            ; r is lifted: still over a BG record? (only when the bar has lifted patrons)
    ld   a, (_ch_x)
    or   a, a
    jr   z, 55$
    push hl
    push bc
    inc  hl
    ld   b, (hl)                ; b = r.c
    inc  hl
    ld   h, (hl)                ; h = r.e1
    ld   a, (_rec_end)
    sub  a, #<(_rec)
    srl  a
    srl  a
    ld   c, a                   ; c = records
    ld   de, #_rec
62$:
    ld   a, (de)
    inc  de
    bit  7, a
    jr   nz, 64$                ; (x lifted)
    ld   a, (de)                ; x.c
    cp   a, h
    jr   nc, 64$                ; x.c >= r.e1
    inc  de
    ld   a, (de)                ; x.e1
    dec  de
    cp   a, b
    jr   c, 64$
    jr   z, 64$                 ; x.e1 <= r.c
    ld   a, #1                  ; busy
    jr   68$
64$:
    inc  de
    inc  de
    inc  de
    dec  c
    jr   nz, 62$
    xor  a, a
68$:
    ld   e, a                   ; e = busy
    pop  bc
    pop  hl
    ld   a, (hl)
    and  a, #0x0F
    ld   d, a                   ; d = slot
    push hl
    add  a, #<(_lift_bp)
    ld   l, a
    ld   a, #>(_lift_bp)
    adc  a, #0
    ld   h, a
    ld   (hl), e                ; lift_busy[s] = busy
    ld   a, e
    or   a, a
    jr   z, 69$
    ld   a, d
    add  a, #<(_lift_clear)
    ld   l, a
    ld   a, #>(_lift_clear)
    adc  a, #0
    ld   h, a
    ld   (hl), #0               ; lift_clear[s] = 0
69$:
    pop  hl
    jp   55$
; ---- the priority of slot e (d = 0) in a (pushed 4, hurried walker 3, walker 2, drinker 1; 0: may not be lifted); clobbers hl
_cb_prio:
    ld   hl, #_patron_lift
    add  hl, de
    ld   a, (hl)
    or   a, a
    jr   nz, 2$
    ld   hl, #_patron_dist
    add  hl, de
    ld   a, (hl)
    or   a, a
    jr   nz, 2$
    ld   hl, #_patron_draw
    add  hl, de
    bit  7, (hl)
    jr   nz, 2$
    ld   hl, #_patron_state
    add  hl, de
    ld   a, (hl)
    cp   a, #2                  ; PATRON_PUSHED
    jr   z, 3$
    cp   a, #1                  ; PATRON_WALKING
    ld   a, #1
    ret  nz
    ld   hl, #_patron_hurry
    add  hl, de
    ld   a, (hl)
    add  a, #2
    ret
3$:
    ld   a, #4
    ret
2$:
    xor  a, a
    ret
; ---- conflict(l, r): hl = r, de = l (records); de = the record that stays on the BG, 0: both stay. As the C conflict().
_cb_conf:
    push hl
    push de
    ld   a, (de)
    and  a, #0x0F
    ld   e, a
    ld   d, #0
    call _cb_prio
    ld   b, a                   ; b = pa
    pop  de
    pop  hl
    push hl
    push de
    ld   a, (hl)
    and  a, #0x0F
    ld   e, a
    ld   d, #0
    call _cb_prio
    ld   c, a                   ; c = pr
    pop  de
    pop  hl
    ld   a, c
    cp   a, b
    jr   nc, 1$                 ; pr >= pa: x = r
    ld   a, h                   ; else x = l: hl = l, de = r
    ld   h, d
    ld   d, a
    ld   a, l
    ld   l, e
    ld   e, a
1$:                             ; hl = x (the one to lift), de = the other
    ld   a, b
    or   a, c
    jr   z, 5$                  ; (neither may be lifted)
    ld   a, (_lift_total)       ; try_lift's first refusals, here: the budgets (a lift of x passes its other tests: prio > 0)
    cp   a, #4                  ; LIFT_MAX
    jr   nc, 4$
    ld   a, (_ch_b)
    ld   c, a
    ld   b, #0
    push hl
    ld   hl, #_lift_n
    add  hl, bc
    ld   a, (hl)
    pop  hl
    cp   a, #2                  ; LIFT_PER_BAR
    jr   nc, 4$
    ld   a, (_lift_total)
    inc  a
    add  a, a
    ld   c, a
    ld   a, (_mugs_live)
    add  a, c
    jr   c, 4$
    cp   a, #20                 ; mugs_live + ((lift_total + 1) << 1) > 19
    jr   nc, 4$
    push hl                     ; the rest of try_lift
    push de
    ld   a, (hl)
    and  a, #0x0F
    ld   e, #1                  ; LIFT_OBJ
    call _try_lift
    pop  de
    pop  hl
    cp   a, #1
    jr   z, 6$
    cp   a, #2
    jr   nz, 4$
    ld   a, #2                  ; (not this frame: the copy list / his BG copy)
    ld   (_ch_retry), a
    jr   5$
4$:
    ld   a, (_ch_retry)         ; (the budgets: later)
    or   a, a
    jr   nz, 5$
    ld   a, #1
    ld   (_ch_retry), a
5$:                             ; both stay on the BG: the would-be lifted one covers the other
    ld   a, (hl)
    and  a, #0x0F
    add  a, #<(_patron_ovl)
    ld   l, a
    ld   a, #>(_patron_ovl)
    adc  a, #0
    ld   h, a
    ld   a, (hl)
    or   a, #2                  ; OVL_TOP
    ld   (hl), a
    ld   a, (_ch_bit)
    ld   hl, #_ovl_bars
    or   a, (hl)
    ld   (hl), a
    ld   a, #1
    ld   (_ch_x + 1), a
    ld   de, #0
    ret
6$:                             ; lifted
    set  7, (hl)                ; REC_OBJ
    ld   hl, #_lift_lifts
    inc  (hl)
    ret
__endasm;
}
#else
// 1. Greedy, left to right: a BG record r sharing a real column with the last BG one l is a conflict (conflict()
//    lifts one of them, or flags the pair). 2. BG footprints that meet (r left of x): the covered one of a pair loses
//    quick redraws (shared_pair); when only r's empty 3rd column lies on x's figure, r gets OVL_SHARED | OVL_TWO.
// 3. A record whose flags changed: his columns are composed again.
static void choose_asm(void) __naked {
__asm
    push bc
    ld   hl, #_rec          ; r
    ld   de, #0             ; l (0: none yet)
10$:                        ; ---- 1. greedy
    ld   a, (_rec_end)
    cp   a, l
    jr   nz, 11$
    ld   a, (_rec_end + 1)
    cp   a, h
    jr   z, 19$
11$:
    inc  hl
    inc  hl
    inc  hl
    bit  7, (hl)            ; r[3] & REC_OBJ (lifted: not on the BG)
    dec  hl
    dec  hl
    dec  hl
    jr   nz, 18$
    ld   a, d
    or   a, e
    jr   z, 17$             ; (the first BG one)
    inc  de
    ld   a, (de)            ; l[1]
    dec  de
    ld   c, a
    ld   a, (hl)            ; r[0]
    cp   a, c
    jr   nc, 17$            ; r[0] >= l[1]: no real column shared
    push hl
    ld   a, e
    ld   (_ch_l), a
    ld   a, d
    ld   (_ch_l + 1), a
    ld   a, l
    ld   (_ch_r), a
    ld   a, h
    ld   (_ch_r + 1), a
    call _conflict_g
    pop  hl
    ld   a, (_ch_x)
    ld   e, a
    ld   a, (_ch_x + 1)
    ld   d, a
    or   a, e
    jr   nz, 18$            ; l = the one that stays on the BG
    ld   a, (_ch_l)         ; both stay: go on from the one reaching further right
    ld   e, a
    ld   a, (_ch_l + 1)
    ld   d, a
    inc  hl
    ld   c, (hl)            ; r[1]
    dec  hl
    inc  de
    ld   a, (de)            ; l[1]
    dec  de
    cp   a, c
    jr   nc, 18$
17$:
    ld   d, h
    ld   e, l               ; l = r
18$:
    ld   bc, #4
    add  hl, bc
    jr   10$
19$:
    ld   hl, #_rec          ; ---- 2. footprints that meet: r = hl, x = de
20$:
    ld   a, (_rec_end)
    cp   a, l
    jr   nz, 21$
    ld   a, (_rec_end + 1)
    cp   a, h
    jp   z, 39$
21$:
    ld   a, l
    add  a, #3
    ld   e, a
    ld   a, h
    adc  a, #0
    ld   d, a               ; de = r + 3
    ld   a, (de)
    bit  7, a
    jp   nz, 29$            ; (r lifted)
    and  a, #0x0F
    ld   (_s_r), a
    inc  de                 ; x = r + 4
22$:
    ld   a, (_rec_end)
    cp   a, e
    jr   nz, 23$
    ld   a, (_rec_end + 1)
    cp   a, d
    jr   z, 29$
23$:
    ld   a, (de)            ; x[0]
    ld   c, a
    inc  hl
    inc  hl
    ld   a, (hl)            ; r[2]
    dec  hl
    dec  hl
    cp   a, c
    jr   c, 29$             ; x[0] >= r[2]: no later record meets r (sorted)
    jr   z, 29$
    inc  de
    inc  de
    inc  de
    ld   a, (de)            ; x[3]
    dec  de
    dec  de
    dec  de
    bit  7, a
    jr   nz, 28$            ; (x lifted)
    and  a, #0x0F
    ld   (_s_x), a
    inc  hl
    ld   a, (hl)            ; r[1]
    dec  hl
    cp   a, c
    jr   c, 25$             ; r[1] <= x[0]: only the empty column of r meets x
    jr   z, 25$
    push hl
    push de
    call _shared_pair
    pop  de
    pop  hl
    jr   28$
25$:
    push hl
    ld   a, (_s_r)
    add  a, #<(_patron_ovl)
    ld   l, a
    ld   a, #0
    adc  a, #>(_patron_ovl)
    ld   h, a
    ld   a, (hl)
    or   a, #5              ; OVL_SHARED | OVL_TWO
    ld   (hl), a
    pop  hl
28$:
    ld   a, e
    add  a, #4
    ld   e, a
    ld   a, d
    adc  a, #0
    ld   d, a
    jr   22$
29$:
    ld   bc, #4
    add  hl, bc
    jp   20$
39$:
    ld   hl, #_rec          ; ---- 3. flags changed: compose his columns again
40$:
    ld   a, (_rec_end)
    cp   a, l
    jr   nz, 41$
    ld   a, (_rec_end + 1)
    cp   a, h
    jr   z, 49$
41$:
    push hl
    ld   a, (hl+)           ; r[0]
    ld   (_md_x0), a
    inc  hl
    ld   a, (hl+)           ; r[2]
    ld   (_md_x1), a
    ld   a, (hl)            ; r[3]: slot, old flags in bits 4-6
    ld   c, a
    swap a
    and  a, #7
    ld   b, a
    ld   a, c
    and  a, #0x0F
    add  a, #<(_patron_ovl)
    ld   l, a
    ld   a, #0
    adc  a, #>(_patron_ovl)
    ld   h, a
    ld   a, (hl)
    cp   a, b
    jr   z, 42$
    call _md_g
42$:
    pop  hl
    ld   bc, #4
    add  hl, bc
    jr   40$
49$:
    pop  bc
    ret
__endasm;
}

// Bar b: lift so that the BG patrons are column-disjoint (greedy, left to right), flag the pairs that stay on the BG,
// and note which lifted patrons still cover a BG one.
static void choose_bar(uint8_t b) {
    uint8_t *r, *x, s, busy;
    gather(b);
    ch_b = b;
    ch_bit = bar_bit[b];
    ovl_bars &= ~ch_bit;
    ch_retry = 0;
    if (rec_end == rec + 4) {                             // one patron: nothing to share
        s = rec[3];
        if (s & REC_OBJ) lift_busy[s & REC_SLOT] = 0;
        if (s & 0x70) mark_dirty_attrs(b, rec[0], rec[2]);      // (his old flags are gone: with the attributes, see md_g)
        return;
    }
    choose_asm();
    if (!lift_n[b]) return;
    for (r = rec; r != rec_end; r += 4) {                 // lifted ones: still over a BG patron?
        if (!(r[3] & REC_OBJ)) continue;
        busy = 0;
        for (x = rec; x != rec_end; x += 4)
            if (!(x[3] & REC_OBJ) && x[0] < r[1] && r[0] < x[1]) { busy = 1; break; }
        s = r[3] & REC_SLOT;
        lift_busy[s] = busy;
        if (busy) lift_clear[s] = 0;
    }
}

#endif

// Every frame while someone is lifted, the chooser has work or the hook is set, after the rules and before queue_vram().
void lift_frame(void) BANKED {
    uint8_t p, b, w, i, r = 0, done = 0, first = 0, fc = frame_counter;
    est_ok = 0;
    if (lift_total) {                                     // (nobody lifted: only the chooser has work, keep it cheap)
        lifted_pass();
        SEC(SEC_P5);
        need_estimate();
        SEC(SEC_P6);
        forced_drops();
    }
    SEC(SEC_COMPOSE);
    if (lift_hook_op) hook();
    // The chooser, on the bars whose columns changed (ovl_dirty bits 0-3). A lift refused by the budgets is tried again
    // RETRY_FRAMES later (bits 4-7: waiting), one that only has to wait for this frame's copy list next frame.
    // It looks at one bar at least, unless the frame has already run into the next one (an overloaded frame), and at
    // one only (the start bar goes round); bars it leaves stay dirty for the next frame.
    b = ovl_dirty;
    ovl_dirty = 0;
    if (b && (HALF & HALF_ON)) fc >>= 1;                 // (30 fps: the round robin counts pictures)
    for (i = b ? 0 : NUM_BARS; i < NUM_BARS; i++) {      // (nothing dirty or waiting: no pass over the bars)
        p = (i + fc) & (NUM_BARS - 1);                   // (round robin: the bar the frame starts at moves on every frame)
        w = bar_bit[p];
        if (!(b & w)) {
            if (!(b & (w << 4))) continue;
            if (--retry_wait[p]) { r |= w << 4; continue; }
        }
        if (!done && !first) {                            // the first bar of this frame: is the frame late already?
            first = 1;
            if (((uint8_t)sys_time != frame_t0 || (LY_REG < 144 && LY_REG >= CHOOSER_LY_LATE)) && !(HALF & HALF_ON)) {   // (30 fps: the next step is the short one, a long picture is paid for there)
                if (++ch_late < CHOOSER_LATE_MAX) first = 2;   // (later; but at least every CHOOSER_LATE_MAX frames)
                else ch_late = 0;
            } else ch_late = 0;
        }
        if (first == 2 || done) { r |= w; continue; }       // (one bar a frame at most: the rest next frame)
        done = 1;
        SEC(SEC_P7);
        choose_bar(p);
        if (ch_retry == 2) r |= w;
        else if (ch_retry) { retry_wait[p] = RETRY_FRAMES; r |= w << 4; }
    }
    ovl_dirty |= r;
    if (est_ok) for (p = 0; p < NUM_BARS; p++) lift_load[p] = ld[p];   // (after this frame's drops and lifts)
}

// OAM 25 down: two 8x16 entries per patron drawn as a sprite (his shift-0 pose; OAM x gives every pixel position and
// the sway). Entries used last frame but not now are hidden unless the mugs took them this frame.
// (hand-written: the C loop cost ~10 lines a frame) dl_n patrons written, OAM 25 down, two entries each. Per lifted
// patron p: x = (patron_draw[p] & 0x7F) + 8 - (patron_lift[p] == LIFT_EDGE ? patron_aux[p] : 0) (uint8_t: wraps past the
// left edge); entries { bar_oam_y[bar], x, lift_tile[v], lift_prop[v] } and { .., x + 8, lift_tile[v] + 2, lift_prop[v] };
// it stops after lift_total patrons. The C version (draw_lifted_c, ASM_LIFT_DRAW 0, make cfall) is the reference.
static uint8_t dl_n, dl_v, dl_x, dl_y, dl_t, dl_p;
static uint8_t *dl_o;
#if !ASM_LIFT_DRAW
static void dl_one(uint8_t p, uint8_t l) {                // one lifted patron's two entries at dl_o (its own function: the scan below stays tiny)
    uint8_t x = (uint8_t)((patron_draw[p] & 0x7F) + 8), t, a;
    OAM_item_t *e = (OAM_item_t *)dl_o;                   // (struct fields: SDCC writes them through one pointer; indexed bytes cost it 16-bit adds)
    if (l == LIFT_EDGE) x = (uint8_t)(x - patron_aux[p]);
    l = patron_variant[p];
    t = lift_tile[l & 7]; a = lift_obj[(l ^ (l >> 3)) & 7] | lift_prop[0] | ((l >> 3) & 8);
    e->y = bar_oam_y[patron_bar[p] & 3]; e->x = x; e->tile = t; e->prop = a;                    // his left half
    e--;
    e->y = (e + 1)->y; e->x = (uint8_t)(x + 8); e->tile = (uint8_t)(t + 2); e->prop = a;       // his right half: the entry below
    dl_o = (uint8_t *)(e - 1);
}
static void draw_lifted_asm(void) {
    uint8_t n = 0, p;
    const uint8_t *q = patron_lift;
    dl_o = (uint8_t *)shadow_OAM + 100;                   // OAM 25 (OAM_LIFT_TOP)
    do {
        if (*q & 3) {                                     // (the scan is the cost: one test and one pointer step per patron)
            p = (uint8_t)(q - patron_lift);
            if (patron_draw[p] != 0xFF) {
                dl_one(p, *q & 3);
                if (++n == 4 || n >= lift_total) break;   // LIFT_MAX; all lift_total of them written
            }
        }
    } while (++q != patron_lift + MAX_PATRONS);
    dl_n = n;
}
#else
static void draw_lifted_asm(void) __naked {
__asm
    push bc
    ld   hl, #_dl_o
    ld   a, #<(_shadow_OAM + 100)   ; OAM 25 (OAM_LIFT_TOP)
    ld   (hl+), a
    ld   (hl), #>(_shadow_OAM + 100)
    ld   bc, #0             ; c: p, b: patrons written
1$:
    ld   a, c
    add  a, #<(_patron_lift)
    ld   l, a
    ld   a, #0
    adc  a, #>(_patron_lift)
    ld   h, a
    ld   a, (hl)
    and  a, #3
    jp   z, 9$
    ld   (_dl_v), a
    ld   a, c
    add  a, #<(_patron_draw)
    ld   l, a
    ld   a, #0
    adc  a, #>(_patron_draw)
    ld   h, a
    ld   a, (hl)
    cp   a, #0xFF
    jp   z, 9$
    and  a, #0x7F
    add  a, #8
    ld   (_dl_x), a
    ld   a, (_dl_v)
    cp   a, #2              ; LIFT_EDGE: patron_aux px further left (past the left edge of the screen: OAM X wraps)
    jr   nz, 3$
    ld   a, c
    add  a, #<(_patron_aux)
    ld   l, a
    ld   a, #0
    adc  a, #>(_patron_aux)
    ld   h, a
    ld   a, (_dl_x)
    sub  a, (hl)
    ld   (_dl_x), a
3$:
    ld   a, c
    add  a, #<(_patron_bar)
    ld   l, a
    ld   a, #0
    adc  a, #>(_patron_bar)
    ld   h, a
    ld   a, (hl)
    and  a, #3
    add  a, #<(_bar_oam_y)
    ld   l, a
    ld   a, #0
    adc  a, #>(_bar_oam_y)
    ld   h, a
    ld   a, (hl)
    ld   (_dl_y), a
    ld   a, c
    add  a, #<(_patron_variant)
    ld   l, a
    ld   a, #0
    adc  a, #>(_patron_variant)
    ld   h, a
    ld   a, (hl)            ; the variant byte: look bits 0-2, (palette instance ^ look) bits 3-5, the bank-1 flag bit 6
    ld   (_dl_v), a
    and  a, #7
    ld   e, a
    ld   d, #0
    ld   hl, #_lift_tile
    add  hl, de
    ld   a, (hl)
    ld   (_dl_t), a
    ld   a, (_dl_v)
    ld   e, a
    rrca
    rrca
    rrca                    ; v >> 3 in bits 0-5 (bit 6 -> bit 3)
    ld   d, a
    xor  a, e
    and  a, #7              ; the palette instance
    add  a, #<(_story_scratch + 254)
    ld   l, a
    ld   a, #0
    adc  a, #>(_story_scratch + 254)
    ld   h, a
    ld   a, (hl)            ; its OBJ palette
    ld   e, a
    ld   a, d
    and  a, #8              ; VRAM bank 1 (OAM bit 3)
    or   a, e
    ld   hl, #_lift_prop
    or   a, (hl)            ; DMG: OBP1
    ld   (_dl_p), a
    ld   a, (_dl_o)
    ld   l, a
    ld   a, (_dl_o + 1)
    ld   h, a
    ld   a, (_dl_y)         ; his left half: y, x, t, attributes
    ld   (hl+), a
    ld   a, (_dl_x)
    ld   (hl+), a
    ld   a, (_dl_t)
    ld   (hl+), a
    ld   a, (_dl_p)
    ld   (hl), a
    ld   de, #-7
    add  hl, de             ; the entry below
    ld   a, (_dl_y)         ; his right half: y, x + 8, t + 2, attributes
    ld   (hl+), a
    ld   a, (_dl_x)
    add  a, #8
    ld   (hl+), a
    ld   a, (_dl_t)
    add  a, #2
    ld   (hl+), a
    ld   a, (_dl_p)
    ld   (hl), a
    add  hl, de             ; the next one down
    ld   a, l
    ld   (_dl_o), a
    ld   a, h
    ld   (_dl_o + 1), a
    inc  b
    ld   a, b
    cp   a, #4              ; LIFT_MAX
    jr   z, 10$
    ld   hl, #_lift_total
    cp   a, (hl)
    jr   nc, 10$            ; (all lift_total of them written: the rest of the slots need no look)
9$:
    inc  c
    ld   a, c
    cp   a, #16             ; MAX_PATRONS
    jp   nz, 1$
10$:
    ld   a, b
    ld   (_dl_n), a
    pop  bc
    ret
__endasm;
}
#endif

void draw_lifted(void) BANKED {
    uint8_t i, n;
    draw_lifted_asm();
    n = dl_n;
    for (i = OAM_LIFT_TOP + 1 - (lift_oam_n << 1); i < (uint8_t)(OAM_LIFT_TOP + 1 - (n << 1)); i++)
        if (i >= oam_used) shadow_OAM[i].y = 0;
    lift_oam_n = n;
}
