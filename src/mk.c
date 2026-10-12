// MONKEY BUSINESS, the jungle zoo's mini-game (docs/minigames_bosses.md 4.9; art approved by the owner 2026-10-12: the proposal's
// reading 1 with G1, "looks good, green boxes"). Five supply crates on the counter; monkeys pop out of them to grab coconuts from
// Kiki's pile. Hop to the crate and shoo the monkey with a feather duster before it grabs one. Don't shoo the parrot.
//
// Rules (the spec's numbers):
// - The Spigoteer stands in front of crate k (0-4, 32 px apart; x = 4 + 32 k). Left / Right hops one crate in 6 frames (held:
//   repeats every 10 frames). A: an 8-frame shoo at crate k; the hit is on its 4th frame (the swing). A command pressed during a
//   hop or a shoo waits and runs when it ends (one is kept).
// - A pop: the lid rattles 20 frames, the monkey peeks 6 frames and stays up U frames (counted after the peek), then grabs a
//   coconut and runs off with it (4 px a frame). U = 90 at the start, falling by 1 every 40 frames to 45 at 30 s. Pop interval 60
//   frames at the start, 24 at 45 s (1 less every 75 frames). At most 2 up (counting a rattling crate and the parrot's flight)
//   before 20 s, 3 after.
// - Reachability (the fairness fix): a monkey's pop is scheduled only if the greedy path (nearest deadline first, 6 frames a hop,
//   8 frames to shoo, the hit on the 4th) reaches every monkey that will be up with >= 8 frames to spare, the Spigoteer's current
//   action and lockout counted. If not, another crate is tried, or the pop waits (it is tried again every frame).
// - A shoo with a monkey up (peeking counts): shooed, 100, +100 if within 20 frames of the lid opening. With nothing there: a
//   whiff, and a 12-frame lockout (it starts when the shoo's swing is done; no input then, none is kept). The parrot (from 15 s, 1
//   pop in 6) rises the same way; shooing it costs 200 (never below what this game earned; it flies off, no lockout); left alone
//   it flies off by itself after the same time.
// - Engine rule (the proposal's): at most one runner on screen. A monkey whose time is up while another still runs waits (up,
//   shoo-able) until the runner has gone: at most 22 frames. The sprite budget follows: at most 3 crates occupied (a flying parrot
//   keeps its crate until it has left) = 6 entries, 1 runner = 2, the puff = 1: 9 on the worst line.
// - 8 coconuts. Ends at 45 s or when the pile is empty; +200 per coconut left. Medal by score (src/mg.c's table): GOLD 8000,
//   SILVER 5000, BRONZE 2500 (tuned: PLAN.md "Monkey Business as built"). One setting (the spec has no HARD).
//
// Screen (the approved mock-up, reading 1 / G1): HUD row 0 (score, 8 coconut pips at columns 8-15, the timer at 16-19); the awning
// band rows 1-4 (BG palette 5, over the banner rows 2-3 until the first play frame); Kiki's pile at columns 16-19, rows 5-7 (6
// states) and her helmet at columns 14-15, row 7 (palette 3); the crates at columns 1 + 4 k, rows 12-13 (palette 2: closed,
// 2 rattles, open); the framework's zoo wall between; the wood counter rows 14-16 (palette 6) and its floor row 17. OAM 0 the
// puff, 1-2 the duster, 3-6 the Spigoteer (the fill pose mirrored for the shoo), 7-8 the runner, 9-18 a crate's occupant each
// (monkey / parrot, 2 entries). CGB OBJ palettes: 0 the Spigoteer, 3 monkey, 6 parrot, 1 duster, 5 puff (not 4: the level load
// does not put it back). DMG: the Spigoteer on OBP0, the rest on OBP1 (0xE4).
// Tiles: BG MK_BG (MG_GAME_BG, ids 125-169), OBJ 56-91 and 96-105; all put back by the next level load.
#pragma bank 255
#include <gb/gb.h>
#include <gb/cgb.h>
#include <stdint.h>

#include "game.h"
#include "music.h"
#include "mg.h"
#include "mk_art.h"         // this bank's own art (assets/art/monkey/*.txt)

#define S               (MG->mk)
#define MK_BG           MG_GAME_BG
typedef char mk_fits[(MK_BG + MK_BG_TILES <= 256 && MK_OBJ_A + MK_OBJ_A_TILES <= OBJ_COIN && MK_OBJ_B + MK_OBJ_B_TILES <= 128
                      && sizeof(struct mk_state) <= STORY_SCRATCH) ? 1 : -1];
#define MK_TIME       2700                  // 45 s
#define MK_COCO          8
#define MK_RATTLE       20
#define MK_PEEK          6
#define MK_U0           90
#define MK_U_MIN        45
#define MK_U_STEP       40                  // frames a step of U: 90 -> 45 at 30 s
#define MK_GAP0         60
#define MK_GAP_MIN      24
#define MK_GAP_STEP     75                  // frames a step of the interval: 60 -> 24 at 45 s
#define MK_FIRST_POP    30
#define MK_CAP_LATE   1500                  // time left at 20 s: the cap goes 2 -> 3
#define MK_PARROT_AT  1800                  // time left at 15 s: the parrots begin
#define MK_HOP           6
#define MK_REPEAT       10
#define MK_SHOO          8
#define MK_HIT           4                  // the shoo's frame that decides
#define MK_LOCK         12
#define MK_SPARE         8                  // the reachability rule's margin
#define MK_QUICK        20                  // frames after the lid opens that a shoo earns the bonus
#define MK_AFTER        24                  // frames a crate stays open after a theft or a flight
#define MK_FLY_END      33                  // frames a parrot's flight lasts (off the screen)
#define MK_RUN_SPEED     4
#define MK_PUFF_LEN     12
#define MK_FAIL_LEN     12
#define MK_PTS_SHOO    100
#define MK_PTS_QUICK   100
#define MK_PTS_PARROT  200
#define MK_PTS_COCO    200
#define SPIG_Y         112
#define SPIG_X0          4                  // x of the Spigoteer in front of crate 0 (crate k: + 32 k)
#define CRATE_X0         8                  // crate k's left edge: + 32 k
#define MON_Y           81
#define PUFF_Y          84
#define DUSTER_X        12                  // from the Spigoteer's x
#define DUSTER_Y        97
#define CRATE_ROW       12
#define PILE_COL        16
#define PILE_ROW         5
#define HELMET_ROW       7
#define BANNER_ROW       9
#define OAM_PUFF         0
#define OAM_DUSTER       1
#define OAM_SPIG         3
#define OAM_RUN          7
#define OAM_OCC          9
#define PAL_CRATE        2
#define PAL_PILE         3
#define PAL_AWNING       5
#define PAL_COUNTER      6
#define OPAL_MONKEY      3
#define OPAL_PARROT      6
#define OPAL_DUSTER      1
#define OPAL_PUFF        5
enum { MC_IDLE, MC_RATTLE, MC_UP, MC_AFTER, MC_FLY };
enum { MA_NONE, MA_HOP, MA_SHOO };
enum { MP_NONE, MP_LEFT, MP_RIGHT, MP_SHOO };
enum { ML_NONE, ML_SHOOED, ML_QUICK, ML_PARROT, ML_WHIFF, ML_THEFT };
#define RGB15(r, g, b) ((uint16_t)((r) | ((g) << 5) | ((b) << 10)))
#define HEX(v)  RGB15(((v) >> 19) & 31, ((v) >> 11) & 31, ((v) >> 3) & 31)
extern uint32_t score;
extern uint8_t score_digits[6];
extern uint8_t joy;

static const uint16_t pal_crate[4]   = { HEX(0xD0F090UL), HEX(0x58B838UL), HEX(0x1C6A28UL), HEX(0x06240EUL) };   // G1 leafy
static const uint16_t pal_awning[4]  = { 0, HEX(0xE0F4A8UL), HEX(0x48A838UL), HEX(0x0C3A18UL) };                 // [0]: the wall
static const uint16_t pal_pile[4]    = { 0, HEX(0xC89860UL), HEX(0xA05A28UL), HEX(0x281408UL) };                 // [0]: the wall
static const uint16_t pal_counter[4] = { HEX(0xD8A860UL), HEX(0xA86830UL), HEX(0x683818UL), HEX(0x241008UL) };
static const uint16_t pal_monkey[4]  = { 0, HEX(0xE8C090UL), HEX(0x885028UL), HEX(0x281808UL) };
static const uint16_t pal_parrot[4]  = { 0, HEX(0xF04838UL), HEX(0x2860D8UL), HEX(0x281020UL) };
static const uint16_t pal_duster[4]  = { 0, HEX(0xFFF0C8UL), HEX(0xE05030UL), HEX(0x3A2010UL) };
static const uint16_t pal_puff[4]    = { 0, HEX(0xFFFFFFUL), HEX(0xB8C0D0UL), HEX(0x384050UL) };
static const uint8_t hop_dx[MK_HOP + 1] = { 0, 5, 11, 16, 21, 27, 32 };             // the hop's x offset a frame (32 px in 6)
static const uint8_t duster_f[MK_SHOO] = { 0, 1, 0, 2, 0, 1, 2, 0 };                // the duster's swing (the mock-up's)
static const uint8_t pile_of[MK_COCO + 1] = { 5, 4, 3, 3, 2, 2, 1, 1, 0 };          // the pile's state by coconuts left

static void put(uint8_t bank, uint8_t *t, uint8_t col, uint8_t row, uint8_t n) {   // LCD on: the queue; off: at once
    if (LCDC_REG & LCDCF_ON) { vq_add(bank, t, col, row, n); return; }
    if (bank) VBK_REG = VBK_BANK_1;
    vram_put(col, row, t, n);
    VBK_REG = VBK_BANK_0;
}

static void attr_put(uint8_t row, uint8_t pal, uint8_t col, uint8_t n) {           // LCD off, CGB
    uint8_t i;
    for (i = 0; i < n; i++) row_buf[i] = pal;
    VBK_REG = VBK_BANK_1;
    vram_put(col, row, row_buf, n);
    VBK_REG = VBK_BANK_0;
}

static void hud_time(void) {                    // 'T' + seconds (3 digits) at columns 16-19, as the framework's timer
    uint8_t s = S.secs, h = 0, t = 0;
    while (s >= 100) { s -= 100; h++; }
    while (s >= 10) { s -= 10; t++; }
    S.tbuf[0] = TILE_GLYPH_T; S.tbuf[1] = TILE_GLYPH_0 + h; S.tbuf[2] = TILE_GLYPH_0 + t; S.tbuf[3] = TILE_GLYPH_0 + s;
}

static uint8_t secs_left(void) { return (uint8_t)((S.time + 59) / 60); }

static void hud_pips(void) {                    // the coconuts left: full pips, then empty ones (HUD columns 8-15)
    uint8_t i;
    for (i = 0; i < MK_COCO; i++) S.pips[i] = MK_BG + MKB_PIPS + (i >= S.coco);
    put(0, S.pips, 8, HUD_ROW, MK_COCO);
}

static void pile(void) {                        // Kiki's pile for the coconuts left (columns 16-19, rows 5-7)
    uint8_t st = pile_of[S.coco], r, c;
    if (S.pile_shown == st) return;
    S.pile_shown = st;
    for (r = 0; r < 3; r++) {
        for (c = 0; c < 4; c++) S.pbuf[r][c] = MK_BG + MKB_PILE + mk_pile_map[st * 12 + r * 4 + c];
        put(0, S.pbuf[r], PILE_COL, PILE_ROW + r, 4);
    }
}

static uint8_t cframe(uint8_t k) {              // the crate's look: 0 closed, 1 / 2 the rattle, 3 open
    struct mk_crate *c = &S.c[k];
    switch (c->st) {
    case MC_RATTLE: return (c->t >> 1) & 1 ? 2 : 1;
    case MC_UP: return 3;
    case MC_AFTER: case MC_FLY: return c->t < MK_AFTER ? 3 : 0;
    default: return 0;
    }
}

static void crates(void) {                      // the crates' tiles that changed
    uint8_t k, f, q;
    for (k = 0; k < MK_CRATES; k++) {
        f = cframe(k);
        if (S.cshown[k] == f) continue;
        S.cshown[k] = f;
        for (q = 0; q < 4; q++) S.cbuf[k][q] = MK_BG + MKB_CRATE + mk_crate_map[f * 4 + q];
        put(0, S.cbuf[k], 1 + 4 * k, CRATE_ROW, 2);
        put(0, S.cbuf[k] + 2, 1 + 4 * k, CRATE_ROW + 1, 2);
    }
}

// ---- the sprites ----
static void obj(uint8_t oam, int16_t x, int16_t y, uint8_t tile, uint8_t pal) {    // one 8x16 entry, screen px of the top-left
    OAM_item_t *o = shadow_OAM + oam;
    if (tile == 0xFF || x <= -8 || x >= 160 || y <= -16) { o->y = 0; return; }
    o->y = (uint8_t)(y + 16); o->x = (uint8_t)(x + 8); o->tile = tile; o->prop = is_cgb ? pal : S_PALETTE;
}

static void obj2(uint8_t oam, int16_t x, int16_t y, uint8_t spr, uint8_t pal) {    // a 16x16: its two entries
    obj(oam, x, y, mk_spr[2 * spr], pal);
    obj(oam + 1, x + 8, y, mk_spr[2 * spr + 1], pal);
}

static uint8_t px(void) {                       // the Spigoteer's x (screen px)
    uint8_t d = hop_dx[S.act == MA_HOP && S.act_t < MK_HOP ? S.act_t : 0];
    if (S.act == MA_HOP) return S.from < S.pos ? SPIG_X0 + 32 * S.from + d : SPIG_X0 + 32 * S.from - d;
    return SPIG_X0 + 32 * S.pos;
}

static int16_t runner_x(void) {                 // the runner's left edge: away from the middle, 4 px a frame
    int16_t d = (int16_t)MK_RUN_SPEED * S.run_t;
    return CRATE_X0 + 32 * S.run_k + (S.run_k <= 2 ? -d : d);
}

static void sprites(void) {
    uint8_t k, f, x = px(), pose = BT_IDLE, left = 0, o;
    int16_t t;
    struct mk_crate *c;
    if (S.act == MA_SHOO) { pose = BT_FILL; left = 1; }
    else if (S.act == MA_HOP) pose = S.act_t < 3 ? BT_WALK1 : BT_WALK2;
    else if (S.fail_t) pose = BT_FAIL;
    if (S.puff_t) obj(OAM_PUFF, S.puff_x, PUFF_Y, mk_puff[MK_PUFF_LEN - S.puff_t < 5 ? 0 : 1], OPAL_PUFF);
    else shadow_OAM[OAM_PUFF].y = 0;
    if (S.act == MA_SHOO) {
        f = duster_f[S.act_t < MK_SHOO ? S.act_t : MK_SHOO - 1];
        obj(OAM_DUSTER, x + DUSTER_X, DUSTER_Y, mk_duster[2 * f], OPAL_DUSTER);
        obj(OAM_DUSTER + 1, x + DUSTER_X, DUSTER_Y + 16, mk_duster[2 * f + 1], OPAL_DUSTER);
    } else shadow_OAM[OAM_DUSTER].y = shadow_OAM[OAM_DUSTER + 1].y = 0;
    mg_spigoteer(x, SPIG_Y, pose, left, OAM_SPIG);
    if (S.run_on) {                             // the runner: front-facing leap, one frame every 3
        f = (S.run_t / 3) & 1;
        obj2(OAM_RUN, runner_x(), MON_Y - (f ? 2 : 0), MKS_RUN0 + f, OPAL_MONKEY);
    } else shadow_OAM[OAM_RUN].y = shadow_OAM[OAM_RUN + 1].y = 0;
    for (k = 0; k < MK_CRATES; k++) {           // the occupants
        c = &S.c[k];
        o = OAM_OCC + 2 * k;
        x = CRATE_X0 + 32 * k;
        if (c->st == MC_UP) {
            if (c->kind) obj2(o, x, MON_Y, c->t < MK_PEEK ? MKS_PPEEK : MKS_PERCH, OPAL_PARROT);
            else obj2(o, x, MON_Y, c->t < MK_PEEK ? MKS_PEEK : MKS_UP, OPAL_MONKEY);
        } else if (c->st == MC_FLY) {
            t = c->t;
            obj2(o, x + t, MON_Y - 3 * t, MKS_FLAP0 + ((c->t / 3) & 1), OPAL_PARROT);
        } else shadow_OAM[o].y = shadow_OAM[o + 1].y = 0;
    }
}

// ---- the screen ----
void mk_enter(void) BANKED {
    uint8_t k, r, c, *z = (uint8_t *)&S, *v = (uint8_t *)0x9800, tb[20], ta[20];
    uint16_t p[4];
    for (k = 0; k < sizeof(struct mk_state); k++) z[k] = 0;
    set_bkg_data(MK_BG, MK_BG_TILES, mk_bg_tiles);
    set_sprite_data(MK_OBJ_A, MK_OBJ_A_TILES, mk_obj_a_tiles);
    if (MK_OBJ_B_TILES) set_sprite_data(MK_OBJ_B, MK_OBJ_B_TILES, mk_obj_b_tiles);
    if (is_cgb) {
        set_bkg_palette(PAL_CRATE, 1, pal_crate);
        p[0] = venue.pal[VENUE_PAL_BAR][0];                 // the wall's colour behind the awning and the pile
        p[1] = pal_awning[1]; p[2] = pal_awning[2]; p[3] = pal_awning[3];
        set_bkg_palette(PAL_AWNING, 1, p);
        p[1] = pal_pile[1]; p[2] = pal_pile[2]; p[3] = pal_pile[3];
        set_bkg_palette(PAL_PILE, 1, p);
        set_bkg_palette(PAL_COUNTER, 1, pal_counter);
        set_sprite_palette(OPAL_MONKEY, 1, pal_monkey);
        set_sprite_palette(OPAL_PARROT, 1, pal_parrot);
        set_sprite_palette(OPAL_DUSTER, 1, pal_duster);
        set_sprite_palette(OPAL_PUFF, 1, pal_puff);
    } else OBP1_REG = 0xE4;                                 // everything but the Spigoteer
    // the state
    S.pos = 2; S.from = 2; S.coco = MK_COCO; S.time = MK_TIME; S.secs = MK_TIME / 60;
    S.unow = MK_U0; S.gap = MK_GAP0; S.next = MK_FIRST_POP; S.pile_shown = 255;
    for (k = 0; k < MK_CRATES; k++) S.cshown[k] = 255;
    for (k = 0; k < 20; k++) S.hattr[k] = BGPAL_HUD;
    // the screen: the framework drew the wall and floor
    for (r = 0; r < 4; r++) {                               // the awning band, rows 1-4 (rows 2-3: the banner's, put back later)
        for (c = 0; c < 20; c++) row_buf[c] = MK_BG + MKB_BAND + mk_band_map[r * 20 + c];
        if (r == 1 || r == 2) for (c = 0; c < 20; c++) S.band[r - 1][c] = row_buf[c];
        vram_put(0, 1 + r, row_buf, 20);
        if (is_cgb && (r == 0 || r == 3)) attr_put(1 + r, PAL_AWNING, 0, 20);
    }
    for (c = 0; c < 20; c++) S.pal[c] = PAL_AWNING;
    for (c = 0; c < 20; c++) {                              // row 11 was the framework's counter: the wall again, as row 9
        tb[c] = v[9 * 32 + c];
    }
    vram_put(0, 11, tb, 20);
    if (is_cgb) {
        VBK_REG = VBK_BANK_1;
        for (c = 0; c < 20; c++) ta[c] = v[9 * 32 + c];
        vram_put(0, 11, ta, 20);
        VBK_REG = VBK_BANK_0;
    }
    for (r = 0; r < 3; r++) {                               // the counter, rows 14-16
        for (c = 0; c < 20; c++) row_buf[c] = MK_BG + MKB_COUNTER + (r == 0 ? 0 : 1 + (c & 1));
        vram_put(0, 14 + r, row_buf, 20);
        if (is_cgb) attr_put(14 + r, PAL_COUNTER, 0, 20);
    }
    for (k = 0; k < 2; k++) row_buf[k] = MK_BG + MKB_HELMET + k;           // Kiki's helmet beside the pile
    vram_put(14, HELMET_ROW, row_buf, 2);
    if (is_cgb) {
        attr_put(HELMET_ROW, PAL_PILE, 14, 2);
        for (r = 0; r < 3; r++) attr_put(PILE_ROW + r, PAL_PILE, PILE_COL, 4);
        for (k = 0; k < MK_CRATES; k++) { attr_put(CRATE_ROW, PAL_CRATE, 1 + 4 * k, 2); attr_put(CRATE_ROW + 1, PAL_CRATE, 1 + 4 * k, 2); }
    }
    pile();
    crates();
    hud_pips();
    hud_time();
    vram_put(16, HUD_ROW, S.tbuf, 4);
    sprites();
}

// ---- the game ----
static void banner(const char *s) {             // a line on row 9 in the HUD colours
    mg_say(BANNER_ROW, s);
    if (is_cgb) vq_add(1, S.hattr, 0, BANNER_ROW, 20);
}

static void penalty(uint16_t n) {               // -n, never below what this game earned
    if (n > mg_score) n = mg_score;
    mg_score -= n;
    score -= n;
    split6(score_digits, score);
    hud_dirty |= HUD_SCORE;
    prep_hud();
}

static uint8_t absd(uint8_t a, uint8_t b) { return a > b ? a - b : b - a; }

// The reachability rule for a monkey popping at crate j (its up time u): the greedy path, nearest deadline first.
static uint8_t reach_ok(uint8_t j, uint8_t u) {
    uint8_t av[MK_CRATES], dl[MK_CRATES], cr[MK_CRATES], used[MK_CRATES], n = 0, k, i, b, pos = S.pos, tt, arrive, start;
    struct mk_crate *c;
    for (k = 0; k < MK_CRATES; k++) {
        c = &S.c[k];
        if (c->kind || (c->st != MC_RATTLE && c->st != MC_UP) || (c->st == MC_UP && c->t >= c->u)) continue;   // (one waiting for a runner is as good as gone)
        cr[n] = k;
        if (c->st == MC_RATTLE) { av[n] = MK_RATTLE - c->t; dl[n] = MK_RATTLE - c->t + c->u; }
        else { av[n] = 0; dl[n] = c->u - c->t; }
        used[n++] = 0;
    }
    cr[n] = j; av[n] = MK_RATTLE; dl[n] = MK_RATTLE + u; used[n++] = 0;
    tt = S.lock;                                // the current action, then the lockout
    if (S.act == MA_HOP) tt += MK_HOP - S.act_t;
    else if (S.act == MA_SHOO) tt += MK_SHOO - S.act_t;
    for (i = 0; i < n; i++) {
        b = 255;
        for (k = 0; k < n; k++) if (!used[k] && (b == 255 || dl[k] < dl[b])) b = k;
        used[b] = 1;
        if (tt > 150) return 0;
        arrive = tt + 6 * absd(pos, cr[b]);
        start = av[b] > MK_HIT && (uint8_t)(av[b] - MK_HIT) > arrive ? av[b] - MK_HIT : arrive;
        if ((uint8_t)(start + MK_HIT + MK_SPARE) > dl[b]) return 0;
        tt = start + MK_SHOO;
        pos = cr[b];
    }
    return 1;
}

static void pop_try(void) {
    uint8_t occ = 0, k, j, r, parrot = 0, u = 6 + S.unow, cap = S.time <= MK_CAP_LATE ? 3 : 2;
    for (k = 0; k < MK_CRATES; k++) if (S.c[k].st == MC_RATTLE || S.c[k].st == MC_UP || S.c[k].st == MC_FLY) occ++;
    if (occ >= cap) return;
    if (S.time <= MK_PARROT_AT) parrot = mg_rand() % 6 == 0;
    r = mg_rand() % MK_CRATES;
    for (k = 0; k < MK_CRATES; k++) {
        j = r + k;
        if (j >= MK_CRATES) j -= MK_CRATES;
        if (S.c[j].st != MC_IDLE) continue;
        if (!parrot && !reach_ok(j, u)) continue;
        S.c[j].st = MC_RATTLE; S.c[j].kind = parrot; S.c[j].t = 0; S.c[j].u = u;
        S.next = S.gap;
        S.pops++;
        return;
    }
}

static void steal(uint8_t k) {
    S.c[k].st = MC_AFTER; S.c[k].t = 0;
    S.run_on = 1; S.run_k = k; S.run_t = 0;
    S.coco--; S.stolen++; S.last = ML_THEFT;
    SFX(SFX_LIFE);
    hud_pips();
    pile();
}

static void shoo_hit(void) {
    struct mk_crate *c = &S.c[S.pos];
    if (c->st == MC_UP && !c->kind) {
        mg_points(MK_PTS_SHOO + (c->t <= MK_QUICK ? MK_PTS_QUICK : 0));
        S.last = c->t <= MK_QUICK ? ML_QUICK : ML_SHOOED;
        SFX(c->t <= MK_QUICK ? SFX_SERVE : SFX_COIN);
        S.shooed++;
        c->st = MC_IDLE; c->t = 0;
        S.puff_t = MK_PUFF_LEN; S.puff_x = CRATE_X0 + 32 * S.pos + 4;
    } else if (c->st == MC_UP) {                // the parrot
        penalty(MK_PTS_PARROT);
        S.last = ML_PARROT; S.parrots++;
        SFX(SFX_BREAK);
        c->st = MC_FLY; c->t = 0;
        S.fail_t = MK_FAIL_LEN;
    } else {                                    // nothing there
        S.last = ML_WHIFF; S.whiffs++;
        SFX(SFX_SHAKE);
        S.lock = MK_LOCK; S.fail_t = MK_FAIL_LEN;
    }
}

static void command(uint8_t cmd) {
    S.rep = 0;
    if (cmd == MP_SHOO) { S.act = MA_SHOO; S.act_t = 0; return; }
    if (cmd == MP_LEFT) { if (!S.pos) return; S.from = S.pos; S.pos--; }
    else { if (S.pos >= MK_CRATES - 1) return; S.from = S.pos; S.pos++; }
    S.act = MA_HOP; S.act_t = 0;
}

static void input(uint8_t pressed) {
    uint8_t cmd = 0;
    if (pressed & J_A) cmd = MP_SHOO;
    else if (pressed & J_LEFT) cmd = MP_LEFT;
    else if (pressed & J_RIGHT) cmd = MP_RIGHT;
    if (S.lock) { S.pend = 0; return; }
    if (S.act) { if (cmd) S.pend = cmd; return; }
    if (!cmd) {
        cmd = S.pend;
        if (!cmd && S.rep >= MK_REPEAT) cmd = (joy & J_LEFT) ? MP_LEFT : (joy & J_RIGHT) ? MP_RIGHT : 0;
    }
    S.pend = 0;
    if (cmd) command(cmd);
}

static void outro_begin(void) {
    S.st = 1;
    if (S.coco) mg_points((uint16_t)MK_PTS_COCO * S.coco);
    banner(S.coco ? "TIME UP" : "ALL GONE");
}

static void world(void) {                       // crates, runner, puff
    uint8_t k;
    int16_t rx;
    struct mk_crate *c;
    for (k = 0; k < MK_CRATES; k++) {
        c = &S.c[k];
        if (c->st == MC_IDLE) continue;
        if (c->t < 255) c->t++;
        switch (c->st) {
        case MC_RATTLE:
            if (c->t >= MK_RATTLE) { c->st = MC_UP; c->t = 0; }
            break;
        case MC_UP:
            if (c->t >= c->u && !S.st) {
                if (c->kind) { c->st = MC_FLY; c->t = 0; }
                else if (!S.run_on) steal(k);
            }
            break;
        case MC_AFTER:
            if (c->t >= MK_AFTER) { c->st = MC_IDLE; c->t = 0; }
            break;
        default:                                // the parrot's flight
            if (c->t >= MK_FLY_END) { c->st = MC_IDLE; c->t = 0; }
            break;
        }
    }
    if (S.run_on) {
        S.run_t++;
        rx = runner_x();
        if (rx <= -16 || rx >= 160) S.run_on = 0;
    }
    if (S.puff_t) S.puff_t--;
    if (S.fail_t) S.fail_t--;
}

void mk_update(uint8_t pressed) BANKED {
    uint8_t s;
    if (mg_phase == MG_END && !S.st) outro_begin();            // (also when a test ends the game early)
    if (!S.started) {                           // the first frame: the banner rows (the framework's text) become awning again
        S.started = 1;
        vq_add(0, S.band[0], 0, 2, 20); vq_add(0, S.band[1], 0, 3, 20);
        if (is_cgb) { vq_add(1, S.pal, 0, 2, 20); vq_add(1, S.pal, 0, 3, 20); }
    }
    if (!S.st) {
        if (S.rep < 255) S.rep++;
        if (S.act) {                            // the action goes on; the shoo's swing decides on its 4th frame
            S.act_t++;
            if (S.act == MA_SHOO && S.act_t == MK_HIT) shoo_hit();
            if (S.act_t >= (S.act == MA_HOP ? MK_HOP : MK_SHOO)) { S.act = MA_NONE; S.act_t = 0; }
        } else if (S.lock) S.lock--;
        input(pressed);
        world();
        if (S.next) S.next--;
        if (!S.next) pop_try();
        if (++S.ucnt >= MK_U_STEP) { S.ucnt = 0; if (S.unow > MK_U_MIN) S.unow--; }
        if (++S.gcnt >= MK_GAP_STEP) { S.gcnt = 0; if (S.gap > MK_GAP_MIN) S.gap--; }
        if (S.time) S.time--;
        s = secs_left();
        if (s != S.secs) { S.secs = s; hud_time(); vq_add(0, S.tbuf, 16, HUD_ROW, 4); }
        if (!S.time || !S.coco) { mg_finish(); outro_begin(); }
    } else world();
    crates();
    sprites();
    S.anim++;                                   // (last: `S.anim++; if (...)` made SDCC test the counter, PLAN.md's pitfall)
}
