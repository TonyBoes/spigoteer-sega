// Shared declarations for the gameplay modules:
//   main.c     game flow, screens, HUD and score, input, the frame loop and its timing counters
//   patrons.c  the patron pool and its rules (walk, catch, push back, drink, serve), spawning, the show
//   mugs.c     the mug pool and its rules (slide, catch an empty, break), the mug / fill sprites
//   render.c   the BG side: wall-row shadow, dirty spans, VBlank copy queue; bartender and stage sprites
//
// Everything a test reads is a plain global with the name it always had (build/game.noi). The patron and mug
// pools stay structure-of-arrays (patron_x[16], mug_state[20], ...) because the tests read and poke them by
// name and index; the hot loops reach them through pointers and per-bar lists instead of indexing them all.
#ifndef GAME_H
#define GAME_H
#include <gb/gb.h>
#include <stdint.h>
#include "art.h"
#include "layout.h"

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

// mugs
#define MAX_MUGS          20   // pool size: the OAM budget (was 24 before the M5 dancers); the per-bar cap below is unchanged
#define MUGS_PER_BAR       6
#define MUG_START_X      136   // just left of the bartender at the tap
#define MUG_END_X         16   // a mug past x < 16 has left the counter
#define MUG_SPEED_FULL     2
#define MUG_SPEED_EMPTY    1
#define MUG_RIGHT_END    152   // an empty mug past this x has left the counter
#define EMPTY_SCORE      100
#define FILL_FRAMES       24
#define SLIDE_FRAMES       8
#define GLASS_X            0   // screen x of the glass breaking at the door end
#define GLASS_X_RIGHT    144   // ... and at the tap end
#define GLASS_FRAME_TIME   8   // frames per glass frame
enum { MUG_FREE, MUG_FULL, MUG_EMPTY, MUG_BREAKING, MUG_HELD };   // HELD: caught, in a patron's hand

#define HUD_LIVES         1
#define HUD_SCORE         2

// game flow
enum { GS_TITLE, GS_PLAYING, GS_LIFE_LOST, GS_LEVEL_CLEAR, GS_GAME_OVER, GS_PAUSED, GS_BONUS };

// bartender animation frames (order of assets/art/bartender.txt)
enum { BT_IDLE, BT_WALK1, BT_WALK2, BT_FILL, BT_SLIDE, BT_CATCH, BT_FAIL };

// OBJ tile layout in VRAM
#define OBJ_BARTENDER   0
#define OBJ_MUG         (BARTENDER_FRAMES * BARTENDER_TILES_PER_FRAME)
#define OBJ_GLASS       (OBJ_MUG + MUG_TILE_COUNT)
#define OBJ_MUG_FILL    (OBJ_GLASS + GLASS_TILE_COUNT)
#define OBJ_MUG_DRINK   (OBJ_MUG_FILL + MUG_FILL_TILE_COUNT)
#define OBJ_COIN        (OBJ_MUG_DRINK + MUG_DRINK_TILE_COUNT)
#define OBJ_DANCER      (OBJ_COIN + COIN_TILE_COUNT)
// OBJ tile ids stay below 128: ids 128+ share VRAM (0x8800 block) with the patron BG tiles
#define OAM_FILL        4     // OAM entry of the filling mug; pooled mugs start at 5
// OAM budget (40): bartender 0-3, fill 4, mugs 5..26 (20 mugs + 2 spare for a breaking glass's 2nd entry),
// tip coin 27, three dancers x 4 entries 28..39
#define OAM_MUG_END    27
#define OAM_COIN       27
#define OAM_DANCERS    28

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

// ---- state (globals => symbols the tests read) ----------------------------------
extern uint8_t  bar, bartender_x, facing, bartender_frame, fill_timer, fill_stage, is_cgb;
extern uint8_t  lives, life_lost, game_state, hud_dirty, level_clear;
extern uint8_t  quota, spawned, served, serve_score, patron_speed, pushback_px, intro_timer;
extern uint8_t  start_mask, start_per_bar;
extern uint16_t spawn_interval, spawn_timer;
extern uint8_t  tip_chance, tip_bar, tip_x, dancer_frame, dance_tick, dancers_vis, dancer_sig;
extern uint16_t tip_timer, show_timer;

extern uint8_t  patron_state[MAX_PATRONS], patron_bar[MAX_PATRONS], patron_x[MAX_PATRONS];
extern uint8_t  patron_frac[MAX_PATRONS], patron_draw[MAX_PATRONS], patron_variant[MAX_PATRONS];
extern uint8_t  patron_timer[MAX_PATRONS], patron_aux[MAX_PATRONS], patron_mug[MAX_PATRONS];
extern uint8_t  patron_catchx[MAX_PATRONS], patron_dist[MAX_PATRONS], patrons_live;
extern uint8_t  mug_state[MAX_MUGS], mug_bar[MAX_MUGS], mug_x[MAX_MUGS], mug_timer[MAX_MUGS];
extern uint8_t  mug_patron[MAX_MUGS], mugs_live;
extern uint8_t  oam_used;

extern const uint8_t bar_bit[NUM_BARS];
extern const uint8_t bar_oam_y[NUM_BARS];     // OAM y (+16) of the bar's top pixel row

// ---- main.c --------------------------------------------------------------------------
uint8_t next_rand(void);
void add_score(uint16_t n);
void lose_life(void);

// ---- patrons.c --------------------------------------------------------------------------
extern uint8_t lists_ok;                      // 0: bar lists must be rebuilt before use (see patrons.c)
uint8_t add_patron(uint8_t b, uint8_t x, uint8_t variant);
void remove_patron(uint8_t p);
uint8_t catch_full(uint8_t i);                // mugs.c asks for every full mug
void begin_catch_frame(void);
extern uint8_t catch_lim[NUM_BARS];          // a full mug at x >= catch_lim[its bar] is caught by nobody (see patrons.c)
void start_show(void);
void end_show(void);
void update_patrons(void);
void place_start_patrons(void);
void clear_patrons(void);

// ---- mugs.c ------------------------------------------------------------------------------
uint8_t spawn_mug(uint8_t b, uint8_t x, uint8_t state);
void launch_mug(void);
void update_mugs(void);
void update_glass(void);
void draw_mugs(void);
void draw_fill(void);
void clear_mugs(void);

// ---- render.c ------------------------------------------------------------------------------
extern uint8_t row_buf[20];
extern uint8_t vram_pending, vq_count, drain_ticks_max;
extern uint8_t score_tiles[6], lives_tiles[3];
void vram_put(uint8_t x, uint8_t y, const uint8_t *src, uint8_t n);
void put_row(uint8_t y);
void mark_dirty(uint8_t b, uint8_t x0, uint8_t x1);         // tile ids of columns x0..x1-1 changed
void mark_dirty_attrs(uint8_t b, uint8_t x0, uint8_t x1);   // ... and their CGB attributes too
void clear_dirty(void);
void write_all_bars(void);
void vq_add(uint8_t bank, const uint8_t *src, uint8_t x, uint8_t y, uint8_t n);
void vq_vbl(void);
void vq_frame_begin(void);
void vq_frame_end(void);
void vq_reset(void);
void queue_vram(void);
void draw_bartender(void);
void draw_stage_fx(void);
void hide_all_sprites(void);
void oam_touched(void);                       // OAM entries were changed behind the drawing code: redraw cached ones
#endif
