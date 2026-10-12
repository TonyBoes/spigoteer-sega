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
// boss_cap, boss_own_gap, boss_window, boss_fast_full / boss_fast_empty / boss_returns for his bar's mugs).
#pragma bank 255
#include <gb/gb.h>
#include <gb/cgb.h>
#include <stdint.h>

#include "game.h"
#include "music.h"
#include "palettes.h"
#include "story.h"
#include "boss.h"            // the engine's inside, shared with the boss files (src/boss_<name>.c)

extern uint8_t pat_pos, pat_buf[STORY_PAT_MAX];   // (story.c) the arrival pattern patrons.c follows while pat_len
extern uint16_t pat_wait[4];

#define G_BOSS            3       // story_goal.type of a fight (story.h: G_SERVE 0, G_CATCH 1, G_CLEAR 2)
#define BOSS_SPAWN_PCT  150       // the regulars' spawn interval in a fight (owner Q10: they keep coming, more slowly)
#define BOSS_TAP_X      SPOUT_X   // his right edge here: a life
#define CATCH_DX          4       // a full mug is caught at boss_x + W - CATCH_DX
#define HOP_FRAMES        4       // push-back: one 8 px hop per HOP_FRAMES
#define STOMP_FRAMES      8       // the STOMP pose after each stomp
#define OUTRO_FRAMES    120
#define OAM_TOPPER      OAM_DANCERS   // (no show in a fight; OAM 26 is the perfect pour's cue)

enum { HOOK_NONE, HOOK_TELL, HOOK_METER_1, HOOK_DEFEAT };            // boss_hook (tests)

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
    uint8_t art;          // (0: his art is in his own file, src/boss_<name>.c)
    const char *line1, *line2;   // the banner's goal lines (HUD glyphs, <= 20)
} boss_row_t;

// One row per venue (boss id = the venue / chapter index). width 0: not built yet, the fight plays row 0's.
static const boss_row_t rows[BOSS_COUNT] = {
    // width x  bar step push gulp hands sip meter hat art
    [0] = {  40,  16,  1, 120,  16,  40,   3,  60,  8,   16,  0, "BIG TEX RIDES IN", "QUENCH HIM 8 MUGS" },   // Saloon: Big Tex (3.3)
    [2] = {  32,  16,  2,  90,   8,   8,   2,   0, 12,   12,  0, "NO SUCH THING", "12 COFFEES FAST" },      // Lumber lodge: Sasquatch (3.5)
    [3] = {  32,  16,  1, 110,  16,  60,   1,  90,  8,    9,  0, "THE CRITIC DINES", "PERFECT POURS ONLY" }, // Bistro: the Food Critic (3.6)
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
uint8_t  boss_map[BOSS_POSES_MAX][BOSS_W_MAX], boss_hand[4], boss_npose;   // his poses' column pairs (his file's art)
static uint8_t boss_hop, boss_step_t, boss_stomp, boss_hat, boss_row;
static uint16_t boss_own_na;      // next_arrival as his last empty left it (still equal: nobody scheduled one since)
static uint8_t hud_row[8];
static const boss_row_t *br;

// The hook table: one row per built boss (the row index = his rows[] index), his dispatcher in his own file
// (src/boss_<name>.c, banked; the events: src/boss.h). A row of rows[] needs its row here too (his art is there).
static uint8_t boss_call(uint8_t ev, uint8_t arg) {
    switch (boss_row) {
    case 0: return boss_big_tex(ev, arg);        // Saloon: src/boss_big_tex.c
    case 2: return boss_sasquatch(ev, arg);      // Lumber lodge: src/boss_sasquatch.c
    case 3: return boss_critic(ev, arg);         // Bistro: src/boss_critic.c
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

// His pose from his state: the body's columns (boss_cols) and, when they changed, their tiles queued.
static void boss_look(void) {
    uint8_t p = BP_WALK, h, key, k, w = br->width >> 3;
    const uint8_t *m;
    if (boss_state == BS_OUTRO) p = BP_HAPPY;
    else if (boss_push) p = BP_WINCE;
    else if (boss_xpose) p = boss_xpose;
    else if (boss_state == BS_GULP) p = BP_GULP;
    else if (boss_stomp) p = BP_STOMP;
    h = (p == BP_WALK || p == BP_STOMP || p == BP_WINCE) ? (boss_hold > 3 ? 3 : boss_hold) : 0;
    key = p | (h << 4);
    if (key == boss_pose) return;
    boss_pose = key;
    m = boss_map[p];
    for (k = 0; k < w; k++) boss_cols[k] = pair_id(m[k]);
    if (h) boss_cols[w - 1] = pair_id(boss_hand[h]);
    for (; k < BOSS_W_MAX; k++) boss_cols[k] = 0;
    mark_dirty(boss_bar, boss_col, boss_col + w);
}

static void boss_move(uint8_t x) {
    uint8_t oc = boss_col, nc = x >> 3, w = br->width >> 3;
    boss_x = x; boss_col = nc;
    if (nc < oc) mark_dirty_attrs(boss_bar, nc, oc + w);
    else mark_dirty_attrs(boss_bar, oc, nc + w);
}

static void boss_limit(void) {
    boss_lim = boss_hp && boss_state != BS_OUTRO && boss_hold + boss_queue < boss_cap
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
    boss_xpose = 0; boss_queue = 0; boss_cap = boss_hands; boss_own_gap = 0; boss_window = 0xFFFF;
    boss_fast_full = boss_fast_empty = boss_returns = 0;
    boss_call(BEV_SET, 0);                       // his art's pose table, his own settings
    boss_look();
}

// enter_level_screen, LCD off, after start_level (which loaded every patron variant): his body over variant C's tiles
// and the back views, the HUD's face and meter, the topper's frames; CGB his palettes (colour 0 the venue's wall).
void boss_load(void) BANKED {
    boss_call(BEV_LOAD, 0);                      // his body, face, topper and palettes (src/boss_load.h), his extras
    set_bkg_data(BOSS_HUD_BG + 1, 3, boss_meter_tiles);
    boss_pal = BOSS_PAL;
}

// reset_actors (the level's start, and after a lost life): at his start x on his bar, nothing in his hands, his meter
// kept; the whole bar recomposed (he may have been anywhere).
void boss_reset(void) BANKED {
    boss_x = br->start_x; boss_col = boss_x >> 3;
    if (boss_state != BS_OUTRO) boss_state = BS_WALK;
    boss_t = 0; boss_push = 0; boss_hop = 0; boss_hold = 0; boss_step_t = 0; boss_sip_t = 0; boss_stomp = 0; boss_hat = 0;
    boss_pose = 255; boss_queue = 0; boss_own_na = 0;
    boss_call(BEV_RESET, 0);
    boss_look();
    mark_dirty_attrs(boss_bar, 0, 20);
    boss_limit();
    shadow_OAM[OAM_TOPPER].y = 0;
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
    pat_wait[0] = spawn_interval;
    boss_hud();
    boss_call(BEV_BEGIN, 0);
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

static void boss_take_hook(void) {
    if (boss_hook == HOOK_METER_1) boss_hp = 1;
    else if (boss_hook == HOOK_DEFEAT) boss_hp = 0;
    else if (boss_hook == HOOK_TELL) boss_call(BEV_TELL, 0);   // (a boss without a special ignores it)
    boss_hook = HOOK_NONE;
    boss_hud();
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
// back: 1 px a frame to the right, the bartender catches it as an empty, past the right end it breaks: a life).
static void boss_mugs(void) {
    uint8_t i, x, st;
    if (!(boss_fast_full | boss_fast_empty | boss_returns)) return;
    for (i = 0; i != MAX_MUGS; i++) {
        if (mug_bar[i] != boss_bar) continue;
        st = mug_state[i]; x = mug_x[i];
        if (st == MUG_FULL) {
            if (boss_fast_full && x >= MUG_END_X) mug_x[i] = x - 1;
        } else if (st == MUG_EMPTY) {
            if (boss_fast_empty && (mug_timer[i] & 1)) mug_x[i] = x + 1;
        } else if (st == MUG_RETURN) {
            mug_x[i] = ++x;
            if (x >= bartender_x && ((uint8_t)(x - bartender_x) < 16 || bartender_x == tap_now) && boss_bar == bar) {
                mug_state[i] = MUG_FREE;         // caught (mugs.c empty_step's rule)
                add_score(EMPTY_SCORE);
                SFX(SFX_CATCH);
                catch_pose = CATCH_POSE_FRAMES;
            } else if (x > BAR_MUG_END(boss_bar)) {   // off the tap end: it breaks (mugs.c break_mug)
                mug_state[i] = MUG_BREAKING;
                mug_timer[i] = 0;
                mug_events++;
                SFX(SFX_BREAK);
                lose_life();
            }
        }
    }
}

// story_play, every PLAYING frame of a fight (not the frame a life went): 1 = the meter is empty, the outro begins.
uint8_t boss_frame(void) BANKED {
    uint8_t x = boss_x;
    if (boss_hook) boss_take_hook();
    if (!boss_hp) { boss_state = BS_OUTRO; boss_lim = 0; boss_look(); return 1; }
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
        } else if (boss_state == BS_WALK && ++boss_step_t >= boss_step) {   // (a tell or special: he stands)
            boss_step_t = 0;
            x += 8;
            boss_stomp = STOMP_FRAMES;
            SFX(SFX_SHAKE);                      // the thud
        }
        if (boss_hold) boss_empties();
        if (x != boss_x) boss_move(x);
        boss_call(BEV_FRAME, 0);                 // his special
    }
    boss_look();
    boss_limit();
    if ((uint8_t)(boss_x + br->width) >= BOSS_TAP_X) lose_life();   // at the tap: a life (boss_reset after the freeze)
    return 0;
}

// story_update, frame t (1..) of the outro (GS_STORY: nothing else moves): the mugs gone, the HAPPY pose, the hat
// bobbing; 1 when it is over (story.c: CHAPTER CLEAR).
uint8_t boss_outro(uint8_t t) BANKED {
    uint8_t i, n;
    if (t == 1) {
        boss_call(BEV_OUTRO, 0);
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

// pour_frame (every drawn frame of a fight, after every other sprite): the topper over his head, its upper half above
// his bar. Sprites per line: every other OAM entry is counted on the four 4-line bands of the topper's 16 lines it
// touches (an upper bound for each line: spec 3.1 counts the same bands); the topper is left out on a frame where a
// band already has LINE_OBJ_MAX, so it is never an 11th object on a line (the hat blinks off for those frames).
void boss_draw(void) BANKED {
    OAM_item_t *o = shadow_OAM;
    uint8_t k, top = bar_oam_y[boss_bar] - 8, n0 = 0, n1 = 0, n2 = 0, n3 = 0;
    int8_t r;
    for (k = 0; k != 40; k++, o++) {
        if (k == OAM_TOPPER || !o->y) continue;
        r = (int8_t)(uint8_t)(o->y - top);
        if (r > 15 || r < -15) continue;
        if (r >= 0) { if (r < 4) n0++; if (r < 8) n1++; if (r < 12) n2++; n3++; }
        else { n0++; if (r >= -11) n1++; if (r >= -7) n2++; if (r >= -3) n3++; }
    }
    o = shadow_OAM + OAM_TOPPER;
    if (n0 >= LINE_OBJ_MAX || n1 >= LINE_OBJ_MAX || n2 >= LINE_OBJ_MAX || n3 >= LINE_OBJ_MAX) { o->y = 0; return; }
    o->y = top; o->x = boss_x + br->hat_dx + 8;
    o->tile = OBJ_TOPPER + ((boss_pose & 15) == BP_STOMP ? 2 : 0);
    o->prop = is_cgb ? OBJPAL_PATRON_C : S_PALETTE;
}
