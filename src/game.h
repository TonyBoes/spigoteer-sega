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
// The left end (no door, owner 2026-10-09): the wall and the counter run to the screen's left edge. Left of ENTRY_X
// (columns 0-1) a patron is only ever a sprite (LIFT_EDGE, lift.c): a new one slides in from beyond x 0 (he spawns at
// SPAWN_X with patron_aux = PATRON_W px of him still off the screen, drawn patron_aux px left of patron_x; OAM X < 8
// clips him at the edge) and walks EMERGE_SPEED / 256 px a frame, 32 px in 64 frames, until ENTRY_X, then at the
// level's speed (the walk from ENTRY_X to the tap takes what it always did); one pushed back to ENTRY_X is served
// (PATRON_LEAVING) and slides out past the edge (PUSH_SPEED, patron_aux counting the px gone), then is removed.
// Columns 0-1 never show a BG patron in play (unless a forced drop puts an entering one fully on screen there).
#define ENTRY_X        16
#define SPAWN_X         0
#define EMERGE_SPEED  128

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
#define SPAWN_RETRY      20   // frames before trying again when the bar's left end is crowded
#define PATRON_TILE_BASE PATRON_FIRST_TILE   // M13a: BAR_TILE_COUNT rounded up to even (the shift-0 poses double as 8x16 OBJ tiles)
#define PATRON_OBJ_BASE  (PATRON_TILE_BASE + PATRON_SHIFT0_OFS)   // shift-0 pose of variant v: + v * 6, column-major (OBJ tiles t, t + 2)
#define PATRON_BLANK     (PATRON_OBJ_BASE + 4)   // its 3rd column: plain colour 0 (the wall), what a lifted patron leaves on the BG
#if PATRON_FIRST_TILE != ((BAR_TILE_COUNT + 1) & ~1) || PATRON_OBJ_BASE < 128 || (PATRON_OBJ_BASE & 1)
#error "patron tile layout (tools/gen_art.py): shift-0 poses must be even OBJ ids >= 128"
#endif
#define PATRON_BACK_BASE (PATRON_TILE_BASE + PATRON_TILES_PER_GROUP)   // the 12 back-view tiles follow the 144 shifted ones
#define DRAW_BACK        0x80 // patron_draw bit 7: drawn in its back view (x < 128, so the bit is free)
#define SHUFFLE_MAX         4 // a patron turning to watch the show shuffles at most this far to a multiple of 8 px
// BG tile budget (signed 0x8800 mode, LCDC bit 4 clear): ids 0..255. OBJ tiles stay below 128, so BG ids 128+
// (VRAM 0x8800-0x8FFF, which OBJ would see as 128+) are free for the patrons. M9: scene = venue pool 0-35 (stage from 0 up,
// bar + floor packed at the top) + shared HUD tiles 36-71 (72), patrons 72-215 + back views 216-227: 228 of 256.
#if PATRON_TILE_BASE + PATRON_GROUP_TILES > 256
#error "BG tile budget: scene + patron tiles exceed 256"
#endif
enum { PATRON_NONE, PATRON_WALKING, PATRON_PUSHED, PATRON_DRINKING, PATRON_LEAVING };   // LEAVING: served, sliding out
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
#define GLASS_X            0   // screen x of the glass breaking at the left end
#define GLASS_X_RIGHT    144   // ... and at the tap end
#define GLASS_FRAME_TIME   8   // frames per glass frame
enum { MUG_FREE, MUG_FULL, MUG_EMPTY, MUG_BREAKING, MUG_HELD };   // HELD: caught, in a patron's hand

#define HUD_LIVES         1
#define HUD_SCORE         2

// game flow
// GS_DEBUG: the debug level select (DEBUG_MENU builds). M10b: GS_LOOP the "LOOP n" banner before the first level of a
// loop, GS_INITIALS the initials entry after a game over that made the top 5, GS_SCORES the top-5 table (scores.c)
// M11b story mode: GS_STORY a cut-scene (or the TRY AGAIN banner), GS_GOAL the chapter's goal banner before play
enum { GS_TITLE, GS_PLAYING, GS_LIFE_LOST, GS_LEVEL_CLEAR, GS_GAME_OVER, GS_PAUSED, GS_BONUS, GS_DEBUG, GS_LOOP, GS_INITIALS, GS_SCORES,
       GS_STORY, GS_GOAL };

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
// OAM budget (40): bartender 0-3, fill 4, mugs 5..25 (20 mugs + 1 spare for a breaking glass's 2nd entry),
// 26 unused (was the door puff), tip coin 27, three dancers x 4 entries 28..39. M13a: lifted patrons (2 entries each) count down from 25,
// and the mugs then end at OAM_MUG_END - 2 * lift_total.
#define OAM_MUG_END    26
#define OAM_COIN       27
#define OAM_DANCERS    28

// CGB OBJ palette slots (M13a): the breaking glass uses the venue's empty-drink palette (2); the tip
// coin shares slot 5 with the show (never on screen together: render.c rewrites it in VBlank when one appears);
// lifted patrons use 3, 6, 7 (variants A, B, C; colours 1-3 of their BG palettes); M14a: 4 is the group's extra palette
// <group>_x for one lifted column of its enhanced variant (src/enhance.c).
#define OBJPAL_BARTENDER 0
#define OBJPAL_MUG_FULL  1
#define OBJPAL_MUG_EMPTY 2
#define OBJPAL_PATRON_A  3
#define OBJPAL_ENH       4   // (M14a; was OBJPAL_SPARE)
#define OBJPAL_COIN      5
#define OBJPAL_DANCER    5
#define OBJPAL_PATRON_B  6
#define OBJPAL_PATRON_C  7
// DMG (M13a): OBP1 = 0xE4 in play (lifted patrons, the BG's shades); what used OBP1 (0xC4) before draws with OBP0 (0xD0)
// from copies of its tiles with the two bit planes swapped (colours 1 and 2 trade places), made at level load
#define OBP1_PLAY        0xE4
#define OBP1_MENU        0xC4   // the title / bonus OBP1 (mugs, sparkles)
#define OBJ_DMG_COPY     240    // sliding full mug 240, sliding empty 242, held empty 244
// CGB BG palette slots (2..7 are free for patrons)
#define BGPAL_BAR        0
#define BGPAL_HUD        1
#define BGPAL_PATRON     2   // 2, 3, 4 = patron variants A, B, C
#define BGPAL_STAGE      5   // the venue's stage palettes A and B (M9)
#define BGPAL_STAGE_B    6
#define BGPAL_BAR_B      7   // the venue's second bar palette (keg / spout); M14a: also an enhanced variant's row palette S
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
extern uint8_t  bar, bartender_x, bartender_frac, facing, bartender_frame, bt_bob, fill_timer, fill_stage, is_cgb;
extern uint8_t  catch_pose;   // frames left of the bartender's catch pose (an empty caught, a glass taken)
extern uint8_t  lives, life_lost, game_state, hud_dirty, level_clear;
extern uint8_t  quota, spawned, served, serve_score, patron_speed, pushback_px, intro_timer;
extern uint8_t  start_mask, start_per_bar, empty_gap;
extern uint16_t next_arrival;
extern uint16_t spawn_interval, spawn_timer;
// Story shifts: an arrival pattern (patrons.c try_spawn). pat_len 0: the normal random bar every spawn_interval; else
// the next patron goes to bar pat_bar, and after each spawn the banked pat_done() (story.c) moves the pattern on and
// returns the frames to the next one. Set by story.c per shift, cleared by start_new_game (arcade).
extern uint8_t  pat_len, pat_bar;
uint16_t pat_done(void) BANKED;
extern uint8_t  tip_chance, tip_bar, tip_x, dancer_frame, dance_tick, dancers_vis, dancer_sig;
extern uint16_t tip_timer, show_timer;

extern uint8_t  patron_state[MAX_PATRONS], patron_bar[MAX_PATRONS], patron_x[MAX_PATRONS];
extern uint8_t  patron_frac[MAX_PATRONS], patron_draw[MAX_PATRONS], patron_variant[MAX_PATRONS];
extern uint8_t  patron_timer[MAX_PATRONS], patron_aux[MAX_PATRONS], patron_mug[MAX_PATRONS];
extern uint8_t  patron_catchx[MAX_PATRONS], patron_drinks[MAX_PATRONS], patron_dist[MAX_PATRONS], patron_facing[MAX_PATRONS], patrons_live;
extern uint8_t  mug_state[MAX_MUGS], mug_bar[MAX_MUGS], mug_x[MAX_MUGS], mug_timer[MAX_MUGS];
extern uint8_t  mug_patron[MAX_MUGS], mugs_live;
extern uint8_t  oam_used, mug_events;
// M13a lifted patrons (lift.c): patron_lift[p] LIFT_BG / LIFT_OBJ / LIFT_EDGE, | LIFT_DROP while the BG copy is being put
// back (the sprite stays until it is on screen); lift_n[b] patrons of bar b drawn as sprites, lift_total all of them.
#define LIFT_BG          0
#define LIFT_OBJ         1
#define LIFT_EDGE        2    // OBJ at the left end (entering / leaving): no BG footprint, drawn patron_aux px left, never dropped off screen
#define LIFT_DROP        0x80
#define LIFT_OFF_BG(v)   ((uint8_t)((v) - 1) < 2)   // lifted, not dropping: the BG shows plain wall in his footprint
#define LIFT_MAX         4
#define LIFT_PER_BAR     2
#define LINE_OBJ_MAX    10
extern uint8_t  patron_lift[MAX_PATRONS], lift_n[NUM_BARS], lift_total, lift_oam_n;
// M13b overlap rules (lift.c chooses who is lifted): patron_ovl[p] flags for BG patrons whose footprints meet: OVL_SHARED
// no quick redraws (render.c composes his span: a quick redraw would draw him over someone who covers him, or his empty
// 3rd column over someone's figure), OVL_TOP drawn after the other BG patrons (the budget-exhausted fallback: the one that
// would have been lifted covers the other), OVL_TWO at shift 0 only his 2 real columns are stamped (his empty 3rd column
// lies on another patron's figure). ovl_bars: bars with an OVL_TOP patron (render.c composes them in two passes).
// ovl_dirty: bars the chooser must look at (ovl_touch: a patron who meets someone changed columns) or that wait for a lift.
#define OVL_SHARED       1
#define OVL_TOP          2
#define OVL_TWO          4
#define LIFT_CLEAR_FRAMES 8   // a lifted patron drops after this many frames clear of every BG patron (hysteresis)
extern uint8_t  patron_ovl[MAX_PATRONS], ovl_bars, ovl_dirty;
// M13b speeds: patron_hurry[p] = 1: a hurried walker (hurry_speed, about 1.5x patron_speed; 0 = no hurried patrons this level)
extern uint8_t  patron_hurry[MAX_PATRONS], hurry_speed;
extern uint8_t  lift_hook_op, lift_hook_p, lift_hook_res;
extern uint8_t  spr_full_t, spr_full_p, spr_empty_t, spr_empty_p, spr_hempty_t, spr_hempty_p;

extern const uint8_t bar_bit[NUM_BARS];
extern const uint8_t bar_oam_y[NUM_BARS];     // OAM y (+16) of the bar's top pixel row

// ---- main.c --------------------------------------------------------------------------
uint8_t next_rand(void);
void add_score(uint16_t n);
void lose_life(void);
void prep_hud(void);                          // lives_tiles / score_tiles from lives and score_digits
void show_overlay(const char *s);             // the banner's text (ROM0: callers pass strings from their own bank)
void lcd_isr(void);                           // LYC handler: the banner window off below the banner
// ROM0 helpers: copy out of another ROM bank and come back to the caller's
void far_copy(void *dst, const void *src, uint16_t n, uint8_t bank);
void bkg_data_far(uint8_t first, uint8_t n, const uint8_t *d, uint8_t bank);
void spr_data_far(uint8_t first, uint8_t n, const uint8_t *d, uint8_t bank);
#define START_LIVES           3
#define MAX_LIVES             4     // story: a gold medal's bonus life (the HUD shows 4 mugs at columns 8-11)
#define LIFE_FREEZE_FRAMES  120     // the life-lost freeze (main.c)
#define BANNER_WY  BAR_TOP_Y(1)       // window overlay: 3 tile rows over bar 1 (y 64..87), clear of the HUD and stage
#define BANNER_LYC (BAR_TOP_Y(1) + 22)  // line where the LCD interrupt switches the window off again
void start_level(void) BANKED;                // src/level.c: the level table, the arcade loops' difficulty, the level load
// ---- main_cold.c (banked: boot, screen changes; nothing per frame) ----------------------------
void boot_init(void) BANKED;                  // hardware, palettes, sprites, the banner window, then the title
void draw_hud(void) BANKED;                   // the whole HUD row (VRAM: LCD off)
uint8_t glyph_for(char c) BANKED;             // HUD glyph tile of a character (blank if none)
void enter_level_screen(void) BANKED;         // LCD off: the level's screen, then PLAYING (or LOOP)
void start_new_game(uint8_t lv) BANKED;
void resume_after_life(void) BANKED;
void enter_game_over(void) BANKED;
void enter_level_clear(void) BANKED;

// ---- patrons.c --------------------------------------------------------------------------
extern uint8_t lists_ok;                      // 0: bar lists must be rebuilt before use (see patrons.c)
extern uint8_t lists_dirty;                   // set by the tests after poking patron_state / patron_bar
uint8_t add_patron(uint8_t b, uint8_t x, uint8_t variant);
void remove_patron(uint8_t p);
uint8_t catch_full(uint8_t i);                // mugs.c asks for every full mug
void begin_catch_frame(void);
extern uint8_t catch_lim[NUM_BARS];          // a full mug at x >= catch_lim[its bar] is caught by nobody (see patrons.c)
void start_show(void) BANKED;                  // (show.c, bank 5)
void end_show(void) BANKED;
void redraw_at(uint8_t p, uint8_t nd);        // p is now drawn at nd (| DRAW_BACK): marks the columns that change
void ovl_touch(uint8_t p) BANKED;             // (lift.c) p changed columns: wake the chooser if he meets anyone
uint8_t watch_step(uint8_t p) BANKED;         // (show.c) a distracted walker shuffles to his place and turns round
uint8_t col_scan(uint8_t b, uint8_t k, uint8_t p);   // M13b: patrons of bar b but p covering column k (cs_dist: a watcher among them)
extern uint8_t cs_dist;
void update_patrons(void);
void place_start_patrons(void) BANKED;
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
extern uint8_t vram_pending, vq_count, drain_ticks_max, vq_held;
extern uint8_t score_tiles[6], lives_tiles[4];   // lives_tiles: HUD columns 8-11 (8: the 4th life)
void vram_put(uint8_t x, uint8_t y, const uint8_t *src, uint8_t n);
void put_row(uint8_t y);
void mark_dirty(uint8_t b, uint8_t x0, uint8_t x1);         // tile ids of columns x0..x1-1 changed
extern uint8_t frame_t0;                                    // (main.c) the low byte of sys_time when the frame began
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
void oam_touched(void);                       // OAM entries were changed behind the drawing code: redraw cached ones
uint8_t bg_pending(uint8_t p);                // patron p's BG columns still wait to be queued
uint8_t bg_urgent(uint8_t b, uint8_t c);      // compose + queue columns c-1..c+3 of bar b first thing this frame (0: not now)
extern uint8_t pal5_cur;                      // CGB OBJ palette 5 holds: 1 the coin, 2 the show
extern uint16_t coin_pal[4];                  // (main.c) PAL_COIN, copied out of the banked palette table at boot
// ---- lift.c (banked, M13a lifted patrons) ------------------------------------------------------
void lift_level_init(uint8_t g) BANKED;       // level load (LCD off): OBJ palettes / DMG copies and looks, no one lifted
void lift_frame(void) BANKED;                 // after the rules, before queue_vram: drops, forced drops, the test hook
void draw_lifted(void) BANKED;                // OAM 25 down, after draw_mugs
uint8_t lift_spawn(uint8_t p) BANKED;         // lift a new patron at the left edge now (1), or not (0: no room)
uint8_t lift_leave(uint8_t p) BANKED;         // a served patron slides out as a sprite: 1 done, 2 done (wait for his BG copy to go), 0 no room
// ---- enhance.c (banked, M14a enhanced patron variants) ------------------------------------------
extern uint8_t pat_row[8], back_row[8];       // BG palette of variant v's top tile row [v] and bottom row [4 + v] (front / back view)
extern uint8_t lift_prop[8];                  // (lift.c) OAM attributes of variant v's lifted left column [v] and right column [4 + v]
void enhance_load(uint8_t g) BANKED;          // level load (LCD off), after lift_level_init: the tables, OBJ 4, the bank-1 lift tiles
// ---- venue.c (banked, M9 themed venues; LCD off) ----------------------------------------------
extern uint8_t venue_id;
void load_venue(uint8_t t) BANKED;                      // tiles, palettes, base_tile/base_attr of theme t
void draw_venue(void) BANKED;                           // stage, counter rows, floor, HUD attributes
// Stage animation (src/venue.c): a few stage tile ids get their pixels rewritten on a looped script, through the
// VBlank copy queue (render.c queue_stage). sa_hold (tests) freezes it; vq_reset() stops it (sa_on = 0).
#define SA_MAX_WAIT 3                                   // refused frames before the stage update goes first
extern uint8_t sa_on, sa_hold, sa_timer;                // running (level screen); frozen; frames to the next step
extern uint8_t sa_lo, sa_left, sa_wait;                 // pending update: animated tiles sa_lo.. (sa_left of them)
extern uint8_t *sa_frame;                               // the step's frame (WRAM)
extern uint16_t sa_vram;                                // VRAM address of the first animated tile
void stage_anim_start(void) BANKED;                     // level screen, LCD off, after load_venue / draw_venue
void stage_anim_step(void) BANKED;                      // sa_timer ran out: take the next script step
void venue_backdrop(uint8_t first, uint8_t counter_row) BANKED;   // plain venue wall + counter + floor (title, bonus)
// ---- title.c (banked, M10a title screen) -----------------------------------------------------
void title_enter(void) BANKED;                          // LCD off: draws the title and turns the LCD on
uint8_t title_update(uint8_t pressed) BANKED;           // one title frame; 1: ARCADE chosen, 2: idle, show the table
void title_music_toggle(void) BANKED;                   // music on/off and the MUSIC line
// ---- scores.c (banked, M10b initials entry and top-5 table) --------------------------------------
void scores_table(void) BANKED;                         // LCD off: the table screen (GS_SCORES)
void scores_after_game(void) BANKED;                    // after GAME OVER: initials (GS_INITIALS) or the table
uint8_t scores_update(uint8_t pressed) BANKED;          // one frame of either; 1: back to the title
// ---- story.c (banked, M11b story mode) -------------------------------------------------------------
extern uint8_t story_on;                                // 1: story mode
void story_begin(uint8_t cont) BANKED;                  // from the title: STORY (0) or CONTINUE (1); LCD off
uint8_t story_update(uint8_t pressed) BANKED;           // a GS_STORY / GS_GOAL frame; 1: the screen changed
void story_play(void) BANKED;                           // every GS_PLAYING frame in story mode: the chapter goal
void story_level_done(void) BANKED;                     // GS_LEVEL_CLEAR is over: save, the POST scene
void story_fail(void) BANKED;                           // the goal failed: TRY AGAIN, then the shift / the venue again
void story_life_frame(void) BANKED;                     // every GS_LIFE_LOST frame in story mode: the 2-lives cue
void story_bonus_life(void) BANKED;                     // +1 life (max MAX_LIVES): a gold medal in the mini-game
#endif
