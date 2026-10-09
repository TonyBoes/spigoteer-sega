// Spigoteer for Game Boy / Game Boy Color: game flow, screens, HUD and score, input, and the frame loop.
// The rules live in patrons.c and mugs.c, the BG composition and the VBlank queue in render.c (see game.h).
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

#include "game.h"
#include "palettes.h"
#include "bonus.h"
#include "music.h"

BANKREF_EXTERN(art_tiles)

// The tile data (build/art.c) is in a switchable bank; these copy it to VRAM (LCD off or VBlank only).
static void bkg_data(uint8_t first, uint8_t n, const uint8_t *d) {
    uint8_t saved = CURRENT_BANK;
    SWITCH_ROM(BANK(art_tiles));
    set_bkg_data(first, n, d);
    SWITCH_ROM(saved);
}

static void spr_data(uint8_t first, uint8_t n, const uint8_t *d) {
    uint8_t saved = CURRENT_BANK;
    SWITCH_ROM(BANK(art_tiles));
    set_sprite_data(first, n, d);
    SWITCH_ROM(saved);
}

// Per-section frame cost in DIV ticks (256 cycles), only in a measurement build (-DPERF_SECTIONS).
enum { SEC_FLUSH, SEC_INPUT, SEC_MUGS, SEC_PATRONS, SEC_COMPOSE, SEC_QUEUE, SEC_DRAW_BT, SEC_DRAW_MUGS, SEC_FX, SEC_REST, SEC_MUSIC, SEC_N };
#ifdef PERF_SECTIONS
uint8_t  sec_frame[SEC_N];        // this frame's ticks per section
uint8_t  sec_done[SEC_N];         // ... of the last finished frame, and its frame_counter (read by the measuring script)
uint8_t  sec_done_id;
static uint8_t sec_t;
#define SEC_BEGIN() do { uint8_t _k; for (_k = 0; _k < SEC_N; _k++) sec_frame[_k] = 0; sec_t = DIV_REG; } while (0)
#define SEC(i) do { uint8_t _t = DIV_REG; sec_frame[i] += (uint8_t)(_t - sec_t); sec_t = _t; } while (0)
#else
#define SEC_BEGIN()
#define SEC(i)
#endif

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
    uint8_t empty_gap;      // frames kept between two empties' arrivals at the bartender's end (fair empties)
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
// L4, 3 after. Levels past 9 keep the last row's speeds. The empty gap (fair empties, patrons.c) falls from
// 2 s at L1 to a floor of 45 frames at L9, still enough for a bar switch and a short walk.
//                 grp mask per quota spawn step push score gap
static const level_cfg_t level_table[LEVEL_ROWS] = {
    { 0, 0x5, 1,  8, 300, 64, 4,  50, 120 },   // 1 cowboys: bars 0 and 2
    { 1, 0x7, 1, 10, 275, 60, 4,  75, 110 },   // 2 sports: bars 0-2
    { 2, 0xF, 1, 12, 250, 56, 4,  75, 100 },   // 3 lumberjacks: all bars
    { 3, 0xF, 1, 14, 230, 52, 4, 100,  90 },   // 4 chefs
    { 4, 0xF, 1, 16, 210, 48, 3, 100,  80 },   // 5 divers
    { 5, 0xF, 2, 18, 190, 44, 3, 125,  70 },   // 6 robots
    { 6, 0xF, 2, 20, 175, 40, 3, 125,  60 },   // 7 ninjas
    { 7, 0xF, 2, 21, 160, 37, 3, 150,  52 },   // 8 aliens
    { 8, 0xF, 2, 22, 150, 34, 3, 150,  45 },   // 9 zoo; later levels reuse this row's speeds with cycling art
};

// game flow
#define LIFE_FREEZE_FRAMES  120
#define CLEAR_FRAMES        150
#define LEVEL_BONUS        1000
#define START_LIVES           3
#define BANNER_WY  BAR_TOP_Y(1)       // window overlay: 3 tile rows over bar 1 (y 64..87), clear of the HUD and stage
#define BANNER_LYC (BAR_TOP_Y(1) + 22)  // line where the LCD interrupt switches the window off again

#define WALL_RGB    ((uint16_t)(12 | (5 << 5) | (8 << 10)))   // dusky wine

// ---- state (globals => symbols) ----------------------------------------------
uint8_t  bar;               // 0 top .. 3 bottom
uint8_t  bartender_x;       // pixel x of the bartender's left edge (screen coords)
uint8_t  bartender_frac;    // sub-pixel part of his walk (1/256 px); 0 whenever he stands
uint8_t  facing;            // 0 left, 1 right
uint8_t  bartender_frame;   // BT_*
uint8_t  at_tap;            // 1 when bartender_x == TAP_X
uint8_t  walk_timer;        // frames into the current step of the walk cycle (0..WALK_STEP_FRAMES-1)
uint8_t  walk_phase;        // step of the walk cycle: 0 walk1, 1 idle, 2 walk2, 3 idle
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
uint8_t  level_clear;       // quota spawned, no patrons, no mugs

// level state (loaded from level_table by start_level)
uint8_t  quota, spawned, step_frames, pushback_cols, serve_score, empty_gap;
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
    load_patron_tiles(g, PATRON_TILE_BASE);      // 144 pre-shifted + 12 back-view tiles, from the group's bank (LCD is off)
    if (!is_cgb) return;
    for (v = 0; v < 3; v++) {                    // colour 0 = the wall, so the art needs no transparency
        p[0] = WALL_RGB;
        for (i = 1; i < 4; i++) p[i] = palettes[patron_pal_ids[g][v]][i];
        set_bkg_palette(BGPAL_PATRON + v, 1, p);
    }
}

// ---- scene -------------------------------------------------------------------
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
    // The HUD digits are kept in step with `score`. Digits come off n by repeated subtraction of constants: SDCC's
    // 16-bit divide costs ~600 cycles a call, and a patron serve (this, plus the tip roll, plus a redraw) is one of
    // the heaviest frames of the game.
    uint8_t d4 = 0, d3 = 0, d2 = 0, d1 = 0, d, carry;
    score += n;
    while (n >= 10000) { n -= 10000; d4++; }
    while (n >= 1000)  { n -= 1000;  d3++; }
    while (n >= 100)   { n -= 100;   d2++; }
    d = (uint8_t)n;                                  // now n < 100
    while (d >= 10) { d -= 10; d1++; }
    // digit by digit from the ones (score_digits[5]) up; [0] is the 100000s
    d += score_digits[5];
    carry = d >= 10; score_digits[5] = carry ? d - 10 : d;
    d = score_digits[4] + d1 + carry;
    carry = d >= 10; score_digits[4] = carry ? d - 10 : d;
    d = score_digits[3] + d2 + carry;
    carry = d >= 10; score_digits[3] = carry ? d - 10 : d;
    d = score_digits[2] + d3 + carry;
    carry = d >= 10; score_digits[2] = carry ? d - 10 : d;
    d = score_digits[1] + d4 + carry;
    carry = d >= 10; score_digits[1] = carry ? d - 10 : d;
    d = score_digits[0] + carry;
    score_digits[0] = d >= 10 ? d - 10 : d;
    hud_dirty |= HUD_SCORE;
    prep_hud();
}

void lose_life(void) {
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
            for (c = 0; c < 18; c++) {               // the counter runs from the door (column 0) to the keg
                row_buf[c] = r == 2 ? TILE_COUNTER
                           : (r == 1 && (c & 1)) ? TILE_WALL2 : TILE_WALL;
            }
            if (r < 2) {                             // the door: the two wall rows only
                row_buf[0] = TILE_DOOR + r * 2;
                row_buf[1] = TILE_DOOR + r * 2 + 1;
            }
            if (r == 1) row_buf[17] = TILE_SPOUT;
            row_buf[18] = TILE_TAP + r * 2;
            row_buf[19] = TILE_TAP + r * 2 + 1;
            put_row(y);
        }
    }
    for (c = 0; c < 20; c++) row_buf[c] = TILE_FLOOR;
    put_row(FLOOR_ROW);
}

static void init_scene(void) {
    uint8_t y, i;
    uint8_t attr[20];

    bkg_data(0, BAR_TILE_COUNT, bar_tiles);
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
    spr_data(OBJ_BARTENDER, BARTENDER_FRAMES * BARTENDER_TILES_PER_FRAME, bartender_tiles);
    spr_data(OBJ_MUG, MUG_TILE_COUNT, mug_tiles);
    spr_data(OBJ_GLASS, GLASS_TILE_COUNT, glass_tiles);
    spr_data(OBJ_MUG_FILL, MUG_FILL_TILE_COUNT, mug_fill_tiles);
    spr_data(OBJ_MUG_DRINK, MUG_DRINK_TILE_COUNT, mug_drink_tiles);
    spr_data(OBJ_COIN, COIN_TILE_COUNT, coin_tiles);
    spr_data(OBJ_DANCER, DANCER_FRAMES * DANCER_TILES_PER_FRAME, dancer_tiles);
    for (i = 0; i < 40; i++) move_sprite(i, 0, 0);          // hide everything

    rng_state = 0xA7;
    frame_counter = 0; joy = joy_prev = 0;
    game_over = 0; game_state = GS_TITLE;
    CRITICAL { add_VBL(vq_vbl); }  // the VBlank copy queue drains from the interrupt (render.c)
    win_init();
    SHOW_BKG; SHOW_SPRITES;
    enter_title();                 // turns the LCD on
}

uint8_t next_rand(void) {                    // 8-bit xorshift, fixed seed => reproducible runs
    rng_state ^= rng_state << 7;
    rng_state ^= rng_state >> 5;
    rng_state ^= rng_state << 3;
    return rng_state;
}

static void start_level(void) {
    uint8_t idx = level - 1;
    const level_cfg_t *c = &level_table[idx < LEVEL_ROWS ? idx : LEVEL_ROWS - 1];
    cur_group = idx % LEVEL_ROWS;               // art cycles, speeds stay at the last row
    quota = c->quota; spawn_interval = c->spawn_interval; step_frames = c->step_frames;
    pushback_cols = c->pushback_cols; pushback_px = pushback_cols << 3;
    patron_speed = (uint8_t)(2048u / step_frames);          // 8 px per step_frames, in 1/256 px per frame
    serve_score = c->serve_score; start_per_bar = c->start_per_bar; empty_gap = c->empty_gap;
    start_mask = c->start_mask;
    served = 0; spawn_timer = spawn_interval; intro_timer = INTRO_FRAMES; level_clear = 0;
    clear_patrons();
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
        if (shadow_OAM[i].y > BANNER_WY && shadow_OAM[i].y < BANNER_WY + 40) { shadow_OAM[i].y = 0; oam_touched(); }
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
    overlay_on = 0; HIDE_WIN; vq_reset(); hud_dirty = 0;
    hide_all_sprites();
    bkg_data(0, BAR_TILE_COUNT, bar_tiles);
    bkg_data(BAR_TILE_COUNT, TITLE_TILE_COUNT, title_tiles);   // lettering over the patron ids; the level load puts them back
    if (is_cgb) {
        palette_t p;                                  // title lettering: pale gold, amber, dark brown
        p[0] = WALL_RGB; p[1] = RGB15(31, 29, 16); p[2] = RGB15(29, 20, 4); p[3] = RGB15(10, 3, 2);
        set_bkg_palette(BGPAL_PATRON, 1, p);
    }
    for (y = 0; y < 18; y++) fill_row(y, y == 16 ? TILE_COUNTER : y == 17 ? TILE_FLOOR : TILE_WALL);
    for (y = 0; y < 2; y++) {                         // SPIGOTEER, 9 letters of 2x2 tiles at columns 1..18, rows 4..5
        static const uint8_t letters[9] = { TILE_TITLE_S, TILE_TITLE_P, TILE_TITLE_I, TILE_TITLE_G, TILE_TITLE_O,
                                            TILE_TITLE_T, TILE_TITLE_E, TILE_TITLE_E, TILE_TITLE_R };
        for (i = 0; i < 18; i++) row_buf[i] = letters[i >> 1] + y * 2 + (i & 1);
        vram_put(1, 4 + y, row_buf, 18);
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
            if (y == 4 || y == 5) for (i = 1; i < 19; i++) row_buf[i] = BGPAL_PATRON;
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
    bar = 0; bartender_x = TAP_X; bartender_frac = 0; facing = 0; bartender_frame = BT_IDLE; at_tap = 1;
    walk_timer = 0; walk_phase = 0; fill_timer = 0; fill_stage = 0; slide_timer = 0;
    clear_mugs();
    next_arrival = 0;
    tip_timer = 0; show_timer = 0; dancers_vis = 0; oam_touched();      // a bar reset ends the show and takes the tip away
    for (i = 0; i < MAX_PATRONS; i++) patron_dist[i] = 0;
}

// Draw the playfield for the current level/lives/score. Screen transition: LCD off.
static void enter_level_screen(void) {
    DISPLAY_OFF;
    spr_data(OBJ_DANCER, DANCER_FRAMES * DANCER_TILES_PER_FRAME, dancer_tiles);   // the bonus round borrows these OBJ tiles
    overlay_on = 0; HIDE_WIN; vq_reset(); hud_dirty = 0; life_lost = 0;
    start_level();
    init_scene();
    reset_actors();
    hide_all_sprites();
    draw_bartender();
    game_over = 0;
    game_state = GS_PLAYING;
    music_play(TUNE_VENUE0 + cur_group);          // the venue's own tune
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
    music_play(TUNE_VENUE0 + cur_group);         // a show that was running ended with the life: back to the venue's tune
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
    dancers_vis = 0; oam_touched();
    add_score(LEVEL_BONUS);
    state_timer = 0;
    show_overlay("LEVEL CLEAR");
    music_play(TUNE_CLEAR);
    game_state = GS_LEVEL_CLEAR;                 // last: whoever sees the state sees the banner and the jingle
}

// One walking step: 1.5 px per frame as 1 px plus a 1/256 px fraction.
static uint8_t walk_px(void) {
    uint8_t f = bartender_frac;
    bartender_frac = f + WALK_FRAC;
    return bartender_frac < f ? WALK_PX + 1 : WALK_PX;
}

static const uint8_t walk_cycle[4] = { BT_WALK1, BT_IDLE, BT_WALK2, BT_IDLE };

static void play_frame(uint8_t pressed) {
    uint8_t walked = 0, switched, carry, x, d;

    // A full mug still held (A down) is carried along to another bar instead of being cancelled.
    carry = fill_timer >= FILL_FRAMES && (joy & J_A);
    // Up/Down: change bar (wrapping) and snap to that bar's fill position, facing the bar
    switched = pressed & (J_UP | J_DOWN);
    if (pressed & J_UP)        bar = bar == 0 ? NUM_BARS - 1 : bar - 1;
    else if (pressed & J_DOWN) bar = bar == NUM_BARS - 1 ? 0 : bar + 1;
    if (switched) { bartender_x = TAP_X; facing = 0; }

    // Left/Right: walk (1.5 px per frame)
    x = bartender_x;
    if (joy & J_LEFT) {
        facing = 0;
        if (x > LEFT_LIMIT) { d = walk_px(); x = x - d < LEFT_LIMIT ? LEFT_LIMIT : x - d; }
    } else if (joy & J_RIGHT) {
        facing = 1;
        if (x < TAP_X) { d = walk_px(); x = x + d > TAP_X ? TAP_X : x + d; }
    }
    if (x != bartender_x) { bartender_x = x; walked = 1; }
    else bartender_frac = 0;                     // standing (or against a wall): the next walk starts afresh
    // A pressed close enough to the fill position: snap to it (a fresh press only)
    if ((pressed & J_A) && !fill_timer && bartender_x >= TAP_X - TAP_GRACE && bartender_x < TAP_X) {
        bartender_x = TAP_X; bartender_frac = 0;
    }
    at_tap = bartender_x == TAP_X;

    // Filling: A pressed at the fill position starts it; walking, a bar change (unless carrying a full mug)
    // or letting go ends it, and letting go after FILL_FRAMES launches a mug on the bar he is at.
    if (fill_timer) {
        if (switched && carry && !walked) {
            // carried to the new bar's fill position: still holding the full mug under the spout
        } else if (walked || switched || !at_tap || !(joy & J_A)) {
            if (!walked && !switched && at_tap && fill_timer >= FILL_FRAMES) {
                launch_mug();
                slide_timer = SLIDE_FRAMES;
            }
            fill_timer = 0;
            if (!walked) facing = 0;             // turns back to the bar (and slides the mug that way)
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
    else facing = 1;                             // filling: faces the tap, the mug under the spout

    if (slide_timer) slide_timer--;

    if (fill_timer) {
        bartender_frame = BT_FILL;
        walk_timer = 0; walk_phase = 0;
    } else if (walked) {                         // walk1, idle, walk2, idle, WALK_STEP_FRAMES each
        bartender_frame = walk_cycle[walk_phase];
        if (++walk_timer >= WALK_STEP_FRAMES) { walk_timer = 0; walk_phase = (walk_phase + 1) & 3; }
    } else {
        bartender_frame = slide_timer ? BT_SLIDE : BT_IDLE;
        walk_timer = 0; walk_phase = 0;
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

    SEC(SEC_INPUT);
    update_mugs();
    SEC(SEC_MUGS);
    update_patrons();
    SEC(SEC_PATRONS);
}

static void update(void) {
    uint8_t pressed;

    vq_frame_begin();                // the VBlank interrupt has drained last frame's copy list (or it waits)
    if (lists_dirty) { lists_dirty = 0; lists_ok = 0; }   // a test poked patron_state / patron_bar: rebuild the bar lists
    SEC(SEC_FLUSH);
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

    SEC(SEC_REST);
    if (vram_pending || hud_dirty) queue_vram();
    SEC(SEC_QUEUE);
    if (game_state == GS_PLAYING || game_state == GS_LIFE_LOST) {
        draw_bartender();
        draw_fill();
        SEC(SEC_DRAW_BT);
        draw_mugs();
        SEC(SEC_DRAW_MUGS);
        draw_stage_fx();
        SEC(SEC_FX);
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
    SEC(SEC_REST);
}

// Frame-time instrumentation (cheap enough to ship; tests/test_perf.py reads it). "End LY" is the LY register
// when the frame's work ended: 0..143 normally (a frame that finishes inside the VBlank it started in reads 0).
// A frame that ran past the next VBlank reads 144 + the lines since that VBlank began (+154 per extra one).
// During the frame only (sys_time, LY) snapshots are taken; the arithmetic happens after the music tick.
uint16_t perf_logic_max;    // highest end LY of update() so far
uint16_t perf_end_max;      // ... of update() + music tick
uint16_t perf_logic_last, perf_end_last;     // this frame's
uint16_t missed_frames;     // frames that began outside VBlank (the previous one overran) or were skipped
uint8_t  frame_ly_max;      // latest LY a frame's logic started on (after the VBlank interrupt and its drain)
static uint8_t perf_last_t, perf_prev_playing;
static uint8_t snap_t, snap_ly;

static void perf_snap(void) {
    do { snap_t = (uint8_t)sys_time; snap_ly = LY_REG; } while (snap_t != (uint8_t)sys_time);   // (a VBlank between the reads would skew it)
}

static uint16_t perf_ly(uint8_t t0, uint8_t t, uint8_t ly) {
    uint8_t dt = t - t0;
    if (dt == 0) return ly >= 144 ? 0 : ly;
    return 144 + (uint16_t)(dt - 1) * 154 + (ly >= 144 ? ly - 144 : ly + 10);
}

void main(void) {
    uint8_t t0, ly0, st0, lt, lly, d, ok;
    init();
    perf_last_t = (uint8_t)sys_time;
    while (1) {
        vsync();
        t0 = (uint8_t)sys_time; ly0 = LY_REG; st0 = game_state;
        SEC_BEGIN();
        update();
        vq_frame_end();      // the copy list is complete: the next VBlank interrupt executes it
        perf_snap(); lt = snap_t; lly = snap_ly;
        // Music and effects, every frame, after the logic (so they cannot delay the game's input-to-state latency).
        music_tick();
        SEC(SEC_MUSIC);
        perf_snap();
#ifdef PERF_SECTIONS
        for (d = 0; d < SEC_N; d++) sec_done[d] = sec_frame[d];
        sec_done_id = frame_counter;
#endif
        d = t0 - perf_last_t;
        perf_last_t = t0;
        ok = perf_prev_playing && st0 == GS_PLAYING;            // transitions turn the LCD off: not a normal frame
        perf_prev_playing = st0 == GS_PLAYING;
        perf_logic_last = perf_ly(t0, lt, lly);
        perf_end_last = perf_ly(t0, snap_t, snap_ly);
        if (perf_logic_last >= 144) music_late++;               // the tick began only after the next VBlank had begun
        if (!ok) continue;
        if (ly0 < 144 || d != 1) missed_frames++;
        if (ly0 > frame_ly_max) frame_ly_max = ly0;
        if (perf_logic_last > perf_logic_max) perf_logic_max = perf_logic_last;
        if (perf_end_last > perf_end_max) perf_end_max = perf_end_last;
    }
}
