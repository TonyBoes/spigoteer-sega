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
#define MG_STUB        16       // GREEN LIGHT, the framework's stub

enum { MG_INTRO, MG_COUNT, MG_PLAY, MG_END, MG_RESULT };
enum { MEDAL_NONE, MEDAL_BRONZE, MEDAL_SILVER, MEDAL_GOLD };

#define MG_TEXT_A       2       // the two banner rows (map rows, in the HUD colours)
#define MG_TEXT_B       3
#define MG_COUNTER_ROW 11       // the venue backdrop's counter row
#define MG_BG          77       // BAR_TILE_COUNT: BG ids from here are free (the patrons' tiles; the level load puts them back)
#define MG_ICON_N       4       // the medal icon: MG_ICON_N x MG_ICON_N tiles a medal (32x32; GOLD, SILVER, BRONZE)
#define MG_GAME_BG     (MG_BG + 3 * MG_ICON_N * MG_ICON_N)   // after the icon's 48 tiles (77-124): the game's own BG tiles

// ---- the framework's state (test hooks: mg_id, mg_phase, mg_timer, mg_score, mg_medal, mg_seed_force) ----
extern uint8_t  mg_id, mg_mode, mg_phase, mg_medal, mg_t;
extern uint16_t mg_timer;       // frames left (0: no timer / out); set by the game's enter for a timed game
extern uint16_t mg_score;       // the game's points (also added to the HUD score as they are earned)
extern uint16_t mg_seed, mg_seed_force;   // the game's RNG seed: next_rand() at entry, or mg_seed_force when non-zero

void mg_enter(uint8_t id, uint8_t mode) BANKED;  // LCD off: game `id` (MG_*), the intro banner, GS_MINI
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

// All mini-game state, over story.c's backdrop buffer (story_scratch, STORY_SCRATCH bytes; game.h).
union mg_ram {
    struct stub_state stub;
    struct qd_state qd;
    struct bs_state bs;
    struct ou_state ou;
};
#define MG ((union mg_ram *)story_scratch)
typedef char mg_ram_fits_in_story_scratch[(sizeof(union mg_ram) <= STORY_SCRATCH) ? 1 : -1];   // static size assert
#endif
