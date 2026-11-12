// The level table and the level load (moved out of main.c to a switchable bank for M13a: ROM0 was full).
// start_level(): LCD off; copies the level's row (with the arcade loop's difficulty) into the globals and loads the
// venue, the patron tiles and palettes, the lifted-patron set-up (lift.c) and the start patrons.
#pragma bank 5
#include <gb/gb.h>
#include <gb/cgb.h>
#include <stdint.h>

#include "game.h"
#include "order.h"
#include "palettes.h"
#include "music.h"
#include "tip2.h"
#include "scratch.h"
#include "showlights.h"

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

// Color, the Saloon: GUS (look 2, variant C) is drawn with his skin in colour 2 and his beard in 1, every other look the other way round, so his
// tiles get their two bitplanes swapped (1 <-> 2; 0 and 3 stay) and palette instance 0 (HANK's) is his own (owner Q46 2026-10-29). LCD off.
// Tiles: the 42 shifted ones, the shift-0 pose and the back view (the credits load pose 0 from ROM unswapped, with EMMA's palette: the same picture).
// The Lodge's ASH (look 2 too, the same offsets; owner 2026-10-30: skin in colour 1 like every other look, so palettes can be shared) is the same swap
// with lumberjacks_c's colours 1 and 2 exchanged in assets/palettes.json: the same picture. The credits swap that palette back (credits.c).
static void swap_tiles(uint8_t id, uint8_t n) {
    uint8_t *q, a, t;
    for (; n; n--, id++) {
        q = (uint8_t *)(id < 128 ? 0x9000 + ((uint16_t)id << 4) : 0x8800 + ((uint16_t)(id - 128) << 4));
        for (a = 8; a; a--, q += 2) { t = q[0]; q[0] = q[1]; q[1] = t; }
    }
}
static void swap_gus(void) {
    swap_tiles(PATRON_TILE_BASE + 84, 42);
    swap_tiles(PATRON_OBJ_BASE + 8, 4);
    swap_tiles(PATRON_BACK_BASE + 8, 4);
}

// The BG side of palette instance pi of venue g: colour 0 = the wall; the full-mug instance takes the venue's own drink colours (build/looks.c looks_pal_get)
static void inst_bg_pal(uint8_t g, uint8_t pi, palette_t q) {
    uint8_t k, r;
    if (g && looks_bg_get(g, pi, q)) return;    // (a generated venue: the slot's colours as the Atlas draws them)
    r = looks_pal_get(g, pi, q);
    if (r) for (k = 1; k < 4; k++) q[k] = venue.pal[r == 1 ? VENUE_PAL_DRINK_FULL : r == 2 ? VENUE_PAL_DRINK_EMPTY : VENUE_PAL_SHOW][k];
    q[0] = WALL_RGB;
}

static void load_patron_group(uint8_t g) {
    palette_t p;
    uint8_t v, n = looks_insts(g, INST_OBJ, INST_BG);   // the instances' palette slots (the DMG reads the OBJ ones for its OAM attribute too)
    load_patron_tiles(g, PATRON_TILE_BASE);      // 144 pre-shifted + 12 back-view tiles, from the group's bank (LCD is off)
    if (!is_cgb) return;
    if (!g || g == 2) swap_gus();   // (the Saloon's GUS, the Lodge's ASH)
    if (!g || n < 3) n = 3;                      // (the Saloon's 4th and 5th are loaded below)
    for (v = 0; v < n; v++) {                    // colour 0 = the wall, so the art needs no transparency
        if (INST_BG[v] == BGPAL_STAGE || INST_BG[v] == BGPAL_STAGE_B || (g && INST_BG[v] == BGPAL_HUD) || !INST_BG[v]) continue;   // (a chain slot: start_level loads it, reloaded where the playfield starts; BG 1 is the HUD's above it; BG 0: the bar's own palette, which is XENO's colours in the Space Lounge)
        inst_bg_pal(g, v, p);
        set_bkg_palette(INST_BG[v], 1, p);       // (the legacy venues: instance v on BG 2 + v)
        music_pump();                            // (BRIGHT: ~0.1 frame a palette's lift, LCD off)
    }
    if (g) {
        if (extra_on()) for (v = 0; v < 8; v++) { looks_load(g, v); music_pump(); }   // a generated venue's Color-only looks 3-7: tiles in VRAM bank 1 (its BG 5 / 6 are the split's: start_level)
        return;
    }
    for (v = 0; v < 8; v++) { load_saloon_x(v); music_pump(); }   // the Saloon's Color-only looks 3-7: tiles in VRAM bank 1
    patron_pal_get(0, 3, p);                     // palette instance 3 (ROSIE, REDD): the keg's BG slot, free in the Saloon's playfield
    p[0] = WALL_RGB;
    set_bkg_palette(BGPAL_BAR_B, 1, p);
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
// The push a mug gives patron p: pushback_px, the row class's constant, for his first mug; every mug he has had grows it (owner 2026-11-08:
// the more drinks, the easier to push out; mug n pushes pushback_px * (n + 1) / 2). CLASSIC and the boss fights keep the flat push. He is SERVED (Option C) when it reaches the left-edge stop, d >= x - ENTRY_X: he does not stop
// to drink but slides on and off the screen (the push returned is x + PATRON_W, all of him past the edge); one at or
// left of ENTRY_X is always served. Otherwise he is pushed d px and drinks (never left of ENTRY_X, where the BG
// patrons end), and some patrons ((level - 1) * EARLY_PER_LEVEL, of 256; none on level 1)
// take only a quarter or a half of the push and drink at once.
static uint8_t push_calc(uint8_t p) {
    uint8_t x = patron_x[p], d = pushback_px, m;
    uint16_t c;
    if (x <= ENTRY_X) return x + PATRON_W;                    // (at the old door: always served; else a 24 px push could never serve one)
    c = (uint16_t)(level - 1) * EARLY_PER_LEVEL;                // (level 1: nobody drinks early)
    if (play_mode == MODE_CLASSIC || boss_on || !patron_drinks[p]) {   // (CLASSIC and the boss fights keep the old rule: early drinkers on any mug, a flat push)
        if (level > 1 && next_rand() < (c > EARLY_MAX ? EARLY_MAX : c)) d = next_rand() & 1 ? d >> 2 : d >> 1;   // thirst: else only a FIRST mug can be a short push
    } else {                                                    // thirst: mug n pushes pushback_px * (n + 1) / 2 (patron_drinks counts the mugs before this one)
        c = ((uint16_t)d * (patron_drinks[p] + 2)) >> 1;
        d = c > 255 ? 255 : (uint8_t)c;
    }
    m = x - ENTRY_X;
    if (d >= m) {                                              // (Option C: a push that reaches the left-edge stop serves him: he slides on and off)
        if (!patron_drinks[p] && (c = almost_one_in[play_mode][RUN_DIFF & 3]) && next_rand() % (uint8_t)c == 0) return m;   // almost out: stops at ENTRY_X
        return x + PATRON_W;
    }
    return d;
}

// push_calc, and a patron it serves may tip (patrons.c maybe_tip: the coin drops under him as the mug lands and the push takes him away,
// so it is his and shows while he is still on the screen; owner 2026-10-17). A drinker's push is d < x - ENTRY_X.
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
    pal5_req &= 2;                                 // (a show's OBJ 5 colours, pal5_cur 3: asked for again by split_resume)
    LYC_REG = SPLIT_WANT;                          // (the window's own line back: the ISR may have left the split's)
    CRITICAL { remove_VBL(split_vbl); remove_VBL(split_vbl3); remove_VBL(vq_vbl); add_VBL(vq_vbl); remove_LCD(split_isr); SPLIT_ISR3_OFF(); remove_LCD(lcd_isr); add_LCD(lcd_isr); }
    if (!(LCDC_REG & LCDCF_ON)) {
        if (SPLIT_L_BCPS) split_put_a(SPLIT_L_BCPS, SPLIT_STG);
        if (SPLIT_E_BCPS) split_put_a(SPLIT_E_BCPS, SPLIT_E_STG);
        if (KEG_BCPS) split_put_a(KEG_BCPS, KEG_STG);
    }
}

// (LCD off) The palettes the split rewrites are read back into the STG buffers; the patron-side ones start as the same (the caller sets them).
// late: the BG slot reloaded at SPLIT_LY (the Saloon's BG 5); early: the one at SPLIT_EARLY_LY; keg: BG 1, the HUD's, which holds the keg's colours below the bar's top. 0 = none.
// The Saloon alone (late BG 5, nothing else) is mode 1, the asm handler; any other is mode 3 (main.c split_isr3).
void split_resume(void) BANKED {   // the pause card closed on a level: the split the card's LCD-off dropped, as start_level armed it (the scratch holds its colours; split_off wrote the STG buffers back)
    if (!is_cgb || SPLIT_ON || !(cur_group == 0 || VENUE_KEG_BG(cur_group) == 1 || extra_on())) return;
    SPLIT_WANT = LYC_REG;
    SPLIT_ON = (cur_group || (pal5_cur & 1)) ? 3 : 1;     // (the Saloon runs the event list while a show's dancers share OBJ 5 with MABEL and ARTIE: show_pal5)
    if (SPLIT_ON == 3) split_plan();
    if (pal5_cur == 3) pal5_req |= 1;
    CRITICAL {
        remove_VBL(vq_vbl); remove_LCD(lcd_isr);
        if (SPLIT_ON == 3) { add_VBL(split_vbl3); add_LCD(SPLIT_ISR3); } else { add_VBL(split_vbl); add_LCD(split_isr); }
    }
}

static void split_arm(uint8_t late, uint8_t early, uint8_t keg) {
    uint8_t k, v;
    SPLIT_L_BCPS = late ? 0x80 | (late << 3) : 0;
    SPLIT_E_BCPS = early ? 0x80 | (early << 3) : 0;
    KEG_BCPS = keg ? 0x80 | (keg << 3) : 0;
    for (k = 0; k < 8; k++) {
        if (late) { BCPS_REG = (late << 3) | k; v = BCPD_REG; SPLIT_STG[k] = v; SPLIT_PAL[k] = v; }
        if (early) { BCPS_REG = (early << 3) | k; v = BCPD_REG; SPLIT_E_STG[k] = v; SPLIT_E_PAL[k] = v; }
        if (keg) { BCPS_REG = (keg << 3) | k; v = BCPD_REG; KEG_STG[k] = v; KEG_PAL[k] = v; }
    }
    SPLIT_WANT = LYC_REG;
    SPLIT_ON = (early || keg) ? 3 : 1;
    if (SPLIT_ON == 3) split_plan();
    CRITICAL {
        remove_VBL(vq_vbl); remove_VBL(split_vbl); remove_VBL(split_vbl3); remove_LCD(lcd_isr); remove_LCD(split_isr); SPLIT_ISR3_OFF();
        if (SPLIT_ON == 3) { add_VBL(split_vbl3); add_LCD(SPLIT_ISR3); } else { add_VBL(split_vbl); add_LCD(split_isr); }
    }   // (split_vbl is vq_vbl with the stage's palette put back first: early in the VBlank)
}

// The chain's lower colours (patron side of the reloads), recomputed from the venue's tables: start_level arms with them (chain_set) and the palette fades (trans.c) ask for them at
// every step, so a fade can lift the reloaded palettes with the screen. d: 24 bytes, the keg's BG 1 (8), the late reload's (8), the early one's (8); an unused one is left alone.
// chain_sel: s[0] the late slot, s[1] the early slot, s[2] the keg's slot (0 none), s[3] the late instance, s[4] the early one, s[5] the keg's instance (255 none).
static void chain_sel(uint8_t *s) {
    uint8_t e = 255, l = 255, i, kp = 255, keg = VENUE_KEG_BG(cur_group) == 1 ? BGPAL_HUD : 0;
    uint8_t es = BGPAL_STAGE, ls = BGPAL_STAGE_B;       // (the early and the late reload's BG slot: the Factory's BG 5 ends the stage's row 3, its BG 6 the row 4)
    if ((LOOKS_EARLY6 >> cur_group) & 1) { es = BGPAL_STAGE_B; ls = BGPAL_STAGE; }   // (the Igloo, the Chrome Cow, the Teahouse: BG 5 is on the stage's last row, BG 6 is not)
    if (extra_on()) for (i = 0; i < 8; i++) { if (INST_BG[i] == es) e = i; else if (INST_BG[i] == ls) l = i; else if (INST_BG[i] == BGPAL_HUD) { kp = i; keg = BGPAL_HUD; } }   // (the Stadium: PETE and FRANK on BG 1, the keg on BG 0)
    if (l == 255) { l = e; e = 255; ls = es; }   // (only one used: the one late reload)
    s[0] = ls; s[1] = es; s[2] = keg; s[3] = l; s[4] = e; s[5] = kp;
}

static void chain_put(uint8_t *d, const uint16_t *q) {
    uint8_t k;
    for (k = 0; k < 4; k++) { uint16_t c = BRIGHTEN(q[k]); d[k << 1] = c; d[(k << 1) | 1] = c >> 8; }
}

// OBJ 5 during a show (game.h OBJ_PAT / OBJ_SHOW), d: 16 bytes, the patron's (palette instance 4, lifted for SCREEN BRIGHT) and the show's. With three show palettes (OBJX_ON) x is 32 bytes, scratch.h's SCR_OBJX
// buffers as they lie: the patron colours of OBJ 4 and OBJ 3 (the instances that wear those slots), then the show's for OBJ 3 (the right dancer's palette) and OBJ 4 (the middle's).
static void obj_pat(uint8_t inst, uint8_t *d) {      // the colours of palette instance inst (lifted); the venue's mug colours where it is the mug's
    palette_t q;
    uint8_t r = looks_pal_get(cur_group, inst, q), j;
    if (r) for (j = 0; j < 4; j++) q[j] = venue.pal[r == 1 ? VENUE_PAL_DRINK_FULL : r == 2 ? VENUE_PAL_DRINK_EMPTY : VENUE_PAL_SHOW][j];   // (1 / 2: the venue's full / empty mug colours, 3: the show's)
    chain_put(d, q);
}

static void obj_x(uint8_t *x) {
    {
        uint16_t p[8];
        uint8_t i;
        far_copy(p, venue.show_tiles + DANCER_TILE_COUNT * 16, 16, venue_bank);   // (the middle and the right performer's palettes follow the show's tiles in the venue's bank)
        chain_put(x + 16, p + 4);
        chain_put(x + 24, p);
        for (i = 0; i < 8; i++) { x[i] = x[24 + i]; x[8 + i] = x[16 + i]; }       // (an OBJ slot no instance wears: its "patron" colours are the show's: nothing to give back)
        for (i = 0; i < 5; i++) {
            if (INST_OBJ[i] == 4) obj_pat(i, x);
            if (INST_OBJ[i] == 3) obj_pat(i, x + 8);
        }
    }
}
static void obj_cols(uint8_t *d, uint8_t *x) {
    obj_pat(4, d);
    chain_put(d + 8, venue.pal[VENUE_PAL_SHOW]);
    if (OBJX_ON) { obj_x(x); SHOWLT_STAMP = 0; }       // (OBJX_CO is the show lights' buffer too: showlights.h)
}

// The three show palettes' setup is spread over the show's first three frames (the start frame is the one that has the coin, the plan and the dancers' first entry to do: it is full): show_pal5 only
// asks (OBJX_F 0x40), then one call a frame (rom0_relief.c dance_tick_step): 0x40 fills the colour buffers, 0x80 decides which slots have a give-back and plans the events (OBJX_ON). The dancers pop in
// from the 8th frame on (DANCER_STAGGER), the first one is the left one, who wears OBJ 5 in either state.
void obj_stage(void) BANKED {
    uint8_t k, f = 1;
    if (OBJX_F & 0x40) { obj_x((uint8_t *)OBJX_PAT4); OBJX_F = 0x80; return; }
    for (k = 0; k < 8; k++) {
        if (OBJX_PAT4[k] != OBJX_SHOW[8 + k]) f |= 2;
        if (OBJX_PAT3[k] != OBJX_SHOW[k]) f |= 4;
    }
    if (pal5_cur == 3 && SPLIT_ON == 3) { OBJX_F = 0x88 | (f << 3 & 0x70); split_plan(); }   // (the plan takes frame's third: until it is swapped in, the events run as the old plan timed them, so the give-back bits wait in bits 3-5 and split_plan publishes them with the swap)
    else OBJX_F = f;
}

void chain_cols(uint8_t *d) BANKED {    // d: 40 bytes; [24..39] the OBJ 5 pair (a venue whose instance 4 is OBJ 5), else left alone; with three show palettes OBJX_CO gets OBJ 4's and OBJ 3's (the fades' source colours)
    palette_t q;
    uint8_t s[6];
    if (OBJ5_CHAIN()) obj_cols(d + 24, OBJX_CO);
    if (cur_group == 0) {
        patron_pal_get(0, 4, q);                // palette instance 4 (MABEL, ARTIE): BG 5 below the split, lifted once (BRIGHT) like the others
        q[0] = WALL_RGB;
        chain_put(d + 8, q);
        return;
    }
    chain_sel(s);
    if (KEG_BCPS) {
        if (s[5] != 255) inst_bg_pal(cur_group, s[5], q); else { uint8_t j; for (j = 0; j < 4; j++) q[j] = venue.pal[VENUE_PAL_BAR_B][j]; }
        chain_put(d, q);
    }
    if (SPLIT_L_BCPS && s[3] != 255) { inst_bg_pal(cur_group, s[3], q); chain_put(d + 8, q); }
    if (SPLIT_E_BCPS && s[4] != 255) { inst_bg_pal(cur_group, s[4], q); chain_put(d + 16, q); }
}

static void chain_set(void) {                   // the colours below the split, from the venue
    uint8_t d[40], k;
    chain_cols(d);
    for (k = 0; k < 8; k++) {
        if (KEG_BCPS) KEG_PAL[k] = d[k];
        if (SPLIT_L_BCPS) SPLIT_PAL[k] = d[8 + k];
        if (SPLIT_E_BCPS) SPLIT_E_PAL[k] = d[16 + k];
        if (OBJ5_CHAIN()) { OBJ_PAT[k] = d[24 + k]; OBJ_SHOW[k] = d[32 + k]; }
    }
}

// Mode 3's events of a frame (game.h EV_*), from what the frame holds: the early and late stage reloads, the keg's BG 1 (below the stage's last row, on the line before the late
// reload's when there is one: one palette an HBlank) and the window's: when a window is shown, BG 1 is the HUD's again from its top line (WY_REG) to its end (SPLIT_WANT, its LYC).
// Sorted by line; a line holds one event, the later one moves down a line; the window's end line is an event only when no palette is due on it (the ISR's prologue hides the window).
// Runs whenever SPLIT_WANT or WY_REG changes (set_lyc, SET_WY), and at the arm; the next event is the first below the beam (LY), the first of the frame when none is.
void split_plan(void) BANKED {
    uint8_t line[EV_MAX], kind[EV_MAX], n = 0, i, j, k_, t, w = SPLIT_WANT, wy = WY_REG, kl = SPLIT_L_BCPS ? SPLIT_LY - 1 : SPLIT_LY, ly = LY_REG, shown = LCDC_REG & LCDCF_WINON, ds = DS_NOW ? 0 : 1, xf = ((OBJX_F & 0x88) == 0x88) ? (OBJX_F >> 3) & 7 : OBJX_F & 7;
    if (SPLIT_E_BCPS) { line[n] = SPLIT_EARLY_LY; kind[n++] = EV_E; }
    if (SPLIT_L_BCPS) { line[n] = SPLIT_LY; kind[n++] = EV_L; }
    if (KEG_BCPS) {
        if (SPLIT_L_BCPS && !(shown && wy <= kl + 1 && kl + 1 < w) && !(ds && shown && w <= kl + 2)) {   // (the keg's put and the late reload's: one hit)
            kind[n - 1] = EV_KEG_L;                                      // (double speed: both in the late line's HBlank; normal speed: the hit is on the keg's line, the late palette follows in the next line's HBlank)
            if (ds) line[n - 1] = kl;
        } else { line[n] = kl; kind[n++] = (shown && wy <= kl + 1 && kl + 1 < w) ? EV_KEG_HID : EV_KEG; }   // (a window over the line below it: no keg there, the window's end brings it)
        if (shown && wy > kl + 1 && wy < FLOOR_ROW * 8) { line[n] = wy - 1; kind[n++] = EV_HUD_SHOWN; }
        if (shown && w > kl + 1 && w < FLOOR_ROW * 8) { line[n] = w - 1; kind[n++] = EV_KEG_SHOWN; }
        line[n] = FLOOR_ROW * 8; kind[n++] = EV_HUD_END;   // (the floor row has no keg: BG 1 is the HUD's for the next frame's first line)
    }
    if (pal5_cur & 1) {                                               // (a show: OBJ 5 the patron's again, between the dancers' last line and the first bar's; main.c's wait for it takes no window flags: off the window's end line)
        t = (xf & 6) ? EV_OBJ_LY3 : EV_OBJ_LY;                    // (three show palettes: OBJ 4's and 3's give-backs follow in the next lines' HBlanks, main.c _split_put_o)
        if (shown && (t == w || t + 1 == w || ((xf & 6) && t + 1 < w && w <= t + 3))) t += (xf & 6) ? 4 : 2;   // (the window's end line is not for a palette; no window ends near the stage's last lines but the note's, 31)
        j = t;
        line[n] = j; kind[n++] = EV_OBJ;
        if (xf & 1) { line[n] = EV_OBJS_LY; kind[n++] = EV_OBJS; }    // (three show palettes: OBJ 3 and 4 hold the patrons' colours since the give-backs above: the show's go in at the top of the frame, before the dancers' first line)
    }
    for (i = 1; i < n; i++) {                       // (insertion sort: six at most)
        t = line[i]; j = kind[i];
        for (k_ = i; k_ && line[k_ - 1] > t; k_--) { line[k_] = line[k_ - 1]; kind[k_] = kind[k_ - 1]; }
        line[k_] = t; kind[k_] = j;
    }
    for (i = 1; i < n; i++) if (line[i] <= line[i - 1]) line[i] = line[i - 1] + 1;   // (one palette an HBlank)
    for (i = 0; i < n; i++) if (line[i] > 142) kind[i] = EV_NONE;               // (no HBlank before the frame's end)
    for (i = j = 0; i < n; i++) {
        if (!ds) { if (line[i] == w) j = 1; }                 // (double speed: the ISR hides the window as its hit starts, an event on the end line is the end)
        else if (shown && w < 154) {                          // (normal speed: a palette on the line before the window's end takes the window off after itself; one on the end line, as the line starts)
            if (line[i] == w) { if (kind[i]) kind[i] |= EV_HIDE_FIRST; j = 1; }
            else if (kind[i] && line[i] + 1 == w) { kind[i] |= EV_HIDE_AFTER; j = 1; }
        }
    }
    if (shown && !j && w < 154) {                            // the window's end: its own event, in its place
        for (i = 0; i < n && line[i] < w; i++) ;
        for (j = n; j > i; j--) { line[j] = line[j - 1]; kind[j] = kind[j - 1]; }
        line[i] = w; kind[i] = EV_NONE; n++;
    }
    if (n < 2) { line[n] = 143; kind[n++] = EV_PAD; }    // (the ISR always has a next line to set: a frame's one event gets a harmless second)
    ly = LY_REG;                                       // (the plan took a tenth of a frame or more: the beam is where it is now, not where it was when this began)
    for (i = 0; i < n && line[i] <= ly; i++) ;
    CRITICAL {
        SPLIT_OFF = SPLIT_HIT(ds);
        if ((OBJX_F & 0x88) == 0x88) OBJX_F = xf;                  // (obj_stage's give-back bits: with the new table)
        for (j = 0; j < n; j++) { EV_LINE(j) = line[j] - SPLIT_HIT(ds); EV_KIND(j) = kind[j]; }
        EV_LINE(n) = line[0] - SPLIT_HIT(ds);                                      // (the sentinel: the line after the last is the first's, next frame)
        EV_N = n;
        EV_PS = shown ? 0x80 : 0;                                  // (planned for a shown window: win_on_ / win_off_ replan when the window is not that)
        if (SPLIT_ON == 3) { EV_I = i < n ? i : 0; LYC_REG = EV_LINE(EV_I); }     // (the Saloon changing over from its one reload: saloon_mode puts these after the swap)
    }
}

// The Saloon's split between its two modes (game.h SPLIT_ON 1 / 3) while a show plays: 1 the one reload, 3 the event list (EV_OBJ needs it). Not while a window is up (its end line is the ISR's
// work and the plan takes a frame's tenth): 0, and the caller tries again next frame.
static uint8_t saloon_mode(uint8_t m) {
    uint8_t i;
    if ((LCDC_REG & LCDCF_WINON) || overlay_on) return 0;
    if (m == 3) split_plan();                    // (SPLIT_ON is 1 still, the one reload goes on while the list is made: the swap below puts EV_I and LYC, for the beam as it is by then)
    while (LY_REG >= 30 && LY_REG < 44) ;        // (not while the reload's hit (line 38 / 39) or the OBJ 5 write's (34 / 35) is near: a handler that starts a line late writes a line late; the logic of a Saloon frame ends about here)
    CRITICAL {
        remove_VBL(split_vbl); remove_VBL(split_vbl3); remove_LCD(split_isr); SPLIT_ISR3_OFF();
        SPLIT_ON = m;
        if (m == 3) {
            add_VBL(split_vbl3); add_LCD(SPLIT_ISR3);
            for (i = 0; i < EV_N && EV_LINE(i) + SPLIT_OFF <= LY_REG; i++) ;
            EV_I = i < EV_N ? i : 0;
            LYC_REG = EV_LINE(EV_I);
        } else { add_VBL(split_vbl); add_LCD(split_isr); LYC_REG = SPLIT_LY; }
    }
    return 1;
}

// A show starts (on) or ends on a Color level (render.c pal5_check; draw_stage_fx waits for pal5_cur 2 or 3 to draw the dancers). A venue whose palette instance 4 is OBJ 5 (OBJ5_CHAIN: the Saloon, the Factory...)
// runs the chain: the show's colours go into OBJ 5 in every VBlank, split_isr3 writes the patron's back below the dancers (EV_OBJ); any other has the show's colours in OBJ 5 alone.
void show_pal5(uint8_t on) BANKED {
    if (!on) {                                   // (pal5_cur 3: OBJ 5 is the patron's already, the last event of the frame wrote it)
        if (pal5_cur == 3) { pal5_cur = 1; pal5_req &= 2; OBJX_F &= 6; if (OBJX_F && SPLIT_ON == 3) split_plan(); return; }   // (three show palettes: the give-backs stay for this frame, the show's colours at lines 4 and 5 do not come again)          // (1: the show is over, the event stays one more frame: the palette RAM holds the show's colours until it has written the patron's)
        if (cur_group == 0 && SPLIT_ON == 3 && !saloon_mode(1)) return;     // (a window is up: next frame)
        pal5_cur = 0;
        OBJX_F = 0;
        if (SPLIT_ON == 3) split_plan();
        return;
    }
    if (SPLIT_ON && OBJ5_CHAIN()) {
        pal5_cur = 3;                            // (the plan below has the event)
        {
            uint8_t d[16], k;
            if (venue.show_band & 8) dance_tick = DANCER_BEAT;
            OBJX_F = (venue.show_band & 8) ? 0x40 : 0;   // (three show palettes: the dancers' own OBJ slots, and the give-backs of those that differ: obj_stage, the next frames)
            obj_cols(d, (uint8_t *)OBJX_PAT4);
            for (k = 0; k < 8; k++) { OBJ_PAT[k] = d[k]; OBJ_SHOW[k] = d[8 + k]; }   // (the buffers are the fades' only while a show is on: pal5_cur odd)
        }
        if (SPLIT_ON == 1) { if (!saloon_mode(3)) { pal5_cur = 0; OBJX_F = 0; return; } }
        else split_plan();
        pal5_src = (const uint16_t *)OBJ_SHOW; pal5_req = 1;
        return;
    }
    if (SCR_BRIGHT()) { pal5_lift(); pal5_src = pal5_lifted; }   // SCREEN BRIGHT: the VBlank writes pal5_lifted raw, so the show's colours are lifted into it here (src/bright.c)
    else pal5_src = venue.pal[VENUE_PAL_SHOW];
    pal5_cur = 2;
    pal5_req = 1;
}

// The keg tiles' BG slot on the level screen (the Atlas plan: BG 1 or BG 0, art.h VENUE_KEG_BG): the venue art names BGPAL_BAR_B for them (the mini-games and the title keep that),
// the level's bars, counter and the boss's belt take the plan's. Run after load_venue, before the bars are mirrored.
static void keg_remap(void) {
    uint8_t k = VENUE_KEG_BG(cur_group), r, c;
    for (c = 0; c < sizeof venue.bar_attr; c++) if (venue.bar_attr[c] == BGPAL_BAR_B) venue.bar_attr[c] = k;
    for (c = 0; c < BASE_W; c++) {
        for (r = 0; r < 2; r++) if (base_attr[r][c] == BGPAL_BAR_B) base_attr[r][c] = k;
        if (ctr_all[1][c] == BGPAL_BAR_B) ctr_all[1][c] = k;
    }
}


void start_level(void) BANKED {
    uint8_t idx = level - 1, k, g;
    const level_cfg_t *c;
    level_cfg_t row;
    if (is_cgb) LOOK_HIST[0] = LOOK_HIST[1] = LOOK_HIST[2] = LOOK_HIST[3] = 255;   // the Color spawn rule's history of looks (scratch.h)
    TIP2->t = 0;                                    // (the second tip coin lives in story_scratch, which the last screen left junk in: tip2.h)
    if ((k = classic_row(&row)) != 255) c = &row;   // P5: CLASSIC's table (classic.c), its repeats as the loops
    else {
        cur_group = story_on ? VEN(idx % LEVEL_ROWS) : idx % LEVEL_ROWS;   // (STORY / ARCADE: level n is chapter n of the story's order, its venue; the LEVEL harness plays the rows in order; src/order.h)
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
    if (is_cgb) keg_remap();
    if (is_cgb && cur_group == 0) {             // patron-rev-2: the Saloon's mid-frame palette split (game.h)
        palette_t q;
        split_arm(BGPAL_STAGE, 0, 0);
        patron_pal_get(0, 4, q);                // palette instance 4 (MABEL, ARTIE): BG 5 below the split, lifted once (BRIGHT) like the others (chain_cols: the same, for the fades)
        q[0] = WALL_RGB;
        chain_put((uint8_t *)SPLIT_PAL, q);     // (OBJ 5's two colour sets: show_pal5, when a show starts; the level load is already a frame's work)
    } else if (is_cgb) {                        // every other venue (mode 3): the keg's BG 1 and, for a generated one (the Factory), its instances on BG 5 (reloaded early, line 31) and BG 6 (late, line 39)
        uint8_t s[6];
        chain_sel(s);
        if (s[2] || s[3] != 255) { split_arm(s[3] == 255 ? 0 : s[0], s[4] == 255 ? 0 : s[1], s[2]); chain_set(); }
    }
    lift_level_init(cur_group);                 // M13a: lifted-patron palettes, DMG copies, nobody lifted
    mirror_load(play_mode == MODE_LEVEL ? level_dirs : classic_dirs);   // P3: bars from the right (the harness, CLASSIC)
    place_start_patrons();
    half_decide();                              // 30 fps on the DMG for the heavy levels (src/half.c)
}

