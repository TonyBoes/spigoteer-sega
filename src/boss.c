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
// the HUD's face and meter; OBJ 96-99 (the show performers') for the topper at OAM 28 (the dancers' first entry); CGB
// BG palette 4 (variant C's; colour 0 = the venue's wall) and OBJ palette 7 (lifted variant C's: the same colours 1-3);
// DMG: the BG greys and OBP1 0xE4 as the lifted patrons. The HUD: column 12 his face, 13-19 the meter (2 pips a tile).
#pragma bank 255
#include <gb/gb.h>
#include <gb/cgb.h>
#include <stdint.h>

#include "game.h"
#include "music.h"
#include "palettes.h"
#include "story.h"
#include "boss_art.h"        // this bank's own art (tools/gen_boss.py)

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
#define OBJ_TOPPER      OBJ_DANCER    // 4 tiles: STILL, BOB (8x16 each)
#define BOSS_BG_A       (PATRON_TILE_BASE + 84)   // variant C's 42 shifted tiles: 21 column pairs
#define BOSS_BG_B       (PATRON_OBJ_BASE + 12)    // variant C's shift-0 pose + the 12 back views: 9 pairs
#define BOSS_PAIRS_A    21
#define BOSS_HUD_BG     252                       // the face, then the meter's EMPTY, HALF, FULL
#define BOSS_PAL        (BGPAL_PATRON + 2)
#if BOSS_BG_A + 2 * BOSS_PAIRS_A != PATRON_OBJ_BASE || BOSS_BG_B + 18 != PATRON_BACK_BASE + 12 \
    || BOSS_PAIRS_A + 9 != BOSS_PAIRS_MAX || PATRON_BACK_BASE + 12 > OBJ_POUR || BOSS_HUD_BG < OBJ_DMG_COPY + 6
#error "boss tiles: variant C's 162-203, its shift-0 pose and the back views 216-233, the HUD 252-255"
#endif

enum { BS_WALK, BS_GULP, BS_TELL, BS_SPECIAL, BS_JUMP, BS_OUTRO };   // boss_state (spec 2.5's test hook names)
enum { BP_WALK, BP_STOMP, BP_GULP, BP_WINCE, BP_HAPPY };            // poses: the art's order (gen_boss POSES)
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
    uint8_t art;          // index in arts[]
    const char *line1, *line2;   // the banner's goal lines (HUD glyphs, <= 20)
} boss_row_t;

// One row per venue (boss id = the venue / chapter index). width 0: not built yet, the fight plays row 0's.
static const boss_row_t rows[BOSS_COUNT] = {
    // width x  bar step push gulp hands sip meter hat art
    {  40,  16,  1, 120,  16,  40,   3,  60,  8,   16,  0, "BIG TEX RIDES IN", "QUENCH HIM 8 MUGS" },   // Saloon: Big Tex (3.3)
};

typedef struct {
    const uint8_t *body; uint8_t pairs;
    const uint8_t *pose;  // [BOSS_POSES][width / 8] column pair indices
    const uint8_t *hand;  // [4] the hand column's pair holding 0..3 empties
    const uint8_t *hat, *icon;
    const uint16_t *pal;
} boss_art_t;
static const boss_art_t arts[BOSS_ARTS] = {
    { tex_body, TEX_PAIRS, &tex_pose[0][0], tex_hand, tex_hat, tex_icon, tex_pal },
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
static uint8_t boss_hop, boss_step_t, boss_sip_t, boss_stomp, boss_hat;
static uint8_t hud_row[8];
static const boss_row_t *br;
static const boss_art_t *ba;

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
    else if (boss_state == BS_GULP) p = BP_GULP;
    else if (boss_stomp) p = BP_STOMP;
    h = (p == BP_WALK || p == BP_STOMP || p == BP_WINCE) ? (boss_hold > 3 ? 3 : boss_hold) : 0;
    key = p | (h << 4);
    if (key == boss_pose) return;
    boss_pose = key;
    m = ba->pose + p * w;
    for (k = 0; k < w; k++) boss_cols[k] = pair_id(m[k]);
    if (h) boss_cols[w - 1] = pair_id(ba->hand[h]);
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
    boss_lim = boss_hp && boss_state != BS_OUTRO && boss_hold < boss_hands ? boss_x + br->width - (CATCH_DX - 1) : 0;
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
    br = &rows[id < BOSS_COUNT && rows[id].width ? id : 0];
    ba = &arts[br->art];
    boss_on = 1; boss_bar = br->bar;
    boss_hp = br->meter; boss_hits = 0; boss_special_t = 0; boss_hook = HOOK_NONE;
    s = br->step; boss_hands = br->hands;
    if (boss_hard) { s -= s >> 2; if (boss_hands > 1) boss_hands--; }
    boss_step = s;
    boss_state = BS_WALK; boss_hold = 0; boss_push = 0; boss_stomp = 0;
    boss_x = br->start_x; boss_col = boss_x >> 3; boss_pose = 255;
    boss_look();
}

// enter_level_screen, LCD off, after start_level (which loaded every patron variant): his body over variant C's tiles
// and the back views, the HUD's face and meter, the topper's frames; CGB his palettes (colour 0 the venue's wall).
void boss_load(void) BANKED {
    palette_t p;
    uint8_t n = ba->pairs;
    set_bkg_data(BOSS_BG_A, (n > BOSS_PAIRS_A ? BOSS_PAIRS_A : n) << 1, ba->body);
    if (n > BOSS_PAIRS_A) set_bkg_data(BOSS_BG_B, (n - BOSS_PAIRS_A) << 1, ba->body + BOSS_PAIRS_A * 32);
    set_bkg_data(BOSS_HUD_BG, 1, ba->icon);
    set_bkg_data(BOSS_HUD_BG + 1, 3, boss_meter_tiles);
    set_sprite_data(OBJ_TOPPER, 4, ba->hat);
    boss_pal = BOSS_PAL;
    if (!is_cgb) return;                         // (DMG: OBP1 is lift_level_init's 0xE4, the BG's shades)
    p[0] = venue.pal[VENUE_PAL_BAR][0];
    p[1] = ba->pal[1]; p[2] = ba->pal[2]; p[3] = ba->pal[3];
    set_bkg_palette(BOSS_PAL, 1, p);
    p[0] = 0;
    set_sprite_palette(OBJPAL_PATRON_C, 1, p);
}

// reset_actors (the level's start, and after a lost life): at his start x on his bar, nothing in his hands, his meter
// kept; the whole bar recomposed (he may have been anywhere).
void boss_reset(void) BANKED {
    boss_x = br->start_x; boss_col = boss_x >> 3;
    if (boss_state != BS_OUTRO) boss_state = BS_WALK;
    boss_t = 0; boss_push = 0; boss_hop = 0; boss_hold = 0; boss_step_t = 0; boss_sip_t = 0; boss_stomp = 0; boss_hat = 0;
    boss_pose = 255;
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
}

// patrons.c catch_full: full mug i reached him (on his bar, mug_x < boss_lim: a hand free). He drinks it.
uint8_t boss_catch(uint8_t i) BANKED {
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

// The per-boss special (spec section 3): Big Tex has none. Later bosses add a case on boss_id here.
static void boss_special(void) {
}

static void boss_take_hook(void) {
    if (boss_hook == HOOK_METER_1) boss_hp = 1;
    else if (boss_hook == HOOK_DEFEAT) boss_hp = 0;
    boss_hook = HOOK_NONE;                       // (HOOK_TELL: no special to tell yet)
    boss_hud();
}

// Held empties: the first one `sip` frames after it was caught (or after the last went), and only when the fair-empties
// schedule lets it arrive at the tap end no sooner than empty_gap after the last one scheduled.
static void boss_empties(void) {
    uint8_t ex;
    uint16_t t;
    if (boss_sip_t < br->sip) { boss_sip_t++; return; }
    ex = boss_x + br->width;
    t = ex >= TAP_X ? 0 : (uint16_t)(uint8_t)(TAP_X - ex) * EMPTY_STEP_FRAMES;
    if (t < next_arrival || !spawn_mug(boss_bar, ex, MUG_EMPTY)) return;
    next_arrival = t + empty_gap;
    boss_hold--;
    boss_sip_t = 0;
}

// story_play, every PLAYING frame of a fight (not the frame a life went): 1 = the meter is empty, the outro begins.
uint8_t boss_frame(void) BANKED {
    uint8_t x = boss_x;
    if (boss_hook) boss_take_hook();
    if (!boss_hp) { boss_state = BS_OUTRO; boss_lim = 0; boss_look(); return 1; }
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
        } else if (++boss_step_t >= boss_step) {
            boss_step_t = 0;
            x += 8;
            boss_stomp = STOMP_FRAMES;
            SFX(SFX_SHAKE);                      // the thud
        }
        if (boss_hold) boss_empties();
        if (x != boss_x) boss_move(x);
    }
    boss_look();
    boss_limit();
    boss_special();
    if ((uint8_t)(boss_x + br->width) >= BOSS_TAP_X) lose_life();   // at the tap: a life (boss_reset after the freeze)
    return 0;
}

// story_update, frame t (1..) of the outro (GS_STORY: nothing else moves): the mugs gone, the HAPPY pose, the hat
// bobbing; 1 when it is over (story.c: CHAPTER CLEAR).
uint8_t boss_outro(uint8_t t) BANKED {
    uint8_t i, n;
    if (t == 1) {
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
