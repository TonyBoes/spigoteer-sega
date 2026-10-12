// The boss engine's inside (src/boss.c) as each boss's own file sees it (src/boss_<name>.c, banked; docs/minigames_bosses.md
// 2.5 and 3). game.h has what the rest of the game calls; this is only for boss.c and the boss files.
//
// A boss = one row of boss.c's rows[] (his numbers: spec 3.2) + one row of boss.c's hook table (boss_call: his
// dispatcher) + his own file src/boss_<name>.c with that dispatcher, his art (build/boss_<name>_art.h, gen_boss.py
// BOSSES) and his special. The dispatcher gets every event below; it returns 0 for "nothing special" (the engine's
// common rules apply), and for BEV_CATCH 1 = "I took that mug myself".
#ifndef BOSS_H
#define BOSS_H
#include <gb/gb.h>
#include <stdint.h>
#include "game.h"
#include "boss_art.h"        // BOSS_POSES_MAX, BOSS_PAIRS_MAX, BOSS_ICE_MAX, the meter (tools/gen_boss.py)

// events (boss_call's ev)
enum {
    BEV_SET,      // boss_set: the fight is next (nothing on screen): his pose table into WRAM (boss_art_set), his state
    BEV_LOAD,     // boss_load, LCD off, after the level load: his tiles and palettes (boss_art_load), any extra tiles
    BEV_RESET,    // boss_reset: the level's start and after a lost life (he is back at his start x, hands empty)
    BEV_BEGIN,    // boss_begin: LCD on, the banner up, the regulars' pattern drawn
    BEV_FRAME,    // boss_frame, every PLAYING frame once the intro is over, after the engine's walk / push / empties and
                  // before his pose and catch limit are worked out: the special (timers, tells, effects)
    BEV_CATCH,    // boss_catch: full mug `arg` reached him (on his bar, below boss_lim): 1 = he took it himself (it must
                  // be freed or turned by then), 0 = the common catch (meter -1, push, gulp, one more empty held)
    BEV_TELL,     // boss_hook 1 (tests): start the special's tell now
    BEV_OUTRO,    // the outro's first frame (the mugs are gone): put back anything the special changed on screen
};

enum { BS_WALK, BS_GULP, BS_TELL, BS_SPECIAL, BS_JUMP, BS_OUTRO };   // boss_state (spec 2.5's test hook names)
// poses: the art's order (tools/gen_boss.py POSES), then each boss's extra poses from BP_EXTRA (his gen_boss `extra`)
enum { BP_WALK, BP_STOMP, BP_GULP, BP_WINCE, BP_HAPPY, BP_EXTRA };

// Resources a fight borrows (the next level load puts every one back)
#define BOSS_BG_A       (PATRON_TILE_BASE + 84)   // variant C's 42 shifted tiles: 21 column pairs
#define BOSS_BG_B       (PATRON_OBJ_BASE + 12)    // variant C's shift-0 pose + the 12 back views: 9 pairs
#define BOSS_PAIRS_A    21
#define BOSS_HUD_BG     252                       // the face, then the meter's EMPTY, HALF, FULL
#define BOSS_ICE_BG     246                       // extra BG tiles (the Yeti's icy counter): 246-251 are free in the story
#define BOSS_PAL        (BGPAL_PATRON + 2)
#define OBJ_TOPPER      OBJ_DANCER                // 4 tiles: STILL, BOB (8x16 each)
#if BOSS_BG_A + 2 * BOSS_PAIRS_A != PATRON_OBJ_BASE || BOSS_BG_B + 18 != PATRON_BACK_BASE + 12 \
    || BOSS_PAIRS_A + 9 != BOSS_PAIRS_MAX || PATRON_BACK_BASE + 12 > OBJ_POUR || BOSS_HUD_BG < OBJ_DMG_COPY + 6 \
    || BOSS_ICE_BG < OBJ_DMG_COPY + 6 || BOSS_ICE_BG + BOSS_ICE_MAX > BOSS_HUD_BG
#error "boss tiles: variant C's 162-203, its shift-0 pose and the back views 216-233, extra 246-251, the HUD 252-255"
#endif

// ---- the engine's state (src/boss.c; the test hooks of spec 2.5 among them) ----
extern uint8_t  boss_x, boss_hp, boss_hold, boss_state, boss_t, boss_push, boss_hits, boss_step, boss_hands;
extern uint16_t boss_special_t;   // frames to the next special (a boss with one; tests)
extern uint8_t  boss_xpose;       // an extra pose shown instead of WALK / STOMP / GULP (BP_EXTRA..; 0: none). Only the
                                  // push-back (WINCE) and the outro (HAPPY) show over it
extern uint8_t  boss_queue;       // things he holds besides boss_hold (the Critic's returns): counted against boss_cap
extern uint8_t  boss_cap;         // he catches while boss_hold + boss_queue < boss_cap (boss_set: boss_hands)
extern uint8_t  boss_sip_t;       // frames since his last empty went (boss_set... ; >= the row's sip: the next may go)
extern uint8_t  boss_own_gap;     // his own empties' gap after his own last one (0: the level's empty_gap; Sasquatch 80)
extern uint16_t boss_window;      // an empty / return goes only if it arrives within this many frames (0xFFFF: any)
extern uint8_t  boss_fast_full;   // 1: full mugs on his bar slide 3 px a frame (the Yeti's ice; boss.c boss_mugs)
extern uint8_t  boss_fast_empty;  // 1: empties on his bar slide 1 px a frame (the Sasquatch; the ice)
extern uint8_t  boss_returns;     // 1: MUG_RETURN mugs may be on his bar (the Critic): boss_mugs moves them
#define MUG_RETURN  5             // mug_state: a full drink sent back to the bartender (boss.c boss_mugs moves it; mugs.c
                                  // draws it as a full mug and counts it live but does not step it: game.h's enum + 1)
extern uint8_t  boss_map[BOSS_POSES_MAX][BOSS_W_MAX];   // his poses: the column pair of each column (boss_art_set)
extern uint8_t  boss_hand[4];                           // the hand column's pair holding 0..3 empties
extern uint8_t  boss_npose;                             // poses in boss_map

uint8_t boss_send(uint8_t kind) BANKED;   // send one MUG_EMPTY / MUG_RETURN from his right edge if the fair-empties
                                          // schedule (and boss_window) allows: 1 = sent (next_arrival updated)
uint8_t boss_width(void) BANKED;          // his row's width (px)

// ---- the hook table's rows (boss.c boss_call): one dispatcher per built boss, in his own file ----
uint8_t boss_big_tex(uint8_t ev, uint8_t arg) BANKED;     // src/boss_big_tex.c: Big Tex, the saloon (3.3)
#endif
