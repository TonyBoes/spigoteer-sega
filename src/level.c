// The level table and the level load (moved out of main.c to a switchable bank for M13a: ROM0 was full).
// start_level(): LCD off; copies the level's row (with the arcade loop's difficulty) into the globals and loads the
// venue, the patron tiles and palettes, the lifted-patron set-up (lift.c) and the start patrons.
#pragma bank 5
#include <gb/gb.h>
#include <gb/cgb.h>
#include <stdint.h>

#include "game.h"
#include "palettes.h"
#include "music.h"

extern uint8_t level, cur_group, arcade_loop, served, step_frames, pushback_cols;
#define WALL_RGB    (venue.pal[VENUE_PAL_BAR][0])   // the venue's wall: colour 0 of the bar and of the patron palettes

// per-level knobs (level_cfg_t, game.h); start_level() copies one row into the globals
#define LEVEL_ROWS 10
// One row per patron group, in the order of gen_art.py's PATRON_GROUPS (= the story's chapters).
// Playtest 4 flattened the curve: the old one was impossible by level 6. Level 1 is meant for a first-time
// player (2 bars started, ~17 s to cross a bar, a patron every 5 s, 8 to serve); L2 is unchanged. From L2
// every column is interpolated in a straight line to the NEW L6 = the OLD L3 row, and on to the NEW L9 = the
// OLD L5 row (rounded). M10b: past level 10 the rows come round again, a little harder per loop (start_level).
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
// The 10th venue (2026-10-11, docs/venue10_impact.md): The Chrome Cow (punks) is level 7 and the space lounge moves to
// the end: the rows stay with the POSITION (the difficulty ramp), not the venue. Level 7 is a new row midway between
// the old levels 6 and 7; levels 8-10 are the old rows 7-9 (the teahouse keeps the old level 7's numbers, the zoo takes
// the old level 8's, the space lounge, now last, the old level 9's: the hardest row).
//                 grp mask per quota spawn step push score gap
#define PUSH_COLS_NORMAL 4   // a mug's push: 32 px (the row class's constant; the two hardest rows: PUSH_COLS_HARD)
#define PUSH_COLS_HARD   3   // 24 px
static const level_cfg_t level_table[LEVEL_ROWS] = {
    { 0, 0x5, 1,  8, 300, 64, PUSH_COLS_NORMAL,  50, 120 },   // 1 cowboys: bars 0 and 2
    { 1, 0x7, 1, 10, 275, 60, PUSH_COLS_NORMAL,  75, 110 },   // 2 sports: bars 0-2
    { 2, 0xF, 1, 10, 269, 64, PUSH_COLS_NORMAL,  75, 108 },   // 3 lumberjacks: all bars; hurried patrons from here (M13b)
    { 3, 0xF, 1, 11, 263, 63, PUSH_COLS_NORMAL, 100, 105 },   // 4 chefs
    { 4, 0xF, 1, 11, 256, 62, PUSH_COLS_NORMAL, 100, 102 },   // 5 divers
    { 5, 0xF, 1, 12, 250, 61, PUSH_COLS_NORMAL, 125, 100 },   // 6 robots: plays like the old level 3
    { 6, 0xF, 1, 12, 244, 60, PUSH_COLS_NORMAL, 125,  97 },   // 7 punks (The Chrome Cow): midway between rows 6 and 8
    { 7, 0xF, 1, 13, 237, 58, PUSH_COLS_NORMAL, 125,  93 },   // 8 ninjas
    { 8, 0xF, 1, 15, 223, 56, PUSH_COLS_HARD, 150,  87 },   // 9 zoo
    { 9, 0xF, 1, 16, 210, 52, PUSH_COLS_HARD, 150,  80 },   // 10 aliens: plays like the old level 5; level 11 is row 1 again (loop 2)
};

static void load_patron_group(uint8_t g) {
    palette_t p;
    uint8_t v;
    load_patron_tiles(g, PATRON_TILE_BASE);      // 144 pre-shifted + 12 back-view tiles, from the group's bank (LCD is off)
    if (!is_cgb) return;
    for (v = 0; v < 3; v++) {                    // colour 0 = the wall, so the art needs no transparency
        patron_pal_get(g, v, p);
        p[0] = WALL_RGB;
        set_bkg_palette(BGPAL_PATRON + v, 1, p);
        music_pump();                            // (BRIGHT: ~0.1 frame a palette's lift, LCD off)
    }
}

// M10b arcade loops: after level 10 the venues come round again (level 11 = venue 0 = loop 2, level 21 = loop 3, ...),
// each loop a little harder than the table row, up to LOOP_STEPS_MAX loops' worth: walk speed +LOOP_SPEED_PCT % per
// loop (cap +30 %), spawn interval -LOOP_SPAWN_PCT % per loop (cap -24 %), empty gap -LOOP_GAP_STEP frames per loop,
// never below EMPTY_GAP_FLOOR. Quota, start patrons, push-back and the serve score stay the row's.
#define LOOP_STEPS_MAX   3
#define LOOP_SPEED_PCT  10
#define LOOP_SPAWN_PCT   8
#define LOOP_GAP_STEP    5
#define EMPTY_GAP_FLOOR 80
#define HURRY_FROM       3
// "Almost out" (owner 2026-10-17): of the patrons whose FIRST drink would carry them off the left edge, 1 in N stops just shy of it
// (at ENTRY_X, the last BG column) and drinks there, then comes back as any drinker does. N per play mode (rows: ARCADE, STORY,
// CLASSIC, the LEVEL harness, BOSS RUSH) and run difficulty (columns: NORMAL, HARD, EASY, -): 0 never. This is the tuning table: 7
// everywhere, CLASSIC (kept authentic: the original has no such patron) never.
#define ALMOST_N 7
const uint8_t almost_one_in[5][4] = {
    { ALMOST_N, ALMOST_N, ALMOST_N, ALMOST_N },   // ARCADE
    { ALMOST_N, ALMOST_N, ALMOST_N, ALMOST_N },   // STORY
    { 0, 0, 0, 0 },                               // CLASSIC
    { ALMOST_N, ALMOST_N, ALMOST_N, ALMOST_N },   // the LEVEL harness (the debug select, the tests)
    { ALMOST_N, ALMOST_N, ALMOST_N, ALMOST_N },   // BOSS RUSH
};
// The push a mug gives patron p (the arcade's rule: the same for every mug, no thirst multiplier): pushback_px, the row
// class's constant. He is SERVED (Option C) when it reaches the left-edge stop, d >= x - ENTRY_X: he does not stop
// to drink but slides on and off the screen (the push returned is x + PATRON_W, all of him past the edge); one at or
// left of ENTRY_X is always served. Otherwise he is pushed d px and drinks (never left of ENTRY_X, where the BG
// patrons end), and some patrons ((level - 1) * EARLY_PER_LEVEL, of 256; none on level 1)
// take only a quarter or a half of the push and drink at once.
static uint8_t push_calc(uint8_t p) {
    uint8_t x = patron_x[p], d = pushback_px, m;
    uint16_t c;
    if (x <= ENTRY_X) return x + PATRON_W;                    // (at the old door: always served; else a 24 px push could never serve one)
    c = (uint16_t)(level - 1) * EARLY_PER_LEVEL;                // (level 1: nobody drinks early)
    if (level > 1 && next_rand() < (c > EARLY_MAX ? EARLY_MAX : c)) d = next_rand() & 1 ? d >> 2 : d >> 1;
    m = x - ENTRY_X;
    if (d >= m) {                                              // (Option C: a push that reaches the left-edge stop serves him: he slides on and off)
        if (!patron_drinks[p] && (c = almost_one_in[play_mode][RUN_DIFF & 3]) && next_rand() % (uint8_t)c == 0) return m;   // almost out: stops at ENTRY_X
        return x + PATRON_W;
    }
    return d;
}

// push_calc, and a patron it serves may tip (patrons.c maybe_tip: the coin drops under him as the mug lands and the push takes him away,
// so it is his and shows while he is still on the screen; owner 2026-10-17). A drinker's push is d < x - ENTRY_X.
extern void maybe_tip(uint8_t p);
uint8_t push_for(uint8_t p) BANKED {
    uint8_t r = push_calc(p);
    if (r + ENTRY_X > patron_x[p]) maybe_tip(p);
    return r;
}

// The row's walk speeds and spawn interval for loop k (ARCADE's repeats are a little faster): what start_level starts a level with, and
// level_pace_again gives back to a level that is already running.
static void level_pace(const level_cfg_t *c, uint8_t k) {
    spawn_interval = c->spawn_interval;
    spawn_interval -= (uint16_t)(spawn_interval * (uint8_t)(k * LOOP_SPAWN_PCT)) / 100;
    // 8 px per step_frames in 1/256 px per frame (the old speed over a 120 px walk), scaled by the walk's new length:
    // the level's speed starts at ENTRY_X (left of it a patron is entering, game.h), so (PATRON_FAR_X - ENTRY_X) /
    // PATRON_FAR_X of the distance (13/15 = 104/120) at the same time to the tap (within 2%; 1/256 px resolution).
    patron_speed = (uint8_t)((((2048u / c->step_frames) * (PATRON_FAR_X - ENTRY_X)) + PATRON_FAR_X / 2) / PATRON_FAR_X);
    patron_speed += (uint8_t)((uint16_t)(patron_speed * (uint8_t)(k * LOOP_SPEED_PCT)) / 100);
    // M13b: hurried walkers (patrons.c try_spawn, about 1 in 4) from level HURRY_FROM on, loops included, at 1.5x the
    // speed above (so the loop's +10 % steps apply to them too)
    hurry_speed = level >= HURRY_FROM ? patron_speed + (patron_speed >> 1) : 0;
}

// story.c boss_in_place: Last call turns into the boss fight on the running level, whose speeds and spawn interval carry Last call's percentages: back to
// the row's own, exactly (dividing the percentages out again lost a unit here and there: slower walkers, more of them, more crowding and lifted patrons).
void level_pace_again(void) BANKED {
    uint8_t k = arcade_loop - 1;
    if (k > LOOP_STEPS_MAX) k = LOOP_STEPS_MAX;
    level_pace(&level_table[cur_group], k);
}

void split_off(void) BANKED {   // (the LCD is off) the stage's palette back, the split stops
    SPLIT_ON = 0;
    LYC_REG = SPLIT_WANT;                          // (the window's own line back: the ISR may have left the split's)
    CRITICAL { remove_VBL(split_vbl); remove_VBL(vq_vbl); add_VBL(vq_vbl); remove_LCD(split_isr); remove_LCD(lcd_isr); add_LCD(lcd_isr); }
    if (!(LCDC_REG & LCDCF_ON)) split_pal_put(SPLIT_STG);
}

static void split_arm(void) {        // (LCD off) the stage's palette is read back into SPLIT_STG; the patron palette starts as the same (the caller sets it)
    uint8_t k, v;
    for (k = 0; k < 8; k++) {
        BCPS_REG = (BGPAL_STAGE << 3) | k;
        v = BCPD_REG;
        SPLIT_STG[k] = v; SPLIT_PAL[k] = v;
    }
    SPLIT_WANT = LYC_REG;
    SPLIT_ON = 1;
    CRITICAL { remove_VBL(vq_vbl); remove_VBL(split_vbl); add_VBL(split_vbl); remove_LCD(lcd_isr); remove_LCD(split_isr); add_LCD(split_isr); }   // (split_vbl is vq_vbl with the stage's palette put back first: early in the VBlank)
}


void start_level(void) BANKED {
    uint8_t idx = level - 1, k, g;
    const level_cfg_t *c;
    level_cfg_t row;
    if ((k = classic_row(&row)) != 255) c = &row;   // P5: CLASSIC's table (classic.c), its repeats as the loops
    else {
        cur_group = idx % LEVEL_ROWS;
        c = &level_table[cur_group];
        arcade_loop = idx / LEVEL_ROWS + 1;
        k = arcade_loop - 1;
        if (k > LOOP_STEPS_MAX) k = LOOP_STEPS_MAX;
    }
    quota = c->quota; step_frames = c->step_frames;
    level_pace(c, k);
    pushback_cols = c->pushback_cols; pushback_px = pushback_cols << 3;
    g = c->empty_gap; k *= LOOP_GAP_STEP;
    empty_gap = g >= EMPTY_GAP_FLOOR + k ? g - k : EMPTY_GAP_FLOOR;
    serve_score = c->serve_score; start_per_bar = c->start_per_bar;
    start_mask = c->start_mask;
    served = 0; spawn_timer = spawn_interval; intro_timer = INTRO_FRAMES; level_clear = 0;
    clear_patrons();
    clear_dirty();
    load_venue(cur_group);                      // M9: the venue of the level's theme (theme index = patron group)
    load_patron_group(cur_group);
    if (is_cgb && cur_group == 0) split_arm();  // patron-rev-2: the Saloon's mid-frame palette split (game.h)
    lift_level_init(cur_group);                 // M13a: lifted-patron palettes, DMG copies, nobody lifted
    mirror_load(play_mode == MODE_LEVEL ? level_dirs : classic_dirs);   // P3: bars from the right (the harness, CLASSIC)
    place_start_patrons();
    half_decide();                              // 30 fps on the DMG for the heavy levels (src/half.c)
}

