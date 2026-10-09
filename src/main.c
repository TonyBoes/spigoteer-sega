// Tapper for Game Boy / Game Boy Color. Milestone M3: bar scene, bartender,
// mugs, patrons (background tiles) and empty mugs.
//
// Everything a test can assert on is a plain global in WRAM, so it shows up
// in build/game.noi and tests/ can read it by name (bar, bartender_x, ...).
//
// Conventions:
//   - positions in pixels, screen coordinates (OAM's +8/+16 offset is added
//     only when writing OAM)
//   - the whole frame runs between vsync() calls; OAM is written through
//     GBDK's shadow OAM and DMA'd in the VBlank handler
//   - sprites are 8x16; the bartender is 4 entries (2 columns x 2 rows)
#include <gb/gb.h>
#include <gb/cgb.h>
#include <stdint.h>

#include "art.h"
#include "palettes.h"

// ---- tunables --------------------------------------------------------------
#define TAP_X         144   // bartender_x at the tap (columns 18-19)
#define LEFT_LIMIT     16   // column 2, the end of the door
#define WALK_SPEED      2   // px per frame
#define WALK_ANIM_FRAMES 8  // walk1/walk2 swap period
#define NUM_BARS        4

// patrons (16x16 = 2x2 BG tiles on the two back-wall rows of a bar)
#define MAX_PATRONS      16
#define PATRON_SPACING    4   // min column distance between two patrons on a bar
#define PATRON_FAR_COL   16   // a walker whose left column gets here has reached the tap
#define PUSHED_STEP_FRAMES 4  // frames per column while pushed back
#define DRINK_FRAMES     90
#define INTRO_FRAMES     90   // nothing moves or spawns for this long after a level starts
#define SPAWN_RETRY      20   // frames before trying again when the door is crowded
#define PATRON_TILE_BASE BAR_TILE_COUNT
enum { PATRON_NONE, PATRON_WALKING, PATRON_PUSHED, PATRON_DRINKING };

// empty mugs
#define MUG_SPEED_EMPTY   1
#define MUG_RIGHT_END   152   // an empty mug past this x has left the counter
#define EMPTY_SCORE     100
#define HUD_LIVES         1
#define HUD_SCORE         2

// per-level knobs; start_level() copies one row into the globals below
typedef struct {
    uint8_t group;          // patron art group (index into patron_tiles)
    uint8_t start_per_bar;
    uint8_t quota;          // patrons spawned in the level, including the start ones
    uint8_t spawn_interval; // frames
    uint8_t step_frames;    // frames per column step
    uint8_t pushback_cols;
    uint8_t serve_score;
} level_cfg_t;
static const level_cfg_t level_table[] = {
    { 0, 1, 12, 180, 40, 4, 50 },   // level 1: cowboys
};

// bartender animation frames (order of assets/art/bartender.txt)
enum { BT_IDLE, BT_WALK1, BT_WALK2, BT_FILL, BT_SLIDE, BT_CATCH, BT_FAIL };

// OBJ tile layout in VRAM
#define OBJ_BARTENDER   0
#define OBJ_MUG         (BARTENDER_FRAMES * BARTENDER_TILES_PER_FRAME)
#define OBJ_GLASS       (OBJ_MUG + MUG_TILE_COUNT)

// mugs
#define MAX_MUGS          24
#define MUGS_PER_BAR       6
#define MUG_START_X      136   // just left of the bartender at the tap
#define MUG_END_X         16   // a mug past x < 16 has left the counter
#define MUG_SPEED_FULL     2
#define FILL_FRAMES       24
#define SLIDE_FRAMES       8
#define GLASS_X            0   // screen x of the glass breaking at the door end
#define GLASS_X_RIGHT    144   // ... and at the tap end
#define GLASS_FRAME_TIME   8   // frames per glass frame
enum { MUG_FREE, MUG_FULL, MUG_EMPTY, MUG_BREAKING };

// CGB OBJ palette slots
#define OBJPAL_BARTENDER 0
#define OBJPAL_MUG_FULL  1
#define OBJPAL_MUG_EMPTY 2
#define OBJPAL_GLASS     3
// CGB BG palette slots (2..7 are free for patrons)
#define BGPAL_BAR        0
#define BGPAL_HUD        1
#define BGPAL_PATRON     2   // 2, 3, 4 = patron variants A, B, C
#define WALL_RGB    ((uint16_t)(12 | (5 << 5) | (8 << 10)))   // dusky wine

// ---- state (globals => symbols) ----------------------------------------------
uint8_t  bar;               // 0 top .. 3 bottom
uint8_t  bartender_x;       // pixel x of the bartender's left edge (screen coords)
uint8_t  facing;            // 0 left, 1 right
uint8_t  bartender_frame;   // BT_*
uint8_t  at_tap;            // 1 when bartender_x == TAP_X
uint8_t  walk_timer;        // frames spent walking, drives the walk cycle
uint8_t  frame_counter;
uint8_t  joy, joy_prev;
uint32_t score;             // HUD shows 6 digits
uint8_t  is_cgb;            // running on colour hardware
uint8_t  lives = 3;
uint8_t  level = 1;
uint8_t  fill_timer;        // frames A has been held at the tap (0 = not filling)
uint8_t  slide_timer;       // frames left showing the "slide" pose
uint8_t  game_over;         // set when lives reach 0; gameplay freezes
uint8_t  hud_dirty;         // HUD_LIVES / HUD_SCORE bits: needs redrawing
uint8_t  score_digits[6];   // the HUD digits, most significant first
static uint8_t score_tiles[6];   // ... as BG tile ids, prepared outside VBlank
static uint8_t lives_tiles[3];
uint8_t  level_clear;       // quota spawned, no patrons, no mugs

// level state (loaded from level_table by start_level)
uint8_t  quota, spawned, spawn_interval, spawn_timer, step_frames, pushback_cols, serve_score;
uint8_t  intro_timer;
uint8_t  rng_state;
uint8_t  drain_ticks_max;   // longest VRAM drain so far in DIV ticks (256 cycles each); VBlank is ~17 ticks

// patron pool
uint8_t  patron_state[MAX_PATRONS];    // PATRON_*
uint8_t  patron_bar[MAX_PATRONS];
uint8_t  patron_col[MAX_PATRONS];      // left tile column, 0..16
uint8_t  patron_variant[MAX_PATRONS];  // 0..2
uint8_t  patron_timer[MAX_PATRONS];
uint8_t  patron_aux[MAX_PATRONS];      // columns left to be pushed back
uint8_t  patrons_live;

// mug pool (plain arrays so tests can read them by name)
uint8_t  mug_state[MAX_MUGS];   // MUG_FREE / MUG_FULL / MUG_EMPTY / MUG_BREAKING
uint8_t  mug_bar[MAX_MUGS];
uint8_t  mug_x[MAX_MUGS];       // pixel x of the mug's left edge
uint8_t  mug_timer[MAX_MUGS];   // frames since breaking began
uint8_t  mugs_live;             // number of non-free slots

// ---- palettes ----------------------------------------------------------------
#define RGB15(r, g, b) ((uint16_t)((r) | ((g) << 5) | ((b) << 10)))

static void load_cgb_palettes(void) {
    palette_t p;
    uint8_t i;

    // BG 0: wall (colour 0) + counter ramp, shared by door, counter and tap
    for (i = 1; i < 4; i++) p[i] = palettes[PAL_COUNTER][i];
    p[0] = WALL_RGB;
    set_bkg_palette(BGPAL_BAR, 1, p);

    // BG 1: HUD, light text on a dark band (art: '.' text, '#' band)
    p[0] = RGB15(31, 29, 22);
    p[1] = RGB15(24, 20, 10);
    p[2] = RGB15(29, 20, 4);
    p[3] = RGB15(3, 2, 8);
    set_bkg_palette(BGPAL_HUD, 1, p);

    set_sprite_palette(OBJPAL_BARTENDER, 1, palettes[PAL_BARTENDER]);
    set_sprite_palette(OBJPAL_MUG_FULL, 1, palettes[PAL_MUG_FULL]);
    set_sprite_palette(OBJPAL_MUG_EMPTY, 1, palettes[PAL_MUG_EMPTY]);
    set_sprite_palette(OBJPAL_GLASS, 1, palettes[PAL_GLASS]);
}

static void load_patron_group(uint8_t g) {
    palette_t p;
    uint8_t v, i;
    set_bkg_data(PATRON_TILE_BASE, PATRON_TILES_PER_GROUP, patron_tiles + (uint16_t)g * PATRON_GROUP_BYTES);
    if (!is_cgb) return;
    for (v = 0; v < 3; v++) {                    // colour 0 = the wall, so the art needs no transparency
        p[0] = WALL_RGB;
        for (i = 1; i < 4; i++) p[i] = palettes[patron_pal_ids[g][v]][i];
        set_bkg_palette(BGPAL_PATRON + v, 1, p);
    }
}

// ---- scene -------------------------------------------------------------------
static uint8_t row_buf[20];

// Raw BG map writes (map at 0x9800), a hand-written copy loop: SDCC's own loop
// cost ~160 cycles per byte and set_bkg_tiles ~300 per call, which blew the
// VBlank budget with 4 patrons + HUD (measured with LY, see vram_ly_min).
// Only call with the LCD off or during VBlank. Arguments travel in globals so
// the asm does not depend on the calling convention.
uint16_t vr_dst, vr_src;
uint8_t  vr_n;

static void vram_copy(void) {
__asm
    push bc
    ld   a, (_vr_src)
    ld   e, a
    ld   a, (_vr_src + 1)
    ld   d, a
    ld   a, (_vr_dst)
    ld   l, a
    ld   a, (_vr_dst + 1)
    ld   h, a
    ld   a, (_vr_n)
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

static void vram_put(uint8_t x, uint8_t y, const uint8_t *src, uint8_t n) {
    vr_dst = 0x9800 + ((uint16_t)y << 5) + x;
    vr_src = (uint16_t)src;
    vr_n = n;
    vram_copy();
}

static void put_row(uint8_t y) {
    vram_put(0, y, row_buf, 20);
}

static void glyph_row(uint8_t y, uint8_t x, const uint8_t *tiles, uint8_t n) {
    vram_put(x, y, tiles, n);
}

static uint8_t digit_tile(uint8_t d) { return TILE_GLYPH_0 + d; }

// one mug per life (row 1 cols 10-12) and the score digits (row 1 cols 1-6):
// the tile ids are prepared by prep_hud() in the logic phase so that the VBlank
// part is nothing but a copy.
static void prep_hud(void) {
    uint8_t i;
    for (i = 0; i < 3; i++) lives_tiles[i] = (i < lives) ? TILE_HUD_MUG : TILE_HUD_BLANK;
    for (i = 0; i < 6; i++) score_tiles[i] = digit_tile(score_digits[i]);
}

static void draw_lives(void) {
    glyph_row(1, 10, lives_tiles, 3);
    hud_dirty &= ~HUD_LIVES;
}

static void draw_score(void) {
    glyph_row(1, 1, score_tiles, 6);
    hud_dirty &= ~HUD_SCORE;
}

// score as 32-bit total (for tests) plus decimal digits (no division in VBlank)
static void add_score(uint16_t n) {
    uint8_t i, d, carry = 0;
    score += n;
    for (i = 6; i != 0; i--) {
        d = score_digits[i - 1] + (uint8_t)(n % 10) + carry;
        n /= 10;
        carry = d >= 10;
        score_digits[i - 1] = carry ? d - 10 : d;
        if (n == 0 && !carry) break;
    }
    hud_dirty |= HUD_SCORE;
    prep_hud();
}

static void lose_life(void) {
    if (lives) lives--;
    hud_dirty |= HUD_LIVES;
    prep_hud();
    if (lives == 0) game_over = 1;
}

static void draw_hud(void) {
    uint8_t buf[6], i;

    prep_hud();
    for (i = 0; i < 20; i++) row_buf[i] = TILE_HUD_BLANK;
    put_row(0); put_row(1);

    // "SCORE" row 0 cols 1-5, six digits row 1 cols 1-6
    buf[0] = TILE_GLYPH_S; buf[1] = TILE_GLYPH_C; buf[2] = TILE_GLYPH_O;
    buf[3] = TILE_GLYPH_R; buf[4] = TILE_GLYPH_E;
    glyph_row(0, 1, buf, 5);
    draw_score();

    // "LIVES" row 0 cols 9-13, one mug per life row 1 cols 10-12
    buf[0] = TILE_GLYPH_L; buf[1] = TILE_GLYPH_I; buf[2] = TILE_GLYPH_V;
    buf[3] = TILE_GLYPH_E; buf[4] = TILE_GLYPH_S;
    glyph_row(0, 9, buf, 5);
    prep_hud();
    draw_lives();

    // "LV" row 0 cols 17-18, level as two digits row 1
    buf[0] = TILE_GLYPH_L; buf[1] = TILE_GLYPH_V;
    glyph_row(0, 17, buf, 2);
    buf[0] = digit_tile(level / 10); buf[1] = digit_tile(level % 10);
    glyph_row(1, 17, buf, 2);
}

static void draw_bars(void) {
    uint8_t b, r, c, y;
    for (b = 0; b < NUM_BARS; b++) {
        for (r = 0; r < 4; r++) {
            y = 2 + 4 * b + r;
            for (c = 2; c < 18; c++) {
                row_buf[c] = r == 2 ? TILE_COUNTER_TOP
                           : r == 3 ? TILE_COUNTER_FRONT
                           : (r == 1 && (c & 1)) ? TILE_WALL2 : TILE_WALL;
            }
            row_buf[0]  = TILE_DOOR + r * 2;
            row_buf[1]  = TILE_DOOR + r * 2 + 1;
            row_buf[18] = TILE_TAP + r * 2;
            row_buf[19] = TILE_TAP + r * 2 + 1;
            put_row(y);
        }
    }
}

static void write_all_bars(void);

static void init_scene(void) {
    uint8_t y, i;
    uint8_t attr[20];

    set_bkg_data(0, BAR_TILE_COUNT, bar_tiles);
    draw_bars();
    draw_hud();

    if (is_cgb) {                                // palette per row via VRAM bank 1
        VBK_REG = VBK_BANK_1;
        for (y = 0; y < 18; y++) {
            for (i = 0; i < 20; i++) attr[i] = y < 2 ? BGPAL_HUD : BGPAL_BAR;
            set_bkg_tiles(0, y, 20, 1, attr);
        }
        VBK_REG = VBK_BANK_0;
    }
    write_all_bars();
}

// ---- patrons: shadow of the two wall rows of each bar + dirty spans ---------------
// The picture is composed into sh_tile/sh_attr during the frame; the changed
// column spans are copied into VRAM at the start of the next frame, right after
// vsync (inside VBlank). A patron step touches 3 columns x 2 rows x (tile +
// attribute) = 12 bytes, so even 4 simultaneous steps stay well inside VBlank
// (vram_ly_min proves it in the tests).
// rows indexed (bar << 1) | r, 32 wide: power-of-two strides keep SDCC from calling its slow multiply
static uint8_t sh_tile[NUM_BARS * 2][32];
static uint8_t sh_attr[NUM_BARS * 2][32];
static uint8_t dirty_x0[NUM_BARS], dirty_x1[NUM_BARS];
static uint8_t fresh;             // bars marked this frame (to be composed)
static uint8_t vram_pending;      // anything for drain_vram to do (keeps idle frames cheap)

static const uint8_t bar_bit[4] = { 1, 2, 4, 8 };

static void mark_dirty(uint8_t b, uint8_t x0, uint8_t x1) {
    if (x1 > 20) x1 = 20;
    if (x0 < dirty_x0[b]) dirty_x0[b] = x0;
    if (x1 > dirty_x1[b]) dirty_x1[b] = x1;
    vram_pending = 1;
    fresh |= bar_bit[b];
}

// wall/door/tap tiles for columns x0..x1-1 of bar b's two wall rows
static void base_fill(uint8_t b, uint8_t x0, uint8_t x1) {
    uint8_t r, c, row;
    for (r = 0; r < 2; r++) {
        row = (b << 1) | r;
        for (c = x0; c < x1; c++) {
            sh_tile[row][c] = c < 2 ? TILE_DOOR + r * 2 + c
                            : c >= 18 ? TILE_TAP + r * 2 + (c - 18)
                            : (r == 1 && (c & 1)) ? TILE_WALL2 : TILE_WALL;
            sh_attr[row][c] = BGPAL_BAR;
        }
    }
}

// Redraw the dirty span of every bar marked this frame: base tiles, then each
// patron stamped over it (one pass over the patron pool, not one per bar).
static void compose_dirty(void) {
    uint8_t b, p, k, r, row, cc, v, c;
    if (!fresh) return;
    for (b = 0; b < NUM_BARS; b++)
        if (fresh & bar_bit[b]) base_fill(b, dirty_x0[b], dirty_x1[b]);
    for (p = 0; p < MAX_PATRONS; p++) {
        if (patron_state[p] == PATRON_NONE) continue;
        b = patron_bar[p];
        if (!(fresh & bar_bit[b])) continue;
        v = patron_variant[p];
        c = patron_col[p];
        for (k = 0; k < 2; k++) {
            cc = c + k;
            if (cc < dirty_x0[b] || cc >= dirty_x1[b]) continue;
            for (r = 0; r < 2; r++) {
                row = (b << 1) | r;
                sh_tile[row][cc] = PATRON_TILE_BASE + v * 4 + r * 2 + k;
                sh_attr[row][cc] = BGPAL_PATRON + v;
            }
        }
    }
    fresh = 0;
}

static void clear_dirty(void) {
    uint8_t b;
    vram_pending = 0; fresh = 0;
    for (b = 0; b < NUM_BARS; b++) { dirty_x0[b] = 255; dirty_x1[b] = 0; }
}

static void write_span(uint8_t b, uint8_t x0, uint8_t x1) {
    uint8_t r, y, w = x1 - x0;
    for (r = 0; r < 2; r++) {
        y = 2 + (b << 2) + r;
        vram_put(x0, y, &sh_tile[(b << 1) | r][x0], w);
        if (is_cgb) {
            VBK_REG = VBK_BANK_1;
            vram_put(x0, y, &sh_attr[(b << 1) | r][x0], w);
            VBK_REG = VBK_BANK_0;
        }
    }
}

// ---- VBlank copy queue --------------------------------------------------------------
// SDCC code is far too slow to do the BG writes inside VBlank (a single 3-tile row
// span cost ~1500 cycles). So the logic phase builds a list of copy commands
// (what to copy where, in which VRAM bank) and the first thing after vsync is one
// small hand-written loop that executes it, ~40 cycles per byte. The builder keeps
// a cost budget per frame; bars that do not fit stay dirty and go out next frame
// (a patron appears a frame late, nothing tears). drain_ticks_max is the longest
// flush seen, in DIV ticks of 256 cycles; VBlank is ~17 ticks long.
typedef struct {
    uint8_t n;            // bytes to copy (>= 1)
    uint8_t bank;         // VRAM bank to select (0 tiles, 1 CGB attributes)
    const uint8_t *src;
    uint8_t *dst;
} vq_entry_t;               // 6 bytes, the asm below relies on this layout
#define VQ_MAX        24
#define VQ_BUDGET     64    // cost units (~40 cycles each) per frame, see queue_vram
#define VQ_CHUNK       6    // widest span queued for one bar row at a time
vq_entry_t vq[VQ_MAX];
uint8_t    vq_count;

static void vq_exec(void) {
__asm
    push bc
    ld   a, (_vq_count)
    or   a, a
    jr   z, 9$
    ld   c, a
    ld   hl, #_vq
1$:
    ld   b, (hl)            ; n
    inc  hl
    ld   a, (hl+)           ; bank
    ld   (0xFF4F), a
    ld   e, (hl)            ; src
    inc  hl
    ld   d, (hl)
    inc  hl
    ld   a, (hl+)           ; dst low, hl -> dst high
    push hl
    ld   h, (hl)
    ld   l, a
2$:
    ld   a, (de)
    inc  de
    ld   (hl+), a
    dec  b
    jr   nz, 2$
    pop  hl
    inc  hl                 ; next entry
    dec  c
    jr   nz, 1$
    xor  a, a
    ld   (0xFF4F), a        ; back to bank 0
9$:
    pop  bc
__endasm;
}

static void vq_flush(void) {
    uint8_t t0, t;
    if (vq_count == 0) return;
    t0 = DIV_REG;
    vq_exec();
    t = DIV_REG - t0;
    if (t > drain_ticks_max) drain_ticks_max = t;
    vq_count = 0;
}

static void vq_add(uint8_t bank, const uint8_t *src, uint8_t x, uint8_t y, uint8_t n) {
    vq_entry_t *e = &vq[vq_count++];
    e->n = n; e->bank = bank; e->src = src;
    e->dst = (uint8_t *)0x9800 + ((uint16_t)y << 5) + x;
}

// End of the logic phase: turn the HUD flags and dirty bar spans into queue entries.
static void queue_vram(void) {
    uint8_t b, r, row, y, x0, w, cost = 0, c;
    if (hud_dirty & HUD_LIVES) { vq_add(0, lives_tiles, 10, 1, 3); cost += 6; }
    if (hud_dirty & HUD_SCORE) { vq_add(0, score_tiles, 1, 1, 6); cost += 9; }
    hud_dirty = 0;
    vram_pending = 0;
    for (b = 0; b < NUM_BARS; b++) {
        if (dirty_x0[b] >= dirty_x1[b]) continue;
        x0 = dirty_x0[b];
        w = dirty_x1[b] - x0;
        if (w > VQ_CHUNK) w = VQ_CHUNK;
        c = (is_cgb ? 4 : 2) * (3 + w);
        if (cost && cost + c > VQ_BUDGET) { vram_pending = 1; break; }
        for (r = 0; r < 2; r++) {
            row = (b << 1) | r;
            y = 2 + (b << 2) + r;
            vq_add(0, &sh_tile[row][x0], x0, y, w);
            if (is_cgb) vq_add(1, &sh_attr[row][x0], x0, y, w);
        }
        cost += c;
        dirty_x0[b] = x0 + w;
        if (dirty_x0[b] >= dirty_x1[b]) { dirty_x0[b] = 255; dirty_x1[b] = 0; }
        else vram_pending = 1;
    }
}

static void write_all_bars(void) {          // LCD off only
    uint8_t b;
    for (b = 0; b < NUM_BARS; b++) mark_dirty(b, 0, 20);
    compose_dirty();
    for (b = 0; b < NUM_BARS; b++) write_span(b, 0, 20);
    clear_dirty();
}

// ---- bartender sprite -----------------------------------------------------------
// OAM 0..3: [col A top, col B top, col A bottom, col B bottom]. Screen layout
// left to right is A,B when facing left (art faces left) and B,A flipped when
// facing right.
static void draw_bartender(void) {
    uint8_t base = OBJ_BARTENDER + bartender_frame * BARTENDER_TILES_PER_FRAME;
    uint8_t ytop = (3 + 4 * bar) * 8 + 16;        // feet on the bottom of the counter front
    uint8_t ybot = ytop + 16;
    uint8_t flags = (facing ? S_FLIPX : 0) | OBJPAL_BARTENDER;
    uint8_t xa = facing ? bartender_x + 16 : bartender_x + 8;   // art column A (left half)
    uint8_t xb = facing ? bartender_x + 8 : bartender_x + 16;   // art column B
    OAM_item_t *o = shadow_OAM;

    o->y = ytop; o->x = xa; o->tile = base;     o->prop = flags; o++;
    o->y = ytop; o->x = xb; o->tile = base + 2; o->prop = flags; o++;
    o->y = ybot; o->x = xa; o->tile = base + 4; o->prop = flags; o++;
    o->y = ybot; o->x = xb; o->tile = base + 6; o->prop = flags;
}

static void start_level(void);

// ---- game -----------------------------------------------------------------------
static void init(void) {
    uint8_t i;

    DISPLAY_OFF;
    // _cpu alone is not enough under PyBoy: its DMG mode still hands the cart
    // A=0x11. FF4F (VBK) reads 0xFE|bank on colour hardware, but plain 0x00 in
    // PyBoy's DMG mode, so the VBK test rejects PyBoy-DMG. It cannot tell a real
    // DMG apart (unmapped I/O reads 0xFF, which also passes), but a real DMG
    // already fails the _cpu test, so the pair is right on all three.
    VBK_REG = VBK_BANK_0;
    is_cgb = (_cpu == CGB_TYPE) && ((VBK_REG & 0xFE) == 0xFE);
    if (is_cgb) {
        load_cgb_palettes();
    } else {
        BGP_REG  = 0xE4;   // 11 10 01 00: index 3 darkest
        OBP0_REG = 0xD0;   // bartender: idx1 white, idx2 light grey, idx3 black
        OBP1_REG = 0xC4;   // mugs, glass: idx1 light grey, idx2 white, idx3 black (shows on the grey counter)
    }
    SPRITES_8x16;
    set_sprite_data(OBJ_BARTENDER, BARTENDER_FRAMES * BARTENDER_TILES_PER_FRAME, bartender_tiles);
    set_sprite_data(OBJ_MUG, MUG_TILE_COUNT, mug_tiles);
    set_sprite_data(OBJ_GLASS, GLASS_TILE_COUNT, glass_tiles);
    for (i = 0; i < 40; i++) move_sprite(i, 0, 0);          // hide everything

    rng_state = 0xA7;
    start_level();
    init_scene();

    bar = 0; bartender_x = TAP_X; facing = 0; bartender_frame = BT_IDLE; at_tap = 1;
    walk_timer = 0; frame_counter = 0; joy = joy_prev = 0;
    fill_timer = 0; slide_timer = 0; game_over = 0; mugs_live = 0;
    for (i = 0; i < MAX_MUGS; i++) mug_state[i] = MUG_FREE;
    draw_bartender();
    SHOW_BKG; SHOW_SPRITES;
    DISPLAY_ON;
}

// ---- mugs and patrons ---------------------------------------------------------------
static uint8_t next_rand(void) {                    // 8-bit xorshift, fixed seed => reproducible runs
    rng_state ^= rng_state << 7;
    rng_state ^= rng_state >> 5;
    rng_state ^= rng_state << 3;
    return rng_state;
}

static uint8_t spawn_mug(uint8_t b, uint8_t x, uint8_t state) {
    uint8_t i, n = 0, slot = MAX_MUGS;
    for (i = 0; i < MAX_MUGS; i++) {
        if (mug_state[i] == MUG_FREE) { if (slot == MAX_MUGS) slot = i; }
        else if (mug_bar[i] == b) n++;
    }
    if (n >= MUGS_PER_BAR || slot == MAX_MUGS) return 0;
    mug_state[slot] = state;
    mug_bar[slot] = b;
    mug_x[slot] = x;
    mug_timer[slot] = 0;
    mugs_live++;
    return 1;
}

static void launch_mug(void) {
    spawn_mug(bar, MUG_START_X, MUG_FULL);
}

static uint8_t add_patron(uint8_t b, uint8_t col, uint8_t variant) {
    uint8_t p;
    for (p = 0; p < MAX_PATRONS; p++) {
        if (patron_state[p] != PATRON_NONE) continue;
        patron_state[p] = PATRON_WALKING;
        patron_bar[p] = b; patron_col[p] = col; patron_variant[p] = variant;
        patron_timer[p] = 0; patron_aux[p] = 0;
        mark_dirty(b, col, col + 2);
        return 1;
    }
    return 0;
}

static void remove_patron(uint8_t p) {
    patron_state[p] = PATRON_NONE;
    mark_dirty(patron_bar[p], patron_col[p], patron_col[p] + 2);
}

// is another patron too close ahead (to the right) for p to step one column right?
static uint8_t blocked_ahead(uint8_t p) {
    uint8_t q, c = patron_col[p];
    for (q = 0; q < MAX_PATRONS; q++)
        if (patron_state[q] && patron_bar[q] == patron_bar[p] && patron_col[q] > c
            && patron_col[q] < c + 1 + PATRON_SPACING) return 1;
    return 0;
}

// ... or behind (to the left) for p to slide one column left?
static uint8_t blocked_behind(uint8_t p) {
    uint8_t q, c = patron_col[p];
    for (q = 0; q < MAX_PATRONS; q++)
        if (patron_state[q] && patron_bar[q] == patron_bar[p] && patron_col[q] < c
            && c - 1 < patron_col[q] + PATRON_SPACING) return 1;
    return 0;
}

// Full mug at mug_x[i] reaches the rightmost walking patron whose 16 px contain it.
static uint8_t catch_full(uint8_t i) {
    uint8_t p, best = 255, x = mug_x[i], l;
    for (p = 0; p < MAX_PATRONS; p++) {
        if (patron_state[p] != PATRON_WALKING || patron_bar[p] != mug_bar[i]) continue;
        l = patron_col[p] << 3;
        if (x >= l && x < l + 16 && (best == 255 || patron_col[p] > patron_col[best])) best = p;
    }
    if (best == 255) return 0;
    if (patron_col[best] < pushback_cols) {       // close to the door: out he goes
        remove_patron(best);
        add_score(serve_score);
    } else {
        patron_state[best] = PATRON_PUSHED;
        patron_timer[best] = 0;
        patron_aux[best] = pushback_cols;
    }
    return 1;
}

static void update_mugs(void) {
    uint8_t i, st, live = 0;
    if (mugs_live == 0) return;
    for (i = 0; i < MAX_MUGS; i++) {
        st = mug_state[i];
        if (st == MUG_FREE) continue;
        if (st == MUG_FULL) {
            mug_x[i] -= MUG_SPEED_FULL;
            if (catch_full(i)) { mug_state[i] = MUG_FREE; continue; }
            if (mug_x[i] < MUG_END_X) {          // fell off the left end
                mug_state[i] = MUG_BREAKING;
                mug_timer[i] = 0;
                lose_life();
            }
        } else if (st == MUG_EMPTY) {
            mug_x[i] += MUG_SPEED_EMPTY;
            if (mug_bar[i] == bar && mug_x[i] >= bartender_x && mug_x[i] < bartender_x + 16) {
                mug_state[i] = MUG_FREE;         // caught
                add_score(EMPTY_SCORE);
                continue;
            }
            if (mug_x[i] > MUG_RIGHT_END) {      // fell off the right end
                mug_state[i] = MUG_BREAKING;
                mug_timer[i] = 0;
                lose_life();
            }
        } else if (st == MUG_BREAKING) {
            if (++mug_timer[i] >= GLASS_FRAMES * GLASS_FRAME_TIME) { mug_state[i] = MUG_FREE; continue; }
        }
        live++;
    }
    mugs_live = live;
}

// New patron at the door of a random bar, if columns 0..PATRON_SPACING-1 of it are free.
static uint8_t try_spawn(void) {
    uint8_t b = (next_rand() >> 2) & 3, p, v;
    for (p = 0; p < MAX_PATRONS; p++)
        if (patron_state[p] && patron_bar[p] == b && patron_col[p] < PATRON_SPACING) return 0;
    v = next_rand() % 3;
    if (!add_patron(b, 0, v)) return 0;
    spawned++;
    return 1;
}

static void update_patrons(void) {
    uint8_t p, st, live = 0, go = (intro_timer == 0), old, sf = step_frames;
    uint8_t *ps = patron_state, *pt = patron_timer;   // pointer walk: much cheaper than indexing in SDCC

    if (!go) {
        intro_timer--;
    } else if (spawned < quota) {
        if (spawn_timer) spawn_timer--;
        else spawn_timer = try_spawn() ? spawn_interval : SPAWN_RETRY;
    }

    for (p = 0; p < MAX_PATRONS; p++, ps++, pt++) {
        st = *ps;
        if (st == PATRON_NONE) continue;
        if (st == PATRON_WALKING) {
            if (go) {
                if (*pt < sf) { (*pt)++; live++; continue; }
                if (!blocked_ahead(p)) {
                    old = patron_col[p];
                    patron_timer[p] = 0;
                    patron_col[p] = old + 1;
                    mark_dirty(patron_bar[p], old, old + 3);
                    if (old + 1 >= PATRON_FAR_COL) {      // reached the tap
                        patron_state[p] = PATRON_NONE;
                        lose_life();
                        continue;
                    }
                }
            }
        } else if (st == PATRON_PUSHED) {
            if (++patron_timer[p] >= PUSHED_STEP_FRAMES) {
                patron_timer[p] = 0;
                if (patron_aux[p] && patron_col[p] && !blocked_behind(p)) {
                    old = patron_col[p];
                    patron_col[p] = old - 1;
                    patron_aux[p]--;
                    mark_dirty(patron_bar[p], old - 1, old + 2);
                } else {
                    patron_aux[p] = 0;
                }
                if (patron_aux[p] == 0) patron_state[p] = PATRON_DRINKING;
            }
        } else {                                          // drinking, then back to walking
            if (++patron_timer[p] >= DRINK_FRAMES) {
                if (spawn_mug(patron_bar[p], (patron_col[p] << 3) + 16, MUG_EMPTY)) {
                    patron_state[p] = PATRON_WALKING;
                    patron_timer[p] = 0;
                } else {
                    patron_timer[p] = DRINK_FRAMES;       // pool or bar full: try again next frame
                }
            }
        }
        live++;
    }
    patrons_live = live;
    if (spawned >= quota && patrons_live == 0 && mugs_live == 0) level_clear = 1;
}

// OAM 4.. : one entry per mug, two per breaking glass. Entries used last frame
// but not this one are hidden (y = 0).
static uint8_t oam_used = 4;
static void draw_mugs(void) {
    uint8_t i, n = 4, st, y, t, gx;
    OAM_item_t *o = shadow_OAM + 4;
    if (mugs_live) {
        for (i = 0; i < MAX_MUGS; i++) {
            st = mug_state[i];
            if (st == MUG_FREE) continue;
            y = (3 + 4 * mug_bar[i]) * 8 + 16;               // mug sits on the counter-top row
            if (st == MUG_BREAKING) {
                if (n > 38) continue;
                gx = mug_x[i] > 80 ? GLASS_X_RIGHT : GLASS_X;   // left or right end
                t = OBJ_GLASS + (mug_timer[i] / GLASS_FRAME_TIME) * GLASS_TILES_PER_FRAME;
                y += mug_timer[i] >> 2;                      // falls a little as it breaks
                o->y = y; o->x = gx + 8;  o->tile = t;     o->prop = S_PALETTE | OBJPAL_GLASS; o++;
                o->y = y; o->x = gx + 16; o->tile = t + 2; o->prop = S_PALETTE | OBJPAL_GLASS; o++;
                n += 2;
            } else {
                if (n > 39) continue;
                o->y = y; o->x = mug_x[i] + 8;
                if (st == MUG_EMPTY) { o->tile = OBJ_MUG + 2; o->prop = S_PALETTE | OBJPAL_MUG_EMPTY; }
                else                 { o->tile = OBJ_MUG;     o->prop = S_PALETTE | OBJPAL_MUG_FULL; }
                o++; n++;
            }
        }
    }
    for (i = n; i < oam_used; i++) shadow_OAM[i].y = 0;       // hide what is no longer used
    oam_used = n;
}

static void start_level(void) {
    const level_cfg_t *c = &level_table[(level - 1) < (sizeof level_table / sizeof level_table[0]) ? level - 1 : 0];
    uint8_t b, k;
    quota = c->quota; spawn_interval = c->spawn_interval; step_frames = c->step_frames;
    pushback_cols = c->pushback_cols; serve_score = c->serve_score;
    spawned = 0; spawn_timer = spawn_interval; intro_timer = INTRO_FRAMES; level_clear = 0;
    for (b = 0; b < MAX_PATRONS; b++) patron_state[b] = PATRON_NONE;
    clear_dirty();
    load_patron_group(c->group);
    for (b = 0; b < NUM_BARS; b++)
        for (k = 0; k < c->start_per_bar; k++) {
            add_patron(b, 4 * k, next_rand() % 3);
            spawned++;
        }
    patrons_live = spawned;
}

static void update(void) {
    uint8_t pressed, moved = 0, old_x, old_bar;

    vq_flush();                      // first thing after vsync: still in VBlank
    if (game_over) return;           // everything stops (M4 adds the screen)

    joy_prev = joy;
    joy = joypad();
    pressed = joy & ~joy_prev;

    old_x = bartender_x; old_bar = bar;

    // Up/Down: change bar (wrapping) and snap to that bar's tap, facing the bar
    if (pressed & J_UP)        bar = bar == 0 ? NUM_BARS - 1 : bar - 1;
    else if (pressed & J_DOWN) bar = bar == NUM_BARS - 1 ? 0 : bar + 1;
    if (pressed & (J_UP | J_DOWN)) { bartender_x = TAP_X; facing = 0; }

    // Left/Right: walk
    if (joy & J_LEFT) {
        facing = 0;
        if (bartender_x > LEFT_LIMIT) bartender_x -= WALK_SPEED;
    } else if (joy & J_RIGHT) {
        facing = 1;
        if (bartender_x < TAP_X) bartender_x += WALK_SPEED;
    }
    at_tap = bartender_x == TAP_X;
    moved = (bartender_x != old_x) || (bar != old_bar) || (pressed & (J_UP | J_DOWN));

    // Filling: A pressed at the tap starts it; any move or letting go ends it,
    // and letting go after FILL_FRAMES launches a mug.
    if (fill_timer) {
        if (moved || !at_tap || !(joy & J_A)) {
            if (!moved && at_tap && fill_timer >= FILL_FRAMES) {
                launch_mug();
                slide_timer = SLIDE_FRAMES;
            }
            fill_timer = 0;
        } else if (fill_timer < FILL_FRAMES) {
            fill_timer++;
        }
    } else if (at_tap && (pressed & J_A)) {
        fill_timer = 1;
    }

    if (slide_timer) slide_timer--;

    if (fill_timer) {
        bartender_frame = BT_FILL;
        walk_timer = 0;
    } else if (bartender_x != old_x) {
        bartender_frame = ((walk_timer / WALK_ANIM_FRAMES) & 1) ? BT_WALK2 : BT_WALK1;
        walk_timer++;
    } else {
        bartender_frame = slide_timer ? BT_SLIDE : BT_IDLE;
        walk_timer = 0;
    }

    update_mugs();
    update_patrons();
    compose_dirty();
    if (vram_pending || hud_dirty) queue_vram();
    draw_bartender();
    draw_mugs();
    frame_counter++;
}

void main(void) {
    init();
    while (1) {
        vsync();
        update();
    }
}
