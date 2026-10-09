// The show and the start patrons (moved out of patrons.c to a switchable bank for M13b: ROM0 was full). start_show(): a tip was
// picked up, some walkers turn to watch the dancers; end_show(): they turn back. place_start_patrons(): the level's (or
// the life's) first patrons. Rare calls, so the banked call costs nothing that matters.
#pragma bank 255
#include <gb/gb.h>
#include <stdint.h>

#include "game.h"
#include "music.h"

extern uint8_t cur_group;

void end_show(void) BANKED {
    uint8_t p;
    show_timer = 0;
    music_play(TUNE_VENUE0 + cur_group);          // the venue's tune again, from its start
    for (p = 0; p < MAX_PATRONS; p++) {
        patron_dist[p] = 0;                      // (a drinker's timer is its drink / wind-up: left alone)
        if (patron_state[p] != PATRON_NONE && (patron_draw[p] & DRAW_BACK) && patron_draw[p] != 255)
            redraw_at(p, patron_x[p]);           // turns back to the bar (its front frame, at the same x)
    }
    if (spawn_timer > (spawn_interval / SHOW_SPAWN_DIV)) spawn_timer = spawn_interval / SHOW_SPAWN_DIV;   // new patrons come sooner, once
}

// M13b: does a distracted patron already cover one of p's columns? (Then p is not distracted: two watchers would
// cover each other on the BG, as neither can be lifted.)
static uint8_t near_watcher(uint8_t p) {
    uint8_t d = patron_draw[p], b = patron_bar[p] & (NUM_BARS - 1), c, e;
    if (d == 255) return 0;
    d &= ~DRAW_BACK;
    c = d >> 3;
    e = c + ((d & 7) ? 3 : 2);
    for (; c != e; c++) { col_scan(b, c, p); if (cs_dist) return 1; }
    return 0;
}

// The tip is picked up: each walking patron is distracted with probability 1/2 (at least one if any walk).
// A distracted patron shuffles to the nearest multiple of 8 px and turns its back (watch_step).
void start_show(void) BANKED {
    uint8_t p, any = 0, first = NO_SLOT;
    show_timer = SHOW_FRAMES;
    music_play(TUNE_SHOW);                        // "Galop infernal" for as long as the show runs
    dancer_frame = 0; dance_tick = 0;
    for (p = 0; p < MAX_PATRONS; p++) {
        patron_dist[p] = 0;
        if (patron_state[p] != PATRON_WALKING) continue;
        if (first == NO_SLOT) first = p;
        if (!(next_rand() & 0x40) || near_watcher(p)) continue;
        patron_dist[p] = 1; patron_timer[p] = 0; any = 1;
    }
    ovl_dirty |= 0x0F;                            // M13b: who may be lifted changed (lift.c)
    if (!any && first != NO_SLOT) { patron_dist[first] = 1; patron_timer[first] = 0; }
}

// Put the level's start patrons on the bars (from DOOR_X; a 2nd group 32 px on where the level has two),
// but never more than the quota still to serve.
void place_start_patrons(void) BANKED {
    uint8_t b, k, placed = 0, remaining = quota > served ? quota - served : 0;
    for (k = 0; k < start_per_bar; k++)
        for (b = 0; b < NUM_BARS; b++)
            if ((start_mask & bar_bit[b]) && placed < remaining) { add_patron(b, DOOR_X + PATRON_SPACING * k, next_rand() % 3); placed++; }
    spawned = served + placed;
    patrons_live = placed;
}

// May patron p (distracted) stand in his back view at column c (columns c, c + 1)? Not over another distracted patron
// (neither can be lifted, so they would cover each other on the BG), and never three to a column.
static uint8_t watch_free(uint8_t b, uint8_t c, uint8_t p) {
    if (col_scan(b, c, p) >= 2 || cs_dist) return 0;
    return col_scan(b, c + 1, p) < 2 && !cs_dist;
}

// Distracted by the show: shuffle 1 px a frame to the nearest multiple of 8 px (at most SHUFFLE_MAX px, never onto
// the tap end), then turn round: the back view, which exists only at shift 0. 4 px off: toward the door if that place
// is free, else toward the tap. M13b: a place is free unless another distracted patron covers its columns (neither can
// be lifted) or two others do (watch_free). A patron who cannot get there waits facing the bar and tries again next
// frame. It stays put either way.
uint8_t watch_step(uint8_t p) BANKED {
    uint8_t x = patron_x[p], r = x & 7, b, t;
    if (r) {
        b = patron_bar[p];
        t = x - r;                                        // the multiple of 8 to the left
        if (r > SHUFFLE_MAX || (r == SHUFFLE_MAX && !watch_free(b, t >> 3, p))) {
            t += 8;                                       // ... or to the right
            if (t >= PATRON_FAR_X || !watch_free(b, t >> 3, p)) t = x;
        } else if (!watch_free(b, t >> 3, p)) t = x;
        if (t == x) {                                     // waiting: drawn at his x, facing the bar
            if (x != patron_draw[p]) redraw_at(p, x);
            return 1;
        }
        x = t > x ? x + 1 : x - 1;
        patron_x[p] = x;
        if (x & 7) { redraw_at(p, x); return 1; }
    }
    x |= DRAW_BACK;                                       // on a multiple of 8: watching the stage
    if (x != patron_draw[p]) redraw_at(p, x);
    return 1;
}
