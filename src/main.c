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
#include "layout.h"
#include "bonus.h"
#include "music.h"

BANKREF_EXTERN(patron_tiles)

// ---- tunables --------------------------------------------------------------
#define TAP_X         144   // bartender_x at the tap (columns 18-19)
#define TAP_GRACE      16   // A pressed within this many px left of the tap snaps to it and fills
#define LEFT_LIMIT     16   // column 2, the end of the door
#define WALK_SPEED      2   // px per frame
#define WALK_ANIM_FRAMES 8  // walk1/walk2 swap period
#define NUM_BARS        4

// patrons: 16x16 px, drawn as a 3x2-tile BG footprint on the two back-wall rows of a bar.
// Position is in pixels (patron_x, left edge of the 16 px figure) plus a fraction; the picture
// is pre-shifted by 0/2/4/6 px in the tile set, so it moves in 2 px steps by swapping map entries.
#define MAX_PATRONS      16
#define PATRON_SPACING   32   // min px between the left edges of two patrons on a bar (no shared tile column)
#define PATRON_FAR_X    128   // a walker whose patron_x gets here has reached the tap (old column 16)
#define PATRON_W         16
#define PUSH_SPEED        1   // px per frame while pushed back
#define DRINK_FRAMES     90
#define SWAY_FRAMES      12   // while drinking the drawn shift alternates by 2 px this often
#define NO_SLOT         255
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
    uint8_t start_mask;     // bit b set: bar b starts with patrons
    uint8_t start_per_bar;  // patrons per started bar (stacked 32 px apart)
    uint8_t quota;          // patrons spawned in the level, including the start ones
    uint16_t spawn_interval; // frames
    uint8_t step_frames;    // frames per 8 px of walking (patron_speed = 8 px / step_frames)
    uint8_t pushback_cols;
    uint8_t serve_score;
} level_cfg_t;
#define LEVEL_ROWS 9
// One row per patron group, in the order of gen_art.py's PATRON_GROUPS.
// The curve is a gentle ramp: level 1 is meant for a first-time player. Patrons
// start on only 2 bars and take ~17 s to cross a bar (16 steps x 64 frames), a
// new one arrives every 5 s, and only 8 must be served. Each level then opens
// one more bar (L2: 3 bars, L3: all 4), shortens the spawn interval
// (300 -> 150 frames) and the step time (64 -> 34 frames per column), and raises
// the quota (8 -> 22). From L6 a second patron per bar is waiting at the start.
// Level 9 lands near what levels 4-5 used to be. Pushback is 4 columns up to
// L4, 3 after. Levels past 9 keep the last row's speeds.
//                 grp mask per quota spawn step push score
static const level_cfg_t level_table[LEVEL_ROWS] = {
    { 0, 0x5, 1,  8, 300, 64, 4,  50 },   // 1 cowboys: bars 0 and 2
    { 1, 0x7, 1, 10, 275, 60, 4,  75 },   // 2 sports: bars 0-2
    { 2, 0xF, 1, 12, 250, 56, 4,  75 },   // 3 lumberjacks: all bars
    { 3, 0xF, 1, 14, 230, 52, 4, 100 },   // 4 chefs
    { 4, 0xF, 1, 16, 210, 48, 3, 100 },   // 5 divers
    { 5, 0xF, 2, 18, 190, 44, 3, 125 },   // 6 robots
    { 6, 0xF, 2, 20, 175, 40, 3, 125 },   // 7 ninjas
    { 7, 0xF, 2, 21, 160, 37, 3, 150 },   // 8 aliens
    { 8, 0xF, 2, 22, 150, 34, 3, 150 },   // 9 zoo; later levels reuse this row's speeds with cycling art
};

// game flow
enum { GS_TITLE, GS_PLAYING, GS_LIFE_LOST, GS_LEVEL_CLEAR, GS_GAME_OVER, GS_PAUSED, GS_BONUS };
#define LIFE_FREEZE_FRAMES  120
#define CLEAR_FRAMES        150
#define LEVEL_BONUS        1000
#define START_LIVES           3
#define BANNER_WY  BAR_TOP_Y(1)       // window overlay: 3 tile rows over bar 1 (y 64..87), clear of the HUD and stage
#define BANNER_LYC (BAR_TOP_Y(1) + 22)  // line where the LCD interrupt switches the window off again

// bartender animation frames (order of assets/art/bartender.txt)
enum { BT_IDLE, BT_WALK1, BT_WALK2, BT_FILL, BT_SLIDE, BT_CATCH, BT_FAIL };

// OBJ tile layout in VRAM
#define OBJ_BARTENDER   0
#define OBJ_MUG         (BARTENDER_FRAMES * BARTENDER_TILES_PER_FRAME)
#define OBJ_GLASS       (OBJ_MUG + MUG_TILE_COUNT)
#define OBJ_MUG_FILL    (OBJ_GLASS + GLASS_TILE_COUNT)
#define OAM_FILL        4     // OAM entry of the filling mug; pooled mugs start at 5
// OAM budget (40): bartender 0-3, fill 4, mugs 5..26 (20 mugs + 2 spare for a breaking glass's 2nd entry),
// tip coin 27, three dancers x 4 entries 28..39
#define OAM_MUG_END    27
#define OAM_COIN       27
#define OAM_DANCERS    28

// mugs
#define MAX_MUGS          20   // pool size: the OAM budget (was 24 before the M5 dancers); the per-bar cap below is unchanged
#define MUGS_PER_BAR       6
#define MUG_START_X      136   // just left of the bartender at the tap
#define MUG_END_X         16   // a mug past x < 16 has left the counter
#define MUG_SPEED_FULL     2
#define FILL_FRAMES       24
#define SLIDE_FRAMES       8
#define GLASS_X            0   // screen x of the glass breaking at the door end
#define GLASS_X_RIGHT    144   // ... and at the tap end
#define GLASS_FRAME_TIME   8   // frames per glass frame
#define OBJ_MUG_DRINK   (OBJ_MUG_FILL + MUG_FILL_TILE_COUNT)
#define OBJ_COIN        (OBJ_MUG_DRINK + MUG_DRINK_TILE_COUNT)
#define OBJ_DANCER      (OBJ_COIN + COIN_TILE_COUNT)
// OBJ tile ids stay below 128: ids 128+ share VRAM (0x8800 block) with the patron BG tiles
enum { MUG_FREE, MUG_FULL, MUG_EMPTY, MUG_BREAKING, MUG_HELD };   // HELD: caught, in a patron's hand

// CGB OBJ palette slots
#define OBJPAL_BARTENDER 0
#define OBJPAL_MUG_FULL  1
#define OBJPAL_MUG_EMPTY 2
#define OBJPAL_GLASS     3
#define OBJPAL_COIN      4
#define OBJPAL_DANCER    5
// CGB BG palette slots (2..7 are free for patrons)
#define BGPAL_BAR        0
#define BGPAL_HUD        1
#define BGPAL_PATRON     2   // 2, 3, 4 = patron variants A, B, C
#define BGPAL_STAGE      5   // stage, curtains, sign (6, 7 free)
#define WALL_RGB    ((uint16_t)(12 | (5 << 5) | (8 << 10)))   // dusky wine

// tips and the stage show
#define TIP_FRAMES       480   // a tip stays this long (8 s)
#define TIP_BLINK         60   // ... and blinks for the last second
#define TIP_SCORE       1500
#define TIP_CHANCE_DEFAULT 64  // out of 256 per served patron (255 = always, 0 = never)
#define SHOW_FRAMES      360
#define DANCER_BEAT       12   // frames per dance step
#define DANCER_STAGGER     8   // dancers pop in / out one after the other
#define DIST_BOB          10   // a distracted patron shifts by 2 px this often
#define SHOW_SPAWN_DIV     4   // after a show the next patron comes after spawn_interval / this (once)
#define NUM_DANCERS        3

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
uint8_t  lives = START_LIVES;
uint8_t  level = 1;
uint8_t  fill_timer;        // frames A has been held at the tap (0 = not filling)
uint8_t  fill_stage;        // 0..3 mug fill animation frame while filling (0 otherwise)
uint8_t  slide_timer;       // frames left showing the "slide" pose
uint8_t  game_over;         // set when lives reach 0; gameplay freezes
uint8_t  game_state;        // GS_*
uint8_t  state_timer;       // frames spent in LIFE_LOST / LEVEL_CLEAR
uint8_t  life_lost;         // a life went this frame; the state machine reacts at the end of update()
uint8_t  overlay_on;        // window banner shown
uint32_t hi_score;          // loaded from SRAM at boot (save.c), written back at game over when beaten
uint8_t  hi_digits[6];
uint8_t  served;            // patrons served (left through the door) this level
uint8_t  start_mask, start_per_bar, cur_group;
uint8_t  hud_dirty;         // HUD_LIVES / HUD_SCORE bits: needs redrawing
uint8_t  score_digits[6];   // the HUD digits, most significant first
static uint8_t score_tiles[6];   // ... as BG tile ids, prepared outside VBlank
static uint8_t lives_tiles[3];
uint8_t  level_clear;       // quota spawned, no patrons, no mugs

// level state (loaded from level_table by start_level)
uint8_t  quota, spawned, step_frames, pushback_cols, serve_score;
uint8_t  patron_speed;      // walking speed in 1/256 px per frame
uint8_t  pushback_px;       // pushback_cols * 8
uint16_t spawn_interval, spawn_timer;   // frames; 16-bit: level 1 spawns every 300
uint8_t  intro_timer;
uint8_t  rng_state;
uint8_t  tip_chance = TIP_CHANCE_DEFAULT;   // 0..255 out of 256; 255 = always
uint16_t tip_timer;         // frames the tip has left (0 = no tip on screen)
uint8_t  tip_bar, tip_x;    // where the coin lies (screen x of its left edge)
uint16_t show_timer;        // frames the show has left (0 = no show)
uint8_t  dancer_frame;      // 0 stand, 1 left kick, 2 arms up, 3 right kick
uint8_t  dance_tick;        // frames in the current dance step
static uint8_t dancers_vis; // dancer OAM entries written (and so to be hidden again)
uint8_t  drain_ticks_max;   // longest VRAM drain so far in DIV ticks (256 cycles each); VBlank is ~17 ticks

// patron pool
uint8_t  patron_state[MAX_PATRONS];    // PATRON_*
uint8_t  patron_bar[MAX_PATRONS];
uint8_t  patron_x[MAX_PATRONS];        // pixel x of the figure's left edge, 0..127 (screen coords)
uint8_t  patron_frac[MAX_PATRONS];     // sub-pixel fraction, 1/256 px
uint8_t  patron_draw[MAX_PATRONS];     // x it is drawn at (patron_x & ~1, +2 while swaying); 255 = not drawn yet
uint8_t  patron_variant[MAX_PATRONS];  // 0..2
uint8_t  patron_timer[MAX_PATRONS];
uint8_t  patron_aux[MAX_PATRONS];      // px left to be pushed back
uint8_t  patron_mug[MAX_PATRONS];      // mug slot held while pushed/drinking, NO_SLOT otherwise
uint8_t  patron_catchx[MAX_PATRONS];   // x of the last full mug it caught (where its tip would lie)
uint8_t  patron_dist[MAX_PATRONS];     // 1: watching the show (stands still, ignores mugs)
uint8_t  patrons_live;

// mug pool (plain arrays so tests can read them by name)
uint8_t  mug_state[MAX_MUGS];   // MUG_FREE / MUG_FULL / MUG_EMPTY / MUG_BREAKING
uint8_t  mug_bar[MAX_MUGS];
uint8_t  mug_x[MAX_MUGS];       // pixel x of the mug's left edge
uint8_t  mug_timer[MAX_MUGS];   // frames since breaking began
uint8_t  mug_patron[MAX_MUGS];  // MUG_HELD: the patron holding it
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

    // BG 5: stage. 0 cream (sign lettering), 1 mauve backdrop, 2 wine curtains, 3 near black
    p[0] = RGB15(31, 28, 18);
    p[1] = RGB15(19, 11, 17);
    p[2] = RGB15(14, 5, 8);
    p[3] = RGB15(3, 2, 6);
    set_bkg_palette(BGPAL_STAGE, 1, p);

    set_sprite_palette(OBJPAL_BARTENDER, 1, palettes[PAL_BARTENDER]);
    set_sprite_palette(OBJPAL_MUG_FULL, 1, palettes[PAL_MUG_FULL]);
    set_sprite_palette(OBJPAL_MUG_EMPTY, 1, palettes[PAL_MUG_EMPTY]);
    set_sprite_palette(OBJPAL_GLASS, 1, palettes[PAL_GLASS]);
    set_sprite_palette(OBJPAL_COIN, 1, palettes[PAL_COIN]);

    // dancers: 1 skin, 2 gold plume and sequins, 3 teal costume/outline (index 0 is transparent)
    p[0] = 0;
    p[1] = RGB15(31, 24, 18);
    p[2] = RGB15(31, 26, 6);
    p[3] = RGB15(1, 8, 13);
    set_sprite_palette(OBJPAL_DANCER, 1, p);
}

static void load_patron_group(uint8_t g) {
    palette_t p;
    uint8_t v, i;
    uint8_t saved = CURRENT_BANK;
    SWITCH_ROM(BANK(patron_tiles));              // the tile data lives in a switchable bank (LCD is off here)
    set_bkg_data(PATRON_TILE_BASE, PATRON_TILES_PER_GROUP, patron_tiles + (uint16_t)g * PATRON_GROUP_BYTES);
    SWITCH_ROM(saved);
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

void vram_put(uint8_t x, uint8_t y, const uint8_t *src, uint8_t n) {
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

// one mug per life (HUD row, cols 9-11) and the score digits (cols 1-6):
// the tile ids are prepared by prep_hud() in the logic phase so that the VBlank
// part is nothing but a copy.
static void prep_hud(void) {
    uint8_t i;
    for (i = 0; i < 3; i++) lives_tiles[i] = (i < lives) ? TILE_HUD_MUG : TILE_HUD_BLANK;
    for (i = 0; i < 6; i++) score_tiles[i] = digit_tile(score_digits[i]);
}

static void draw_lives(void) {
    glyph_row(HUD_ROW, 9, lives_tiles, 3);
    hud_dirty &= ~HUD_LIVES;
}

static void draw_score(void) {
    glyph_row(HUD_ROW, 1, score_tiles, 6);
    hud_dirty &= ~HUD_SCORE;
}

// score as 32-bit total (for tests) plus decimal digits (no division in VBlank)
void add_score(uint16_t n) {
    // The HUD digits are kept in step with `score`. Digits come off n by repeated subtraction: SDCC's 16-bit
    // divide costs ~600 cycles a call, and a patron serve (this, plus the tip roll, plus a redraw) is the
    // heaviest frame of the game.
    static const uint16_t place[5] = { 10000, 1000, 100, 10, 1 };
    uint8_t nd[5], i, d, carry = 0;
    score += n;
    for (i = 0; i < 5; i++) {
        d = 0;
        while (n >= place[i]) { n -= place[i]; d++; }
        nd[i] = d;
    }
    for (i = 5; i != 0; i--) {                       // score_digits[5] is the ones digit, [0] the 100000s
        d = score_digits[i] + nd[i - 1] + carry;
        carry = d >= 10;
        score_digits[i] = carry ? d - 10 : d;
    }
    d = score_digits[0] + carry;
    score_digits[0] = d >= 10 ? d - 10 : d;
    hud_dirty |= HUD_SCORE;
    prep_hud();
}

static void lose_life(void) {
    if (life_lost) return;          // one incident costs one life, however many things go wrong in the same frame
    if (lives) lives--;
    hud_dirty |= HUD_LIVES;
    prep_hud();
    life_lost = 1;
    if (lives == 0) game_over = 1;
}

void draw_hud(void) {
    uint8_t buf[2], i;

    prep_hud();
    for (i = 0; i < 20; i++) row_buf[i] = TILE_HUD_BLANK;
    put_row(HUD_ROW);
    draw_score();                                   // six digits, cols 1-6
    draw_lives();                                   // one mug per life, cols 9-11
    buf[0] = TILE_GLYPH_L;                          // "L" col 17, level as two digits cols 18-19
    glyph_row(HUD_ROW, 17, buf, 1);
    buf[0] = digit_tile(level / 10); buf[1] = digit_tile(level % 10);
    glyph_row(HUD_ROW, 18, buf, 2);
}

static void draw_stage(void) {
    uint8_t y, c;
    for (y = STAGE_FIRST_ROW; y <= STAGE_LAST_ROW; y++) {
        for (c = 2; c < 18; c++) row_buf[c] = (y == STAGE_LAST_ROW) ? TILE_STAGE_EDGE
                                           : ((c + y) & 1) ? TILE_STAGE_WALL2 : TILE_STAGE_WALL;
        row_buf[0] = TILE_CURTAIN_L0; row_buf[1] = TILE_CURTAIN_L1;
        row_buf[18] = TILE_CURTAIN_R0; row_buf[19] = TILE_CURTAIN_R1;
        if (y == STAGE_LAST_ROW) row_buf[0] = row_buf[1] = row_buf[18] = row_buf[19] = TILE_STAGE_EDGE;
        if (y == 1 || y == 2) for (c = 0; c < 6; c++) row_buf[7 + c] = TILE_SIGN + (y - 1) * 6 + c;
        put_row(y);
    }
}

static void draw_bars(void) {
    uint8_t b, r, c, y;
    draw_stage();
    for (b = 0; b < NUM_BARS; b++) {
        for (r = 0; r < 3; r++) {
            y = BAR_TOP_ROW(b) + r;
            for (c = 2; c < 18; c++) {
                row_buf[c] = r == 2 ? TILE_COUNTER
                           : (r == 1 && (c & 1)) ? TILE_WALL2 : TILE_WALL;
            }
            row_buf[0]  = TILE_DOOR + r * 2;
            row_buf[1]  = TILE_DOOR + r * 2 + 1;
            row_buf[18] = TILE_TAP + r * 2;
            row_buf[19] = TILE_TAP + r * 2 + 1;
            put_row(y);
        }
    }
    for (c = 0; c < 20; c++) row_buf[c] = TILE_FLOOR;
    put_row(FLOOR_ROW);
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
            for (i = 0; i < 20; i++) attr[i] = y == HUD_ROW ? BGPAL_HUD : y <= STAGE_LAST_ROW ? BGPAL_STAGE : BGPAL_BAR;
            set_bkg_tiles(0, y, 20, 1, attr);
        }
        VBK_REG = VBK_BANK_0;
    }
    write_all_bars();
}

// ---- patrons: shadow of the two wall rows of each bar + dirty spans ---------------
// The picture is composed into sh_tile/sh_attr during the frame; the changed
// column spans are copied into VRAM at the start of the next frame, right after
// vsync (inside VBlank). A patron redraw touches 3-4 columns x 2 rows x (tile +
// attribute) = 16-24 bytes, so even 4 simultaneous redraws stay inside VBlank
// (vram_ly_min proves it in the tests).
// rows indexed (bar << 1) | r, 32 wide: power-of-two strides keep SDCC from calling its slow multiply
static uint8_t sh_tile[NUM_BARS * 2][32];
static uint8_t sh_attr[NUM_BARS * 2][32];
static uint8_t dirty_x0[NUM_BARS], dirty_x1[NUM_BARS];
static uint8_t fresh;             // bars marked this frame (to be composed)
uint8_t vram_pending;      // anything for drain_vram to do (keeps idle frames cheap)

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
    uint8_t b, p, k, r, row, cc, v, c, t0;
    if (!fresh) return;
    for (b = 0; b < NUM_BARS; b++)
        if (fresh & bar_bit[b]) base_fill(b, dirty_x0[b], dirty_x1[b]);
    for (p = 0; p < MAX_PATRONS; p++) {
        if (patron_state[p] == PATRON_NONE) continue;
        b = patron_bar[p];
        if (!(fresh & bar_bit[b])) continue;
        c = patron_draw[p];
        if (c == 255) continue;                    // not drawn yet
        v = patron_variant[p];
        t0 = PATRON_TILE_BASE + (v << 4) + (v << 3) + (((c >> 1) & 3) * 6);   // variant v * 24 + shift * 6
        c >>= 3;
        for (k = 0; k < 3; k++) {
            cc = c + k;
            if (cc < dirty_x0[b] || cc >= dirty_x1[b]) continue;
            for (r = 0; r < 2; r++) {
                row = (b << 1) | r;
                sh_tile[row][cc] = t0 + r * 3 + k;
                sh_attr[row][cc] = BGPAL_PATRON + v;
            }
        }
    }
    fresh = 0;
}

void clear_dirty(void) {
    uint8_t b;
    vram_pending = 0; fresh = 0;
    for (b = 0; b < NUM_BARS; b++) { dirty_x0[b] = 255; dirty_x1[b] = 0; }
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

void vq_add(uint8_t bank, const uint8_t *src, uint8_t x, uint8_t y, uint8_t n) {
    vq_entry_t *e = &vq[vq_count++];
    e->n = n; e->bank = bank; e->src = src;
    e->dst = (uint8_t *)0x9800 + ((uint16_t)y << 5) + x;
}

// End of the logic phase: turn the HUD flags and dirty bar spans into queue entries.
static void queue_vram(void) {
    uint8_t b, r, row, y, x0, w, cost = 0, c;
    if (hud_dirty & HUD_LIVES) { vq_add(0, lives_tiles, 9, HUD_ROW, 3); cost += 6; }
    if (hud_dirty & HUD_SCORE) { vq_add(0, score_tiles, 1, HUD_ROW, 6); cost += 9; }
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
            y = BAR_TOP_ROW(b) + r;
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
    uint8_t ytop = BAR_TOP_Y(bar) + 16;           // 24 px tall: feet on the bottom of the counter row
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

static void lcd_isr(void) {          // LYC: switch the banner window off below the banner
    HIDE_WIN;
}


// ---- game -----------------------------------------------------------------------
static void win_init(void);
static void enter_title(void);
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
    music_init();
    hi_load();
    SPRITES_8x16;
    set_sprite_data(OBJ_BARTENDER, BARTENDER_FRAMES * BARTENDER_TILES_PER_FRAME, bartender_tiles);
    set_sprite_data(OBJ_MUG, MUG_TILE_COUNT, mug_tiles);
    set_sprite_data(OBJ_GLASS, GLASS_TILE_COUNT, glass_tiles);
    set_sprite_data(OBJ_MUG_FILL, MUG_FILL_TILE_COUNT, mug_fill_tiles);
    set_sprite_data(OBJ_MUG_DRINK, MUG_DRINK_TILE_COUNT, mug_drink_tiles);
    set_sprite_data(OBJ_COIN, COIN_TILE_COUNT, coin_tiles);
    set_sprite_data(OBJ_DANCER, DANCER_FRAMES * DANCER_TILES_PER_FRAME, dancer_tiles);
    for (i = 0; i < 40; i++) move_sprite(i, 0, 0);          // hide everything

    rng_state = 0xA7;
    frame_counter = 0; joy = joy_prev = 0;
    game_over = 0; game_state = GS_TITLE;
    win_init();
    SHOW_BKG; SHOW_SPRITES;
    enter_title();                 // turns the LCD on
}

// ---- mugs and patrons ---------------------------------------------------------------
uint8_t next_rand(void) {                    // 8-bit xorshift, fixed seed => reproducible runs
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
    SFX(SFX_LAUNCH);
}

// Where patron p is drawn: its position at 2 px granularity, +2 px on alternate beats while drinking (sway).
static uint8_t drawn_x(uint8_t p) {
    uint8_t x = patron_x[p] & 0xFE;
    if (patron_state[p] == PATRON_DRINKING && ((patron_timer[p] / SWAY_FRAMES) & 1)) x += 2;
    else if (patron_dist[p] && ((patron_timer[p] / DIST_BOB) & 1)) x += 2;   // watching the show: shifts about
    return x;
}

// Redraw p if its drawn position changed: mark the columns it leaves and the ones it covers.
static void refresh_patron(uint8_t p) {
    uint8_t nd = drawn_x(p), od = patron_draw[p], lo, hi, b = patron_bar[p];
    if (nd == od) return;
    patron_draw[p] = nd;
    if (od == 255) od = nd;
    lo = (nd < od ? nd : od) >> 3;
    hi = (nd < od ? od : nd) >> 3;
    mark_dirty(b, lo, hi + 3);
}

static uint8_t add_patron(uint8_t b, uint8_t x, uint8_t variant) {
    uint8_t p;
    for (p = 0; p < MAX_PATRONS; p++) {
        if (patron_state[p] != PATRON_NONE) continue;
        patron_state[p] = PATRON_WALKING;
        patron_bar[p] = b; patron_x[p] = x; patron_frac[p] = 0; patron_variant[p] = variant;
        patron_timer[p] = 0; patron_aux[p] = 0; patron_mug[p] = NO_SLOT;
        patron_dist[p] = 0; patron_catchx[p] = x;
        patron_draw[p] = 255;
        refresh_patron(p);
        return 1;
    }
    return 0;
}

static void free_held_mug(uint8_t p) {
    uint8_t m = patron_mug[p];
    if (m != NO_SLOT && mug_state[m] == MUG_HELD) {
        mug_state[m] = MUG_FREE;
        if (mugs_live) mugs_live--;
    }
    patron_mug[p] = NO_SLOT;
}

static void remove_patron(uint8_t p) {
    uint8_t d = patron_draw[p] >> 3;
    patron_state[p] = PATRON_NONE;
    free_held_mug(p);
    if (patron_draw[p] != 255) mark_dirty(patron_bar[p], d, d + 3);
    patron_draw[p] = 255;
}

// A served patron may leave a tip where it last caught a mug: not while a tip lies there or a show runs.
static void maybe_tip(uint8_t p) {
    if (tip_timer || show_timer) return;
    if (!tip_chance || (tip_chance != 255 && next_rand() >= tip_chance)) return;   // 0 never (and draws no random number)
    tip_timer = TIP_FRAMES;
    tip_bar = patron_bar[p];
    tip_x = patron_catchx[p];
}

static void end_show(void) {
    uint8_t p;
    show_timer = 0;
    for (p = 0; p < MAX_PATRONS; p++) { patron_dist[p] = 0; patron_timer[p] = 0; }
    if (spawn_timer > (spawn_interval / SHOW_SPAWN_DIV)) spawn_timer = spawn_interval / SHOW_SPAWN_DIV;   // new patrons come sooner, once
}

// The tip is picked up: each walking patron is distracted with probability 1/2 (at least one if any walk).
static void start_show(void) {
    uint8_t p, any = 0, first = NO_SLOT;
    show_timer = SHOW_FRAMES;
    dancer_frame = 0; dance_tick = 0;
    for (p = 0; p < MAX_PATRONS; p++) {
        patron_dist[p] = 0;
        if (patron_state[p] != PATRON_WALKING) continue;
        if (first == NO_SLOT) first = p;
        if (next_rand() & 0x40) { patron_dist[p] = 1; patron_timer[p] = 0; any = 1; }
    }
    if (!any && first != NO_SLOT) { patron_dist[first] = 1; patron_timer[first] = 0; }
}

// is another patron too close ahead (to the right) for p to step one px right?
static uint8_t blocked_ahead(uint8_t p) {
    uint8_t q, x = patron_x[p];
    for (q = 0; q < MAX_PATRONS; q++)
        if (patron_state[q] && patron_bar[q] == patron_bar[p] && patron_x[q] > x
            && (uint8_t)(patron_x[q] - x) <= PATRON_SPACING) return 1;
    return 0;
}

// ... or behind (to the left) for p to slide one px left?
static uint8_t blocked_behind(uint8_t p) {
    uint8_t q, x = patron_x[p];
    for (q = 0; q < MAX_PATRONS; q++)
        if (patron_state[q] && q != p && patron_bar[q] == patron_bar[p] && patron_x[q] < x
            && (uint8_t)(x - patron_x[q]) <= PATRON_SPACING) return 1;
    return 0;
}

// Full mug i at mug_x[i] reaches the rightmost walking patron whose 16 px contain it:
// he catches it, the mug stays in his hand (MUG_HELD) and he is pushed back.
static uint8_t catch_full(uint8_t i) {
    uint8_t p, best = 255, x = mug_x[i], l;
    for (p = 0; p < MAX_PATRONS; p++) {
        if (patron_state[p] != PATRON_WALKING || patron_dist[p] || patron_bar[p] != mug_bar[i]) continue;   // distracted: the mug slides past
        l = patron_x[p];
        if (x >= l && x < l + PATRON_W && (best == 255 || l > patron_x[best])) best = p;
    }
    if (best == 255) return 0;
    patron_state[best] = PATRON_PUSHED;
    patron_timer[best] = 0;
    patron_aux[best] = pushback_px;
    patron_frac[best] = 0;
    patron_mug[best] = i;
    patron_catchx[best] = x;
    mug_state[i] = MUG_HELD;
    mug_patron[i] = best;
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
            if (catch_full(i)) { live++; continue; }
            if (mug_x[i] < MUG_END_X) {          // fell off the left end
                mug_state[i] = MUG_BREAKING;
                mug_timer[i] = 0;
                SFX(SFX_BREAK);
                lose_life();
            }
        } else if (st == MUG_EMPTY) {
            mug_x[i] += MUG_SPEED_EMPTY;
            if (mug_bar[i] == bar && mug_x[i] >= bartender_x && mug_x[i] < bartender_x + 16) {
                mug_state[i] = MUG_FREE;         // caught
                add_score(EMPTY_SCORE);
                SFX(SFX_CATCH);
                continue;
            }
            if (mug_x[i] > MUG_RIGHT_END) {      // fell off the right end
                mug_state[i] = MUG_BREAKING;
                mug_timer[i] = 0;
                SFX(SFX_BREAK);
                lose_life();
            }
        } else if (st == MUG_BREAKING) {
            if (++mug_timer[i] >= GLASS_FRAMES * GLASS_FRAME_TIME) { mug_state[i] = MUG_FREE; continue; }
        } else if (st == MUG_HELD) {             // its patron is gone (or never held it): let it go
            if (patron_state[mug_patron[i]] == PATRON_NONE || patron_mug[mug_patron[i]] != i) { mug_state[i] = MUG_FREE; continue; }
        }
        live++;
    }
    mugs_live = live;
}

// New patron at the door of a random bar, if its first PATRON_SPACING px are free.
static uint8_t try_spawn(void) {
    uint8_t b = (next_rand() >> 2) & 3, p, v;
    for (p = 0; p < MAX_PATRONS; p++)
        if (patron_state[p] && patron_bar[p] == b && patron_x[p] < PATRON_SPACING) return 0;
    v = next_rand() % 3;
    if (!add_patron(b, 0, v)) return 0;
    spawned++;
    return 1;
}

static void update_patrons(void) {
    uint8_t p, st, live = 0, go = (intro_timer == 0), f, m;
    uint8_t *ps = patron_state;                       // pointer walk: much cheaper than indexing in SDCC

    if (!go) {
        intro_timer--;
    } else if (spawned < quota) {
        if (spawn_timer) spawn_timer--;
        else spawn_timer = try_spawn() ? spawn_interval : SPAWN_RETRY;
    }

    for (p = 0; p < MAX_PATRONS; p++, ps++) {
        st = *ps;
        if (st == PATRON_NONE) continue;
        if (st == PATRON_WALKING) {
            if (patron_dist[p]) {
                patron_timer[p]++;                        // watching the show: no walking, just the bob
            } else if (go) {
                f = patron_frac[p] + patron_speed;
                if (f < patron_frac[p]) {                 // carried: one whole pixel
                    if (!blocked_ahead(p)) {
                        patron_frac[p] = f;
                        if (++patron_x[p] >= PATRON_FAR_X) {   // reached the tap
                            remove_patron(p);
                            lose_life();
                            continue;
                        }
                    }
                } else {
                    patron_frac[p] = f;
                }
            }
        } else if (st == PATRON_PUSHED) {
            if (patron_aux[p] == 0) {
                *ps = PATRON_DRINKING; patron_timer[p] = 0;
            } else if (patron_x[p] == 0) {                // pushed out through the door: served
                remove_patron(p);
                served++;
                add_score(serve_score);
                SFX(SFX_SERVE);
                maybe_tip(p);
                continue;
            } else if (blocked_behind(p)) {               // no room: stay put and drink
                patron_aux[p] = 0;
                *ps = PATRON_DRINKING; patron_timer[p] = 0;
            } else {
                patron_x[p] -= PUSH_SPEED;
                patron_aux[p] -= PUSH_SPEED;
                if (patron_aux[p] == 0) { *ps = PATRON_DRINKING; patron_timer[p] = 0; }
            }
        } else {                                          // drinking, then the empty slides out and he walks on
            if (++patron_timer[p] >= DRINK_FRAMES) {
                m = patron_mug[p];
                if (m != NO_SLOT && mug_state[m] == MUG_HELD) {
                    mug_state[m] = MUG_EMPTY;
                    mug_x[m] = patron_x[p] + PATRON_W;
                }
                patron_mug[p] = NO_SLOT;
                *ps = PATRON_WALKING;
                patron_timer[p] = 0;
            }
        }
        refresh_patron(p);
        live++;
    }
    patrons_live = live;
    if (spawned >= quota && patrons_live == 0 && mugs_live == 0) level_clear = 1;
}

// OAM 4: the glass the bartender holds under the tap while filling (hidden otherwise).
// It sits where the launched mug will start (MUG_START_X, the counter-top row).
static void draw_fill(void) {
    OAM_item_t *o = shadow_OAM + OAM_FILL;
    uint8_t y;
    if (!fill_timer) { o->y = 0; return; }
    y = BAR_TOP_Y(bar) + MUG_DY + 16;
    o->y = y; o->x = (uint8_t)(MUG_START_X + 8);
    o->tile = OBJ_MUG_FILL + fill_stage * 2; o->prop = is_cgb ? OBJPAL_MUG_FULL : 0;   // DMG: OBP0 (beer light grey) shows on the white wall; OBP1 would make it white
}

// Held-mug pose by drinking time (index = patron_timer / 4, 0..22): the mug rises from the hand to the
// mouth, tilts and tips while he drinks, and is lowered empty. dx is the sprite's offset from the
// drawn patron x, dy from the bar's top pixel row (art is in sprite rows 2-12, so dy 1 puts a tilted
// mug at face height and dy 6 at the hand, always inside the bar's 24 lines).
#define HELD_DX_CARRY 9
#define HELD_DY_CARRY 6
static const uint8_t drink_frame[23] = { 0,0,0, 1,1,1,1,1,1,1,1, 2,2,2,2,2,2,2,2, 3,3,3,3 };
static const uint8_t drink_dx[23]    = { 9,9,8, 8,8,8,8,8,8,8,8, 8,8,8,8,8,8,8,8, 8,9,9,9 };
static const uint8_t drink_dy[23]    = { 5,3,2, 1,1,1,1,1,1,1,1, 1,1,1,1,1,1,1,1, 2,3,5,6 };

// OAM 5.. : one entry per mug, two per breaking glass. Entries used last frame
// but not this one are hidden (y = 0).
static uint8_t oam_used = OAM_FILL + 1;
static void draw_mugs(void) {
    uint8_t i, n = OAM_FILL + 1, st, y, t, gx;
    OAM_item_t *o = shadow_OAM + OAM_FILL + 1;
    if (mugs_live) {
        for (i = 0; i < MAX_MUGS; i++) {
            st = mug_state[i];
            if (st == MUG_FREE) continue;
            y = BAR_TOP_Y(mug_bar[i]) + MUG_DY + 16;         // mug stands on the counter surface
            if (st == MUG_BREAKING) {
                if (n > OAM_MUG_END - 2) continue;
                gx = mug_x[i] > 80 ? GLASS_X_RIGHT : GLASS_X;   // left or right end
                t = OBJ_GLASS + (mug_timer[i] / GLASS_FRAME_TIME) * GLASS_TILES_PER_FRAME;
                y += mug_timer[i] >> 2;                      // falls a little as it breaks
                o->y = y; o->x = gx + 8;  o->tile = t;     o->prop = S_PALETTE | OBJPAL_GLASS; o++;
                o->y = y; o->x = gx + 16; o->tile = t + 2; o->prop = S_PALETTE | OBJPAL_GLASS; o++;
                n += 2;
            } else if (st == MUG_HELD) {
                if (n >= OAM_MUG_END) continue;
                gx = mug_patron[i];
                t = patron_state[gx] == PATRON_DRINKING ? patron_timer[gx] >> 2 : 255;
                if (t > 22) {                                 // being carried back: upright, full, at the hand
                    t = 0; mug_x[i] = patron_draw[gx] + HELD_DX_CARRY;
                    o->y = BAR_TOP_Y(mug_bar[i]) + HELD_DY_CARRY + 16;
                } else {
                    mug_x[i] = patron_draw[gx] + drink_dx[t];
                    o->y = BAR_TOP_Y(mug_bar[i]) + drink_dy[t] + 16;
                    t = drink_frame[t];
                }
                o->x = mug_x[i] + 8; o->tile = OBJ_MUG_DRINK + t * 2;
                // CGB: full / empty OBJ palette. DMG: the full mug uses OBP0 (beer light grey, foam white) like the
                // fill glass so it shows on the white wall; the empty one uses OBP1 like every empty mug.
                o->prop = t == 3 ? (S_PALETTE | OBJPAL_MUG_EMPTY) : (is_cgb ? OBJPAL_MUG_FULL : 0);
                o++; n++;
            } else {
                if (n >= OAM_MUG_END) continue;
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

static const uint8_t dancer_x[NUM_DANCERS] = { 24, 72, 120 };   // screen x of the left edge, across the stage
static const uint8_t dance_seq[4] = { 0, 1, 2, 3 };               // stand, left kick, arms up, right kick

// OAM 27: the tip coin on its bar's counter (blinks in its last second, glints every half second).
// OAM 28..39: the dancers on the platform, 4 entries each (16x24 art, feet on the top of row STAGE_LAST_ROW).
static void draw_stage_fx(void) {
    OAM_item_t *o = shadow_OAM + OAM_COIN;
    uint8_t k, base, flags, y, elapsed, vis, x;

    if (!tip_timer || (tip_timer < TIP_BLINK && (tip_timer & 4))) {
        o->y = 0;
    } else {
        o->y = BAR_TOP_Y(tip_bar) + MUG_DY + 16;
        o->x = tip_x + 8;
        o->tile = OBJ_COIN + (((tip_timer >> 3) & 7) == 0 ? 2 : 0);
        o->prop = is_cgb ? OBJPAL_COIN : 0;
    }

    o = shadow_OAM + OAM_DANCERS;
    if (!show_timer) {
        if (dancers_vis) {
            for (k = 0; k < NUM_DANCERS * 4; k++) o[k].y = 0;
            dancers_vis = 0;
        }
        return;
    }
    dancers_vis = 1;
    elapsed = SHOW_FRAMES - show_timer > 255 ? 255 : SHOW_FRAMES - show_timer;
    base = OBJ_DANCER + dance_seq[dancer_frame] * DANCER_TILES_PER_FRAME;
    flags = is_cgb ? OBJPAL_DANCER : 0;
    y = STAGE_LAST_ROW * 8 - 24 + 16;           // OAM y of the top entry: art 24 px tall, feet on the platform
    for (k = 0; k < NUM_DANCERS; k++, o += 4) {
        // pop in one after another at the start and leave in the same order at the end
        vis = elapsed >= (k + 1) * DANCER_STAGGER && show_timer > (k + 1) * DANCER_STAGGER;
        if (!vis) { o[0].y = o[1].y = o[2].y = o[3].y = 0; continue; }
        x = dancer_x[k] + 8;
        o[0].y = y;      o[0].x = x;     o[0].tile = base;     o[0].prop = flags;
        o[1].y = y;      o[1].x = x + 8; o[1].tile = base + 2; o[1].prop = flags;
        o[2].y = y + 16; o[2].x = x;     o[2].tile = base + 4; o[2].prop = flags;
        o[3].y = y + 16; o[3].x = x + 8; o[3].tile = base + 6; o[3].prop = flags;
    }
}

// Put the level's start patrons on the bars (2nd group 32 px on where the level has two),
// but never more than the quota still to serve.
static void place_start_patrons(void) {
    uint8_t b, k, placed = 0, remaining = quota > served ? quota - served : 0;
    for (k = 0; k < start_per_bar; k++)
        for (b = 0; b < NUM_BARS; b++)
            if ((start_mask & bar_bit[b]) && placed < remaining) { add_patron(b, PATRON_SPACING * k, next_rand() % 3); placed++; }
    spawned = served + placed;
    patrons_live = placed;
}

static void start_level(void) {
    uint8_t idx = level - 1, b;
    const level_cfg_t *c = &level_table[idx < LEVEL_ROWS ? idx : LEVEL_ROWS - 1];
    cur_group = idx % LEVEL_ROWS;               // art cycles, speeds stay at the last row
    quota = c->quota; spawn_interval = c->spawn_interval; step_frames = c->step_frames;
    pushback_cols = c->pushback_cols; pushback_px = pushback_cols << 3;
    patron_speed = (uint8_t)(2048u / step_frames);          // 8 px per step_frames, in 1/256 px per frame
    serve_score = c->serve_score; start_per_bar = c->start_per_bar;
    start_mask = c->start_mask;
    served = 0; spawn_timer = spawn_interval; intro_timer = INTRO_FRAMES; level_clear = 0;
    for (b = 0; b < MAX_PATRONS; b++) patron_state[b] = PATRON_NONE;
    clear_dirty();
    load_patron_group(cur_group);
    place_start_patrons();
}

// ---- screens and state changes --------------------------------------------------------
uint8_t glyph_for(char c) {
    if (c >= '0' && c <= '9') return TILE_GLYPH_0 + (c - '0');
    switch (c) {
    case 'A': return TILE_GLYPH_A; case 'C': return TILE_GLYPH_C; case 'E': return TILE_GLYPH_E;
    case 'G': return TILE_GLYPH_G; case 'H': return TILE_GLYPH_H; case 'I': return TILE_GLYPH_I;
    case 'L': return TILE_GLYPH_L; case 'M': return TILE_GLYPH_M; case 'O': return TILE_GLYPH_O;
    case 'P': return TILE_GLYPH_P; case 'R': return TILE_GLYPH_R; case 'S': return TILE_GLYPH_S;
    case 'B': return TILE_GLYPH_B; case 'D': return TILE_GLYPH_D; case 'K': return TILE_GLYPH_K;
    case 'N': return TILE_GLYPH_N; case 'W': return TILE_GLYPH_W; case 'Y': return TILE_GLYPH_Y;
    case 'F': return TILE_GLYPH_F; case 'T': return TILE_GLYPH_T; case 'U': return TILE_GLYPH_U; case 'V': return TILE_GLYPH_V;
    }
    return TILE_HUD_BLANK;
}

// text into row_buf at column x, then onto BG row y (LCD off only)
static void text_at(uint8_t y, uint8_t x, const char *s) {
    uint8_t n = 0;
    while (s[n]) { row_buf[n] = glyph_for(s[n]); n++; }
    vram_put(x, y, row_buf, n);
}

static void fill_row(uint8_t y, uint8_t tile) {
    uint8_t i;
    for (i = 0; i < 20; i++) row_buf[i] = tile;
    put_row(y);
}

static void hide_all_sprites(void) {
    uint8_t i;
    for (i = 0; i < 40; i++) shadow_OAM[i].y = 0;
    oam_used = OAM_FILL + 1;
    dancers_vis = 0;
}

// Banner window (tile rows 0..2 of the 0x9C00 map): frame, a text row that
// show_overlay() rewrites through the VBlank queue, frame. Attributes are HUD palette.
static void win_init(void) {
    uint8_t i;
    for (i = 0; i < 20; i++) row_buf[i] = TILE_PANEL_TOP;
    vram_put(0, 32, row_buf, 20);
    for (i = 0; i < 20; i++) row_buf[i] = TILE_HUD_BLANK;
    vram_put(0, 33, row_buf, 20);
    for (i = 0; i < 20; i++) row_buf[i] = TILE_PANEL_BOT;
    vram_put(0, 34, row_buf, 20);
    if (is_cgb) {
        VBK_REG = VBK_BANK_1;
        for (i = 0; i < 20; i++) row_buf[i] = BGPAL_HUD;
        vram_put(0, 32, row_buf, 20); vram_put(0, 33, row_buf, 20); vram_put(0, 34, row_buf, 20);
        VBK_REG = VBK_BANK_0;
    }
    LCDC_REG |= LCDCF_WIN9C00;
    WX_REG = 7; WY_REG = BANNER_WY;
    STAT_REG = STATF_LYC; LYC_REG = BANNER_LYC;
    add_LCD(lcd_isr);
    set_interrupts(VBL_IFLAG | LCD_IFLAG);
}

static void hide_banner_sprites(void) {      // 8x16 sprites that would overlap the banner lines
    uint8_t i;
    for (i = 0; i < 40; i++)
        if (shadow_OAM[i].y > BANNER_WY && shadow_OAM[i].y < BANNER_WY + 40) shadow_OAM[i].y = 0;
}

static uint8_t win_tiles[20];
static void show_overlay(const char *s) {
    uint8_t n = 0, i;
    for (i = 0; i < 20; i++) win_tiles[i] = TILE_HUD_BLANK;
    while (s[n]) n++;
    for (i = 0; i < n; i++) win_tiles[((20 - n) >> 1) + i] = glyph_for(s[i]);
    vq_add(0, win_tiles, 0, 33, 20);
    overlay_on = 1;
    hide_banner_sprites();
}

static uint8_t music_tiles[9];                   // "MUSIC ON " / "MUSIC OFF" on the title (BG row 14)
static void build_music_text(void) {
    const char *t = sound_on ? "MUSIC ON " : "MUSIC OFF";
    uint8_t i;
    for (i = 0; i < 9; i++) music_tiles[i] = glyph_for(t[i]);
}

static void enter_title(void) {
    uint8_t i, y;
    DISPLAY_OFF;
    overlay_on = 0; HIDE_WIN; vq_count = 0; hud_dirty = 0;
    hide_all_sprites();
    set_bkg_data(0, BAR_TILE_COUNT, bar_tiles);
    if (is_cgb) {
        palette_t p;                                  // title lettering: pale gold, amber, dark brown
        p[0] = WALL_RGB; p[1] = RGB15(31, 29, 16); p[2] = RGB15(29, 20, 4); p[3] = RGB15(10, 3, 2);
        set_bkg_palette(BGPAL_PATRON, 1, p);
    }
    for (y = 0; y < 18; y++) fill_row(y, y == 16 ? TILE_COUNTER : y == 17 ? TILE_FLOOR : TILE_WALL);
    for (y = 0; y < 2; y++) {                         // TAPPER, 6 letters of 2x2 tiles at columns 4..15
        static const uint8_t letters[6] = { TILE_TITLE_T, TILE_TITLE_A, TILE_TITLE_P, TILE_TITLE_P,
                                            TILE_TITLE_E, TILE_TITLE_R };
        for (i = 0; i < 12; i++) row_buf[i] = letters[i >> 1] + y * 2 + (i & 1);
        vram_put(4, 4 + y, row_buf, 12);
    }
    fill_row(9, TILE_HUD_BLANK);  text_at(9, 4, "PRESS START");
    fill_row(12, TILE_HUD_BLANK); text_at(12, 5, "HI");
    fill_row(14, TILE_HUD_BLANK); build_music_text(); vram_put(5, 14, music_tiles, 9);
    for (i = 0; i < 6; i++) row_buf[i] = digit_tile(hi_digits[i]);
    vram_put(8, 12, row_buf, 6);
    if (is_cgb) {
        VBK_REG = VBK_BANK_1;
        for (y = 0; y < 18; y++) {
            for (i = 0; i < 20; i++) row_buf[i] = (y == 9 || y == 12 || y == 14) ? BGPAL_HUD : BGPAL_BAR;
            if (y == 4 || y == 5) for (i = 4; i < 16; i++) row_buf[i] = BGPAL_PATRON;
            put_row(y);
        }
        VBK_REG = VBK_BANK_0;
    }
    game_state = GS_TITLE;
    music_play(TUNE_TITLE);
    DISPLAY_ON;
}

static void reset_actors(void) {
    uint8_t i;
    bar = 0; bartender_x = TAP_X; facing = 0; bartender_frame = BT_IDLE; at_tap = 1;
    walk_timer = 0; fill_timer = 0; fill_stage = 0; slide_timer = 0;
    for (i = 0; i < MAX_MUGS; i++) mug_state[i] = MUG_FREE;
    mugs_live = 0;
    tip_timer = 0; show_timer = 0; dancers_vis = 0;      // a bar reset ends the show and takes the tip away
    for (i = 0; i < MAX_PATRONS; i++) patron_dist[i] = 0;
}

// Draw the playfield for the current level/lives/score. Screen transition: LCD off.
static void enter_level_screen(void) {
    DISPLAY_OFF;
    set_sprite_data(OBJ_DANCER, DANCER_FRAMES * DANCER_TILES_PER_FRAME, dancer_tiles);   // the bonus round borrows these OBJ tiles
    overlay_on = 0; HIDE_WIN; vq_count = 0; hud_dirty = 0; life_lost = 0;
    start_level();
    init_scene();
    reset_actors();
    hide_all_sprites();
    draw_bartender();
    game_over = 0;
    game_state = GS_PLAYING;
    music_play(TUNE_GAME);
    DISPLAY_ON;
}

static void start_new_game(void) {
    uint8_t i;
    lives = START_LIVES; level = 1; score = 0; bonus_round = 0;
    for (i = 0; i < 6; i++) score_digits[i] = 0;
    enter_level_screen();
}

// after a lost life: same level, same served count, fresh bars
static void resume_after_life(void) {
    uint8_t p;
    for (p = 0; p < MAX_PATRONS; p++) if (patron_state[p]) remove_patron(p);
    reset_actors();
    hide_all_sprites();
    life_lost = 0;
    spawn_timer = spawn_interval; intro_timer = INTRO_FRAMES;
    place_start_patrons();
    draw_bartender();
    game_state = GS_PLAYING;
}

static void enter_game_over(void) {
    uint8_t i;
    if (score > hi_score) {
        hi_score = score;
        for (i = 0; i < 6; i++) hi_digits[i] = score_digits[i];
        hi_save();
    }
    show_overlay("GAME OVER");
    music_play(TUNE_OVER);
    game_state = GS_GAME_OVER;
}

static void enter_level_clear(void) {
    uint8_t i;
    tip_timer = 0; show_timer = 0;               // a tip is simply forgotten when the level ends
    for (i = OAM_COIN; i < 40; i++) shadow_OAM[i].y = 0;
    dancers_vis = 0;
    add_score(LEVEL_BONUS);
    state_timer = 0;
    show_overlay("LEVEL CLEAR");
    music_play(TUNE_CLEAR);
    game_state = GS_LEVEL_CLEAR;                 // last: whoever sees the state sees the banner and the jingle
}

// glass pieces keep falling while the rest of the picture is frozen
static void update_glass(void) {
    uint8_t i, live = 0;
    for (i = 0; i < MAX_MUGS; i++) {
        if (mug_state[i] == MUG_FREE) continue;
        if (mug_state[i] == MUG_BREAKING && ++mug_timer[i] >= GLASS_FRAMES * GLASS_FRAME_TIME) {
            mug_state[i] = MUG_FREE; continue;
        }
        live++;
    }
    mugs_live = live;
}

static void play_frame(uint8_t pressed) {
    uint8_t moved = 0, old_x, old_bar;

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
    // A pressed close enough to the tap: snap to it, facing the bar (a fresh press only)
    if ((pressed & J_A) && !fill_timer && bartender_x >= TAP_X - TAP_GRACE && bartender_x < TAP_X) {
        bartender_x = TAP_X; facing = 0;
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
        fill_stage = fill_timer >= FILL_FRAMES ? 3 : fill_timer >= 2 * FILL_FRAMES / 3 ? 2
                   : fill_timer >= FILL_FRAMES / 3 ? 1 : 0;
    } else if (at_tap && (pressed & J_A)) {
        fill_timer = 1; fill_stage = 0;
        SFX(SFX_FILL);
    }
    if (!fill_timer) fill_stage = 0;

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

    // tip: counts down, and is picked up by standing on it (16 px span overlapping its 8 px)
    if (tip_timer) {
        tip_timer--;
        if (tip_timer && bar == tip_bar && bartender_x < (uint8_t)(tip_x + 8) && (uint8_t)(bartender_x + 16) > tip_x) {
            tip_timer = 0;
            add_score(TIP_SCORE);
            SFX(SFX_COIN);
            start_show();
        }
    }
    if (show_timer) {
        if (++dance_tick >= DANCER_BEAT) { dance_tick = 0; dancer_frame = (dancer_frame + 1) & 3; }
        if (--show_timer == 0) end_show();
    }

    update_mugs();
    update_patrons();
}

static void update(void) {
    uint8_t pressed;

    vq_flush();                      // first thing after vsync: still in VBlank
    if (overlay_on) SHOW_WIN; else HIDE_WIN;

    joy_prev = joy;
    joy = joypad();
    pressed = joy & ~joy_prev;

    switch (game_state) {
    case GS_TITLE:
        if (pressed & J_SELECT) {
            music_set_on(!sound_on);
            build_music_text();
            vq_add(0, music_tiles, 5, 14, 9);
        }
        if (pressed & J_START) start_new_game();
        frame_counter++;
        return;
    case GS_PLAYING:
        if (pressed & J_START) {
            game_state = GS_PAUSED;
            show_overlay("PAUSE");
            break;
        }
        play_frame(pressed);
        break;
    case GS_LIFE_LOST:
        update_glass();
        fill_timer = 0; fill_stage = 0;
        bartender_frame = BT_FAIL;
        if (++state_timer >= LIFE_FREEZE_FRAMES) {
            if (lives == 0) enter_game_over(); else resume_after_life();
        }
        break;
    case GS_LEVEL_CLEAR:
        if (++state_timer >= CLEAR_FRAMES) {
            if (!(level & 1)) {                  // levels 2, 4, 6, ... are followed by the bonus round
                bonus_enter();
                game_state = GS_BONUS;
                return;
            }
            if (level < 99) level++;
            enter_level_screen();
            return;
        }
        break;
    case GS_BONUS:
        if (bonus_update(pressed)) {
            if (level < 99) level++;
            enter_level_screen();
            return;
        }
        break;
    case GS_GAME_OVER:
        if (pressed & J_START) { enter_title(); return; }
        break;
    case GS_PAUSED:
        if (pressed & J_START) { game_state = GS_PLAYING; overlay_on = 0; }
        break;
    }

    compose_dirty();
    if (vram_pending || hud_dirty) queue_vram();
    if (game_state == GS_PLAYING || game_state == GS_LIFE_LOST) {
        draw_bartender();
        draw_fill();
        draw_mugs();
        draw_stage_fx();
    }
    if (game_state == GS_PLAYING) {              // reactions to what this frame did
        if (life_lost) {
            life_lost = 0;
            state_timer = 0;
            game_state = GS_LIFE_LOST;
            SFX(SFX_LIFE);
        } else if (level_clear) {
            enter_level_clear();
        }
    }
    if (overlay_on) hide_banner_sprites();
    frame_counter++;
}

void main(void) {
    uint8_t ly;
    init();
    while (1) {
        vsync();
        update();            // starts with the VBlank queue drain
        // Music and effects, once per frame, after the drain and after the logic (so they cannot delay the
        // game's input-to-state latency). A heavy frame can leave less than the ~7 lines the driver needs
        // before the next VBlank; then it waits a frame rather than make the game skip one.
        ly = LY_REG;
        if (ly < MUSIC_LATEST_LY || ly >= 144) music_tick(); else music_late++;
    }
}
