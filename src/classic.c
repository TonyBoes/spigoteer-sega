// CLASSIC (the three modes, P5; plan: the modes proposal 2.1, 2.2, C5-C9, C13): a level-by-level copy of the 1983
// game's layouts on our venues. Everything here runs at a level load, a lost life, a level's end, or once every
// RAMP_FRAMES frames; the per-frame rules are in ROM0 behind cheap tests (patrons.c: bar_cap in try_spawn, tip_first in
// send_empty / maybe_tip, ramp_t in update_patrons; main.c: classic_bonus_due at a level's end).
//   - The table: 26 rows (both waves), one a level. Settings and their venues: the saloon (cowboys, 50 a serve), the
//     stadium (sports fans, 75), The Chrome Cow (punks, 100), the space lounge (aliens, 150). Directions and per-bar caps
//     from the guide; quota, spawn, step, push-back and the empty gap are ours (tune in playtest). From level 27 the
//     second wave repeats (level 27 = row 14, 40 = row 14 again ...), each repeat a little faster with the LEVEL
//     harness's loop rule (level.c: walk +10 %, spawn -8 %, empty gap -5 frames a repeat, at most 3 repeats).
//   - Every bar starts with one patron; a bar never holds more than its cap at once (bar_n: the leaving ones count
//     while they are on screen).
//   - The in-level ramp (the guide: the longer a level runs, the faster they come): every RAMP_FRAMES of play the
//     spawn interval -RAMP_SPAWN_PCT % and the walk +RAMP_WALK_PCT % of the level's own values, RAMP_STEPS at most; a
//     lost life puts the level's values back and starts the count again.
//   - Bonus rounds: the can shake-up only (bonus.c), after levels 2, 5, 9, 13, 15, 18, 22, 26, then every 13 levels.
//   - Tips: the first one of a level lies where the patron who sends the level's 2nd empty stands (no other tip before
//     it); later ones as in the other modes.
#pragma bank 255
#include <gb/gb.h>
#include <stdint.h>

#include "game.h"

extern uint8_t level, cur_group, arcade_loop;

// one level of the table
typedef struct {
    uint8_t set;            // the setting: 0 saloon, 1 sports bar, 2 punk bar, 3 space bar
    uint8_t dirs;           // bit b: bar b (0 = the top one) is R (patrons from the right)
    uint8_t caps;           // 2 bits a bar (bar 0 lowest): the bar's cap - 1
    uint8_t quota;
    uint16_t spawn;         // frames
    uint8_t step;           // frames per 8 px of walking
    uint8_t push;           // push-back, tile columns
    uint8_t gap;            // fair empties' gap, frames
} classic_row_t;

#define CAPS(a, b, c, d)  ((uint8_t)(((a) - 1) | (((b) - 1) << 2) | (((c) - 1) << 4) | (((d) - 1) << 6)))
#define L 0
#define R 1
#define DIRS(a, b, c, d)  ((uint8_t)((a) | ((b) << 1) | ((c) << 2) | ((d) << 3)))

//                                     set  dirs top -> bottom   caps top -> bottom  quota spawn step push gap
const classic_row_t classic_table[CLASSIC_ROWS] = {
    // wave 1
    { 0, DIRS(L, L, L, L), CAPS(1, 1, 1, 1), 10, 300, 64, 4, 120 },   //  1 saloon
    { 0, DIRS(L, L, L, L), CAPS(2, 2, 2, 2), 14, 270, 60, 4, 110 },   //  2 saloon            bonus 1
    { 1, DIRS(R, R, R, R), CAPS(2, 3, 3, 3), 16, 260, 62, 4, 108 },   //  3 sports: the whole screen flips
    { 1, DIRS(R, R, R, R), CAPS(2, 3, 3, 4), 18, 250, 61, 4, 105 },   //  4 sports
    { 1, DIRS(R, R, R, R), CAPS(3, 3, 4, 4), 20, 240, 60, 4, 102 },   //  5 sports            bonus 2
    { 2, DIRS(R, R, L, L), CAPS(2, 3, 3, 4), 20, 230, 59, 4, 100 },   //  6 punk: split halves
    { 2, DIRS(L, L, R, R), CAPS(3, 3, 4, 4), 22, 220, 58, 4,  97 },   //  7 punk
    { 2, DIRS(R, R, L, L), CAPS(3, 4, 4, 4), 24, 210, 57, 3,  93 },   //  8 punk
    { 2, DIRS(L, L, R, R), CAPS(4, 4, 4, 4), 26, 200, 56, 3,  90 },   //  9 punk              bonus 3
    { 3, DIRS(R, L, L, R), CAPS(4, 4, 4, 4), 28, 190, 55, 3,  87 },   // 10 space: outer / inner pairs
    { 3, DIRS(L, R, R, L), CAPS(4, 4, 4, 4), 28, 180, 54, 3,  84 },   // 11 space
    { 3, DIRS(R, L, R, L), CAPS(4, 4, 4, 4), 30, 170, 53, 3,  82 },   // 12 space: fully alternating
    { 3, DIRS(L, R, L, R), CAPS(4, 4, 4, 4), 30, 160, 52, 3,  80 },   // 13 space             bonus 4
    // wave 2 (every bar 4; from level 27 these 13 rows repeat)
    { 0, DIRS(R, L, R, L), CAPS(4, 4, 4, 4), 30, 160, 50, 3,  80 },   // 14 saloon
    { 0, DIRS(L, R, L, R), CAPS(4, 4, 4, 4), 30, 156, 50, 3,  80 },   // 15 saloon            bonus 5
    { 1, DIRS(R, R, R, R), CAPS(4, 4, 4, 4), 32, 152, 49, 3,  80 },   // 16 sports
    { 1, DIRS(R, R, R, R), CAPS(4, 4, 4, 4), 32, 148, 49, 3,  80 },   // 17 sports
    { 1, DIRS(R, R, R, R), CAPS(4, 4, 4, 4), 32, 145, 48, 3,  80 },   // 18 sports            bonus 6
    { 2, DIRS(R, R, L, L), CAPS(4, 4, 4, 4), 34, 142, 47, 3,  80 },   // 19 punk
    { 2, DIRS(L, L, R, R), CAPS(4, 4, 4, 4), 34, 140, 47, 3,  80 },   // 20 punk
    { 2, DIRS(R, R, L, L), CAPS(4, 4, 4, 4), 34, 138, 46, 3,  80 },   // 21 punk
    { 2, DIRS(L, L, R, R), CAPS(4, 4, 4, 4), 34, 136, 46, 3,  80 },   // 22 punk              bonus 7
    { 3, DIRS(R, R, R, R), CAPS(4, 4, 4, 4), 36, 134, 45, 3,  80 },   // 23 space
    { 3, DIRS(R, R, R, R), CAPS(4, 4, 4, 4), 36, 132, 45, 3,  80 },   // 24 space
    { 3, DIRS(R, R, R, R), CAPS(4, 4, 4, 4), 36, 131, 44, 3,  80 },   // 25 space
    { 3, DIRS(R, R, R, R), CAPS(4, 4, 4, 4), 36, 130, 44, 3,  80 },   // 26 space             bonus 8
};
// the settings' venues (patron groups) and serve scores
const uint8_t classic_venue[4] = { 0, 1, 6, 9 };
const uint8_t classic_score[4] = { 50, 75, 100, 150 };
// the levels (of 1..26) a bonus round follows; later ones: 14..26's, every 13 levels
const uint8_t classic_bonus_lv[8] = { 2, 5, 9, 13, 15, 18, 22, 26 };

#define RAMP_FRAMES    600
#define RAMP_STEPS       3
#define RAMP_SPAWN_PCT   6
#define RAMP_WALK_PCT    5

uint8_t  bar_cap[NUM_BARS] = { 255, 255, 255, 255 };   // patrons a bar may hold at once (patrons.c try_spawn); 255: no cap
uint8_t  tip_first;                 // CLASSIC: empties still to come before the level's first tip (patrons.c); 0: off
uint16_t ramp_t;                    // CLASSIC: frames of play to the ramp's next step (patrons.c); 0: off
uint8_t  ramp_k;                    // the ramp's steps so far this life
uint8_t  classic_dirs;              // this level's directions (level.c passes them to mirror_load)
static uint16_t base_spawn;         // the level's own values, kept at the ramp's first step
static uint8_t  base_speed, base_hurry;

// level (1..99) -> its row (0..25): 1..26 as they are, then 27 = 14 again, every 13 levels
static uint8_t row_of(uint8_t lv) {
    while (lv > CLASSIC_ROWS) lv -= 13;
    return lv - 1;
}

// start_level: in CLASSIC, the level's row into *c (the venue into cur_group, the caps, the directions, the first tip
// and the ramp set up) and the repeats past wave 2 (0..3); elsewhere every CLASSIC rule off and 255.
uint8_t classic_row(level_cfg_t *c) BANKED {
    const classic_row_t *r;
    uint8_t b, k, caps;
    if (play_mode != MODE_CLASSIC) {
        bar_cap[0] = bar_cap[1] = bar_cap[2] = bar_cap[3] = 255;
        tip_first = 0; ramp_t = 0; ramp_k = 0; classic_dirs = 0;
        return 255;
    }
    r = &classic_table[row_of(level)];
    k = level > CLASSIC_ROWS ? (uint8_t)((uint8_t)(level - CLASSIC_ROWS - 1) / 13) + 1 : 0;
    if (k > 3) k = 3;
    cur_group = classic_venue[r->set];
    arcade_loop = 1;                                // (no LOOP banner in CLASSIC)
    c->group = cur_group;
    c->start_mask = 0xF; c->start_per_bar = 1;
    c->quota = r->quota; c->spawn_interval = r->spawn; c->step_frames = r->step;
    c->pushback_cols = r->push; c->serve_score = classic_score[r->set]; c->empty_gap = r->gap;
    caps = r->caps;
    for (b = 0; b < NUM_BARS; b++) { bar_cap[b] = (caps & 3) + 1; caps >>= 2; }
    classic_dirs = r->dirs;
    tip_first = 2;
    ramp_t = RAMP_FRAMES; ramp_k = 0;
    return k;
}

// GS_LEVEL_CLEAR is over in CLASSIC: 1 when a bonus round follows this level
uint8_t classic_bonus_due(void) BANKED {
    uint8_t r = row_of(level) + 1, i;
    for (i = 0; i < 8; i++) if (classic_bonus_lv[i] == r) return 1;
    return 0;
}

static void ramp_apply(void) {
    uint8_t k = ramp_k;
    spawn_interval = base_spawn - (uint16_t)(base_spawn * (uint8_t)(k * RAMP_SPAWN_PCT)) / 100;   // (300 x 18 fits 16 bits)
    patron_speed = base_speed + (uint8_t)((uint16_t)(base_speed * (uint8_t)(k * RAMP_WALK_PCT)) / 100);
    hurry_speed = base_hurry ? base_hurry + (uint8_t)((uint16_t)(base_hurry * (uint8_t)(k * RAMP_WALK_PCT)) / 100) : 0;
}

// patrons.c update_patrons: RAMP_FRAMES more of play went by (ramp_t ran out)
void classic_ramp(void) BANKED {
    if (!ramp_k) { base_spawn = spawn_interval; base_speed = patron_speed; base_hurry = hurry_speed; }
    ramp_k++;
    ramp_apply();
    if (spawn_timer > spawn_interval) spawn_timer = spawn_interval;
    ramp_t = ramp_k < RAMP_STEPS ? RAMP_FRAMES : 0;
}

// main_cold.c resume_after_life (CLASSIC): the level's own pace again, the ramp from the start
void classic_ramp_reset(void) BANKED {
    if (ramp_k) { ramp_k = 0; ramp_apply(); }
    ramp_t = RAMP_FRAMES;
}

// patrons.c send_empty: patron p sent the level's 2nd empty (tip_first ran out): the level's first tip lies where he
// stands, centred under him (no tip can lie there yet: maybe_tip waits for this one)
void classic_tip(uint8_t p) BANKED {
    tip_timer = TIP_FRAMES;
    tip_bar = patron_bar[p];
    tip_x = patron_x[p] + 4;
}
