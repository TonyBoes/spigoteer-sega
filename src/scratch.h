// THE STORY_SCRATCH MAP: who may share which bytes of story_scratch (game.h STORY_SCRATCH = 520 bytes of WRAM that no screen owns).
//
// WRAM is full, so every screen that needs a buffer lays it over this one. That is safe only while two users that are alive at the same
// time never share a byte. 4279ba3 was the bug: the Mothership's LIGHTS_BUF (written all through his fight) sat on top of the Boss Rush
// list's state (alive through every fight of a run) by four bytes.
//
// This file holds the offsets that are SHARED between files and alive together: everything a boss fight touches, and the Boss Rush
// struct that lives across the fights of a run. Each file takes its offset from here (no literal "+ 300" in a .c file), and the asserts
// at the end fail the build if two of them meet. Users that live alone (the cut-scene backdrop, the story map, the credits, the lists,
// the mini-games) are listed, with their lifetimes, in the USERS table of tests/test_scratch_map.py, which also reads this file and the
// sources, checks that every use of story_scratch is one the map knows, and fails when a new use meets a declared co-alive one.
//
// To add a user: pick bytes, say here (or in the test's USERS table) what it lives with, and let the asserts / the test object.
#ifndef SCRATCH_H
#define SCRATCH_H
#include "game.h"

// ---- a boss fight (src/boss*.c), BOSS RUSH included: all of these are alive at once ----------------------------------------------------
#define SCR_LD_AT        70      // boss.c LD: [0] the head's offset, then the jobs that stream his tiles and palettes in (in-place start only)
#define SCR_LD_MAX       110     // a job may start at LD + SCR_LD_MAX: it is at most 9 bytes, then the 0 that ends the list
#define SCR_LD_END       (SCR_LD_AT + SCR_LD_MAX + 10)
#define SCR_HB_AT        190     // story.c boss_in_place: the HUD's goal columns (9 bytes) until the copy queue has taken them
#define SCR_HB_N         9
#define SCR_BELT_AT      200     // boss_prototype.c BELT_ATTR: the belt's counter attributes (18 bytes) while they wait in the queue
#define SCR_BELT_N       18
#define SCR_CAP_AT       300     // staging for tiles on their way through the copy queue (STAGE / BOSS_CAPBUF, Duke's ENT_BUF, the Sumo's HUD)
#define SCR_CAP_N        64
#define SCR_RUSH_AT      387     // rush.h: the Boss Rush's struct (it lives through every fight of a run)
#define SCR_RUSH_N       48      // sizeof(struct rush_state), asserted in rush.h
#define SCR_LIGHTS_N     8       // boss.h LIGHTS_BUF: the Mothership's lights for the VBlank write
#define SCR_BOSS_N       73      // boss.h BOSS_SCRATCH: his pose table, hand column, BOSS_OWN and BOSS_FX: the end of the buffer
#define SCR_BOSS_AT      (STORY_SCRATCH - SCR_BOSS_N)
#define SCR_LIGHTS_AT    (SCR_BOSS_AT - SCR_LIGHTS_N)

// The fight's ranges, in order, none touching the next. (A new fight-time buffer goes in here: put it in the order and the chain fails if
// it does not fit.)
typedef char scr_fight_ld_hb[SCR_LD_END <= SCR_HB_AT ? 1 : -1];
typedef char scr_fight_hb_belt[SCR_HB_AT + SCR_HB_N <= SCR_BELT_AT ? 1 : -1];
typedef char scr_fight_belt_cap[SCR_BELT_AT + SCR_BELT_N <= SCR_CAP_AT ? 1 : -1];
typedef char scr_fight_cap_rush[SCR_CAP_AT + SCR_CAP_N <= SCR_RUSH_AT ? 1 : -1];
typedef char scr_fight_rush_lights[SCR_RUSH_AT + SCR_RUSH_N <= SCR_LIGHTS_AT ? 1 : -1];
typedef char scr_fight_lights_boss[SCR_LIGHTS_AT + SCR_LIGHTS_N <= SCR_BOSS_AT ? 1 : -1];
typedef char scr_fight_in_buffer[SCR_BOSS_AT + SCR_BOSS_N <= STORY_SCRATCH ? 1 : -1];
#endif
