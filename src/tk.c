// TAIKO POUR, the teahouse's mini-game (docs/minigames_bosses.md 4.7; art approved by the owner 2026-10-12: look B "sakura
// stream"). The drummer sets the beat of "Sakura Sakura"; notes slide along two water lanes to the hit marks: A hits the top
// lane (the don, a lit paper lantern), B the bottom lane (the ka, an empty lantern frame). A good hit pours tea; eight fill
// a bowl for a guest.
//
// Rules (the spec's numbers; tools/taiko_chart.py has the chart):
// - Notes move left at 1.5 px a frame from x 160 to the hit mark at x 24: 91 frames of look-ahead (spawned at 93 frames, the
//   last that fits the screen: no note waits off-screen on a scanline).
// - A press judges the earliest note of its lane not judged yet within 10 frames (T = the note's hit time): PERFECT within 3,
//   GOOD within 6, else MISS (the note is spent, the combo ends). A press with no such note is a SPILL (-50, never below what
//   this game earned, combo ends). A note not pressed by T + 10 is a MISS too, and slides on to x < 6, where it is dropped (the
//   proposal's engine rule: with the 22 px spacing, an 8th note on a lane line plus the hit flash made 10 sprites).
// - Score: PERFECT 300, GOOD 100, plus 10 for each note of the combo counting this one (at most 100); each 8 GOOD-or-better
//   notes serve a bowl (+500). Medal by accuracy (PERFECT 1, GOOD 0.5, of all the notes): GOLD >= 90%, SILVER >= 75%,
//   BRONZE >= 50%. One setting (the spec has no HARD).
// - Sync: the clock is src/music.c's music_frames (frames since the tune's first row), so a late frame never drifts the
//   chart: a note's x is computed from the clock, not stepped. With MUSIC OFF (owner Q4: silent, but playable) the game
//   counts its own frames from the same start (the framework's intro + count are about 150 frames).
// - The count-in: the banner rows show 1 2 3 4 on the beats before the first note (bar 4), then the shoji window comes back.
//   Visual metronome: the stone banks flash on each beat (their tile data is swapped), the drummer dances on it.
// - Sounds: a hit on lane A SFX_DON, on lane B SFX_KA (perfect or good alike; the flash colour tells them), SPILL BREAK, a bowl served SERVE.
//
// Screen (the approved mock-up): HUD row 0 (score; combo icon + X + 2 digits at columns 8-11; cups icon + X + 2 digits at 16-19 (a perfect game serves 14 bowls));
// the shoji window rows 1-4 (CGB BG palette 3; the lantern flickers; the banner rows 2-3 hold the framework's text until the
// first note nears); the banks on rows 5, 8, 11; lanes rows 6-7 and 9-10 (palette 2) with the hit marks at columns 2-3; the
// bamboo blind rows 12-13 (palette 5); the framework's teahouse wall and floor below; the bowl at columns 13-14, rows 15-16
// (palette 6, colour 0 the wall's). OAM: 0-3 the Spigoteer (the fill pose, mirrored, holding the pot), 4-5 the pot, 6 the
// stream, 7 the steam / the spill, 8-11 the hit flashes (a lane each), 12-15 the drummer (the show's tiles and palette 5),
// 16-27 the notes. CGB OBJ: 0 the Spigoteer, 1 don, 2 ka, 3 flashes, 7 pot, 5 drummer, 6 stream / steam / spill (4 is left alone). DMG: the
// Spigoteer on OBP0, the rest on OBP1 (set here).
// Tiles: BG TK_BG.. (MG_GAME_BG, ids 125-185), OBJ 56-91; all put back by the next level load.
#pragma bank 255
#include <gb/gb.h>
#include <gb/cgb.h>
#include <stdint.h>

#include "game.h"
#include "music.h"
#include "mg.h"
#include "tk_art.h"         // this bank's own art and chart (assets/art/taiko/*.txt, tools/taiko_chart.py)

#define S               (MG->tk)
#define TK_BG           MG_GAME_BG
#define TK_OBJ          OBJ_MUG             // 56..91 (the drink frames: the level load puts them back)
typedef char tk_fits[(TK_OBJ + TK_OBJ_TILES <= OBJ_COIN && TK_BG + TK_BG_TILES <= 256
                      && sizeof(struct tk_state) <= STORY_SCRATCH) ? 1 : -1];
#define TK_SPAWN       93                   // frames before T a note appears (x 163: its sprite's left edge is 159)
#define TK_PERFECT      3
#define TK_GOOD         6
#define TK_REACH       10                   // a press this near a note judges it; later than this the note is a miss
#define TK_DROP        12                   // c - T > 12: x < 6, the note is dropped (the engine rule)
#define TK_HIT_X       24                   // the hit mark's centre
#define TK_BEAT        24                   // frames a quarter note
#define TK_FLASH_LEN    8                   // the banks lit at each beat
#define TK_COUNT_AT   192                   // the first count-in digit's beat (bar 3); FIRST is bar 4
#define TK_FIRST      288
#define TK_END_WAIT    45                   // frames after the last note before the game ends
#define TK_POUR_LEN    16
#define TK_SPILL_LEN   36
#define TK_SERVE_LEN   70
#define TK_PTS_PERFECT 300
#define TK_PTS_GOOD    100
#define TK_PTS_COMBO    10                  // per note of the combo, at most TK_COMBO_MAX notes
#define TK_COMBO_MAX   10
#define TK_PTS_CUP     500
#define TK_PTS_SPILL    50
#define TK_CUP_HITS     8
#define TK_OWN_START  150                   // MUSIC OFF: the own clock at the first play frame (the intro + count)
#define OAM_SPIG        0
#define OAM_POT         4
#define OAM_STREAM      6
#define OAM_STEAM       7
#define OAM_FLASH       8
#define OAM_DRUM       12
#define OAM_NOTES      16
#define OAM_N          (OAM_NOTES + TK_LIVE)
#define SPIG_X         80
#define SPIG_Y        112
#define POT_X          94
#define POT_Y         118
#define STREAM_X      108
#define STREAM_Y      120
#define STEAM_X       108
#define STEAM_Y       104
#define SPILL_X       124
#define SPILL_Y       128
#define DRUM_X         16
#define DRUM_Y        112
#define MARK_COL        2
#define CUP_COL        13
#define CUP_ROW        15
#define PAL_LANE        2
#define PAL_SHOJI       3
#define PAL_BLIND       5
#define PAL_BOWL        6
#define OPAL_DON        1
#define OPAL_KA         2
#define OPAL_FLASH      3
#define OPAL_POT        7                   // (not 4: OBJPAL_ENH is not put back by the level load)
#define OPAL_DRUM       OBJPAL_DANCER       // 5: the show's (load_venue)
#define OPAL_TEA        6
#define SPIG_FILL       BT_FILL
#define SPIG_FAIL       BT_FAIL
typedef struct { uint8_t n, bank; const uint8_t *src; uint8_t *dst; uint8_t pad[2]; } vq_entry_t;   // src/render.c's copy list
extern vq_entry_t vq[];
extern uint8_t vq_count;
extern uint32_t score;
extern uint8_t score_digits[6];
#define RGB15(r, g, b) ((uint16_t)((r) | ((g) << 5) | ((b) << 10)))
#define HEX(v)  RGB15(((v) >> 19) & 31, ((v) >> 11) & 31, ((v) >> 3) & 31)

static const uint8_t lane_y[2] = { 48, 72 };    // the lanes' top lines (map rows 6 and 9)
static const uint16_t pal_shoji[4] = { HEX(0xF8F0E0UL), HEX(0xF088A8UL), HEX(0x785038UL), HEX(0x281810UL) };
static const uint16_t pal_lane[4]  = { HEX(0xE0F0E8UL), HEX(0x78C0D0UL), HEX(0x387888UL), HEX(0x183040UL) };
static const uint16_t pal_blind[4] = { HEX(0xE8F0B8UL), HEX(0xA0C060UL), HEX(0x587830UL), HEX(0x203010UL) };
static const uint16_t pal_don[4]   = { 0, HEX(0xF8D868UL), HEX(0xE04058UL), HEX(0x301020UL) };
static const uint16_t pal_ka[4]    = { 0, HEX(0xF8C0D0UL), HEX(0xF080A0UL), HEX(0x402040UL) };
static const uint16_t pal_flash[4] = { 0, HEX(0xF8F8E0UL), HEX(0xF88098UL), HEX(0xC03060UL) };
static const uint16_t pal_pot[4]   = { 0, HEX(0xB8C0C8UL), HEX(0x687080UL), HEX(0x181828UL) };
static const uint16_t pal_tea[4]   = { 0, HEX(0xF8F0D8UL), HEX(0x78C040UL), HEX(0x181830UL) };

static void put(uint8_t bank, uint8_t *t, uint8_t col, uint8_t row, uint8_t n) {   // LCD on: the queue; off: at once
    if (LCDC_REG & LCDCF_ON) { vq_add(bank, t, col, row, n); return; }
    if (bank) VBK_REG = VBK_BANK_1;
    vram_put(col, row, t, n);
    VBK_REG = VBK_BANK_0;
}

static void attr_row(uint8_t row, uint8_t pal, uint8_t col, uint8_t n) {   // LCD off, CGB
    uint8_t i;
    for (i = 0; i < n; i++) row_buf[i] = pal;
    VBK_REG = VBK_BANK_1;
    vram_put(col, row, row_buf, n);
    VBK_REG = VBK_BANK_0;
}

static uint8_t *tile_addr(uint8_t id) {             // BG ids 0-127 are at 0x9000, 128-255 at 0x8800 (LCDC bit 4 clear)
    return (uint8_t *)(id < 128 ? 0x9000 + (uint16_t)id * 16 : 0x8800 + (uint16_t)(id - 128) * 16);
}

static void digits(uint8_t n, uint8_t *d) {         // two digit tiles of n (0..99)
    uint8_t t = 0;
    while (n >= 10) { n -= 10; t++; }
    d[0] = TILE_GLYPH_0 + t; d[1] = TILE_GLYPH_0 + n;
}

static void hud_combo(void) {
    digits(S.combo > 99 ? 99 : S.combo, S.hud);
    put(0, S.hud, 10, HUD_ROW, 2);
}

static void hud_cups(void) {
    digits(S.cups > 99 ? 99 : S.cups, S.hud + 2);
    put(0, S.hud + 2, 18, HUD_ROW, 2);
}

// the bowl: state 0..4 (empty .. full) at columns 13-14, rows 15-16
static void cup(uint8_t st) {
    const uint8_t *m = tk_cup_map + 4 * st;
    uint8_t k;
    if (S.cup_shown == st) return;
    S.cup_shown = st;
    for (k = 0; k < 4; k++) S.cup[k >> 1][k & 1] = TK_BG + TKB_CUP + m[k];
    put(0, S.cup[0], CUP_COL, CUP_ROW, 2);
    put(0, S.cup[1], CUP_COL, CUP_ROW + 1, 2);
}

// ---- the sprites ----
static void obj(uint8_t oam, uint8_t x, uint8_t y, uint8_t t, uint8_t prop) {      // one 8x16 entry, px top-left
    OAM_item_t *o = shadow_OAM + oam;
    o->y = y + 16; o->x = x + 8; o->tile = t; o->prop = prop;
}

static void obj2(uint8_t oam, uint8_t x, uint8_t y, uint8_t t, uint8_t prop) {     // a 16x16 pair: tiles t, t + 2
    obj(oam, x, y, t, prop);
    obj(oam + 1, x + 8, y, t + 2, prop);
}

static void hide(uint8_t oam) { shadow_OAM[oam].y = 0; }

static uint8_t cgb(uint8_t pal) { return is_cgb ? pal : S_PALETTE; }   // an OBJ prop: CGB palette, DMG OBP1

static void sprites(void) {
    uint8_t k, f, i, lane, x, spill = S.spill_t != 0;
    int16_t d, cx;
    const uint8_t *w;
    mg_spigoteer(SPIG_X, SPIG_Y, spill ? SPIG_FAIL : SPIG_FILL, 1, OAM_SPIG);
    // the pot: level, tilted while pouring
    f = TKO_POT_0;
    if (S.pour_t) f = S.pour_t > 13 || S.pour_t < 4 ? TKO_POT_1 : TKO_POT_2;   // tilts, pours, tilts back
    obj2(OAM_POT, POT_X, POT_Y, TK_OBJ + f, cgb(OPAL_POT));
    if (S.pour_t >= 4 && S.pour_t <= 13)                 // the stream, while the pot pours
        obj(OAM_STREAM, STREAM_X, STREAM_Y, TK_OBJ + ((S.pour_t >> 1) & 1 ? TKO_STREAM_1 : TKO_STREAM_0), cgb(OPAL_TEA));
    else hide(OAM_STREAM);
    if (spill) obj(OAM_STEAM, SPILL_X, SPILL_Y, TK_OBJ + ((S.spill_t >> 3) & 1 ? TKO_SPILL_1 : TKO_SPILL_0),
                   cgb(OPAL_TEA));
    else if (S.serve_t) obj(OAM_STEAM, STEAM_X, STEAM_Y, TK_OBJ + ((S.anim >> 3) & 1 ? TKO_STEAM_1 : TKO_STEAM_0),
                            cgb(OPAL_TEA));
    else hide(OAM_STEAM);
    for (lane = 0; lane < 2; lane++) {                  // the hit flashes
        if (S.flash_t[lane])
            obj2(OAM_FLASH + 2 * lane, MARK_COL * 8, lane_y[lane], TK_OBJ + (S.flash_k[lane] ? TKO_FLASH_G : TKO_FLASH_P),
                 cgb(OPAL_FLASH));
        else { hide(OAM_FLASH + 2 * lane); hide(OAM_FLASH + 2 * lane + 1); }
    }
    // the drummer: his rest pose, a dance step on each beat's first half (the whole show's tiles, as the level has them)
    f = 0;
    if ((mg_phase == MG_PLAY || mg_phase == MG_END) && (uint8_t)(S.clk % TK_BEAT) < 12) f = 1 + (uint8_t)((S.clk / TK_BEAT) % 3);
    w = venue.show_tile[f];
    obj(OAM_DRUM, DRUM_X, DRUM_Y, OBJ_DANCER + w[0], cgb(OPAL_DRUM));
    obj(OAM_DRUM + 1, DRUM_X + 8, DRUM_Y, OBJ_DANCER + w[1], cgb(OPAL_DRUM));
    obj(OAM_DRUM + 2, DRUM_X, DRUM_Y + 16, OBJ_DANCER + w[2], cgb(OPAL_DRUM));
    obj(OAM_DRUM + 3, DRUM_X + 8, DRUM_Y + 16, OBJ_DANCER + w[3], cgb(OPAL_DRUM));
    // the notes
    for (k = 0; k < TK_LIVE; k++) {
        i = S.live[k];
        if (i == 255) { hide(OAM_NOTES + k); continue; }
        lane = tk_chart[i & 0x7F] >> 15;
        d = (int16_t)(tk_chart[i & 0x7F] & 0x7FFF) - (int16_t)S.clk;
        cx = TK_HIT_X + d + (d >> 1);                   // 1.5 px a frame
        if (cx - 4 >= 160 || cx < 6) { hide(OAM_NOTES + k); continue; }
        x = (uint8_t)(cx - 4);
        obj(OAM_NOTES + k, x, lane_y[lane], TK_OBJ + (lane ? TKO_KA : TKO_DON), cgb(lane ? OPAL_KA : OPAL_DON));
    }
}

// ---- the screen ----
static void rails_data(uint8_t on) {                    // the banks' lit / dim tile data (one tile, 16 bytes at VBlank)
    S.rail_on = on;
    vq_add(0, S.rail[on], 0, 0, 16);
    vq[vq_count - 1].dst = tile_addr(TK_BG + TKB_RAIL);
}

static void lantern(uint8_t on) {                       // the lantern's 2x2 tiles: frame 0 or frame 1
    uint8_t r, c, y = TK_LANT_Y, x = TK_LANT_X, t;
    S.lant_on = on;
    for (r = 0; r < TK_BAND_ROWS; r++)
        for (c = 0; c < TK_LANT_W; c++) {
            t = on ? tk_band_alt[r * TK_LANT_W + c] : tk_band_map[(y + r) * 20 + x + c];
            S.lant[r][c] = TK_BG + TKB_BAND + t;
        }
    for (r = 0; r < TK_BAND_ROWS; r++) put(0, S.lant[r], x, 1 + y + r, TK_LANT_W);
}

static void band_rows(void) {                           // the shoji window's rows 2-3 (the banner's place) as tiles
    uint8_t r, c;
    for (r = 0; r < 2; r++)
        for (c = 0; c < 20; c++) S.band[r][c] = TK_BG + TKB_BAND + tk_band_map[(1 + r) * 20 + c];
    for (c = 0; c < 20; c++) S.pal[c] = PAL_SHOJI;
}

void tk_enter(void) BANKED {
    uint16_t p[4];
    uint8_t r, c, k;
    set_bkg_data(TK_BG, TK_BG_TILES, tk_bg_tiles);
    set_sprite_data(TK_OBJ, TK_OBJ_TILES, tk_obj_tiles);
    for (k = 0; k < 16; k++) {                          // the banks' two tile states, from the BG data just loaded
        S.rail[0][k] = tk_bg_tiles[(TKB_RAIL + 0) * 16 + k];
        S.rail[1][k] = tk_bg_tiles[(TKB_RAIL + 1) * 16 + k];
    }
    // the screen, row by row (the framework drew the wall and floor; rows 1-13 are all this game's)
    for (r = 0; r < 4; r++) {                           // the shoji window
        for (c = 0; c < 20; c++) row_buf[c] = TK_BG + TKB_BAND + tk_band_map[r * 20 + c];
        vram_put(0, 1 + r, row_buf, 20);
    }
    for (r = 5; r <= 11; r++) {                         // banks (5, 8, 11) and lanes (6-7, 9-10)
        for (c = 0; c < 20; c++) {
            if (r == 5 || r == 8 || r == 11) k = TKB_RAIL;
            else k = TKB_LANE + (r == 6 || r == 9 ? 0 : 1);
            row_buf[c] = TK_BG + k;
        }
        vram_put(0, r, row_buf, 20);
    }
    for (r = 0; r < 2; r++) {                           // the hit marks: A on rows 6-7, B on rows 9-10, columns 2-3
        row_buf[0] = TK_BG + TKB_MARK + 4 * 0 + 2 * r;     row_buf[1] = TK_BG + TKB_MARK + 4 * 0 + 2 * r + 1;
        vram_put(MARK_COL, 6 + r, row_buf, 2);
        row_buf[0] = TK_BG + TKB_MARK + 4 * 1 + 2 * r;     row_buf[1] = TK_BG + TKB_MARK + 4 * 1 + 2 * r + 1;
        vram_put(MARK_COL, 9 + r, row_buf, 2);
    }
    for (r = 0; r < 2; r++) {                           // the bamboo blind, rows 12-13
        for (c = 0; c < 20; c++) row_buf[c] = TK_BG + TKB_BLIND + r;
        vram_put(0, 12 + r, row_buf, 20);
    }
    S.cup_shown = 255;
    cup(0);
    // the HUD: the combo icon, X, two digits at columns 8-11; the cups icon, X, two digits at 16-19
    row_buf[0] = TK_BG + TKB_HUD; row_buf[1] = TILE_GLYPH_X;
    vram_put(8, HUD_ROW, row_buf, 2);
    row_buf[0] = TK_BG + TKB_HUD + 1; row_buf[1] = TILE_GLYPH_X;
    vram_put(16, HUD_ROW, row_buf, 2);
    if (is_cgb) {
        for (r = 1; r <= 4; r++) attr_row(r, PAL_SHOJI, 0, 20);
        for (r = 5; r <= 11; r++) attr_row(r, PAL_LANE, 0, 20);
        attr_row(12, PAL_BLIND, 0, 20); attr_row(13, PAL_BLIND, 0, 20);
        attr_row(CUP_ROW, PAL_BOWL, CUP_COL, 2); attr_row(CUP_ROW + 1, PAL_BOWL, CUP_COL, 2);
        set_bkg_palette(PAL_SHOJI, 1, pal_shoji);
        set_bkg_palette(PAL_LANE, 1, pal_lane);
        set_bkg_palette(PAL_BLIND, 1, pal_blind);
        p[0] = venue.pal[VENUE_PAL_BAR][0];              // the wall's colour round the bowl
        p[1] = pal_tea[1]; p[2] = pal_tea[2]; p[3] = pal_tea[3];
        set_bkg_palette(PAL_BOWL, 1, p);
        set_sprite_palette(OPAL_DON, 1, pal_don);
        set_sprite_palette(OPAL_KA, 1, pal_ka);
        set_sprite_palette(OPAL_FLASH, 1, pal_flash);
        set_sprite_palette(OPAL_POT, 1, pal_pot);
        set_sprite_palette(OPAL_TEA, 1, pal_tea);
        set_sprite_palette(OPAL_DRUM, 1, venue.pal[VENUE_PAL_SHOW]);
    } else OBP1_REG = 0xE4;                              // the notes, pot, drummer: the usual OBP1 (a Practice run may come from Order Up!'s 0xC4)
    // the tune from its first row (a looping tune already playing is not restarted by music_play); the count is in tune frames
    music_fast = 0;
    music_stop();
    S.clk = 0; S.own = TK_OWN_START; S.next = 0; S.judged = 0; S.combo = 0; S.best = 0; S.hits = 0; S.cups = 0;
    S.perfect = S.good = S.miss = S.spills = 0; S.cnt = 0; S.band_on = 0; S.end_t = 0; S.anim = 0; S.pour_t = 0;
    S.spill_t = 0; S.serve_t = 0; S.flash_t[0] = S.flash_t[1] = 0; S.flash_k[0] = S.flash_k[1] = 0;
    S.rail_on = 0; S.lant_on = 0; S.last = 0;
    for (k = 0; k < TK_LIVE; k++) S.live[k] = 255;
    band_rows();
    S.combo = 0; hud_combo(); hud_cups();
    backing();
    sprites();
}

uint8_t tk_medal(void) BANKED {
    uint16_t a2 = 2 * (uint16_t)S.perfect + S.good;      // accuracy in half notes, of 2 x TK_NOTES
    if (10 * a2 >= 18 * (uint16_t)TK_NOTES) return MEDAL_GOLD;
    if (2 * a2 >= 3 * (uint16_t)TK_NOTES) return MEDAL_SILVER;
    return a2 >= TK_NOTES ? MEDAL_BRONZE : MEDAL_NONE;
}

// ---- the game ----
static uint16_t note_t(uint8_t i) { return tk_chart[i] & 0x7FFF; }

static void spill_penalty(void) {                         // -50, never below what this game earned
    uint16_t n = mg_score < TK_PTS_SPILL ? mg_score : TK_PTS_SPILL;
    mg_score -= n;
    score -= n;
    split6(score_digits, score);
    hud_dirty |= HUD_SCORE;
    prep_hud();
}

static void judged(uint8_t slot) {                        // note in `slot` is resolved: out of the live list
    S.live[slot] = 255;
    S.judged++;
}

static void hit(uint8_t lane, uint8_t slot, uint8_t perfect) {
    uint8_t c;
    uint16_t pts = perfect ? TK_PTS_PERFECT : TK_PTS_GOOD;
    judged(slot);
    if (perfect) S.perfect++; else S.good++;
    if (S.combo < 255) S.combo++;
    if (S.combo > S.best) S.best = S.combo;
    c = S.combo > TK_COMBO_MAX ? TK_COMBO_MAX : S.combo;
    mg_points(pts + (uint16_t)TK_PTS_COMBO * c);
    S.last = perfect ? 1 : 2;
    S.flash_t[lane] = TK_FLASH_LEN; S.flash_k[lane] = !perfect;
    S.pour_t = TK_POUR_LEN;
    if (lane) SFX(SFX_KA); else SFX(SFX_DON);              // A: the drum's centre, B: the rim (perfect or good)
    hud_combo();
    if (++S.hits >= TK_CUP_HITS) {                         // a bowl served
        S.hits = 0; S.cups++;
        S.serve_t = TK_SERVE_LEN;
        mg_points(TK_PTS_CUP);
        SFX(SFX_SERVE);
        hud_cups();
    }
}

static void lose_combo(void) {
    if (S.combo) { S.combo = 0; hud_combo(); }
}

static void press(uint8_t lane, uint16_t c) {
    uint8_t k, i, found = 255;
    int16_t d;
    for (k = 0; k < TK_LIVE; k++) {
        i = S.live[k];
        if (i == 255 || (i & 0x80) || (tk_chart[i] >> 15) != lane) continue;
        d = (int16_t)c - (int16_t)note_t(i);
        if (d < -TK_REACH) break;                          // (live is in time order: nothing nearer follows)
        if (d <= TK_REACH) { found = k; break; }
    }
    if (found == 255) {                                    // SPILL
        S.spills++; S.last = 4;
        lose_combo();
        spill_penalty();
        S.spill_t = TK_SPILL_LEN;
        SFX(SFX_BREAK);
        return;
    }
    i = S.live[found];
    d = (int16_t)c - (int16_t)note_t(i);
    if (d < 0) d = -d;
    if (d <= TK_GOOD) { hit(lane, found, d <= TK_PERFECT); return; }
    S.live[found] = i | 0x80;                              // MISS: spent, slides on
    S.miss++; S.judged++; S.last = 3;
    lose_combo();
}

static void count_in(uint16_t c) {
    static const char *const num[4] = { "1", "2", "3", "4" };
    if (S.cnt < 4 && c >= TK_COUNT_AT + TK_BEAT * S.cnt) {
        S.cnt++;
        if (c < TK_COUNT_AT + TK_BEAT * S.cnt) mg_say(MG_TEXT_A, num[S.cnt - 1]);
    }
    if (S.band_on == 0 && c >= TK_FIRST - TK_BEAT / 2 && S.cnt >= 4) {    // the window comes back to the banner rows
        band_rows();
        put(0, S.band[0], 0, 2, 20); put(0, S.band[1], 0, 3, 20);
        if (is_cgb) { put(1, S.pal, 0, 2, 20); put(1, S.pal, 0, 3, 20); }
        S.band_on = 1;
    }
}

static void notes_update(uint16_t c, uint8_t pressed) {
    uint8_t k, i, n;
    int16_t d;
    // drop what passed (x < 6); a note not pressed by T + 10 is a miss
    for (k = 0; k < TK_LIVE; k++) {
        i = S.live[k];
        if (i == 255) continue;
        d = (int16_t)c - (int16_t)note_t(i & 0x7F);
        if (d > TK_REACH && !(i & 0x80)) { S.live[k] = i |= 0x80; S.miss++; S.judged++; S.last = 3; lose_combo(); }
        if (d > TK_DROP) S.live[k] = 255;
    }
    // compact (time order), then spawn
    for (k = 0, n = 0; k < TK_LIVE; k++)
        if (S.live[k] != 255) S.live[n++] = S.live[k];
    for (k = n; k < TK_LIVE; k++) S.live[k] = 255;
    while (S.next < TK_NOTES && n < TK_LIVE && (int16_t)note_t(S.next) - (int16_t)c <= TK_SPAWN) S.live[n++] = S.next++;
    if (pressed & J_A) press(0, c);
    if (pressed & J_B) press(1, c);
}

#if TAIKO_VARIANT
// ---- the drum's pitched body (src/music.h TAIKO_VARIANT; the noise layer is SFX_DON / SFX_KA, src/music.c) ----
// A hit's age is TK_FLASH_LEN - 1 - flash_t (0 on the frame of the press), so the drum needs no state of its own: on age 0
// the pulse channel is triggered (the hardware length counter ends it), on the next frames its period is slid down by hand.
// DON: a knock then a thump: period TKD_PK (~240 Hz) on age 0, then TKD_P1 (120 Hz) falling by TKD_PS a frame to ~85 Hz
// (period p sounds 131072 / (2048 - p) Hz), envelope 0xF2 (15, one step a 2/64 s), cut by the length counter after 14 frames.
// KA: a high short pulse (12.5 % duty, ~2 kHz) cut after 4 frames.
// The pulse is channel 2 (D1: the melody's channel), channels 2 and 1 together (D2: 50 % and 25 % duty, twice the level),
// or channel 1 (D3).
#define TKD_PK  1500
#define TKD_P1   956
#define TKD_PS   -91
#define TKD_PKA 1985
#define TKD_LEN_DON  4                      // the length counter: (64 - 4) / 256 s = 14 frames
#define TKD_LEN_KA  47                      // 17 / 256 s = 4 frames
#if TAIKO_VARIANT == 1
#define TKD_N 1                             // channel 2 only
#elif TAIKO_VARIANT == 2
#define TKD_N 2                             // channel 2, then channel 1
#else
#define TKD_N 1
#endif
#if TAIKO_VARIANT == 3
#define TKD_FIRST 0xFF10                    // NR10..NR14
#else
#define TKD_FIRST 0xFF15                    // (unused) NR21..NR24; the second pulse of D2 is five bytes below
#endif
static void pulse(volatile uint8_t *r, uint8_t age, uint8_t dl, uint16_t p) {   // r[0..4]: NR10 / (NR20) .. NR14 / NR24
    if (age) { r[3] = (uint8_t)p; r[4] = 0x40 | (p >> 8); return; }   // (a retune: no trigger, the length counter stays on)
    r[0] = 0; r[1] = dl; r[2] = 0xF2;
    r[3] = (uint8_t)p; r[4] = 0xC0 | (p >> 8);
}

static void drum(void) {                                   // after the flash timers: the pulse body of the youngest hit
    uint8_t a, b, ka = 0;
    uint16_t p;
    if (S.flash_t[0]) a = TK_FLASH_LEN - 1 - S.flash_t[0];
    else if (S.flash_t[1]) a = 255;
    else return;
    if (S.flash_t[1]) {
        b = TK_FLASH_LEN - 1 - S.flash_t[1];
        if (b < a) { a = b; ka = 1; }
    }
    if (ka && a) return;                                   // (the KA is a click: one write, the length counter ends it)
    p = ka ? TKD_PKA : a ? TKD_P1 + (a - 1) * TKD_PS : TKD_PK;
    pulse((volatile uint8_t *)TKD_FIRST, a, ka ? TKD_LEN_KA : 0x80 | TKD_LEN_DON, p);
#if TKD_N == 2
    pulse((volatile uint8_t *)(TKD_FIRST - 5), a, ka ? TKD_LEN_KA : 0x40 | TKD_LEN_DON, p);
#endif
}
#endif

// What the tune does behind the drums (src/music.h TAIKO_VARIANT): kept in hUGE_mute_mask's spare bits, set again every frame.
static void backing(void) {
    uint8_t m = hUGE_mute_mask | TK_NOGROOVE;
#if TAIKO_VARIANT == 1
    m |= TK_NOMELODY | 2;
    NR51_REG = 0xBF;                                        // the bass (channel 3) to the right side only: -6 dB on the speaker
#elif TAIKO_VARIANT == 2
    m |= TK_NOMELODY | TK_NOHARM | 2;
    NR51_REG = 0xBF;                                        // the bass (channel 3) to the right side only: -6 dB on the speaker
#elif TAIKO_VARIANT == 3
    {                                                       // the melody sounds only where a half bar begins (its row start is
        uint8_t ph = (uint8_t)(S.clk % 48);                 // the tick after clock 47 mod 48; a frame either side is harmless)
        m |= TK_NOHARM | TK_NOMELODY;
        NR51_REG = 0x9F;                                    // melody and bass to the right side only: -6 dB
        if (ph == 46 || ph == 47 || ph == 0) m &= ~2; else m |= 2;
    }
#endif
    hUGE_mute_mask = m;
}

void tk_leave(void) BANKED {                               // mg_leave: the tune goes back to its full band
    volatile uint8_t *r;
    hUGE_mute_mask &= ~(TK_HOLD | 2);
#if TAIKO_VARIANT
    r = (volatile uint8_t *)TKD_FIRST; r[2] = 0x08; r[4] = 0x80;   // (the pulses: volume 0, the DAC kept on: no click)
#if TKD_N == 2
    r = (volatile uint8_t *)(TKD_FIRST - 5); r[2] = 0x08; r[4] = 0x80;
#endif
    NR51_REG = 0xFF;                                       // (every channel to both sides again)
#endif
}

void tk_update(uint8_t pressed) BANKED {
    uint16_t c;
    uint8_t want;
    if (sound_on) c = music_frames;                       // (before S.anim++: SDCC fuses that inc (hl) with the test into an `or a, (hl)`)
    else { c = S.own + 1; S.own = c; }
    S.clk = c;
    S.anim++;
    if (mg_phase == MG_PLAY) {
        count_in(c);
        notes_update(c, pressed);
        if (S.judged >= TK_NOTES && S.next >= TK_NOTES) {
            if (++S.end_t >= TK_END_WAIT) mg_finish();
        }
    }
    if (S.pour_t) S.pour_t--;
    if (S.spill_t) S.spill_t--;
    if (S.serve_t) S.serve_t--;
    if (S.flash_t[0]) S.flash_t[0]--;
    if (S.flash_t[1]) S.flash_t[1]--;
    cup(S.serve_t ? 4 : S.hits >> 1);
    want = mg_phase == MG_PLAY && (uint8_t)(c % TK_BEAT) < TK_FLASH_LEN;   // the beat's flash on the banks
    if (want != S.rail_on) rails_data(want);
    if (S.band_on) {                                   // the lantern flickers (slowly, not in step with the beat)
        want = (uint8_t)((c >> 3) % 6) < 2;
        if (want != S.lant_on) lantern(want);
    }
    backing();
#if TAIKO_VARIANT
    drum();
#endif
    sprites();
}
