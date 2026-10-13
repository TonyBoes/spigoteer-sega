// THE POUR-OFF, the story's finale (docs/minigames_bosses.md section 5; owner 2026-10-12: it is played in the SALOON, no new
// stage; the story's lives rule and the perfect pour apply). A race against Dregs, the second bartender, from the opposite end
// of the same four bars: the Spigoteer on the right as always, Dregs on the left. A drink that reaches a thirsty townsfolk first
// scores for whoever slid it. First to 20 wins; Dregs reaching 20 first, or the lives running out (3), loses, and a loss
// restarts the Pour-Off only (mg.c: result_frame; STORY then goes on to FINALE_B, story.c story_pouroff_done).
//
// It runs on the mini-game framework (src/mg.c: the banner, the count-in, MG_PLAY; there is no result window, no medal and no
// timer) as game id MG_POUROFF (11), entered from story.c after FINALE_A. Its own module, with its own bartender update for two
// bartenders and its own mug and seat rules: it touches nothing of patrons.c, mugs.c or lift.c. All state is in the mini-game
// union (struct po_state, src/po.h): no WRAM global of its own.
//
// Rules (the spec's numbers):
// - Seats: three a bar at x 40, 72, 104 (mirrored about the centre: each is as far from Dregs's spout, x 16, as its mirror is from
//   yours, x 136). Patrons do not walk; one pops in on a free seat every 50 frames at the start, 35 at the end (by the leader's
//   score), at most 2 a bar. Patience 480 frames (2 a tick); in the last 120 they sway; at 0 they leave and nobody scores.
// - A full drink slides 2 px a frame (Dregs's to the right). The first THIRSTY patron whose 16 px it meets catches it: +1 for the
//   bartender who slid it (yours also scores as the story does: 100, a PERFECT pour 200). He drinks 60 frames (a held mug
//   sprite), then slides the empty back to the same bartender at 1 px a frame and leaves the seat. A drink meeting nobody
//   reaches the far end and the other bartender takes it off the counter (a THANKS note): a wasted throw costs only time. Two
//   drinks going opposite ways on a bar pass each other.
// - Your empties: catch them as always (on that bar, overlapping); one past x 144 breaks and costs a life. Dregs catches his
//   (x <= 32 on his bar); one he misses (x <= 8: a window of 24 frames, as yours) breaks: Dregs -1 point and he slips (60 frames out of action).
// - At most 4 mugs a bar (both directions, sliding, held in a hand, breaking). A drink that does not fit stays in the bartender's
//   hand (the full glass under the spout) until there is room: nothing is lost silently.
// - The perfect pour (story mode everywhere, src/pour.c): the sparkle window of the fill, 27..31 frames; released in it the drink is
//   PERFECT (the story score doubled, a cue). It never changes the race: a serve is one point.
// Dregs (the CPU), one decision at a time, from mg_rand: (1) an empty of his arriving at his end within 40 frames: switch to that
// bar and wait to catch it (10 frames' reaction); (2) else the thirsty patron with the shortest slide that none of his drinks in
// flight is heading for (one pick in 8 goes to a contested seat or a patron about to leave: comic waste); (3) think 27 frames at 0
// points falling to 16 at 15 (+8 if he leads by 4 or more, -6 if he trails by 4), fill 16 frames, slide. po.tune[] holds the knobs.
//
// Screen: the saloon's stage (rows 1-4) and four bars (rows 5-16, wall wall counter) with the kegs and spouts at both ends (the
// left ones mirrored copies in BG ids MG_BG.., DMG cannot flip BG tiles), the patrons' footprints on the wall rows, the HUD with
// the lives and "Y12 D10" (columns 13-19). The banner rows 2-3 (the framework's text, THANKS and the outro) cover the stage and
// are put back as it was (saved: no VRAM read).
// Crowd: three looks, a table (po_crowd: patron group, variant), each loaded as its shift-0 pose and one sway pose (2 px): the
// saloon's cowboy and cowgirl and one guest from the bistro (a chef), a mixed finale crowd: "the whole tour came".
// BG ids: MG_BG .. the flipped keg tiles (<= 9), then PO_PAT 12 a look. CGB BG palettes 2-4 the three looks (colour 0 the wall).
// OBJ: ids 0.. the Spigoteer, the venue's drink at 56.., the pour tiles 234.., Dregs 128-183, the DMG mug copies 184-189;
// CGB OBJ palette 3 Dregs; DMG OBP0 the Spigoteer, OBP1 (0xE4) Dregs and the sparkle. OAM: 0-3 the Spigoteer, 4-7 Dregs,
// 8-9 the fill glasses, 10-25 the mugs, 26 the cue ("x2", left of the patron who took a PERFECT drink; the Spigoteer stands to his
// right). Sprites on a line: at most 10 (two bartenders 4, two glasses 2, 4 mugs a bar); the cue is left out when its lines are full.
#pragma bank 255
#include <gb/gb.h>
#include <gb/cgb.h>
#include <stdint.h>
#include <stddef.h>

#include "game.h"
#include "music.h"
#include "mg.h"
#include "palettes.h"
#include "po_art.h"         // this bank's own art (assets/art/dregs/dregs.txt): Dregs's OBJ tiles

BANKREF_EXTERN(patron_tiles_cowboys)
BANKREF_EXTERN(patron_tiles_chefs)
extern const uint8_t patron_tiles_cowboys[], patron_tiles_chefs[];
extern uint8_t joy;

#define S               (MG->po)
#define Y               (S.y)
#define D               (S.d)
#define PO_FLIP         MG_BG                       // the left keg's flipped tiles (<= 9)
#define PO_PAT          (MG_BG + 9)                 // 3 looks x 12 tiles (shift-0 pose, shift-2 pose)
#define PO_DREGS        128                         // OBJ ids of Dregs's 7 frames x 8
#define PO_DMG          (PO_DREGS + PO_DREGS_TILES) // DMG: the mug tiles with the bit planes swapped (full, empty, held empty)
#define PO_OBP1         0xE4                        // DMG: OBP1 (Dregs: idx1 light grey, idx2 dark grey, idx3 black; the sparkle)
#define PO_LEFT         44                          // how far left the Spigoteer may walk (Dregs stands at x 24..40)
#define PO_DX           24                          // Dregs's x (the mirror of TAP_X: 160 - 16 - 120)
#define PO_SPOUT_D      16                          // Dregs's spout, a launched mug's start (the mirror of SPOUT_X 136)
#define PO_DREGS_PAL    3
#define PO_DRINK_FRAMES 60
#define PO_PATIENCE     240                         // ticks of 2 frames
#define PO_SWAY_AT      60                          // ticks left when they sway
#define PO_CAP          4
#define PO_CATCH_D      32                          // an empty at x <= this on his bar is Dregs's
#define PO_BREAK_Y      144                         // an empty past this is lost (the Spigoteer's end)
#define PO_BREAK_D      8                           // ... and past this (the mirror of yours, x <= 8) one of his is lost: a window of 24 frames, as yours
#define PO_NOTE_FRAMES  45
#define PO_CUE_FRAMES   48
#define OAM_YOU         0
#define OAM_DREGS       4
#define OAM_FILL_Y      8
#define OAM_FILL_D      9
#define OAM_MUG0        10
#define OAM_CUE_PO      26
typedef char po_fits[(sizeof(struct po_state) <= STORY_SCRATCH && PO_PAT + 36 <= MG_GAME_BG + 3
                      && PO_DMG + 6 <= 234 && PO_DREGS >= 128) ? 1 : -1];
// the offsets tests/po_helpers.py reads
typedef char po_off_a[(offsetof(struct po_state, y) == 29 && offsetof(struct po_state, d) == 46 && offsetof(struct po_state, seat) == 58
                       && offsetof(struct po_state, mug) == 142) ? 1 : -1];

static const uint8_t seat_x[3] = { 40, 72, 104 };
// the knobs, in PT_* order (po.h): think 27 frames at 0 points, 16 at 15 (the spec's 30 and 18, tuned with tests/po_helpers.py's bots:
// see PLAN.md), +8 leading by 4, -6 trailing by 4, 10 frames' reaction, 40 frames ahead, one pick in 8 comic, 60 frames' slip
static const uint8_t po_tune[8] = { 27, 16, 8, 6, 10, 40, 8, 60 };
// the crowd: the patron group (level.c's order: 0 cowboys .. 3 chefs) and its variant
static const uint8_t po_crowd[3][2] = { { 0, 0 }, { 0, 1 }, { 3, 0 } };
static const uint8_t walk_cycle[4] = { BT_WALK1, BT_IDLE, BT_WALK2, BT_IDLE };
#define RGB15(r, g, b) ((uint16_t)((r) | ((g) << 5) | ((b) << 10)))
static const uint16_t dregs_pal[4] = { 0, RGB15(30, 27, 20), RGB15(22, 20, 23), RGB15(4, 3, 5) };   // J2: skin (his story-scene cream), grey jacket, ink

// ---- the screen (LCD off) -------------------------------------------------------------------------------------------------
static uint8_t *tile_at(uint8_t t) {             // VRAM of BG id t (signed mode, as mirror.c)
    return (uint8_t *)((t < 128 ? 0x9000u : 0x8000u) + ((uint16_t)t << 4));
}

static uint8_t rev8(uint8_t b) {
    uint8_t r = 0, i;
    for (i = 0; i < 8; i++) { r = (r << 1) | (b & 1); b >>= 1; }
    return r;
}

// The id that shows tile t mirrored: a copy in PO_FLIP... A tap's lettering (gen_art.py LETTER_BOX: none on the saloon's keg, the
// star is its own kind of symmetric) has a pre-mirrored twin in a trailer after the venue's bar tiles (n, 4 L ids, the twins), as
// mirror.c uses for Classic's R bars: its twin is what gets flipped, so the left end's text reads the right way round.
static uint8_t flip_tile(uint8_t t, uint8_t *src, uint8_t *dst, uint8_t *n, const uint8_t *alt) {
    uint8_t k, same = 1, *s, *d, buf[16];
    for (k = 0; k < *n; k++) if (src[k] == t) return dst[k];
    s = tile_at(t);
    for (k = 0; k < alt[0]; k++)
        if (alt[1 + k] == t) {
            far_copy(buf, venue.bar_tiles + (uint16_t)venue.bar_n * 16 + 5 + k * 16, 16, venue_bank);
            s = buf;
            break;
        }
    d = tile_at(PO_FLIP + *n);
    for (k = 0; k < 16; k++) { d[k] = rev8(s[k]); if (d[k] != tile_at(t)[k]) same = 0; }
    src[*n] = t; dst[*n] = PO_FLIP + *n;
    if (same) dst[*n] = t;                       // (its own mirror image: it keeps its id)
    return dst[(*n)++];
}

static void put_rows(uint8_t y, const uint8_t *t, const uint8_t *a) {   // one row: tiles, CGB attributes
    vram_put(0, y, t, 20);
    if (!is_cgb) return;
    VBK_REG = VBK_BANK_1;
    vram_put(0, y, a, 20);
    VBK_REG = VBK_BANK_0;
}

static void swap_copy(uint8_t src, uint8_t dst, uint8_t n) {   // n OBJ tiles with the two bit planes swapped (as lift.c)
    const uint8_t *s = (const uint8_t *)(0x8000u + (uint16_t)src * 16u);
    uint8_t *d = (uint8_t *)(0x8000u + (uint16_t)dst * 16u), k, a;
    for (k = n * 8; k; k--) { a = s[0]; d[0] = s[1]; d[1] = a; s += 2; d += 2; }
}

static void load_crowd(uint8_t i) {
    uint8_t g = po_crowd[i][0], v = po_crowd[i][1], bank;
    const uint8_t *a;
    palette_t p;
    if (g == 3) { a = patron_tiles_chefs; bank = BANK(patron_tiles_chefs); }
    else        { a = patron_tiles_cowboys; bank = BANK(patron_tiles_cowboys); }
    bkg_data_far(PO_PAT + i * 12, 6, a + (PATRON_SHIFT0_OFS + v * 6) * 16, bank);        // shift 0 (3 x 2 tiles, column by column)
    bkg_data_far(PO_PAT + i * 12 + 6, 6, a + (v * 42 + 6) * 16, bank);                   // shift 2
    if (!is_cgb) return;
    patron_pal_get(g, v, p);
    p[0] = venue.pal[VENUE_PAL_BAR][0];          // colour 0 = the wall, so the art needs no transparency
    set_bkg_palette(BGPAL_PATRON + i, 1, p);
}

static void put_hud(void) {                      // "Y12 D10" into S.hud (HUD columns 13-19)
    uint8_t a = Y.score, b = D.score;
    S.hud[0] = TILE_GLYPH_Y;
    S.hud[1] = TILE_GLYPH_0 + (a >= 20 ? 2 : a >= 10 ? 1 : 0);
    S.hud[2] = TILE_GLYPH_0 + (a >= 20 ? a - 20 : a >= 10 ? a - 10 : a);
    S.hud[3] = TILE_HUD_BLANK;
    S.hud[4] = TILE_GLYPH_D;
    S.hud[5] = TILE_GLYPH_0 + (b >= 20 ? 2 : b >= 10 ? 1 : 0);
    S.hud[6] = TILE_GLYPH_0 + (b >= 20 ? b - 20 : b >= 10 ? b - 10 : b);
}

void po_enter(void) BANKED {
    uint8_t *z = (uint8_t *)&S, r, b, c, k, n = 0, fs[12], fd[12];
    uint16_t zi;
    uint8_t t[3][20], a[3][20], alt[5];
    for (zi = 0; zi < sizeof S; zi++) z[zi] = 0;
    for (k = 0; k < 8; k++) S.tune[k] = po_tune[k];
    lives = PO_LIVES;
    prep_hud();
    vram_put(8, HUD_ROW, lives_tiles, 4);
    Y.x = TAP_X; Y.bar = 1;
    D.x = PO_DX; D.bar = 2; D.st = PD_IDLE;
    S.spawn_t = 20;
    // the screen: the stage (rows 1-4), the bars (rows 5-16) with a mirrored keg and spout at the left end
    for (k = 0; k < 20; k++) S.hattr[k] = BGPAL_HUD;
    for (r = 0; r < 4; r++)                      // (rows 1-3: the banner's, over the sign: the HUD's colours until the first play frame)
        put_rows(STAGE_FIRST_ROW + r, venue.stage_map + r * 20, r < 3 ? S.hattr : venue.stage_attr + r * 20);
    mg_say(1, "");                               // (row 1 is blank under the banner: the TAPS sign's top does not poke out above it)
    far_copy(alt, venue.bar_tiles + (uint16_t)venue.bar_n * 16, 5, venue_bank);   // the lettering twins
    for (b = 0; b < NUM_BARS; b++) {
        for (c = 0; c < 20; c++) {
            t[0][c] = base_tile[0][c]; a[0][c] = base_attr[0][c];
            t[1][c] = base_tile[1][c]; a[1][c] = base_attr[1][c];
            t[2][c] = ctr_all[0][c];   a[2][c] = ctr_all[1][c];
        }
        for (r = 0; r < 3; r++)
            for (c = 0; c < 3; c++) {
                t[r][c] = flip_tile(t[r][19 - c], fs, fd, &n, alt);   // (a bar's columns 19, 18, 17: the keg and the spout)
                a[r][c] = a[r][19 - c];
            }
        for (r = 0; r < 3; r++) put_rows(BAR_TOP_ROW(b) + r, t[r], a[r]);
    }
    for (k = 0; k < 20; k++)                     // stage rows 1-3: what they are
        for (r = 0; r < 3; r++) { S.wall[r][k] = venue.stage_map[r * 20 + k]; S.wattr[r][k] = venue.stage_attr[r * 20 + k]; }
    for (k = 0; k < 3; k++) load_crowd(k);
    // sprites: Dregs, the drink, the pour (sparkle, overflow, cue)
    set_sprite_data(PO_DREGS, PO_DREGS_TILES, po_dregs_tiles);
    pour_load(0);
    if (is_cgb) set_sprite_palette(PO_DREGS_PAL, 1, dregs_pal);
    else {
        OBP1_REG = PO_OBP1;
        swap_copy(OBJ_MUG, PO_DMG, 4);                   // sliding full, sliding empty
        swap_copy(OBJ_MUG_DRINK + 6, PO_DMG + 4, 2);     // the empty in a hand
    }
    put_hud();
    vram_put(13, HUD_ROW, S.hud, 7);
    S.hudq = 0;
}

// ---- mugs and seats ------------------------------------------------------------------------------------------------------
// (hot code, SDCC on the SM83: the loops walk pointers; the per-bar counts, Dregs's drinks in flight and his nearest empty
// come out of the one pass over the mugs, mugs_step, and are read a frame later)
static const uint8_t seat_bar[PO_SEATS] = { 0, 0, 0, 1, 1, 1, 2, 2, 2, 3, 3, 3 };
static const uint8_t seat_k[PO_SEATS]   = { 0, 1, 2, 0, 1, 2, 0, 1, 2, 0, 1, 2 };

static uint8_t po_spawn(uint8_t bar, uint8_t x, uint8_t own, uint8_t st, uint8_t aux) {   // 1: placed (the bar has room)
    uint8_t i;
    struct po_mug *m = S.mug;
    if (S.cnt[bar] >= PO_CAP) return 0;
    for (i = PO_MUGS; i; i--, m++) {
        if (m->st != PM_FREE) continue;
        m->x = x; m->bar = bar; m->own = own; m->aux = aux;
        m->st = st;                              // (last: a test reading between two frames' halves never sees a half-made mug)
        S.cnt[bar]++;
        if (own && st == PM_FULL) S.dfull[bar]++;
        return 1;
    }
    return 0;
}

static const char *const band_txt[6] = { "", "THANKS", "OOPS", "YOU WIN", "DREGS WINS", "OUT OF LIVES" };
static void band(uint8_t k) {                    // a line on row 2 with row 1 blank above it: the sign behind is covered (the blank
    mg_say(1, "");                               // row now, the text the next frame: the VBlank copy stays short)
    if (is_cgb) vq_add(1, S.hattr, 0, 1, 20);
    S.pend = k;
}

static void note(uint8_t k) {                    // ... for a while
    band(k);
    S.note_t = PO_NOTE_FRAMES;
}

static void note_off(uint8_t r) {                // stage row r (1 or 2) again: one row a frame keeps the VBlank copy short
    vq_add(0, S.wall[r - 1], 0, r, 20);
    if (is_cgb) vq_add(1, S.wattr[r - 1], 0, r, 20);
}

static void seat_draw(uint8_t i) {               // its footprint (3 x 2 tiles) into the queue buffers, and queued
    struct po_seat *s = &S.seat[i];
    uint8_t k, c, p, r, *tb = S.sbuf[i];
    c = 5 + 4 * seat_k[i];
    r = BAR_TOP_ROW(seat_bar[i]);
    if (s->st == PS_EMPTY) {
        for (k = 0; k < 3; k++) {
            tb[k] = base_tile[0][c + k]; tb[3 + k] = base_tile[1][c + k];
            S.sattr[i][k] = base_attr[0][c + k]; S.sattr[i][3 + k] = base_attr[1][c + k];
        }
    } else {
        p = PO_PAT + s->v * 12 + (s->sh ? 6 : 0);
        tb[0] = p; tb[1] = p + 2; tb[2] = p + 4; tb[3] = p + 1; tb[4] = p + 3; tb[5] = p + 5;
        for (k = 0; k < 6; k++) S.sattr[i][k] = BGPAL_PATRON + s->v;
    }
    vq_add(0, tb, c, r, 3);
    vq_add(0, tb + 3, c, r + 1, 3);
    if (is_cgb) { vq_add(1, S.sattr[i], c, r, 3); vq_add(1, S.sattr[i] + 3, c, r + 1, 3); }
    s->dirty = 0;
}

// ---- the Spigoteer (main.c play_frame's rules on this struct) ---------------------------------------------------------------
static uint8_t walk_px(void) {
    uint8_t f = Y.frac;
    Y.frac = f + WALK_FRAC;
    return Y.frac < f ? WALK_PX + 1 : WALK_PX;
}

static void launch_you(void) {                   // the full drink under his spout slides (or waits in his hand)
    if (po_spawn(Y.bar, SPOUT_X, 0, PM_FULL, Y.pq)) {
        Y.hold = 0; Y.slide = SLIDE_FRAMES;
        SFX(SFX_LAUNCH);
    } else Y.hold = 1;
}

static void you_step(uint8_t pressed) {
    uint8_t walked = 0, switched, carry, x, d, t = TAP_X, end = POUR_WIN_START + POUR_WIN_LEN;
    carry = Y.fill >= FILL_FRAMES && (joy & J_A);
    switched = pressed & (J_UP | J_DOWN);
    if (pressed & J_UP)        Y.bar = Y.bar == 0 ? NUM_BARS - 1 : Y.bar - 1;
    else if (pressed & J_DOWN) Y.bar = Y.bar == NUM_BARS - 1 ? 0 : Y.bar + 1;
    if (switched) { Y.x = t; Y.facing = 0; }
    x = Y.x;
    d = joy;
    if (d & J_LEFT) {
        Y.facing = 0;
        if (x > PO_LEFT) { d = walk_px(); x = x - d < PO_LEFT ? PO_LEFT : x - d; }
    } else if (d & J_RIGHT) {
        Y.facing = 1;
        if (x < t) { d = walk_px(); x = x + d > t ? t : x + d; }
    }
    if (x != Y.x) { Y.x = x; walked = 1; }
    else Y.frac = 0;
    if ((pressed & J_A) && !Y.fill && !Y.hold && Y.x >= (uint8_t)(t - TAP_GRACE) && Y.x < t) { Y.x = t; Y.frac = 0; }
    Y.at_tap = Y.x == t;
    if (Y.fill) {
        if (switched && carry && !walked) {
            // carried to the new bar: still holding the full mug under the spout
        } else if (walked || switched || !Y.at_tap || !(joy & J_A)) {
            if (!walked && !switched && Y.at_tap && Y.fill >= FILL_FRAMES) launch_you();
            Y.fill = 0;
            if (!walked) Y.facing = 0;
        } else if (Y.fill < FILL_FRAMES) {
            Y.fill++;
        }
    } else if (Y.at_tap && (pressed & J_A) && !Y.hold) {
        Y.fill = 1;
        SFX(SFX_FILL);
    }
    if (Y.hold && Y.at_tap) launch_you();        // a full drink waits in his hand until the bar has room
    if (Y.fill) Y.facing = 1;
    if (Y.slide) Y.slide--;
    if (Y.catch_pose) Y.catch_pose--;
    Y.bob = 0;
    if (Y.fill) {
        Y.frame = BT_FILL;
        Y.walk_t = 0; Y.walk_ph = 0;
    } else if (Y.catch_pose) {
        Y.frame = BT_CATCH;
    } else if (walked) {
        Y.frame = walk_cycle[Y.walk_ph];
        Y.bob = !switched & Y.walk_ph;
        if (++Y.walk_t >= WALK_STEP_FRAMES) { Y.walk_t = 0; Y.walk_ph = (Y.walk_ph + 1) & 3; }
    } else {
        Y.frame = Y.slide ? BT_SLIDE : BT_IDLE;
        Y.walk_t = 0; Y.walk_ph = 0;
    }
    // the perfect pour (pour.c pour_frame): the fill frames counted past FILL_FRAMES; released in the window it is PERFECT
    if (Y.fill < FILL_FRAMES) Y.pour_t = 0;
    else if (Y.bar != Y.pour_bar) Y.pour_t = end;
    else if (!Y.pour_t) Y.pour_t = FILL_FRAMES;
    else if (Y.pour_t < end) Y.pour_t++;
    Y.pour_bar = Y.bar;
    Y.pq = Y.pour_t >= POUR_WIN_START && Y.pour_t < end;
}

// ---- Dregs ------------------------------------------------------------------------------------------------------------------
static uint8_t dregs_pick(void) {                // the bar of his next drink (255: no one is thirsty)
    uint8_t b, k, m, i, n = 0, best = 255, bpx, px, cand[PO_SEATS], nc = 0;
    struct po_seat *s = S.seat;
    for (i = PO_SEATS; i; i--, s++) if (s->st == PS_THIRSTY) nc++;
    if (!nc) return 255;
    nc = 0;
    if (S.tune[PT_COMIC] && !(mg_rand() % S.tune[PT_COMIC])) {          // comic waste: a contested seat or a patron about to leave
        s = S.seat;
        for (i = 0; i < PO_SEATS; i++, s++)
            if (s->st == PS_THIRSTY && (seat_k[i] == 1 || s->t < PO_SWAY_AT)) cand[nc++] = i;
        if (nc) return seat_bar[cand[mg_rand() % nc]];
    }
    bpx = 255;
    for (b = 0; b < NUM_BARS; b++) {
        m = S.dfull[b];                          // his drinks in flight on this bar each take the next thirsty seat ahead
        px = 255;
        for (k = 0; k < 3; k++) {
            if (S.seat[b * 3 + k].st != PS_THIRSTY) continue;
            if (m) { m--; continue; }
            px = seat_x[k];
            break;
        }
        if (px == 255) continue;
        if (px < bpx) { bpx = px; best = b; n = 1; }
        else if (px == bpx) { n++; if (!(mg_rand() % n)) best = b; }       // (equal slides: any of them)
    }
    return best;
}

static uint8_t dregs_think_delay(void) {
    uint8_t n = D.score > 15 ? 15 : D.score, t = S.tune[PT_THINK0] - (uint8_t)((uint16_t)(S.tune[PT_THINK0] - S.tune[PT_THINK15]) * n / 15);
    if (D.score >= Y.score + 4) t += S.tune[PT_LEAD];
    else if (Y.score >= D.score + 4) t = t > S.tune[PT_TRAIL] ? t - S.tune[PT_TRAIL] : 1;
    return t ? t : 1;
}

static void dregs_launch(void) {
    if (po_spawn(D.bar, PO_SPOUT_D, 1, PM_FULL, 0)) { D.hold = 0; D.st = PD_SLIDE; D.t = SLIDE_FRAMES; SFX(SFX_LAUNCH); }
    else D.hold = 1;                             // no room: the full glass stays under the spout
}

static void dregs_step(void) {
    uint8_t i, hit;
    if (D.catch_pose) D.catch_pose--;
    if (D.slip) {                                // slipped: out of action
        D.slip--;
        D.frame = BT_FAIL;
        if (!D.slip) { D.st = PD_IDLE; D.t = 0; D.react = 0; }
        return;
    }
    // (1) an empty of his reaching his end within tune[PT_AHEAD] frames (the nearest, as mugs_step saw it last frame)
    hit = S.eta <= S.tune[PT_AHEAD];
    if (hit) {
        if (D.bar == S.ebar) D.react = 0;
        else if (!D.react || D.rbar != S.ebar) { D.react = S.tune[PT_REACT]; D.rbar = S.ebar; }
        else if (--D.react == 0) { D.bar = S.ebar; D.st = PD_WAIT; D.t = 0; }
        if (D.bar == S.ebar && (D.st == PD_IDLE || D.st == PD_THINK)) D.st = PD_WAIT;
    } else {
        D.react = 0;
        if (D.st == PD_WAIT) D.st = PD_IDLE;
    }
    switch (D.st) {
    case PD_IDLE:
        if (D.hold) { dregs_launch(); break; }   // a full drink in his hand: try again
        if (D.t) { D.t--; break; }               // (nobody was thirsty a moment ago)
        i = dregs_pick();
        if (i != 255) { D.bar = i; D.st = PD_THINK; D.t = dregs_think_delay(); }
        else D.t = 3;
        break;
    case PD_THINK:
        if (--D.t == 0) { D.st = PD_FILL; D.t = 0; }
        break;
    case PD_FILL:
        if (D.t < FILL_FRAMES) D.t++;
        else dregs_launch();
        break;
    case PD_SLIDE:
        if (--D.t == 0) D.st = PD_IDLE;
        break;
    default:
        break;
    }
    if ((D.st == PD_FILL) || D.hold) D.frame = BT_FILL;
    else if (D.catch_pose) D.frame = BT_CATCH;
    else D.frame = D.st == PD_SLIDE ? BT_SLIDE : BT_IDLE;
}

// ---- the mugs and the seats -----------------------------------------------------------------------------------------------------
static void lose_life_po(void) {
    if (lives) lives--;
    prep_hud();
    hud_dirty |= HUD_LIVES;
    if (!lives && S.res == PR_PLAY) S.res = PR_LIVES;
}

static void patron_catch(struct po_mug *m, uint8_t seat) {   // a thirsty patron takes the full drink
    struct po_seat *s = &S.seat[seat];
    s->st = PS_DRINKING; s->t = 0; s->who = m->own; s->pf = m->aux; s->dirty = 1; s->sh = 0;
    m->st = PM_HELD; m->aux = seat;
    S.served++;
    S.hudq = 1;
    if (m->own) { D.score++; return; }
    Y.score++;
    add_score(s->pf ? 200 : 100);                // (PERFECT: the story score doubled)
    SFX(SFX_SERVE);
}

static void full_step(struct po_mug *m) {
    uint8_t k, sx, s0 = m->bar * 3, i;
    struct po_seat *s;
    if (m->own) m->x += 2; else m->x -= 2;
    for (i = 0; i < 3; i++) {
        k = m->own ? i : 2 - i;                  // (the seat the drink meets first)
        s = &S.seat[s0 + k];
        if (s->st != PS_THIRSTY) continue;
        sx = seat_x[k];
        if ((uint8_t)(m->x + 8) > sx && m->x < sx + 16) {
            if (!m->own && m->aux) {             // PERFECT: its cue (patron_catch doubles the score)
                SFX(SFX_COIN);
                S.cue_t = PO_CUE_FRAMES; S.cue_x = sx; S.cue_y = bar_oam_y[m->bar] + MUG_DY;   // (left of the patron: the Spigoteer stands to his right)
            }
            patron_catch(m, s0 + k);
            m->x = sx + 8;
            return;
        }
    }
    if ((!m->own && m->x <= PO_SPOUT_D) || (m->own && m->x >= SPOUT_X)) {   // the far end: the other bartender takes it
        m->st = PM_FREE;
        note(1);
    }
}

static void empty_step(struct po_mug *m) {
    if (!m->own) {
        m->x++;
        if (m->bar == Y.bar && m->x >= Y.x && ((uint8_t)(m->x - Y.x) < 16 || Y.x == TAP_X)) {
            m->st = PM_FREE;
            add_score(EMPTY_SCORE);
            SFX(SFX_CATCH);
            Y.catch_pose = CATCH_POSE_FRAMES;
        } else if (m->x > PO_BREAK_Y) {
            m->st = PM_BREAK; m->aux = 0;
            SFX(SFX_BREAK);
            lose_life_po();
        }
    } else {
        m->x--;
        if (m->bar == D.bar && !D.slip && m->x <= PO_CATCH_D) {
            m->st = PM_FREE;
            D.catch_pose = CATCH_POSE_FRAMES;
        } else if (m->x <= PO_BREAK_D) {
            m->st = PM_BREAK; m->aux = 0;
            SFX(SFX_BREAK);
            if (D.score) D.score--;
            S.hudq = 1;
            D.slip = S.tune[PT_SLIP]; D.st = PD_IDLE; D.t = 0;
            note(2);
        }
    }
}

static void mugs_step(void) {                    // every mug one step, and the counts for the next frame's decisions
    uint8_t i, st, e;
    struct po_mug *m = S.mug;
    S.cnt[0] = S.cnt[1] = S.cnt[2] = S.cnt[3] = 0;
    S.dfull[0] = S.dfull[1] = S.dfull[2] = S.dfull[3] = 0;
    S.eta = 255;
    for (i = PO_MUGS; i; i--, m++) {
        st = m->st;
        if (st == PM_FREE) continue;
        if (st == PM_FULL) full_step(m);
        else if (st == PM_EMPTY) empty_step(m);
        else if (st == PM_BREAK && ++m->aux >= 24) m->st = PM_FREE;
        st = m->st;
        if (st == PM_FREE) continue;
        S.cnt[m->bar]++;
        if (!m->own) continue;
        if (st == PM_FULL) S.dfull[m->bar]++;
        else if (st == PM_EMPTY) {               // how long until it reaches his end
            e = m->x > PO_CATCH_D ? m->x - PO_CATCH_D : 0;
            if (e < S.eta) { S.eta = e; S.ebar = m->bar; }
        }
    }
}

static void seats_step(void) {
    uint8_t i, j, n, b, k, tick = !(S.anim & 1);
    struct po_seat *s = S.seat;
    struct po_mug *m;
    for (i = 0; i < PO_SEATS; i++, s++) {
        if (s->st == PS_THIRSTY) {
            if (tick && --s->t == 0) {                   // out of patience: he leaves, nobody scores
                s->st = PS_EMPTY; s->dirty = 1; s->sh = 0;
                continue;
            }
            k = s->t < PO_SWAY_AT && ((uint8_t)(S.anim + 3 * i) >> 3) & 1;   // swaying in the last 120 frames (each seat on its own beat)
            if (k != s->sh) { s->sh = k; s->dirty = 1; }
        } else if (s->st == PS_DRINKING) {
            if (++s->t >= PO_DRINK_FRAMES) {             // done: the empty goes back to its bartender, he leaves
                m = S.mug;
                for (j = PO_MUGS; j; j--, m++) {
                    if (m->st == PM_HELD && m->aux == i) {
                        m->own = s->who; m->aux = 0;
                        m->x = s->who ? seat_x[seat_k[i]] - 8 : seat_x[seat_k[i]] + 16;
                        m->st = PM_EMPTY;
                    }
                }
                s->st = PS_EMPTY; s->dirty = 1; s->sh = 0;
            }
        }
    }
    // a new patron
    if (S.spawn_t) { S.spawn_t--; return; }
    n = Y.score > D.score ? Y.score : D.score;
    S.spawn_t = 50 - ((n * 3) >> 2);                     // 50 frames at the start, 35 at 20
    b = mg_rand() & 3;
    for (j = 0; j < NUM_BARS; j++, b = (b + 1) & 3) {
        k = 0;
        s = &S.seat[b * 3];
        for (i = 0; i < 3; i++) if (s[i].st != PS_EMPTY) k++;
        if (k >= 2) continue;
        i = mg_rand() % 3;
        while (s[i].st != PS_EMPTY) i = i == 2 ? 0 : i + 1;
        s += i;
        s->st = PS_THIRSTY; s->t = PO_PATIENCE; s->v = mg_rand() % 3; s->sh = 0; s->dirty = 1;
        return;
    }
    S.spawn_t = 10;                                      // (no room anywhere: try again soon)
}

// ---- sprites ------------------------------------------------------------------------------------------------------------------------
static void put_bt(uint8_t oam, uint8_t x, uint8_t y, uint8_t base, uint8_t flip, uint8_t prop) {   // 4 entries; x, y: its top-left px
    uint8_t xa = x + 8, xb = x + 16, fl = prop;
    OAM_item_t *o = shadow_OAM + oam;
    if (flip) { xa = x + 16; xb = x + 8; fl |= S_FLIPX; }
    y += 16;
    o->y = y;      o->x = xa; o->tile = base;     o->prop = fl; o++;
    o->y = y;      o->x = xb; o->tile = base + 2; o->prop = fl; o++;
    o->y = y + 16; o->x = xa; o->tile = base + 4; o->prop = fl; o++;
    o->y = y + 16; o->x = xb; o->tile = base + 6; o->prop = fl;
}

static void put_obj(uint8_t oam, uint8_t x, uint8_t y, uint8_t tile, uint8_t prop) {
    OAM_item_t *o = shadow_OAM + oam;
    o->y = y; o->x = x; o->tile = tile; o->prop = prop;
}

static void draw(void) {
    uint8_t i, k, f, t, p, y, n, x, full_p = is_cgb ? OBJPAL_MUG_FULL : 0, empty_p = is_cgb ? OBJPAL_MUG_EMPTY : 0;
    uint8_t t_full = is_cgb ? OBJ_MUG : PO_DMG, t_empty = is_cgb ? OBJ_MUG + 2 : PO_DMG + 2;
    struct po_mug *m = S.mug;
    OAM_item_t *o = shadow_OAM + OAM_MUG0;
    struct po_seat *s;
    put_bt(OAM_YOU, Y.x, BAR_TOP_Y(Y.bar) - Y.bob, OBJ_BARTENDER + Y.frame * BARTENDER_TILES_PER_FRAME, Y.facing, 0);
    f = D.frame;
    put_bt(OAM_DREGS, D.x, BAR_TOP_Y(D.bar), PO_DREGS + f * BARTENDER_TILES_PER_FRAME, f != BT_FILL, is_cgb ? PO_DREGS_PAL : S_PALETTE);
    // the glasses under the spouts
    if (Y.fill || Y.hold) {
        k = Y.hold || Y.fill >= FILL_FRAMES ? 3 : Y.fill >= 2 * FILL_FRAMES / 3 ? 2 : Y.fill >= FILL_FRAMES / 3 ? 1 : 0;
        t = OBJ_MUG_FILL + k * 2; p = full_p;
        if (Y.pour_t >= POUR_WIN_START && !Y.hold) { t = Y.pq ? OBJ_POUR : OBJ_POUR + 2; p = is_cgb ? OBJPAL_MUG_FULL : S_PALETTE; }
        put_obj(OAM_FILL_Y, SPOUT_X + 8, bar_oam_y[Y.bar] + MUG_DY, t, p);
    } else shadow_OAM[OAM_FILL_Y].y = 0;
    if (D.st == PD_FILL || D.hold) {
        k = D.hold || D.t >= FILL_FRAMES ? 3 : D.t >= 2 * FILL_FRAMES / 3 ? 2 : D.t >= FILL_FRAMES / 3 ? 1 : 0;
        put_obj(OAM_FILL_D, PO_SPOUT_D + 8, bar_oam_y[D.bar] + MUG_DY, OBJ_MUG_FILL + k * 2, full_p);
    } else shadow_OAM[OAM_FILL_D].y = 0;
    // the mugs
    for (i = PO_MUGS; i; i--, m++, o++) {
        f = m->st;
        if (f == PM_FREE) { o->y = 0; continue; }
        y = bar_oam_y[m->bar] + MUG_DY;
        x = m->x + 8;
        t = t_empty; p = empty_p;
        switch (f) {
        case PM_FULL: t = t_full; p = full_p; break;
        case PM_HELD:
            s = &S.seat[m->aux];
            n = s->t >= PO_DRINK_FRAMES - 8 ? 3 : s->t >= 40 ? 2 : s->t >= 20 ? 1 : 0;   // the drink goes down, then the empty
            x = seat_x[seat_k[m->aux]] + (s->sh ? 2 : 0) + 16;
            y++;
            if (n == 3) { t = is_cgb ? OBJ_MUG_DRINK + 6 : PO_DMG + 4; }
            else { t = OBJ_MUG_DRINK + n * 2; p = full_p; }
            break;
        case PM_BREAK:                             // blinks out
            if (m->aux & 4) { o->y = 0; continue; }
            break;
        default: break;                            // (PM_EMPTY)
        }
        o->y = y; o->x = x; o->tile = t; o->prop = p;
    }
    // the PERFECT cue, only where the lines have room (never an 11th object on a line)
    shadow_OAM[OAM_CUE_PO].y = 0;
    if (S.cue_t) {
        S.cue_t--;
        if ((S.cue_t & 3) == 1) {                // (every 4th frame, never the catch frame itself: the lines are counted a few frames on)
            n = 0;
            y = S.cue_y;
            for (i = 0, f = 0; i < OAM_CUE_PO; i++, f += 4)       // (OAM 0-25 are everything else)
                if (((uint8_t *)shadow_OAM)[f] && (uint8_t)(((uint8_t *)shadow_OAM)[f] - y + 15) < 31) n++;
            S.cue_ok = n < LINE_OBJ_MAX;
        }
        if (S.cue_ok && (S.cue_t > 16 || (S.cue_t & 4))) put_obj(OAM_CUE_PO, S.cue_x, S.cue_y, OBJ_POUR_CUE, full_p);
    }
}

// ---- the game --------------------------------------------------------------------------------------------------------------------------
static void finish(uint8_t res) {
    uint8_t i;
    struct po_mug *m = S.mug;
    S.res = res;
    S.note_t = 0;
    mg_finish();
    band(res == PR_WIN ? 3 : res == PR_DREGS ? 4 : 5);
    for (i = PO_MUGS; i; i--, m++) if (m->st == PM_BREAK) m->st = PM_FREE;
    SFX(res == PR_WIN ? SFX_SERVE : SFX_LIFE);
}

void po_update(uint8_t pressed) BANKED {
    uint8_t i, n = 0;
    struct po_seat *s;
    if (S.started < 3) {                         // the first frames: stage rows 1-3 (the framework's banner) come back, a row a frame
        vq_add(0, S.wall[S.started], 0, 1 + S.started, 20);
        if (is_cgb) vq_add(1, S.wattr[S.started], 0, 1 + S.started, 20);
        S.started++;
    }
    if (S.hudq) { S.hudq = 0; put_hud(); vq_add(0, S.hud, 13, HUD_ROW, 7); }          // (first: what a catch changed is drawn the frame after it)
    s = S.seat;
    for (i = 0; i < PO_SEATS && !n; i++, s++)            // (one seat a frame: the sways are on different beats)
        if (s->dirty) { seat_draw(i); n++; }
    if (S.pend) {                                // the band's text (its blank row 1 went last frame)
        mg_say(MG_TEXT_A, band_txt[S.pend]);
        if (is_cgb) vq_add(1, S.hattr, 0, MG_TEXT_A, 20);
        S.pend = 0;
    }
    S.anim++;
    if (S.res == PR_PLAY && mg_phase == MG_END) S.res = PR_LIVES;     // (a test ended the game early)
    if (S.res == PR_PLAY) {
        you_step(pressed);
        dregs_step();
        mugs_step();
        seats_step();
        if (Y.score >= PO_WIN) finish(PR_WIN);
        else if (D.score >= PO_WIN) finish(PR_DREGS);
        else if (S.res == PR_LIVES) finish(PR_LIVES);
        if (S.note_t) {                          // (the note goes: row 1, then row 2 a frame later)
            if (--S.note_t == 1) note_off(1);
            else if (!S.note_t) note_off(2);
        }
    } else {                                     // the outro: the end pose, the drinks as they were
        struct po_mug *m = S.mug;
        Y.frame = S.res == PR_WIN ? BT_CATCH : BT_FAIL;
        D.frame = S.res == PR_WIN ? BT_FAIL : BT_CATCH;
        D.st = PD_IDLE;
        Y.fill = 0; Y.hold = 0; D.hold = 0;
        for (i = PO_MUGS; i; i--, m++) if (m->st == PM_BREAK && ++m->aux >= 24) m->st = PM_FREE;
    }
    draw();
}
