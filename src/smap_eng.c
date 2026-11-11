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

// DMG: the slot table, 176 tile ids (0x3FF: nothing resident), laid over A_TBL..A_TBL + 351. The slot of every cell is planned at build time (tools/smap_world/route.py): a cell's slot comes
// with it (smap_fc.aux), the tile is loaded when the slot holds another one, and nothing counts uses or searches: a line that leaves the region costs nothing.
#define DTBL ((uint16_t *)SC(A_TBL))

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

// DMG: one cell into the region. Its slot is the cell's own (planned: smap_fc.aux), its id the slot's; the tile is loaded when the slot holds another one. R_OK, or why not (nothing
// changed then). The id goes into the line buffer at k (the line's map entries are queued by the caller when it has added what it will this frame).
static uint8_t add_cell_d(const smap_fc *f, uint8_t k, uint8_t cx, uint8_t cy, uint8_t vert) {
    uint16_t t = f->w & 0x3FF, *e = DTBL + (uint8_t)f->aux;
    uint8_t s = (uint8_t)f->aux, id = pool_id(s), need = *e != t, cost, ents = 0;
    if (!V(V_DIRECT)) {
        cost = CELL_COST(vert);
        if (need) { if (V(V_NSTG) >= NSTG_MAX) return R_ROOM; cost += 19; ents = 1; }
        if (room() < (uint8_t)(cost + V(V_RES)) || (uint8_t)(vq_count + ents + V(V_RESE)) > VQ_USE) return R_ROOM;
    }
    if (need) { *e = t; tile_load(0, id, t); }
    SC(S_T + T_IDS)[k] = id;
    if (V(V_DIRECT)) *(volatile uint8_t *)map_addr(cx, cy) = id;
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


// the next cell shows what the one before it does (the same tile and palette, already resident): no lookup, no load
static uint8_t add_same(const smap_fc *f, uint8_t k, uint8_t cx, uint8_t cy, uint8_t vert) {
    uint8_t direct = V(V_DIRECT), id = SC(S_T + T_IDS)[k - 1], att = 0;
    if (!direct) {
        if (room() < (uint8_t)(CELL_COST(vert) + V(V_RES)) || (uint8_t)(vq_count + CELL_ENT(vert) + V(V_RESE)) > VQ_USE) return R_ROOM;
    }
    if (is_cgb) { att = SC(A_IDA)[k - 1]; SC(A_IDA)[k] = att; pal_count((uint8_t)((f->w >> 10) & 31), 1); }
    SC(S_T + T_IDS)[k] = id;
    if (direct) {
        *(volatile uint8_t *)map_addr(cx, cy) = id;
        if (is_cgb) { VBK_REG = VBK_BANK_1; *(volatile uint8_t *)map_addr(cx, cy) = att; VBK_REG = VBK_BANK_0; }
    }
    return R_OK;
}

// n cells that show f's tile leave the region (Color: the palette's count; the DMG's slots are not counted)
static void drop_cells(const smap_fc *f, uint8_t n) {
    pal_count((uint8_t)((f->w >> 10) & 31), -(int8_t)n);
}

static void fetch(uint8_t cx, uint8_t cy, uint8_t n, uint8_t vert, smap_fc *out) {
    if (is_cgb) smap_c_fetch(cx, cy, n, vert, V(V_STATE), out); else { smap_d_fetch(cx, cy, n, vert, V(V_STATE), out); if (V(V_STATE) < 11) smap_d_fix(cx, cy, n, vert, out); }
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
// DMG, asm (behind ASM_SMAP; the C twin is add_cell_d, which the same cells run without it): the cells of a fetched chunk whose slot already holds their tile: their ids into the line's
// id buffer. It stops at the first cell that needs a load (the C code takes that one) and leaves the count of cells not done in V_BM. It queues nothing: job_run has counted the room
// for the V_BM cells, and the line goes out as one entry when it is done. In: de = the first cell (word, slot); V_JP the cell's position in the line (= its index in the id buffer),
// V_BM the cells to do. (the offsets below: S_V 396, V_JP 34, V_BM 58; the id buffer 496, the table 0)
typedef char smap_asm_offsets[(S_V == 396 && S_T + T_IDS == 496 && A_TBL == 0 && V_JP == 34 && V_BM == 58 && SMAPW_POOL == 176 && sizeof(smap_fc) == 4) ? 1 : -1];
static void smap_burst(const smap_fc *f) __naked {
    (void)f;
__asm
    push bc
    ld   a, (_story_scratch + 430)          ; V_JP
    ld   c, a
    ld   b, #0
    ld   hl, #_story_scratch + 496
    add  hl, bc
    ld   b, h
    ld   c, l                               ; bc = the id buffer at the position
1$:
    ld   a, (_story_scratch + 454)          ; V_BM
    or   a, a
    jr   z, 9$
    inc  de
    inc  de
    ld   a, (de)                            ; the cell's slot
    ld   l, a
    dec  de
    dec  de
    ld   h, #0
    add  hl, hl
    ld   a, l
    add  a, #<_story_scratch
    ld   l, a
    ld   a, h
    adc  a, #>_story_scratch
    ld   h, a                               ; hl = the slot's entry in the table
    ld   a, (de)                            ; the tile, low byte
    cp   a, (hl)
    jr   nz, 9$
    inc  hl
    inc  de
    ld   a, (de)
    dec  de
    and  a, #3
    cp   a, (hl)
    jr   nz, 9$                             ; (the slot holds another tile: a load)
    inc  de
    inc  de
    ld   a, (de)                            ; the slot again: its id (pool_id)
    dec  de
    dec  de
    cp   a, #36
    jr   c, 2$
    add  a, #57
2$:
    ld   (bc), a
    inc  bc
    ld   a, e
    add  a, #4
    ld   e, a
    jr   nc, 3$
    inc  d
3$:
    ld   hl, #_story_scratch + 454
    dec  (hl)
    jr   1$
9$:
    pop  bc
    ret
__endasm;
}
#endif

// Color: work on the add job's line: at most cap cells now, and what is left of this frame's list. 1: the line is complete. (The DMG's is job_run_d: the two models' lines are
// planned differently, and a change to the DMG's must not move a cycle of the Color's.)
static uint8_t job_run_c(uint8_t cap) {
    uint8_t vert = V(V_JK) == J_COL, idx = V(V_JI), a = V(V_JA), n = V(V_JN), pos = V(V_JP), first = pos, m, k, r = R_OK, cx, cy, cpc = CELL_COST(vert);
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
            if (!ly_ok(!(pos > first && fc[k].w == pw))) { r = R_ROOM; break; }                        // (the cells that need no load count too: a Color cell takes a line or two)
            if (pos > first && fc[k].w == pw) r = add_same(fc + k, pos, vert ? cx : cx + k, vert ? cy + k : cy, vert);
            else {
                V(V_SLOW) = 1;
                r = add_cell_c(fc + k, pos, vert ? cx : cx + k, vert ? cy + k : cy, vert);
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

// DMG: work on the add job's line: at most cap cells now, and what is left of this frame's list. 1: the line is complete.
static uint8_t job_run_d(uint8_t cap) {
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
            if (!is_cgb && !V(V_DIRECT)) {               // (the cells that need nothing but their id, in asm; see smap_burst)
                j = room() > V(V_RES) ? (uint8_t)(room() - V(V_RES)) : 0;      // (how many the drain budget still takes: a cell costs 1)
                if (j > m - k) j = m - k;
                if (j && (uint8_t)(vq_count + V(V_RESE)) <= VQ_USE) {
                    V(V_JP) = pos; V(V_BM) = j;
                    smap_burst(fc + k);
                    j -= V(V_BM);                       // (the cells it took)
                    if (j) { k += j; pos += j; cap -= j; V(V_RES) += j * cpc; pw = fc[k - 1].w; }
                    if (k >= m || !cap) break;
                }
            }
#endif
            if (!ly_ok(!(pos > first && fc[k].w == pw))) { r = R_ROOM; break; }                        // (the cells that need no load count too: a Color cell takes a line or two)
            if (pos > first && fc[k].w == pw) r = add_same(fc + k, pos, vert ? cx : cx + k, vert ? cy + k : cy, vert);
            else {
                V(V_SLOW) = 1;
                r = add_cell_d(fc + k, pos, vert ? cx : cx + k, vert ? cy + k : cy, vert);
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
    if (!is_cgb) { V(V_JK) = J_NONE; V(V_STALL) = 0; return 1; }      // (the DMG's slots are not counted: the cells already added stay, resident, and cost nothing)
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
static void region_work(void) {
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
    if (!is_cgb) {                                   // the DMG: a line that leaves costs nothing (route plan): the region is the wanted window at once, an add job that spans a line that left starts over
        i = 0;
        while (V(V_C0) < wc0 && V(V_C0) < V(V_C1)) { V(V_C0)++; i |= J_COL; }
        while (V(V_C1) > wc1 && V(V_C1) > V(V_C0)) { V(V_C1)--; i |= J_COL; }
        while (V(V_R0) < wr0 && V(V_R0) < V(V_R1)) { V(V_R0)++; i |= J_ROW; }
        while (V(V_R1) > wr1 && V(V_R1) > V(V_R0)) { V(V_R1)--; i |= J_ROW; }
        if (V(V_JK) != J_NONE && (i & (V(V_JK) ^ 3))) V(V_JK) = J_NONE;
    } else if (V(V_DK) == J_NONE) {                  // the next line to drop, if any: its place in the region goes now, its cells a few at a time
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
    if (is_cgb ? job_run_c(22) : job_run_d(ADD_CAP)) {                          // complete: the line is part of the region
        if (V(V_JK) == J_COL) { if (V(V_JI) < V(V_C0)) V(V_C0) = V(V_JI); else V(V_C1) = V(V_JI); }
        else { if (V(V_JI) < V(V_R0)) V(V_R0) = V(V_JI); else V(V_R1) = V(V_JI); }
        V(V_JK) = J_NONE;
    }
}

// THE TILE ANIMATIONS (stage 3, build/smap_an.c, tools/smap_world/anims.py): a group of map cells shows one tile (its own id); its picture changes at ticks of a 256-frame loop (V_TICK, the
// map's frame counter: no state of its own). An event rewrites the tile's 16 bytes in VRAM from the group's frame image, in VBlank through the copy list, only when the tile is resident (Color:
// its slot holds its variant; DMG: the allocator has it). A tile that is not there is not drawn: when it comes into the region it loads as the map holds it (image 0) and takes the next
// change. The writes use what the cell loads left over (the staging, the room in the list), after them: a frame with none left skips the event and the next change sets the picture right.
#define AN_COST (is_cgb ? 9 : 19)
#define AN_LY   (is_cgb ? 90 : 30)
static void anim_step(void) {
    uint8_t t = V(V_TICK), n, i, bank, id, ev[5 * SMAPW_AN_MAX], *p, *d;
    uint16_t tile, aux;
    if (!(smapw_anbits[t >> 3] & (1 << (t & 7))) || V(V_DIRECT)) return;
    n = smap_an_due(t, is_cgb, ev, &V(V_C0));
    for (i = 0, p = ev; i < n; i++, p += 5) {
        tile = p[0] | ((uint16_t)p[1] << 8); aux = p[2] | ((uint16_t)p[3] << 8);
        if (is_cgb) {
            if (nib_get(aux & 0x1FF) != ((aux >> 9) & 3)) continue;                        // (not resident)
            bank = (aux & 0x1FF) >= SMAPW_POOL;
            id = pool_id(bank ? (uint8_t)((aux & 0x1FF) - SMAPW_POOL) : (uint8_t)(aux & 0x1FF));
        } else {
            id = (uint8_t)aux;
            if (DTBL[id] != tile) continue;                                                   // (not resident)
            id = pool_id(id); bank = 0;
        }
        if (V(V_NSTG) >= NSTG_MAX || room() < (uint8_t)(AN_COST + (bank << 1) + V(V_RES)) || (uint8_t)(vq_count + 1 + V(V_RESE)) > VQ_USE) return;
        d = is_cgb ? (uint8_t *)(((uint16_t)SC(A_XSTG) + 15) & 0xFFF0) + (V(V_NSTG) << 4) : SC(S_T + T_TILES + (V(V_NSTG) << 4));
        smap_an_img(is_cgb, p[4], d);
        if (is_cgb) qsp(bank, d, tile_addr(id), 2); else qraw(0, d, tile_addr(id), 16);
        V(V_NSTG)++;
    }
}

void smap_region_work(void) BANKED {
    region_work();
    if (LY_REG < AN_LY || LY_REG >= 144) anim_step();                      // (only on a frame with lines to spare: the walk's worst frames end right at the cliff, a few lines more and the frame is missed)
}

// LCD off (smap_enter): the columns c0..c1 of the view into the map, one add job each; the region is then [c0, c1] x the view's rows
void smap_fill_view(uint8_t c0, uint8_t c1) BANKED {
    uint8_t c;
    V(V_DIRECT) = 1;
    for (c = c0; c <= c1; c++) {
        V(V_JK) = J_COL; V(V_JI) = c; V(V_JA) = V(V_R0); V(V_JN) = V(V_R1) - V(V_R0) + 1; V(V_JP) = 0;
        if (is_cgb) job_run_c(255); else job_run_d(255);
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
