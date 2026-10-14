// The mini-game framework (src/mg.c, banked) and what a mini-game file needs from it. docs/minigames_bosses.md 2.1.
//
// A mini-game is one file (`#pragma bank 255`) with xx_enter() (LCD off: its own tiles, palettes and BG over the venue
// backdrop the framework drew; it may set mg_timer) and xx_update(pressed) (every MG_PLAY and MG_END frame; it ends the
// play with mg_finish()). mg.c dispatches to them with a switch (no banked function pointers). Its state lives in the
// union below, over story.c's cut-scene backdrop buffer (no cut-scene runs while a mini-game does).
//
// Resources a game may use (no patrons, mugs or show while it runs; the next level load puts everything back):
//   BG tile ids MG_GAME_BG..255 (MG_BG..MG_GAME_BG-1 hold the medal icon); OBJ tile ids 56-91 and 96-127 (and 128+ not
//   used as BG; not 92-95, the coin: it is loaded once at boot, not by the level load); OAM 0-39 (mg_spigoteer draws the Spigoteer in the 4 slots from the one it is given); CGB BG palettes 2-3 (4 is the medal's in the result window; 0 and
//   5-7 the venue backdrop; 1 the HUD), CGB OBJ palettes 1-7; DMG OBP1. Text: mg_say (game.h, ROM0) on rows
//   MG_TEXT_A / MG_TEXT_B (the banner rows), at most 4 lines a frame.
#ifndef MG_H
#define MG_H
#include <gb/gb.h>
#include <stdint.h>
#include "game.h"
#include "po.h"

// mg_enter's mode: the story's mini-game slot, or Practice (a later step: its menu), optionally HARD (owner Q7)
#define MG_STORY        0
#define MG_PRACTICE     1
#define MG_HARD         2       // | MG_PRACTICE: the game plays its HARD setting (the game reads mg_mode)

// Mini-game ids (mg_enter's id; Practice's SRAM bit and medal index): one per planned game, named, independent of the
// venue order (each game's venue is mg.c's mg_venue[]; the story finds a chapter's game with mg_of_venue[]). An id that
// is planned but not built yet plays the stub in its own venue (only reachable when a test marks the story's mini slot
// built). MG_STUB is the framework's stub game itself (the saloon's backdrop; never saved, never in the release list).
#define MG_QUICKDRAW    0       // the saloon (docs/minigames_bosses.md 4.1)
#define MG_TSHIRT       1       // the stadium (4.2)
#define MG_LOGROLL      2       // the lumber lodge (4.3)
#define MG_ORDERUP      3       // the bistro (4.4)
#define MG_MARSHMALLOW  4       // the igloo (4.5)
#define MG_BATTERY      5       // the robot factory (4.6)
#define MG_MILKRUN      6       // The Chrome Cow (4.10)
#define MG_TAIKO        7       // the teahouse (4.7)
#define MG_MONKEY       8       // the jungle zoo (4.9)
#define MG_ASTEROID     9       // the space lounge (4.8)
#define MG_PLANNED     10       // ids below this are saved (save.c: Practice's block)
#define MG_POUROFF     11       // the story's finale race against Dregs (src/po.c; not in Practice, never saved)
#define MG_STUB        16       // GREEN LIGHT, the framework's stub

enum { MG_INTRO, MG_COUNT, MG_PLAY, MG_END, MG_RESULT };
enum { MEDAL_NONE, MEDAL_BRONZE, MEDAL_SILVER, MEDAL_GOLD };

#define MG_TEXT_A       2       // the two banner rows (map rows, in the HUD colours)
#define MG_TEXT_B       3
#define MG_COUNTER_ROW 11       // the venue backdrop's counter row
#define MG_BG          77       // BAR_TILE_COUNT: BG ids from here are free (the patrons' tiles; the level load puts them back)
#define MG_ICON_N       4       // the medal icon: MG_ICON_N x MG_ICON_N tiles a medal (32x32; GOLD, SILVER, BRONZE)
#define MG_HOURGLASS   220      // the HUD timer's hourglass tile (mg_enter loads it; just above every game's BG tiles, Marshmallow's end at 219; the level load puts it back)
#define MG_GAME_BG     (MG_BG + 3 * MG_ICON_N * MG_ICON_N)   // after the icon's 48 tiles (77-124): the game's own BG tiles

// ---- the framework's state (test hooks: mg_id, mg_phase, mg_timer, mg_score, mg_medal, mg_seed_force) ----
extern uint8_t  mg_id, mg_mode, mg_phase, mg_medal, mg_t;
extern uint16_t mg_timer;       // frames left (0: no timer / out); set by the game's enter for a timed game
extern uint16_t mg_score;       // the game's points (also added to the HUD score as they are earned)
extern uint16_t mg_seed, mg_seed_force;   // the game's RNG seed: next_rand() at entry, or mg_seed_force when non-zero

void mg_enter(uint8_t id, uint8_t mode) BANKED;  // LCD off: game `id` (MG_*), the intro banner, GS_MINI
void mg_hourglass_load(uint8_t id) BANKED;       // the timer's hourglass tile into BG id `id` (LCD off): a timed story shift's HUD (story.c)
uint8_t mg_of_venue(uint8_t venue) BANKED;       // the venue's (the chapter's) mini-game id
// helpers for the games
void mg_points(uint16_t n) BANKED;               // n points to mg_score and the HUD score
void mg_finish(void) BANKED;                     // the play is over: MG_END (the game's outro, then the result)
uint8_t mg_rand(void) BANKED;                    // the game's own 16-bit xorshift on mg_seed (the bar's RNG untouched)
void mg_spigoteer(uint8_t x, uint8_t y, uint8_t frame, uint8_t left, uint8_t oam) BANKED;   // OAM oam..oam+3, px of his top-left
void mg_number(char *dst, uint16_t n) BANKED;    // n in decimal, no leading zeros, 0-terminated (dst: WRAM, >= 6)

// ---- the games -------------------------------------------------------------------------------------------------
void stub_enter(void) BANKED;                    // src/mg_stub.c: GREEN LIGHT
void stub_update(uint8_t pressed) BANKED;

struct stub_state {             // tests read these at story_scratch + offset (tests/test_mg.py)
    uint8_t st;                 // +0 GL_*
    uint8_t round;              // +1 rounds started (1..STUB_ROUNDS)
    uint8_t t;                  // +2 frames in this state
    uint8_t wait;               // +3 frames of red left
    uint8_t react;              // +4 the last reaction, frames (0: too soon / too slow)
    uint8_t lamp[2][2];         // the lamp's two tile rows (VBlank queue source)
    char    txt[12];            // a text line being built
};

void qd_enter(void) BANKED;                      // src/qd.c: QUICK DRAW (the saloon)
void qd_update(uint8_t pressed) BANKED;
uint8_t qd_medal(void) BANKED;                   // the medal its rounds earned (not a score threshold)

struct qd_state {               // tests read these at story_scratch + offset (tests/test_qd.py)
    uint8_t st;                 // +0 QS_* (src/qd.c)
    uint8_t round;              // +1 the round (1..QD_ROUNDS)
    uint8_t wins[2];            // +2 the player's rounds, +3 the Kid's
    uint16_t wait;              // +4 frames left before DRAW! (poke 1 to skip the wait)
    uint8_t badge;              // +6 0: A, 1: B
    uint8_t r;                  // +7 the frame the Kid draws on (frames after DRAW!)
    uint8_t t;                  // +8 frames since DRAW! (or in this state)
    uint8_t res;                // +9 the round's end: QR_* (src/qd.c)
    uint8_t react;              // +10 the player's winning frame (frames after DRAW!)
    uint8_t feint;              // +11 this round's feint: QF_* (0 none)
    uint16_t feint_at;          // +12 the wait value its first frame starts on
    uint8_t feint_t;            // +14 frames into it (QD_FEINT_LEN: over)
    uint8_t fx;                 // +15 the feint's x (screen px + 8, as OAM)
    uint8_t sign[2][14];        // the sign's two letter rows (VBlank queue source; the frame rows at entry)
    uint8_t attr[2];            // the badge's CGB palette for its two columns (bank 1 VBlank queue source)
    uint8_t pips[6];            // row 12: the pips, the Kid's 3 and the player's 3 (VBlank queue source)
    char    txt[14];            // a text line being built
    uint8_t anim;               // frames counted by qd_update (the shake's and the drips' beat)
    uint8_t wall[20];           // the wall's tile row under the stream, saved at entry
    uint8_t row[20];            // the stream row being shown (VBlank queue source)
};

void bs_enter(void) BANKED;                      // src/bs.c: BATTERY SORT (the robot factory)
void bs_update(uint8_t pressed) BANKED;

struct bs_fly { uint8_t type, dir, t; };         // a battery in the air (dir 0: none)
struct bs_state {               // tests read these at story_scratch + offset (tests/test_bs.py)
    uint8_t st;                 // +0 BS_* (src/bs.c)
    uint8_t n;                  // +1 batteries on the belt (bs_queue / bs_qx)
    uint8_t wait;               // +2 frames left for the front battery on the flap (0: none waiting)
    uint8_t window;             // +3 D, the wait a battery gets
    uint8_t speed;              // +4 the belt, 1/8 px a frame
    uint8_t strikes;            // +5
    uint8_t sorted;             // +6 correct sorts
    uint8_t streak;             // +7
    uint8_t made;               // +8 batteries made so far (the 16th is the first broken one)
    uint8_t chute;              // +9 1: the SCRAP chute is open
    uint8_t banner;             // +10 frames left of the chute's banner
    uint8_t last;               // +11 the last outcome: BR_* (src/bs.c)
    uint8_t screen_t;           // +12 frames left of the diverter's arrow
    uint8_t pose, pose_t, flip; // +13 the Spigoteer's frame, its frames left, X-flipped
    uint8_t anim;               // +16
    uint8_t started;            // +17
    uint8_t queue[8];           // +18 the batteries on the belt, front first: BT_*
    int16_t qx[8];              // +26 their x in 1/8 px
    uint8_t belt, belt_f;       // +42 the belt's position (1/8 px), its tile frame
    struct bs_fly fly[3];       // +44
    uint8_t spark_t, spark_x;   // +53 a right bin's sparks
    uint8_t cross_t, cross_x, cross_y;   // +55 the WRONG cross
    uint8_t spit_t, spit_type, spit_dir; // +58 the spat battery
    uint8_t band[2];            // +61 the banner rows' pending change
    uint8_t lamps[3], scr[2], lid[4], belt_row[9];   // VBlank queue sources
    uint8_t hud_attr[20];
    uint8_t wall[2][20], wattr[2][20];   // the banner rows as wall (tiles, CGB attributes), saved at entry
};

void ou_enter(void) BANKED;                      // src/ou.c: ORDER UP! (the bistro)
void ou_update(uint8_t pressed) BANKED;
uint8_t ou_medal(void) BANKED;                   // the medal its rounds earned (not a score threshold)

#define OU_LEN_MAX      9       // round 7's order
struct ou_state {               // tests read these at story_scratch + offset (tests/test_ou.py)
    uint8_t st;                 // +0 OS_* (src/ou.c)
    uint8_t round;              // +1 the round (1..OU_ROUNDS)
    uint8_t len;                // +2 this round's order length (round + 2)
    uint8_t idx;                // +3 dishes called (calling) / served (your turn) so far
    uint8_t strikes;            // +4 0..3
    uint8_t t;                  // +5 frames in this state (or this dish's call)
    uint8_t wait;               // +6 frames left for the next press (your turn)
    uint8_t cleared;            // +7 rounds cleared (the medal)
    uint8_t seq[OU_LEN_MAX];    // +8 the order: 0 UP, 1 RIGHT, 2 DOWN, 3 LEFT (one sequence, grown each round)
    uint8_t x_on;               // +17 the X's cell: a dish, OU_CLOCHE (4), or OU_NONE (255)
    uint8_t want, shown;        // +18 the lit dish wanted, +19 the one on screen (OU_NONE: none)
    uint8_t pal_dish, pal_want; // +20 the dish CGB BG palette 7 holds, +21 the one to write at the next frame's top
    uint8_t light_t;            // +22 frames left of a served dish's light
    uint8_t serve_t;            // +23 frames left of the Spigoteer's serve pose
    uint8_t bubble;             // +24 Colby's bubble: OU_NONE hidden, OU_EMPTY (5), or the dish in it
    uint8_t colby;              // +25 his pose (src/ou.c C_*)
    uint8_t again;              // +26 1: the round is called again after a strike (the order is not grown)
    uint8_t anim;               // +27 frames counted by ou_update (the steam's and the waiter's beat)
    uint8_t cloche;             // +28 0 down, 1 lifted
    uint8_t dish[4][4];         // each cross cell's tiles (TL TR BL BR; VBlank queue source)
    uint8_t dattr[4][4];        // and its CGB palettes (bank 1 queue source)
    uint8_t cl[4];              // the cloche's tiles
    uint8_t bub[5][4];          // the bubble's rows 4-8, columns 3-6 as queued (VBlank queue source)
    uint8_t battr[2][2];        // its inside's CGB palettes (rows 5-6, columns 4-5)
    uint8_t wall[5][4];         // the wall under the bubble, saved at entry
    uint8_t wattr[5][4];        // and its CGB attributes
    uint8_t pips[9];            // row 12, columns 8-16 (VBlank queue source)
    uint8_t pwall[9];           // the wall there, saved at entry
    uint8_t hud[3];             // the strikes, HUD columns 16-18
    char    txt[14];            // a text line being built
};

void mr_enter(void) BANKED;                      // src/mr.c: MILK RUN (The Chrome Cow)
void mr_update(uint8_t pressed) BANKED;
uint8_t mr_medal(void) BANKED;                   // the medal its deliveries earned (not a score threshold)
void mr_vbl(void);                               // src/main.c (ROM0): its VBlank handler, the street's next map column
void mr_lcd_isr(void);                           // src/main.c (ROM0): its LYC handler (the raster split), swapped in for lcd_isr
#define MR_FT           6       // street features alive at once: gates and boxes
#define MR_COL_ROWS    17       // the street's map rows 1-17
#define MR_SPLIT_LY     7       // the LYC line where the street starts to scroll (below the HUD row)
// A map column is written by mr_vbl from the first 36 bytes (main.c's asm reads them at these offsets); lcd_isr reads scx
struct mr_toss { uint8_t t, side, y0; };         // a crate in the air: frames since the toss (0: none), kerb, bike y
struct mr_state {               // tests read these at story_scratch + offset (tests/test_mg_milkrun.py)
    uint16_t dst;               // +0 the column's first map address (row 1), for mr_vbl
    uint8_t ctile[MR_COL_ROWS]; // +2 the column's tiles
    uint8_t cattr[MR_COL_ROWS]; // +19 and its CGB palettes
    uint8_t colq;               // +36 1: a column waits for the next VBlank
    uint8_t scx;                // +37 the street's SCX (lcd_isr sets it below the HUD)
    uint8_t st;                 // +38 0 riding, 1 the outro (time up)
    uint8_t steps;              // +39 speed steps: 1/16 px a frame = 24 + 4 x steps (1.5 .. 2.5 px)
    uint8_t frac;               // +40 the scroll's 1/16 px
    uint8_t lane;               // +41 the bike's lane (the target): 0 top, 1 middle, 2 bottom
    uint8_t y;                  // +42 the bike's top, screen px
    int8_t  queued;             // +43 a lane change pressed during one: -1 up, 1 down, 0 none
    uint8_t inv;                // +44 crash timer: 90 .. 61 wobbling, 60 .. 1 blinking
    uint8_t crates;             // +45 crates left
    uint8_t delivered;          // +46 crates that landed on a box (the medal)
    uint8_t perfect;            // +47 of them PERFECT
    uint8_t anim;               // +48 frames counted (the ride's two frames)
    uint8_t boxes_made;         // +49 boxes generated so far (12)
    uint8_t ti, bi;             // +50 the verges' column counters
    uint8_t started;            // +52 the first play frame has put the banner rows back
    uint8_t secs;               // +53 the HUD timer's seconds
    uint8_t pop_t;              // +54 frames left of the PERFECT pop
    uint8_t pop_y;              // +55 its y (the kerb's), before it rises
    uint8_t lost_t;             // +56 frames since a crate fell off (0: none)
    uint8_t lost_y;             // +57 its y
    uint16_t px;                // +58 the scroll, px
    uint16_t next_col;          // +60 the next world column to stream
    uint16_t time;              // +62 frames left
    uint16_t clk;               // +64 frames toward the next speed step
    uint16_t pop_x;             // +66 world x of the pop's left
    uint16_t lost_x;            // +68 world x of the lost crate
    uint16_t fcol[MR_FT];       // +70 the live features' world columns
    uint8_t fkind[MR_FT];       // +82 0 none; gate: 0x80 | potholes << 3 | blocked lanes; box: 0x40 | full << 1 | bottom
    uint16_t gcol;              // +88 the next gate (generated, not streamed yet)
    uint8_t gkind;              // +90 its kind byte (0: none)
    uint16_t bcol;              // +91 the next box (0xFFFF: none left)
    uint8_t bside;              // +93 its kerb: 0 top, 1 bottom
    struct mr_toss toss[2];     // +94 crates in the air
    uint8_t tbuf[4], cbuf[4];   // +100 HUD timer and crates (VBlank queue sources)
    uint8_t boxbuf[2];          // +108 a landed box's new top tiles
    uint8_t wall[2][20], wattr[2][20];   // +110 map rows 2-3 as the street has them (the banner rows' place)
};

void lr_enter(void) BANKED;                      // src/lr.c: LOG ROLL (the lumber lodge)
void lr_update(uint8_t pressed) BANKED;
uint8_t lr_medal(void) BANKED;                   // the medal its seconds on the log earned (not a score threshold)

struct lr_state {               // tests read these at story_scratch + offset (tests/test_mg_logroll.py)
    int32_t lean;               // +0 the balance marker's offset, 1/65536 px (fall beyond +-64 px)
    int32_t vel;                // +4 1/65536 px a frame
    int16_t drift;              // +8 the log's push now, 1/65536 px a frame squared
    uint16_t on;                // +10 frames on the log (the medal: seconds)
    uint16_t elapsed;           // +12 play frames (the drift's ramp)
    uint16_t flip_in;           // +14 frames to the next flip's telling
    uint16_t roll;              // +16 the bark's phase, 4 frames in 65536
    uint8_t st;                 // +18 LS_* (src/lr.c)
    uint8_t falls;              // +19
    uint8_t fall_t;             // +20 frames since the fall (in the water)
    int8_t  tsgn;               // +21 the push's direction after the last telling: -1 left, 1 right
    int8_t  tell;               // +22 the bark's ramp -30..30 (it turns first)
    int8_t  dsr;                // +23 the push's ramp -30..30 (the same ramp 30 frames later)
    uint8_t fdelay;             // +24 frames until the push starts to turn
    uint8_t s60;                // +25 frames toward the next 100 points
    uint8_t roll_f, roll_vis;   // +26 the bark frame wanted, and the one queued into VRAM
    uint8_t rip_f, rip_vis;     // +28 the same for the ripples
    uint8_t anim;               // +30 frames counted by lr_update
    uint8_t started;            // +31 the first play frame has put the banner rows back
    uint8_t ended;              // +32 the outro's first frame has come
    uint8_t top_t;              // +33 frames of the partner's topple (0: none)
    uint8_t drop_t;             // +34 frames of the droplets' burst (0: none)
    uint8_t drop_x;             // +35 its origin x
    uint8_t band[2];            // +36 a banner row's pending change
    uint8_t digit;              // +38 the HUD falls digit (VBlank queue source)
    uint8_t hud_attr[20];       // +39 the HUD colours of a banner row (CGB attribute source)
    uint8_t brow[20], battr[20];   // +59 a banner row's forest tiles and attributes (queue source)
    uint8_t roll_buf[64];       // +99 the log's body tiles of the frame queued (VBlank queue source)
    uint8_t rip_buf[32];        // +163 the ripple tiles
};

void ad_enter(void) BANKED;                      // src/ad.c: ASTEROID DELIVERY (the space lounge)
void ad_update(uint8_t pressed) BANKED;
uint8_t ad_medal(void) BANKED;                   // the medal its deliveries earned (not a score threshold)

#define AD_ROCKS       10       // 5 lanes x 2
struct ad_state {               // tests read these at story_scratch + offset (tests/test_mg_asteroid.py)
    uint8_t st;                 // +0 AS_*: 0 the beaker flies, 1 it tumbles, 2 no beaker (a new one is coming), 3 the outro
    uint8_t lit;                // +1 the lit porthole 0..2
    uint8_t delivered;          // +2
    uint8_t t;                  // +3 frames in this state
    uint8_t whoa;               // +4 frames left of the WHOA banner (row 14)
    uint8_t secs;               // +5 the HUD timer's seconds
    uint8_t anim;               // +6 frames counted
    uint8_t started;            // +7 the first play frame has put the banner rows back
    uint8_t spd;                // +8 rock speed step: 0 x1, 1 x1.5 (3 delivered), 2 x2 (6)
    uint8_t spawn;              // +9 frames left before a new beaker (state 2)
    int8_t  tx, ty;             // +10 / +11 the thrust this frame (-1, 0, 1)
    uint8_t bounced;            // +12 WHOA bounces so far
    uint8_t spills;             // +13 rock hits so far
    uint16_t x, y;              // +14 / +16 the beaker: centre x, top y, 8.8 px
    int16_t vx, vy;             // +18 / +20 8.8 px a frame
    uint16_t time;              // +22 frames left
    uint16_t clk;               // +24 frames since the lit porthole lit (the time bonus)
    uint16_t rx[AD_ROCKS];      // +26 the rocks' x, 8.8 px over a 176 px loop (lane k: rocks 2k and 2k + 1)
    uint8_t tbuf[4], dbuf[4];   // +46 HUD timer, +50 HUD deliveries (VBlank queue sources)
    uint8_t pbuf[2][9];         // +54 the portholes being redrawn (VBlank queue sources)
    uint8_t r14[20], r14a[20];  // +72 / +92 map row 14 (the launch gap's sky) and its CGB attributes
    uint8_t hattr[20];          // +112 the HUD colours (the banner on row 14)
    uint8_t wall[2][20], wattr[2][20];   // +132 map rows 2-3 as the portholes have them (the banner rows' place)
};

void tk_enter(void) BANKED;                      // src/tk.c: TAIKO POUR (the teahouse)
void tk_leave(void) BANKED;                      // src/tk.c: Taiko Pour's tune goes back to its full band (mg_leave)
void tk_update(uint8_t pressed) BANKED;
uint8_t tk_medal(void) BANKED;                   // the medal its accuracy earned (not a score threshold)

#define TK_LIVE        12       // notes on screen at once (the chart keeps at most 5 a lane in 105 frames)
struct tk_state {               // tests read these at story_scratch + offset (tests/test_mg_taiko.py)
    uint16_t clk;               // +0 the game clock: music_frames, or tk_update's own count with MUSIC OFF
    uint16_t own;               // +2 that own count
    uint8_t next;               // +4 notes spawned (the chart index of the next one)
    uint8_t judged;             // +5 notes resolved (hit, missed or passed)
    uint8_t combo;              // +6
    uint8_t best;               // +7 the best combo
    uint8_t hits;               // +8 GOOD-or-better notes toward the cup being poured (0..7)
    uint8_t cups;               // +9 cups served
    uint8_t perfect;            // +10
    uint8_t good;               // +11
    uint8_t miss;               // +12
    uint8_t spills;             // +13
    uint8_t cnt;                // +14 count-in digits shown (0..4)
    uint8_t band_on;            // +15 the shoji window is back on the banner rows: 0 no, 1 yes
    uint8_t end_t;              // +16 frames since the last note was resolved
    uint8_t anim;               // +17 frames counted
    uint8_t pour_t;             // +18 frames left of the pour (teapot tilted, the stream)
    uint8_t spill_t;            // +19 frames left of the spill (the Spigoteer's fail pose, the puddle)
    uint8_t serve_t;            // +20 frames left of a served bowl (full, steaming)
    uint8_t flash_t[2];         // +21 frames left of each lane's hit flash
    uint8_t flash_k[2];         // +23 its kind: 0 PERFECT, 1 GOOD
    uint8_t rail_on;            // +25 1: the banks are lit (the beat flash)
    uint8_t lant_on;            // +26 1: the lantern's second frame shows
    uint8_t cup_shown;          // +27 the bowl's state on screen (0..4; 255: not drawn yet)
    uint8_t live[TK_LIVE];      // +28 the notes on screen: chart index, | 0x80 judged a miss and sliding off; 255 empty
    uint8_t hud[4];             // +40 combo tens, ones, cups tens, ones (VBlank queue sources)
    uint8_t cup[2][2];          // +44 the bowl's tiles as queued
    uint8_t rail[2][16];        // +48 the banks' tile data: dim, lit
    uint8_t band[2][20];        // +80 the shoji window's rows 2-3
    uint8_t pal[20];            // +120 CGB attributes (the shoji palette) for them
    uint8_t lant[2][2];         // +140 the lantern's tiles as queued
    uint8_t last;               // +144 the last press: 0 none, 1 PERFECT, 2 GOOD, 3 MISS, 4 SPILL
};

void mm_enter(void) BANKED;                      // src/mm.c: MARSHMALLOW DROP (the igloo)
void mm_update(uint8_t pressed) BANKED;

#define MM_MUGS         5       // cup slots (at most 4 share the screen: spacing >= 48 px)
struct mm_state {               // tests read these at story_scratch + offset (tests/test_mg_marshmallow.py)
    int16_t dx;                 // +0 the pail's x, 1/8 px (128..1088)
    int16_t ax;                 // +2 the falling marshmallow's x, px (its left edge)
    int16_t cx[MM_MUGS];        // +4 each cup's x, 1/8 px
    uint8_t on[MM_MUGS];        // +14 the slot is a cup on the belt
    uint8_t n[MM_MUGS];         // +19 marshmallows in it (0..3)
    uint8_t spl[MM_MUGS];       // +24 frames since it splashed + 1 (0: not splashed)
    uint8_t pop[MM_MUGS];       // +29 frames left of its perfect pop
    int8_t dir;                 // +34 the pail's direction (1 right, -1 left)
    uint8_t air;                // +35 a marshmallow is falling
    uint8_t t;                  // +36 frames it has fallen (22: it lands)
    uint8_t load;               // +37 frames until the next one is loaded (0: loaded)
    uint8_t anim;               // +38 frames counted
    uint8_t started;            // +39 the banner rows are the scene again
    uint8_t wstep;              // +40 the aurora frame shown (0..2)
    uint8_t bph;                // +41 the belt's phase
    uint8_t lead;               // +42 the last cup spawned (the next comes when it is gapn px in)
    uint8_t gapn;               // +43 the spacing to the next cup, px (48..72)
    uint8_t perfect;            // +44 perfect cocoas
    uint8_t drops;              // +45
    uint8_t hits;               // +46 marshmallows that landed in a cup
    uint8_t splashes;           // +47
    uint8_t gone;               // +48 cups that left at the right
    uint8_t hud[2];             // +49 the tally's digits (VBlank queue source)
    uint8_t win[4][6];          // +51 the aurora window's map rows (queue source)
    uint8_t belt[2][18];        // +75 the belt row's two phases
    uint8_t wall[2][20];        // +111 map rows 2-3 as the scene has them (the banner rows' place)
    uint8_t wattr[2][20];       // +151
};

void mk_enter(void) BANKED;                      // src/mk.c: MONKEY BUSINESS (the jungle zoo)
void mk_update(uint8_t pressed) BANKED;

#define MK_CRATES       5
struct mk_crate {               // one crate on the counter
    uint8_t st;                 // +0 MC_* (src/mk.c): 0 idle, 1 the lid rattles, 2 up (a peek, then up), 3 open after a theft, 4 the parrot flies
    uint8_t kind;               // +1 0 monkey, 1 parrot
    uint8_t t;                  // +2 frames in this state
    uint8_t u;                  // +3 frames the occupant stays up before it grabs / flies off (a peek of 6 + U)
};
struct mk_state {               // tests read these at story_scratch + offset (tests/test_mg_monkey.py)
    uint8_t st;                 // +0 0 playing, 1 the outro
    uint8_t pos;                // +1 the crate the Spigoteer stands at (the target while he hops)
    uint8_t from;               // +2 the crate he hopped from
    uint8_t act;                // +3 0 none, 1 hop (6 frames), 2 shoo (8 frames; the hit on frame 4)
    uint8_t act_t;              // +4 frames into it
    uint8_t lock;               // +5 whiff lockout frames left (counts down while he is idle)
    uint8_t pend;               // +6 a command pressed during an action: 0 none, 1 left, 2 right, 3 shoo
    uint8_t rep;                // +7 frames since the last hop began (a held direction repeats at 10)
    uint8_t fail_t;             // +8 frames of the fail pose left
    uint8_t coco;               // +9 coconuts left (8 at the start)
    uint8_t started;            // +10 the first play frame has put the awning's rows back
    uint8_t secs;               // +11 the HUD timer's seconds
    uint8_t anim;               // +12 frames counted
    uint8_t next;               // +13 frames to the next pop
    uint8_t unow;               // +14 U now: frames a monkey stays up after its peek (90 -> 45 at 30 s)
    uint8_t ucnt;               // +15 frames toward the next step of U
    uint8_t gap;                // +16 the pop interval now (60 -> 24 at 45 s)
    uint8_t gcnt;               // +17 frames toward the next step of it
    uint8_t shooed;             // +18 monkeys shooed
    uint8_t stolen;             // +19 coconuts taken
    uint8_t parrots;            // +20 parrots shooed
    uint8_t whiffs;             // +21
    uint8_t last;               // +22 the last event: 1 shooed, 2 shooed quick (+100), 3 parrot, 4 whiff, 5 theft
    uint8_t pops;               // +23 pops so far
    uint8_t run_on;             // +24 1: a monkey runs off with a coconut (at most one)
    uint8_t run_k;              // +25 the crate it left
    uint8_t run_t;              // +26 frames it has run
    uint8_t puff_t;             // +27 frames of the shoo puff left
    uint8_t puff_x;             // +28 its x
    uint8_t pile_shown;         // +29 the pile's state on screen (0..5; 255: not drawn yet)
    uint16_t time;              // +30 frames left
    struct mk_crate c[MK_CRATES];   // +32
    uint8_t cshown[MK_CRATES];  // +52 the frame each crate shows (0 closed, 1 / 2 rattle, 3 open; 255 not drawn)
    uint8_t cbuf[MK_CRATES][4]; // +57 each crate's tiles as queued (VBlank queue source)
    uint8_t pbuf[3][4];         // +77 the pile's rows as queued
    uint8_t pips[8];            // +89 the HUD pips as queued
    uint8_t tbuf[4];            // +97 the HUD timer
    uint8_t band[2][20];        // +101 the awning's rows 2-3 (the banner rows' place)
    uint8_t pal[20];            // +141 their CGB attributes (palette 5)
    uint8_t hattr[20];          // +161 the HUD colours (the end banner)
};

void ts_enter(void) BANKED;                      // src/ts.c: T-SHIRT CANNON (the stadium)
void ts_update(uint8_t pressed) BANKED;

struct ts_state {               // tests read these at story_scratch + offset (tests/test_mg_tshirt.py)
    uint8_t st;                 // +0 TSS_*: 0 aim, 1 the shirt flies, 2 reload, 3 the last shirt landed (the cheer), 4 the outro
    uint8_t angle;              // +1 0..10 (10 + 5 x angle degrees)
    int8_t  wind;               // +2 k, -2..2 (k / 256 px a frame^2)
    uint8_t shots;              // +3 shirts fired
    uint8_t num;                // +4 the number of the shot aimed or flying, 1..12 (the wave's speed, the wind's schedule)
    uint8_t reload;             // +5 frames of reload left
    uint8_t rep;                // +6 frames until a held Up / Down steps again
    uint8_t wave;               // +7 the wave's centre fan column, 1..9 (columns centre - 1 .. centre + 1 stand)
    int8_t  wdir;               // +8 its direction
    uint8_t wt;                 // +9 frames until it moves
    uint8_t last;               // +10 the last shot's fan column 0..10 (map column - 9), 255: lost
    uint8_t lastpts;            // +11 its points / 100 (3 wave, 1 next to it, 0)
    uint8_t pose, pose_t;       // +12 the Spigoteer's pose (idle, fire, cheer, miss), +13 frames left of it
    uint8_t puff;               // +14 frames of the muzzle puff left
    uint8_t anim;               // +15 frames counted
    uint8_t started;            // +16 the first play frame has put the banner rows back
    uint8_t t;                  // +17 frames of the flight
    uint16_t shown;             // +18 the fans drawn standing (bit 0..10)
    uint8_t cheer[11];          // +20 frames left of each fan's cheer
    uint16_t x, y;              // +31 / +33 the shirt's centre, 8.8 px
    int16_t vx, vy;             // +35 / +37 8.8 px a frame
    uint8_t dots[6];            // +39 the preview's three dots, x y x y x y (screen px)
    uint8_t hbuf[4], wbuf[2];   // +45 HUD shirts (icon, 2 digits, a blank), +49 HUD wind (chevron, strength): VBlank queue sources
    uint8_t qb[8], qn;          // +51 one-tile queue sources of a frame, +59 how many
    uint8_t sock[6];            // +60 the windsock's tiles
    uint8_t wall[2][20], wattr[2][20];   // +66 map rows 2-3 as the stage has them (the banner rows' place), their CGB attributes
};
void po_enter(void) BANKED;                      // src/po.c: THE POUR-OFF (the finale, in the saloon)
void po_update(uint8_t pressed) BANKED;
void story_pouroff_done(void) BANKED;            // src/story.c: the Pour-Off is won: FINALE_B

// All mini-game state, over story.c's backdrop buffer (story_scratch, STORY_SCRATCH bytes; game.h).
union mg_ram {
    struct stub_state stub;
    struct qd_state qd;
    struct bs_state bs;
    struct ou_state ou;
    struct mr_state mr;
    struct lr_state lr;
    struct ad_state ad;
    struct tk_state tk;
    struct mm_state mm;
    struct mk_state mk;
    struct ts_state ts;
    struct po_state po;
};
#define MG ((union mg_ram *)story_scratch)
typedef char mg_ram_fits_in_story_scratch[(sizeof(union mg_ram) <= STORY_SCRATCH) ? 1 : -1];   // static size assert
#endif
