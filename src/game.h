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
// The keg stands on columns 18-19; its spout reaches left over column 17 (SPOUT_X), where the mug is filled.
// TAP_X is the fill position: the bartender (16 px) stands just left of the spout (columns 15-16), the right end
// of his walk. He faces right (the tap) while filling and turns left when he slides the mug.
#define SPOUT_X       136   // screen x of the spout's column (17): the fill mug's x, and where a launched mug starts
#define TAP_X         120   // bartender_x at the fill position (SPOUT_X - 16)
#define TAP_GRACE      32   // A pressed within this many px left of the fill position snaps to it and fills
#define LEFT_LIMIT     16   // column 2
#define WALK_PX         1   // walking speed 1.5 px per frame: 1 px + WALK_FRAC/256 px
#define WALK_FRAC     128
#define WALK_STEP_FRAMES 10 // frames per step of the walk cycle walk1, idle, walk2, idle
#define NUM_BARS        4
// The door: columns 0-1 (16 px) of every bar's two wall rows. Patrons come in at DOOR_X, just right of it, and
// are served out (pushed back) when they would go left of it, so their 3-tile footprint never covers the door.
#define DOOR_X         16

// patrons: 16x16 px, drawn as a 3x2-tile BG footprint on the two back-wall rows of a bar.
// Position is in pixels (patron_x, left edge of the 16 px figure) plus a fraction; the picture
// is pre-shifted by 0..7 px in the tile set (M8b), so it moves in 1 px steps by swapping map entries.
// A patron watching the show stands on a multiple of 8 px and shows its back view (2x2 tiles, no shifts).
#define MAX_PATRONS      16
#define PATRON_SPACING   32   // min px between the left edges of two patrons on a bar (no shared tile column)
#define PATRON_FAR_X    120   // a walker whose patron_x gets here has reached the bartender's end (right edge at the spout)
#define PATRON_W         16
#define PUSH_SPEED        1   // px per frame while pushed back
#define DRINK_FRAMES     90
#define SWAY_FRAMES      12   // while drinking the drawn shift alternates by 2 px this often
// M8d: a drinker who has finished (DRINK_FRAMES) but may not send its empty yet (fair empties) sips on: its timer
// loops SIP_LOOP_T..DRINK_FRAMES-1. When the empty may go it winds up (lowers the mug, draws it back, swings it forward) for
// WINDUP_FRAMES, timer WINDUP_T0.., then the empty slides. Sub-state in patron_aux while DRINKING (DRINK_*).
// A finished drinker (waiting or winding up) catches a full mug, and the bartender standing on him takes the glass.
#define SIP_LOOP_T       24
#define WINDUP_FRAMES    30
#define WINDUP_T0        96   // a multiple of 4 above DRINK_FRAMES: the mug poses 24..31 in mugs.c
#define NO_SLOT         255
#define INTRO_FRAMES     90   // nothing moves or spawns for this long after a level starts
#define SPAWN_RETRY      20   // frames before trying again when the door is crowded
#define PATRON_TILE_BASE BAR_TILE_COUNT
#define PATRON_BACK_BASE (PATRON_TILE_BASE + PATRON_TILES_PER_GROUP)   // the 12 back-view tiles follow the 144 shifted ones
#define DRAW_BACK        0x80 // patron_draw bit 7: drawn in its back view (x < 128, so the bit is free)
#define SHUFFLE_MAX         4 // a patron turning to watch the show shuffles at most this far to a multiple of 8 px
// BG tile budget (signed 0x8800 mode, LCDC bit 4 clear): ids 0..255. OBJ tiles stay below 128, so BG ids 128+
// (VRAM 0x8800-0x8FFF, which OBJ would see as 128+) are free for the patrons. M9: scene = venue stage slot 0-19 + venue bar
// slot 20-35 + shared HUD tiles 36-71 (72), patrons 72-215 + back views 216-227: 228 of 256.
#if PATRON_TILE_BASE + PATRON_GROUP_TILES > 256
#error "BG tile budget: scene + patron tiles exceed 256"
#endif
enum { PATRON_NONE, PATRON_WALKING, PATRON_PUSHED, PATRON_DRINKING };
enum { DRINK_MIN, DRINK_WAIT, DRINK_WINDUP };   // patron_aux while PATRON_DRINKING

// mugs
#define MAX_MUGS          20   // pool size: the OAM budget (was 24 before the M5 dancers); the per-bar cap below is unchanged
#define MUGS_PER_BAR       6
#define MUG_START_X  SPOUT_X   // a launched mug starts under the spout
#define MUG_END_X         16   // a mug past x < 16 has left the counter
#define MUG_SPEED_FULL     2
#define EMPTY_STEP_FRAMES  2   // an empty slides 1 px every 2nd frame of its own (0.5 px per frame); fixed in mugs.c
#define MUG_RIGHT_END    152   // an empty mug past this x has left the counter
#define EMPTY_SCORE      100
#define CATCH_POSE_FRAMES  8   // the bartender shows BT_CATCH this long after catching an empty / taking a glass
#define FILL_FRAMES       16
#define SLIDE_FRAMES       8
#define GLASS_X            0   // screen x of the glass breaking at the door end
#define GLASS_X_RIGHT    144   // ... and at the tap end
#define GLASS_FRAME_TIME   8   // frames per glass frame
enum { MUG_FREE, MUG_FULL, MUG_EMPTY, MUG_BREAKING, MUG_HELD };   // HELD: caught, in a patron's hand

#define HUD_LIVES         1
#define HUD_SCORE         2

// game flow
enum { GS_TITLE, GS_PLAYING, GS_LIFE_LOST, GS_LEVEL_CLEAR, GS_GAME_OVER, GS_PAUSED, GS_BONUS, GS_DEBUG };   // GS_DEBUG: the debug level select (DEBUG_MENU builds)

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
#if OBJ_DANCER + DANCER_FRAMES * DANCER_TILES_PER_FRAME > 128
#error "OBJ tiles must stay below 128: ids 128+ share VRAM with the patron BG tiles"
#endif
// OBJ tile ids stay below 128: ids 128+ share VRAM (0x8800 block) with the patron BG tiles
#define OAM_FILL        4     // OAM entry of the filling mug; pooled mugs start at 5
// Door puff: one 8x16 entry at the doorway of the bar where a patron just came in or was served out. Its 3 frames
// of 8x16 live at OBJ ids after the patron BG tile range (OBJ ids 228+ overlap no BG tile id).
#define PUFF_TOTAL     12     // frames the puff lasts (3 frames of 4)
#define PUFF_X          4     // screen x of the puff (the door is 16 px wide)
#define OBJ_PUFF       ((PATRON_TILE_BASE + PATRON_GROUP_TILES + 1) & ~1)
#if OBJ_PUFF + PUFF_FRAMES * 2 > 256
#error "OBJ tile budget: the puff tiles do not fit above the patron BG tiles"
#endif
// OAM budget (40): bartender 0-3, fill 4, mugs 5..25 (20 mugs + 1 spare for a breaking glass's 2nd entry),
// door puff 26, tip coin 27, three dancers x 4 entries 28..39
#define OAM_MUG_END    26
#define OAM_PUFF       26
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
#define BGPAL_STAGE      5   // the venue's stage palettes A and B (M9)
#define BGPAL_STAGE_B    6
#define BGPAL_BAR_B      7   // the venue's second bar palette (keg / spout)
#if BGPAL_STAGE != VENUE_BGPAL_STAGE_A || BGPAL_STAGE_B != VENUE_BGPAL_STAGE_B || BGPAL_BAR != VENUE_BGPAL_BAR || BGPAL_BAR_B != VENUE_BGPAL_BAR_B
#error "tools/gen_art.py PAL_* must match the BGPAL_* slots"
#endif

// tips and the stage show
#define TIP_FRAMES       480   // a tip stays this long (8 s)
#define TIP_BLINK         60   // ... and blinks for the last second
#define TIP_SCORE       1500
#define TIP_CHANCE_DEFAULT 64  // out of 256 per served patron (255 = always, 0 = never)
#define SHOW_FRAMES      704
#define DANCER_BEAT       12   // frames per dance step
#define DANCER_STAGGER     8   // dancers pop in / out one after the other
#define SHOW_SPAWN_DIV     4   // after a show the next patron comes after spawn_interval / this (once)
#define NUM_DANCERS        3

// ---- state (globals => symbols the tests read) ----------------------------------
extern uint8_t  bar, bartender_x, bartender_frac, facing, bartender_frame, fill_timer, fill_stage, is_cgb;
extern uint8_t  catch_pose;   // frames left of the bartender's catch pose (an empty caught, a glass taken)
extern uint8_t  lives, life_lost, game_state, hud_dirty, level_clear;
extern uint8_t  quota, spawned, served, serve_score, patron_speed, pushback_px, intro_timer;
extern uint8_t  start_mask, start_per_bar, empty_gap;
extern uint16_t next_arrival;
extern uint16_t spawn_interval, spawn_timer;
extern uint8_t  puff_bar, puff_timer;   // door puff: its bar and frames left (0: none)
extern uint8_t  tip_chance, tip_bar, tip_x, dancer_frame, dance_tick, dancers_vis, dancer_sig;
extern uint16_t tip_timer, show_timer;

extern uint8_t  patron_state[MAX_PATRONS], patron_bar[MAX_PATRONS], patron_x[MAX_PATRONS];
extern uint8_t  patron_frac[MAX_PATRONS], patron_draw[MAX_PATRONS], patron_variant[MAX_PATRONS];
extern uint8_t  patron_timer[MAX_PATRONS], patron_aux[MAX_PATRONS], patron_mug[MAX_PATRONS];
extern uint8_t  patron_catchx[MAX_PATRONS], patron_drinks[MAX_PATRONS], patron_dist[MAX_PATRONS], patron_facing[MAX_PATRONS], patrons_live;
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
extern uint8_t lists_dirty;                   // set by the tests after poking patron_state / patron_bar
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
void mark_quick(uint8_t p);                                 // patron p moved within his own 3 columns (tile ids only)
void clear_dirty(void);
void write_all_bars(void);
void vq_add(uint8_t bank, const uint8_t *src, uint8_t x, uint8_t y, uint8_t n);
void vq_vbl(void);
void vq_frame_begin(void);
void vq_frame_end(void);
void vq_reset(void);
void queue_vram(void);
extern uint8_t base_tile[2][20], base_attr[2][20];   // the bar's two wall rows without patrons (current venue)
void draw_bartender(void);
void draw_stage_fx(void);
void hide_all_sprites(void);
void door_puff(uint8_t b);                    // a patron came in / left on bar b: start the dust puff at its door
void oam_touched(void);                       // OAM entries were changed behind the drawing code: redraw cached ones
// ---- venue.c (banked, M9 themed venues; LCD off) ----------------------------------------------
extern uint8_t venue_id;
void load_venue(uint8_t t) BANKED;                      // tiles, palettes, base_tile/base_attr of theme t
void draw_venue(void) BANKED;                           // stage, counter rows, floor, HUD attributes
void venue_backdrop(uint8_t first, uint8_t counter_row) BANKED;   // plain venue wall + counter + floor (title, bonus)
// ---- title.c (banked, M10a title screen) -----------------------------------------------------
void title_enter(void) BANKED;                          // LCD off: draws the title and turns the LCD on
uint8_t title_update(uint8_t pressed) BANKED;           // one title frame; 1: ARCADE chosen
void title_music_toggle(void) BANKED;                   // music on/off and the MUSIC line
#endif
