// The story map's streaming engine (see src/smap.c "THE WORLD ON THE HARDWARE"): the tile slots (Color: a static plan; DMG: a dynamic allocator), the BG palettes,
// the lines of cells of the region (add and drop jobs), the camera and the region that follows it. Its own bank: smap.c (the screen) is a bank on its own.
#pragma bank 255
#include <gb/gb.h>
#include <gb/cgb.h>
#include <stdint.h>

#include "asm_cfg.h"
#include "game.h"
#include "music.h"
#define SMAPW_VIEWS
#include "smap_world.h"
#include "smap_priv.h"

// ---- the world: slots, palettes, lines ---------------------------------------------------------------------------------------------------------------------------
static uint8_t nib_get(uint16_t s) { return (SC(A_NIB)[s >> 1] >> ((s & 1) << 2)) & 15; }
static void nib_set(uint16_t s, uint8_t v) {
    uint8_t *p = SC(A_NIB) + (s >> 1);
    if (s & 1) *p = (*p & 0x0F) | (v << 4); else *p = (*p & 0xF0) | v;
}

static uint16_t tbl_get(uint8_t s) {
    return SC(A_TBL)[s] | ((uint16_t)((SC(A_TBL)[176 + (s >> 2)] >> ((s & 3) << 1)) & 3) << 8);
}
static void tbl_set(uint8_t s, uint16_t t) {
    uint8_t *h = SC(A_TBL) + 176 + (s >> 2), sh = (s & 3) << 1;
    SC(A_TBL)[s] = (uint8_t)t;
    *h = (*h & ~(3 << sh)) | ((t >> 8) << sh);
}
#if ASM_SMAP
// DMG, asm: the slot holding tile lo + 256 V_ID (a table scan: the C twin is the loop in tbl_find), 255: none. Eight slots a pass, 20 cycles a slot.
typedef char smap_scan_offsets[(V_ID == 60 && A_TBL == 0 && SMAPW_POOL == 176 && S_V == 396) ? 1 : -1];
static uint8_t smap_scan(uint8_t lo) __naked {
    (void)lo;
__asm
    ld   b, a
    ld   hl, #_story_scratch
    ld   c, #22
1$:
    ld   a, (hl+)
    cp   a, b
    jr   z, 5$
    ld   a, (hl+)
    cp   a, b
    jr   z, 5$
    ld   a, (hl+)
    cp   a, b
    jr   z, 5$
    ld   a, (hl+)
    cp   a, b
    jr   z, 5$
    ld   a, (hl+)
    cp   a, b
    jr   z, 5$
    ld   a, (hl+)
    cp   a, b
    jr   z, 5$
    ld   a, (hl+)
    cp   a, b
    jr   z, 5$
    ld   a, (hl+)
    cp   a, b
    jr   z, 5$
    dec  c
    jr   nz, 1$
9$:
    ld   a, #0xFF
    ret
5$:                                         ; the low byte matches at hl - 1: the high bits too?
    ld   a, l
    sub  a, #<(_story_scratch + 1)
    ld   d, a                               ; d = the slot
    call 20$
    jr   z, 8$
    ld   a, #175                            ; (rare: another tile with this low byte) the slots after it, one at a time
    sub  a, d
    jr   z, 9$
    ld   c, a
6$:
    inc  d
    ld   a, (hl+)
    cp   a, b
    jr   nz, 7$
    call 20$
    jr   z, 8$
7$:
    dec  c
    jr   nz, 6$
    jr   9$
8$:
    ld   a, d
    ret
20$:                                        ; z: the high bits of slot d are V_ID (hl, bc kept)
    push hl
    push bc
    ld   a, d
    srl  a
    srl  a
    ld   c, a
    ld   b, #0
    ld   hl, #_story_scratch + 176
    add  hl, bc
    ld   b, (hl)
    ld   a, d
    and  a, #3
    add  a, a
    ld   c, a
    ld   a, b
    inc  c
21$:
    dec  c
    jr   z, 22$
    srl  a
    jr   21$
22$:
    and  a, #3
    ld   hl, #_story_scratch + 456
    cp   a, (hl)
    pop  bc
    pop  hl
    ret
__endasm;
}
// DMG, asm: the first free slot (use count 0) from slot rr on, wrapping once; 255: none. The C twin is the loop in add_cell. Four slots a step, 24 cycles a slot (the C loop: about 70).
typedef char smap_free_offsets[(A_CNT == 220 && SMAPW_POOL == 176 && S_V == 396) ? 1 : -1];
static uint8_t smap_freeslot(uint8_t rr) __naked {
    (void)rr;
__asm
    ld   e, a
    ld   c, a
    ld   b, #0
    ld   hl, #_story_scratch + 220
    add  hl, bc                             ; hl = the count of slot rr
    ld   a, #176
    sub  a, e
    jr   z, 4$
    ld   b, a                               ; the slots rr .. 175
    call 1$
    jr   c, 8$
4$:
    ld   a, e
    or   a, a
    jr   z, 9$
    ld   b, a                               ; the slots 0 .. rr - 1
    ld   hl, #_story_scratch + 220
    call 1$
    jr   c, 8$
9$:
    ld   a, #0xFF
    ret
8$:
    ld   a, l
    sub  a, #<(_story_scratch + 221)
    ret
1$:                                         ; b slots (b > 0) from hl: carry set: hl - 1 is the free one
    ld   a, b
    and  a, #3
    jr   z, 3$
    ld   c, a
2$:
    ld   a, (hl+)
    or   a, a
    jr   z, 7$
    dec  c
    jr   nz, 2$
3$:
    ld   a, b
    srl  a
    srl  a
    jr   z, 6$
    ld   b, a
5$:
    ld   a, (hl+)
    or   a, a
    jr   z, 7$
    ld   a, (hl+)
    or   a, a
    jr   z, 7$
    ld   a, (hl+)
    or   a, a
    jr   z, 7$
    ld   a, (hl+)
    or   a, a
    jr   z, 7$
    dec  b
    jr   nz, 5$
6$:
    xor  a, a                               ; none (carry clear)
    ret
7$:
    scf
    ret
__endasm;
}
#endif
#if ASM_SMAP
// DMG, asm: the whole of add_cell for a tile that is not resident (the C twin is the code of add_cell below it, which also takes every other case): the slot (the hint, its second
// home, else the first free one after the pointer), the old tile's far count, the table, the tile staged and queued, the slot's count. In: de = the cell (word, aux). Out: bc,
// c = R_OK, R_RES, R_ROOM, or 3: not for it (the tile may be resident, NDISP is not 0): the C code takes the cell; b = the id when R_OK.
// (story_scratch + : 438 V_NSTG, 439 V_RES, 440 V_RESE, 442 V_RR, 450 V_PWL, 451 V_PWH tile, 452 V_LIMC the hint, 453 V_LIMQ the slot, 457 V_NDISP, 220 the counts, 176 the highs)
typedef char smap_dadd_offsets[(V_NSTG == 42 && V_RES == 43 && V_RESE == 44 && V_RR == 46 && V_PWL == 54 && V_PWH == 55 && V_LIMC == 56 && V_LIMQ == 57 && V_NDISP == 61
                                && S_V == 396 && S_T + T_TILES == 464 && A_CNT == 220 && A_TBL == 0 && SMAPW_POOL == 176 && VQ_USE == 22 && VQ_DRAIN_BUDGET == 86 && sizeof(vq_entry_t) == 8) ? 1 : -1];
static uint16_t smap_dadd(const smap_fc *f) __naked {
    (void)f;
__asm
    ld   a, (de)
    ld   (_story_scratch + 450), a          ; the tiles low byte
    inc  de
    ld   a, (de)
    and  a, #3
    ld   (_story_scratch + 451), a          ; its high bits
    inc  de
    ld   a, (de)
    ld   (_story_scratch + 452), a          ; the hint
    ld   e, a
    call 60$                                ; the hint slot holds it?
    jp   z, 80$
    ld   a, (_story_scratch + 452)
    call 70$                                ; a = home2
    ld   e, a
    call 60$
    jp   z, 80$
    ld   a, (_story_scratch + 457)          ; V_NDISP: a far tile may hold it: the scan (the C code takes the cell if it finds it)
    or   a, a
    jr   z, 3$
    ld   a, (_story_scratch + 451)
    ld   (_story_scratch + 456), a          ; V_ID: the tile high bits for smap_scan
    ld   a, (_story_scratch + 450)
    call _smap_scan
    cp   a, #0xFF
    jp   nz, 80$
3$:
    ld   a, (_story_scratch + 438)          ; V_NSTG
    cp   a, #2
    jp   nc, 82$
    ld   a, (_qv_cost)                      ; room(): 81 - qv_cost, 0 from 81 on
    cp   a, #81
    jp   nc, 82$
    ld   b, a
    ld   a, #81
    sub  a, b
    ld   b, a
    ld   a, (_story_scratch + 439)          ; V_RES
    add  a, #20                             ; (the cell 1 + a tile 19)
    ld   c, a
    ld   a, b
    cp   a, c
    jp   c, 82$
    ld   a, (_vq_count)
    ld   b, a
    ld   a, (_story_scratch + 440)          ; V_RESE
    add  a, b
    inc  a                                  ; (the tiles entry)
    cp   a, #23
    jp   nc, 82$
    ld   a, (_story_scratch + 452)          ; the slot: the hint if no cell shows what it holds, else its second home, else the next free after the pointer
    ld   e, a
    ld   d, #0
    ld   hl, #_story_scratch + 220
    add  hl, de
    ld   a, (hl)
    or   a, a
    jr   z, 5$
    ld   a, e
    call 70$
    ld   e, a
    ld   d, #0
    ld   hl, #_story_scratch + 220
    add  hl, de
    ld   a, (hl)
    or   a, a
    jr   z, 5$
    ld   a, (_story_scratch + 442)          ; V_RR
    call _smap_freeslot
    cp   a, #0xFF
    jp   z, 81$
    ld   e, a
    inc  a
    cp   a, #176
    jr   c, 4$
    xor  a, a
4$:
    ld   (_story_scratch + 442), a
5$:
    ld   a, e
    ld   (_story_scratch + 453), a          ; the slot
    call 50$                                ; (the old tile: b = its high bits, c = its low byte)
    ld   a, c
    inc  a
    jr   nz, 6$
    ld   a, b
    cp   a, #3
    jr   z, 8$                              ; the slot was free
6$:
    ld   e, #___bank_smap_d_a
    ld   hl, #_smap_d_hintx
    call ___sdcc_bcall_ehl                  ; a = the old tiles hint slot
    ld   hl, #_story_scratch + 453
    ld   e, (hl)
    call 71$                                ; (a = n: is the slot far from it?)
    jr   nc, 8$
    ld   hl, #_story_scratch + 457
    dec  (hl)
8$:
    ld   a, (_story_scratch + 453)
    ld   e, a
    ld   a, (_story_scratch + 452)
    call 71$
    jr   nc, 9$
    ld   hl, #_story_scratch + 457
    inc  (hl)
9$:
    ld   a, (_story_scratch + 453)          ; tbl_set
    ld   e, a
    ld   d, #0
    ld   hl, #_story_scratch
    add  hl, de
    ld   a, (_story_scratch + 450)
    ld   (hl), a
    ld   a, e
    srl  a
    srl  a
    ld   l, a
    ld   h, #0
    ld   bc, #_story_scratch + 176
    add  hl, bc
    ld   a, e
    and  a, #3
    add  a, a
    ld   c, a
    ld   a, (_story_scratch + 451)
    ld   d, a
    ld   a, #3
    inc  c
10$:
    dec  c
    jr   z, 11$
    sla  a
    sla  d
    jr   10$
11$:
    cpl
    and  a, (hl)
    or   a, d
    ld   (hl), a
    ld   e, #___bank_smap_d_t
    ld   hl, #_smap_d_tcopy
    call ___sdcc_bcall_ehl                  ; the tile into the staging slot
    ld   a, (_story_scratch + 453)
    cp   a, #36                             ; pool_id
    jr   c, 12$
    add  a, #57
12$:
    ld   (_story_scratch + 449), a          ; V_BCAP: the id
    ld   c, a
    ld   l, a
    ld   h, #0
    add  hl, hl
    add  hl, hl
    add  hl, hl
    add  hl, hl
    bit  7, c
    ld   a, #0x90
    jr   z, 13$
    ld   a, #0x80
13$:
    add  a, h
    ld   h, a                               ; hl = tile_addr(id)
    push hl
    ld   a, (_vq_count)                     ; qraw(0, staging, hl, 16)
    cp   a, #24
    jr   nc, 15$
    ld   b, a
    inc  a
    ld   (_vq_count), a
    ld   l, b
    ld   h, #0
    add  hl, hl
    add  hl, hl
    add  hl, hl
    ld   de, #_vq
    add  hl, de
    ld   a, (_qv_cost)
    cp   a, #87
    jr   nc, 14$
    add  a, #19
    ld   (_qv_cost), a
14$:
    ld   a, #16
    ld   (hl+), a
    xor  a, a
    ld   (hl+), a
    ld   a, (_story_scratch + 438)
    swap a
    and  a, #0xF0
    add  a, #<(_story_scratch + 464)
    ld   (hl+), a
    ld   a, #>(_story_scratch + 464)
    adc  a, #0
    ld   (hl+), a
    pop  de
    ld   a, e
    ld   (hl+), a
    ld   (hl), d
    jr   16$
15$:
    pop  hl
16$:
    ld   hl, #_story_scratch + 438
    inc  (hl)                               ; V_NSTG
    ld   a, (_story_scratch + 453)
    ld   e, a
    ld   d, #0
    ld   hl, #_story_scratch + 220
    add  hl, de
    inc  (hl)                               ; the slots count
    ld   a, (_story_scratch + 449)
    ld   b, a                               ; (the id)
    ld   c, #0
    ret
80$:
    ld   c, #3
    ret
81$:
    ld   c, #1
    ret
82$:
    ld   c, #2
    ret
50$:                                        ; e = a slot: b = its high bits, c = its low byte
    call 51$
    ld   b, a
    ld   d, #0
    ld   hl, #_story_scratch
    add  hl, de
    ld   c, (hl)
    ret
51$:                                        ; e = a slot: a = its high bits (bc, hl)
    ld   a, e
    srl  a
    srl  a
    ld   l, a
    ld   h, #0
    ld   bc, #_story_scratch + 176
    add  hl, bc
    ld   b, (hl)
    ld   a, e
    and  a, #3
    add  a, a
    ld   c, a
    ld   a, b
    inc  c
52$:
    dec  c
    jr   z, 53$
    srl  a
    jr   52$
53$:
    and  a, #3
    ret
60$:                                        ; e = a slot: z when it holds the tile
    ld   d, #0
    ld   hl, #_story_scratch
    add  hl, de
    ld   a, (hl)
    ld   hl, #_story_scratch + 450
    cp   a, (hl)
    ret  nz
    call 51$
    ld   hl, #_story_scratch + 451
    cp   a, (hl)
    ret
70$:                                        ; a = a hint: a = its second home
    cp   a, #88
    jr   c, 72$
    sub  a, #88
    ret
72$:
    add  a, #88
    ret
71$:                                        ; a = a tiles hint n, e = a slot: carry when the slot is neither n nor its second home
    cp   a, e
    jr   z, 73$
    call 70$
    cp   a, e
    jr   z, 73$
    scf
    ret
73$:
    or   a, a
    ret
__endasm;
}
#endif
static uint8_t home2(uint8_t h) { return h < 88 ? h + 88 : h - 88; }   // a tile's second home slot (when its hint is busy)
static uint8_t tbl_find(uint16_t t, uint8_t hint) {     // the slot holding tile t, or NIL
    uint8_t s;
    if (tbl_get(hint) == t) return hint;
    s = home2(hint);
    if (tbl_get(s) == t) return s;
    if (!V(V_NDISP)) return NIL;                            // (a tile lives at its hint slot or the second home unless both were busy: V_NDISP such tiles are resident)
    s = V(V_CS);                                            // (the slot the last such search found: the cells of one tile come together)
    if (s < SMAPW_POOL && tbl_get(s) == t) return s;
#if ASM_SMAP
    V(V_ID) = (uint8_t)(t >> 8);
    s = smap_scan((uint8_t)t);
    if (s != NIL) V(V_CS) = s;
    return s;
#else
    for (s = 0; s < SMAPW_POOL; s++) if (SC(A_TBL)[s] == (uint8_t)t && tbl_get(s) == t) { V(V_CS) = s; return s; }
    return NIL;
#endif
}

// stage a tile load (the staging area holds two a frame; the caller has checked V_NSTG and the room) and queue it, or, with the LCD off, put it in VRAM
static void tile_load(uint8_t bank, uint8_t id, uint16_t tile) {
    uint8_t *d = is_cgb ? (uint8_t *)(((uint16_t)SC(A_XSTG) + 15) & 0xFFF0) + (V(V_NSTG) << 4) : SC(S_T + T_TILES + (V(V_NSTG) << 4));     // (the Color's: on a 16-byte boundary for the DMA)
    if (is_cgb) smap_c_tile(tile, d); else smap_d_tile(tile, d);
    if (V(V_DIRECT)) {
        if (bank) VBK_REG = VBK_BANK_1;
        set_bkg_data(id, 1, d);
        VBK_REG = VBK_BANK_0;
        return;
    }
    if (is_cgb) qsp(bank, d, tile_addr(id), 2);     // (Color: general-purpose DMA, one block in VBlank, bank bit 1; it costs 9-11 of the drain, not 19-21)
    else qraw(bank, d, tile_addr(id), 16);
    V(V_NSTG)++;
}

// Color: palette pal takes a hardware slot (NIL: none free) and its colours are written (queued: one palette a frame, the caller checked V_PALQ and the room)
static void pal_write(uint8_t s, uint8_t pal) {
    uint8_t *st = SC(A_PSTG);
    smap_c_palette(pal, st + 1);
    if (V(V_DIRECT)) { set_bkg_palette(s, 1, (const uint16_t *)(st + 1)); return; }
    st[0] = 0x80 | (s << 3);                       // BCPS: auto increment from colour 0 of palette s
    qraw(0, st, 0xFF68, 1);
    for (pal = 1; pal < 9; pal++) qraw(0, st + pal, 0xFF69, 1);
    V(V_PALQ) = 1;
}

static uint8_t pal_take(uint8_t pal) {
    uint8_t s;
    for (s = 0; s < 8; s++) if (SC(A_PUSE)[s] == NIL) break;
    if (s == 8) return NIL;
    SC(A_PUSE)[s] = pal; SC(A_PSLOT)[pal] = s;
    pal_write(s, pal);
    return s;
}

// THE PALETTE HAND-OVER (Color).  A line the camera cannot show yet may need a 9th palette: it is added with palette pal on the hardware slot of the palette q the generator named
// (smapw_ret: q's only cells are in the line at the other end of the region, the last one the camera still shows).  Until q's cells have left, the slot is q's (PEND = pal, PLN the line);
// when q's last cell goes (pal_count) the hand-over is due (PEND bit 5): pal_hand queues pal's colours into the slot, in the frame the line left.  The camera and Sal may not show the
// borrowed line before that (smap_room, cov_ok), so no pixel ever has a wrong colour.
static uint8_t pal_alias(uint8_t pal) {
    uint8_t q = smapw_ret[pal], s;
    if (q == NIL || PEND != NIL || V(V_DIRECT) || SC(A_PSLOT)[q] == NIL) return NIL;
    s = SC(A_PSLOT)[q];
    SC(A_PSLOT)[pal] = s;
    PEND = pal; PLN = V(V_JI) | (V(V_JK) == J_COL ? 0x80 : 0);
    return s;
}

static void pal_hand(void) {
    uint8_t p = PEND, s;
    if (!(p & 0x20) || p == NIL || V(V_PALQ) || room() < (uint8_t)(36 + V(V_RES)) || (uint8_t)(vq_count + 9 + V(V_RESE)) > VQ_USE) return;
    p &= 0x1F;
    s = SC(A_PSLOT)[p];
    SC(A_PUSE)[s] = p;
    pal_write(s, p);
    PEND = NIL;
}

static void pal_count(uint8_t pal, int8_t d) {          // the region's cells in palette pal change by d; the slot is free at 0
    uint8_t *c = SC(A_PCNT) + (pal << 1);
    uint16_t v = (c[0] | ((uint16_t)c[1] << 8)) + (int16_t)d;
    c[0] = (uint8_t)v; c[1] = (uint8_t)(v >> 8);
    if (!v && d < 0) {
        if (PEND != NIL) {
            if (pal == PEND) { SC(A_PSLOT)[pal] = NIL; PEND = NIL; return; }                           // (the borrowing palette's cells all left again: the slot stays its owner's)
            if (pal == smapw_ret[PEND & 0x1F] && !(PEND & 0x20)) { PEND |= 0x20; SC(A_PSLOT)[pal] = NIL; return; }   // (the owner's last cell left: the slot is due to the borrower, pal_hand)
        }
        SC(A_PUSE)[SC(A_PSLOT)[pal]] = NIL; SC(A_PSLOT)[pal] = NIL;
    }
}

#define R_OK    0
#define R_RES   1                                   // no slot or palette free: the line waits for the camera to drop a line
#define R_ROOM  2                                   // not enough room in this frame's list: tomorrow

static uint8_t slot_of_id(uint8_t id) { return id < 36 ? id : (uint8_t)(id - 57); }      // (pool_id's inverse)

// a cell of a column: its map entry (a row's go out as runs when its line is flushed)
#define CELL_COST(vert) (is_cgb ? 2 : 1)                                    // the drain's cost of one cell of a line (a column goes out as a stride run: a byte a cell, and an id and an attribute)
#define CELL_ENT(vert)  0                                                   // and the list entries it takes (a line's runs are reserved up front: V_RESE)

// One cell into the region: its tile (and palette) made resident, its id and attribute in the line buffers at k (the line's map entries are queued by the caller when it
// has added what it will this frame). R_OK, or why not (nothing changed then).
static uint8_t add_cell(const smap_fc *f, uint8_t k, uint8_t cx, uint8_t cy, uint8_t vert) {
    uint16_t t = f->w & 0x3FF, slot9 = 0;
    uint8_t direct = V(V_DIRECT), need_t, need_p = 0, hw = 0, slot = 0, id, att = 0, pal = 0, bank = 0, var = 0, cost, ents, h, s, rr, n;
    if (is_cgb) {
        pal = (uint8_t)(f->w >> 10);
        slot9 = f->aux & 0x1FF; var = (uint8_t)(f->aux >> 9);
        need_p = SC(A_PSLOT)[pal] == NIL;
        need_t = nib_get(slot9) != var;
        bank = slot9 >= SMAPW_POOL;
    } else {
        slot = tbl_find(t, (uint8_t)f->aux);
        need_t = slot == NIL;
    }
    if (!direct) {
        cost = CELL_COST(vert); ents = CELL_ENT(vert);
        if (need_t) { if (V(V_NSTG) >= NSTG_MAX) return R_ROOM; cost += (is_cgb ? 9 : 19) + (bank << 1); ents++; }
        if (need_p) { if (V(V_PALQ)) return R_ROOM; cost += 36; ents += 9; }
        if (room() < (uint8_t)(cost + V(V_RES)) || (uint8_t)(vq_count + ents + V(V_RESE)) > VQ_USE) return R_ROOM;
    }
    if (is_cgb) {
        hw = SC(A_PSLOT)[pal];
        if (need_p) { hw = pal_take(pal); if (hw == NIL) return R_RES; }
        id = pool_id(bank ? (uint8_t)(slot9 - SMAPW_POOL) : (uint8_t)slot9);
        if (need_t) { nib_set(slot9, var); tile_load(bank, id, t); }
        pal_count(pal, 1);
        att = hw | (bank ? 8 : 0);
    } else {
        if (need_t) {                                // the hint slot when no cell shows what it holds, else the next such slot after the pointer
            h = (uint8_t)f->aux;
            if (SC(A_CNT)[h] == 0) s = h;
            else if (SC(A_CNT)[home2(h)] == 0) s = home2(h);
            else {
#if ASM_SMAP
                s = smap_freeslot(V(V_RR));
                if (s == NIL) return R_RES;
                V(V_RR) = s + 1 >= SMAPW_POOL ? 0 : s + 1;
#else
                rr = V(V_RR);
                for (n = 0; n < SMAPW_POOL; n++) { s = rr; rr = rr + 1 >= SMAPW_POOL ? 0 : rr + 1; if (SC(A_CNT)[s] == 0) break; }
                if (n == SMAPW_POOL) return R_RES;
                V(V_RR) = rr;
#endif
            }
            slot = s;
            slot9 = tbl_get(s);                      // the tile it held leaves (a far one is one fewer); the new one is far when both its homes were busy
            if (slot9 != 0x3FF) { n = smap_d_hintof(slot9); if (s != n && s != home2(n)) V(V_NDISP)--; }
            if (s != h && s != home2(h)) V(V_NDISP)++;
            tbl_set(slot, t);
            tile_load(0, pool_id(slot), t);
        }
        id = pool_id(slot);
        SC(A_CNT)[slot]++;
    }
    SC(S_T + T_IDS)[k] = id;
    if (is_cgb) SC(A_IDA)[k] = att;
    if (direct) {
        *(volatile uint8_t *)map_addr(cx, cy) = id;
        if (is_cgb) { VBK_REG = VBK_BANK_1; *(volatile uint8_t *)map_addr(cx, cy) = att; VBK_REG = VBK_BANK_0; }
    }
    return R_OK;
}


// Color: the cell of a column or row for the Color model, the same as add_cell's Color half (a function of its own, so that the DMG's add_cell above is compiled exactly as it was).
// The cell word's bits 10-14 are the palette, bit 15 says the cell shows the tile id's alternate (its mirror image, the Color flip-merge): the slot table's bits 11-12 are that flip
// (attribute bit 5: X, bit 6: Y), bits 9-10 the variant.
static uint8_t add_cell_c(const smap_fc *f, uint8_t k, uint8_t cx, uint8_t cy, uint8_t vert) {
    uint16_t t = f->w & 0x3FF, slot9 = f->aux & 0x1FF;
    uint8_t direct = V(V_DIRECT), need_t, need_p, hw, id, att, pal = (uint8_t)((f->w >> 10) & 31), bank, var = (uint8_t)((f->aux >> 9) & 3), cost, ents;
    need_p = SC(A_PSLOT)[pal] == NIL;
    need_t = nib_get(slot9) != var;
    bank = slot9 >= SMAPW_POOL;
    if (!direct) {
        cost = CELL_COST(vert); ents = CELL_ENT(vert);
        if (need_t) { if (V(V_NSTG) >= NSTG_MAX) return R_ROOM; cost += 9 + (bank << 1); ents++; }
        if (need_p) { if (V(V_PALQ)) return R_ROOM; cost += 36; ents += 9; }
        if (room() < (uint8_t)(cost + V(V_RES)) || (uint8_t)(vq_count + ents + V(V_RESE)) > VQ_USE) return R_ROOM;
    }
    hw = SC(A_PSLOT)[pal];
    if (need_p) { hw = pal_take(pal); if (hw == NIL) hw = pal_alias(pal); if (hw == NIL) return R_RES; }
    id = pool_id(bank ? (uint8_t)(slot9 - SMAPW_POOL) : (uint8_t)slot9);
    if (need_t) { nib_set(slot9, var); tile_load(bank, id, t); }
    pal_count(pal, 1);
    att = hw | (bank ? 8 : 0);
    if (f->w & 0x8000) att |= (uint8_t)(f->aux >> 6) & 0x60;
    SC(S_T + T_IDS)[k] = id;
    SC(A_IDA)[k] = att;
    if (direct) {
        *(volatile uint8_t *)map_addr(cx, cy) = id;
        VBK_REG = VBK_BANK_1; *(volatile uint8_t *)map_addr(cx, cy) = att; VBK_REG = VBK_BANK_0;
    }
    return R_OK;
}

#if ASM_SMAP
// DMG: add_cell, with the tile-load cases in asm first (the Color calls add_cell itself: its code and cost are the same as without the asm)
static uint8_t add_cell_d(const smap_fc *f, uint8_t k, uint8_t cx, uint8_t cy, uint8_t vert) {
    uint16_t x;
    if (!V(V_DIRECT)) {
        x = smap_dadd(f);                            // (3: the C code takes the cell)
        if ((uint8_t)x != 3) { if ((uint8_t)x) return (uint8_t)x; SC(S_T + T_IDS)[k] = (uint8_t)(x >> 8); return R_OK; }
    }
    return add_cell(f, k, cx, cy, vert);
}
#endif

// the next cell shows what the one before it does (the same tile and palette, already resident): no lookup, no load
static uint8_t add_same(const smap_fc *f, uint8_t k, uint8_t cx, uint8_t cy, uint8_t vert) {
    uint8_t direct = V(V_DIRECT), id = SC(S_T + T_IDS)[k - 1], att = 0;
    if (!direct) {
        if (room() < (uint8_t)(CELL_COST(vert) + V(V_RES)) || (uint8_t)(vq_count + CELL_ENT(vert) + V(V_RESE)) > VQ_USE) return R_ROOM;
    }
    if (is_cgb) { att = SC(A_IDA)[k - 1]; SC(A_IDA)[k] = att; pal_count((uint8_t)((f->w >> 10) & 31), 1); }
    else SC(A_CNT)[slot_of_id(id)]++;
    SC(S_T + T_IDS)[k] = id;
    if (direct) {
        *(volatile uint8_t *)map_addr(cx, cy) = id;
        if (is_cgb) { VBK_REG = VBK_BANK_1; *(volatile uint8_t *)map_addr(cx, cy) = att; VBK_REG = VBK_BANK_0; }
    }
    return R_OK;
}

// n cells that show f's tile leave the region
static void drop_cells(const smap_fc *f, uint8_t n) {
    uint8_t s;
    if (is_cgb) { pal_count((uint8_t)((f->w >> 10) & 31), -(int8_t)n); return; }
    s = tbl_find(f->w & 0x3FF, (uint8_t)f->aux);
    if (s == NIL) return;
    SC(A_CNT)[s] -= n;
    if (!SC(A_CNT)[s] && s != (uint8_t)f->aux && s != home2((uint8_t)f->aux)) { tbl_set(s, 0x3FF); V(V_NDISP)--; }   // (a far tile nobody shows is forgotten: only the ones at a home stay cached)
}

static void fetch(uint8_t cx, uint8_t cy, uint8_t n, uint8_t vert, smap_fc *out) {
    if (is_cgb) smap_c_fetch(cx, cy, n, vert, V(V_STATE), out); else smap_d_fetch(cx, cy, n, vert, V(V_STATE), out);
}

// the cells [a, b) of the line (their ids at T_IDS + a ..) into the copy list as runs: a row's along the map (it wraps at column 31), a column's down it (the drain's stride mode,
// bank bit 1), each with its attributes on a Color. Cell i of the line lies at (idx, first + i) for a column, (first + i, idx) for a row.
static void flush_line(uint8_t vert, uint8_t idx, uint8_t first, uint8_t a, uint8_t b) {
    uint8_t n, x;
    if (vert) {
        while (a < b) {                                 // a column: its ids (and attributes) as runs down the map (the drain's stride mode: bank bit 1), cut at the map's wrap
            x = (first + a) & 31;
            n = b - a;
            if (x + n > 32) n = 32 - x;
            qsp(0, SC(S_T + T_IDS + a), map_addr(idx, first + a), n);
            if (is_cgb) qsp(1, SC(A_IDA + a), map_addr(idx, first + a), n);
            a += n;
        }
        return;
    }
    while (a < b) {
        x = (first + a) & 31;
        n = b - a;
        if (x + n > 32) n = 32 - x;
        qraw(0, SC(S_T + T_IDS + a), map_addr(first + a, idx), n);
        if (is_cgb) qraw(1, SC(A_IDA + a), map_addr(first + a, idx), n);
        a += n;
    }
}

#if ASM_SMAP
// DMG, asm (behind ASM_SMAP; the C twin is the per-cell code in job_run and drop_run, which the same lines run without it): the cells of a fetched chunk that need no
// work beyond a counter: a cell that shows what the one before it does, or whose tile sits in a home slot. It stops at the first cell that needs more (a tile to load: the
// C code takes that one) and leaves the state in V. It queues nothing: job_run has counted the room for the V_BM cells, and the line goes out as one entry when it is done.
//   mode 0 (add): V_JP the next cell's position in the line (= its index in the id buffer), V_BF 1 when a cell of this job precedes the first, V_PWL/H its word, V_ID its id,
//     V_BM the cells to do (down to what is left).
//   mode 1 (drop): V_BM the cells left; each cell's hint slot counts one less.
// (the offsets below: S_V 396, V_JK 30, V_JI 31, V_JA 32, V_JP 34, V_BF 52 .. V_ID 60; the id buffer 496, the counts 220, the table 0, its highs 176)
typedef char smap_asm_offsets[(S_V == 396 && S_T + T_IDS == 496 && A_CNT == 220 && A_TBL == 0 && V_JK == 30 && V_JI == 31 && V_JA == 32 && V_JP == 34 && V_BF == 52 && V_BCAP == 53
                               && V_PWL == 54 && V_PWH == 55 && V_LIMC == 56 && V_LIMQ == 57 && V_BM == 58 && V_BMODE == 59 && V_ID == 60 && J_COL == 1 && SMAPW_POOL == 176
                               && sizeof(vq_entry_t) == 8) ? 1 : -1];
static void smap_burst(const smap_fc *f) __naked {
    (void)f;
__asm
    push bc
    ld   a, (_story_scratch + 455)          ; V_BMODE
    or   a, a
    jp   nz, 20$
1$:                                         ; ---- add: one cell
    ld   a, (_story_scratch + 454)          ; V_BM
    or   a, a
    jp   z, 9$
    ld   a, (_story_scratch + 448)          ; V_BF: a cell before this one in the call?
    or   a, a
    jr   z, 3$
    ld   a, (de)                            ; the word the same as the previous cell?
    ld   hl, #_story_scratch + 450          ; V_PWL
    cp   a, (hl)
    jr   nz, 3$
    inc  de
    ld   a, (de)
    dec  de
    inc  hl                                 ; V_PWH
    cp   a, (hl)
    jr   nz, 3$
    ld   a, (_story_scratch + 456)          ; V_ID: the id of the previous cell again; the count of its slot goes up
    cp   a, #36
    jr   c, 2$
    sub  a, #57                             ; (slot_of_id)
2$:
    ld   c, a
    ld   b, #0
    ld   hl, #_story_scratch + 220
    add  hl, bc
    inc  (hl)
    jr   4$
3$:                                         ; the hint slot (or its second home) holds the tile?
    call 30$
    jp   c, 9$
    ld   c, a
    ld   b, #0
    ld   hl, #_story_scratch + 220
    add  hl, bc
    inc  (hl)                               ; (the count)
    ld   a, c
    cp   a, #36
    jr   c, 5$
    add  a, #57                             ; (pool_id)
5$:
    ld   (_story_scratch + 456), a          ; V_ID
4$:                                         ; the id into the buffer
    ld   a, (_story_scratch + 430)          ; V_JP
    ld   c, a
    ld   b, #0
    ld   hl, #_story_scratch + 496
    add  hl, bc
    ld   a, (_story_scratch + 456)
    ld   (hl), a
    ld   a, (de)                            ; the previous word is this one now
    ld   (_story_scratch + 450), a
    inc  de
    ld   a, (de)
    ld   (_story_scratch + 451), a
    inc  de
    inc  de
    inc  de
    ld   hl, #_story_scratch + 430          ; V_JP
    inc  (hl)
    ld   a, #1
    ld   (_story_scratch + 448), a          ; V_BF
    ld   hl, #_story_scratch + 454          ; V_BM
    dec  (hl)
    jp   1$
20$:                                        ; ---- drop: one cell
    ld   a, (_story_scratch + 454)          ; V_BM
    or   a, a
    jr   z, 9$
    call 30$
    jr   c, 9$
    ld   c, a
    ld   b, #0
    ld   hl, #_story_scratch + 220
    add  hl, bc
    dec  (hl)
    inc  de
    inc  de
    inc  de
    inc  de
    ld   hl, #_story_scratch + 454
    dec  (hl)
    jr   20$
9$:
    pop  bc
    ret
30$:                                        ; the hint slot or the second home holds the tile at (de)? a = the slot, carry clear; else carry set (de kept)
    push de
    ld   a, (de)
    ld   b, a                               ; b = low byte of the tile
    inc  de
    ld   a, (de)
    and  a, #3
    ld   c, a                               ; c = its high bits
    inc  de
    ld   a, (de)
    ld   e, a                               ; e = the hint slot
    ld   d, #0
    call 40$
    jr   nc, 35$
    ld   a, e                               ; the second home: hint + 88 (or - 88)
    cp   a, #88
    jr   c, 36$
    sub  a, #88
    jr   37$
36$:
    add  a, #88
37$:
    ld   e, a
    call 40$
    jr   c, 34$
35$:
    ld   a, e
    pop  de
    or   a, a                               ; (carry clear)
    ret
34$:
    pop  de
    scf
    ret
40$:                                        ; slot e holds tile b + 256 c? carry clear: yes (b, c, d, e kept)
    ld   hl, #_story_scratch
    add  hl, de
    ld   a, (hl)
    cp   a, b
    jr   nz, 44$
    push bc
    ld   a, e
    srl  a
    srl  a
    ld   l, a
    ld   h, #0
    ld   bc, #_story_scratch + 176
    add  hl, bc
    ld   b, (hl)
    ld   a, e
    and  a, #3
    add  a, a
    ld   c, a
    ld   a, b
    inc  c
41$:
    dec  c
    jr   z, 42$
    srl  a
    jr   41$
42$:
    and  a, #3
    pop  bc
    cp   a, c
    jr   nz, 44$
    or   a, a
    ret
44$:
    scf
    ret
__endasm;
}
#endif
// Work on the add job's line: at most cap cells now, and what is left of this frame's list. 1: the line is complete.
static uint8_t job_run(uint8_t cap) {
    uint8_t vert = V(V_JK) == J_COL, idx = V(V_JI), a = V(V_JA), n = V(V_JN), pos = V(V_JP), first = pos, m, k, r = R_OK, cx, cy, cpc = CELL_COST(vert), j;
    smap_fc fc[8];
    uint16_t pw = 0;
    V(V_RES) = 0; V(V_RESE) = 0;
    if (!V(V_DIRECT)) { V(V_RES) = is_cgb ? 16 : 7; V(V_RESE) = is_cgb ? 4 : 2; if ((a & 31) + n > 32) V(V_RES) <<= 1; }   // (a line's runs come at the end: their overhead is kept back, twice when it wraps at the map's edge)
    while (pos < n && r == R_OK && cap) {
        m = n - pos; if (m > 8) m = 8;
        if (m > cap) m = cap;
        cx = vert ? idx : a + pos; cy = vert ? a + pos : idx;
        fetch(cx, cy, m, vert, fc);
        k = 0;
        while (k < m && cap) {
#if ASM_SMAP
            if (!is_cgb && !V(V_DIRECT)) {               // (the cells that need only a counter, in asm; see smap_burst)
                j = room() > V(V_RES) ? (uint8_t)(room() - V(V_RES)) : 0;      // (how many the drain budget still takes: a cell costs 1)
                if (j > m - k) j = m - k;
                if (j && (uint8_t)(vq_count + V(V_RESE)) <= VQ_USE) {
                    V(V_JP) = pos; V(V_BF) = pos > first; V(V_PWL) = (uint8_t)pw; V(V_PWH) = (uint8_t)(pw >> 8); V(V_BM) = j; V(V_BMODE) = 0;
                    if (pos > first) V(V_ID) = SC(S_T + T_IDS)[pos - 1];
                    smap_burst(fc + k);
                    j -= V(V_BM);                       // (the cells it took)
                    k += j; pos += j; cap -= j; V(V_RES) += j * cpc; pw = V(V_PWL) | ((uint16_t)V(V_PWH) << 8);
                    if (k >= m || !cap) break;
                }
            }
#endif
            if (!ly_ok(!(pos > first && fc[k].w == pw))) { r = R_ROOM; break; }                        // (the cells that need no load count too: a Color cell takes a line or two)
            if (pos > first && fc[k].w == pw) r = add_same(fc + k, pos, vert ? cx : cx + k, vert ? cy + k : cy, vert);
            else {
                V(V_SLOW) = 1;
#if ASM_SMAP
                if (!is_cgb) r = add_cell_d(fc + k, pos, vert ? cx : cx + k, vert ? cy + k : cy, vert);
                else
#endif
#if ASM_SMAP
                r = add_cell_c(fc + k, pos, vert ? cx : cx + k, vert ? cy + k : cy, vert);
#else
                r = is_cgb ? add_cell_c(fc + k, pos, vert ? cx : cx + k, vert ? cy + k : cy, vert) : add_cell(fc + k, pos, vert ? cx : cx + k, vert ? cy + k : cy, vert);
#endif
            }
            if (r) break;
            V(V_RES) += cpc; V(V_RESE) += CELL_ENT(vert);
            pw = fc[k].w; pos++; cap--; k++;
        }
    }
    if (!V(V_DIRECT) && pos > first) { V(V_RES) = 0; V(V_RESE) = 0; flush_line(vert, idx, a, first, pos); }
    V(V_RES) = 0; V(V_RESE) = 0;
    V(V_JP) = pos;
    if (V(V_WALK)) V(V_RATE) = (uint8_t)((V(V_RATE) + (pos - first) + 1) >> 1);     // (the pace of a walk follows it: smap.c walk_step)
    if (r == R_RES) { if (V(V_STALL) < 255) V(V_STALL)++; } else V(V_STALL) = 0;
    return pos >= n;
}

// the add job's line is given up: the cells of it already added leave again, from the end, at most DROP_CAP a frame (the job's position falls with them: a camera that turns
// back finds the job where it is). 1: none is left.
static uint8_t job_abort(void) {
    uint8_t vert = V(V_JK) == J_COL, a = V(V_JA), idx = V(V_JI), pos = V(V_JP), cap = DROP_CAP, m, k, j;
    smap_fc fc[8];
    while (pos && cap) {
        m = pos; if (m > 8) m = 8;
        if (m > cap) m = cap;
        pos -= m; cap -= m;
        fetch(vert ? idx : a + pos, vert ? a + pos : idx, m, vert, fc);
        for (k = 0; k < m; k = j) {
            for (j = k + 1; j < m && fc[j].w == fc[k].w; j++) ;
            drop_cells(fc + k, j - k);
        }
        V(V_JP) = pos;
    }
    if (pos) return 0;
    V(V_JK) = J_NONE; V(V_STALL) = 0;
    return 1;
}

// the drop job's line leaves the region: at most cap cells now (its extents left the region when the job started)
static void drop_run(uint8_t cap) {
    uint8_t vert = V(V_DK) == J_COL, a = V(V_DA), idx = V(V_DI), n = V(V_DN), pos = V(V_DP), m, k, j;
    smap_fc fc[8];
    while (pos < n && cap) {
        m = n - pos; if (m > 8) m = 8;
        if (m > cap) m = cap;
        fetch(vert ? idx : a + pos, vert ? a + pos : idx, m, vert, fc);
#if ASM_SMAP
        if (!is_cgb) {
            k = 0;
            while (k < m) {
                V(V_BM) = m - k; V(V_BMODE) = 1;
                smap_burst(fc + k);
                k = m - V(V_BM);
                if (k >= m || !ly_ok(1)) break;
                V(V_SLOW) = 1;
                drop_cells(fc + k, 1);
                k++;
            }
        } else
#endif
        for (k = 0; k < m; k = j) {
            for (j = k + 1; j < m && fc[j].w == fc[k].w; j++) ;
            if (!ly_ok(1)) break;
            V(V_SLOW) = 1;
            drop_cells(fc + k, j - k);
        }
        pos += k; cap = k < m ? 0 : cap - k;
    }
    V(V_DP) = pos;
    if (pos >= n) V(V_DK) = J_NONE;
}

// Walking, the camera follows Sal (feet at 80, 110 on the screen: low, so that the sky and the peaks above the road show: owner Q9 11-08); standing at a stop it rests at the stop's own view (smapw_view: the whole venue and Sal on the screen);
// the same camera step glides it there and back. A walk that is set off from a resting view waits (V_DONE: its direction + 1, smap.c) until the camera has come to Sal's spot:
// the walk then runs as it always did.
uint8_t smap_stop_side(uint8_t s) BANKED { return smapw_view[s][2] | (smapw_view[s][0] != 255 || smapw_view[s][1] != 255 ? 2 : 0); }   // bit 0: the side of the name tag and the venue panel at stop s (1 the bottom, 0 the top: away from the art); bit 1: the stop has a resting view

void smap_cam_target(int16_t *tx, int16_t *ty) BANKED {
    int16_t x = (int16_t)g16(V_FX) - 80, y = (int16_t)g16(V_FY) - 110;
    if (!V(V_WALK) && !V(V_DONE) && smap_stop < NSTOPS) {
        if (smapw_view[smap_stop][0] != 255) x = (int16_t)smapw_view[smap_stop][0] << 1;
        if (smapw_view[smap_stop][1] != 255) y = (int16_t)smapw_view[smap_stop][1] << 1;
    }
    *tx = x < 0 ? 0 : x > CAM_MAXX ? CAM_MAXX : x;
    *ty = y < 0 ? 0 : y > CAM_MAXY ? CAM_MAXY : y;
}

// the line a borrowed palette stands in (the hand-over): the view may not show it before the hand-over, so no cell of it wears the leaving palette's colours on the screen
static uint8_t cov_ok(uint8_t horiz, int16_t c) {
    uint8_t n = PLN;
    if (!is_cgb || PEND == NIL || ((n & 0x80) != 0) != (horiz != 0)) return 1;
    n &= 0x7F;
    return n <= (horiz ? V(V_C0) : V(V_R0)) ? (uint8_t)(c >> 3) > n : (uint8_t)((c + (horiz ? 159 : 143)) >> 3) < n;
}
static uint8_t cov_x(int16_t x) { return (uint8_t)(x >> 3) >= V(V_C0) && (uint8_t)((x + 159) >> 3) <= V(V_C1) && cov_ok(1, x); }
static uint8_t cov_y(int16_t y) { return (uint8_t)(y >> 3) >= V(V_R0) && (uint8_t)((y + 143) >> 3) <= V(V_R1) && cov_ok(0, y); }

// How many px Sal may walk on, along x (horiz) or y, toward larger (up) or smaller coordinates, before the camera that follows him would show a cell the region does not hold
// (255: as far as you like). fx or fy: his feet's coordinate on that axis. The camera follows him step for step (80 and 110: the feet's place on the screen), clamped to the world.
uint8_t smap_room(uint8_t horiz, uint8_t up, uint16_t f) BANKED {
    uint8_t lo = horiz ? V(V_C0) : V(V_R0), hi = horiz ? V(V_C1) : V(V_R1), n = PLN;
    int16_t lim;
    if (is_cgb && PEND != NIL && ((n & 0x80) != 0) == (horiz != 0)) { n &= 0x7F; if (n <= lo) lo = n + 1; else hi = n - 1; }      // (a borrowed line is not shown before its hand-over)
    if (up ? hi >= (horiz ? 63 : SMAPW_CH - 1) : !lo) return 255;
    if (up) lim = (int16_t)((hi + 1) << 3) - (horiz ? 80 : 34) - (int16_t)f;
    else lim = (int16_t)f - (int16_t)(lo << 3) - (horiz ? 80 : 110);
    return lim < 0 ? 0 : lim > 255 ? 255 : (uint8_t)lim;
}

// the camera moves toward Sal, but only where the region already covers what it will show. 1: it moved
uint8_t smap_camera_step(void) BANKED {
    int16_t cx = (int16_t)g16(V_CAMX), cy = (int16_t)g16(V_CAMY), tx, ty, nx, ny, d;
    smap_cam_target(&tx, &ty);
    if (!V(V_WALK)) {                                                 // (a walk sets them itself, by its stretches: smap.c walk_step)
        if (tx != cx) V(V_DIRX) = tx > cx ? 2 : 1;
        if (ty != cy) V(V_DIRY) = ty > cy ? 2 : 1;
    }
    d = tx - cx; if (d > CAM_SPD) d = CAM_SPD; else if (d < -CAM_SPD) d = -CAM_SPD;
    nx = cx + d;
    while (nx != cx && !cov_x(nx)) nx += nx > cx ? -1 : 1;
    d = ty - cy; if (d > CAM_SPD) d = CAM_SPD; else if (d < -CAM_SPD) d = -CAM_SPD;
    ny = cy + d;
    while (ny != cy && !cov_y(ny)) ny += ny > cy ? -1 : 1;
    if (!V(V_WALK) && nx == tx && ny == ty) { V(V_DIRX) = 0; V(V_DIRY) = 0; }
    d = tx - nx; if (d < 0) d = -d;                                   // how far the camera is behind Sal's spot (px, both axes together): the walk waits while it is too far
    d += ty > ny ? ty - ny : ny - ty;
    if (!V(V_WALK)) V(V_LAG) = d > 255 ? 255 : (uint8_t)d;           // (a walk's: smap.c walk_step sets it, 1 on a hold)
    if (nx == cx && ny == cy) return 0;
    s16(V_CAMX, nx); s16(V_CAMY, ny);
    return 1;
}

// the region follows the camera: the lines it has left drop (a few cells a frame), the lines the camera will want next (one ahead on each axis in the direction of
// travel) load (a few cells a frame): one job of each kind at a time
void smap_region_work(void) BANKED {
    uint16_t cx = g16(V_CAMX), cy = g16(V_CAMY);
    uint8_t nc0 = (uint8_t)(cx >> 3), nc1 = (uint8_t)((cx + 159) >> 3), nr0 = (uint8_t)(cy >> 3), nr1 = (uint8_t)((cy + 143) >> 3);
    uint8_t wc0 = nc0, wc1 = nc1, wr0 = nr0, wr1 = nr1, dx = V(V_DIRX) & 3, dy = V(V_DIRY) & 3, rows1st = V(V_DIRY) & 4, kind = V(V_JK), i, dk, di = 0, *eg = 0;
    int8_t egd = 0;
    if (dx == 1) wc0 = wc0 > LEAD ? wc0 - LEAD : 0;
    if (dx == 2) wc1 = wc1 + LEAD > 63 ? 63 : wc1 + LEAD;
    if (dy == 1) wr0 = wr0 > LEAD ? wr0 - LEAD : 0;
    if (dy == 2) wr1 = wr1 + LEAD > SMAPW_CH - 1 ? SMAPW_CH - 1 : wr1 + LEAD;
    i = V(V_JI);
    if ((kind == J_COL && (i < wc0 || i > wc1)) || (kind == J_ROW && (i < wr0 || i > wr1))) { if (!job_abort()) return; }       // (still taking its cells out: nothing else this frame)
    if (V(V_PANEL) || vq_held) return;
    if (V(V_DK) == J_NONE) {                         // the next line to drop, if any: its place in the region goes now, its cells a few at a time
        dk = J_COL;
        if (V(V_C0) < wc0 && V(V_C0) < V(V_C1)) { eg = &V(V_C0); egd = 1; di = (*eg)++; }
        else if (V(V_C1) > wc1 && V(V_C1) > V(V_C0)) { eg = &V(V_C1); egd = -1; di = (*eg)--; }
        else {
            dk = J_ROW;
            if (V(V_R0) < wr0 && V(V_R0) < V(V_R1)) { eg = &V(V_R0); egd = 1; di = (*eg)++; }
            else if (V(V_R1) > wr1 && V(V_R1) > V(V_R0)) { eg = &V(V_R1); egd = -1; di = (*eg)--; }
            else dk = J_NONE;
        }
        if (dk != J_NONE && V(V_JK) != J_NONE && V(V_JK) != dk && !V(V_STALL)) { *eg -= egd; dk = J_NONE; }   // (an add job across it would add cells of the line that leaves: the line stays until the job is done, unless the job waits for a slot)
        if (dk != J_NONE) {
            if (V(V_JK) != J_NONE && V(V_JK) != dk && !job_abort()) { *eg -= egd; return; }     // (the job waits for a slot: it goes first; the line stays)
            V(V_DK) = dk; V(V_DI) = di; V(V_DP) = 0;
            if (dk == J_COL) { V(V_DA) = V(V_R0); V(V_DN) = V(V_R1) - V(V_R0) + 1; }
            else { V(V_DA) = V(V_C0); V(V_DN) = V(V_C1) - V(V_C0) + 1; }
        }
    }
    if (V(V_DK) != J_NONE) drop_run(is_cgb ? 22 : DROP_CAP);
    if (is_cgb && PEND != NIL) pal_hand();
    if (V(V_JK) == J_NONE) {
        if (rows1st && V(V_R0) > wr0) { V(V_JK) = J_ROW; V(V_JI) = V(V_R0) - 1; }     // (walking down or up: the rows first, a column's lead can wait)
        else if (rows1st && V(V_R1) < wr1) { V(V_JK) = J_ROW; V(V_JI) = V(V_R1) + 1; }
        else if (V(V_C0) > wc0) { V(V_JK) = J_COL; V(V_JI) = V(V_C0) - 1; }
        else if (V(V_C1) < wc1) { V(V_JK) = J_COL; V(V_JI) = V(V_C1) + 1; }
        else if (V(V_R0) > wr0) { V(V_JK) = J_ROW; V(V_JI) = V(V_R0) - 1; }
        else if (V(V_R1) < wr1) { V(V_JK) = J_ROW; V(V_JI) = V(V_R1) + 1; }
        else return;
        if (V(V_JK) == J_COL) { V(V_JA) = V(V_R0); V(V_JN) = V(V_R1) - V(V_R0) + 1; }
        else { V(V_JA) = V(V_C0); V(V_JN) = V(V_C1) - V(V_C0) + 1; }
        V(V_JP) = 0;
    }
    if (job_run(is_cgb ? 22 : ADD_CAP)) {                          // complete: the line is part of the region
        if (V(V_JK) == J_COL) { if (V(V_JI) < V(V_C0)) V(V_C0) = V(V_JI); else V(V_C1) = V(V_JI); }
        else { if (V(V_JI) < V(V_R0)) V(V_R0) = V(V_JI); else V(V_R1) = V(V_JI); }
        V(V_JK) = J_NONE;
    }
}

// LCD off (smap_enter): the columns c0..c1 of the view into the map, one add job each; the region is then [c0, c1] x the view's rows
void smap_fill_view(uint8_t c0, uint8_t c1) BANKED {
    uint8_t c;
    V(V_DIRECT) = 1;
    for (c = c0; c <= c1; c++) {
        V(V_JK) = J_COL; V(V_JI) = c; V(V_JA) = V(V_R0); V(V_JN) = V(V_R1) - V(V_R0) + 1; V(V_JP) = 0;
        job_run(255);
        V(V_C1) = c;
    }
    V(V_JK) = J_NONE; V(V_DIRECT) = 0;
}

void smap_pin_town(void) BANKED {
    V(V_DIRECT) = 1;
    if (is_cgb) { pal_take(SMAPW_PAL_TOWN); pal_count(SMAPW_PAL_TOWN, 1); }
    V(V_DIRECT) = 0;
}

// ---- the special runs of the copy list ---------------------------------------------------------------------------------------------------------------------------
// The map registers render.c's smap_vbl after vq_vbl (smap_enter / leave): the list went out, its special entries (bank 2/3) are done here. Every other screen's drain is untouched.
extern volatile uint8_t vq_ready;

#if ASM_SMAP
static void sp_run(void) {
__asm
    ldh  a, (0x4F)
    push af                 ; the interrupted code's VRAM bank
    push bc
    ld   hl, #_vq
1$:
    ld   a, l
    cp   a, #<(_vq + 192)
    jr   nz, 2$
    ld   a, h
    cp   a, #>(_vq + 192)
    jr   z, 9$
2$:
    ld   a, (hl)            ; n: 0 is the mark that ends the list
    or   a, a
    jr   z, 9$
    push hl
    inc  hl
    ld   a, (hl+)           ; bank
    bit  1, a
    jr   z, 8$
    ldh  (0x4F), a
    ld   e, (hl)            ; src
    inc  hl
    ld   d, (hl)
    inc  hl
    inc  hl
    inc  hl                 ; -> pad[0]
    ld   a, (hl+)
    ld   c, a
    ld   a, (hl)            ; pad[1]
    bit  7, a
    jr   z, 5$
    ld   b, a               ; stride: n - 1 in bits 10-14, the map offset in bits 0-9
    srl  b
    srl  b
    res  5, b
    inc  b
    and  a, #3
    add  a, #0x98
    ld   h, a
    ld   l, c
6$:
    ld   a, (de)
    inc  de
    ld   (hl), a
    ld   a, l
    add  a, #32
    ld   l, a
    jr   nc, 7$
    inc  h
7$:
    dec  b
    jr   nz, 6$
    jr   8$
5$:                         ; a tile: dst = 0x8000 + 16 * (a:c), one general-purpose DMA block (the CPU waits for it)
    ld   b, a
    ld   a, c
    swap a
    ld   h, a
    and  a, #0xF0
    ld   l, a
    ld   a, h
    and  a, #0x0F
    ld   h, a
    ld   a, b
    swap a
    and  a, #0xF0
    add  a, h
    add  a, #0x80
    ld   h, a
    ld   a, d
    ldh  (0x51), a
    ld   a, e
    ldh  (0x52), a
    ld   a, h
    ldh  (0x53), a
    ld   a, l
    ldh  (0x54), a
    xor  a, a
    ldh  (0x55), a
8$:
    pop  hl
    inc  hl
    res  1, (hl)            ; (done: a later scan passes it)
    dec  hl
    ld   de, #8
    add  hl, de
    jr   1$
9$:
    pop  bc
    pop  af
    and  a, #1
    ldh  (0x4F), a
__endasm;
}
#else
static void sp_run(void) {                          // the C twin of the asm above
    uint8_t vbk = VBK_REG, i, k, n;
    uint16_t w, d;
    uint8_t *p;
    const uint8_t *s;
    for (i = 0; i != SMAP_VQ_MAX && vq[i].n; i++) {
        if (!(vq[i].bank & 2)) continue;
        vq[i].bank &= 1;   // (done; its bank bit is read first below)
        VBK_REG = vq[i].bank & 1;
        s = vq[i].src;
        w = vq[i].pad[0] | ((uint16_t)vq[i].pad[1] << 8);
        if (w & 0x8000) {
            n = ((w >> 10) & 31) + 1;
            p = (uint8_t *)(0x9800 + (w & 0x3FF));
            for (k = 0; k != n; k++) { *p = *s++; p += 32; }
        } else {
            d = 0x8000 + (w << 4);
            *(volatile uint8_t *)0xFF51 = (uint8_t)((uint16_t)s >> 8);
            *(volatile uint8_t *)0xFF52 = (uint8_t)(uint16_t)s;
            *(volatile uint8_t *)0xFF53 = (uint8_t)(d >> 8);
            *(volatile uint8_t *)0xFF54 = (uint8_t)d;
            *(volatile uint8_t *)0xFF55 = 0;
        }
    }
    VBK_REG = vbk & 1;
}
#endif

// After vq_vbl: if it just took a list (nothing ready, nothing queued, the list's first entry still there), its special entries go out now and the list's head is cleared.
// (A list the main thread is still building has vq_count > 0 or vq_ready, and is left alone.)
void smap_vbl(void);                                  // src/render.c
extern uint8_t game_state, story_phase;
void smap_isr(void) BANKED {
    if (game_state != GS_STORY || story_phase != STORY_PHASE_MAP) { remove_VBL(smap_vbl); return; }   // (the map was left: the next screen's drain is the plain one; this was the last handler)
    if (vq_ready || vq_count || !vq[0].n) return;
    sp_run();
    vq[0].n = 0;
}

// smap_enter: no entry of an earlier list may look like a special run still to do
void smap_isr_arm(void) BANKED {
    uint8_t i;
    for (i = 0; i != SMAP_VQ_MAX; i++) { vq[i].n = 0; vq[i].bank = 0; }
}
