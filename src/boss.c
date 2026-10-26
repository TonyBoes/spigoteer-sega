// The boss engine (docs/minigames_bosses.md 2.5, 3.1-3.3; step 2 of section 6): one engine, a parameter row per boss
// and a per-boss special hook. Only Big Tex (the saloon) has his row so far; an id without one plays Tex's.
//
// A fight is the venue's level in story mode: Last call's serve quota turns that level into it in place (story.c boss_in_place:
// boss_set, then the cover, his tiles, the fight's banner and pace from boss_goal / boss_begin); BOSS RUSH starts it from a fresh level
// (story.c rush_fight: boss_set, shift_start). The bar game runs as usual on the other bars (regulars, the
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
#define BOSS_WANT_CAP        // (boss_art.h: the capacity indicator's mug tiles)
#include "boss.h"            // the engine's inside, shared with the boss files (src/boss_<name>.c)

extern uint8_t pat_pos, pat_buf[STORY_PAT_MAX];   // (story.c) the arrival pattern patrons.c follows while pat_len
extern uint16_t pat_wait[4];
extern uint8_t overlay_on, save_lock;

#define G_BOSS            3       // story_goal.type of a fight (story.h: G_SERVE 0, G_CATCH 1, G_CLEAR 2)
#define BOSS_SPAWN_PCT  150       // the regulars' spawn interval in a fight (owner Q10: they keep coming, more slowly)
#define BOSS_TAP_X      SPOUT_X   // his right edge here: a life
#define CATCH_DX          4       // a full mug is caught at boss_x + W - CATCH_DX
#define HOP_FRAMES        4       // push-back: one 8 px hop per HOP_FRAMES
#define STOMP_FRAMES      8       // the STOMP pose after each stomp
#define OUTRO_FRAMES    120
#define CLEAR_BANNER_FRAMES 90   // "CLEAR THE BAR" stays this long once he is beaten and regulars remain
#define OAM_TOPPER      OAM_DANCERS   // (no show in a fight; OAM 26 is the perfect pour's cue)
// E9: the boss enters at once when the fight starts (docs/minigames_bosses.md 2.6); Last call is the warm-up (owner 2026-10-17: the 20 s
// warm-up the boss round had is gone). WARM_WAIT: a test hook that clears boss_t may make the entrance wait for his bar to empty and the mugs to land.
#define WARM_WAIT      180
#define WALK_STEP        6        // the fallback entrance: frames per 8 px he walks in from the left edge

enum { HOOK_NONE, HOOK_TELL, HOOK_METER_1, HOOK_DEFEAT, HOOK_FIGHT, HOOK_ENTER, HOOK_WALKIN,
       HOOK_CARD };   // HOOK_CARD (set by fight_start, never by a test): his first-appearance HOW TO PLAY card opens at the start of the next frame, with the picture whole   // boss_hook (tests; any but HOOK_ENTER in the
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
uint8_t  boss_pose;               // the pose shown (255: redraw)
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
// and BP_SWAY on the patrons' beat, the mug staying up; the topper and the hand mug (sprites) move with it (sway_dx).
// Only in the common gulp (no push-back, no special's pose over it). br->sway 0: no shifted pose (his column pairs are
// full: the Sasquatch, whose 20-frame gulp keeps E1's mug-down beat; the Sumo never gulps).
static uint8_t sip_beat(void) {
    return boss_state == BS_GULP && !boss_push && !boss_xpose && sway_tab[boss_t];   // (boss_t < gulp: the table is (t / SWAY_FRAMES) & 1, no divide)
}

static void hand_hide(void);                 // (below: the hand mug's two entries off)

// His pose from his state: the body's columns (boss_cols) and, when they changed, their tiles queued.
static void boss_look(void) {
    uint8_t p = BP_WALK, k, w = br->width >> 3;
    const uint8_t *m;
    if (boss_state == BS_OUTRO) p = boss_xpose == BP_HIDE ? BP_HIDE : BP_HAPPY;   // (the Mothership's minis: no saucer left to be happy)
    else if (boss_push) p = BP_WINCE;
    else if (boss_xpose) p = boss_xpose;
    else if (boss_state == BS_GULP) p = sip_beat() ? (br->sway ? BP_SWAY : BP_WALK) : BP_GULP;   // (the drinking sway, above)
    else if (boss_stomp) p = BP_STOMP;
    if (p == boss_pose) return;
    if (p == BP_HIDE || (boss_pose & 15) == BP_HIDE) {   // (a moving boss: gone from his spot, or back: the wall's
        boss_pose = p;                                    // own attributes there, then his)
        for (k = 0; k < BOSS_W_MAX; k++) boss_cols[k] = p == BP_HIDE || k >= w ? 0 : pair_id(boss_map[p * BOSS_W_MAX + k]);
        mark_dirty_attrs(boss_bar, boss_col, boss_col + w);
        return;
    }
    boss_pose = p;
    m = boss_map + p * BOSS_W_MAX;
    for (k = 0; k < w; k++) boss_cols[k] = pair_id(m[k]);
    // (columns w.. are his special's: boss_set clears them)
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
    HALF &= ~HALF_ON;                            // (a fight is drawn every frame, at 60 fps: src/half.c; the level's next load decides again)
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
    // The entrance starts on the fight's first frame (Last call before it was the warm-up; BOSS RUSH has none): BS_WARM is "not here yet",
    // his bar stays free of regulars but he is not on it (HIDE) until he walks in.
    boss_state = BS_WARM; boss_t = WARM_WAIT; boss_lim = 0;
    boss_special_t = 1; boss_xpose = BP_HIDE; boss_look();
}

// ---- the loader: his tiles and palettes ----
// With the LCD off (a level load: BOSS RUSH, a debug start) every tile and palette goes straight in. With the LCD on (Last call turning into his fight, in
// place: no cover, no LCD-off swap, owner 2026-10-17) boss_ld / boss_ldpal only record jobs in story_scratch (LD: [0] the head's offset, then the jobs
// from [1], a 0 byte after the last) and ld_step, one call a frame from boss_pre while he is BS_WARM, hands them out:
//   - tiles: 4 a frame. The art is in the boss file's ROM bank and the VBlank copy queue (render.c vq_vbl) reads WRAM only, so each chunk is copied to
//     STAGE first (far_copy), then queued as one entry (a 64 byte copy, ~7 lines of VBlank) to its VRAM place; the scene goes on meanwhile. They land
//     on tile ids nothing on screen shows (variant C's and the back views: the bars are empty, he comes only then; OBJ 96-127: the show's, none runs).
//   - CGB palettes: written when their turn comes, after waiting for the next VBlank (palette RAM only takes writes there, and the logic runs in the picture).
// job: tiles [n | LD_MASK?, dst lo, dst hi, src lo, src hi, bank] (6 bytes; src 0: the capacity indicator's mugs); palette [LD_PAL | obj << 3 | idx, 8 bytes of colours] (9).
#define LD          (story_scratch + SCR_LD_AT)   // (src/scratch.h: a job at LD + LD_MAX ends below story.c's HUD bytes)
#define LD_MAX      SCR_LD_MAX
#define LD_PAL      0x80
#define LD_MASK     0x40
#define STAGE       BOSS_CAPBUF
typedef struct { uint8_t n, bank; const uint8_t *src; uint8_t *dst; uint8_t pad[2]; } vq_entry_t;   // (render.c's list entry)
extern vq_entry_t vq[];
extern uint8_t vq_count;

static uint8_t *ld_next(uint8_t *j) {
    return j + ((*j & LD_PAL) ? 9 : 6);
}

// n tiles (up to 4) from src in `bank` to STAGE (mask: every byte & 0xF0 | 0x0F; src 0: the capacity indicator's mugs)
static void ld_fetch(uint8_t mask, const uint8_t *src, uint8_t n, uint8_t bank) {
    uint8_t i;
    if (!src) { boss_cap_stage(STAGE); return; }
    far_copy(STAGE, src, (uint16_t)n << 4, bank);
    if (mask)
        for (i = 0; i != (uint8_t)(n << 4); i++) STAGE[i] = (STAGE[i] & 0xF0) | 0x0F;
}

void boss_ld(uint8_t kind, uint8_t first, uint8_t n, const uint8_t *src, uint8_t bank) BANKED {
    uint8_t *j, c;
    uint16_t dst;
    if (!(LCDC_REG & LCDCF_ON)) {
        while (n) {
            c = n > 4 ? 4 : n;
            ld_fetch(kind == 2, src, c, bank);
            if (kind == 1) set_sprite_data(first, c, STAGE); else set_bkg_data(first, c, STAGE);
            first += c; n -= c;
            if (src) src += (uint16_t)c << 4;
        }
        return;
    }
    while (n) {
        c = kind != 1 && first < 128 && (uint8_t)(first + n) > 128 ? 128 - first : n;   // (a BG run over id 128 changes its VRAM block: two jobs)
        dst = (kind != 1 && first < 128 ? 0x9000 : 0x8000) + ((uint16_t)first << 4);
        for (j = LD + 1; *j; j = ld_next(j)) ;
        if (j > LD + LD_MAX) return;
        j[0] = c | (kind == 2 ? LD_MASK : 0);
        j[1] = (uint8_t)dst; j[2] = (uint8_t)(dst >> 8);
        j[3] = (uint8_t)(uint16_t)src; j[4] = (uint8_t)((uint16_t)src >> 8);
        j[5] = bank; j[6] = 0;
        first += c; n -= c;
        if (src) src += (uint16_t)c << 4;
    }
}

void boss_ldpal(uint8_t obj, uint8_t idx, const uint16_t *p) BANKED {
    uint8_t *j, code = LD_PAL | (obj << 3) | idx;
    if (!(LCDC_REG & LCDCF_ON)) {
        if (obj) set_sprite_palette(idx, 1, p); else set_bkg_palette(idx, 1, p);
        return;
    }
    for (j = LD + 1; *j && *j != code; j = ld_next(j)) ;   // (the same slot again: the later colours replace the earlier)
    if (!*j) { if (j > LD + LD_MAX) return; j[9] = 0; }
    j[0] = code;
    memcpy(j + 1, p, 8);
    if (SCR_BRIGHT()) pal_lift((uint16_t *)(j + 1));   // SCREEN BRIGHT: lifted here, in the main loop; ld_step writes the queued colours raw
}

// One step of the stream: 1 = everything has gone out (the last tiles are in VRAM, the last palette written).
static uint8_t ld_step(void) {
    uint8_t *j = LD + 1 + LD[0], n, c;
    uint16_t d;
    const uint8_t *src;
    vq_entry_t *e;
    if (!*j) return !vq_held;
    if (*j & LD_PAL) {                                 // a CGB palette: set_*_palette waits for the LCD's palette-RAM-safe mode before each colour (no spin to VBlank: the frame
        if (*j & 8) (set_sprite_palette)(*j & 7, 1, (const uint16_t *)(j + 1));   // would end past its line 154: a late frame)
        else (set_bkg_palette)(*j & 7, 1, (const uint16_t *)(j + 1));   // (raw: boss_ldpal lifted them when it queued them)
        LD[0] += 9;
        return 0;
    }
    if (vq_held || vq_count > 16) return 0;            // (last frame's list has not gone out: STAGE is still to be read)
    n = *j & 0x3F; c = n > 4 ? 4 : n;
    d = j[1] | ((uint16_t)j[2] << 8);
    src = (const uint8_t *)(j[3] | ((uint16_t)j[4] << 8));
    ld_fetch(*j & LD_MASK, src, c, j[5]);
    e = &vq[vq_count++];
    e->n = c << 4; e->bank = 0; e->src = STAGE; e->dst = (uint8_t *)d;
    if (qv_cost <= VQ_DRAIN_BUDGET) qv_cost += (c << 4) + 3;
    n -= c;
    if (!n) { LD[0] += 6; return 0; }
    d += (uint16_t)c << 4;
    if (src) src += (uint16_t)c << 4;
    j[0] = (j[0] & LD_MASK) | n;
    j[1] = (uint8_t)d; j[2] = (uint8_t)(d >> 8);
    j[3] = (uint8_t)(uint16_t)src; j[4] = (uint8_t)((uint16_t)src >> 8);
    return 0;
}

// enter_level_screen, LCD off, after start_level (BOSS RUSH, a level that starts as a fight): his body over variant C's tiles and the back views, the HUD's
// face and meter, the topper's frames; CGB his palettes (colour 0 the venue's wall). In place (LCD on, story.c boss_in_place): the same, recorded and streamed.
void boss_load(void) BANKED {
    LD[0] = 0; LD[1] = 0;
    boss_ld(1, OBJ_CAP, 4, 0, 0);                // the free slot's glass (first: a boss file's pool over 124-127 is then his own)
    boss_call(BEV_LOAD, 0);                      // his body, face, topper and palettes (src/boss_load.h), his extras
    boss_ld(0, BOSS_HUD_BG + 1, 3, boss_meter_tiles, CURRENT_BANK);
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
    shadow_OAM[OAM_TOPPER].y = 0; hand_hide();
}

// The capacity indicator's two mugs (assets/art/boss/tag.txt: ROOM, TAKEN, 8x16 each), 64 bytes to dst: OBJ_CAP.
void boss_cap_stage(uint8_t *dst) BANKED {
    memcpy(dst, boss_cap_tiles, BOSS_CAP_BYTES);
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

// ---- E9: the entrance ----
// The fight starts in BS_WARM ("not here yet"; the regulars are never bound for his bar): on the first frame entrance_start runs (when
// boss_t is below WARM_WAIT, only a test hook, it waits until his bar is empty and no mug is in the air): the world is cleared of
// mugs, any straggler on his bar is gone, intro_timer freezes the bar (BEV_INTRO / BEV_DRAW run), his entrance plays (BEV_ENTER: his
// own, or the fallback walk-in), and fight_start puts the banner up and the boss rules apply (and, the first time he ever appears
// in a save, the game pauses on his HOW TO PLAY card).
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
    if (shown && save_lock != SAVE_LOCK_DEBUG && !boss_card_seen(boss_id)) {   // the first time he ever appears (per save): his HOW TO PLAY card, the game paused
        boss_card_mark(boss_id);                 // behind it, and resumed by itself when the card is left (pause.c); not from here: this frame's OAM and bar rows are
        boss_hook = HOOK_CARD;                   // half done (his entrance sprites gone, his body not yet drawn), and the card's fade would show that: the next frame opens it
    }
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
        if (!ld_step()) return;                  // (in place: his tiles and palettes stream in first, a few frames; nothing to stream otherwise)
        if (boss_t < WARM_WAIT && (mugs_live || bar_busy())) boss_t++;
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
    if (boss_hook == HOOK_CARD) { boss_hook = HOOK_NONE; pause_boss_card(); return 0; }   // (the frame before's picture is whole: it fades out into the card)
    if (boss_hook && (boss_state != BS_WARM || !LD[1 + LD[0]])) boss_take_hook();   // (a test's hook waits for his tiles to be handed out: the fight / entrance it starts is on whole art)
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
        for (i = 0; i != 3; i++) shadow_OAM[OAM_CAP - 1 - i].y = 0;   // (the mug row and the hand mug are not drawn in the outro: when he is beaten with no regular left it begins
        hand_hide();                                    // at once, and the last frame's would stay)
        SFX(SFX_SERVE);
    }
    if (!(t & 15)) {
        boss_hat ^= 2;
        if (shadow_OAM[OAM_TOPPER].y) shadow_OAM[OAM_TOPPER].tile = OBJ_TOPPER + boss_hat;
    }
    return t >= OUTRO_FRAMES;
}

// Sprites per line over his bar: bands() and bands_intro() below.
// After the intro the hat, the indicator and the hand mug add at most `extra` entries (the hat 1, a glass for each of his hands, the mug while he gulps) on the 28 lines
// from the topper's y (OAM y `top`), so when no more than LINE_OBJ_MAX - extra of the entries already in OAM touch those lines nothing can reach 11 on a line and
// nothing more is counted (the usual case: a pass over OAM and nothing else; 0 is returned and fits() says yes). Otherwise each such entry is counted
// in n[] on the seven 4-line bands it touches and n is returned.
#define BANDS 7
// How many of the k entries from q (4 bytes apart: their y's) have y - t1 below span (the lines they touch overlap a window: its first line - 15 is t1)
static uint8_t near_in(const uint8_t *q, uint8_t k, uint8_t t1, uint8_t span) {
    uint8_t near = 0, y;
    for (; k; k--, q += 4) {
        y = *q;
        if (y && (uint8_t)(y - t1) < span) near++;
    }
    return near;
}

// How many of the k entries from q (k not 0) touch the 43 lines of the boss's bar window (t1 = top - 15: y from t1 on; near_in's span 43). The loop of every OAM entry in
// use every frame: a constant span, and an empty entry (y 0) is never in the window (top - 15 is no more than 256 - 43: 0 - t1 is past the span), so no test of its own
static uint8_t near_w(const uint8_t *q, uint8_t k, uint8_t t1) {
    uint8_t near = 0;
    do {
        if ((uint8_t)(*q - t1) < 43) near++;
        q += 4;
    } while (--k);
    return near;
}

// The OAM entries in use that touch a window of lines (t1, span as near_in). Only the entries in use are looked at (mirror.c does the same): 0..oam_used-1 are
// the bartender, the fill glass and the mugs (draw_mugs hides the rest up to the lifted patrons), OAM_MUG_END - 2 * lift_total on the lifted patrons (they take the
// top entries below OAM_MUG_END), then the cue, the coin and the effects up to the end. Everything between is 0.
uint8_t boss_near(uint8_t t1, uint8_t span) BANKED {
    uint8_t first = OAM_MUG_END - 2 * lift_total;
    return near_in((const uint8_t *)shadow_OAM, oam_used, t1, span) + near_in((const uint8_t *)(shadow_OAM + first), 40 - first, t1, span);
}

// For d (an entry's y - t1) from 0 to 42: the first band it touches and one past the last (its lines are d - 15 to d from the bar's first line: 4-line bands, the 28 lines from top)
static const uint8_t band_span[43 * 2] = { 0, 1, 0, 1, 0, 1, 0, 1, 0, 2, 0, 2, 0, 2, 0, 2, 0, 3, 0, 3, 0, 3, 0, 3, 0, 4, 0, 4, 0, 4, 0, 4, 0, 5, 0, 5, 0, 5, 1, 5, 1, 6, 1, 6, 1, 6, 2, 6, 2, 7, 2, 7, 2, 7, 3, 7, 3, 7, 3, 7, 3, 7, 4, 7, 4, 7, 4, 7, 4, 7, 5, 7, 5, 7, 5, 7, 5, 7, 6, 7, 6, 7, 6, 7, 6, 7 };

// Counts the entries of one range of OAM (k of them from q, 4 bytes apart) into the seven bands as a difference array (n[lo]++, n[hi]--: bands() adds them up):
// t1 = top - 15, so d = y - t1 is 0 for the entry 15 lines above the first line (k not 0)
static void band_count(const uint8_t *q, uint8_t k, uint8_t t1, uint8_t *n) {
    uint8_t d;
    const uint8_t *p;
    do {
        d = *q - t1;                         // (an empty entry is past the window: as near_w)
        if (d < 43) {
            p = band_span + d + d;
            n[p[0]]++;
            n[p[1]]--;
        }
        q += 4;
    } while (--k);
}

static const uint8_t *bands(uint8_t top, uint8_t *n, uint8_t extra) {
    uint8_t d = OAM_MUG_END - 2 * lift_total, lo;
    lo = near_w((const uint8_t *)shadow_OAM, oam_used, top - 15) + near_w((const uint8_t *)(shadow_OAM + d), 40 - d, top - 15);   // (its lines overlap the 28 from top: its y from -15 to 27 on)
    if (lo + extra <= LINE_OBJ_MAX) return 0;
    memset(n, 0, BANDS + 1);
    // Only the OAM entries in use are counted (the two ranges of boss_near; everything between is 0)
    band_count((const uint8_t *)shadow_OAM, oam_used, top - 15, n);
    band_count((const uint8_t *)(shadow_OAM + d), 40 - d, top - 15, n);
    n[1] += n[0]; n[2] += n[1]; n[3] += n[2]; n[4] += n[3]; n[5] += n[4]; n[6] += n[5];
    return n;
}

// The intro (Duke's entrance has 20 sprites of its own, anywhere in OAM: all 40 entries are looked at) only has the hat: every entry within 15 lines of its y counts
// on the four 4-line bands of the topper's 16 lines it touches (the same bands as bands(): an upper bound for each line: spec 3.1 counts the same bands), as ever.
// The bartender's 4 entries hang BT_DY lower than the bands were laid out for: counted as before (a y BT_DY lower), so his two pairs, which never share a line,
// are not both counted in the band that his top pair now just reaches. Like bands(): 0 when no more than LINE_OBJ_MAX - 1 entries touch the 43 lines (fits() says yes).
static const uint8_t *bands_intro(uint8_t top, uint8_t *n) {
    uint8_t k = near_w((const uint8_t *)(shadow_OAM + 4), 36, top - 15), i;
    for (i = 0; i != 4; i++) if (shadow_OAM[i].y && (uint8_t)(shadow_OAM[i].y - BT_DY - top + 15) < 43) k++;
    if (k < LINE_OBJ_MAX) return 0;
    memset(n, 0, BANDS + 1);
    band_count((const uint8_t *)shadow_OAM, 4, top - 15 + BT_DY, n);
    band_count((const uint8_t *)(shadow_OAM + 4), 36, top - 15, n);
    n[1] += n[0]; n[2] += n[1]; n[3] += n[2];
    return n;
}

// c more entries on bands k0..k1 would stay within LINE_OBJ_MAX (n 0: yes)
static uint8_t fits(const uint8_t *n, uint8_t k0, uint8_t k1, uint8_t c) {
    if (!n) return 1;
    for (; k0 <= k1; k0++)
        if (n[k0] + c > LINE_OBJ_MAX) return 0;
    return 1;
}

// The hand mug: while he gulps, the mug the player served over his right hand (the hand column: OBJ tile / palette of the sliding mug: the venue's own
// drink art, mugs.c), its bottom at row hand_base of his 16 body rows. 255: none (the Sumo is hit, the Mothership beams its drinks up).
static const uint8_t hand_base[BOSS_COUNT] = { 15, 15, 15, 12, 15, 11, 12, 255, 15, 255 };   // (rows[] order: Tex, Mascot, Sasquatch, Critic, Yeti, Prototype, Duke, Sumo, Leo, Mothership)

// The mug follows the patrons' drink (mugs.c pose_*) at full size: over his gulp it rises from the hand to his mouth, tilts, lies on its side (the
// crash's on-its-side frame, OBJ_GLASS: the full mug turned 90 degrees, 16x16, two entries) and is lowered empty (the sliding empty mug). Not the
// patrons' small drink frames: they shrink the mug. The steps are 16 and END with his gulp: he is pushed back first (HOP_FRAMES, hidden), so they
// count from the end, E - boss_t frames before it (hand_end: the last frame he holds the mug up, one before his gulp is over; the Sasquatch's
// arm goes down at 12), at hand_inv per frame: 4096 / (the frames from boss_t HOP_FRAMES to E, less one), rounded up, so (E - boss_t) * hand_inv >> 8
// is 15 on the first (0..15; before it the mug waits at his hand). Each step: its frame (high nibble: 0 the served mug upright, 1 the 45 degree
// tilt of his venue (hand_tilt: its tile, 16x16 two entries; 0 while there is none: the mug stays upright), 2 on its side, 3 the empty upright) and how
// far along the way to his mouth, in eighths (low nibble). hand_dx, hand_dy: that way from the hand (px, the upright mug's sprite, its rim at its
// (2, 4)): the mouth of each boss (assets/art/boss/*.txt, his gulp pose); no lower than row 4 of his body, so the sprite stays inside the 28
// lines the bands count. Lying on its side (a 16x16 sprite, mouth at its left, 11 down) it sits 2 left and 7 up of that.
// The second entry of the two: the first free one below the capacity row (Leo's waves or the Critic's cloche may be there: then it stays upright).
// The Prototype's battery stays upright at his hand and pulses (its full and empty colours, boss_t & 8): it is "in use".
#define HAND_T2   (OBJ_GLASS + GLASS_FALL_FULL + 2)   // the right half of the on-its-side mug (its left is the tile before)
static const uint8_t hand_seq[16] = { 0x00, 0x02, 0x05, 0x08, 0x18, 0x18, 0x28, 0x28, 0x28, 0x28, 0x28, 0x28, 0x38, 0x35, 0x32, 0x30 };
static const int8_t  hand_dx[BOSS_COUNT]  = { -12, -12, -12, -12, -16, -13, -11, 0, -9, 0 };
static const int8_t  hand_dy[BOSS_COUNT]  = {   3,   3,   3,   6,   0,   7,   6, 0,  3, 0 };
static const uint8_t hand_end[BOSS_COUNT] = {  57,  33,  11,  83,  43,  29,  29, 0,  43, 0 };   // (his gulp - 1; the Sasquatch's 11: his mug-down beat is 12 on)
static const uint16_t hand_inv[BOSS_COUNT] = {  73, 133, 549,  49,  99, 154, 154, 0,  99, 0 };   // (4096 / (E - HOP_FRAMES) up; tests/test_boss_cap_ui.py checks them)
static const uint8_t hand_tilt[BOSS_COUNT] = { 120, 120, 120, 120, 120,   0, 120, 0, 100, 0 };   // (the 45 degree tilt's first tile, gen_boss `tilt`: OBJ 120-123, Leo 100-103; the Prototype has none)
#define HAND_PROTO 5

// The hand mug's entries off (the second only if it is ours: Leo's waves, the Critic's cloche may be in the slot)
static void hand_hide(void) {
    OAM_item_t *o = shadow_OAM + OAM_CAP - 1 - boss_hands;
    shadow_OAM[OAM_HAND].y = 0;
    if (o->tile == HAND_T2 || (hand_tilt[boss_row] && o->tile == hand_tilt[boss_row] + 2)) o->y = 0;
}

// n: the bands from the topper's y; extra: the entries drawn over them already (the hat, the mug row)
static void hand_draw(uint8_t top, const uint8_t *n, uint8_t extra) {
    OAM_item_t *o = shadow_OAM + OAM_HAND, *o2 = shadow_OAM + OAM_CAP - 1 - boss_hands;
    uint8_t d, dx = 0, e, f, w, t, p, two = 0;
    hand_hide();
    if (boss_row == 9) boss_call(BEV_DRAW, 1);   // (the Mothership's own: a drink lifted into the saucer on a beam, OAM 29 and 30)
    if (boss_state != BS_GULP || boss_push || boss_xpose || hand_base[boss_row] == 255) return;   // (the common gulp only: the pose shows his hand up)
    if (sip_beat()) {
        if (!br->sway) return;                   // (the mug-down beat of a boss with no shifted pose: the Sasquatch)
        dx = br->sway == 2 ? -2 : 2;
    }
    e = 0;
    if (boss_row != HAND_PROTO) {
        e = hand_end[boss_row];
        e = e > boss_t ? (uint16_t)(e - boss_t) * hand_inv[boss_row] >> 8 : 0;   // (frames to the end, in steps)
        e = hand_seq[e > 15 ? 0 : 15 - e];
    }
    f = e >> 4; w = e & 15;
    t = spr_full_t; p = spr_full_p;
    if (f == 3) { t = spr_empty_t; p = spr_empty_p; }
    else if (f == 1 && hand_tilt[boss_row]) t = hand_tilt[boss_row];
    else if (f == 2) t = OBJ_GLASS + GLASS_FALL_FULL;
    if (t != spr_full_t && t != spr_empty_t) {
        if (o2->y) t = spr_full_t;               // (the second entry's slot is taken: the mug stays upright)
        else two = 1;
    }
    d = bar_oam_y[boss_bar] + hand_base[boss_row] - 14 + (hand_dy[boss_row] * w >> 3);   // its y; from top: -8..4, so bands 0..6 (28 lines on at most)
    if (two) d -= f == 1 ? 0 : 7;               // (the 45 degree tilt is centred on the upright mug; the one on its side sits 7 up)
    if (!fits(n, (uint8_t)(d - top) >> 2, (uint8_t)(d - top + 15) >> 2, extra + 1 + two)) return;
    if (boss_row == HAND_PROTO && (boss_t & 8)) p ^= is_cgb ? OBJPAL_MUG_FULL ^ OBJPAL_MUG_EMPTY : S_PALETTE;   // (the battery's two palettes: in use. DMG OBP0 / OBP1)
    o->y = d; o->x = boss_x + br->width + dx + (hand_dx[boss_row] * w >> 3) - (f == 1 ? 4 : 2) * two; o->tile = t; o->prop = p;
    if (two) { o2->y = d; o2->x = o->x + 8; o2->tile = t + 2; o2->prop = p; }
}

// The capacity indicator's slots: 255 none to show (BEV_ROOM), 254 no limit (the Sumo's 250, the Prototype's red light:
// only the glasses he holds are shown), else the free slots now (0 while a drink would not be caught).
static uint8_t room_free(void) {
    uint8_t f, k = 0;
    if (boss_cap > 9 || boss_row == 7) return 254;
    f = boss_lim && boss_hands > boss_hold ? boss_hands - boss_hold : 0;
    if (boss_row == 3 || boss_row == 8) k = boss_call(BEV_ROOM, f);
    return k ? (k == ROOM_OFF ? 255 : k - 2) : f;
}

// The capacity indicator (owner 2026-10-18: "the empty/full drink icons above and to the right of the boss"): one mug icon a hand (boss_hands) in a
// row above and to the right of him (his top line, from his right edge): a TAKEN (full, dark) mug for each empty he holds, then a ROOM (empty,
// bright) one for each free hand (OBJ_CAP, tag.txt). It follows his drinking sway. Only the taken ones when there is no limit (the Sumo, the
// Prototype's red light). OAM 39 down to 37 (Leo has 2 hands, Tex 3: Tex has no effect sprites).
#define CAP_PROP   (is_cgb ? OBJPAL_MUG_EMPTY : 0)   // (the venue's empty-glass palette; DMG OBP0, the bartender's)
// n: the bands from the topper's y `top`; hat: 1 if the hat is drawn (its budget first). Returns the icons drawn.
static uint8_t cap_draw(uint8_t top, const uint8_t *n, uint8_t hat) {
    uint8_t *p = (uint8_t *)(shadow_OAM + OAM_CAP), f = room_free(), sl = boss_hands, tk, k, x;
    if (f == 255) return 0;
    if (f == 254) { f = 0; tk = boss_hold > sl ? sl : boss_hold; }
    else { if (f > sl) f = sl; tk = sl - f; }
    sl = tk + f;
    if (!sl || !fits(n, 0, 3, hat + sl)) return 0;
    x = boss_x + br->width;
    if (sip_beat()) x += br->sway == 2 ? -2 : 2;
    for (k = 0; k != sl; k++, x += 8) {
        p -= 4;
        p[0] = top; p[1] = x; p[2] = OBJ_CAP + (k < tk ? 2 : 0); p[3] = CAP_PROP;
    }
    return sl;
}

// pour_frame (every drawn frame of a fight, after every other sprite): the topper over his head, its upper half above his bar; the capacity
// mug row; the hand mug. Sprites per line: every other OAM entry is counted on the 4-line bands its lines touch (bands above); the topper is
// left out on a frame where a band already has LINE_OBJ_MAX, so it is never an 11th object on a line (the hat blinks off for those frames); the
// indicator and the mug likewise.
void boss_draw(void) BANKED {
    uint8_t k, top = bar_oam_y[boss_bar] - 8, hat, intro;
    uint8_t n[BANDS + 1];
    const uint8_t *np;
    OAM_item_t *o;
    if (boss_state == BS_WARM) { shadow_OAM[OAM_TOPPER].y = 0; hand_hide(); return; }   // (E9: not here yet)
    intro = intro_timer;
    if (intro) {                                 // the intro: a special's own sprites (Duke's entrance) before the lines are counted
        boss_call(BEV_DRAW, 0);
        shadow_OAM[OAM_CAP - 1].y = 0;           // (no mug row in the intro: after a lost life it would still show; Leo's waves end at OAM 37)
        shadow_OAM[OAM_CAP - 2].y = 0;
    } else {
        for (k = 0; k != boss_hands; k++) shadow_OAM[OAM_CAP - 1 - k].y = 0;   // (the glasses: set again below)
        hand_hide();
    }
    if (boss_state == BS_JUMP || boss_xpose == BP_HIDE) {   // (away: no hat in the air)
        shadow_OAM[OAM_TOPPER].y = 0;
        return;
    }
    shadow_OAM[OAM_TOPPER].y = 0;   // (so the count skips it: it is set again below)
    np = intro ? bands_intro(top, n) : bands(top, n, 1 + boss_hands + 2 * (boss_state == BS_GULP));   // (the hat, a glass a hand, the hand mug while he gulps: two entries when it lies on its side)
    o = shadow_OAM + OAM_TOPPER;
    hat = fits(np, 0, 3, 1);
    if (hat) {
        o->y = top; o->x = boss_x + br->hat_dx + 8 + (sip_beat() ? (br->sway == 2 ? -2 : 2) : 0);   // (drinking: moves with his body)
        o->tile = OBJ_TOPPER + (BOSS_TOPPER_T ? BOSS_TOPPER_T : (boss_pose & 15) == BP_STOMP ? 2 : 0);
        o->prop = !is_cgb ? S_PALETTE : BOSS_TOPPER_PAL ? BOSS_TOPPER_PAL : OBJPAL_PATRON_C;
    } else o->y = 0;
    if (intro) return;
    k = !boss_hp || boss_state == BS_OUTRO ? 0 : cap_draw(top, np, hat);
    hand_draw(top, np, hat + k);
}
