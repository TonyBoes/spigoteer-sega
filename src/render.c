// The picture: the BG shadow of the bars' wall rows (where the patrons stand), dirty spans, the VBlank copy
// queue, and the sprites that are not mugs (bartender, tip coin, dancers).
//
// A frame's BG changes are composed into sh_tile/sh_attr during the logic phase and turned into a list of copy
// commands (queue_vram); the list is executed by one small hand-written loop at the start of the next frame,
// inside VBlank (vq_drain). The drain never runs outside VBlank: if a frame starts late, the list waits for the
// next VBlank and nothing more is queued meanwhile, so the picture can lag a frame but never loses a write.
#include <gb/gb.h>
#include <gb/cgb.h>
#include <stdint.h>

#include "game.h"

uint8_t row_buf[20];
uint8_t score_tiles[6];      // the HUD digits as BG tile ids, prepared outside VBlank
uint8_t lives_tiles[3];

const uint8_t bar_bit[NUM_BARS] = { 1, 2, 4, 8 };
#define OAM_Y(b) ((uint8_t)(BAR_TOP_Y(b) + 16u))
const uint8_t bar_oam_y[NUM_BARS] = { OAM_Y(0), OAM_Y(1), OAM_Y(2), OAM_Y(3) };

// Generic byte copy, hand-written (SDCC's loops cost ~160 cycles per byte, GBDK's memcpy ~500 cycles of setup
// per call): copy_n() copies cp_n bytes cp_src -> cp_dst. Arguments travel in globals so the asm does not depend on the calling convention. cp_n >= 1.
// vram_put() uses copy_n() for raw BG map writes (map at 0x9800): only with the LCD off or during VBlank.
uint16_t cp_dst, cp_src;
uint8_t  cp_n;

void copy_n(void) {
__asm
    push bc
    ld   a, (_cp_src)
    ld   e, a
    ld   a, (_cp_src + 1)
    ld   d, a
    ld   hl, #_cp_dst
    ld   a, (hl+)
    ld   h, (hl)
    ld   l, a
    ld   a, (_cp_n)
    ld   b, a
1$:
    ld   a, (de)
    inc  de
    ld   (hl+), a
    dec  b
    jr   nz, 1$
    pop  bc
__endasm;
}

// Two rows: cp_n bytes cp_src -> cp_dst, then cp_n bytes cp_src + 20 -> cp_dst + 32 (a bar's two wall rows from
// base_tile / base_attr, 20 wide, into the 32-wide shadow rows). 1 <= cp_n <= 20.
static void copy_2rows(void) {
__asm
    push bc
    ld   a, (_cp_src)
    ld   e, a
    ld   a, (_cp_src + 1)
    ld   d, a
    ld   hl, #_cp_dst
    ld   a, (hl+)
    ld   h, (hl)
    ld   l, a
    ld   a, (_cp_n)
    ld   c, a
    ld   b, a
1$:
    ld   a, (de)
    inc  de
    ld   (hl+), a
    dec  b
    jr   nz, 1$
    ld   a, #20             ; de += 20 - n
    sub  a, c
    add  a, e
    ld   e, a
    jr   nc, 2$
    inc  d
2$:
    ld   a, #32             ; hl += 32 - n
    sub  a, c
    add  a, l
    ld   l, a
    jr   nc, 3$
    inc  h
3$:
    ld   b, c
4$:
    ld   a, (de)
    inc  de
    ld   (hl+), a
    dec  b
    jr   nz, 4$
    pop  bc
__endasm;
}

void vram_put(uint8_t x, uint8_t y, const uint8_t *src, uint8_t n) {
    cp_dst = 0x9800 + ((uint16_t)y << 5) + x;
    cp_src = (uint16_t)src;
    cp_n = n;
    copy_n();
}

void put_row(uint8_t y) {
    vram_put(0, y, row_buf, 20);
}

// ---- patrons: shadow of the two wall rows of each bar + dirty spans ---------------
// A patron redraw marks the columns it leaves and covers dirty (mark_dirty). At the end of the frame's logic
// queue_vram() takes a chunk of each dirty span (as many as the VBlank budget allows), composes exactly those
// columns into the shadow rows (wall, then the bar's patrons over it) and queues them. Composing only what is
// sent bounds the work per frame; columns left over stay dirty and are composed, with the then current picture,
// when their turn comes. A patron redraw touches 3-4 columns x 2 rows x (tile + attribute) = 16-24 bytes, so
// even 4 simultaneous redraws stay inside VBlank (vram_ly_min proves it in the tests).
// rows indexed (bar << 1) | r, 32 wide: power-of-two strides keep SDCC from calling its slow multiply
static uint8_t sh_rows[2][NUM_BARS * 2][32];   // [0]: tile ids, [1]: CGB attributes, right behind
#define sh_tile sh_rows[0]
#define sh_attr sh_rows[1]
static uint8_t dirty_x0[NUM_BARS], dirty_x1[NUM_BARS];
static uint8_t attr_x0[NUM_BARS], attr_x1[NUM_BARS];   // CGB: the part of the dirty span whose attributes changed
uint8_t vram_pending;             // dirty spans left to queue (keeps idle frames cheap)

// The bar's two wall rows without patrons (door, wall, spout, keg), tile ids and CGB attributes by row and column:
// what compose_dirty() restores under (and around) the patrons. Filled from the level's venue (load_venue, M9), the
// same picture the level screen starts with. Row 1 follows row 0 directly (restore_base relies on it).
uint8_t base_tile[2][20], base_attr[2][20];

void mark_dirty(uint8_t b, uint8_t x0, uint8_t x1) {
    if (x1 > 20) x1 = 20;
    if (x0 < dirty_x0[b]) dirty_x0[b] = x0;
    if (x1 > dirty_x1[b]) dirty_x1[b] = x1;
    vram_pending = 1;
}

// A patron appeared, left, or moved to other columns: the attributes of those columns may change as well. (A
// patron moving within his columns changes tile ids only, which keeps most CGB redraws at half the work.)
void mark_dirty_attrs(uint8_t b, uint8_t x0, uint8_t x1) {
    mark_dirty(b, x0, x1);
    if (x1 > 20) x1 = 20;
    if (x0 < attr_x0[b]) attr_x0[b] = x0;
    if (x1 > attr_x1[b]) attr_x1[b] = x1;
}

extern uint8_t bar_list[NUM_BARS][MAX_PATRONS], bar_n[NUM_BARS];
void build_lists(void);

// Compose columns cz_x0..cz_x1-1 of a bar: the wall restored over the span, then each patron of the bar stamped
// over it in slot order. Split into small functions on purpose: SDCC keeps their few values in registers; one
// big function spends most of its time moving spilled values to and from the stack.
static uint8_t cz_x0, cz_x1, cz_pal;      // span of the bar being composed, palette of the patron being stamped
static uint8_t *cz_tile, *cz_attr;        // its first wall row in sh_tile / sh_attr (cz_attr 0 on DMG)

#define ST(v, s) ((uint8_t)(PATRON_TILE_BASE + (v) * 48u + (s) * 6u))   // first tile of variant v pre-shifted by s px
#define ST8(v) ST(v, 0), ST(v, 1), ST(v, 2), ST(v, 3), ST(v, 4), ST(v, 5), ST(v, 6), ST(v, 7)
static const uint8_t stamp_tile[32] = { ST8(0), ST8(1), ST8(2), ST8(0) };   // (variant 3 does not occur)
#define SB(v) ((uint8_t)(PATRON_BACK_BASE + (v) * 4u))                     // first back-view tile of variant v
static const uint8_t back_tile[4] = { SB(0), SB(1), SB(2), SB(0) };

static uint8_t st_t;                      // first tile of the patron being stamped

static void stamp_look(uint8_t s, uint8_t d) {           // st_t and cz_pal for patron s drawn at x d (front view)
    uint8_t v = patron_variant[s] & 3;
    cz_pal = BGPAL_PATRON + v;
    st_t = stamp_tile[(v << 3) | (d & 7)];
}

static void stamp3(uint8_t c) {                          // the whole 3x2 footprint at column c
    uint8_t *r = cz_tile + c, t = st_t;
    r[0] = t; r[1] = t + 1; r[2] = t + 2;
    r += 32;
    r[0] = t + 3; r[1] = t + 4; r[2] = t + 5;
    if (!cz_attr) return;
    r = cz_attr + c; t = cz_pal;
    r[0] = t; r[1] = t; r[2] = t;
    r += 32;
    r[0] = t; r[1] = t; r[2] = t;
}

static void put_col(uint8_t c, uint8_t t) {              // one 1x2 column, if inside the span
    uint8_t *r;
    if (c < cz_x0 || c >= cz_x1) return;
    r = cz_tile + c;
    r[0] = t; r[32] = t + 3;
    if (!cz_attr) return;
    r = cz_attr + c;
    r[0] = cz_pal; r[32] = cz_pal;
}

static void put_back_col(uint8_t c, uint8_t t) {         // one 1x2 column of a back view (2x2 tiles), if inside the span
    uint8_t *r;
    if (c < cz_x0 || c >= cz_x1) return;
    r = cz_tile + c;
    r[0] = t; r[32] = t + 2;
    if (!cz_attr) return;
    r = cz_attr + c;
    r[0] = cz_pal; r[32] = cz_pal;
}

// Patron s, watching the show, in its back view at column c (on a multiple of 8 px: 2 columns; the 3rd column of
// its footprint stays wall).
static void stamp_back(uint8_t s, uint8_t c) {
    uint8_t v = patron_variant[s] & 3;
    cz_pal = BGPAL_PATRON + v;
    v = back_tile[v];
    put_back_col(c, v); put_back_col(c + 1, v + 1);
}

// Patron s over the bar being composed: the columns of its 3x2 footprint that lie inside the span.
static void stamp(uint8_t s) {
    uint8_t d = patron_draw[s], c;
    if (d == 255) return;                                 // not drawn yet
    c = (d & ~DRAW_BACK) >> 3;
    if (c + 3 <= cz_x0 || c >= cz_x1) return;             // all outside the span
    if (d & DRAW_BACK) { stamp_back(s, c); return; }
    stamp_look(s, d);
    if (c >= cz_x0 && c + 3 <= cz_x1) { stamp3(c); return; }
    put_col(c, st_t); put_col(c + 1, st_t + 1); put_col(c + 2, st_t + 2);
}

static uint8_t cz_attrs;                  // compose the attributes too (CGB, and they changed)

static void restore_base(void) {                         // the wall over the span (cz_*), both rows
    uint8_t x0 = cz_x0;
    cp_n = cz_x1 - x0;
    cp_dst = (uint16_t)(cz_tile + x0); cp_src = (uint16_t)&base_tile[0][x0]; copy_2rows();
    if (!cz_attrs) { cz_attr = 0; return; }
    cz_attr = cz_tile + sizeof sh_tile;                   // sh_attr follows sh_tile
    cp_dst = (uint16_t)(cz_attr + x0); cp_src = (uint16_t)&base_attr[0][x0]; copy_2rows();
}

static void stamp_bar(uint8_t b) {
    const uint8_t *q = bar_list[b];
    uint8_t n;
    for (n = bar_n[b]; n; n--, q++)
        if (patron_state[*q] != PATRON_NONE) stamp(*q);
}

static void compose_bar(uint8_t b) {                     // columns cz_x0..cz_x1-1 of bar b
    if (!lists_ok) build_lists();
    cz_tile = sh_tile[b << 1];
    restore_base();
    stamp_bar(b);
}

// Quick redraws (M8b): a patron who moved within his own 3 columns (a 1 px step, front view before and after)
// changes only the 6 tile ids of his footprint, and nobody else ever stands in those columns (PATRON_SPACING 32 >
// the 24 px footprint). So instead of a dirty span (wall restored, every patron of the bar stamped) he goes on
// this list, and queue_vram() writes his 6 ids straight into the shadow and queues them, tiles only: about a
// third of a span's cost. Walking at 1 px steps makes this the common redraw.
static uint8_t quick_list[MAX_PATRONS], quick_n;
static uint8_t quick_on[MAX_PATRONS];        // p is on quick_list

void mark_quick(uint8_t p) {
    if (quick_on[p]) return;
    quick_on[p] = 1;
    quick_list[quick_n++] = p;
    vram_pending = 1;
}

void clear_dirty(void) {
    uint8_t b;
    vram_pending = 0;
    while (quick_n) quick_on[quick_list[--quick_n]] = 0;
    for (b = 0; b < NUM_BARS; b++) { dirty_x0[b] = 255; dirty_x1[b] = 0; attr_x0[b] = 255; attr_x1[b] = 0; }
}

static void write_span(uint8_t b, uint8_t x0, uint8_t x1) {
    uint8_t r, y, w = x1 - x0;
    for (r = 0; r < 2; r++) {
        y = BAR_TOP_ROW(b) + r;
        vram_put(x0, y, &sh_tile[(b << 1) | r][x0], w);
        if (is_cgb) {
            VBK_REG = VBK_BANK_1;
            vram_put(x0, y, &sh_attr[(b << 1) | r][x0], w);
            VBK_REG = VBK_BANK_0;
        }
    }
}

void write_all_bars(void) {          // LCD off only
    uint8_t b;
    cz_x0 = 0; cz_x1 = 20; cz_attrs = is_cgb;
    for (b = 0; b < NUM_BARS; b++) { compose_bar(b); write_span(b, 0, 20); }
    clear_dirty();
}

// ---- VBlank copy queue --------------------------------------------------------------
// SDCC code is far too slow to do the BG writes inside VBlank (a single 3-tile row
// span cost ~1500 cycles). So the logic phase builds a list of copy commands
// (what to copy where, in which VRAM bank), and one small hand-written loop executes
// it, ~40 cycles per byte, from the VBlank interrupt: vq_vbl() is a GBDK VBL handler
// and runs right after the OAM DMA, at the very start of VBlank. That makes "only
// inside VBlank" structural: a frame that overruns cannot drain outside it. The
// builder keeps a cost budget per frame; bars that do not fit stay dirty and go out
// next frame (a patron appears a frame late, nothing tears). drain_ticks_max is the
// longest drain seen, in DIV ticks of 256 cycles; VBlank is ~17 ticks long.
//
// Handshake: the frame's logic only touches the queue while vq_ready is 0 and sets it
// when the list is complete (vq_frame_end). The interrupt drains only a ready list.
// A list that was not drained (the frame overran past VBlank, or the interrupt came
// too late) stays: the next frame finds vq_ready still set, takes the list back
// (vq_frame_begin) and queues nothing more, and it goes out with the next VBlank.
typedef struct {
    uint8_t n;            // bytes to copy (>= 1)
    uint8_t bank;         // VRAM bank to select (0 tiles, 1 CGB attributes)
    const uint8_t *src;
    uint8_t *dst;
    uint8_t pad[2];
} vq_entry_t;               // 8 bytes (indexing is a shift, not a multiply); the asm below relies on this layout
#define VQ_MAX        24
#define VQ_BUDGET     64    // cost units (~40 cycles each) per frame, see queue_vram
#define VQ_CHUNK       6    // widest span queued for one bar row at a time
#define VQ_LATEST_LY 147    // a full-budget drain (~7 lines, drain_ticks_max) that starts later could run into line 0
vq_entry_t vq[VQ_MAX];
uint8_t    vq_count;
volatile uint8_t vq_ready;      // the list is complete: the VBlank interrupt may execute it
uint8_t    drain_ticks_max;     // longest drain so far in DIV ticks (256 cycles each); VBlank is ~17 ticks
uint8_t    vq_latest_ly = VQ_LATEST_LY;   // last LY a drain may start on (a variable so a test can move it)
uint8_t    vq_held;             // this frame found last frame's list still waiting: nothing more is queued
uint16_t   vq_late;             // VBlanks whose drain was refused (not early enough in VBlank)
uint8_t    vq_drain_ly_max;     // latest LY a drain started on
uint8_t    vq_drain_ly_last;    // LY the last drain attempt saw
uint8_t    vq_end_ly_max;       // latest LY a drain ended on (154 + LY when past the end of VBlank)

static void vq_exec(void) {
__asm
    push bc
    ld   a, (_vq_count)
    or   a, a
    jr   z, 9$
    ld   c, a
    ld   hl, #_vq
1$:
    ld   a, (hl+)           ; n
    ld   b, a
    ld   a, (hl+)           ; bank
    ldh  (0x4F), a
    ld   a, (hl+)           ; src
    ld   e, a
    ld   a, (hl+)
    ld   d, a
    ld   a, (hl+)           ; dst low, hl -> dst high
    push hl
    ld   h, (hl)
    ld   l, a
    srl  b                  ; two bytes per pass, the odd one first
    jr   nc, 3$
    ld   a, (de)
    inc  de
    ld   (hl+), a
    inc  b
    dec  b
    jr   z, 4$
3$:
    ld   a, (de)
    inc  de
    ld   (hl+), a
    ld   a, (de)
    inc  de
    ld   (hl+), a
    dec  b
    jr   nz, 3$
4$:
    pop  hl
    inc  hl                 ; next entry (past dst high and the 2 pad bytes)
    inc  hl
    inc  hl
    dec  c
    jr   nz, 1$
    xor  a, a
    ldh  (0x4F), a          ; back to bank 0
9$:
    pop  bc
__endasm;
}

// VBL interrupt handler (registered in init()).
void vq_vbl(void) {
    uint8_t t0, t, ly, vbk;
    if (!vq_ready) return;
    ly = LY_REG;
    vq_drain_ly_last = ly;
    if (ly < 144 || ly > vq_latest_ly) { vq_late++; return; }    // too late in VBlank: the list waits
    if (ly > vq_drain_ly_max) vq_drain_ly_max = ly;
    vbk = VBK_REG;                               // (the interrupted code may have selected bank 1)
    t0 = DIV_REG;
    vq_exec();
    ly = LY_REG;
    if (ly < 144) ly += 154;                     // (0..143: it ran into the next frame)
    if (ly > vq_end_ly_max) vq_end_ly_max = ly;
    t = DIV_REG - t0;
    if (t > drain_ticks_max) drain_ticks_max = t;
    VBK_REG = vbk & 1;
    vq_count = 0;
    vq_ready = 0;
}

// Start of a frame's logic: if last frame's list is still waiting, take it back; it is handed over again,
// unchanged but for what this frame adds with vq_add(), by vq_frame_end().
void vq_frame_begin(void) {
    vq_held = vq_ready;
    vq_ready = 0;
}

void vq_frame_end(void) {
    if (vq_count) vq_ready = 1;
}

// Throw the list away (screen changes, LCD off).
void vq_reset(void) {
    vq_ready = 0;
    vq_count = 0;
    vq_held = 0;
}

void vq_add(uint8_t bank, const uint8_t *src, uint8_t x, uint8_t y, uint8_t n) {
    vq_entry_t *e;
    if (vq_count >= VQ_MAX) return;              // (cannot happen: one frame queues at most ~16 entries)
    e = &vq[vq_count++];
    e->n = n; e->bank = bank; e->src = src;
    e->dst = (uint8_t *)0x9800 + ((uint16_t)y << 5) + x;
}

static uint8_t * const bar_map[NUM_BARS] = {
    (uint8_t *)(0x9800 + BAR_TOP_ROW(0) * 32), (uint8_t *)(0x9800 + BAR_TOP_ROW(1) * 32),
    (uint8_t *)(0x9800 + BAR_TOP_ROW(2) * 32), (uint8_t *)(0x9800 + BAR_TOP_ROW(3) * 32),
};

// End of the logic phase: turn the HUD flags and dirty bar spans into queue entries, composing the bar columns
// as they are queued (in small steps, for the same reason as the compose functions).
static uint8_t qv_cost, qv_w, qv_bar;
static uint8_t *qv_p;                    // next entry, as bytes
static uint16_t qv_src, qv_dst;

// One entry (see vq_entry_t) from the qv_ globals; written byte by byte through one pointer, which SDCC keeps in
// a register (struct field stores through a pointer cost it an address computation each).
static void queue_entry(uint8_t bank) {
    uint8_t *p = qv_p;
    *p++ = qv_w; *p++ = bank;
    *p++ = (uint8_t)qv_src; *p++ = (uint8_t)(qv_src >> 8);
    *p++ = (uint8_t)qv_dst; *p++ = (uint8_t)(qv_dst >> 8);
    qv_p = p + 2;
}

// one wall row of qv_w bytes: the tile entry, and the attribute entry if they changed (sh_attr follows sh_tile)
static void queue_row(void) {
    queue_entry(0);
    vq_count++;
    if (!cz_attrs) return;
    qv_src += sizeof sh_tile;
    queue_entry(1);
    vq_count++;
    qv_src -= sizeof sh_tile;
}

// Do the columns cz_x0..cz_x1-1 of bar qv_bar need their attributes? Consumes that part of the attribute span.
static uint8_t take_attrs(void) {
    uint8_t b = qv_bar;
    if (attr_x0[b] >= cz_x1 || attr_x1[b] <= cz_x0) return 0;
    if (attr_x1[b] <= cz_x1) { attr_x0[b] = 255; attr_x1[b] = 0; }
    else if (attr_x0[b] < cz_x1) attr_x0[b] = cz_x1;
    return 1;
}

// The chunk cz_x0..cz_x1-1 of bar qv_bar: compose it, queue it, and take it off the dirty span. Globals in and
// out: in SDCC a few global loads are much cheaper than locals that do not fit in registers.
static void queue_chunk(void) {
    uint8_t b = qv_bar;
    cz_attrs = is_cgb && take_attrs();
    compose_bar(b);
    qv_src = (uint16_t)(cz_tile + cz_x0);         // (compose_bar left cz_tile at the bar's first row)
    qv_dst = (uint16_t)(bar_map[qv_bar] + cz_x0);
    queue_row();
    qv_src += 32; qv_dst += 32;
    queue_row();
    b = qv_bar;
    if (cz_x1 >= dirty_x1[b]) { dirty_x0[b] = 255; dirty_x1[b] = 0; }
    else { dirty_x0[b] = cz_x1; vram_pending = 1; }
}

// Queue (a chunk of) bar b's dirty span. Returns 0 when the frame's budget is used up.
// Cost of a chunk w columns wide, 4 * (3 + w): what a CGB chunk (tiles + attributes) costs to drain. A DMG chunk
// drains in half that, but composing it costs the same as on CGB, and composing is what bounds the frame's logic
// time: so DMG queues no more chunks per frame than CGB does (M8a perf; a redraw at most waits a frame longer).
static const uint8_t chunk_cost[VQ_CHUNK + 1] = { 12, 16, 20, 24, 28, 32, 36 };
static uint8_t queue_bar(uint8_t b) {
    uint8_t x0 = dirty_x0[b], w, c;
    if (x0 >= dirty_x1[b]) return 1;
    w = dirty_x1[b] - x0;
    if (w > VQ_CHUNK) w = VQ_CHUNK;
    c = chunk_cost[w];
    if (qv_cost && (uint8_t)(qv_cost + c) > VQ_BUDGET) { vram_pending = 1; return 0; }
    qv_cost += c;
    qv_w = w; qv_bar = b; cz_x0 = x0; cz_x1 = x0 + w;
    queue_chunk();
    return 1;
}

// Quick redraws, as many as the budget allows; the rest wait for the next frame. The 6 tile ids of a front view
// (variant v, shift s) are PATRON_TILE_BASE + v * 48 + s * 6 + 0..5, so both rows are copied straight out of
// id_seq (ROM0: the drain reads it from the VBlank interrupt, whatever bank is mapped then); the shadow rows are not
// touched (a later span recomposes its columns from the patrons anyway). A patron who has left, or turned to his
// back view, since he was listed falls back to a dirty span.
#define QI(n)   (uint8_t)(PATRON_TILE_BASE + (n))
#define QI6(n)  QI(n), QI((n) + 1), QI((n) + 2), QI((n) + 3), QI((n) + 4), QI((n) + 5)
#define QI48(n) QI6(n), QI6((n) + 6), QI6((n) + 12), QI6((n) + 18), QI6((n) + 24), QI6((n) + 30), QI6((n) + 36), QI6((n) + 42)
static const uint8_t id_seq[PATRON_TILES_PER_GROUP] = { QI48(0), QI48(48), QI48(96) };
#define QUICK_COST 16          // logic time like 2/3 of a 3-column span (measured); the drain is half a span's
// The two entries of a quick redraw: patron p, front view, drawn at d. (Its own small function: SDCC keeps p and d
// in registers here; inside the loop it spilled them.)
static void quick_entries(uint8_t p, uint8_t d) {
    qv_src = (uint16_t)(id_seq - PATRON_TILE_BASE) + stamp_tile[((patron_variant[p] & 3) << 3) | (d & 7)];
    qv_dst = (uint16_t)bar_map[patron_bar[p] & (NUM_BARS - 1)] + (d >> 3);
    qv_w = 3;
    queue_entry(0);
    qv_src += 3; qv_dst += 32;
    queue_entry(0);
    vq_count += 2;
}

static void queue_quick(void) {
    uint8_t p, d;
    while (quick_n) {
        if ((uint8_t)(qv_cost + QUICK_COST) > VQ_BUDGET) { vram_pending = 1; return; }
        p = quick_list[--quick_n];
        quick_on[p] = 0;
        d = patron_draw[p];
        if (patron_state[p] == PATRON_NONE || d == 255) continue;   // gone: remove_patron() marked his columns
        if (d & DRAW_BACK) { d = (d & ~DRAW_BACK) >> 3; mark_dirty(patron_bar[p] & (NUM_BARS - 1), d, d + 3); continue; }
        qv_cost += QUICK_COST;
        quick_entries(p, d);
    }
}

void queue_vram(void) {
    if (vq_held) return;                         // last frame's list has not gone out yet: everything stays dirty
    qv_cost = 0;
    if (hud_dirty & HUD_LIVES) { vq_add(0, lives_tiles, 9, HUD_ROW, 3); qv_cost += 6; }
    if (hud_dirty & HUD_SCORE) { vq_add(0, score_tiles, 1, HUD_ROW, 6); qv_cost += 9; }
    hud_dirty = 0;
    if (!vram_pending) return;
    vram_pending = 0;
    qv_p = (uint8_t *)&vq[vq_count];
    if (quick_n) queue_quick();
    if (queue_bar(0) && queue_bar(1) && queue_bar(2)) queue_bar(3);
}

// ---- sprites other than the mugs ------------------------------------------------------
// OAM 0..3: [col A top, col B top, col A bottom, col B bottom]. Screen layout
// left to right is A,B when facing left (art faces left) and B,A flipped when
// facing right.
uint8_t bt_drawn[4];         // bar, x, frame, facing the bartender's OAM entries show; bt_drawn[0] = 255: rewrite them

void draw_bartender(void) {
    uint8_t base, ytop, ybot, flags, xa, xb;
    OAM_item_t *o = shadow_OAM;
    if (bt_drawn[0] == bar && bt_drawn[1] == bartender_x && bt_drawn[2] == bartender_frame && bt_drawn[3] == facing) return;
    bt_drawn[0] = bar; bt_drawn[1] = bartender_x; bt_drawn[2] = bartender_frame; bt_drawn[3] = facing;
    base = OBJ_BARTENDER + bartender_frame * BARTENDER_TILES_PER_FRAME;
    ytop = bar_oam_y[bar];                        // 24 px tall: feet on the bottom of the counter row
    ybot = ytop + 16;
    flags = (facing ? S_FLIPX : 0) | OBJPAL_BARTENDER;
    xa = facing ? bartender_x + 16 : bartender_x + 8;   // art column A (left half)
    xb = facing ? bartender_x + 8 : bartender_x + 16;   // art column B

    o->y = ytop; o->x = xa; o->tile = base;     o->prop = flags; o++;
    o->y = ytop; o->x = xb; o->tile = base + 2; o->prop = flags; o++;
    o->y = ybot; o->x = xa; o->tile = base + 4; o->prop = flags; o++;
    o->y = ybot; o->x = xb; o->tile = base + 6; o->prop = flags;
}

static const uint8_t dancer_x[NUM_DANCERS] = { 24, 72, 120 };   // screen x of the left edge, across the stage
static const uint8_t dance_seq[4] = { 0, 1, 2, 3 };               // stand, left kick, arms up, right kick
uint8_t dancers_vis;              // dancer OAM entries written (and so to be hidden again)
#define DANCER_OAM_Y (STAGE_LAST_ROW * 8 - 24 + 16)   // OAM y of a dancer's top entries: art 24 px tall, feet on the platform
uint8_t dancer_sig;               // what the dancer entries show (0x80 | frame << 3 | visible mask); 0: rewrite them

// OAM 27: the tip coin on its bar's counter (blinks in its last second, glints every half second).
static void draw_coin(void) {
    OAM_item_t *o = shadow_OAM + OAM_COIN;
    if (!tip_timer || (tip_timer < TIP_BLINK && (tip_timer & 4))) { o->y = 0; return; }
    o->y = bar_oam_y[tip_bar] + MUG_DY;
    o->x = tip_x + 8;
    o->tile = OBJ_COIN + (((tip_timer >> 3) & 7) == 0 ? 2 : 0);
    o->prop = is_cgb ? OBJPAL_COIN : 0;
}

// OAM 26: the door puff on the bar where a patron just came in or left (3 frames of PUFF_TOTAL / 3 game frames).
uint8_t puff_bar, puff_timer;
static uint8_t puff_shown;
void door_puff(uint8_t b) { puff_bar = b; puff_timer = PUFF_TOTAL; }
static void draw_puff(void) {
    OAM_item_t *o = shadow_OAM + OAM_PUFF;
    uint8_t t = puff_timer;
    if (!t) { if (puff_shown) { o->y = 0; puff_shown = 0; } return; }
    puff_shown = 1;
    o->y = bar_oam_y[puff_bar];
    o->x = PUFF_X + 8;
    o->tile = OBJ_PUFF + (t > 8 ? 0 : t > 4 ? 2 : 4);
    o->prop = S_PALETTE | OBJPAL_GLASS;
}

// What the dancer entries must show: 0x80 | dance frame << 3 | bit k: dancer k is on stage. They pop in one
// after another at the start of the show and leave in the same order at the end.
static uint8_t dancer_look(void) {
    uint16_t left = show_timer, elapsed = SHOW_FRAMES - show_timer;
    uint8_t sig = 0x80 | (dancer_frame << 3);
    if (elapsed >= 1 * DANCER_STAGGER && left > 1 * DANCER_STAGGER) sig |= 1;
    if (elapsed >= 2 * DANCER_STAGGER && left > 2 * DANCER_STAGGER) sig |= 2;
    if (elapsed >= 3 * DANCER_STAGGER && left > 3 * DANCER_STAGGER) sig |= 4;
    return sig;
}

// OAM 28..39: the dancers on the platform, 4 entries each (16x24 art, feet on the top of row STAGE_LAST_ROW).
static void draw_dancers(uint8_t sig) {
    OAM_item_t *o = shadow_OAM + OAM_DANCERS;
    uint8_t k, base, flags, x;
    base = OBJ_DANCER + dance_seq[dancer_frame] * DANCER_TILES_PER_FRAME;
    flags = is_cgb ? OBJPAL_DANCER : 0;
    for (k = 0; k < NUM_DANCERS; k++, o += 4) {
        if (!(sig & (1 << k))) { o[0].y = o[1].y = o[2].y = o[3].y = 0; continue; }
        x = dancer_x[k] + 8;
        o[0].y = DANCER_OAM_Y;      o[0].x = x;     o[0].tile = base;     o[0].prop = flags;
        o[1].y = DANCER_OAM_Y;      o[1].x = x + 8; o[1].tile = base + 2; o[1].prop = flags;
        o[2].y = DANCER_OAM_Y + 16; o[2].x = x;     o[2].tile = base + 4; o[2].prop = flags;
        o[3].y = DANCER_OAM_Y + 16; o[3].x = x + 8; o[3].tile = base + 6; o[3].prop = flags;
    }
}

void draw_stage_fx(void) {
    uint8_t k, sig;
    draw_coin();
    draw_puff();
    if (!show_timer) {
        if (dancers_vis) {
            OAM_item_t *o = shadow_OAM + OAM_DANCERS;
            for (k = 0; k < NUM_DANCERS * 4; k++) o[k].y = 0;
            dancers_vis = 0;
        }
        dancer_sig = 0;
        return;
    }
    dancers_vis = 1;
    sig = dancer_look();
    if (sig == dancer_sig) return;               // the entries already show exactly this
    dancer_sig = sig;
    draw_dancers(sig);
}

// Anything that writes OAM entries behind the drawing code's back calls this: the cached ones are redrawn.
void oam_touched(void) {
    bt_drawn[0] = 255;
    dancer_sig = 0;
}

void hide_all_sprites(void) {
    uint8_t i;
    for (i = 0; i < 40; i++) shadow_OAM[i].y = 0;
    oam_used = OAM_FILL + 1;
    puff_timer = 0; puff_shown = 0;
    dancers_vis = 0;
    oam_touched();
}
