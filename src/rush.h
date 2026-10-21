// BONUS > BOSS RUSH (src/rush.c): its state, over story.c's cut-scene backdrop buffer (story_scratch). A rush never runs
// a cut-scene or a mini-game, and its own screens' row buffers use story_scratch's first RUSH_AT bytes; a fight's boss
// buffers (boss.h BOSS_SCRATCH) are its last 64. So this lives through every fight of a run without a WRAM byte of its
// own (the stack sits right above the game's variables: see PLAN.md "Boss wave 1 ROM and WRAM"). Tests read it at
// story_scratch + RUSH_AT + the offsets noted.
#ifndef RUSH_H
#define RUSH_H
#include <stdint.h>
#include "game.h"
#include "scratch.h"

#define RUSH_AT        SCR_RUSH_AT   // 387 (src/scratch.h), offset in story_scratch (the list's row buffers: 14 x 20 = 280 bytes before it); the struct must end below boss.h LIGHTS_BUF (RUSH_TOP - 8): the Mothership's lights wrote over built / top / nlines
#define RUSH_TOP       SCR_BOSS_AT   // 447: boss.h BOSS_SCRATCH, STORY_SCRATCH - BOSS_SCRATCH_N (73)

enum { RS_MENU, RS_LIST, RS_NEXT, RS_RESULT, RS_FIGHT };   // rush_state.scr
enum { RM_ALL, RM_CHOOSE };                                 // rush_state.mode

// the save part (RUSH_SAVE_N bytes, save.c: the Practice block from byte 16)
#define RSV_BITS       0          // 2: bit v = venue v's boss beaten in STORY or ARCADE (unlocked here)
#define RSV_BEST       2          // 2 x BOSS_COUNT: the fastest rush win per boss, frames (LE; 0 none)
#define RSV_ALL_SCORE  (RSV_BEST + 2 * BOSS_COUNT)   // 3: ALL's best score (LE, <= 999999; 0 none)
#define RSV_ALL_TIME   (RSV_ALL_SCORE + 3)           // 2: that run's time (frames)
#define RSV_ALL_N      (RSV_ALL_TIME + 2)            // 1: that run's bosses beaten (<= BOSS_COUNT)
#if RSV_ALL_N + 1 != RUSH_SAVE_N
#error "rush save part: RUSH_SAVE_N (game.h) must be its size"
#endif

struct rush_state {               // offset
    uint8_t  scr;                 // 0  RS_*
    uint8_t  mode;                // 1  RM_*
    uint8_t  sel;                 // 2  the menu's line (0 ALL, 1 CHOOSE)
    uint8_t  list_sel;            // 3  the list's line
    uint8_t  boss;                // 4  the venue of the fight on (or next)
    uint8_t  won;                 // 5  fights won in this run
    uint8_t  n;                   // 6  fights in this run (ALL: the bosses unlocked; CHOOSE: 1)
    uint8_t  result;              // 7  1: the run was won (every fight)
    uint8_t  best;                // 8  1: the result is a new best
    uint8_t  t;                   // 9  frames on this screen (stops at 255)
    uint16_t fight_t;             // 10 this fight's PLAYING frames (story.c story_play counts them)
    uint16_t total_t;             // 12 the run's (the fights' sum)
    uint16_t dirty;               // 14 row buffers to redraw (menu / list)
    uint8_t  save[RUSH_SAVE_N];   // 16 the save part as loaded (rush_load) and as written (rush_store)
    uint16_t built;               // 44 bit v = venue v's boss is built (rush_enter reads the story's step table once)
    uint8_t  top;                 // 46 the list's first line shown (the window scrolls: src/rush.c RVIS)
    uint8_t  nlines;              // 47 the built bosses counted (the list's lines; rush_enter): a count of `built` per call ran the frame long
};
#define RUSH ((struct rush_state *)(story_scratch + RUSH_AT))
typedef char rush_fits[(sizeof(struct rush_state) <= SCR_RUSH_N && RUSH_AT + sizeof(struct rush_state) <= RUSH_TOP - SCR_LIGHTS_N && RUSH_TOP <= STORY_SCRATCH) ? 1 : -1];
typedef char rush_rows_fit[(14 * 20 <= SCR_CAP_AT && 14 * 20 <= RUSH_AT) ? 1 : -1];   // (the list's row buffers, below everything a fight stages)
#endif
