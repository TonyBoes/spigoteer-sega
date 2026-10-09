// The level table and the level load (moved out of main.c to a switchable bank for M13a: ROM0 was full).
// start_level(): LCD off; copies the level's row (with the arcade loop's difficulty) into the globals and loads the
// venue, the patron tiles and palettes, the lifted-patron set-up (lift.c) and the start patrons.
#pragma bank 5
#include <gb/gb.h>
#include <gb/cgb.h>
#include <stdint.h>

#include "game.h"
#include "palettes.h"

extern uint8_t level, cur_group, arcade_loop, served, step_frames, pushback_cols;
#define WALL_RGB    (venue.pal[VENUE_PAL_BAR][0])   // the venue's wall: colour 0 of the bar and of the patron palettes

// per-level knobs; start_level() copies one row into the globals below
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
#define LEVEL_ROWS 9
// One row per patron group, in the order of gen_art.py's PATRON_GROUPS.
// Playtest 4 flattened the curve: the old one was impossible by level 6. Level 1 is meant for a first-time
// player (2 bars started, ~17 s to cross a bar, a patron every 5 s, 8 to serve); L2 is unchanged. From L2
// every column is interpolated in a straight line to the NEW L6 = the OLD L3 row, and on to the NEW L9 = the
// OLD L5 row (rounded). M10b: past level 9 the rows come round again, a little harder per loop (start_level).
// Old -> new, per level:
//   level      1    2    3    4    5    6    7    8    9
//   quota old  8   10   12   14   16   18   20   21   22
//   quota new  8   10   10   11   11   12   13   15   16
//   spawn old 300  275  250  230  210  190  175  160  150
//   spawn new 300  275  269  263  256  250  237  223  210
//   step  old 64   60   56   52   48   44   40   37   34
//   step  new 64   60   59   58   57   56   53   51   48
//   push  old 4    4    4    4    3    3    3    3    3
//   push  new 4    4    4    4    4    4    4    3    3
//   gap   old 120  110  100  90   80   70   60   52   45
//   gap   new 120  110  108  105  102  100  93   87   80
// The start patrons are one per started bar throughout (the old L6+ second patron is gone: old L5 had one);
// bars 0+2 at L1, bars 0-2 at L2, all four from L3. The serve score column is unchanged. The empty gap
// (fair empties, patrons.c) never drops below 80 frames now, above the old 45 floor, so a bar switch and a
// short walk always fit.
// M13b (overlapping patrons): from level 3 about 1 in 4 spawns is hurried, at 1.5x the level's walk speed (HURRY_*).
// To keep the difficulty where it was, the step column of levels 3-9 is retuned so the AVERAGE entry-to-tap time is
// unchanged: with 3/4 at speed v and 1/4 at 1.5 v the mean crossing time is (3/4 + 1/4 / 1.5) = 11/12 of a v walker's,
// so step_new = step_old x 12/11 (rounded):
//   level      3    4    5    6    7    8    9
//   step M13a  59   58   57   56   53   51   48
//   step M13b  64   63   62   61   58   56   52
// (hurried walkers then take 64/1.5 = 43 .. 52/1.5 = 35 frames per 8 px: about the old L7 .. beyond the old L9 for
// that one patron). Levels 1-2 have no hurried patrons and keep their rows. Quota, spawn, push-back and the empty gap
// are unchanged.
//                 grp mask per quota spawn step push score gap
static const level_cfg_t level_table[LEVEL_ROWS] = {
    { 0, 0x5, 1,  8, 300, 64, 4,  50, 120 },   // 1 cowboys: bars 0 and 2
    { 1, 0x7, 1, 10, 275, 60, 4,  75, 110 },   // 2 sports: bars 0-2
    { 2, 0xF, 1, 10, 269, 64, 4,  75, 108 },   // 3 lumberjacks: all bars; hurried patrons from here (M13b)
    { 3, 0xF, 1, 11, 263, 63, 4, 100, 105 },   // 4 chefs
    { 4, 0xF, 1, 11, 256, 62, 4, 100, 102 },   // 5 divers
    { 5, 0xF, 1, 12, 250, 61, 4, 125, 100 },   // 6 robots: plays like the old level 3
    { 6, 0xF, 1, 13, 237, 58, 4, 125,  93 },   // 7 ninjas
    { 7, 0xF, 1, 15, 223, 56, 3, 150,  87 },   // 8 aliens
    { 8, 0xF, 1, 16, 210, 52, 3, 150,  80 },   // 9 zoo: plays like the old level 5; level 10 is row 1 again (loop 2)
};

static void load_patron_group(uint8_t g) {
    palette_t p;
    uint8_t v, i;
    load_patron_tiles(g, PATRON_TILE_BASE);      // 144 pre-shifted + 12 back-view tiles, from the group's bank (LCD is off)
    if (!is_cgb) return;
    for (v = 0; v < 3; v++) {                    // colour 0 = the wall, so the art needs no transparency
        p[0] = WALL_RGB;
        for (i = 1; i < 4; i++) p[i] = palettes[patron_pal_ids[g][v]][i];
        set_bkg_palette(BGPAL_PATRON + v, 1, p);
    }
}

// M10b arcade loops: after level 9 the venues come round again (level 10 = venue 0 = loop 2, level 19 = loop 3, ...),
// each loop a little harder than the table row, up to LOOP_STEPS_MAX loops' worth: walk speed +LOOP_SPEED_PCT % per
// loop (cap +30 %), spawn interval -LOOP_SPAWN_PCT % per loop (cap -24 %), empty gap -LOOP_GAP_STEP frames per loop,
// never below EMPTY_GAP_FLOOR. Quota, start patrons, push-back and the serve score stay the row's.
#define LOOP_STEPS_MAX   3
#define LOOP_SPEED_PCT  10
#define LOOP_SPAWN_PCT   8
#define LOOP_GAP_STEP    5
#define EMPTY_GAP_FLOOR 80
#define HURRY_FROM       3
void start_level(void) BANKED {
    uint8_t idx = level - 1, k, g;
    const level_cfg_t *c;
    cur_group = idx % LEVEL_ROWS;
    c = &level_table[cur_group];
    arcade_loop = idx / LEVEL_ROWS + 1;
    k = arcade_loop - 1;
    if (k > LOOP_STEPS_MAX) k = LOOP_STEPS_MAX;
    quota = c->quota; spawn_interval = c->spawn_interval; step_frames = c->step_frames;
    spawn_interval -= (uint16_t)(spawn_interval * (uint8_t)(k * LOOP_SPAWN_PCT)) / 100;
    pushback_cols = c->pushback_cols; pushback_px = pushback_cols << 3;
    // 8 px per step_frames in 1/256 px per frame (the old speed over a 120 px walk), scaled by the walk's new length:
    // the level's speed starts at ENTRY_X (left of it a patron is entering, game.h), so (PATRON_FAR_X - ENTRY_X) /
    // PATRON_FAR_X of the distance (13/15 = 104/120) at the same time to the tap (within 2%; 1/256 px resolution).
    patron_speed = (uint8_t)((((2048u / step_frames) * (PATRON_FAR_X - ENTRY_X)) + PATRON_FAR_X / 2) / PATRON_FAR_X);
    patron_speed += (uint8_t)((uint16_t)(patron_speed * (uint8_t)(k * LOOP_SPEED_PCT)) / 100);
    // M13b: hurried walkers (patrons.c try_spawn, about 1 in 4) from level HURRY_FROM on, loops included, at 1.5x the
    // speed above (so the loop's +10 % steps apply to them too)
    hurry_speed = level >= HURRY_FROM ? patron_speed + (patron_speed >> 1) : 0;
    g = c->empty_gap; k *= LOOP_GAP_STEP;
    empty_gap = g >= EMPTY_GAP_FLOOR + k ? g - k : EMPTY_GAP_FLOOR;
    serve_score = c->serve_score; start_per_bar = c->start_per_bar;
    start_mask = c->start_mask;
    served = 0; spawn_timer = spawn_interval; intro_timer = INTRO_FRAMES; level_clear = 0;
    clear_patrons();
    clear_dirty();
    load_venue(cur_group);                      // M9: the venue of the level's theme (theme index = patron group)
    load_patron_group(cur_group);
    lift_level_init(cur_group);                 // M13a: lifted-patron palettes, DMG copies, nobody lifted
    enhance_load(cur_group);                    // M14a: row palettes, lifted columns' attributes, OBJ 4, bank-1 lift tiles
    place_start_patrons();
}

