// ORDER UP!, the bistro's mini-game (docs/minigames_bosses.md 4.4; art approved by the owner 2026-10-12: dish look B
// "big food", Chef Colby behind the counter, the cloche, the bubble, the pips, the strikes, the steam, the X and the
// bistro show's plate-spinning waiter dancing on ORDER UP!). Chef Colby calls an order dish by dish; each dish sits at
// a D-pad direction around the cloche. Repeat it with the D-pad. Each round adds one dish to the same order (Simon).
//
// Rules (the spec's numbers):
// - Four dishes: UP cheese wheel, RIGHT baguette, DOWN soup, LEFT grapes. Each lights (its tiles inverted; CGB: BG
//   palette 7 with that dish's colours round a glow) and plays its sound when called or pressed.
// - Round r = 1..7, the order r + 2 dishes long (3..9): one sequence for the whole game (seeded: mg_rand), grown by
//   one dish a round. The order is called after OU_PRE frames of an empty bubble: each dish lit for L frames (and big
//   in Colby's bubble), then G dark: L / G = 24 / 8 (rounds 1-3), 20 / 6 (4-5), 16 / 6 (6-7).
// - YOUR TURN: OU_PRESS_LEN frames for each dish (from the call's end, and again after each right press). A right
//   press: 50 points, its pip filled, the dish lit and the Spigoteer serving for OU_LIGHT_LEN frames. A wrong press or
//   the time running out is a strike: SENT BACK (the X over the wrong dish, lit; over the cloche on a timeout), Colby
//   cross and steaming, OU_SENT_LEN frames, then the same order is called again (not grown). 3 strikes end the game.
// - The order served: ORDER UP! (the cloche lifts, Colby pleased, the Spigoteer cheers, the waiter dances) and
//   200 x r points, OU_UP_LEN frames; round 7 served ends the game, +1000 with no strike at all.
// - Medal (ou_medal, not a score threshold): GOLD round 7 served, SILVER round 5, BRONZE round 3. No timer, no HARD.
// - Sounds (no new SFX): the dishes UP SFX_COIN, RIGHT SFX_CATCH, DOWN SFX_LAUNCH, LEFT SFX_SHAKE; ORDER UP!
//   SFX_SERVE (the bell); SENT BACK SFX_BREAK.
//
// Screen (the approved mock-ups): the framework's bistro backdrop (counter row 11; it uses BG palette 0 only); the
// cross of dishes round the cloche at columns 10-15, rows 5-10 (UP 12/5, LEFT 10/7, cloche 12/7, RIGHT 14/7, DOWN
// 12/9); Colby's bubble at columns 3-6, rows 4-7, its tail at columns 3-4 of row 8 (BG palette 0; the dish inside in
// its own palette); the order's pips on row 12, centred under the cross; the strikes at HUD columns 16-18 (the
// timer's place). CGB BG palettes: 2 cheese, 3 baguette, 5 soup, 6 grapes, 7 the lit dish (colour 0 of each the
// wall's); 4 stays the result's medal. Colby (16x24 at x 8, y 64: OBJ palette 3 rows 0-15, 4 rows 16-23; DMG OBP0),
// his steam (palette 3), the X (palette 6; DMG OBP1 0xC4: white, outlined black), the Spigoteer at x 124, y 112, the
// waiter at x 40, y 112 (the show's OBJ tiles and palette 5, as load_venue left them; DMG OBP1).
// OAM: 0-1 the X, 2-3 steam, 4-7 Colby, 8-11 the Spigoteer, 12-15 the waiter. Worst line 4.
// Tiles: BG OU_BG.. (MG_GAME_BG: 57, ids 125-181), OBJ 56-87 (Colby, steam, the X; not the coin at 92-95): all put back
// by the next level load (the patron tiles, the drink frames).
#pragma bank 255
#include <gb/gb.h>
#include <gb/cgb.h>
#include <stdint.h>

#include "game.h"
#include "music.h"
#include "mg.h"
#include "ou_art.h"         // this bank's own art (assets/art/orderup/*.txt)

#define S               (MG->ou)
#define OU_BG           MG_GAME_BG
#define OU_OBJ          OBJ_MUG             // 56..87 (the drink frames: the level load puts them back)
typedef char ou_fits[(OU_OBJ + OU_OBJ_TILES <= OBJ_COIN && OU_BG + OU_BG_TILES <= OBJ_POUR
                      && sizeof(struct ou_state) <= STORY_SCRATCH) ? 1 : -1];
#define OU_ROUNDS       7
#define OU_FIRST_LEN    3                   // round r: r + 2 dishes
#define OU_PRE         20                   // the empty bubble before the first dish is called
#define OU_PRESS_LEN  150                   // frames for each press
#define OU_LIGHT_LEN   14                   // a served dish's light and the serve pose
#define OU_UP_LEN      72                   // ORDER UP!: the cloche up / down every OU_CLOCHE_BEAT
#define OU_CLOCHE_BEAT 12
#define OU_SENT_LEN    64                   // SENT BACK
#define OU_STEAM_BEAT   8
#define OU_DISH_PTS    50
#define OU_ROUND_PTS  200                   // x the round
#define OU_PERFECT   1000                   // round 7 served with no strike
#define OU_STRIKES      3
#define OU_NONE       255
#define OU_CLOCHE       4                   // the X's cell on a timeout
#define OU_EMPTY        5                   // the bubble with nothing in it
enum { OU_UP, OU_RIGHT, OU_DOWN, OU_LEFT };
enum { OS_NEXT, OS_PRE, OS_CALL, OS_TURN, OS_ORDERUP, OS_SENT, OS_OVER };
enum { C_CALL, C_WATCH, C_PLEASED, C_CROSS };      // Colby's frames (colby.txt)
#define SPIG_IDLE       0                   // the bartender's frames (mg_spigoteer): idle, slide (serve), catch
#define SPIG_SERVE      4                   // (cheer), fail (shrug)
#define SPIG_CHEER      5
#define SPIG_FAIL       6
#define CROSS_COL      10                   // the cross: columns 10-15, rows 5-10
#define CROSS_ROW       5
#define BUB_COL         3                   // the bubble: columns 3-6, rows 4-7; the tail row 8
#define BUB_ROW         4
#define PIP_ROW        12
#define PIP_COL         8                   // the strip's buffer: columns 8-16 (9 pips at most)
#define PIP_MID        13                   // the strip starts at PIP_MID - (n + 1) / 2
#define STRIKE_COL     16
#define COLBY_X         8
#define COLBY_Y        64
#define SPIG_X        124
#define SPIG_Y        112
#define WAITER_X       40
#define WAITER_Y      112
#define OAM_X           0
#define OAM_STEAM       2
#define OAM_COLBY       4
#define OAM_SPIG        8
#define OAM_WAITER     12
#define OAM_N          16
#define PAL_COLBY_TOP   3
#define PAL_COLBY_LOW   4
#define PAL_X           6
#define PAL_WAITER      OBJPAL_DANCER       // 5: the show's (load_venue)
#define PAL_LIT         7                   // CGB BG: the lit dish
#define RGB15(r, g, b) ((uint16_t)((r) | ((g) << 5) | ((b) << 10)))
#define HEX(v)  RGB15(((v) >> 19) & 31, ((v) >> 11) & 31, ((v) >> 3) & 31)

static const uint8_t cell_col[5] = { 12, 14, 12, 10, 12 };   // UP RIGHT DOWN LEFT, the cloche
static const uint8_t cell_row[5] = { 5, 7, 9, 7, 7 };
static const uint8_t dish_pal[4] = { 2, 3, 5, 6 };
// each dish's light, mid, dark (tile colours 1-3; colour 0 the wall's)
static const uint16_t dish_col[4][3] = {
    { HEX(0xF8E070UL), HEX(0xE09028UL), HEX(0x402010UL) },    // cheese
    { HEX(0xF0C888UL), HEX(0xB86828UL), HEX(0x402010UL) },    // baguette
    { HEX(0xF8F8F0UL), HEX(0xD83820UL), HEX(0x401810UL) },    // soup
    { HEX(0xC890E8UL), HEX(0x7838A8UL), HEX(0x281038UL) },    // grapes
};
#define GLOW    HEX(0xF8E070UL)
static const uint8_t lit_len[OU_ROUNDS] = { 24, 24, 24, 20, 20, 16, 16 };
static const uint8_t gap_len[OU_ROUNDS] = { 8, 8, 8, 6, 6, 6, 6 };

static void ou_put(uint8_t bank, uint8_t *t, uint8_t col, uint8_t row, uint8_t n) {
    if (LCDC_REG & LCDCF_ON) { vq_add(bank, t, col, row, n); return; }
    if (bank) VBK_REG = VBK_BANK_1;
    vram_put(col, row, t, n);
    VBK_REG = VBK_BANK_0;
}

static void tone(uint8_t d) {               // (SFX takes a constant)
    switch (d) {
    case OU_UP: SFX(SFX_COIN); break;
    case OU_RIGHT: SFX(SFX_CATCH); break;
    case OU_DOWN: SFX(SFX_LAUNCH); break;
    default: SFX(SFX_SHAKE); break;
    }
}

// a cross cell (a dish or the cloche: 2x2) from its buffer
static void put_cell(uint8_t c, uint8_t *t, uint8_t *a) {
    uint8_t x = cell_col[c], y = cell_row[c];
    ou_put(0, t, x, y, 2); ou_put(0, t + 2, x, y + 1, 2);
    if (is_cgb && a) { ou_put(1, a, x, y, 2); ou_put(1, a + 2, x, y + 1, 2); }
}

static void dish(uint8_t d, uint8_t lit) {
    uint8_t k, t = OU_BG + (lit ? OUB_LIT : OUB_DISH) + 4 * d, *b = S.dish[d], *a = S.dattr[d];
    for (k = 0; k < 4; k++) { b[k] = t + k; a[k] = lit ? PAL_LIT : dish_pal[d]; }
    put_cell(d, b, a);
}

static void cloche(uint8_t up) {
    uint8_t k;
    S.cloche = up;
    for (k = 0; k < 4; k++) S.cl[k] = OU_BG + OUB_CLOCHE + 4 * up + k;
    put_cell(OU_CLOCHE, S.cl, 0);
}

// CGB BG palette 7 for dish d: [dark, mid, light, glow] (the LIT tiles are the dish's inverted)
static void pal_lit(uint8_t d) {
    uint16_t p[4];
    p[0] = dish_col[d][2]; p[1] = dish_col[d][1]; p[2] = dish_col[d][0]; p[3] = GLOW;
    set_bkg_palette(PAL_LIT, 1, p);
    S.pal_dish = d;
}

// The lit dish on screen follows S.want, one dish at a time: the old one goes dark first; on CGB the new one waits for
// palette 7 to hold its colours (written at the top of the next frame, in VBlank, while no tile uses it).
static void lights(void) {
    if (S.shown == S.want) return;
    if (S.shown != OU_NONE) { dish(S.shown, 0); S.shown = OU_NONE; }
    if (S.want == OU_NONE) return;
    if (is_cgb && S.pal_dish != S.want) { S.pal_want = S.want; return; }
    dish(S.want, 1); S.shown = S.want;
}

// The bubble: hidden (the wall saved at entry), empty, or a dish inside; the rows that changed are queued
static void bubble(uint8_t b) {
    static const uint8_t ring[5][4] = {
        { 0, 1, 1, 2 }, { 3, 255, 255, 4 }, { 3, 255, 255, 4 }, { 5, 6, 7, 8 }, { 9, 10, 254, 254 } };
    uint8_t r, c, v, dirty, *row;
    S.bubble = b;
    for (r = 0; r < 5; r++) {
        row = S.bub[r]; dirty = 0;
        for (c = 0; c < 4; c++) {
            v = ring[r][c];
            if (b == OU_NONE || v == 254) v = S.wall[r][c];
            else if (v == 255) v = b == OU_EMPTY ? OU_BG + OUB_BLANK : OU_BG + OUB_DISH + 4 * b + (r - 1) * 2 + (c - 1);
            else v += OU_BG + OUB_BUBBLE;
            if (row[c] != v) { row[c] = v; dirty = 1; }
        }
        if (dirty) ou_put(0, row, BUB_COL, BUB_ROW + r, 4);
    }
    if (!is_cgb || b == OU_EMPTY) return;       // (the empty inside is colour 0: any palette shows the wall's colour)
    for (r = 0; r < 2; r++) {
        dirty = 0;
        for (c = 0; c < 2; c++) {
            v = b == OU_NONE ? S.wattr[r + 1][c + 1] : dish_pal[b];
            if (S.battr[r][c] != v) { S.battr[r][c] = v; dirty = 1; }
        }
        if (dirty) ou_put(1, S.battr[r], BUB_COL + 1, BUB_ROW + 1 + r, 2);
    }
}

static void pips(uint8_t done) {               // this round's order: one pip a dish, the first `done` served
    uint8_t k, c0 = PIP_MID - (S.len + 1) / 2 - PIP_COL;
    for (k = 0; k < 9; k++) {
        if (k < c0 || k >= c0 + S.len) S.pips[k] = S.pwall[k];
        else S.pips[k] = OU_BG + (k - c0 < done ? OUB_PIP_DONE : OUB_PIP_TODO);
    }
    ou_put(0, S.pips, PIP_COL, PIP_ROW, 9);
}

static void strikes(void) {
    uint8_t k;
    for (k = 0; k < OU_STRIKES; k++) S.hud[k] = OU_BG + (k < S.strikes ? OUB_STRIKE_ON : OUB_STRIKE_OFF);
    ou_put(0, S.hud, STRIKE_COL, HUD_ROW, OU_STRIKES);
}

static void fill_attr(uint8_t col, uint8_t row, uint8_t pal) {   // LCD off, CGB: a 2x2 cell
    uint8_t a[2];
    a[0] = a[1] = pal;
    VBK_REG = VBK_BANK_1;
    vram_put(col, row, a, 2); vram_put(col, row + 1, a, 2);
    VBK_REG = VBK_BANK_0;
}

static void poses(void);

// LCD off, after the framework's screen
void ou_enter(void) BANKED {
    uint16_t p[4];
    uint8_t k, r, *m = (uint8_t *)0x9800;
    set_bkg_data(OU_BG, OU_BG_TILES, ou_bg_tiles);
    set_sprite_data(OU_OBJ, OU_OBJ_TILES, ou_obj_tiles);
    say_bang = (uint8_t)(OU_BG + OUB_BANG);                 // mg_say's '!' ("ORDER UP!"); mg_leave clears it
    for (r = 0; r < 5; r++)                      // the wall under the bubble and the pips (LCD off: VRAM readable)
        for (k = 0; k < 4; k++) S.wall[r][k] = S.bub[r][k] = m[(BUB_ROW + r) * 32 + BUB_COL + k];
    for (k = 0; k < 9; k++) S.pwall[k] = m[PIP_ROW * 32 + PIP_COL + k];
    if (is_cgb) {
        VBK_REG = VBK_BANK_1;
        for (r = 0; r < 5; r++)
            for (k = 0; k < 4; k++) S.wattr[r][k] = m[(BUB_ROW + r) * 32 + BUB_COL + k];
        VBK_REG = VBK_BANK_0;
        for (r = 0; r < 2; r++) for (k = 0; k < 2; k++) S.battr[r][k] = S.wattr[r + 1][k + 1];
        p[0] = venue.pal[VENUE_PAL_BAR][0];      // the wall's colour round every dish
        for (k = 0; k < 4; k++) {
            p[1] = dish_col[k][0]; p[2] = dish_col[k][1]; p[3] = dish_col[k][2];
            set_bkg_palette(dish_pal[k], 1, p);
            fill_attr(cell_col[k], cell_row[k], dish_pal[k]);
        }
        fill_attr(cell_col[OU_CLOCHE], cell_row[OU_CLOCHE], BGPAL_BAR);
        p[0] = 0;
        p[1] = HEX(0xF8F8F0UL); p[2] = HEX(0xF8C098UL); p[3] = HEX(0x482818UL);
        set_sprite_palette(PAL_COLBY_TOP, 1, p); // Colby's toque, face, beard
        p[2] = HEX(0xF0C030UL);
        set_sprite_palette(PAL_COLBY_LOW, 1, p); // his jacket, the cheese-yellow neckerchief
        p[2] = HEX(0xE02820UL); p[3] = HEX(0x301010UL);
        set_sprite_palette(PAL_X, 1, p);         // the X: red, outlined dark
        set_sprite_palette(PAL_WAITER, 1, venue.pal[VENUE_PAL_SHOW]);
    } else OBP1_REG = OBP1_MENU;                 // the X and the waiter: 0xC4 (the level load puts 0xE4 back)
    S.st = OS_NEXT; S.round = 0; S.len = 0; S.idx = 0; S.strikes = 0; S.t = 0; S.wait = 0; S.cleared = 0;
    for (k = 0; k < OU_LEN_MAX; k++) S.seq[k] = 0;
    S.x_on = S.want = S.shown = S.pal_dish = S.pal_want = OU_NONE;
    S.light_t = S.serve_t = 0; S.bubble = OU_NONE; S.colby = C_WATCH; S.again = 0; S.anim = 0;
    for (k = 0; k < 4; k++) dish(k, 0);
    cloche(0);
    strikes();
    poses();
}

uint8_t ou_medal(void) BANKED {
    if (S.cleared >= 7) return MEDAL_GOLD;
    if (S.cleared >= 5) return MEDAL_SILVER;
    return S.cleared >= 3 ? MEDAL_BRONZE : MEDAL_NONE;
}

// ---- the sprites ----
static void obj2(uint8_t oam, uint8_t x, uint8_t y, uint8_t t, uint8_t prop) {   // a 16x16 pair, px top-left
    OAM_item_t *o = shadow_OAM + oam;
    o->y = y + 16; o->x = x + 8;  o->tile = t;     o->prop = prop; o++;
    o->y = y + 16; o->x = x + 16; o->tile = t + 2; o->prop = prop;
}

static void poses(void) {
    uint8_t k, f, top = is_cgb ? PAL_COLBY_TOP : 0, st = S.st, win = S.cleared >= OU_ROUNDS;
    const uint8_t *w;
    for (k = 0; k < OAM_N; k++) shadow_OAM[k].y = 0;
    if (S.x_on != OU_NONE)
        obj2(OAM_X, cell_col[S.x_on] * 8, cell_row[S.x_on] * 8, OU_OBJ + OUO_X, is_cgb ? PAL_X : S_PALETTE);
    if (S.colby == C_CROSS)
        obj2(OAM_STEAM, COLBY_X - 1, COLBY_Y - 16, OU_OBJ + OUO_STEAM + 4 * ((S.anim / OU_STEAM_BEAT) & 1), top);
    obj2(OAM_COLBY, COLBY_X, COLBY_Y, OU_OBJ + OUO_COLBY + 4 * S.colby, top);
    obj2(OAM_COLBY + 2, COLBY_X, COLBY_Y + 16, OU_OBJ + OUO_COLBY_LOW, is_cgb ? PAL_COLBY_LOW : 0);
    f = SPIG_IDLE;
    if (st == OS_ORDERUP || (st == OS_OVER && win)) f = SPIG_CHEER;
    else if (st == OS_SENT || st == OS_OVER) f = SPIG_FAIL;
    else if (S.serve_t) f = SPIG_SERVE;
    mg_spigoteer(SPIG_X, SPIG_Y, f, 0, OAM_SPIG);
    if (st == OS_ORDERUP || (st == OS_OVER && win)) {   // the waiter dances: his three dance frames, a show beat each
        w = venue.show_tile[1 + (uint8_t)(S.t / DANCER_BEAT) % 3];
        obj2(OAM_WAITER, WAITER_X, WAITER_Y, OBJ_DANCER + w[0], is_cgb ? PAL_WAITER : S_PALETTE);
        obj2(OAM_WAITER + 2, WAITER_X, (uint8_t)(WAITER_Y + 16), OBJ_DANCER + w[2], is_cgb ? PAL_WAITER : S_PALETTE);
        shadow_OAM[OAM_WAITER + 1].tile = OBJ_DANCER + w[1];
        shadow_OAM[OAM_WAITER + 3].tile = OBJ_DANCER + w[3];
    }
}

// ---- the game ----
static void say_round(void) {                   // "ROUND n" (banner row A)
    char *d = S.txt;
    *d++ = 'R'; *d++ = 'O'; *d++ = 'U'; *d++ = 'N'; *d++ = 'D'; *d++ = ' '; *d++ = '0' + S.round; *d = 0;
    mg_say(MG_TEXT_A, S.txt);
}

static void call(uint8_t i) {                   // Colby calls dish i of the order
    uint8_t d = S.seq[i];
    S.want = d; S.colby = C_CALL; S.t = 0;
    bubble(d);
    tone(d);
}

static void strike(uint8_t d) {                 // SENT BACK: d the wrong dish, or OU_NONE (time out: the X on the cloche)
    S.strikes++;
    strikes();
    S.st = OS_SENT; S.t = 0;
    S.want = d; S.light_t = 0; S.serve_t = 0;
    S.x_on = d == OU_NONE ? OU_CLOCHE : d;
    S.colby = C_CROSS;
    mg_say(MG_TEXT_B, "SENT BACK");
    SFX(SFX_BREAK);
}

static void over(void) {
    char *d = S.txt;
    const char *w;
    S.st = OS_OVER; S.t = 0;
    if (S.cleared >= OU_ROUNDS) {
        mg_say(MG_TEXT_A, "ALL ORDERS SERVED");
        if (!S.strikes) { mg_points(OU_PERFECT); mg_say(MG_TEXT_B, "NO STRIKES 1000"); }
        else mg_say(MG_TEXT_B, "");
        S.colby = C_PLEASED;
    } else {
        mg_say(MG_TEXT_A, "THREE STRIKES");
        for (w = "ORDERS SERVED "; *w; ) *d++ = *w++;
        *d++ = '0' + S.cleared; *d = 0;
        mg_say(MG_TEXT_B, S.txt);
        S.colby = C_CROSS;
    }
    mg_finish();
}

static uint8_t dpad(uint8_t pressed) {           // the dish a fresh D-pad press asks for (OU_NONE: none)
    if (pressed & J_UP) return OU_UP;
    if (pressed & J_RIGHT) return OU_RIGHT;
    if (pressed & J_DOWN) return OU_DOWN;
    if (pressed & J_LEFT) return OU_LEFT;
    return OU_NONE;
}

void ou_update(uint8_t pressed) BANKED {
    uint8_t d, r;
    if (S.pal_want != OU_NONE && LY_REG >= 144 && LY_REG < 152) {   // (the top of the frame: still in VBlank)
        pal_lit(S.pal_want); S.pal_want = OU_NONE;
    }
    S.anim++;
    if (mg_phase == MG_PLAY) {
        r = S.round ? S.round - 1 : 0;
        switch (S.st) {
        case OS_NEXT:                            // a new round (the order grown by one), or the same order again
            if (!S.again) {
                S.round++; r = S.round - 1;
                while (S.len < S.round + OU_FIRST_LEN - 1) S.seq[S.len++] = mg_rand() & 3;
            }
            S.again = 0; S.idx = 0; S.t = 0;
            S.st = OS_PRE;
            S.x_on = OU_NONE; S.want = OU_NONE; S.colby = C_WATCH;
            say_round();
            mg_say(MG_TEXT_B, "LISTEN");
            pips(0);
            break;
        case OS_PRE:
            if (++S.t == 2) bubble(OU_EMPTY);    // (the frame after the banner's two rows)
            if (S.t >= OU_PRE) { S.st = OS_CALL; call(0); }
            break;
        case OS_CALL:
            S.t++;
            if (S.t == lit_len[r]) { S.want = OU_NONE; S.colby = C_WATCH; bubble(OU_EMPTY); }
            else if (S.t >= lit_len[r] + gap_len[r]) {
                if (++S.idx < S.len) call(S.idx);
                else {
                    S.st = OS_TURN; S.idx = 0; S.t = 0; S.wait = OU_PRESS_LEN;
                    bubble(OU_NONE);
                    mg_say(MG_TEXT_B, "YOUR TURN");
                }
            }
            break;
        case OS_TURN:
            if (S.light_t && --S.light_t == 0) S.want = OU_NONE;
            if (S.serve_t) S.serve_t--;
            if (S.idx >= S.len) {                // all served: ORDER UP! once the last dish's light is out
                if (S.light_t) break;
                S.cleared = S.round;
                S.st = OS_ORDERUP; S.t = 0;
                mg_points((uint16_t)OU_ROUND_PTS * S.round);
                mg_say(MG_TEXT_A, "ORDER UP!");
                mg_number(S.txt, (uint16_t)OU_ROUND_PTS * S.round);
                for (d = 0; S.txt[d]; d++) ;
                S.txt[d++] = ' '; S.txt[d++] = 'P'; S.txt[d++] = 'O'; S.txt[d++] = 'I'; S.txt[d++] = 'N';
                S.txt[d++] = 'T'; S.txt[d++] = 'S'; S.txt[d] = 0;
                mg_say(MG_TEXT_B, S.txt);
                S.colby = C_PLEASED;
                cloche(1);
                SFX(SFX_SERVE);
                break;
            }
            d = dpad(pressed);
            if (d != OU_NONE) {
                if (d != S.seq[S.idx]) { strike(d); break; }
                S.idx++;
                mg_points(OU_DISH_PTS);
                pips(S.idx);
                S.want = d; S.light_t = OU_LIGHT_LEN; S.serve_t = OU_LIGHT_LEN;
                S.wait = OU_PRESS_LEN;
                tone(d);
            } else if (--S.wait == 0) strike(OU_NONE);
            break;
        case OS_ORDERUP:
            S.t++;
            if (S.t < OU_UP_LEN) { if (S.t % OU_CLOCHE_BEAT == 0) cloche(!S.cloche); break; }
            cloche(0);
            S.colby = C_WATCH;
            if (S.round >= OU_ROUNDS) over();
            else S.st = OS_NEXT;
            break;
        case OS_SENT:
            if (++S.t < OU_SENT_LEN) break;
            S.x_on = OU_NONE; S.want = OU_NONE; S.colby = C_WATCH;
            if (S.strikes >= OU_STRIKES) over();
            else { S.again = 1; S.st = OS_NEXT; }
            break;
        }
    } else if (S.st == OS_OVER) S.t++;           // (MG_END: the outro's beat)
    lights();
    poses();
}
