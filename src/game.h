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
#include "mpump.h"
#include <stdint.h>
#include "art.h"
#include "layout.h"

// Per-section frame cost in DIV ticks (256 cycles), only in a measurement build (-DPERF_SECTIONS): SEC(i) adds the ticks since the
// last marker to section i (src/main.c stores them; tests/perf harness reads sec_done). SEC_P1..P9 are free probes for a
// profiling session (the macros are empty in the normal build).
enum { SEC_FLUSH, SEC_INPUT, SEC_MUGS, SEC_PATRONS, SEC_COMPOSE, SEC_QUEUE, SEC_DRAW_BT, SEC_DRAW_MUGS, SEC_FX, SEC_REST, SEC_MUSIC,
       SEC_LIFT, SEC_ANIM, SEC_DLIFT, SEC_P1, SEC_P2, SEC_P3, SEC_P4, SEC_P5, SEC_P6, SEC_P7, SEC_P8, SEC_P9, SEC_P10, SEC_P11, SEC_P12, SEC_N };
#ifdef PERF_SECTIONS
extern uint8_t sec_frame[SEC_N], sec_t;
#define SEC_BEGIN() do { uint8_t _k; for (_k = 0; _k < SEC_N; _k++) sec_frame[_k] = 0; sec_t = DIV_REG; } while (0)
void sec_mark(uint8_t i);
#define SEC(i) sec_mark(i)
#else
#define SEC_BEGIN()
#define SEC(i)
#endif

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
#define WALK_X          8   // where an entering patron slows to the level's walking pace (the old door, x 0-16; owner 2026-10-13)
// Push rules (owner 2026-10-13): every mug pushes a patron pushback_px, the same for the 1st, 2nd, 3rd (level.c: PUSH_COLS_*
// per row class); he is served only when it carries all of him off the screen. EARLY_*: the chance (of 256) that a
// patron slides only a quarter or a half of it and drinks at once, (level - 1) * EARLY_PER_LEVEL, none on level 1, at most EARLY_MAX.
#define EARLY_PER_LEVEL 6
#define EARLY_MAX     110
// An empty bar: the next patron is due in REFILL_FRAMES (not after a pattern's breather, pat_breather).
#define REFILL_FRAMES  30

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
// Perfect pour (story mode only, src/pour.c): pour_t counts the fill frames on past FILL_FRAMES (fill_timer itself
// stops there, as in arcade). FILL_FRAMES..POUR_WIN_START-1: full, settling (the plain full drink; a release is
// ordinary). POUR_WIN_START..+pour_win-1: the sparkle window, a release launches a PERFECT drink (pour_q -> mug_timer
// of the full mug, otherwise unused while it slides). After it the foam runs over (ordinary). pour_win is WRAM, set to
// POUR_WIN_LEN at every shift start; Practice's HARD toggle sets POUR_WIN_HARD after that (the window's start stays).
#define POUR_WIN_START    27
#define POUR_WIN_LEN       5
#define POUR_WIN_HARD      3
#define SLIDE_FRAMES       8
#define GLASS_X            0   // screen x of the glass breaking at the left end
#define GLASS_X_RIGHT    144   // ... and at the tap end
#define GLASS_FRAME_TIME   8   // frames per glass frame
enum { MUG_FREE, MUG_FULL, MUG_EMPTY, MUG_BREAKING, MUG_HELD };   // HELD: caught, in a patron's hand

#define HUD_LIVES         1
#define HUD_SCORE         2

// game flow
// GS_DEBUG: the debug menu (src/debug.c). M10b: GS_LOOP the "LOOP n" banner before the first level of a
// loop, GS_INITIALS the initials entry after a game over that made the top 5, GS_SCORES the top-5 table (scores.c)
// M11b story mode: GS_STORY a cut-scene (or the TRY AGAIN banner), GS_GOAL the chapter's goal banner before play
enum { GS_TITLE, GS_PLAYING, GS_LIFE_LOST, GS_LEVEL_CLEAR, GS_GAME_OVER, GS_PAUSED, GS_BONUS, GS_DEBUG, GS_LOOP, GS_INITIALS, GS_SCORES,
       GS_STORY, GS_GOAL, GS_MINI,
       GS_JUKEBOX,                                      // the title's BONUS: the soundtrack player (src/jukebox.c)
       GS_MGLIST };                                     // BONUS > MINI GAMES: the list (src/mg_list.c)

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
#if OBJ_DANCER + DANCER_TILE_COUNT > 128
#error "OBJ tiles must stay below 128: ids 128+ share VRAM with the patron BG tiles"
#endif
// OBJ tile ids stay below 128: ids 128+ share VRAM (0x8800 block) with the patron BG tiles
#define OAM_FILL        4     // OAM entry of the filling mug; pooled mugs start at 5
// OAM budget (40): bartender 0-3, fill 4, mugs 5..25 (20 mugs + 1 spare for a breaking glass's 2nd entry),
// 26 unused (was the door puff), tip coin 27, three dancers x 4 entries 28..39. M13a: lifted patrons (2 entries each) count down from 25,
// and the mugs then end at OAM_MUG_END - 2 * lift_total.
#define OAM_MUG_END    26
#define OAM_CUE        26     // story: the PERFECT cue at a catch (src/pour.c; was the door puff's, unused since)
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
// the bar-change dust puff, 3 frames x 2 tiles (assets/art/dust.txt, tools/gen_pour.py), in ids other things also borrow, never
// at the same time: CLASSIC's DMG flipped copies take 246..251, 77, 252..255 (11 at most; mirror.c free_ids), the story's
// perfect pour 234..239 and neither does the other's work. So the puff sits at 234 (CLASSIC, the harness) or 246 (story, ARCADE).
#define OBJ_DUST         (story_on ? 246 : 234)
#define KEEP_POS         0x80   // level_dirs bit 7: mode A, the bartender keeps his x on a bar change (debug box, START);
                                // clear (the default, and always in CLASSIC): mode B, he snaps to the tap with a dust puff
#define OBJ_DMG_COPY     240    // sliding full mug 240, sliding empty 242, held empty 244
// Perfect pour (story): sparkle 234-235, overflow 236-237 (the venue's), the cue 238-239 (tools/gen_pour.py,
// src/pour.c pour_load at a shift's start). OBJ ids >= 128 share VRAM with BG ids >= 128: these sit above the patron
// tiles (PATRON_FIRST_TILE .. + PATRON_GROUP_TILES - 1) and below the DMG copies (240-245); 246-255 are mirror.c's flipped copies (and, in a story, the dust puff).
#define OBJ_POUR         234
#define OBJ_POUR_CUE     (OBJ_POUR + 4)
#define POUR_CUE_TILES    2
#if PATRON_FIRST_TILE + PATRON_GROUP_TILES > OBJ_POUR || OBJ_POUR_CUE + POUR_CUE_TILES > OBJ_DMG_COPY
#error "perfect pour OBJ tiles 234-239 overlap the patron tiles or the DMG copies"
#endif
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
void     served_done(uint8_t p);      // patrons.c: a patron served out is gone: score, count, tip (lift.c force_out too)
uint8_t  push_for(uint8_t p) BANKED;   // level.c: the push a mug gives patron p (served, early drinker, stopped on screen)
uint8_t  pat_breather(void) BANKED;   // the pattern's last wait was a breather (code 3)
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
void prep_hud(void);                          // lives_tiles (head, digit) / score_tiles from lives and score_digits
#define NOTE_WY    ((STAGE_FIRST_ROW + 2) * 8)  // a note (show_note): the window is ONE row, over the stage's wall under the sign (y 24..30), where nothing plays
#define NOTE_LYC   (NOTE_WY + 7)               // (the glyphs are 7 lines tall: the 8th is blank, so the window may end a line early)
void show_note(const char *s);                // a one-row message on the stage wall while play goes on (never over a bar); end_note takes it away
void end_note(void);                          // (no-op unless a note shows) the banner window's rows, WY and LYC as the banner wants them
void show_overlay(const char *s);             // the banner's text (ROM0: callers pass strings from their own bank)
uint8_t *mg_say(uint8_t row, const char *s);  // a centred line of HUD glyphs on map row `row` (queued; LCD off: written)
extern uint8_t say_bang;                      // (main_cold.c glyph_for) the tile drawn for '!' (bonus2's own, else blank)
void lcd_isr(void);                           // LYC handler: the banner window off below the banner
// ROM0 helpers: copy out of another ROM bank and come back to the caller's
void far_copy(void *dst, const void *src, uint16_t n, uint8_t bank);
void bkg_data_far(uint8_t first, uint8_t n, const uint8_t *d, uint8_t bank);
void spr_data_far(uint8_t first, uint8_t n, const uint8_t *d, uint8_t bank);
#define START_LIVES           3
#define MAX_LIVES             4     // a gold medal's bonus life, an extra life (the HUD shows the head and the digit at columns 7-8)
#define EXTRA_FIRST       20000UL   // ARCADE / CLASSIC: the first extra life at this score (add_score) ...
#define EXTRA_EVERY       40000UL   // ... then one every this many points
extern uint32_t extra_at;           // (main.c) the next extra life's score; 0: none in this mode (story, the harness)
#define LIFE_FREEZE_FRAMES  120     // the life-lost freeze (main.c)
#define BANNER_WY  BAR_TOP_Y(1)       // window overlay: 3 tile rows over bar 1 (y 64..87), clear of the HUD and stage
#define BANNER_LYC (BAR_TOP_Y(1) + 22)  // line where the LCD interrupt switches the window off again
void start_level(void) BANKED;                // src/level.c: the level table, the arcade loops' difficulty, the level load
// ---- main_cold.c (banked: boot, screen changes; nothing per frame) ----------------------------
void boot_init(void) BANKED;                  // hardware, palettes, sprites, the banner window, then the title
void draw_hud(void) BANKED;                   // the whole HUD row (VRAM: LCD off)
// HUD row 0 (owner 2026-10-14): score 0-5, the Spigoteer's head + the lives digit 7-8, a story goal's icon + 2 digits 11-13,
// the boss's face 12 + meter 13-19, the level's flag + 2 digits 17-19 (a timed shift / mini-game: hourglass + seconds 17-19).
// The head and the flag are generic tiles (TILE_HUD_HEAD, TILE_HUD_FLAG). The timer's hourglass and a goal's icon are BG
// tiles of a shift without a boss (a boss's HUD takes 252-255). hud_icon_load: tile k of hud_icon_tiles (HUD_ICON_*,
// art.h) to BG id `id` (LCD off)
#define HUD_HOURGLASS_BG  252
#define HUD_GOAL_BG       253
#define HUD_CURSOR_BG      77   // the initials screen's cursor (scores.c): the pad id no screen of its own uses
void hud_icon_load(uint8_t id, uint8_t k) BANKED;
extern const uint8_t glyph_az[26];                    // (ROM0, main.c) the letters' HUD tiles
// A letter or digit's HUD tile without glyph_for's banked call (~800 cycles a character; the full-screen menus rebuild rows of them);
// anything else: `slow`.
#define GLYPH_FAST(c, slow) ((uint8_t)((c) - 'A') < 26 ? glyph_az[(uint8_t)((c) - 'A')] : (uint8_t)((c) - '0') < 10 ? TILE_GLYPH_0 + (uint8_t)((c) - '0') : (slow))
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

// ---- perfect pour (story; src/pour.c, banked; ROM0 hooks: spawn_mug, caught, the draw block) ----------
extern uint8_t pour_q, pour_t, pour_win, cue_t;
void pour_load(uint8_t t) BANKED;             // LCD off: venue t's sparkle / overflow frames and the cue to OBJ_POUR..
void dust_load(void) BANKED;                  // LCD off (every level screen): the dust puff's 3 frames to OBJ_DUST..
void bar_change(uint8_t pressed) BANKED;      // main.c, Up/Down was pressed (bar is the new one; tap_now = the new bar's tap): where he lands, facing the bar
                                              // (mode A keeps his x; mode B, and CLASSIC always, snaps to the tap with a swish and the puff)
void perfect_catch(uint8_t i) BANKED;         // patrons.c caught(), story: full mug i caught (perfect if mug_timer 1)
void pour_frame(void) BANKED;                 // story, every drawn play frame after the sprites: window, fill frame, cue

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
extern uint8_t vram_pending, vq_count, drain_ticks_max, vq_held, qv_cost;   // (qv_cost: the copy list's tally, see vq_frame_end)
extern uint8_t score_tiles[6], lives_tiles[2];   // score: HUD columns 0-5; lives_tiles: the head and one digit, columns 7-8
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
// The most a VBlank drain takes (bytes + 3 an entry, ~40 cycles each: ~6.3 lines, so that even a drain starting on VQ_LATEST_LY ends on line 153).
#define VQ_DRAIN_BUDGET 86
#define VQ_SPLIT        254      // qv_cost's value for a list that was split (vq_split): its tail is still in the list
void vq_split(void) BANKED;      // src/vq_split.c: the entries of a list that go out this VBlank (vq_ready), the rest wait
void vq_restore(void) BANKED;    // ... and the rest, moved to the head of the next frame's list
void vq_reset(void);
void queue_vram(void);
// P6 slanted bars (CLASSIC, the trapezoid levels): bar b's tap end lies (3 - b) * taper tile columns in from the screen
// edge (taper 0: straight; mirror.c mirror_load takes it in bits 4-5 of its dirs, at most TAPER_MAX); the patrons' end
// stays at the screen edge, the wall beyond the keg is plain wall. Every rule that used TAP_X / SPOUT_X / MUG_RIGHT_END /
// GLASS_X_RIGHT / PATRON_FAR_X uses the bar's own bar_tap[b] (bar-local x as ever; an R bar is still only drawn mirrored).
// The base rows are BASE_W wide: the venue's 20 columns + 3 * TAPER_MAX of plain wall; a bar shows the 20-column window
// from bar_bofs[b] (an L bar shifted k columns: from k; an R bar: its mirrored rows from 3 * TAPER_MAX - k).
#define TAPER_MAX 1
#define BASE_W    (20 + 3 * TAPER_MAX)
extern uint8_t bar_tap[NUM_BARS];              // (mirror.c) bartender_x at bar b's fill position (TAP_X on a straight bar)
extern uint8_t tap_now;                        // (main.c) bar_tap[bar], set at the start of every play frame
extern uint8_t bar_bofs[NUM_BARS];             // (mirror.c) bar b's window into base_all (and ctr_all, see venue.c)
#define BAR_SPOUT(b)    ((uint8_t)(bar_tap[b] + (SPOUT_X - TAP_X)))          // its spout: the fill glass, a launched mug
#define BAR_MUG_END(b)  ((uint8_t)(bar_tap[b] + (MUG_RIGHT_END - TAP_X)))    // an empty past it has left the counter
#define BAR_GLASS_X(b)  ((uint8_t)(bar_tap[b] + (GLASS_X_RIGHT - TAP_X)))    // the glass breaking at the tap end
extern uint8_t base_all[4][2][BASE_W];         // the bar's two wall rows without patrons (current venue): tiles, CGB
#define base_tile  (base_all[0])               // attributes, then an R bar's (P3, screen order; restore_base relies on
#define base_attr  (base_all[1])               // this layout)
#define base_rtile (base_all[2])
#define base_rattr (base_all[3])
extern uint8_t sh_rows[2][NUM_BARS * 2][32];   // (render.c) the bars' wall rows as on screen: tile ids, CGB attributes
uint8_t quick_mirror(uint8_t p, uint8_t d) BANKED;   // (mirror.c) R bar: patron p's quick redraw at d into sh_rows; his screen column
// P3/P4 (CLASSIC): bars whose patrons come from the right. bar_dirs bit b: bar b is R. Every rule stays in bar-local x
// (0 = the patrons' end, TAP_X = the tap); an R bar is only drawn mirrored (render.c: BG columns 19 - c with every
// tile flipped, OAM X 168 - X with S_FLIPX toggled; Left / Right swap in main.c). src/mirror.c sets the tables at level
// load: CGB flips by attribute; DMG flips its patron tiles in place when every bar is R, and on a mixed level holds both
// directions at even shifts (draw_mask 0xFE: patrons drawn at even x, owner option (a)); the keg, spout and counter get
// flipped copies in free ids. level_dirs: the LEVEL harness's directions (a test hook and the debug box), 0 = all L.
extern uint8_t bar_dirs, level_dirs, draw_mask, mir_attr, mir_bswap, mir_short;
extern uint8_t bar_sfp[2 * NUM_BARS];          // (mirror.c) OAM attribute toggle of bar b: [b] mugs, glass, fill, coin; [4 + b] lifted patrons
void mirror_oam(void) BANKED;                 // (mirror.c) every drawn play frame with an R bar: OAM 4-27 to their mirrored place
extern uint8_t st_tab[64];
extern uint8_t ctr_all[4][BASE_W];            // the counter row (BASE_W wide as base_all): tiles, attributes; an R bar's (mirror.c)
void mirror_load(uint8_t dirs) BANKED;        // LCD off: after load_venue and the patron tiles (start_level); 0 = all L (title)
void draw_bartender(void);
void draw_stage_fx(void);
void hide_all_sprites(void);
extern const uint8_t sway_tab[256];                 // (patrons.c, ROM0) (t / SWAY_FRAMES) & 1 for t < WINDUP_T0, else 0
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
void mug_cursor_load(void) BANKED;                      // the menus' mug cursor: OBJ_MUG.. tiles and OBJ palettes 1-2 (LCD off)
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
uint8_t title_update(uint8_t pressed) BANKED;           // one title frame (it starts the games); 2: idle, show the table
void title_music_toggle(void) BANKED;                   // music on/off and the MUSIC line
// title menu items (title_items[], debug.c reads them): the top level PLAY / BONUS / SETTINGS, PLAY's submenu
// [CONTINUE] / STORY / ARCADE / CLASSIC, BONUS's SOUNDTRACK / MINI GAMES / BOSS RUSH, SETTINGS's MUSIC ON-OFF / BAR CHANGE SNAP-KEEP
enum { K_ARCADE, K_STORY, K_MUSIC, K_CONTINUE, K_BONUS, K_PLAY, K_SETTINGS, K_SOUNDTRACK, K_CLASSIC, K_MINIGAMES,
       K_BOSSRUSH, K_ERASE, K_DEBUG, K_ERASEQ, K_NO, K_YES, K_BARCHANGE, K_BARKEEP,
       K_CREDITS, K_EASY, K_NORMAL, K_HARD, K_CAP_EASY, K_CAP_NORMAL, K_CAP_HARD };   // (SETTINGS' BAR line is K_BARCHANGE while SNAP, K_BARKEEP while KEEP; ERASE DATA,
                                                                                         // DEBUG MENU (unlocked only); the confirm: the K_ERASEQ label, NO, YES;
                                                                                         // PLAY > STORY's difficulty prompt: EASY, NORMAL, HARD, each with its K_CAP_* caption (HALF / NORMAL / EXTRA POINTS) on the row below (no item: title.c menu_frame); K_BARCHANGE and K_BARKEEP are the bar toggles)
enum { TM_TOP, TM_PLAY, TM_BONUS, TM_SETTINGS, TM_ERASE, TM_HARD };   // title_menu: the top level or the submenu of top item n-1 (TM_ERASE: SETTINGS' ERASE ALL DATA? prompt; TM_HARD: PLAY > STORY's HOW HARD prompt)
extern uint8_t title_items[], title_sel;                // the shown menu's items in screen order, the selected line
extern uint8_t title_back;                              // the menu title_enter opens (TM_*; it resets it to TM_TOP)
extern uint8_t title_back_sel;                          // the line its cursor starts on (then 0); on the title, the debug unlock code's progress
// ---- debug.c (banked): the debug menu (every build; locked until the unlock is saved: save.c debug_unlocked) ----
#define KONAMI_DONE 10                                  // the unlock code's length (debug.c konami_step: the trigger lives there)
uint8_t konami_step(uint8_t i, uint8_t pressed) BANKED; // the code's progress after a frame's new presses; KONAMI_DONE: complete
uint8_t debug_gesture(uint8_t pressed) BANKED;          // SELECT held: SELECT + three START taps open the menu; `pressed` back without the taps
void debug_open(void) BANKED;                           // the full-screen menu (GS_DEBUG)
uint8_t debug_step(uint8_t pressed) BANKED;             // one GS_DEBUG frame; 1: a game started
extern uint8_t debug_menu_open;
// ---- jukebox.c (banked: the title's BONUS, the soundtrack player) ---------------------------------
void jukebox_enter(void) BANKED;                        // LCD off: the soundtrack list (GS_JUKEBOX)
uint8_t jukebox_update(uint8_t pressed) BANKED;         // one frame; 1: back on the title (the screen changed)
// ---- scores.c (banked, M10b initials entry and top-5 table) --------------------------------------
void scores_table(void) BANKED;                         // LCD off: the table screen (GS_SCORES)
void scores_after_game(void) BANKED;                    // after GAME OVER: initials (GS_INITIALS) or the table
uint8_t scores_update(uint8_t pressed) BANKED;          // one frame of either; 1: back to the title
// ---- story.c (banked, M11b story mode) -------------------------------------------------------------
extern uint8_t story_on;                                // 1: story mode
// The mode being played (src/story.c play_mode): ARCADE, STORY, CLASSIC, and LEVEL, the old 10-level rotation kept as the
// test harness (title_go, tests/conftest.py title_level) and the debug select's "LEVEL nn" box. The order is the high
// score tables' (save.c): the harness counts as ARCADE there. MODE_RUSH: BONUS > BOSS RUSH (src/rush.c), boss fights on
// the story's engine with nothing saved but the rush's own bests (no top 5, no story progress, no tune unlocks).
enum { MODE_ARCADE, MODE_STORY, MODE_CLASSIC, MODE_LEVEL, MODE_RUSH };
extern uint8_t play_mode;
// A level's knobs (level.c's table rows; CLASSIC's rows are turned into one: classic.c). start_level copies them into the
// globals.
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
// ---- classic.c (banked, CLASSIC: the 1983 layouts; P5) ----------------------------------------------------------------
#define CLASSIC_ROWS 26
extern uint8_t  bar_cap[NUM_BARS];  // patrons bar b may hold at once (try_spawn); 255 outside CLASSIC
extern uint8_t  tip_first;          // CLASSIC: empties to come before the level's first tip (send_empty); 0 off
extern uint16_t ramp_t;             // CLASSIC: frames of play to the in-level ramp's next step (update_patrons); 0 off
extern uint8_t  ramp_k, classic_dirs;
uint8_t classic_row(level_cfg_t *c) BANKED;   // start_level: CLASSIC's row (and its rules); 255 in the other modes
uint8_t classic_bonus_due(void) BANKED;       // the level just cleared is followed by a bonus round
void classic_ramp(void) BANKED;               // ramp_t ran out: the ramp's next step
void classic_ramp_reset(void) BANKED;         // a lost life: the level's own pace again
void classic_tip(uint8_t p) BANKED;           // patron p sent the level's 2nd empty: the first tip, where he stands
// ---- antics.c (banked, CLASSIC's end-of-level antics; P6) ---------------------------------------------------------------
extern uint8_t antics_force, antics_rng, antics_end;   // test hook (1..6: ending n - 1), the endings' own random byte, the ending
void antics_start(void) BANKED;               // enter_level_clear in CLASSIC: pick the ending, where he stands
uint8_t antics_frame(void) BANKED;            // every GS_LEVEL_CLEAR frame in CLASSIC; 1: the clear is over
void story_begin(uint8_t how) BANKED;                   // from the title, LCD off: bit 0 CONTINUE (the saved difficulty), else a new STORY in the difficulty of bits 1-2 (DIFF_*)
uint8_t story_update(uint8_t pressed) BANKED;           // a GS_STORY / GS_GOAL frame; 1: the screen changed
void story_play(void) BANKED;                           // every GS_PLAYING frame in story mode: the chapter goal
void story_level_done(void) BANKED;                     // GS_LEVEL_CLEAR is over: save, the POST scene
void story_fail(void) BANKED;                           // the goal failed: TRY AGAIN, then the shift / the venue again
void story_life_frame(void) BANKED;                     // every GS_LIFE_LOST frame in story mode: the 2-lives cue
void story_bonus_life(void) BANKED;                     // +1 life (max MAX_LIVES): a gold medal in the mini-game
extern uint8_t story_arc;                               // bit 0: ARCADE (the story's engine, arcade rules: story.c); bits 1-2: a STORY run's difficulty (RUN_DIFF)
// The STORY difficulty (owner 2026-10-16: STORY only; chosen when a new story starts, saved with it; EASY and HARD play like NORMAL for now). The
// codes are mg.h's MG_D_* (Practice's). RUN_DIFF is what balancing reads (0 in ARCADE, CLASSIC, BOSS RUSH, Practice); EASY_RUN: this run unlocks nothing.
#define DIFF_NORMAL 0
#define DIFF_HARD   1
#define DIFF_EASY   2
#define RUN_DIFF    (((story_arc) >> 1) & 3)
#define EASY_RUN    (story_on && play_mode == MODE_STORY && RUN_DIFF == DIFF_EASY)
void hud_pal_reset(void) BANKED;                        // CGB: BG palette 1 (the HUD) with its normal colour 2 (a STORY EASY / HARD run changes it: main_cold.c draw_hud)
uint8_t story_diff_saved(void) BANKED;                  // the difficulty the saved story was started in (DIFF_*; NORMAL for an older save)
uint16_t story_pts(uint16_t n) BANKED;                  // a STORY run's points n scaled live by the difficulty (EASY x0.5, HARD x1.5, nearest 5; other runs: n)
void arcade_begin(void) BANKED;                         // PLAY > ARCADE: the saloon's Opening shift, a new run (LCD off)
void arcade_next(void) BANKED;                          // ARCADE: a venue's bonus round is over, the next venue
void extra_life(void) BANKED;                           // add_score passed extra_at: a life (at most MAX_LIVES), the next
#define STORY_SCRATCH 520                               // story.c's cut-scene backdrop buffer (the mini-games' union)
extern uint8_t story_scratch[STORY_SCRATCH];
extern uint8_t story_unskip;                            // test hook: bit s = step s of the sequence counts as built
// ---- mg.c (banked, the mini-game framework; the games include src/mg.h) ------------------------------------
uint8_t mg_update(uint8_t pressed) BANKED;              // a GS_MINI frame; 1: it left (the next screen is up)
uint8_t mg_list_update(uint8_t pressed) BANKED;         // a GS_MGLIST frame (src/mg_list.c); 1: the screen changed
void mg_abort(void) BANKED;                             // the pause menu's QUIT in a mini-game: mg.c's own leave (LCD off)
// ---- pause.c (banked): the pause menu, every mode (state_timer: bit 0 cursor, bit 1 the question, bit 7 a mini-game)
#define PAUSE_NR51 (*(volatile uint8_t *)0xFFF0)       // HRAM (the linker uses 0xFF80-0xFF92): while the menu is open, the NR51 to restore (never 0); else 0
// ---- trans.c (banked): the scene transition, a fizzy drink filling the screen from the bottom and bubbling away (docs: batchEF g14)
// HRAM 0xFFF1 TRANS: TR_WANT (a wired scene change says "the next DISPLAY_OFF is a transition": TRANS_WANT()), TR_PEND (the cover ran,
// the reveal is owed: main.c lcd_on_p runs it as the LCD comes on, or the caller does when it holds TR_HOLD), TR_OFF (a test hook: no transitions). 0xFFF2 / 0xFFF3: the
// scene's LCDC and LYC while the drink covers it; 0xFF94-0xFFCF: its banner rows. main.c lcd_off_p / lcd_on_p / the loop call these.
#define TRANS      (*(volatile uint8_t *)0xFFF1)
#define TR_WANT    1
#define TR_PEND    2
#define TR_HOLD    8
#define TR_VSHIFT  5                                 // bits 5-6: the variant (0 the drink, 1 fade to white, 2 fade through amber), src/trans.c; the debug ROM cycles 1, 2
#define TR_VMASK   0x60
#ifndef TRANS_DEFAULT
#define TRANS_DEFAULT 1                              // the variant at power-on (-DTRANS_DEFAULT=n: the owner's pick, or a debug ROM fixed to one)
#endif
#define TR_OFF     0x80
#define TRANS_WANT() (TRANS |= TR_WANT)
#define TRANS_HOLD() (TRANS |= TR_HOLD)                 // the caller reveals itself (trans_reveal()) once its scene is whole: lcd_on_p does not
void trans_card_out(void) BANKED;                       // the pause card's fades (src/pause.c): the white fade out (LCD off at the end), the new screen's palettes kept, the fade in
void trans_card_arm(void) BANKED;
void trans_card_in(void) BANKED;
void trans_cover(void) BANKED;                          // the old scene filling up; turns the LCD off (as lcd_off_p), PEND set
void trans_arm(void) BANKED;                            // lcd_on_p, LCD still off: the drink behind the new scene, window over the screen
void trans_reveal(void) BANKED;                         // the new scene is on: the drink drains, its bubbles pop; everything put back (nothing when no drink is up)
void pause_open(void) BANKED;                           // START in play / a mini-game: GS_PAUSED, the music's channels quiet
uint8_t pause_update(uint8_t pressed) BANKED;           // a GS_PAUSED frame; 1: it left (the next screen is up)
void pause_close(void) BANKED;                          // the banner window and the sound as they were, back to the game
void mg_list_enter(void) BANKED;                        // LCD off: BONUS > MINI GAMES, the list (GS_MGLIST)
// The full-screen lists' wood-wall look (src/mg_list.c list_frame; the Practice list, the Boss Rush, the soundtrack). Tiles over the stage ids 0-4, CGB palettes 2-7.

#define SKIN_TILE_EDGE    0
#define SKIN_TILE_MEDAL   0                      // + the medal (MEDAL_BRONZE 1 .. MEDAL_GOLD 3): ids 1-3
#define SKIN_PAL_WALL     2                      // the lines and the blank rows: c0 text, c3 the wall
#define SKIN_PAL_MEDAL    3                      // the medal icons: c0 gold, c1 silver, c2 bronze
#define SKIN_PAL_BTN      4                      // the keys line's buttons
#define SKIN_PAL_HEAD     5                      // the header text row: dark text on the gold band
#define SKIN_PAL_FOOT     6                      // the panel: info lines and its lines
#define SKIN_PAL_EDGE     7                      // the row under the header text
void list_skin_load(void) BANKED;                       // LCD off: the tiles over the stage ids 0-4 and the CGB palettes 2-7
void list_frame(uint8_t sep) BANKED;   // LCD off: the 18 rows (tiles and CGB attributes): the panel's top line on row `sep`, its bottom on 17
void list_arrows_load(void) BANKED;                        // the list scroll arrows (src/mg_list.c; the boss rush list shares them)
void list_arrows_show(uint8_t up, uint8_t down, uint8_t t) BANKED;   // OAM 1 / 2: which show, the bob frame count
// save.c: Practice's block at SRAM 0x40 (the mini-games reached in STORY / ARCADE and the best medal of each)
extern uint16_t mg_unlocked;                            // bit g = mini-game g (MG_* of src/mg.h) reached
extern uint8_t  mg_best[];                              // the best medal (MEDAL_*) per mini-game
void mg_record(uint8_t g, uint8_t medal) BANKED;        // game g reached / played to `medal`: saved when it changes
// save.c: the bonus rounds' block "MGB1" at SRAM 0x70 (src/mg_list.c, mg.c): k = 0 shake-up, 1 Perfect Pour, 2 Tip Shower
uint8_t bonus_info(uint8_t k) BANKED;                   // bit 0: played in ARCADE / CLASSIC (unlocked), bits 1-2: the best medal
void bonus_record(uint8_t k, uint8_t medal) BANKED;     // round k played (medal 0) or earned `medal` (in the difficulty mg_mode holds)
uint8_t bonus_best(uint8_t k, uint8_t diff) BANKED;     // round k's best medal in difficulty diff (mg.h MG_D_*)
uint8_t card_seen(uint8_t id) BANKED;                   // the HOW TO PLAY card of mini-game id was shown before (src/mg.c)
void card_mark(uint8_t id) BANKED;                      // ... it is now (nothing in a debug-select run)
#define SAVE_LOCK_DEBUG 2                               // save_lock: a debug-select run (not even the Practice block)
// save.c: the Boss Rush part of the Practice block (src/rush.c): RUSH_SAVE_N bytes, see save.c's layout
#define RUSH_SAVE_N     28
void rush_load(uint8_t *dst) BANKED;                    // the rush part (zeros when the block does not check out)
void rush_store(const uint8_t *src) BANKED;             // write it (with the mini-games' part from WRAM)
void boss_beaten(uint8_t v) BANKED;                     // venue v's boss beaten in STORY / ARCADE: unlocked for BOSS RUSH
// ---- rush.c (banked, BONUS > BOSS RUSH; its screens run as GS_STORY, story_phase STORY_PHASE_RUSH) ----------------
#define STORY_PHASE_RUSH 7                              // story.c's SP_RUSH: story_update hands the frame to rush_update
void rush_enter(void) BANKED;
void rush_quit(void) BANKED;                            // the pause menu's QUIT in a fight: no result, no time; the BOSS RUSH menu (LCD off)                           // LCD off: the BOSS RUSH menu (ALL / CHOOSE)
uint8_t rush_update(uint8_t pressed) BANKED;            // a frame of a rush screen; 1: the screen changed
void rush_won(void) BANKED;                             // story_level_done in MODE_RUSH: the fight was won
void rush_lost(void) BANKED;                            // story SP_FAIL in MODE_RUSH: out of lives
void rush_fight(uint8_t venue) BANKED;                  // story.c: venue's boss fight alone (the story's step, rules)
// ---- credits.c (banked 20: the credits roll; runs as GS_STORY, story_phase STORY_PHASE_CREDITS) ----------------------------
#define STORY_PHASE_CREDITS 8                           // story.c's SP_CREDITS: story_update hands the frame to credits_update
void credits_enter(uint8_t from_story) BANKED;          // from_story 1: after the story's CREDITS pages (its end is story_end); 0: BONUS > CREDITS (B / the end: BONUS)
uint8_t credits_update(uint8_t pressed) BANKED;         // a frame of the roll; 1: the screen changed
void story_end(void) BANKED;                            // story.c: the run is over, the story's score into the STORY top 5
// ---- boss.c (banked, the boss engine, docs/minigames_bosses.md 2.5; ROM0 hooks: patrons.c catch_full / try_spawn,
// render.c compose_bar). A fight is the venue's level with the boss as a BG figure on his own bar (boss_bar,
// BOSS_NONE when no fight is on: the ROM0 hooks compare against it); boss_cols[k] is the first tile id (top; bottom =
// +1) of his body's column k at boss_col + k (0: no column), in BG palette boss_pal.
#define BOSS_COUNT      10      // rows of the boss table (one per venue; a later venue adds its row, not a constant)
#define BOSS_W_MAX       5      // body columns at most (40 px)
#define BOSS_NONE      255
extern uint8_t boss_on, boss_id, boss_bar, boss_lim, boss_col, boss_pal, boss_cols[BOSS_W_MAX];
// The engine's fight-time bytes at the very end of story_scratch (no WRAM of their own: src/boss.h BOSS_SCRATCH; boss_set
// fills them, so they are read only while boss_on): a moving boss's landing marker (boss.c boss_mark), two column
// pairs (BOSS_MARK_BG.. : top t, bottom t + 1) on bar BOSS_MARK_BAR at columns BOSS_MARK_COL, + 1 (render.c compose_bar
// stamps it over that bar's patrons; BOSS_NONE: none), and the topper's look (boss.h).
#define BOSS_FX_N        4
#define BOSS_FX          (story_scratch + STORY_SCRATCH - BOSS_FX_N)
#define BOSS_MARK_BAR    (BOSS_FX[0])
#define BOSS_MARK_COL    (BOSS_FX[1])
#define BOSS_MARK_BG     248
uint8_t boss_catch(uint8_t i) BANKED;   // patrons.c catch_full: full mug i reached him with a hand free (mug_x < boss_lim)
void boss_set(uint8_t id) BANKED;       // story step_start: venue id's boss fight is the next step (BOSS_NONE: none)
void boss_load(void) BANKED;            // enter_level_screen, LCD off, after start_level: his tiles and palettes
void boss_reset(void) BANKED;           // reset_actors: the level's start and after a life (the meter is kept)
void boss_goal(uint8_t *dst) BANKED;    // story shift_start: the fight's banner lines and pace (dst: a goal_t)
void boss_begin(void) BANKED;           // story shift_start, after the pace: the regulars' arrivals, no tips, the HUD
uint8_t boss_frame(void) BANKED;        // story_play, every PLAYING frame of a fight; 1: he is satisfied (the outro)
uint8_t boss_outro(uint8_t t) BANKED;   // story_update, frame t of the outro; 1: over (CHAPTER CLEAR)
void boss_draw(void) BANKED;            // pour_frame (last of the frame's sprites): the topper, within 10 a line
// ---- mosh.c (banked, the mosh pit: The Chrome Cow's twist, docs/minigames_bosses.md section 9; ROM0 hooks in patrons.c,
// each behind a test of mosh_on). A served patron sliding back bumps the walker behind him (0 <= P.x - Q.x <=
// MOSH_CONTACT), who is shoved MOSH_SHOVE_PX toward the tap at MOSH_SPEED px a frame (never past mosh_limit), then
// staggers MOSH_STAGGER frames; one bump per push (patron_mosh[P]), a counter splash under the contact.
#define MOSH_CONTACT    12
#define MOSH_SHOVE_PX   16
#define MOSH_SPEED       2
#define MOSH_STAGGER    30
#define MOSH_SPLASH     30      // frames the counter splash shows
extern uint8_t mosh_on, mosh_limit, mosh_count;   // on (this shift), the x a shove never passes, shoves + jostles so far
extern uint8_t patron_shove[MAX_PATRONS], patron_stag[MAX_PATRONS], patron_mosh[MAX_PATRONS];   // px left, frames, bumped
void mosh_set(uint8_t twist, uint8_t limit) BANKED;   // story shift_start (twist bits, the shift's limit); 0: off
void mosh_bump(uint8_t p) BANKED;       // patrons.c push_px: pushed p has stepped; mosh_on and his bump not used yet
void mosh_step(uint8_t p) BANKED;       // patrons.c walking_step: walker p is being shoved or staggers (instead of a walk)
void mosh_caught(uint8_t p) BANKED;     // patrons.c caught: p caught a glass (a new push: his bump is free again)
void mosh_frame(void) BANKED;           // patrons.c update_patrons, every frame while on: the counter splash's timer
#endif
