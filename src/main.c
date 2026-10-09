// Tapper for Game Boy / Game Boy Color. Milestone M1: the bar scene and a
// controllable bartender.
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
#define GLASS_X            0   // screen x of the breaking glass (door side)
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
uint8_t  hud_dirty;         // lives need redrawing

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
    p[0] = RGB15(12, 5, 8);                       // dusky wine wall
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

// ---- scene -------------------------------------------------------------------
static uint8_t row_buf[20];

static void put_row(uint8_t y) {
    set_bkg_tiles(0, y, 20, 1, row_buf);
}

static void glyph_row(uint8_t y, uint8_t x, const uint8_t *tiles, uint8_t n) {
    set_bkg_tiles(x, y, n, 1, tiles);
}

static uint8_t digit_tile(uint8_t d) { return TILE_GLYPH_0 + d; }

// one mug per life, row 1 cols 10-12 (3 tiles: small enough for VBlank)
static void draw_lives(void) {
    uint8_t buf[3], i;
    for (i = 0; i < 3; i++) buf[i] = (i < lives) ? TILE_HUD_MUG : TILE_HUD_BLANK;
    glyph_row(1, 10, buf, 3);
    hud_dirty = 0;
}

static void draw_hud(void) {
    uint8_t buf[6], i;
    uint32_t s = score;

    for (i = 0; i < 20; i++) row_buf[i] = TILE_HUD_BLANK;
    put_row(0); put_row(1);

    // "SCORE" row 0 cols 1-5, six digits row 1 cols 1-6
    buf[0] = TILE_GLYPH_S; buf[1] = TILE_GLYPH_C; buf[2] = TILE_GLYPH_O;
    buf[3] = TILE_GLYPH_R; buf[4] = TILE_GLYPH_E;
    glyph_row(0, 1, buf, 5);
    for (i = 6; i != 0; i--) { buf[i - 1] = digit_tile(s % 10); s /= 10; }
    glyph_row(1, 1, buf, 6);

    // "LIVES" row 0 cols 9-13, one mug per life row 1 cols 10-12
    buf[0] = TILE_GLYPH_L; buf[1] = TILE_GLYPH_I; buf[2] = TILE_GLYPH_V;
    buf[3] = TILE_GLYPH_E; buf[4] = TILE_GLYPH_S;
    glyph_row(0, 9, buf, 5);
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

    init_scene();

    bar = 0; bartender_x = TAP_X; facing = 0; bartender_frame = BT_IDLE; at_tap = 1;
    walk_timer = 0; frame_counter = 0; joy = joy_prev = 0;
    fill_timer = 0; slide_timer = 0; game_over = 0; mugs_live = 0;
    for (i = 0; i < MAX_MUGS; i++) mug_state[i] = MUG_FREE;
    draw_bartender();
    SHOW_BKG; SHOW_SPRITES;
    DISPLAY_ON;
}

// ---- mugs -------------------------------------------------------------------------
static void launch_mug(void) {
    uint8_t i, n = 0, slot = MAX_MUGS;
    for (i = 0; i < MAX_MUGS; i++) {
        if (mug_state[i] == MUG_FREE) { if (slot == MAX_MUGS) slot = i; }
        else if (mug_bar[i] == bar) n++;
    }
    if (n >= MUGS_PER_BAR || slot == MAX_MUGS) return;
    mug_state[slot] = MUG_FULL;
    mug_bar[slot] = bar;
    mug_x[slot] = MUG_START_X;
    mug_timer[slot] = 0;
    mugs_live++;
}

static void update_mugs(void) {
    uint8_t i, st, live = 0;
    if (mugs_live == 0) return;
    for (i = 0; i < MAX_MUGS; i++) {
        st = mug_state[i];
        if (st == MUG_FREE) continue;
        if (st == MUG_FULL) {
            mug_x[i] -= MUG_SPEED_FULL;
            if (mug_x[i] < MUG_END_X) {          // fell off the left end
                mug_state[i] = MUG_BREAKING;
                mug_timer[i] = 0;
                if (lives) lives--;
                hud_dirty = 1;
                if (lives == 0) game_over = 1;
            }
        } else if (st == MUG_BREAKING) {
            if (++mug_timer[i] >= GLASS_FRAMES * GLASS_FRAME_TIME) { mug_state[i] = MUG_FREE; continue; }
        }
        live++;
    }
    mugs_live = live;
}

// OAM 4.. : one entry per mug, two per breaking glass. Entries used last frame
// but not this one are hidden (y = 0).
static uint8_t oam_used = 4;
static void draw_mugs(void) {
    uint8_t i, n = 4, st, y, t;
    OAM_item_t *o = shadow_OAM + 4;
    if (mugs_live) {
        for (i = 0; i < MAX_MUGS; i++) {
            st = mug_state[i];
            if (st == MUG_FREE) continue;
            y = (3 + 4 * mug_bar[i]) * 8 + 16;               // mug sits on the counter-top row
            if (st == MUG_BREAKING) {
                if (n > 38) continue;
                t = OBJ_GLASS + (mug_timer[i] / GLASS_FRAME_TIME) * GLASS_TILES_PER_FRAME;
                y += mug_timer[i] >> 2;                      // falls a little as it breaks
                o->y = y; o->x = GLASS_X + 8;  o->tile = t;     o->prop = S_PALETTE | OBJPAL_GLASS; o++;
                o->y = y; o->x = GLASS_X + 16; o->tile = t + 2; o->prop = S_PALETTE | OBJPAL_GLASS; o++;
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

static void update(void) {
    uint8_t pressed, moved = 0, old_x, old_bar;

    if (hud_dirty) draw_lives();     // first thing after vsync: still in VBlank
    if (game_over) return;           // everything stops (M4 adds the screen)

    joy_prev = joy;
    joy = joypad();
    pressed = joy & ~joy_prev;

    update_mugs();

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
