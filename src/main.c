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
#include <string.h>

#include "game.h"
#include "palettes.h"
#include "bonus.h"
#include "music.h"
#include "mg.h"
#include "asm_cfg.h"

BANKREF_EXTERN(art_tiles)

// Tile data lives in switchable banks (build/art.c, build/venue_*.c); these copy it to VRAM (LCD off or VBlank
// only) or WRAM and switch back to the caller's bank, so banked code (venue.c) can use them too.
void bkg_data_far(uint8_t first, uint8_t n, const uint8_t *d, uint8_t bank) {
    uint8_t saved = CURRENT_BANK;
    SWITCH_ROM(bank);
    set_bkg_data(first, n, d);
    SWITCH_ROM(saved);
}

void spr_data_far(uint8_t first, uint8_t n, const uint8_t *d, uint8_t bank) {
    uint8_t saved = CURRENT_BANK;
    SWITCH_ROM(bank);
    set_sprite_data(first, n, d);
    SWITCH_ROM(saved);
}

void far_copy(void *dst, const void *src, uint16_t n, uint8_t bank) {
    uint8_t saved = CURRENT_BANK;
    SWITCH_ROM(bank);
    memcpy(dst, src, n);
    SWITCH_ROM(saved);
}

// (game.h redirects GBDK's calls to these: the music ticks through an LCD-off rebuild. The names in parentheses are the real ones.)
void lcd_off_p(void) {
    uint8_t w = TRANS;
    TRANS = w & ~TR_WANT;
    if (!(LCDC_REG & LCDCF_ON)) return;
    if ((w & (TR_WANT | TR_OFF)) == TR_WANT && game_state != GS_PAUSED) { trans_cover(); return; }   // (a scene change: the drink fills the screen, then the LCD goes off)
    while (LY_REG >= 0x92) music_pump();        // (display_off's own two waits: the LCD goes off at line 145)
    while (LY_REG < 0x91) music_pump();
    LCDC_REG &= ~LCDCF_ON;
}

void lcd_on_p(void) {
    uint8_t t = TRANS;
    if (t & TR_PEND) trans_arm();                // (a scene change: the drink is the first frame, src/trans.c)
    LCDC_REG |= LCDCF_ON;
    if ((t & (TR_PEND | TR_HOLD)) == TR_PEND) trans_reveal();   // (the new scene is up: the drink drains; TR_HOLD: the caller still has work to do, and reveals itself)
}

void set_bkg_tiles_p(uint8_t x, uint8_t y, uint8_t w, uint8_t h, const uint8_t *t) {
    (set_bkg_tiles)(x, y, w, h, t);
    if (!(LCDC_REG & LCDCF_ON)) music_pump();
}

static void data_p(uint8_t obj, uint8_t first, uint8_t n, const uint8_t *d) {
    uint8_t k;
    do {
        k = n > 8 ? 8 : n;
        if (obj) (set_sprite_data)(first, k, d); else (set_bkg_data)(first, k, d);
        if (!(LCDC_REG & LCDCF_ON)) music_pump();
        first += 8; d += 128;
    } while (n -= k);
}
void set_bkg_data_p(uint8_t first, uint8_t n, const uint8_t *d) { data_p(0, first, n, d); }
void set_sprite_data_p(uint8_t first, uint8_t n, const uint8_t *d) { data_p(1, first, n, d); }

#define bkg_data(first, n, d) bkg_data_far(first, n, d, BANK(art_tiles))
#define spr_data(first, n, d) spr_data_far(first, n, d, BANK(art_tiles))

// Per-section frame cost in DIV ticks (256 cycles), only in a measurement build (-DPERF_SECTIONS); SEC / SEC_P* in game.h.
#ifdef PERF_SECTIONS
uint8_t  sec_frame[SEC_N];        // this frame's ticks per section
uint8_t  sec_done[SEC_N];         // ... of the last finished frame, and its frame_counter (read by the measuring script)
uint8_t  sec_done_id;
uint8_t  sec_t;
void sec_mark(uint8_t i) { uint8_t t = DIV_REG; sec_frame[i] += (uint8_t)(t - sec_t); sec_t = t; }
#endif

// game flow
#define CLEAR_FRAMES        150


// ---- state (globals => symbols) ----------------------------------------------
uint8_t  bar;               // 0 top .. 3 bottom
uint8_t  bartender_x;       // pixel x of the bartender's left edge (screen coords)
uint8_t  bartender_frac;    // sub-pixel part of his walk (1/256 px); 0 whenever he stands
uint8_t  facing;            // 0 left, 1 right
uint8_t  bartender_frame;   // BT_*
uint8_t  catch_pose;        // frames left of BT_CATCH (an empty caught, a glass taken; M8d)
uint8_t  at_tap;            // 1 when bartender_x == bar_tap[bar] (TAP_X on a straight bar)
uint8_t  tap_now;           // bar_tap[bar], set at the start of every play frame (mugs.c: the catch at the tap, the spout)
uint8_t  walk_timer;        // frames into the current step of the walk cycle (0..WALK_STEP_FRAMES-1)
uint8_t  bt_bob;           // 1 on the passing poses of the walk: his sprites are drawn 1 px higher
uint8_t  walk_phase;        // step of the walk cycle: 0 walk1, 1 idle, 2 walk2, 3 idle
uint8_t  frame_counter;
uint8_t  joy, joy_prev;
uint32_t score;             // HUD shows 6 digits
uint8_t  is_cgb;            // running on colour hardware
uint8_t  lives = START_LIVES;
uint32_t extra_at;          // the score that gives the next extra life (ARCADE, CLASSIC; 0: none in this mode)
uint8_t  level = 1;
uint8_t  fill_timer;        // frames A has been held at the tap (0 = not filling)
uint8_t  fill_stage;        // 0..3 mug fill animation frame while filling (0 otherwise)
uint8_t  slide_timer;       // frames left showing the "slide" pose
uint8_t  game_over;         // set when lives reach 0; gameplay freezes
uint8_t  game_state;        // GS_*
uint8_t  state_timer;       // frames spent in LIFE_LOST / LEVEL_CLEAR
uint8_t  life_lost;         // a life went this frame; the state machine reacts at the end of update()
uint8_t  overlay_on;        // window banner shown
uint32_t hi_score;          // entry 1 of the top-5 table (save.c, SRAM)
uint8_t  hi_digits[6];
uint8_t  served;            // patrons served (pushed back to the left end) this level
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
palette_t coin_pal;                 // PAL_COIN, copied out of the banked palette table at boot (CGB; main_cold.c)

// ---- scene -------------------------------------------------------------------
static uint8_t digit_tile(uint8_t d) { return TILE_GLYPH_0 + d; }

// the lives (HUD row, cols 7-8: the Spigoteer's head and the count as a digit) and the score digits (cols 0-5): the
// tile ids are prepared by prep_hud() in the logic phase so that the VBlank part is nothing but a copy.
void prep_hud(void) {
    uint8_t i;
    lives_tiles[0] = TILE_HUD_HEAD;
    lives_tiles[1] = digit_tile(lives);
    for (i = 0; i < 6; i++) score_tiles[i] = digit_tile(score_digits[i]);
}

// add_score (score as 32-bit total plus decimal digits) lives in src/rom0_relief.c, banked: ROM0 relief.

void lose_life(void) {
    if (life_lost) return;          // one incident costs one life, however many things go wrong in the same frame
    if (lives) lives--;
    hud_dirty |= HUD_LIVES;
    prep_hud();
    life_lost = 1;
    pour_streak = 0;                // (a lost life ends the perfect-pour streak: src/mugs.c)
    if (lives == 0) game_over = 1;
}

void lcd_isr(void) {          // LYC: switch the banner window off below the banner
    HIDE_WIN;
}

// The credits' cast cards on a DMG (src/credits.c): BGP is one palette for the whole background, but a venue's name stays at the top through the
// fades of its three cards, so the frame is split: lines 0-15 (the header) with the header's BGP, then the card's (story_scratch + 68 / + 69: both
// written by trans.c trans_cast and credits.c). Installed in place of lcd_isr by credits_enter, put back by its end.
void cast_isr(void) {
    if (LYC_REG) { BGP_REG = story_scratch[69]; LYC_REG = 0; }
    else { BGP_REG = story_scratch[68]; LYC_REG = 16; }
}

// Milk Run (src/mr.c) splits the frame: its street scrolls under a HUD row that does not. mr_enter swaps this handler in
// for lcd_isr (mg.c's lcd_normal puts lcd_isr back, so no other screen pays a cycle for it). LYC walks MR_SPLIT_LY (SCX =
// the street's, below the HUD) -> the window's end when one shows -> line 144 (SCX = 0 for the next frame's HUD) ->
// MR_SPLIT_LY; mg.c does not set LYC for Milk Run.
void mr_lcd_isr(void) {
    uint8_t ly;
    HIDE_WIN;                                    // (as lcd_isr: the banner window's end)
    if ((game_state == GS_MINI || game_state == GS_PAUSED) && mg_id == MG_MILKRUN) {
        ly = LYC_REG;
        if (ly == 144) { SCX_REG = 0; ly = MR_SPLIT_LY; }
        else if (ly == MR_SPLIT_LY) {
            SCX_REG = MG->mr.scx;
            if (overlay_on) {
                SHOW_WIN;                        // (the banner window is wanted from its top line)
                if (game_state == GS_PAUSED && (state_timer & 8)) ly = 144;   // (pause.c's HOW TO PLAY card: the window is the whole screen)
                else if (game_state == GS_PAUSED) ly = BANNER_WY + ((state_timer & 0x80) ? 38 : 46);   // (pause.c WIN_LYC: a mini-game's menu is 5 rows)
                else ly = mg_phase == MG_RESULT ? BANNER_WY + 46 : BANNER_LYC;
            } else ly = 144;
        } else ly = 144;                         // the window's end: hidden above
        LYC_REG = ly;
    }
}

// Milk Run's VBlank handler (added by mr_enter): the next street column, 17 tiles down the map from `dst` and then, on
// CGB, its 17 attributes (they follow the tiles: one loop, twice), from the start of the mini-game state (struct
// mr_state: dst +0, tiles +2, attributes +19). Only early in VBlank (the copy is ~620 cycles).
static void mr_col_copy(void) {
__asm
    push bc
    ldh  a, (0x4F)
    and  a, #1
    ld   c, a               ; the VRAM bank of the interrupted code
    xor  a, a
    ldh  (0x4F), a
    ld   de, #_story_scratch + 2
0$:
    ld   a, (_story_scratch)
    ld   l, a
    ld   a, (_story_scratch + 1)
    ld   h, a
    ld   b, #17
1$:
    ld   a, (de)
    inc  de
    ld   (hl), a
    ld   a, l
    add  a, #32
    ld   l, a
    jr   nc, 2$
    inc  h
2$:
    dec  b
    jr   nz, 1$
    ldh  a, (0x4F)          ; bank bit 0 on CGB: the attributes next (a DMG reads 0xFF and ends; so does bank 1)
    and  a, #1
    jr   nz, 9$
    ld   a, (_is_cgb)
    or   a, a
    jr   z, 9$
    ld   a, #1
    ldh  (0x4F), a
    jr   0$
9$:
    ld   a, c
    ldh  (0x4F), a
    pop  bc
__endasm;
}

void mr_vbl(void) {
    uint8_t ly;
    if (game_state != GS_MINI || mg_id != MG_MILKRUN || !MG->mr.colq) return;
    ly = LY_REG;
    if (ly < 144 || ly > 147) return;            // too late in VBlank: the column waits for the next
    mr_col_copy();
    MG->mr.colq = 0;
}


// ---- game -----------------------------------------------------------------------
// boot_init (src/main_cold.c, banked): hardware, palettes, sprites, the banner window, then the title

uint8_t next_rand(void) {                    // 8-bit xorshift, fixed seed => reproducible runs
    rng_state ^= rng_state << 7;
    rng_state ^= rng_state >> 5;
    rng_state ^= rng_state << 3;
    return rng_state;
}

#define LOOP_FRAMES    120              // the "LOOP n" banner, before the level's intro
#define GAMEOVER_FRAMES 240             // the GAME OVER banner goes on to the initials / table by itself after 4 s
uint8_t arcade_loop = 1;                // pass through the ten venues: 1, 2, ...
// (start_level: src/level.c, declared in game.h)

// ---- screens and state changes --------------------------------------------------------
// glyph_for and the banner window's setup (win_init): src/main_cold.c
// The letters' tiles, in ROM0 so that any bank reads them without a banked call (GLYPH_FAST, game.h: the full-screen menus; glyph_for keeps its own switch).
const uint8_t glyph_az[26] = {
    TILE_GLYPH_A, TILE_GLYPH_B, TILE_GLYPH_C, TILE_GLYPH_D, TILE_GLYPH_E, TILE_GLYPH_F, TILE_GLYPH_G, TILE_GLYPH_H, TILE_GLYPH_I,
    TILE_GLYPH_J, TILE_GLYPH_K, TILE_GLYPH_L, TILE_GLYPH_M, TILE_GLYPH_N, TILE_GLYPH_O, TILE_GLYPH_P, TILE_GLYPH_Q, TILE_GLYPH_R,
    TILE_GLYPH_S, TILE_GLYPH_T, TILE_GLYPH_U, TILE_GLYPH_V, TILE_GLYPH_W, TILE_GLYPH_X, TILE_GLYPH_Y, TILE_GLYPH_Z };

static void hide_banner_sprites(void) {      // 8x16 sprites that would overlap the banner lines
    uint8_t i;
    for (i = 0; i < 40; i++)
        if (shadow_OAM[i].y > BANNER_WY && shadow_OAM[i].y < BANNER_WY + 40) { shadow_OAM[i].y = 0; oam_touched(); }
}

// A line of text centred in HUD glyphs on map row `row` (32.. = the window's): through the VBlank queue, or straight to
// VRAM while the LCD is off. In ROM0 because the strings live in the callers' own banks (bonus.c, bonus2.c, the
// mini-games): a ROM0 callee keeps the caller's bank mapped. Each call takes the next of SAY_BUFS row buffers, so at most
// SAY_BUFS lines a frame; it returns the row's tiles (the caller may patch them before the VBlank: an icon).
#define SAY_BUFS 4
static uint8_t say_buf[SAY_BUFS * 20], say_k;
uint8_t *mg_say(uint8_t row, const char *s) {
    uint8_t *b = say_buf + say_k, *p = b, n = 20;
    const char *e = s;
    say_k += 20; if (say_k == SAY_BUFS * 20) say_k = 0;
    do *p++ = TILE_HUD_BLANK; while (--n);
    while (*e) e++;
    p = b + ((uint8_t)(20 - (uint8_t)(e - s)) >> 1);
    while (*s) *p++ = glyph_for(*s++);
    if (LCDC_REG & LCDCF_ON) vq_add(0, b, 0, row, 20); else vram_put(0, row, b, 20);
    return b;
}

// A note (overlay_on 2) is a one-row window on the stage wall (y 24..30): its text in window map row 32 (the banner's top
// frame, put back by end_note), WY and LYC moved to it. Nothing plays there, so a message can show while the game runs.
void show_note(const char *s) {
    mg_say(32, s);
    WY_REG = NOTE_WY; LYC_REG = NOTE_LYC;
    overlay_on = 2;
}

void end_note(void) {
    uint8_t *b, n = 20;
    if (overlay_on != 2) return;
    b = mg_say(32, "");
    while (n) b[--n] = TILE_PANEL_TOP;
    WY_REG = BANNER_WY; LYC_REG = BANNER_LYC;
    overlay_on = 0; HIDE_WIN;
}

void show_overlay(const char *s) {
    end_note();
    mg_say(33, s);
    overlay_on = 1;
    hide_banner_sprites();
}

// reset_actors, enter_level_screen, start_new_game: src/main_cold.c

// The debug menu: src/debug.c (opened by the gesture debug_gesture, called from update below).

uint8_t new_rank = TOP_N;   // M10b: the game's place in the top 5 (TOP_N: none)
// resume_after_life, enter_game_over, enter_level_clear: src/main_cold.c

// One walking step: 1.5 px per frame as 1 px plus a 1/256 px fraction.
static uint8_t walk_px(void) {
    uint8_t f = bartender_frac;
    bartender_frac = f + WALK_FRAC;
    return bartender_frac < f ? WALK_PX + 1 : WALK_PX;
}

static const uint8_t walk_cycle[4] = { BT_WALK1, BT_IDLE, BT_WALK2, BT_IDLE };

static void play_frame(uint8_t pressed) {
    uint8_t walked = 0, switched, carry, x, d, t;

    // A full mug still held (A down) is carried along to another bar instead of being cancelled.
    carry = fill_timer >= FILL_FRAMES && (joy & J_A);
    // Up/Down: change bar (wrapping) and snap to that bar's fill position, facing the bar
    switched = pressed & (J_UP | J_DOWN);
    if (pressed & J_UP)        bar = bar == 0 ? NUM_BARS - 1 : bar - 1;
    else if (pressed & J_DOWN) bar = bar == NUM_BARS - 1 ? 0 : bar + 1;
    tap_now = t = bar_tap[bar];                  // the bar's fill position (P6: a slanted bar's is further in)
    if (switched) bar_change(pressed);               // where he lands: src/pour.c (mode A keeps his x; mode B snaps to the tap, dust and swish)

    // Left/Right: walk (1.5 px per frame). On an R bar (CLASSIC, render.c bar_dirs) they swap: the tap is on the left.
    x = bartender_x;
    d = joy;
    if ((bar_dirs & bar_bit[bar]) && ((uint8_t)((d & (J_LEFT | J_RIGHT)) + 1) & 2)) d ^= J_LEFT | J_RIGHT;
    if (d & J_LEFT) {
        facing = 0;
        if (x > LEFT_LIMIT) { d = walk_px(); x = x - d < LEFT_LIMIT ? LEFT_LIMIT : x - d; }
    } else if (d & J_RIGHT) {
        facing = 1;
        if (x < t) { d = walk_px(); x = x + d > t ? t : x + d; }
    }
    if (x != bartender_x) { bartender_x = x; walked = 1; }
    else bartender_frac = 0;                     // standing (or against a wall): the next walk starts afresh
    // A pressed close enough to the fill position: snap to it (a fresh press only)
    if ((pressed & J_A) && !fill_timer && bartender_x >= (uint8_t)(t - TAP_GRACE) && bartender_x < t) {
        bartender_x = t; bartender_frac = 0;
    }
    at_tap = bartender_x == t;

    // Filling: A pressed at the fill position starts it; walking, a bar change (unless carrying a full mug)
    // or letting go ends it, and letting go after FILL_FRAMES launches a mug on the bar he is at.
    if (fill_timer) {
        if (switched && carry && !walked && at_tap) {
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
    if (catch_pose) catch_pose--;

    bt_bob = 0;
    if (fill_timer) {
        bartender_frame = BT_FILL;
        walk_timer = 0; walk_phase = 0;
    } else if (catch_pose) {
        bartender_frame = BT_CATCH;
    } else if (walked) {                         // walk1, idle, walk2, idle, WALK_STEP_FRAMES each
        bartender_frame = walk_cycle[walk_phase];
        bt_bob = !switched & walk_phase;         // up on the passing (idle) pose, down on the contact poses
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
#ifdef GLOW_A
    glow_tick();                     // (src/glow.c, make GLOW=A: the bistro's palette pulse; VBlank, first thing)
#endif
    if (lists_dirty) { lists_dirty = 0; lists_ok = 0; }   // a test poked patron_state / patron_bar: rebuild the bar lists
    SEC(SEC_FLUSH);
    if (overlay_on) SHOW_WIN;
    else {
        HIDE_WIN;
        if (WY_REG == NOTE_WY) { WY_REG = BANNER_WY; LYC_REG = BANNER_LYC; }   // (a note cut off by a life lost or a scene change: overlay_on 0 without end_note; the next window would start on the note's line)
    }

    joy_prev = joy;
    joy = joypad();
#ifdef AUTO_TRANS                       // test-only ROM (tests/test_fade_hw.py, never in a release): A tapped every 16 frames walks title -> STORY -> NORMAL -> the scenes
    joy = 0;                                     // (AUTO_TRANS 1: STORY / NORMAL, 2: ARCADE; the frames count from boot, the menu is up from about 90)
    if (game_state == GS_TITLE && frame_counter >= 96 && (frame_counter & 15) < 2) joy = (AUTO_TRANS == 2 && (frame_counter & 0x10)) ? J_DOWN : J_A;
#endif
#ifdef AUTO_NOTE                        // test-only (the hook is in src/debug.c)
    joy |= auto_note();
#endif
#ifdef AUTO_BOSS                       // test-only (tests/test_fade_hw.py): the hook is in src/debug.c
    joy = auto_boss();
#endif
#ifdef AUTO_CARD                       // test-only (tests/test_fade_hw.py, never in a release): the hook is in src/debug.c (a banked file: ROM0 has no room)
    joy = auto_card();
#endif
    pressed = joy & ~joy_prev;
    if (joy & J_SELECT) pressed = debug_gesture(pressed);   // SELECT + three START taps: the debug menu (src/debug.c; before the state switch: it may change the state)

    switch (game_state) {
    case GS_TITLE:
        if (title_update(pressed) == 2) scores_table();   // the menu (title.c; it starts the games); 2: idle, the top 5
        frame_counter++;
        return;
    case GS_PLAYING:
        if (pressed & (J_START | J_B) && pause_or_pocket(pressed)) break;   // START: the pause menu (src/pause.c); B: a show from the pocketed tip (src/pocket.c)
        play_frame(pressed);
        if (story_on) story_play();              // M11b: the chapter goal
        // 30 fps (DMG, src/half.c): every second VBlank is a logic-only step, the next one is the same plus the picture (the dirty marks,
        // the HUD flags and the chooser's dirty bits just accumulate until then). A step that ends the level or a life, or opens a fight,
        // is drawn at once.
        if ((HALF & HALF_ON) && !(frame_counter & 1) && game_state == GS_PLAYING && !(life_lost | level_clear | boss_on)) {
            if (sa_on > sa_hold && !--sa_timer) stage_anim_step();   // (the frame's other work that is not drawing, as below)
            half_step();
            frame_counter++;
            return;
        }
        break;
    case GS_LIFE_LOST:
        update_glass();
        fill_timer = 0; fill_stage = 0;
        bartender_frame = BT_FAIL;
        if (story_on) story_life_frame();       // story: a strict rule's 2 lives blink
        if (++state_timer >= LIFE_FREEZE_FRAMES) {
            if (lives == 0) enter_game_over(); else resume_after_life();
        }
        break;
    case GS_LEVEL_CLEAR:                         // (CLASSIC: the antics, src/antics.c, and their own length)
        if (state_timer == 255 ? antics_frame() : ++state_timer >= CLEAR_FRAMES) {   // (255: the antics, enter_level_clear)
            if (story_on) { story_level_done(); return; }   // M11b / ARCADE: the next step (story.c)
            if (play_mode == MODE_CLASSIC ? classic_bonus_due() : !(level & 1)) {   // the harness: after even levels
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
            if (story_on) { arcade_next(); return; }  // ARCADE: the bonus round after a venue, then the next venue
            if (level < 99) level++;
            enter_level_screen();
            return;
        }
        break;
    case GS_DEBUG:
        if (debug_step(pressed)) { frame_counter++; return; }
        break;
    case GS_GAME_OVER:                           // M10b: then the initials (top 5) or the table, then the title
        if ((pressed & (J_START | J_A)) || ++state_timer >= GAMEOVER_FRAMES) { scores_after_game(); return; }
        break;
    case GS_INITIALS:
    case GS_SCORES:
        if (scores_update(pressed)) { title_enter(); return; }
        break;
    case GS_PAUSED:
        if (pause_update(pressed)) return;       // RESUME / QUIT TO MENU (src/pause.c); 1: the run is over
        break;
    case GS_STORY:                               // M11b: a cut-scene / TRY AGAIN, the goal banner
    case GS_GOAL:
        if (story_update(pressed)) return;
        break;
    case GS_MINI:                                // a mini-game (src/mg.c); 1: it left, the next screen is up
        if (mg_update(pressed)) return;
        break;
    case GS_JUKEBOX:                             // the title's BONUS: the soundtrack player (src/jukebox.c)
        if (jukebox_update(pressed)) return;
        break;
    case GS_MGLIST:                              // BONUS > MINI GAMES: the list (src/mg_list.c)
        if (mg_list_update(pressed)) return;
        break;
    case GS_LOOP:
        if (++state_timer >= LOOP_FRAMES) { game_state = GS_PLAYING; overlay_on = 0; }
        break;
    }

    SEC(SEC_REST);
    if ((lift_total | lift_hook_op | ovl_dirty) && (game_state == GS_PLAYING || game_state == GS_LIFE_LOST)) lift_frame();   // M13a/b
    SEC(SEC_LIFT);
    // stage animation: on the level screen (sa_on), not frozen by a test (sa_hold), not while paused
    if (sa_on > sa_hold && game_state != GS_PAUSED && !--sa_timer) stage_anim_step();
    SEC(SEC_ANIM);
    if (vram_pending | hud_dirty | sa_left) queue_vram();
    SEC(SEC_QUEUE);
    if (game_state == GS_PLAYING || game_state == GS_LIFE_LOST) {
        // M13c: no OAM DMA while the sprites are being redrawn. A frame whose logic runs past the start of VBlank would
        // otherwise show a half-drawn OAM for a frame (the realistic-peak perf test caught 11 objects on a line: new mugs
        // already written, a dropped patron's entries not yet taken away); it shows the last complete one instead.
        DISABLE_OAM_DMA;
        draw_bartender();
        draw_fill();
        SEC(SEC_DRAW_BT);
        draw_mugs();
        SEC(SEC_DRAW_MUGS);
        if (lift_total | lift_oam_n) draw_lifted();
        SEC(SEC_DLIFT);
        draw_stage_fx();
        if (bar_dirs) mirror_oam();              // P3: bars from the right: their entries to the mirrored place (mirror.c)
        if (story_on | cue_t) pour_frame();     // story: the perfect pour (src/pour.c; last: it counts OAM lines); else the dust puff (OAM 26)
        ENABLE_OAM_DMA;
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
    if (overlay_on == 1) hide_banner_sprites();   // (a note is not over the bars)
    frame_counter++;
    SEC(SEC_REST);
}

// Frame-time instrumentation (tests/test_perf.py reads it; it costs ~1.2 lines a frame, so only the test / playtest builds have it:
// DEBUG_MENU, the Makefile's default, and PERF_SECTIONS; `make release` leaves it out). "End LY" is the LY register
// when the frame's work ended: 0..143 normally (a frame that finishes inside the VBlank it started in reads 0).
// A frame that ran past the next VBlank reads 144 + the lines since that VBlank began (+154 per extra one).
// During the frame only (sys_time, LY) snapshots are taken; the arithmetic happens after the music tick.
uint8_t  frame_t0;          // (uint8_t)sys_time when this frame began (lift.c: has the frame run into the next one?)
#if defined(DEBUG_MENU) || defined(PERF_SECTIONS)
#define FRAME_STATS 1
uint16_t perf_logic_max;    // highest end LY of update() so far
uint16_t perf_end_max;      // ... of update() + music tick
uint16_t perf_logic_last, perf_end_last;     // this frame's
uint16_t missed_frames;     // frames that began outside VBlank (the previous one overran) or were skipped
uint8_t  frame_ly_max;      // latest LY a frame's logic started on (after the VBlank interrupt and its drain)
static uint8_t perf_last_t, perf_prev_playing;
static uint8_t snap_t, snap_ly;

#if ASM_F
// Hand-written (asm pass batch 1, src/asm_cfg.h ASM_F; the C versions are below under #else and are the reference).
static void perf_snap(void) __naked {
__asm
1$:
    ld   a, (_sys_time)
    ld   (_snap_t), a
    ldh  a, (0x44)          ; LY
    ld   (_snap_ly), a
    ld   a, (_sys_time)     ; a VBlank between the reads would skew it: again
    ld   hl, #_snap_t
    cp   a, (hl)
    jr   nz, 1$
    ret
__endasm;
}

// perf_ly(t0 = A, t = E, ly = on the stack, popped here) -> BC: dt = t - t0; dt 0: ly >= 144 ? 0 : ly;
// else 144 + (dt - 1) * 154 + (ly >= 144 ? ly - 144 : ly + 10). The multiply is an add loop: dt is nearly always 1 or 2.
static uint16_t perf_ly(uint8_t t0, uint8_t t, uint8_t ly) __naked {
    (void)t0; (void)t; (void)ly;
__asm
    ld   c, a               ; t0
    ld   a, e
    sub  a, c               ; dt
    ld   c, a
    ldhl sp, #2
    ld   e, (hl)            ; ly
    or   a, a
    jr   nz, 2$
    ld   a, e               ; dt 0
    cp   a, #144
    jr   c, 1$
    xor  a, a
1$:
    ld   c, a
    ld   b, #0
    jr   9$
2$:
    ld   a, e
    cp   a, #144
    jr   c, 3$
    sub  a, #144
    jr   4$
3$:
    add  a, #10
4$:
    ld   e, a
    ld   d, #0
    ld   hl, #144
    add  hl, de             ; 144 + the last-line part
    dec  c                  ; dt - 1 lots of 154
    jr   z, 6$
    ld   de, #154
5$:
    add  hl, de
    dec  c
    jr   nz, 5$
6$:
    ld   b, h
    ld   c, l
9$:
    pop  hl                 ; the return address; the caller's one stack byte goes with it
    inc  sp
    jp   (hl)
__endasm;
}
#else
static void perf_snap(void) {
    do { snap_t = (uint8_t)sys_time; snap_ly = LY_REG; } while (snap_t != (uint8_t)sys_time);   // (a VBlank between the reads would skew it)
}

static uint16_t perf_ly(uint8_t t0, uint8_t t, uint8_t ly) {
    uint8_t dt = t - t0;
    if (dt == 0) return ly >= 144 ? 0 : ly;
    return 144 + (uint16_t)(dt - 1) * 154 + (ly >= 144 ? ly - 144 : ly + 10);
}
#endif

#endif   // FRAME_STATS

// Wait for the next VBlank (GBDK's vsync() without its race). vsync() clears the "VBlank done" flag and then halts: a
// VBlank interrupt that lands between the two sets the flag before the halt, and the CPU then sleeps until the next
// interrupt, the banner's LYC at line 86 or a whole frame later (M13b: the worst-case pile's 218/223 end LY was a frame
// that ended at line 143 and slept until line 87). Here the flag is checked with interrupts off, and the halt (IME 0)
// wakes on any pending interrupt, which is then taken after the ei.
static void frame_wait(void) __naked {
__asm
    ldh  a, (0x40)          ; LCD off: nothing to wait for (as vsync)
    and  a, #0x80
    ret  z
    xor  a, a
    ld   (__vbl_done), a
1$:
    di
    ld   a, (__vbl_done)
    or   a, a
    jr   nz, 2$
    halt
    nop                     ; (if an interrupt was already pending, the halt bug only repeats this nop)
    ei
    jr   1$                 ; the pending interrupt is taken after this instruction
2$:
    ei
    ret
__endasm;
}

void main(void) {
#ifdef FRAME_STATS
    uint8_t t0, ly0, st0, lt, lly, d, ok;
#endif
    PAUSE_NR51 = 0;      // (HRAM is not cleared at power-on: left non-zero, music_tick played every tune as the pause mix)
    boot_init();
#ifdef FRAME_STATS
    perf_last_t = (uint8_t)sys_time;
#endif
    while (1) {
        // 30 fps: a step that ran past a VBlank has used that VBlank's time, so the next step starts at once, not a frame later (the drawn step is
        // the long one, the logic-only step after it the short one); a step that ends just before a VBlank and is overtaken between the check and
        // the wait loses one: the next step starts at once, too (HALF_OWED).
        if (HALF & HALF_OWED) HALF &= ~HALF_OWED;
        else if (!((HALF & HALF_ON) && game_state == GS_PLAYING && (uint8_t)sys_time != frame_t0)) {
            frame_wait();
            if ((HALF & HALF_ON) && game_state == GS_PLAYING && (uint8_t)((uint8_t)sys_time - frame_t0) > 1) HALF |= HALF_OWED;
        }
#ifdef FRAME_STATS
        frame_t0 = t0 = (uint8_t)sys_time; ly0 = LY_REG; st0 = game_state;
#else
        frame_t0 = (uint8_t)sys_time;
#endif
        SEC_BEGIN();
        update();
        vq_frame_end();      // the copy list is complete: the next VBlank interrupt executes it
#ifdef FRAME_STATS
        perf_snap(); lt = snap_t; lly = snap_ly;
#endif
        // Music and effects, every frame, after the logic (so they cannot delay the game's input-to-state latency).
        if (game_state != GS_PAUSED || !PAUSE_NR51 || NR51_REG) music_tick();   // (the pause menu: the bass and drums play on; NR51 0: a tune the game is clocked by stands still, pause.c)
        SEC(SEC_MUSIC);
#ifdef FRAME_STATS
        perf_snap();
#endif
#ifdef PERF_SECTIONS
        for (d = 0; d < SEC_N; d++) sec_done[d] = sec_frame[d];
        sec_done_id = frame_counter;
#endif
#ifdef FRAME_STATS
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
#endif
    }
}
