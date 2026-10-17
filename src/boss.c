// The boss engine (docs/minigames_bosses.md 2.5, 3.1-3.3; step 2 of section 6): one engine, a parameter row per boss
// and a per-boss special hook. Only Big Tex (the saloon) has his row so far; an id without one plays Tex's.
//
// A fight is the venue's level in story mode (story.c step_start -> boss_set, then shift_start as for a shift, with the
// fight's banner and pace from boss_goal / boss_begin). The bar game runs as usual on the other bars (regulars, the
// bartender, mugs, fair empties, lives); the boss is one more actor on his own bar:
//   - He is a BG figure (no sprite on his lines): W x 16 px on his bar's two wall rows, behind the counter like a
//     patron, stamped by render.c's compose_bar after the bar's patrons (boss_cols, from his pose). Only his topper
//     (the hat's crown) is a sprite: one 8x16 OBJ whose upper half sticks out above his bar (boss_draw).
//   - He stomps 8 px nearer the tap every `step` frames (the STOMP pose for STOMP_FRAMES). His right edge at the tap
//     end (SPOUT_X) costs a life; after the freeze he starts again at his start x, his meter kept (boss_reset).
//   - A full mug on his bar reaching boss_x + W - CATCH_DX is caught (patrons.c catch_full -> boss_catch), unless his
//     hands are full (`hands` empties held): then it slides on past him and breaks at the left end. A catch: meter -1,
//     the serve score (and a perfect pour's bonus), push-back `push` px in 8 px hops (one per HOP_FRAMES; the WINCE
//     pose), the GULP pose until `gulp` frames are over (no stomp meanwhile), and one more empty held.
//   - Each held empty goes back up his bar `sip` frames after the last one (or the first catch), and only when the
//     fair-empties schedule allows (patrons.c next_arrival / empty_gap, the same rule as a patron's, at the empties'
//     0.5 px a frame). His pose's hand column shows the empties he holds (0-3).
//   - Meter 0: story_play hands over to the outro (story.c SP_OUTRO, boss_outro: the HAPPY pose, the mugs gone, the
//     regulars frozen), then CHAPTER CLEAR as a shift's. Lives 0: TRY AGAIN and the venue restarts at its Opening (the
//     owner's lives rule: 3 per venue, carried into the fight; the next fight starts with a full meter).
//   - Regulars: the level row's speeds on the other bars, the spawn interval x BOSS_SPAWN_PCT %, their bars in an order
//     drawn at the fight's start (the story's arrival pattern, never his bar), variants A and B only (variant C's tiles
//     are his: patrons.c try_spawn, show.c place_start_patrons), no tips and so no show (tip_chance 0).
// Resources borrowed (the next level load puts every one back, as after a mini-game): BG ids 162-203 and 216-233
// (variant C's shifted tiles, its shift-0 pose and the back views: no variant C, no show) for his body, 252-255 for
// the HUD's face and meter, 246-251 for a special's extra tiles; OBJ 96-99 (the show performers') for the topper at
// OAM 28 (the dancers' first entry); CGB BG palette 4 (variant C's; colour 0 = the venue's wall) and OBJ palette 7
// (lifted variant C's: the same colours 1-3); DMG: the BG greys and OBP1 0xE4 as the lifted patrons. The HUD: column 12
// his face, 13-19 the meter (2 pips a tile).
//
// Each boss is a row of rows[] (his numbers) and a row of the hook table (boss_call: his dispatcher in his own banked
// file src/boss_<name>.c, with his art and his special; src/boss.h lists the events). The engine works the same for
// all of them; a special changes it only through the hooks and the few WRAM knobs in boss.h (boss_xpose, boss_queue /
// boss_cap, boss_own_gap, boss_window, boss_fast_full / boss_fast_empty / boss_returns for his bar's mugs) and, for the
// bosses that move (wave 2), boss_to_bar / boss_mark / boss_pattern, the BS_JUMP state, the BP_HIDE pose and the
// topper's look (BOSS_TOPPER_T / BOSS_TOPPER_PAL).
#pragma bank 255
#include <gb/gb.h>
#include <gb/cgb.h>
#include <stdint.h>
#include <string.h>

#include "game.h"
#include "music.h"
#include "palettes.h"
#include "story.h"
#define BOSS_WANT_METER      // (boss_art.h: this module draws the meter)
#include "boss.h"            // the engine's inside, shared with the boss files (src/boss_<name>.c)
#include "boss_tag_art.h"    // the status tag's tiles (E1)

extern uint8_t pat_pos, pat_buf[STORY_PAT_MAX];   // (story.c) the arrival pattern patrons.c follows while pat_len
extern uint16_t pat_wait[4];
extern uint8_t overlay_on;

#define G_BOSS            3       // story_goal.type of a fight (story.h: G_SERVE 0, G_CATCH 1, G_CLEAR 2)
#define BOSS_SPAWN_PCT  150       // the regulars' spawn interval in a fight (owner Q10: they keep coming, more slowly)
#define BOSS_TAP_X      SPOUT_X   // his right edge here: a life
#define CATCH_DX          4       // a full mug is caught at boss_x + W - CATCH_DX
#define HOP_FRAMES        4       // push-back: one 8 px hop per HOP_FRAMES
#define STOMP_FRAMES      8       // the STOMP pose after each stomp
#define OUTRO_FRAMES    120
#define CLEAR_BANNER_FRAMES 90   // "CLEAR THE BAR" stays this long once he is beaten and regulars remain
#define OAM_TOPPER      OAM_DANCERS   // (no show in a fight; OAM 26 is the perfect pour's cue)
// E9: the fight opens as a normal shift (the warm-up), then the boss enters (docs/minigames_bosses.md 2.6)
#define WARM_FRAMES   1200        // the warm-up: 20 s of play after the intro (Story and ARCADE; Boss Rush has none)
#define WARM_AVOID     300        // the last 5 s: no new regular for his bar, so it empties before he comes
#define WARM_WAIT      180        // after the warm-up: up to 3 s more for his bar to empty and the mugs to land
#define WALK_STEP        6        // the fallback entrance: frames per 8 px he walks in from the left edge

enum { HOOK_NONE, HOOK_TELL, HOOK_METER_1, HOOK_DEFEAT, HOOK_FIGHT, HOOK_ENTER, HOOK_WALKIN };   // boss_hook (tests; any but HOOK_ENTER in the
                                                                                    // warm-up / entrance = the fight starts now, no entrance)

typedef struct {
    uint8_t width;        // px: 32 or 40 (BOSS_W_MAX columns)
    uint8_t start_x;      // px, a multiple of 8 (also how far the push-back takes him)
    uint8_t bar;          // his bar
    uint8_t step;         // frames per 8 px stomp
    uint8_t push;         // px pushed back per catch
    uint8_t gulp;         // frames of the gulp (no stomp)
    uint8_t hands;        // empties he can hold
    uint8_t sip;          // frames before each held empty may go
    uint8_t meter;        // drinks to satisfy him (<= 14: 7 HUD tiles)
    uint8_t hat_dx;       // the topper's x from his left edge
    uint8_t sway;         // his drinking sway (gen_boss: BOSS_ART_SWAY, boss_art_sway): 1 right, 2 left, 0 none (the Sumo)
    const char *line1, *line2;   // the banner's goal lines (HUD glyphs, <= 20)
} boss_row_t;

// One row per venue (boss id = the venue / chapter index). width 0: not built yet, the fight plays row 0's.
static const boss_row_t rows[BOSS_COUNT] = {
    // width x  bar step push gulp hands sip meter hat sway
    [0] = {  40,  16,  1, 120,  16,  58,   3,  60,  8,   16,  1, "BIG TEX RIDES IN", "QUENCH HIM 8 MUGS" },   // Saloon: Big Tex (3.3)
    [2] = {  32,  16,  2,  90,   8,  20,   2,   0, 12,   12,  0, "NO SUCH THING", "12 COFFEES FAST" },      // Lumber lodge: Sasquatch (3.5)
    [3] = {  32,  16,  1, 110,  16,  84,   1,  90,  8,    9,  1, "THE CRITIC DINES", "PERFECT POURS ONLY" }, // Bistro: the Food Critic (3.6)
    [1] = {  32,  16,  1, 100,   8,  34,   2,  45, 10,    8,  1, "THE MASCOT JUMPS", "FOLLOW HIM 10 MUGS" },   // Stadium: the Mascot (3.4)
    [4] = {  32,  16,  2, 100,   8,  44,   2,  60, 12,    9,  1, "THE YETI IS COLD", "12 COCOAS ON ICE" },   // Igloo: the Yeti (3.7)
    [5] = {  32,  16,  2, 100,   8,  30,   2,  45, 12,    8,  1, "GREEN MEANS GO", "RED MEANS STOP" },   // Robot factory: the Prototype (3.8)
    [6] = {  40,  16,  1,   0,  16,  30,   2,  45, 12,   16,  2, "THE BIGGEST SHAKE", "12 MILKS FOR DUKE" },   // Biker bar: Duke (3.12; step 0: he never stomps)
    [7] = {  40,  24,  1, 192,   0,   0,   2,  90,  6,   16,  0, "THE CHAMPION", "PUSH HIM OUT" }, // Teahouse: the Sumo (3.9)
    [8] = {  32,  16,  2,  80,   8,  44,   2,  60, 14,    6,  1, "LEO THE LION", "14 COCONUTS NO FEAR" },  // Jungle zoo: Leo (3.11)
    [9] = {  40,  16,  1, 100,   8,  34,   2,  45, 14,   12,  1, "THE MOTHERSHIP", "IT SPLITS WHEN FULL" },  // Space lounge: the Mothership (3.10; meter 8 + 6)
};

// ---- state (test hooks: spec 2.5's names) ----
uint8_t  boss_on;                 // a fight is on (story; boss_set)
uint8_t  boss_id;                 // the venue whose boss it is
uint8_t  boss_bar;                // his bar (BOSS_NONE: no fight; the ROM0 hooks compare against it)
uint8_t  boss_x;                  // px of his left edge, a multiple of 8
uint8_t  boss_hp;                 // the meter: drinks still to go
uint8_t  boss_hold;               // empties in his hands
uint8_t  boss_state;              // BS_*
uint8_t  boss_t;                  // frames in the state (stops at 255)
uint16_t boss_special_t;          // frames to the next special (no special yet: 0)
uint8_t  boss_hook;               // test poke: HOOK_*
uint8_t  boss_lim;                // a full mug on his bar at mug_x < boss_lim is his (0: hands full / none)
uint8_t  boss_col, boss_pal, boss_cols[BOSS_W_MAX];   // render.c's stamp: columns, palette, top tile per column
uint8_t  boss_pose;               // pose | the empties shown << 4 (255: redraw)
uint8_t  boss_push;               // px of push-back still to hop
uint8_t  boss_hits;               // drinks caught this fight (tests)
uint8_t  boss_hard;               // Practice's HARD toggle (owner Q7): stomps a quarter faster, one hand fewer
uint8_t  boss_step, boss_hands;   // this fight's step and hands (the row's, or HARD's)
uint8_t  boss_xpose;              // a special's extra pose (BP_EXTRA..; 0 none: src/boss.h)
uint8_t  boss_queue, boss_cap;    // held besides his empties (the Critic's returns); he catches while hold + queue < cap
uint8_t  boss_sip_t;              // frames since his last empty went
uint8_t  boss_own_gap;            // his own empties' gap after his own (0: empty_gap)
uint16_t boss_window;             // his empties / returns must arrive within this many frames (0xFFFF: no limit)
uint8_t  boss_fast_full, boss_fast_empty, boss_returns;   // his bar's fast mugs, MUG_RETURNs (boss_mugs)
static uint8_t boss_hop, boss_step_t, boss_stomp, boss_hat, boss_row;
static uint16_t boss_own_na;      // next_arrival as his last empty left it (still equal: nobody scheduled one since)
static uint8_t hud_row[8];
static const boss_row_t *br;

// The hook table: one row per built boss (the row index = his rows[] index), his dispatcher in his own file
// (src/boss_<name>.c, banked; the events: src/boss.h). A row of rows[] needs its row here too (his art is there).
static uint8_t boss_call(uint8_t ev, uint8_t arg) {
    switch (boss_row) {
    case 0: return boss_big_tex(ev, arg);        // Saloon: src/boss_big_tex.c
    case 1: return boss_mascot(ev, arg);         // Stadium: src/boss_mascot.c
    case 2: return boss_sasquatch(ev, arg);      // Lumber lodge: src/boss_sasquatch.c
    case 3: return boss_critic(ev, arg);         // Bistro: src/boss_critic.c
    case 4: return boss_yeti(ev, arg);           // Igloo: src/boss_yeti.c
    case 5: return boss_prototype(ev, arg);      // Robot factory: src/boss_prototype.c
    case 6: return boss_duke(ev, arg);           // Biker bar: src/boss_duke.c
    case 7: return boss_sumo(ev, arg);           // Teahouse: src/boss_sumo.c
    case 8: return boss_leo(ev, arg);            // Jungle zoo: src/boss_leo.c
    case 9: return boss_mothership(ev, arg);     // Space lounge: src/boss_mothership.c
    }
    return 0;
}

static uint8_t pair_id(uint8_t p) {
    return p < BOSS_PAIRS_A ? BOSS_BG_A + (p << 1) : BOSS_BG_B + ((uint8_t)(p - BOSS_PAIRS_A) << 1);
}

// The HUD's face and meter (columns 12-19): through the VBlank queue, or straight to VRAM with the LCD off.
static void boss_hud(void) {
    uint8_t k, hp = boss_hp, n = (br->meter + 1) >> 1, t;
    hud_row[0] = BOSS_HUD_BG;
    for (k = 0; k < 7; k++) {
        t = TILE_HUD_BLANK;
        if (k < n) {
            t = hp >= 2 ? BOSS_HUD_BG + 3 : hp ? BOSS_HUD_BG + 2 : BOSS_HUD_BG + 1;
            hp = hp >= 2 ? hp - 2 : 0;
        }
        hud_row[1 + k] = t;
    }
    if (LCDC_REG & LCDCF_ON) vq_add(0, hud_row, 12, HUD_ROW, 8); else vram_put(12, HUD_ROW, hud_row, 8);
}

// The drinking shake (owner 2026-10-17: "use the same technique that we use with patrons"): the patrons sway 2 px every
// SWAY_FRAMES while they drink, by drawing a pre-shifted copy of their tiles. A boss does the same: gen_boss makes one extra
// pose of his GULP shifted 2 px (BP_SWAY, boss_art_sway: its own column pairs), and while he drinks the body alternates GULP
// and BP_SWAY on the patrons' beat, the mug staying up; the topper (a sprite) moves with it (sway_dx). The tag stays put.
// Only in the common gulp (no push-back, no special's pose over it). br->sway 0: no shifted pose (his column pairs are
// full: the Sasquatch, whose 20-frame gulp keeps E1's mug-down beat; the Sumo never gulps).
static uint8_t sip_beat(void) {
    return boss_state == BS_GULP && !boss_push && !boss_xpose && sway_tab[boss_t];   // (boss_t < gulp: the table is (t / SWAY_FRAMES) & 1, no divide)
}

// His pose from his state: the body's columns (boss_cols) and, when they changed, their tiles queued.
static void boss_look(void) {
    uint8_t p = BP_WALK, h, key, k, w = br->width >> 3;
    const uint8_t *m;
    if (boss_state == BS_OUTRO) p = boss_xpose == BP_HIDE ? BP_HIDE : BP_HAPPY;   // (the Mothership's minis: no saucer left to be happy)
    else if (boss_push) p = BP_WINCE;
    else if (boss_xpose) p = boss_xpose;
    else if (boss_state == BS_GULP) p = sip_beat() ? (br->sway ? BP_SWAY : BP_WALK) : BP_GULP;   // (the drinking sway, above)
    else if (boss_stomp) p = BP_STOMP;
    h = (p == BP_WALK || p == BP_STOMP || p == BP_WINCE) ? (boss_hold > 3 ? 3 : boss_hold) : 0;
    key = p | (h << 4);
    if (key == boss_pose) return;
    if (p == BP_HIDE || (boss_pose & 15) == BP_HIDE) {   // (a moving boss: gone from his spot, or back: the wall's
        boss_pose = key;                                  // own attributes there, then his)
        for (k = 0; k < BOSS_W_MAX; k++) boss_cols[k] = p == BP_HIDE || k >= w ? 0 : pair_id(boss_map[p * BOSS_W_MAX + k]);
        if (h) boss_cols[w - 1] = pair_id(boss_hand[h]);
        mark_dirty_attrs(boss_bar, boss_col, boss_col + w);
        return;
    }
    boss_pose = key;
    m = boss_map + p * BOSS_W_MAX;
    for (k = 0; k < w; k++) boss_cols[k] = pair_id(m[k]);
    if (h) boss_cols[w - 1] = pair_id(boss_hand[h]);   // (columns w.. are his special's: boss_set clears them)
    mark_dirty(boss_bar, boss_col, boss_col + w);
}

void boss_hud_now(void) BANKED {
    boss_hud();
}

static void boss_move(uint8_t x) {
    uint8_t oc = boss_col, nc = x >> 3, w = br->width >> 3;
    boss_x = x; boss_col = nc;
    if (nc < oc) mark_dirty_attrs(boss_bar, nc, oc + w);
    else mark_dirty_attrs(boss_bar, oc, nc + w);
}

static void boss_limit(void) {
    boss_lim = boss_hp && boss_state < BS_JUMP && boss_hold + boss_queue < boss_cap   // (away or satisfied: none)
             ? boss_x + br->width - (CATCH_DX - 1) : 0;
}

// Story step_start: the step about to begin is venue id's boss fight (a full meter), or (BOSS_NONE) no fight: the
// regulars' tips come back. Nothing on screen yet (the level load follows: boss_load, boss_reset).
void boss_set(uint8_t id) BANKED {
    uint8_t s;
    if (id == BOSS_NONE) {
        if (boss_on) tip_chance = TIP_CHANCE_DEFAULT;
        boss_on = 0; boss_bar = BOSS_NONE; boss_lim = 0;
        return;
    }
    boss_id = id;
    boss_row = id < BOSS_COUNT && rows[id].width ? id : 0;
    br = &rows[boss_row];
    boss_on = 1; boss_bar = br->bar;
    boss_hp = br->meter; boss_hits = 0; boss_special_t = 0; boss_hook = HOOK_NONE;
    s = br->step; boss_hands = br->hands;
    if (boss_hard) { s -= s >> 2; if (boss_hands > 1) boss_hands--; }
    boss_step = s;
    boss_state = BS_WALK; boss_hold = 0; boss_push = 0; boss_stomp = 0;
    boss_x = br->start_x; boss_col = boss_x >> 3; boss_pose = 255;
    for (s = 0; s != BOSS_W_MAX; s++) boss_cols[s] = 0;
    boss_xpose = 0; boss_queue = 0; boss_cap = boss_hands; boss_own_gap = 0; boss_window = 0xFFFF;
    boss_fast_full = boss_fast_empty = boss_returns = 0;
    BOSS_MARK_BAR = BOSS_NONE; BOSS_TOPPER_T = 0; BOSS_TOPPER_PAL = 0;   // (story_scratch: game.h BOSS_FX)
    boss_call(BEV_SET, 0);                       // his art's pose table, his own settings
    // E9: the fight opens as a normal shift: BS_WARM, his bar is a bar like the others (BOSS_NONE: the ROM0 hooks see no
    // boss) until he enters. Boss Rush skips the warm-up: his bar stays free of regulars but he is not on it (HIDE) and the
    // entrance starts on the first frame.
    boss_state = BS_WARM; boss_t = 0; boss_lim = 0;
    if (play_mode == MODE_RUSH) { boss_special_t = 1; boss_t = WARM_WAIT; boss_xpose = BP_HIDE; boss_look(); }
    else { boss_special_t = WARM_FRAMES; boss_look(); boss_bar = BOSS_NONE; }
}

// enter_level_screen, LCD off, after start_level (which loaded every patron variant): his body over variant C's tiles
// and the back views, the HUD's face and meter, the topper's frames; CGB his palettes (colour 0 the venue's wall).
void boss_load(void) BANKED {
    set_sprite_data(OBJ_TAG, 4, boss_tag_tiles);  // the status tag's tiles (first: a boss file's pool over 124-127 is then his own)
    boss_call(BEV_LOAD, 0);                      // his body, face, topper and palettes (src/boss_load.h), his extras
    set_bkg_data((uint8_t)(BOSS_HUD_BG + 1), 3, boss_meter_tiles);
    boss_pal = BOSS_PAL;
}

// reset_actors (the level's start, and after a lost life): at his start x on his bar, nothing in his hands, his meter
// kept; the whole bar recomposed (he may have been anywhere).
void boss_reset(void) BANKED {
    if (boss_state >= BS_WARM) return;           // (E9: the warm-up and the entrance: nothing of his yet; fight_start resets him)
    boss_x = br->start_x; boss_col = boss_x >> 3;
    if (boss_state != BS_OUTRO) boss_state = BS_WALK;
    boss_t = 0; boss_push = 0; boss_hop = 0; boss_hold = 0; boss_step_t = 0; boss_sip_t = 0; boss_stomp = 0; boss_hat = 0;
    boss_pose = 255; boss_queue = 0; boss_own_na = 0;
    boss_call(BEV_RESET, 0);
    boss_look();
    mark_dirty_attrs(boss_bar, 0, 20);
    boss_limit();
    shadow_OAM[OAM_TOPPER].y = 0; shadow_OAM[OAM_TAG].y = 0;
}

void boss_tag_stage(uint8_t *dst) BANKED {
    memcpy(dst, boss_tag_tiles, BOSS_TAG_BYTES);
}

// story shift_start: the fight's goal_t (its banner lines, the pace: the row's walk, spawns x BOSS_SPAWN_PCT %)
void boss_goal(uint8_t *dst) BANKED {
    goal_t *g = (goal_t *)dst;
    const char *s;
    uint8_t i;
    g->type = G_BOSS; g->count = br->meter; g->flags = 0; g->secs = 0; g->twist = 0; g->pattern = 0;
    g->walk = 100; g->spawn = BOSS_SPAWN_PCT; g->quota = 0; g->pad = 0;
    for (s = br->line1, i = 0; *s; ) g->line1[i++] = *s++;
    g->line1[i] = 0;
    for (s = br->line2, i = 0; *s; ) g->line2[i++] = *s++;
    g->line2[i] = 0;
}

// story shift_start, after shift_pace (LCD on, the banner up): the regulars come to the other bars in an order drawn
// now (the story's arrival pattern, one per spawn interval), no tips (no show), the HUD's face and meter.
void boss_begin(void) BANKED {
    uint8_t i, b;
    tip_chance = 0;
    for (i = 0; i < STORY_PAT_MAX; i++) {
        do b = next_rand() & 3; while (b == boss_bar);
        pat_buf[i] = b;                          // (wait code 0: the interval)
    }
    pat_len = STORY_PAT_MAX; pat_pos = 0; pat_bar = pat_buf[0];
    pat_wait[0] = spawn_interval;                // (his face, meter and BEV_BEGIN: fight_start, when he has entered)
}

// patrons.c catch_full: full mug i reached him (on his bar, mug_x < boss_lim: a hand free). He drinks it.
uint8_t boss_catch(uint8_t i) BANKED {
    if (boss_call(BEV_CATCH, i)) { boss_limit(); return 1; }   // his special took it
    perfect_catch(i);                            // (a fight is story mode: a perfect pour scores its bonus and cue)
    mug_state[i] = MUG_FREE;
    add_score(serve_score);
    SFX(SFX_SERVE);
    if (!boss_hold++) boss_sip_t = 0;
    boss_push += br->push;
    boss_state = BS_GULP; boss_t = 0;
    if (boss_hp) boss_hp--;
    boss_hits++;
    boss_hud();
    boss_limit();
    return 1;
}

// ---- E9: the warm-up and the entrance ----
// The fight starts as the shift it is built on: BS_WARM, boss_special_t counts WARM_FRAMES down (after the level's intro),
// the regulars come to every bar (boss_bar is BOSS_NONE: the ROM0 hooks, the render and the patrons see a plain bar). In the
// last WARM_AVOID frames no new regular is bound for his bar; when the time is up the entrance waits (WARM_WAIT frames at the
// most) until his bar is empty and no mug is in the air, then entrance_start: the world is cleared of mugs, any straggler on
// his bar is gone, intro_timer freezes the bar (BEV_INTRO / BEV_DRAW run), his entrance plays (BEV_ENTER: his own, or the
// fallback walk-in), and fight_start puts the banner up and the boss rules apply. Boss Rush: no warm-up (boss_set).
static uint8_t bar_busy(void) {
    uint8_t p;
    for (p = 0; p != MAX_PATRONS; p++)
        if (patron_state[p] != PATRON_NONE && (patron_bar[p] & (NUM_BARS - 1)) == br->bar) return 1;
    return 0;
}

// He is on his bar now: it is his (stragglers vanish), recomposed.
static void take_bar(void) {
    uint8_t p;
    boss_bar = br->bar;
    for (p = 0; p != MAX_PATRONS; p++)
        if (patron_state[p] != PATRON_NONE && (patron_bar[p] & (NUM_BARS - 1)) == boss_bar) remove_patron(p);
    mark_dirty_attrs(boss_bar, 0, 20);
}

// The fight is on: his meter and face, the rules (BEV_RESET, BEV_BEGIN), the regulars never on his bar. shown: after an
// entrance (the intro's beat: nothing moves for a moment); 0: a test hook, straight to the fight.
static void fight_start(uint8_t shown) {
    if (boss_bar != br->bar) take_bar();
    boss_state = BS_WALK; boss_xpose = 0; boss_special_t = 0;
    boss_reset();
    boss_pattern(BOSS_NONE);
    boss_hud();
    boss_call(BEV_BEGIN, 0);
    if (shown && !intro_timer) intro_timer = INTRO_FRAMES - 1;   // (the beat before the first drink: nothing moves)
}

static void entrance_start(void) {
    uint8_t k;
    clear_mugs(); fill_timer = 0; fill_stage = 0; cue_t = 0; catch_pose = 0;
    take_bar();
    boss_hop = bartender_x; boss_step_t = bar; boss_hat = facing;   // (where the bartender is: held there meanwhile, boss_pre; boss_reset clears all three)
    boss_state = BS_ENTER; boss_xpose = BP_HIDE; boss_hold = 0; boss_t = 0;
    boss_to_bar(boss_bar, br->start_x);          // (his bar's regulars are gone: it recomposes without him; his own entrance shows him there)
    intro_timer = INTRO_FRAMES;                  // the bar holds still: his entrance owns the screen
    SFX(SFX_WHOOSH);
    k = boss_hook == HOOK_WALKIN; boss_hook = HOOK_NONE;   // (the test hook: the engine's own walk-in, whoever he is)
    if (k || !boss_call(BEV_ENTER, 0)) {         // (no entrance of his own: he walks in from the left edge)
        boss_state = BS_WALKIN; boss_special_t = 0;
        boss_x = 0; boss_col = 0;
    }
}

// boss_frame, in BS_WARM / BS_ENTER / BS_WALKIN
static void boss_pre(void) {
    uint8_t n, w = br->width >> 3, st = boss_state, k;
    if (st == BS_WARM) {
        if (boss_special_t > 1) {
            if (!intro_timer && --boss_special_t == WARM_AVOID) boss_pattern(br->bar);
        } else if (boss_t < WARM_WAIT && (mugs_live || bar_busy())) boss_t++;
        else entrance_start();
        return;
    }
    bar = boss_step_t; bartender_x = boss_hop; facing = boss_hat; bartender_frac = 0;   // (the player's input is held: he stays where he was)
    fill_timer = 0; fill_stage = 0;
    if (st == BS_ENTER) {                        // his own entrance (BEV_INTRO holds intro_timer; it ends by leaving BS_ENTER)
        boss_call(BEV_INTRO, 0);
        if (boss_state != BS_ENTER) fight_start(1);
        else boss_look();                        // (a special's own poses: the Sasquatch's burst)
        return;
    }
    // the fallback: he walks in from the left edge, 8 px every WALK_STEP frames: first his body comes on screen column by
    // column (the right end of his pose first), then he steps on to his start x with the stomp's thud
    intro_timer = INTRO_FRAMES;
    fill_timer = 0; fill_stage = 0;
    n = boss_special_t / WALK_STEP;
    if (!(boss_special_t++ % WALK_STEP)) {
        if (n < w) {                             // n + 1 columns are in: his pose's last n + 1 columns, at the screen's left edge
            for (k = 0; k != BOSS_W_MAX; k++)
                boss_cols[k] = k <= n ? pair_id(boss_map[BP_WALK * BOSS_W_MAX + w - 1 - n + k]) : 0;
            if (n + 1 == w) { boss_xpose = 0; boss_pose = 255; }   // (complete: the engine draws him from here on)
            mark_dirty_attrs(boss_bar, 0, w + 3);
            SFX(SFX_SHAKE);
        } else if (boss_x < br->start_x) {
            boss_move(boss_x + 8);
            boss_stomp = STOMP_FRAMES;
            SFX(SFX_SHAKE);
        } else {                                 // there: the fight
            intro_timer = INTRO_FRAMES - 1;
            fight_start(1);
            return;
        }
    }
    if (boss_stomp) boss_stomp--;
    boss_look();
}

static void boss_take_hook(void) {
    if (boss_state >= BS_WARM) {                 // (E9 test pokes: HOOK_ENTER ends the warm-up, any other hook starts the fight now)
        if (boss_hook == HOOK_ENTER || boss_hook == HOOK_WALKIN) {
            if (boss_state == BS_WARM) { boss_special_t = 1; boss_t = WARM_WAIT; }
            if (boss_hook == HOOK_ENTER) boss_hook = HOOK_NONE;   // (WALKIN stays until entrance_start has taken it)
            return;
        }
        fight_start(0);
        if (boss_hook == HOOK_FIGHT) { boss_hook = HOOK_NONE; return; }
    }
    if (boss_hook == HOOK_METER_1) boss_hp = 1;
    else if (boss_hook == HOOK_DEFEAT) boss_hp = 0;
    else if (boss_hook == HOOK_TELL) boss_call(BEV_TELL, 0);   // (a boss without a special ignores it)
    boss_hook = HOOK_NONE;
    boss_hud();
}

// One 8 px stomp toward the tap now (the STOMP pose, the thud), for a special that moves him itself (boss_step 0 turns
// the engine's own stomp timer off: the Sumo on the beat, and his charge). From BEV_FRAME: the tap check follows it.
void boss_advance(void) BANKED {
    boss_move(boss_x + 8);
    boss_stomp = STOMP_FRAMES;
    SFX(SFX_SHAKE);
}

uint8_t boss_width(void) BANKED {
    return br->width;
}

// One empty (or a Critic's return) from his right edge, when the fair-empties schedule lets it arrive at the tap end
// no sooner than empty_gap after the last one scheduled (after his own last one: boss_own_gap, when he has one), and
// within boss_window. Its travel at its speed: an empty 0.5 px a frame, 1 while boss_fast_empty (boss_mugs);
// a return always 1. 1 = sent.
uint8_t boss_send(uint8_t kind) BANKED {
    uint8_t ex, tap = bar_tap[boss_bar];
    uint16_t t, need = next_arrival;
    ex = boss_x + br->width;
    t = ex >= tap ? 0 : (uint16_t)(uint8_t)(tap - ex) * EMPTY_STEP_FRAMES;
    if (kind != MUG_EMPTY || boss_fast_empty) t >>= 1;
    if (boss_own_gap && need && need == boss_own_na)     // his own was the last one scheduled: his own gap after it
        need = need > (uint8_t)(empty_gap - boss_own_gap) ? need - (uint8_t)(empty_gap - boss_own_gap) : 0;
    if (t < need || t > boss_window || !spawn_mug(boss_bar, ex, kind)) return 0;
    next_arrival = t + empty_gap;
    boss_own_na = next_arrival;
    return 1;
}

// ---- the bosses that move (wave 2: the Mascot's leap, the Prototype's ride; PLAN.md "Boss hooks as built") ----
// The regulars' arrivals (the story's pattern, wait code 0 in a fight) never go to his bar, nor to bar `also` (the bar
// he is about to land on: BOSS_NONE for none): those entries are drawn again, the next arrival's bar too.
void boss_pattern(uint8_t also) BANKED {
    uint8_t i, b;
    for (i = 0; i != STORY_PAT_MAX; i++) {
        b = pat_buf[i] & 3;
        while (b == boss_bar || b == also) b = next_rand() & 3;
        pat_buf[i] = (pat_buf[i] & 0xF0) | b;
    }
    pat_bar = pat_buf[pat_pos] & 3;
}

// The landing marker (the BOSS_MARK_BG tiles, his file loads them) on bar b's lower wall row at columns c, c + 1, over
// its patrons (render.c compose_bar); b = BOSS_NONE takes it away.
void boss_mark(uint8_t b, uint8_t c) BANKED {
    uint8_t ob = BOSS_MARK_BAR, oc = BOSS_MARK_COL;
    BOSS_MARK_BAR = b; BOSS_MARK_COL = c;
    if (ob < NUM_BARS) mark_dirty_attrs(ob, oc, oc + 2);
    if (b < NUM_BARS) mark_dirty_attrs(b, c, c + 2);
}

// He arrives on bar b at x (a multiple of 8): his old bar is recomposed without him, b with him. Spec 2.5: b's regulars
// are scared off, each sliding out to the left as a leaving patron (no score, not served; a mug in his hand goes with
// him; empties already sliding keep sliding), and no regular comes to b while he is there. His meter, hands (a held
// empty now goes from b, when the schedule allows) and timers go with him; full mugs left on his old bar slide on to
// its left end and break.
void boss_to_bar(uint8_t b, uint8_t x) BANKED {
    uint8_t ob = boss_bar, p, st;
    boss_bar = b; boss_x = x; boss_col = x >> 3; boss_pose = 255;
    if (ob != b) mark_dirty_attrs(ob, 0, 20);
    for (p = 0; p != MAX_PATRONS; p++) {
        st = patron_state[p];
        if (st == PATRON_NONE || st == PATRON_LEAVING || (patron_bar[p] & (NUM_BARS - 1)) != b) continue;
        patron_state[p] = PATRON_LEAVING;        // (patrons.c leaving_step lifts him and slides him out)
        patron_aux[p] = 0; patron_timer[p] = 0;
    }
    boss_pattern(BOSS_NONE);
    boss_look();
    boss_limit();
    if (ob != b) mark_dirty_attrs(b, 0, 20);
    else mark_dirty_attrs(b, boss_col, boss_col + (br->width >> 3));   // (his own bar again, Duke's entrance: only his columns changed)
}

// Held empties: the first one `sip` frames after it was caught (or after the last went), when boss_send lets it go.
static void boss_empties(void) {
    if (boss_sip_t < br->sip) { boss_sip_t++; return; }
    if (!boss_send(MUG_EMPTY)) return;
    boss_hold--;
    boss_sip_t = 0;
}

// His bar's mugs beyond the common rules, after update_mugs moved them this frame (so nothing outside a fight pays for
// it, and no ROM0): a fast full mug 1 px more (3 px a frame; its catch or fall is seen by the next frame's full_step),
// a fast empty 1 px on the frames its own step did not move it (1 px a frame), and every MUG_RETURN (a full drink sent
// back: 1 px a frame to the right, the bartender catches it as an empty, past the right end it breaks: a life) on any
// bar (a boss that moves may have left it behind).
static void boss_mugs(void) {
    uint8_t i, x, st, b, left = mugs_live;       // (the non-free slots: update_mugs counted them this frame; the loop stops after the last)
    if (!left || !(boss_fast_full | boss_fast_empty | boss_returns)) return;
    for (i = 0; i != MAX_MUGS && left; i++) {
        st = mug_state[i];
        if (st == MUG_FREE) continue;
        left--;
        x = mug_x[i]; b = mug_bar[i];
        if (st == MUG_RETURN) {
            mug_x[i] = ++x;
            if (x >= bartender_x && ((uint8_t)(x - bartender_x) < 16 || bartender_x == tap_now) && b == bar) {
                mug_state[i] = MUG_FREE;         // caught (mugs.c empty_step's rule)
                add_score(EMPTY_SCORE);
                SFX(SFX_CATCH);
                catch_pose = CATCH_POSE_FRAMES;
            } else if (x > BAR_MUG_END(b)) {     // off the tap end: it breaks (mugs.c break_mug)
                mug_state[i] = MUG_BREAKING;
                mug_timer[i] = 0;
                mug_events++;
                SFX(SFX_BREAK);
                lose_life();
            }
        } else if (b != boss_bar) continue;
        else if (st == MUG_FULL) {
            if (boss_fast_full && x >= MUG_END_X) mug_x[i] = x - 1;
        } else if (st == MUG_EMPTY) {
            if (boss_fast_empty && (mug_timer[i] & 1)) mug_x[i] = x + 1;
        }
    }
}

// story_play, every PLAYING frame of a fight (not the frame a life went): 1 = the meter is empty, the outro begins.
//
// The meter at 0 does not end the fight (owner, 2026-10-13): he is beaten (BS_OUTRO: the HAPPY pose or gone, his
// special told to stand down) and the fight goes on until patrons_live is 0 (every regular served or cleared). No
// regular spawns meanwhile (spawn_timer held), a patron at the tap still costs a life, and for CLEAR_BANNER_FRAMES the
// banner says what is left. BOSS RUSH plays the same path (story_play calls this for both). 1 = the bar is clear.
uint8_t boss_frame(void) BANKED {
    uint8_t x = boss_x;
    if (boss_hook) boss_take_hook();
    if (boss_state >= BS_WARM) { boss_pre(); return 0; }   // E9: the warm-up, his entrance
    if (!boss_hp) {
        if (boss_state != BS_OUTRO) {            // beaten now (boss_reset keeps BS_OUTRO after a life lost in the phase)
            boss_state = BS_OUTRO; boss_lim = 0; boss_t = 0;
            boss_call(BEV_OUTRO, 0);             // (a special's end state: the Yeti thaws, the Mascot lands, ...)
            boss_look();
            if (patrons_live) show_note("CLEAR THE BAR");   // (a note, not the banner: it never covers a bar)
        } else if (boss_t != 255 && ++boss_t == CLEAR_BANNER_FRAMES) end_note();
        if (!patrons_live) return 1;
        spawn_timer = 0xFFFF;                    // no new regulars
        boss_mugs();                             // (a Critic's returned drinks still fly)
        return 0;
    }
    if (boss_own_na) boss_own_na--;              // (counts down with next_arrival: patrons.c update_patrons)
    boss_mugs();
    if (!intro_timer) {                          // nothing moves before the level's intro is over
        if (boss_t != 255) boss_t++;
        if (boss_stomp) boss_stomp--;
        if (boss_push) {
            if (++boss_hop >= HOP_FRAMES) {
                boss_hop = 0;
                boss_push = boss_push > 8 ? boss_push - 8 : 0;
                if (x > br->start_x) x -= 8;
                else boss_push = 0;              // pinned at his start
            }
        } else if (boss_state == BS_GULP) {
            if (boss_t >= br->gulp) { boss_state = BS_WALK; boss_t = 0; }
        } else if (boss_state == BS_WALK && boss_step && ++boss_step_t >= boss_step) {   // (a tell or special: he
            // stands; boss_step 0: no stomp of the engine's, his special moves him with boss_advance)
            boss_step_t = 0;
            x += 8;
            boss_stomp = STOMP_FRAMES;
            SFX(SFX_SHAKE);                      // the thud
        }
        if (boss_hold && boss_state != BS_JUMP) boss_empties();   // (away from his bar: none goes)
        if (x != boss_x) boss_move(x);
        boss_call(BEV_FRAME, 0);                 // his special
    } else boss_call(BEV_INTRO, 0);              // (the intro: Duke's entrance holds intro_timer until he lands)
    boss_look();
    boss_limit();
    if ((uint8_t)(boss_x + br->width) >= BOSS_TAP_X) lose_life();   // at the tap: a life (boss_reset after the freeze)
    return 0;
}

// story_update, frame t (1..) of the outro (GS_STORY: nothing else moves): the mugs gone, the HAPPY pose, the hat
// bobbing; 1 when it is over (story.c: CHAPTER CLEAR).
uint8_t boss_outro(uint8_t t) BANKED {
    uint8_t i, n;
    if (t == 1) {                                // (BEV_OUTRO went at the start of the clear phase: boss_frame)
        end_note(); overlay_on = 0;
        clear_mugs();
        fill_timer = 0; cue_t = 0;
        n = OAM_MUG_END - 2 * lift_total;
        for (i = OAM_FILL; i < n; i++) shadow_OAM[i].y = 0;
        shadow_OAM[OAM_CUE].y = 0;
        SFX(SFX_SERVE);
    }
    if (!(t & 15)) {
        boss_hat ^= 2;
        if (shadow_OAM[OAM_TOPPER].y) shadow_OAM[OAM_TOPPER].tile = OBJ_TOPPER + boss_hat;
    }
    return t >= OUTRO_FRAMES;
}

// One entry near the topper: d = its y minus the topper's (-15..15 as a byte): the 4-line bands n[0..3] of the topper's 16 lines it touches.
static void band_add(uint8_t d, uint8_t *n) {
    int8_t r = (int8_t)d;
    if (r >= 0) { if (r < 4) n[0]++; if (r < 8) n[1]++; if (r < 12) n[2]++; n[3]++; }
    else { n[0]++; if (r >= -11) n[1]++; if (r >= -7) n[2]++; if (r >= -3) n[3]++; }
}

// pour_frame (every drawn frame of a fight, after every other sprite): the topper over his head, its upper half above
// his bar. Sprites per line: every other OAM entry is counted on the four 4-line bands of the topper's 16 lines it
// touches (an upper bound for each line: spec 3.1 counts the same bands); the topper is left out on a frame where a
// band already has LINE_OBJ_MAX, so it is never an 11th object on a line (the hat blinks off for those frames).
void boss_draw(void) BANKED {
    OAM_item_t *o = shadow_OAM;
    uint8_t k, top = bar_oam_y[boss_bar] - 8, n0, n1, n2, n3, hat, tag;
    uint8_t n[4];
    if (boss_state == BS_WARM) { shadow_OAM[OAM_TOPPER].y = 0; shadow_OAM[OAM_TAG].y = 0; return; }   // (E9: not here yet)
    if (intro_timer) boss_call(BEV_DRAW, 0);     // the intro: a special's own sprites (Duke's entrance) before the lines are counted
    shadow_OAM[OAM_TAG].y = 0;
    if (boss_state == BS_JUMP || boss_xpose == BP_HIDE) { shadow_OAM[OAM_TOPPER].y = 0; return; }   // (away: no hat in the air)
    shadow_OAM[OAM_TOPPER].y = 0;   // (so the count skips it and the tag: both are set again below)
    n[0] = n[1] = n[2] = n[3] = 0;
    k = 40;
    do {
        if (o->y) {
            // (the bartender's 4 entries hang BT_DY lower than the bands were laid out for: counted as before, so his
            // two pairs, which never share a line, are not both counted in the band that his top pair now just reaches)
            uint8_t y = o < shadow_OAM + 4 ? (uint8_t)(o->y - BT_DY) : o->y;
            if ((uint8_t)(y - top + 15) < 31) band_add(y - top, n);
        }
        o++;
    } while (--k);
    n0 = n[0]; n1 = n[1]; n2 = n[2]; n3 = n[3];
    o = shadow_OAM + OAM_TOPPER;
    hat = !(n0 >= LINE_OBJ_MAX || n1 >= LINE_OBJ_MAX || n2 >= LINE_OBJ_MAX || n3 >= LINE_OBJ_MAX);
    if (hat) {
        o->y = top; o->x = boss_x + br->hat_dx + 8 + (sip_beat() ? (br->sway == 2 ? -2 : 2) : 0);   // (drinking: moves with his body)
        o->tile = OBJ_TOPPER + (BOSS_TOPPER_T ? BOSS_TOPPER_T : (boss_pose & 15) == BP_STOMP ? 2 : 0);
        o->prop = !is_cgb ? S_PALETTE : BOSS_TOPPER_PAL ? BOSS_TOPPER_PAL : OBJPAL_PATRON_C;
    } else o->y = 0;
    // The status tag (E1): above his hand column, where a drink reaches him; the hat has the line budget first.
    if (intro_timer || !boss_hp || boss_state == BS_OUTRO) return;
    if (n0 + hat >= LINE_OBJ_MAX || n1 + hat >= LINE_OBJ_MAX || n2 + hat >= LINE_OBJ_MAX || n3 + hat >= LINE_OBJ_MAX) return;
    tag = boss_lim ? TAG_READY : TAG_BUSY;
    k = boss_call(BEV_TAG, tag);
    if (k) tag = k - 1;
    if (tag == TAG_OFF) return;
    o = shadow_OAM + OAM_TAG;
    o->y = top; o->x = boss_x + br->width + (tag == TAG_RETURN ? (frame_t0 & 4) - 2 : 0);
    o->tile = OBJ_TAG + (tag == TAG_READY ? 0 : 2);
    o->prop = !is_cgb ? S_PALETTE : OBJPAL_PATRON_C;
}
