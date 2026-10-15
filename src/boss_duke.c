// Duke, the Chrome Cow's boss (docs/minigames_bosses.md 3.12; art approved 2026-10-12, round 6: H2's leather back with H1's
// forked, braided beard). His row is boss.c rows[6]: 40 px, start 16, bar 1, step 0 (the engine's stomp is off), push 16,
// gulp 20, hands 2, sip 45, meter 12; his helmet is the topper (OBJ 7: red with a white stripe, set here).
//
// Owner change to the design: he STANDS behind the bar like Big Tex, with NO bike in the fight (the bike belongs to his
// entrance, which is not built). The doc's bike behaviours became standing ones:
//   IDLE   after his entry, his last catch or his last lurch: IDLE_150 frames while his meter is 12-9, 120 at 8-5, 90 at
//          4-1 (the shake is nearly full and he gets impatient). The idle pose "shakes with the engine": WALK / STOMP
//          every 8 frames (the topper bobs with STOMP).
//   REV    the tell, DUKE_REV 50 frames: he winds an invisible throttle (TELL1 / TELL2 every 8 frames: his fist at
//          shoulder height twisting, motion arcs, a roaring mouth), SFX_REV (the engine's growl, 50 frames on channel 4), the helmet jumping 1 px every 4 frames
//          (the topper's HAT_BOB frame is the 1 px lower one); he stands (BS_TELL).
//   LURCH  16 px in 8 frames (two boss_advance hops 4 frames apart), the TELL2 pose, then IDLE again from 0. The doc's
//          exhaust puffs, black smoke and entry skid belong to the bike and are not built.
// A catch: the common one (meter -1, push 16 px = two hops, the gulp 20 frames), and the idle clock starts again from 0.
// A catch during the REV stalls him: the lurch is off; he shows WINCE while pushed and then GULP, 20 frames in all
// (DUKE_STALL), then IDLE from 0. Landing a glass on the first frame of the rev always beats it (40 frames to reach him).
// His gang: the regulars come in the venue's Last call "chord" (three bars at once, a breather, three more) on the three
// bars that are not his, at the boss fight's spawn interval; no mosh pit (boss.c sets the twist to 0).
// ENTRANCE (owner-approved 2026-10-12, X1 "skid and vault"; art assets/art/duke_entrance.txt, PLAN.md "Duke as built"): on the
// fight's first start (BEV_LOAD; not after a lost life) he rides in from the left on his chopper, skids to a stop, revs
// (SFX_REV) and vaults off backwards onto his bar while the empty bike rolls away right, behind him. 62 frames in
// BS_JUMP + BP_HIDE (boss.c: nothing of his on his bar, no topper, no catch), then boss_to_bar(boss_bar, 16): his BG body and
// the idle clock from 0; the intro's 90 frames start there (intro_timer is held until the landing) and the fight is as it
// was. The sprites are drawn from boss_draw (BEV_DRAW, last: it counts the OAM lines) into OAM 5.., the mugs' entries (no
// mug: the bartender is held at his bar 0 tap, no glass, until the bike is gone). Tiles: 68 OBJ tiles (34 8x16 pairs), more
// than the 32 a fight borrows (96-127): the 36 at OBJ 56-91 are the drinks' (mug, crash glass, fill, drink: not on screen
// during the entrance); the coin's (92-95) stay. The topper's 96-99 come back at frame 50 (the rev's frames are gone), the
// drinks' once the bike has left (4 tiles a frame through the VBlank queue, from the venue's own drink tiles).
// Test hooks (WRAM: his state is the struct duke_t in BOSS_OWN, no variable of his own): duke.phase, duke.t, duke.ent.
#pragma bank 255
#include <string.h>
#include "boss.h"
#include "boss_duke_art.h"
#include "boss_load.h"
#include "music.h"
#include "story.h"

extern uint8_t pat_pos, pat_buf[STORY_PAT_MAX];   // (story.c) the arrival pattern patrons.c follows while pat_len

#define BP_TELL1     BP_EXTRA           // gen_boss BOSSES duke extra: TELL1, TELL2
#define BP_TELL2     (BP_EXTRA + 1)
#define IDLE_HI      150                // meter 12-9
#define IDLE_MID     120                // 8-5
#define IDLE_LO       90                // 4-1
#define DUKE_REV      50
#define DUKE_HOP       4                // frames per 8 px of the lurch
#define DUKE_LURCH     8                // 16 px
#define DUKE_STALL    20
#define POSE_FRAMES    8                // the idle shake and the tell's two poses
#define HAT_DOWN       2                // topper tile offset: HAT_BOB, 1 px lower
#define CHORD_N        6
#if BOSS_ART_COLS != 5 || CHORD_N > STORY_PAT_MAX
#error "Duke: a 40 px body, the chord fits the pattern buffer"
#endif

enum { DP_IDLE, DP_REV, DP_LURCH, DP_STALL };

typedef struct {
    uint8_t phase;      // DP_* (tests)
    uint8_t t;          // frames in the phase (stops at 255)
    uint8_t revs;       // revs begun this fight (tests)
    uint8_t lurches;    // lurches made (tests)
    uint8_t stalls;     // revs a catch stalled (tests)
    uint8_t ent;        // the entrance: 0 none (or over), else the next frame's number + 1 (tests)
    uint8_t rl;         // the entrance's reloads done: the topper (1), then the drinks' chunks of 4 tiles
} duke_t;
#define duke (*(duke_t *)BOSS_OWN)
#if 7 > BOSS_OWN_N
#error "Duke's state: BOSS_OWN_N"
#endif

static uint8_t idle_len(void) {
    return boss_hp >= 9 ? IDLE_HI : boss_hp >= 5 ? IDLE_MID : IDLE_LO;
}

static void to_idle(void) {
    duke.phase = DP_IDLE; duke.t = 0;
    boss_xpose = 0;
    BOSS_TOPPER_T = 0;
    if (boss_state == BS_TELL || boss_state == BS_SPECIAL) boss_state = BS_WALK;
}

static void to_rev(void) {
    duke.phase = DP_REV; duke.t = 0;
    duke.revs++;
    boss_xpose = BP_TELL1;
    SFX(SFX_REV);
}

// The regulars: the chord on the three free bars (a, b, c): a and b at once, c after a breather, c and b and then a once
// more with a breather (wait codes 1 short, 3 four intervals, as the venue's "chord").
static void chord(void) {
    static const uint8_t cycle[CHORD_N][2] = { {0, 1}, {1, 1}, {2, 3}, {2, 1}, {1, 1}, {0, 3} };
    uint8_t free_bar[3], i, k = 0;
    for (i = 0; i != NUM_BARS; i++) if (i != boss_bar) free_bar[k++] = i;
    for (i = 0; i != CHORD_N; i++) pat_buf[i] = free_bar[cycle[i][0]] | (cycle[i][1] << 4);
    pat_len = CHORD_N; pat_pos = 0; pat_bar = pat_buf[0] & 3;
}

// ---- the entrance ----
#define ENT_LAND     62                 // the landing frame: his BG body at x 16; frames 0-61 he rides, skids, revs, vaults
#define ENT_TOPPER   50                 // the topper's tiles come back (OBJ 96-99: the rev's frames are gone)
#define ENT_GONE    113                 // the bike has rolled off the screen: the drinks' tiles come back
#define ENT_REVSFX   28                 // SFX_REV starts as the bike stops: the rev (30-45), the vault, the engine fading
#define ENT_Y        48                 // the bike's top row, screen y (its wheels stand on the wall's foot, y 79)
#define ENT_LOW_ID   OBJ_MUG            // the first 18 pairs at OBJ 56.. (36 tiles), the other 16 at OBJ 96..
#define ENT_HIGH_ID  OBJ_DANCER
#define ENT_LOW_N    18
#define ENT_OAM      (OAM_FILL + 1)     // the mugs' first entry: nothing is in the air during the entrance
#define ENT_OAM_N    20
#define ENT_BUF      (story_scratch + 300)   // 64 B staging for the reloads (the queue copies from WRAM: banks are not mapped then)
#define ENT_RELOADS  10                // (the 9 drink chunks, then the status tag's 4 tiles: OBJ_TAG 124-127 lie in the pool)
#if BOSS_ART_ENT_PAIRS > 34 || BOSS_ART_ENT_PAIRS < ENT_LOW_N || OBJ_COIN != 92 || OBJ_MUG != 56 || OBJ_GLASS != 60 || OBJ_MUG_FILL != 76 || OBJ_MUG_DRINK != 84 \
    || OBJ_TOPPER != 96 || OBJ_DANCER != 96 || ENT_BUF + 64 > BOSS_SCRATCH || ENT_OAM + ENT_OAM_N > OAM_MUG_END
#error "Duke's entrance: the OBJ tile pool (56-91, 96-127), the OAM entries or the staging buffer"
#endif

typedef struct { uint8_t n, bank; const uint8_t *src; uint8_t *dst; uint8_t pad[2]; } vq_entry_t;   // (render.c's list entry)
extern vq_entry_t vq[];
extern uint8_t vq_count, vq_held;

static const uint8_t skid[15] = { 4, 8, 11, 14, 17, 19, 21, 23, 24, 25, 26, 26, 26, 26, 26 };   // px slid since the ride's x 4 + 26
static const uint8_t reload[ENT_RELOADS][2] = {           // the drinks: OBJ id, first tile in venue.drink_tiles (mug, crash, fill, drink)
    { 56, 0 }, { 60, 20 }, { 64, 24 }, { 68, 28 }, { 72, 32 }, { 76, 4 }, { 80, 8 }, { 84, 12 }, { 88, 16 }, { OBJ_TAG, 0 } };

// Room for a copy now: last frame's list went out (the VBlank interrupt reads ENT_BUF, so it is not written while an older
// entry still waits for it) and the list has space.
static uint8_t ent_room(void) {
    return !vq_held && vq_count < 20;
}

// n tiles from ENT_BUF to OBJ tile id `tile` in the next VBlank (after ent_room)
static void ent_queue(uint8_t tile, uint8_t n) {
    vq_entry_t *e = &vq[vq_count++];
    e->n = n << 4; e->bank = 0; e->src = ENT_BUF; e->dst = (uint8_t *)(0x8000 + ((uint16_t)tile << 4));
}

// Entrance frame f's 8x16 entries at screen (x, y) into OAM from o (up to `end`), with the attributes `prop` (the lower row of
// cells also `low`: the bike goes behind his body, whose lines are the lower row's, but not behind the bar above); the entries
// off the screen are left out (the hardware counts every entry on a line, seen or not).
static OAM_item_t *ent_put(OAM_item_t *o, OAM_item_t *end, uint8_t f, int16_t x, uint8_t y, uint8_t prop, uint8_t low) {
    const uint8_t *c = boss_ent_cells + ((uint16_t)boss_ent_first[f] << 2);
    uint8_t n = boss_ent_first[f + 1] - boss_ent_first[f];
    uint16_t cx;
    x += 8; y += 16;
    for (; n && o != end; n--, c += 4) {
        cx = x + c[0];
        if ((uint16_t)(cx - 1) >= 167) continue;
        o->y = y + c[1]; o->x = (uint8_t)cx; o->tile = c[2];
        o->prop = prop | c[3] | (c[1] ? low : 0);
        o++;
    }
    return o;
}

static int16_t ent_bike_x(uint8_t t) {
    return t < 15 ? 4 * t - 52 : t < 30 ? 4 + skid[t - 15] : t < 48 ? 30 : 30 + 2 * (t - 48);
}

// BEV_DRAW: the entrance's sprites for the frame the logic just reached (boss_draw, after every other sprite)
static void ent_draw(void) {
    OAM_item_t *o = shadow_OAM + ENT_OAM, *top = o + ENT_OAM_N, *end = shadow_OAM + OAM_MUG_END - 2 * lift_total;
    uint8_t t = duke.ent - 2, k, pal = is_cgb ? OBJPAL_COIN : S_PALETTE, hat = is_cgb ? OBJPAL_PATRON_C : S_PALETTE;
    int16_t bx, hx, j;
    uint8_t by = ENT_Y, hy;
    if (duke.ent < 2) return;
    if (end > top) end = top;
    bx = ent_bike_x(t);
    if (t < ENT_LAND - 16) {                         // on the bike: rides in (0-14), skids (15-29), sits and revs (30-45)
        if (t < 15) by += (t >> 1) & 1;              // (the engine's shake)
        else if (t >= 30) by += ((t - 30) >> 1) & 1;
        o = ent_put(o, end, ENT_RIDE, bx, by, pal, 0);
        o = ent_put(o, end, ENT_HELM, bx + 14, by - 8, hat, 0);
        if (t >= 30) {                               // the exhaust, 4 frames in 8
            k = t - 30;
            if ((k & 7) < 4) o = ent_put(o, end, ENT_SMOKE1 + ((k >> 2) & 1), bx - 8 - (k & 7), 56 - ((k & 7) >> 1), pal, 0);
        } else if (t >= 15) {                        // the skid's dust, behind the rear tyre
            k = t - 15;
            o = ent_put(o, end, ENT_DUST1 + (k / 3) % 3, bx - 6 - (k / 3) * 3, 64, pal, 0);
        }
    } else if (t < ENT_LAND) {                       // the vault: Duke arcs back off the seat, the empty bike rolls on
        j = t - (ENT_LAND - 16);
        hx = 36 - ((j * 47) >> 6);
        hy = 48 + ((j * 43) >> 6) - ((j * (15 - j) * 9) >> 5);
        o = ent_put(o, end, ENT_HOP, hx, hy, pal, 0);
        o = ent_put(o, end, ENT_HELM, hx + 7, hy - 8, hat, 0);
        o = ent_put(o, end, ENT_BIKE, bx, by, pal, 0);
        for (k = 0; k != OAM_FILL; k++) shadow_OAM[k].y = 0;   // the bartender ducks out of sight for the vault: the empty bike (6 a
        if (t == ENT_LAND - 1) oam_touched();        // line) + Duke (3) + his helmet (1) leave room for no more than that; redrawn after
    } else if (bx < 160) {                           // the empty bike rolls on behind him (BG colours 1-3 cover it)
        o = ent_put(o, end, ENT_BIKE, bx, by, pal, S_PRIORITY);
        if (t < ENT_LAND + 6) o = ent_put(o, end, ENT_DUST1 + (t - ENT_LAND) / 2, 48, 64, pal | S_PRIORITY, 0);   // the landing's dust, by his feet
    }
    for (; o != top; o++) o->y = 0;
}

// BEV_INTRO, every frame while intro_timer runs: the entrance's clock and what happens at its frames. The player's input is
// undone (the bartender stays at bar 0's tap, nothing is poured) until the bike has gone and the drinks' tiles are back.
static void ent_frame(void) {
    uint8_t t = duke.ent - 1, i;
    bar = 0; bartender_x = bar_tap[0]; bartender_frac = 0; facing = 0; fill_timer = 0; fill_stage = 0;
    bartender_frame = BT_IDLE; catch_pose = 0; bt_bob = 0;
    if (t < ENT_LAND) intro_timer = INTRO_FRAMES;            // (held: the intro's 90 frames start at the landing)
    if (t == ENT_REVSFX) SFX(SFX_REV);
    if (t >= ENT_TOPPER && t < ENT_LAND && !duke.rl && ent_room()) {       // (retried until the queue has room)
        memcpy(ENT_BUF, boss_art_hat, BOSS_ART_HAT_TILES * 16);
        ent_queue(OBJ_TOPPER, BOSS_ART_HAT_TILES);
        duke.rl = 1;
    }
    if (t == ENT_LAND) {
        intro_timer = INTRO_FRAMES - 1;                      // (as the level's first frame leaves it: the fight starts 89 frames on)
        boss_xpose = 0; boss_state = BS_WALK;
        boss_to_bar(boss_bar, 16);                           // his BG body (WALK) at x 16
        to_idle();
        SFX(SFX_SHAKE);
        duke.rl = 0;
    }
    if (t >= ENT_GONE && duke.rl < ENT_RELOADS && ent_room()) {            // the drinks' tiles, 4 a frame
        i = duke.rl++;
        if (reload[i][0] == OBJ_TAG) boss_tag_stage(ENT_BUF);    // (boss.c: the status tag, not a drink)
        else far_copy(ENT_BUF, venue.drink_tiles + reload[i][1] * 16, 64, venue_bank);
        ent_queue(reload[i][0], 4);
    }
    if (t >= ENT_GONE + ENT_RELOADS + 1 && duke.rl == ENT_RELOADS) {   // the last chunk has gone out: the bartender is his again
        for (i = 0; i != ENT_OAM_N; i++) shadow_OAM[ENT_OAM + i].y = 0;
        duke.ent = 0; duke.rl = 0;
        return;
    }
    duke.ent++;
}

uint8_t boss_duke(uint8_t ev, uint8_t arg) BANKED {
    (void)arg;
    switch (ev) {
    case BEV_SET:
        boss_art_set();
        duke.revs = duke.lurches = duke.stalls = 0;
        duke.ent = duke.rl = 0;
        to_idle();
        break;
    case BEV_RESET:
        to_idle();
        if (duke.ent && boss_state == BS_ENTER) { boss_state = BS_JUMP; boss_xpose = BP_HIDE; }   // (the entrance: not on his bar yet)
        break;
    case BEV_LOAD:
        boss_art_load();
        if (is_cgb) {                    // the helmet's own colours (red shell, white stripe, dark outline) in OBJ 7
            palette_t p;
            p[0] = 0; p[1] = RGB(29, 7, 7); p[2] = RGB(31, 31, 31); p[3] = RGB(3, 2, 4);
            set_sprite_palette(OBJPAL_PATRON_C, 1, p);
            p[1] = boss_art_pal[1]; p[2] = boss_art_pal[2]; p[3] = boss_art_pal[3];   // the entrance's: his body's colours, OBJ 5
            set_sprite_palette(OBJPAL_COIN, 1, p);
        }
        break;
    case BEV_ENTER:                      // E9: the warm-up is over (boss.c entrance_start): the tile pool borrows the drinks' tiles
        set_sprite_data(ENT_LOW_ID, ENT_LOW_N * 2, boss_ent_tiles);        // (LCD on: GBDK's STAT-waiting copy; the bar is held)
        set_sprite_data(ENT_HIGH_ID, (BOSS_ART_ENT_PAIRS - ENT_LOW_N) * 2, boss_ent_tiles + ENT_LOW_N * 32);
        duke.ent = 1; duke.rl = 0;
        return 1;
    case BEV_INTRO:
        if (duke.ent) ent_frame();
        break;
    case BEV_DRAW:
        if (duke.ent) ent_draw();
        break;
    case BEV_BEGIN:
        chord();
        break;
    case BEV_TELL:
        if (duke.phase == DP_IDLE) to_rev();
        break;
    case BEV_CATCH:                      // (then the common catch: meter -1, push 16, the gulp)
        if (duke.phase == DP_REV) {
            duke.phase = DP_STALL; duke.t = 0;
            duke.stalls++;
            boss_xpose = 0;              // WINCE while pushed, then GULP
            BOSS_TOPPER_T = 0;
            boss_state = BS_WALK;
        } else if (duke.phase == DP_IDLE) duke.t = 0;
        break;                           // (a catch in the lurch: it finishes, then idle from 0)
    case BEV_OUTRO:
        to_idle();
        break;
    case BEV_FRAME:
        if (duke.t != 255) duke.t++;
        switch (duke.phase) {
        case DP_IDLE:
            if (duke.t >= idle_len() && boss_state == BS_WALK && !boss_push) to_rev();
            else boss_xpose = boss_state == BS_WALK && (duke.t & POSE_FRAMES) ? BP_STOMP : 0;
            break;
        case DP_REV:
            if (duke.t >= DUKE_REV) {
                duke.phase = DP_LURCH; duke.t = 0;
                duke.lurches++;
                boss_xpose = BP_TELL2;
                BOSS_TOPPER_T = 0;
                boss_advance();
            } else {
                boss_xpose = duke.t & POSE_FRAMES ? BP_TELL2 : BP_TELL1;
                BOSS_TOPPER_T = duke.t & DUKE_HOP ? HAT_DOWN : 0;
            }
            break;
        case DP_LURCH:
            if (duke.t == DUKE_HOP) boss_advance();
            if (duke.t >= DUKE_LURCH) to_idle();
            break;
        case DP_STALL:
            if (duke.t >= DUKE_STALL) to_idle();
            break;
        }
        if (duke.phase == DP_REV && boss_state == BS_WALK) boss_state = BS_TELL;       // (he stands)
        else if (duke.phase == DP_LURCH && (boss_state == BS_WALK || boss_state == BS_TELL)) boss_state = BS_SPECIAL;
        break;
    }
    return 0;
}
