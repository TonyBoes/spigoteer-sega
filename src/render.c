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
#include "tip2.h"
#include "palettes.h"
#include "boss.h"

uint8_t row_buf[20];
uint8_t pal5_cur;                 // CGB OBJ palette 5 holds the show (2) or not (0, 1: something else) (load_venue loads the show's); see pal5_check
volatile uint8_t pal5_req;        // bit 0: OBJ palette 5, the show's (pal5_write); bit 1: the Mothership's lights (boss_mothership.c lights; pal5_other)
static const uint16_t *pal5_src;
uint16_t pal5_lifted[4];       // SCREEN BRIGHT: the show's colours lifted, written raw by the VBlank (bright.c pal5_lift)
static void pal5_write(void);
uint8_t score_tiles[6];      // the HUD digits as BG tile ids, prepared outside VBlank
uint8_t lives_tiles[2];

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

// Two rows: cp_n bytes cp_src -> cp_dst, then cp_n bytes cp_src + BASE_W -> cp_dst + 32 (a bar's two wall rows from
// base_tile / base_attr, BASE_W wide, into the 32-wide shadow rows). 1 <= cp_n <= 20.
#if BASE_W != 23
#error "copy_2rows: the base rows' stride (BASE_W) is written into the asm"
#endif
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
    ld   a, #23             ; de += BASE_W - n
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
uint8_t sh_rows[2][NUM_BARS * 2][32];          // [0]: tile ids, [1]: CGB attributes, right behind (mirror.c: quick_mirror)
#define sh_tile sh_rows[0]
#define sh_attr sh_rows[1]
static uint8_t dirty_x0[NUM_BARS], dirty_x1[NUM_BARS];
static uint8_t attr_x0[NUM_BARS], attr_x1[NUM_BARS];   // CGB: the part of the dirty span whose attributes changed
uint8_t vram_pending;             // dirty spans left to queue (keeps idle frames cheap)

// The bar's two wall rows without patrons (wall, spout, keg), tile ids and CGB attributes by row and column:
// what compose_dirty() restores under (and around) the patrons. Filled from the level's venue (load_venue, M9), the
// same picture the level screen starts with. Row 1 follows row 0 directly (restore_base relies on it).
uint8_t base_all[4][2][BASE_W];   // base_tile, base_attr, then (P3, mirror.c) an R bar's base_rtile, base_rattr in screen order

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
static const uint8_t *cz_base;            // its window into base_all (P6: bar_bofs)

// ---- P3/P4 mirrored bars (CLASSIC: patrons from the right). Every rule works in bar-local x (0 = the patrons' end, TAP_X
// the tap); a bar marked R in bar_dirs is only DRAWN mirrored. Its shadow rows hold the SCREEN picture (local column c at
// screen column 19 - c, every tile flipped: CGB attribute bit 5, DMG flipped tile data), so the copy list, the drain and
// write_all_bars are unchanged; the dirty spans stay local (a span [x0, x1) is screen columns [20 - x1, 20 - x0)).
// Sprites: an 8 px entry at OAM X goes to 168 - X with S_FLIPX toggled: the bartender, fill glass, mugs, lifted patrons and
// coin are drawn at bar-local X and moved afterwards (mirror.c mirror_oam). Tables set at level load (mirror.c).
uint8_t bar_dirs;                         // bit b: bar b is R
uint8_t mir_attr;                         // CGB: the BG attribute bit of an R bar (S_FLIPX); DMG 0
uint8_t mir_bswap;                        // DMG mixed level: MIX_A (option (a)): back views are not mirrored (drawn as they are on an R bar); MIX_B (option (b)): looks split by direction (add_patron)
// First tile of variant v pre-shifted by s px, [dir << 5 | v << 3 | s] (dir 1: an R bar). M13a layout (column-major:
// column k is tiles + 2k (top) and + 2k + 1 (bottom); shifts 1..7 first, the shift-0 poses last, so they double as 8x16
// OBJ tiles for a lifted patron). Filled by mirror.c: L and R the same unless the DMG holds two tile sets (a mixed level).
uint8_t st_tab[64];
#define SB(v) ((uint8_t)(PATRON_BACK_BASE + (v) * 4u))                     // first back-view tile of variant v
#define SX(k) ((uint8_t)(SALOON_X_BACK + (k) * 4u))                         // first back-view tile of the Saloon's look 3 + k (VRAM bank 1)
static const uint8_t back_tile[8] = { SB(0), SB(1), SB(2), SX(0), SX(1), SX(2), SX(3), SX(4) };   // by look (3-7: the Color-only ones)
// BG palette slot of palette instance pi (patron_variant): INST_BG, 8 bytes in story_scratch that looks_insts (build/looks.c) fills at the level load: 0-2 the legacy A, B, C (BG 2-4);
// 3 and 4 the Saloon's extra sets (7: the keg's, free in the Saloon's playfield; 5: the stage's, below the split line) or the Factory's (5 and 6: the chain's reloads)
#define pal_bg INST_BG

extern uint8_t cur_group, overlay_on;
#define SPACE_GROUP 9                       // the Space Lounge's patron group (the aliens)
static uint8_t st_t;                      // first tile of the patron being stamped
static uint8_t cz_dir, cz_sto, cz_flip, cz_bswap;   // the bar being composed is R; its st_tab offset, attribute bit, back-view swap

// patron_variant: bits 0-2 the look, bits 3-5 (palette instance ^ look): 0 is the look's own palette (A, B, C = BG 2, 3, 4), bit 6 a
// Color-only look drawn from VRAM bank 1 (its BG attribute and OAM bit 3 = bit 6 >> 3). game.h PATRON_BANK1.
static void patron_attr(uint8_t v) {                     // cz_pal of a patron with variant byte v
    uint8_t i = v >> 3, b = pal_bg[(v ^ i) & 7];
    if (b == BGPAL_PATRON + 1 && cur_group == SPACE_GROUP) b = BGPAL_BAR;   // XENO: the Space Lounge's bar palette is his colours (BG 3 is free)
    cz_pal = b | (i & 8) | cz_flip;
}

static void stamp_look(uint8_t s, uint8_t d) {           // st_t and cz_pal for patron s drawn at x d (front view)
    uint8_t v = patron_variant[s];
    patron_attr(v);
    st_t = st_tab[cz_sto | ((v & 7) << 3) | (d & 7)];
}

static void stamp3(uint8_t c, uint8_t t3) {              // the whole 3x2 footprint at column c (not on an R bar); t3: the 3rd column's top tile (option 2: the shared blank pair at shift 0)
    uint8_t *r = cz_tile + c, t = st_t;
    r[0] = t; r[1] = t + 2; r[2] = t3;
    r += 32;
    r[0] = t + 1; r[1] = t + 3; r[2] = t3 + 1;
    if (!cz_attr) return;
    r = cz_attr + c; t = cz_pal;
    r[0] = t; r[1] = t; r[2] = t;
    r += 32;
    r[0] = t; r[1] = t; r[2] = t;
}

static void put_col(uint8_t c, uint8_t t) {              // one 1x2 column, if inside the span
    uint8_t *r;
    if (c < cz_x0 || c >= cz_x1) return;
    if (cz_dir) c = 19 - c;                              // (R bar: the screen column)
    r = cz_tile + c;
    r[0] = t; r[32] = t + 1;
    if (!cz_attr) return;
    r = cz_attr + c;
    r[0] = cz_pal; r[32] = cz_pal;
}

static void put_back_col(uint8_t c, uint8_t t) {         // one 1x2 column of a back view (2x2 tiles), if inside the span
    uint8_t *r;
    if (c < cz_x0 || c >= cz_x1) return;
    if (cz_dir) c = 19 - c;
    r = cz_tile + c;
    r[0] = t; r[32] = t + 2;
    if (!cz_attr) return;
    r = cz_attr + c;
    r[0] = cz_pal; r[32] = cz_pal;
}

// Patron s, watching the show, in its back view at column c (on a multiple of 8 px: 2 columns; the 3rd column of
// its footprint stays wall).
static void stamp_back(uint8_t s, uint8_t c) {
    uint8_t v = patron_variant[s];
    patron_attr(v);
    v = back_tile[v & 7];
    if (cz_bswap) { put_back_col(c, v + 1); put_back_col(c + 1, v); return; }   // (DMG mixed: drawn unmirrored on an R bar)
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
    if (!(d & 7) && (patron_ovl[s] & (OVL_TWO | OVL_TOP))) { put_col(c, st_t); put_col(c + 1, st_t + 2); return; }   // (M13b)
    d = (d & 7) ? st_t + 4 : PATRON_BLANK;                // (the 3rd column: option 2, shift 0 has no tiles of its own there)
    if (c >= cz_x0 && c + 3 <= cz_x1 && !cz_dir) { stamp3(c, d); return; }   // (an R bar: put_col mirrors)
    put_col(c, st_t); put_col(c + 1, st_t + 2); put_col(c + 2, d);
}

// M13a: a lifted patron (a sprite) leaves his BG footprint as plain wall: colour 0 of his own palette, as his BG copy
// would show it there (the wall's specks stay hidden, so lifting and dropping change no pixel). Stamped before the BG
// patrons of the bar, so it never covers one of them.
static void stamp_blank(uint8_t s) {
    uint8_t d = patron_draw[s], c;
    if (d == 255 || (d & DRAW_BACK)) return;              // (a back view covers its own 2 columns; the 3rd stays wall)
    c = (d & ~DRAW_BACK) >> 3;
    if (c + 3 <= cz_x0 || c >= cz_x1) return;
    patron_attr(patron_variant[s]);                    // (colour 0 only: the wall in every patron palette)
    put_col(c, (uint8_t)PATRON_BLANK); put_col(c + 1, (uint8_t)PATRON_BLANK); put_col(c + 2, (uint8_t)PATRON_BLANK);
}

static uint8_t cz_attrs;                  // compose the attributes too (CGB, and they changed)

static void restore_base(void) {                         // the wall over the span (cz_*), both rows
    uint8_t x0 = cz_x0;
    const uint8_t *t = cz_base;                           // (R bar: in base_rtile, screen order)
    cp_n = cz_x1 - x0;
    if (cz_dir) x0 = 20 - cz_x1;
    t += x0;
    cp_dst = (uint16_t)(cz_tile + x0); cp_src = (uint16_t)t; copy_2rows();
    if (!cz_attrs) { cz_attr = 0; return; }
    cz_attr = cz_tile + sizeof sh_tile;                   // sh_attr follows sh_tile
    cp_dst = (uint16_t)(cz_attr + x0); cp_src = (uint16_t)(t + 2 * BASE_W); copy_2rows();
}

// BG patrons of the bar whose OVL_TOP flag is `top` (M13b: the would-be lifted one of a pair left on the BG goes last).
static void stamp_pass(uint8_t b, uint8_t top) {
    const uint8_t *q = bar_list[b];
    uint8_t n, s;
    for (n = bar_n[b]; n; n--) {
        s = *q++;
        if (patron_state[s] != PATRON_NONE && !LIFT_OFF_BG(patron_lift[s]) && (patron_ovl[s] & OVL_TOP) == top) stamp(s);
    }
}

static void stamp_bar(uint8_t b) {
    const uint8_t *q = bar_list[b];
    uint8_t n, two;
    two = ovl_bars & bar_bit[b];
    if (lift_n[b] | two) {
        // Lifted ones first: plain wall under their sprites (not under one at the left end, LIFT_EDGE: he has no BG
        // footprint, the venue's wall shows behind him). M13b: then the BG patrons, the OVL_TOP ones (ovl_bars) last.
        if (lift_n[b])
            for (n = bar_n[b]; n; n--, q++)
                if (patron_state[*q] != PATRON_NONE && patron_lift[*q] == LIFT_OBJ) stamp_blank(*q);
        stamp_pass(b, 0);
        if (two) stamp_pass(b, OVL_TOP);
        return;
    }
    for (n = bar_n[b]; n; n--, q++)
        if (patron_state[*q] != PATRON_NONE) stamp(*q);
}

// A boss fight (src/boss.c): his BG figure over his bar, after its patrons (there are none: the bar is his), one column
// pair (top t, bottom t + 1) per boss_cols entry, in BG palette boss_pal.
static void stamp_boss(void) {
    uint8_t k, t;
    cz_pal = boss_pal;
    for (k = 0; k != BOSS_W_MAX; k++) if ((t = boss_cols[k])) put_col(boss_col + k, t);
}

// A moving boss's landing marker (boss.c boss_mark) on another bar: two column pairs from BOSS_MARK_BG at columns
// BOSS_MARK_COL, + 1, over the bar's patrons (the tell is never hidden), in his BG palette.
static void stamp_fight(uint8_t b) {
    if (b == boss_bar) stamp_boss();                     // (the Mothership's ray and entrance beam fall on his own bar too: over him)
    if (b != BOSS_MARK_BAR) return;
    cz_pal = boss_pal;
    put_col(BOSS_MARK_COL, BOSS_MARK_BG);
    put_col(BOSS_MARK_COL + 1, (uint8_t)(BOSS_MARK_BG + 2));
}

static void compose_bar(uint8_t b) {                     // columns cz_x0..cz_x1-1 of bar b
    if (!lists_ok) build_lists();
    cz_tile = sh_tile[b << 1];
    cz_base = &base_all[0][0][0] + bar_bofs[b];
    cz_dir = cz_sto = cz_flip = cz_bswap = 0;
    if (bar_dirs & bar_bit[b]) { cz_dir = 1; cz_sto = mir_attr ^ 32; cz_flip = mir_attr; cz_bswap = mir_bswap & MIX_A; }
    restore_base();
    stamp_bar(b);
    if (boss_on) stamp_fight(b);
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

static uint8_t urg_n, urg_b[2], urg_c[2];   // M13a: spans queued first thing this frame (bg_urgent)

// Patron p's BG copy is not on its way yet: a quick redraw or a dirty span over his footprint waits to be queued.
uint8_t bg_pending(uint8_t p) {
    uint8_t b = patron_bar[p] & (NUM_BARS - 1), c = (patron_draw[p] & ~DRAW_BACK) >> 3;
    if (quick_on[p]) return 1;
    return dirty_x0[b] < (uint8_t)(c + 3) && dirty_x1[b] > c;
}

// Columns c-1..c+3 (M13b; M13a: c..c+2) of bar b are composed and queued at the head of this frame's list (before the budget: at most two
// spans, 48 units, beside the HUD's 15), so they go out in the VBlank that also shows this frame's OAM. 0: not
// possible this frame (last frame's list still waits, or two are queued already).
uint8_t bg_urgent(uint8_t b, uint8_t c) {
    if (vq_held || urg_n >= 2) return 0;
    urg_b[urg_n] = b; urg_c[urg_n] = c; urg_n++;
    vram_pending = 1;
    return 1;
}

void clear_dirty(void) {
    uint8_t b;
    vram_pending = 0;
    urg_n = 0;
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
#define QUEUE_LY_LATE 72    // a frame this far on (what is left to build: ~60 lines) carries the bars' spans over to the next one, 3 frames out of 4
#define VQ_LATEST_LY 147    // a full-budget drain (~7 lines, drain_ticks_max) that starts later could run into line 0
// VQ_DRAIN_BUDGET (game.h): bytes + 3 per entry (~40 cycles each) one VBlank's drain may take, whoever queued them (queue_vram, or a
// direct vq_add / vq[] writer): vq_frame_end hands over only the entries that fit, the rest wait at the head of the list for the
// next VBlank, in order (the first entry always goes, however big: the biggest is a 64-byte tile reload).
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
    if (pal5_req) pal5_write();
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

uint8_t qv_cost;                          // the list's cost so far (bytes + 3 an entry; every writer adds, 255 when entries are left over)
uint8_t qv_w, qv_bar;                     // queue_vram's scratch (below); also what a split list leaves for vq_restore

// Start of a frame's logic: if last frame's list is still waiting, take it back; it is handed over again,
// unchanged but for what this frame adds with vq_add(), by vq_frame_end().
void vq_frame_begin(void) {
    vq_held = vq_ready;
    if (qv_cost == VQ_SPLIT) vq_restore();       // the last list was split: the entries that did not go out rejoin it (vq_held = 1)
    qv_cost = -vq_held;                          // 0, or 255 for entries left from last frame: they are not tallied, vq_frame_end counts them out
    vq_ready = 0;
}

// The list is complete. One whose tally is over what a VBlank's drain takes is cut by vq_split to the first entries that fit
// (at least one); the rest waits at the head of the next frame's list.
void vq_frame_end(void) {
    if (!vq_count) return;
    if (qv_cost > VQ_DRAIN_BUDGET) vq_split();
    vq_ready = 1;
}

// Throw the list away (screen changes, LCD off).
void vq_reset(void) {
    vq_ready = 0;
    vq_count = 0;
    qv_cost = 0;
    vq_held = 0;
    sa_on = 0;                                   // the stage animation runs on the level screen only (stage_anim_start)
    sa_left = 0;
}

void vq_add(uint8_t bank, const uint8_t *src, uint8_t x, uint8_t y, uint8_t n) {
    uint8_t *p, c = vq_count;
    if (c >= VQ_MAX) return;                     // (cannot happen: one frame queues at most ~16 entries)
    vq_count = c + 1;
    if (qv_cost <= VQ_DRAIN_BUDGET) qv_cost += n + 3 + (bank << 1);   // (a bank 1 entry costs more: the VBK writes)
    p = (uint8_t *)&vq[c];                       // (byte by byte, as queue_entry: the map address is 0x9800 + y * 32 + x, x < 32)
    *p++ = n; *p++ = bank;
    *p++ = (uint8_t)(uint16_t)src; *p++ = (uint8_t)((uint16_t)src >> 8);
    *p++ = (uint8_t)(y << 5) | x; *p = 0x98 + (y >> 3);
}

static uint8_t * const bar_map[NUM_BARS] = {
    (uint8_t *)(0x9800 + BAR_TOP_ROW(0) * 32), (uint8_t *)(0x9800 + BAR_TOP_ROW(1) * 32),
    (uint8_t *)(0x9800 + BAR_TOP_ROW(2) * 32), (uint8_t *)(0x9800 + BAR_TOP_ROW(3) * 32),
};

// End of the logic phase: turn the HUD flags and dirty bar spans into queue entries, composing the bar columns
// as they are queued (in small steps, for the same reason as the compose functions).
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
    b = cz_dir ? 20 - cz_x1 : cz_x0;              // (the screen columns)
    qv_src = (uint16_t)(cz_tile + b);             // (compose_bar left cz_tile at the bar's first row)
    qv_dst = (uint16_t)(bar_map[qv_bar] + b);
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
    if (bar_n[b] > 2) c += (uint8_t)(bar_n[b] - 2) << 3;    // M13b: composing stamps every patron of the bar (crowded bars)
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
// M13a: the tiles are stored column by column, so the table holds each pose's ids in row order: top t, t+2, t+4,
// bottom t+1, t+3, t+5 (at the pose's own offset, so the lookup is unchanged).
#define QI(n)   (uint8_t)(PATRON_TILE_BASE + (n))
#define QI6(n)  QI(n), QI((n) + 2), QI((n) + 4), QI((n) + 1), QI((n) + 3), QI((n) + 5)
#define QI48(n) QI6(n), QI6((n) + 6), QI6((n) + 12), QI6((n) + 18), QI6((n) + 24), QI6((n) + 30), QI6((n) + 36), QI6((n) + 42)
#define QS0(n)  QI(n), QI((n) + 2), (uint8_t)PATRON_BLANK, QI((n) + 1), QI((n) + 3), (uint8_t)(PATRON_BLANK + 1)   // a shift-0 pose (option 2): its 3rd column is the shared blank pair
static const uint8_t id_seq[PATRON_BLANK_OFS + 18] = { QI48(0), QI48(48), QI6(96), QI6(102), QI6(108), QI6(114), QI6(120),   // the shifted poses, at their own offsets
    QS0(PATRON_SHIFT0_OFS), QS0(PATRON_SHIFT0_OFS + 4), QS0(PATRON_SHIFT0_OFS + 8) };   // then the shift-0 poses, 6 ids each (j = 126 + 6 v)
#define QUICK_COST 16          // logic time like 2/3 of a 3-column span (measured); the drain is half a span's
static uint8_t seq_ofs(uint8_t t) {      // a pose's first tile -> its index in id_seq (a shift-0 pose: 4 tiles apart, its 6 ids 6 apart)
    t -= PATRON_TILE_BASE;
    if (t >= PATRON_BLANK_OFS) { t -= PATRON_SHIFT0_OFS; t = PATRON_BLANK_OFS + t + (t >> 1); }
    return t;
}
// The two entries of a quick redraw: patron p, front view, drawn at d. (Its own small function: SDCC keeps p and d
// in registers here; inside the loop it spilled them.)
static void quick_entries(uint8_t p, uint8_t d) {
    uint8_t b = patron_bar[p] & (NUM_BARS - 1), k = 3;          // (k: from the top row's ids to the bottom row's)
    if ((bar_dirs & bar_bit[b]) || (patron_variant[p] & PATRON_BANK1)) {   // R bar, or a bank-1 look: his 6 ids (mirrored) into the shadow rows (the screen picture), queued from there
        d = quick_mirror(p, d);
        qv_src = (uint16_t)&sh_tile[b << 1][d];
        qv_dst = (uint16_t)bar_map[b] + d;
        k = 32;
    } else {
        qv_src = (uint16_t)id_seq + seq_ofs(st_tab[((patron_variant[p] & 7) << 3) | (d & 7)]);
        qv_dst = (uint16_t)bar_map[b] + (d >> 3);
    }
    qv_w = 3;
    queue_entry(0);
    qv_src += k; qv_dst += 32;
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
        if (LIFT_OFF_BG(patron_lift[p])) continue;                  // lifted: his columns stay plain wall
        // (M13b: his footprint meets another BG patron's: OVL_SHARED, or he covers one and stands on shift 0, where a
        // quick redraw would put his empty 3rd column over the other)
        if ((d & DRAW_BACK) || (patron_ovl[p] & OVL_SHARED) || (!(d & 7) && (patron_ovl[p] & OVL_TOP))) {
            d = (d & ~DRAW_BACK) >> 3; mark_dirty(patron_bar[p] & (NUM_BARS - 1), d, d + 3); continue;
        }
        qv_cost += QUICK_COST;
        quick_entries(p, d);
    }
}

// An urgent span (bg_urgent): composed and queued whatever the budget, tiles and (CGB) attributes.
static void queue_urgent(uint8_t b, uint8_t c) {
    uint8_t x1 = c + 4;                                   // M13b: c-1..c+3, so a patron lifted on the frame he moved
    if (x1 > 20) x1 = 20;                                 // (a pixel either way) leaves no BG copy at his old place
    if (c) c--;
    qv_bar = b; cz_x0 = c; cz_x1 = x1; qv_w = x1 - c;
    qv_cost += chunk_cost[qv_w];
    cz_attrs = is_cgb;
    compose_bar(b);
    if (cz_dir) c = 20 - x1;                              // (R bar: the screen columns)
    qv_src = (uint16_t)(cz_tile + c);
    qv_dst = (uint16_t)(bar_map[b] + c);
    queue_row();
    qv_src += 32; qv_dst += 32;
    queue_row();
}

// The stage animation's pending update (venue.c stage_anim_step): up to 2 of its tiles (32 bytes) as one entry; a
// 3- or 4-tile change goes out over consecutive frames. Cost n + 3 units: 19 for one tile, 35 for two.
#define SA_COST 35
static void queue_stage(void) {
    uint8_t n = sa_left > 2 ? 2 : sa_left;
    uint8_t o = sa_lo << 4;
    qv_w = n << 4;
    qv_src = (uint16_t)sa_frame + o;
    qv_dst = sa_vram + o;
    queue_entry(0);
    vq_count++;
    qv_cost += qv_w + 3;
    sa_lo += n; sa_left -= n;
    sa_wait = 0;
}

void queue_vram(void) {
    uint8_t sa, pre;
    if (vq_held) return;                         // last frame's list has not gone out yet: everything stays dirty
    pre = qv_cost;                               // (what direct vq_add writers queued earlier this frame is no part of the budget below,
    qv_cost = 0;                                 // as ever: only the VBlank drain budget, in vq_frame_end, counts it)
    if (hud_dirty & HUD_LIVES) vq_add(0, lives_tiles, 7, HUD_ROW, 2);     // (vq_add tallies them in qv_cost: 5 and 9)
    if (hud_dirty & HUD_SCORE) vq_add(0, score_tiles, 0, HUD_ROW, 6);
    hud_dirty = 0;
    sa = sa_left;
    if (!vram_pending) {                         // nothing else this frame: the stage update always fits
        if (sa) { qv_p = (uint8_t *)&vq[vq_count]; queue_stage(); }
    } else {
        vram_pending = 0;
        qv_p = (uint8_t *)&vq[vq_count];
        while (urg_n) { urg_n--; queue_urgent(urg_b[urg_n], urg_c[urg_n]); }
        // Stage animation: patrons first. It goes after the bars if the budget has room, else waits; after SA_MAX_WAIT
        // refused frames it goes before the quick redraws and bars (they get what is left, the rest stays dirty).
        if (sa && sa_wait >= SA_MAX_WAIT) { queue_stage(); sa = 0; }
        if (quick_n) queue_quick();
        // The bars' spans (a compose is 5-15 lines on a crowded bar) wait for the next frame when this one is already deep in its
        // budget (LY past QUEUE_LY_LATE, VBlank included); on 3 frames out of 4 at most (frame_counter & 3), so a span is held for
        // 3 frames at the most (measured: peak 8 / 10 / 12 patrons 23.5 / 28.0 / 37.6 % late -> 19.6 / 23.6 / 28.5 %).
        if ((frame_counter & 3) && LY_REG >= QUEUE_LY_LATE && !(HALF & HALF_ON)) vram_pending = 1;
        else if (queue_bar(0) && queue_bar(1) && queue_bar(2)) queue_bar(3);
        if (sa) { if ((uint8_t)(qv_cost + SA_COST) <= VQ_BUDGET) queue_stage(); else sa_wait++; }
    }
    qv_cost += pre;                              // the whole list's tally again
    if (qv_cost < pre) qv_cost = 255;
}

// ---- sprites other than the mugs ------------------------------------------------------
// OAM 0..3: [col A top, col B top, col A bottom, col B bottom]. Screen layout
// left to right is A,B when facing left (art faces left) and B,A flipped when
// facing right.
uint8_t bt_drawn[5];         // bar, x, frame, facing the bartender's OAM entries show; bt_drawn[0] = 255: rewrite them
uint8_t bt_new;              // P3: they were rewritten (at bar-local X; mirror.c mirror_oam moves them on an R bar)

void draw_bartender(void) {
    uint8_t base, ytop, ybot, flags, xa, xb;
    OAM_item_t *o = shadow_OAM;
    if (bt_drawn[0] == bar && bt_drawn[1] == bartender_x && bt_drawn[2] == bartender_frame && bt_drawn[3] == facing && bt_drawn[4] == bt_bob) return;
    bt_drawn[0] = bar; bt_drawn[1] = bartender_x; bt_drawn[2] = bartender_frame; bt_drawn[3] = facing; bt_drawn[4] = bt_bob;
    bt_new = 1;
    base = OBJ_BARTENDER + BT_PIC(bartender_frame) * BARTENDER_TILES_PER_FRAME;
    ytop = bar_oam_y[bar] + BT_DY - bt_bob;               // 24 px tall: feet BT_DY px past the bottom of the counter row
    ybot = ytop + 16;
    flags = (facing ? S_FLIPX : 0) | OBJPAL_BARTENDER;
    xa = facing ? bartender_x + 16 : bartender_x + 8;   // art column A (left half)
    xb = facing ? bartender_x + 8 : bartender_x + 16;   // art column B

    o->y = ytop; o->x = xa; o->tile = base;     o->prop = flags; o++;
    o->y = ytop; o->x = xb; o->tile = base + 2; o->prop = flags; o++;
    o->y = ybot; o->x = xa; o->tile = base + 4; o->prop = flags; o++;
    o->y = ybot; o->x = xb; o->tile = base + 6; o->prop = flags;
}

uint8_t dancers_vis;              // dancer OAM entries written (and so to be hidden again)
uint8_t dancer_sig;               // what the dancer entries show (0x80 | frame << 3 | visible mask); 0: rewrite them

// OAM 27: the tip coin on its bar's counter (blinks in its last second, glints every half second). The second coin is OAM 26 (src/tip.c).
static void draw_coin(void) {
    OAM_item_t *o = shadow_OAM + OAM_COIN;
    if (!tip_timer || (tip_timer < TIP_BLINK && (tip_timer & 4))) { o->y = 0; return; }
    o->y = bar_oam_y[tip_bar] + MUG_DY;
    o->x = tip_x + 8;
    o->tile = OBJ_COIN + (((tip_timer >> 3) & 7) == 0 ? 2 : 0);
    o->prop = OBJPAL_BARTENDER;          // (owner Q37: Sal's palette reads as pale gold; OBJ 5 is the show's alone. DMG: palette 0 too)
}

// CGB OBJ palette 5: the show's (the coin wears Sal's OBJ 0). Loaded with the venue; this reloads it if something else (a fight) had it. Asked for at the end of the frame's
// drawing, written by the VBlank interrupt (vq_vbl) right after the OAM DMA that shows the frame.
static void pal5_check(void) {
    if (!is_cgb) return;
    WIN_FIX();   // (mode 3, here because the DMG never gets this far: the window is not what the plan was made for: the ISR hid it at the plan's end line, or update just showed it)
    if (!show_timer) {                            // the Saloon and the Factory (Color) keep their 5th palette instance in OBJ 5 (lift.c): back from the show's colours when the show ends
        if (pal5_cur == 2 && (SPLIT_ON == 1 || (SPLIT_ON && SPLIT_L_BCPS))) { pal5_src = (const uint16_t *)SPLIT_PAL; pal5_cur = 0; pal5_req = 1; }   // (SPLIT_PAL: that instance, already lifted for SCREEN BRIGHT)
        return;
    }
    if (pal5_cur == 2 || ((SPLIT_ON == 1 || (SPLIT_ON && SPLIT_L_BCPS)) && lift_pi4())) return;   // (the Saloon, Color: a lifted patron wearing the 5th instance keeps OBJ 5 until he is gone: no new lift of one during a show, lift.c try_lift)
    if (SCR_BRIGHT()) { pal5_lift(); pal5_src = pal5_lifted; }   // SCREEN BRIGHT: the VBlank writes pal5_lifted raw, so the show's colours are lifted into it here (src/bright.c)
    else pal5_src = venue.pal[VENUE_PAL_SHOW];
    pal5_cur = 2;
    pal5_req = 1;
}

static void pal5_other(void) {                    // (a lights request: off the coin's own path, VBlank cycles are tight; a fight has no coin, so none waits with it)
    const uint8_t *l = (const uint8_t *)LIGHTS_BUF;
    uint8_t i;
    pal5_req = 0;
    if (!is_cgb) { BGP_REG = l[0]; return; }      // the Mothership's lights (boss_mothership.c lights): DMG the BGP byte, CGB the bar palette, as it computed them
    BCPS_REG = 0x80 | (BGPAL_BAR << 3);
    i = 8;
    do BCPD_REG = *l++; while (--i);
}

static void pal5_write(void) {
    const uint8_t *s = (const uint8_t *)pal5_src;
    if (pal5_req != 1) { pal5_other(); return; }
    OCPS_REG = 0x80 | (OBJPAL_COIN << 3);
    OCPD_REG = s[0]; OCPD_REG = s[1]; OCPD_REG = s[2]; OCPD_REG = s[3];     // (unrolled: the compare above is paid for; this runs in every frame the coin changes)
    s += 4;
    OCPD_REG = s[0]; OCPD_REG = s[1]; OCPD_REG = s[2]; OCPD_REG = s[3];
    pal5_req = 0;
}

void draw_stage_fx(void) {
    uint8_t k;
    draw_coin();
    if (shadow_OAM[OAM_COIN - 1].y || (tip_timer && tip_pocket && TIP2->t)) tip_draw2();   // (the second coin, OAM 26: src/tip.c, banked, so only when it shows or must be hidden)
    pal5_check();
    if (!show_timer || (is_cgb && pal5_cur != 2)) {                // (Color: the dancers wait for their colours, pal5_check)
        if (dancers_vis) {
            OAM_item_t *o = shadow_OAM + OAM_DANCERS;
            for (k = 0; k < NUM_DANCERS * 4; k++) o[k].y = 0;
            dancers_vis = 0;
        }
        dancer_sig = 0;
        return;
    }
    dancers_vis = 1;
    if (!((uint8_t)show_timer & 7) || (dancer_sig & 0x98) != (uint8_t)(0x80 | (dancer_frame << 3))) dancers_step();   // (they pop in and out only on show_timer multiples of 8 (DANCER_STAGGER), else change with the dance step: no banked call to find that out)
}

#if DANCER_STAGGER != 8 || SHOW_FRAMES % 8
#error "draw_stage_fx: the dancers' pop-ins and pop-outs fall on show_timer multiples of 8"
#endif

// Anything that writes OAM entries behind the drawing code's back calls this: the cached ones are redrawn.
void oam_touched(void) {
    bt_drawn[0] = 255;
    dancer_sig = 0;
}

void hide_all_sprites(void) {
    uint8_t i;
    for (i = 0; i < 40; i++) shadow_OAM[i].y = 0;
    oam_used = OAM_FILL + 1;
    lift_oam_n = 0;
    dancers_vis = 0;
    oam_touched();
}
