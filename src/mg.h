// The mini-game framework (src/mg.c, banked) and what a mini-game file needs from it. docs/minigames_bosses.md 2.1.
//
// A mini-game is one file (`#pragma bank 255`) with xx_enter() (LCD off: its own tiles, palettes and BG over the venue
// backdrop the framework drew; it may set mg_timer) and xx_update(pressed) (every MG_PLAY and MG_END frame; it ends the
// play with mg_finish()). mg.c dispatches to them with a switch (no banked function pointers). Its state lives in the
// union below, over story.c's cut-scene backdrop buffer (no cut-scene runs while a mini-game does).
//
// Resources a game may use (no patrons, mugs or show while it runs; the next level load puts everything back):
//   BG tile ids MG_GAME_BG..255 (MG_BG..MG_GAME_BG-1 hold the medal icon); OBJ tile ids 56-127 (and 128+ not used as
//   BG); OAM 4-39 (0-3: the Spigoteer, mg_spigoteer); CGB BG palettes 2-3 (4 is the medal's in the result window; 0 and
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

// mini-game ids = the venue (chapter) whose mini-game it is; MG_STUB the framework's stub game. Until a venue's game is
// built, its id plays the stub (only reachable when a test marks the story's mini slot built).
#define MG_VENUES       9
#define MG_STUB         9

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

void mg_enter(uint8_t id, uint8_t mode) BANKED;  // LCD off: the screen, the intro banner, GS_MINI
// helpers for the games
void mg_points(uint16_t n) BANKED;               // n points to mg_score and the HUD score
void mg_finish(void) BANKED;                     // the play is over: MG_END (the game's outro, then the result)
uint8_t mg_rand(void) BANKED;                    // the game's own 16-bit xorshift on mg_seed (the bar's RNG untouched)
void mg_spigoteer(uint8_t x, uint8_t y, uint8_t frame, uint8_t left) BANKED;   // OAM 0-3, screen px of his top-left
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

// All mini-game state, over story.c's backdrop buffer (story_scratch, STORY_SCRATCH bytes; game.h).
union mg_ram {
    struct stub_state stub;
};
#define MG ((union mg_ram *)story_scratch)
typedef char mg_ram_fits_in_story_scratch[(sizeof(union mg_ram) <= STORY_SCRATCH) ? 1 : -1];   // static size assert
#endif
