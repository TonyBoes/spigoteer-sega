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
    BEV_INTRO,    // boss_frame, every PLAYING frame while the level's intro_timer still runs (Duke's entrance holds it and
                  // takes the player's input; it may set intro_timer again). Not called once the intro is over
    BEV_DRAW,     // boss_draw, every drawn frame of the intro (after every other sprite, before the topper counts the OAM
                  // lines): the special's own sprites
    BEV_ROOM,     // boss_draw, every drawn frame he is on his bar and the intro is over (the capacity indicator: how many more
                  // drinks he can hold): `arg` is the engine's count of free hands (0..boss_hands: boss_lim says a drink
                  // reaching him is caught; 0 when it is not). Return 0 to keep it, ROOM_OFF for no indicator (a state with no
                  // limit or no catching at all), else ROOM_FREE(n): n free hands now (ROOM_FREE(0): he sends back / takes nothing)
    BEV_ENTER,    // boss.c entrance_start (E9: he enters on the fight's first frame: after Last call, which turned into his fight
                  // in place, or in Boss Rush): his entrance starts NOW, mid-play, the world already cleared of mugs and his bar of
                  // regulars; boss_state is BS_ENTER, boss_xpose BP_HIDE, intro_timer held at INTRO_FRAMES. Return 1 = "I have
                  // an entrance": BEV_INTRO / BEV_DRAW follow every frame (he holds intro_timer, as Duke's does) and, when it is
                  // done, he sets boss_xpose 0 and boss_state out of BS_ENTER (BS_WALK) after boss_to_bar(bar, start x): the
                  // engine then starts the fight (HUD, BEV_RESET, BEV_BEGIN, the banner). Return 0 = the engine's fallback: he
                  // walks in from the left edge onto his bar
};

// The capacity indicator (owner 2026-10-18: "the empty/full drink icons above and to the right of the boss"): a row of mug icons above and to the
// right of him, one per hand (boss_hands): a dark TAKEN mug for an empty held, a bright ROOM mug for a free hand (OBJ_CAP 124-127,
// assets/art/boss/tag.txt, boss_cap_tiles via boss_cap_stage). OAM 39 down to 37 (boss.c cap_draw).
#define ROOM_OFF       1                          // BEV_ROOM's return: no row (the Mothership holds nothing)
#define ROOM_FREE(n)   ((n) + 2)                  // BEV_ROOM's return: n free slots
#define OBJ_CAP        124                        // the ROOM mug (a pair) and the TAKEN mug (a pair)
#define BOSS_CAP_BYTES 64
#define BOSS_CAPBUF    (story_scratch + 300)      // boss_load's staging for it (Duke's entrance stages its own at the same place, later)
#define OAM_CAP        40                         // the row's entries are OAM_CAP - 1 downward
// The hand mug (owner 2026-10-17: "the mugs they drink from should look more like the drink served to them"): while he gulps, one OAM
// entry (OAM 29) over his right hand column draws the mug the player served (mugs.c spr_full_t / spr_full_p: the venue's drink art and palette);
// his GULP pose has no mug of its own. The Sumo drinks nothing (he is hit); the Mothership beams its drinks up (boss_mothership.c: OAM 29, 30).
#define OAM_HAND       (OAM_DANCERS + 1)          // (the show's second dancer entry: no show in a fight)

enum { BS_WALK, BS_GULP, BS_TELL, BS_SPECIAL, BS_JUMP, BS_OUTRO,   // boss_state (spec 2.5's test hook names)
       BS_WARM,      // E9: not here yet: his entrance starts on the fight's first frame (his bar is free of regulars, he is hidden)
       BS_ENTER,     // his own entrance (BEV_ENTER returned 1) runs: he is not on his bar yet, nothing is caught
       BS_WALKIN };  // the engine's fallback entrance: he walks in from the left edge (boss_special_t = its frame)
// BS_JUMP: away from his bar (a leap, a ride): he catches nothing (a full mug on his bar slides past and breaks), sends
// no empty, the topper is hidden; the special shows what it likes over his spot (boss_xpose: a puff, BP_HIDE) and ends
// it with boss_to_bar.
// poses: the art's order (tools/gen_boss.py POSES), then each boss's extra poses from BP_EXTRA (his gen_boss `extra`)
enum { BP_WALK, BP_STOMP, BP_GULP, BP_WINCE, BP_HAPPY, BP_EXTRA };
#define BP_SWAY   BOSS_POSES_MAX   // the pose after the last extra one's slot: his GULP shifted 2 px (gen_boss sway_pose; the drinking sway)
#define BP_HIDE   14              // boss_xpose: no body at all (his columns are the bar's wall again)

// Resources a fight borrows (the next level load puts every one back)
#define BOSS_BG_A       (PATRON_TILE_BASE + 84)   // variant C's 42 shifted tiles: 21 column pairs
#define BOSS_BG_B       (PATRON_OBJ_BASE + 12)    // variant C's shift-0 pose + the 12 back views: 9 pairs
#define BOSS_PAIRS_A    21
#define BOSS_HUD_BG     252                       // the face, then the meter's EMPTY, HALF, FULL
#define BOSS_ICE_BG     246                       // extra BG tiles (the Yeti's icy counter, the Prototype's conveyor):
                                                  // 246-251 are free in the story; 248-251 the landing marker (game.h)
#define BOSS_PAL        (BGPAL_PATRON + 2)
#define OBJ_TOPPER      OBJ_DANCER                // 4 tiles: STILL, BOB (8x16 each)
#if BOSS_BG_A + 2 * BOSS_PAIRS_A != PATRON_OBJ_BASE || BOSS_BG_B + 18 != PATRON_BACK_BASE + 12 \
    || BOSS_PAIRS_A + 9 != BOSS_PAIRS_MAX || PATRON_BACK_BASE + 12 > OBJ_POUR || BOSS_HUD_BG < OBJ_DMG_COPY + 6 \
    || BOSS_ICE_BG < OBJ_DMG_COPY + 6 || BOSS_ICE_BG + BOSS_ICE_MAX > BOSS_MARK_BG || BOSS_MARK_BG + BOSS_FX_MAX > BOSS_HUD_BG \
    || OBJ_TOPPER + 2 * BOSS_HATS_MAX > OBJ_DANCER + DANCER_TILE_COUNT
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
// Buffers a fight fills at its start, over the end of story.c's cut-scene backdrop buffer (story_scratch: no
// cut-scene, mini-game or title list runs during a fight; BEV_SET / BEV_LOAD fill them again for every fight). Not
// in WRAM of their own: the stack sits right above the game's variables, and 62 more bytes there cost it the
// headroom it needs (the GBDK library's __map_tile_offset, the last variable, was overwritten).
#define BOSS_SCRATCH_N  73
#define BOSS_SCRATCH    (story_scratch + STORY_SCRATCH - BOSS_SCRATCH_N)
#define boss_map        BOSS_SCRATCH       // [(BOSS_POSES_MAX + 1) * BOSS_W_MAX]: his poses (the last: BP_SWAY), pose p's column k's pair at
                                           // p * BOSS_W_MAX + k
#define boss_hand       (BOSS_SCRATCH + (BOSS_POSES_MAX + 1) * BOSS_W_MAX)       // [4]: (was the hand column holding 0..3 empties; unused: BOSS_OWN stays where it was)
#define BOSS_OWN        (boss_hand + 4)                                     // a boss file's own buffer (BOSS_OWN_N bytes)
#define BOSS_OWN_N      (BOSS_SCRATCH_N - (BOSS_POSES_MAX + 1) * BOSS_W_MAX - 4 - BOSS_FX_N)   // (then BOSS_FX: game.h)
// The topper's look, for a special that changes it (boss_set: 0, 0; put them back at BEV_OUTRO): a tile offset from
// OBJ_TOPPER (0: STILL, BOB on a stomp; else that frame, no bob: gen_boss `hats` from 4) and a CGB OBJ palette (0: OBJ 7)
#define BOSS_TOPPER_T   (BOSS_FX[2])
#define BOSS_TOPPER_PAL (BOSS_FX[3])

uint8_t boss_send(uint8_t kind) BANKED;   // send one MUG_EMPTY / MUG_RETURN from his right edge if the fair-empties
                                          // schedule (and boss_window) allows: 1 = sent (next_arrival updated)
uint8_t boss_width(void) BANKED;          // his row's width (px)
void boss_advance(void) BANKED;           // one 8 px stomp toward the tap now (the STOMP pose, the thud), for a special
                                          // that moves him itself; boss_step 0 turns the engine's own stomp timer off
// boss_cols[w..] (a 32 px boss's 5th column, at boss_col + 4) belong to his special (Leo's "!!"): render.c stamps them
// like his body, in his palette; boss_set clears them, boss_look leaves them alone, the special marks them dirty.
// For the bosses that move (wave 2: the Mascot's leap, the Prototype's ride; PLAN.md "Boss hooks as built"):
void boss_to_bar(uint8_t b, uint8_t x) BANKED;   // he arrives on bar b at x (a multiple of 8): off his old bar, b's
                                                 // regulars scared off, the arrivals kept off b (his hands, meter go with him)
void boss_mark(uint8_t b, uint8_t c) BANKED;     // the landing marker on bar b at columns c, c + 1 (BOSS_NONE: none)
void boss_pattern(uint8_t also) BANKED;          // the regulars' arrivals: never his bar, nor bar `also` (BOSS_NONE: only his)

// ---- the hook table's rows (boss.c boss_call): one dispatcher per built boss, in his own file ----
uint8_t boss_big_tex(uint8_t ev, uint8_t arg) BANKED;     // src/boss_big_tex.c: Big Tex, the saloon (3.3)
uint8_t boss_sasquatch(uint8_t ev, uint8_t arg) BANKED;   // src/boss_sasquatch.c: the Sasquatch, the lumber lodge (3.5)
uint8_t boss_critic(uint8_t ev, uint8_t arg) BANKED;      // src/boss_critic.c: the Food Critic, the bistro (3.6)
uint8_t boss_yeti(uint8_t ev, uint8_t arg) BANKED;        // src/boss_yeti.c: the Yeti, the igloo (3.7)
uint8_t boss_sumo(uint8_t ev, uint8_t arg) BANKED;        // src/boss_sumo.c: the Sumo, the teahouse (3.9)
uint8_t boss_mascot(uint8_t ev, uint8_t arg) BANKED;     // src/boss_mascot.c: the Mascot, the stadium (3.4)
uint8_t boss_prototype(uint8_t ev, uint8_t arg) BANKED;  // src/boss_prototype.c: the Prototype, the robot factory (3.8)
uint8_t boss_duke(uint8_t ev, uint8_t arg) BANKED;        // src/boss_duke.c: Duke, the biker bar (3.12)
uint8_t boss_leo(uint8_t ev, uint8_t arg) BANKED;         // src/boss_leo.c: Leo the Lion, the jungle zoo (3.11)
uint8_t boss_mothership(uint8_t ev, uint8_t arg) BANKED;  // src/boss_mothership.c: the Mothership, the space lounge (3.10)
void boss_cap_stage(uint8_t *dst) BANKED;  // the indicator's ROOM and TAKEN mugs, 4 tiles (BOSS_CAP_BYTES) to dst in WRAM, for a boss file that queues them to OBJ_CAP
// His tiles and palettes, from his file's BEV_LOAD (src/boss_load.h): with the LCD off straight to VRAM / palette RAM; with the LCD on (Last call turning into his
// fight, in place: no screen change) they are recorded as jobs in story_scratch and boss.c ld_step streams them in over the next frames, 4 tiles a frame through
// the VBlank queue (the banked art is copied to WRAM first: the queue reads WRAM only) and a palette a frame through HRAM (render.c bpal_write).
// kind 0: BG tiles, 1: OBJ tiles, 2: BG tiles with colours 1-2 forced to the band colour (the Sumo's one-pip tiles); n tiles at id `first` from src in ROM bank `bank`
// (src 0 with kind 1: the capacity indicator's mugs, boss_cap_stage). obj 0 / 1: BG / OBJ palette idx from the four colours p.
void boss_ld(uint8_t kind, uint8_t first, uint8_t n, const uint8_t *src, uint8_t bank) BANKED;
void boss_ldpal(uint8_t obj, uint8_t idx, const uint16_t *p) BANKED;
#define BOSS_BG(first, n, src)   boss_ld(0, first, n, src, CURRENT_BANK)
#define BOSS_OBJ(first, n, src)  boss_ld(1, first, n, src, CURRENT_BANK)
uint8_t boss_near(uint8_t t1, uint8_t span) BANKED;   // OAM entries in use with y - t1 < span (a window of lines starting 15 above t1), for a special that counts the lines it may fill
void boss_hud_now(void) BANKED;           // the HUD's face and meter from boss_hp now (a special that changes boss_hp itself)
#endif
