// The scene transition (owner 2026-10-15: "the hard transition with the music just popping to a new song is kind of jarring"): a fizzy drink
// fills the screen from the bottom, the next scene is built behind it, and the drink drains away with its bubbles popping.
//
//   COVER   (trans_cover, from main.c lcd_off_p when a wired scene change set TR_WANT): the window (WX 7, LYC off) rises over the frozen old
//           scene 6 px a frame, its top row the foam, the rows under it amber with bubbles; sprites the foam passes are hidden. The tune ducks
//           (master volume NR50 7 -> 0), music_tick every frame. Held full for 2 frames, then the LCD goes off and the banner rows are put back.
//   BUILD   the caller's rebuild runs as it always did (LCD off, music pumped by mpump.h); the new tune starts at volume 0.
//   ARM     (trans_arm, from main.c lcd_on_p): the LCD is still off: the scene's banner rows (window rows 1-3) are kept in HRAM, the drink is written
//           over window rows 0-17, its 4 tiles over BG tile ids 248-251, the window covers the screen and the sprites are off.
//   REVEAL  (trans_reveal, from the main loop before the next frame's logic): the foam line falls 6 px a frame, the bubbles shimmer and pop, the tune
//           fades in; then the banner rows, WY, LYC, the window and sprite bits and the volume are exactly as the scene left them.
//
// Not over the pause menu (lcd_off_p skips GS_PAUSED) and Milk Run's raster handler (swapped for lcd_isr during cover and reveal). The window map rows 5-17
// are scratch everywhere (the pause menu and the result windows rewrite what they use). Tile ids 248-251 (patrons end at 233, a boss HUD takes 252-255): no wired screen uses them (tests/test_trans.py).
// HRAM: 0xFFF1 flags (game.h TRANS), 0xFFF2 the scene's LCDC, 0xFFF3 its LYC, 0xFF94-0xFFCF its banner rows 33-35 (3 x 20).
#pragma bank 255
#include <gb/gb.h>
#include <gb/cgb.h>
#include <stdint.h>

#include "game.h"
#include "music.h"
#include "mg.h"
#include "trans_art.h"

extern uint8_t overlay_on;

#define TR_ARMED   4
#define HR_LCDC    (*(volatile uint8_t *)0xFFF2)
#define HR_LYC     (*(volatile uint8_t *)0xFFF3)
#define HR_ROWS    ((uint8_t *)0xFF94)
#define T_FOAM     248
#define T_FILL     249
#define T_BUB1     250
#define T_BUB2     251
#define RISE_STEP  6                  // px a frame: 24 frames for the 144 lines
#define RISE_N     24
#define HOLD_N     2

static void plain_isr(void) {         // Milk Run's raster handler (it walks LYC and SCX) off for the duration; the framework's lcd_normal puts it right after
    CRITICAL {
        remove_LCD(mr_lcd_isr);
        remove_LCD(lcd_isr);
        add_LCD(lcd_isr);
    }
}

static uint8_t in_milkrun(void) { return game_state == GS_MINI && mg_id == MG_MILKRUN; }

static void tile(uint8_t slot, uint8_t t) { set_bkg_data(slot, 1, fz_tiles + (uint16_t)t * 16); }

static void load_tiles(uint8_t cream) {   // the foam, the fill and the first frame of each bubble; cream: the whitened screen (fill and bubbles all cream)
    tile(T_FOAM, FZ_FOAM);
    tile(T_FILL, cream ? FZ_CREAM : FZ_FILL); tile(T_BUB1, cream ? FZ_CREAM : FZ_BUB); tile(T_BUB2, cream ? FZ_CREAM : FZ_BUB + 3);
}

// Window row r of the drink: the foam, then amber with a scatter of bubbles (a fixed pattern, so a row is the same whenever it is written).
static const uint8_t bub_col[18][3] = {          // where row r's three bubbles sit (BUB1, BUB2, BUB1)
    {3,11,15}, {0,6,13}, {8,17,2}, {15,10,6}, {17,8,0}, {14,19,5}, {3,17,11}, {19,14,7}, {0,4,9},
    {2,19,6}, {4,0,13}, {2,10,19}, {4,17,8}, {15,1,11}, {13,8,3}, {11,0,5}, {3,8,16}, {19,13,5} };

static void drink_row(uint8_t *b, uint8_t r) {
    uint8_t c;
    for (c = 0; c < 20; c++) b[c] = r ? T_FILL : T_FOAM;
    if (r) { b[bub_col[r][0]] = T_BUB1; b[bub_col[r][1]] = T_BUB2; b[bub_col[r][2]] = T_BUB1; }
}

// window row r (map row 32 + r): through set_win_tiles (it waits for VRAM) with the LCD on, straight to VRAM with it off (it would wait for ever)
static void win_put(uint8_t r, const uint8_t *b) {
    if (LCDC_REG & LCDCF_ON) set_win_tiles(0, r, 20, 1, b);
    else { vram_put(0, 32 + r, b, 20); music_pump(); }
}

static void put_win_row(uint8_t r, uint8_t *b, uint8_t attr) {   // window row r's tiles, and on CGB its attributes (the HUD palette: cream, tan, amber)
    uint8_t c;
    win_put(r, b);
    if (attr && is_cgb) {
        for (c = 0; c < 20; c++) b[c] = BGPAL_HUD;
        VBK_REG = VBK_BANK_1;
        win_put(r, b);
        VBK_REG = VBK_BANK_0;
    }
}

static void drink_rows(uint8_t from, uint8_t to) {               // rows from .. to-1 of the drink (at most 18)
    uint8_t b[20];
    for (; from < to && from < 18; from++) {
        drink_row(b, from);
        put_win_row(from, b, 1);
    }
}

static void volume(uint8_t v) { NR50_REG = v * 0x11; }

void trans_cover(void) BANKED {
    uint8_t i, j, wy, rows = 0;
    uint8_t b[20];
    music_tick();                                                // (this frame's tick: the logic that called us never reaches the main loop's)
    HR_LYC = LYC_REG;                                            // (back after the cover: the rebuild leaves LYC and WY to the scene's own setting)
    if (in_milkrun()) plain_isr();
    load_tiles(0);
    WX_REG = 7; LYC_REG = 255; WY_REG = 144; SHOW_WIN;
    drink_rows(0, 1);
    rows = 1;
    for (i = 1; i <= RISE_N; i++) {
        vsync();
        wy = 144 - RISE_STEP * i;
        WY_REG = wy;
        for (j = 0; j < 40; j++) if (shadow_OAM[j].y > wy) shadow_OAM[j].y = 0;   // under the foam: gone (the old scene is not drawn again)
        volume((RISE_N - i) * 7 / RISE_N);
        if (!(i & 3)) tile(T_BUB1, FZ_BUB + ((i >> 2) & 1));
        if ((i & 3) == 2) tile(T_BUB2, FZ_BUB + 3 + ((i >> 2) & 1));
        j = (uint8_t)((144 - wy + RISE_STEP + 7) >> 3);          // the rows the next step shows
        drink_rows(rows, j); if (j > rows) rows = j;
        music_tick();                                            // (as the main loop: the tick follows the frame's work)
    }
    for (i = 0; i < HOLD_N; i++) {
        vsync();
        if (!i) load_tiles(1);                                   // the drink foams over: all cream (the LCD-off blank that follows is white too)
        music_tick();
    }
    volume(0);
    lcd_off_p();                                                 // (TR_WANT is already clear: the plain way)
    LYC_REG = HR_LYC; WY_REG = BANNER_WY; HIDE_WIN;              // the banner window as it stands when nothing shows it
    for (i = 0; i < 20; i++) b[i] = TILE_PANEL_TOP;              // the banner window's rows as win_init left them (the scene's own writes come after)
    win_put(0, b);
    for (i = 0; i < 20; i++) b[i] = TILE_HUD_BLANK;
    win_put(1, b);
    for (i = 0; i < 20; i++) b[i] = TILE_PANEL_BOT;
    win_put(2, b);
    TRANS |= TR_PEND;
}

void trans_arm(void) BANKED {
    uint8_t r, c;
    const uint8_t *m = (const uint8_t *)0x9C00 + 32;             // window row 1
    uint8_t *s = HR_ROWS;
    if (LCDC_REG & LCDCF_ON) return;
    if (!(TRANS & TR_ARMED)) {                                   // (a second arm before the reveal keeps the first's copy)
        HR_LCDC = LCDC_REG; HR_LYC = LYC_REG;
        for (r = 0; r < 3; r++, m += 32)                         // the scene's banner rows 33-35 (LCD off: VRAM can be read)
            for (c = 0; c < 20; c++) *s++ = m[c];
        TRANS |= TR_ARMED;
    }
    load_tiles(1);
    drink_rows(0, 18);
    WX_REG = 7; WY_REG = 0; LYC_REG = 255; SHOW_WIN; HIDE_SPRITES;
    volume(0);
}

void trans_reveal(void) BANKED {
    uint8_t i, c, wy, lyc, lcdc;
    uint8_t b[20], e[20];
    TRANS &= ~TR_HOLD;
    if (!(TRANS & TR_PEND) || !(LCDC_REG & LCDCF_ON)) return;
    lcdc = HR_LCDC;
    lyc = LYC_REG;
    if (lyc == 255) lyc = HR_LYC;                                // (the scene may have set its own after lcd_on_p)
    TRANS &= ~(TR_PEND | TR_ARMED);
    if (in_milkrun()) plain_isr();
    WY_REG = 0; LYC_REG = 255; SHOW_WIN; HIDE_SPRITES;           // (as trans_arm: the scene's code ran after it)
    for (i = 0; i <= RISE_N + HOLD_N; i++) {
        vsync();
        wy = i < HOLD_N ? 0 : (i - HOLD_N) * RISE_STEP;
        WY_REG = wy;
        volume(i > RISE_N ? 7 : i * 7 / RISE_N);
        if (i == 1) { tile(T_FILL, FZ_FILL); tile(T_BUB2, FZ_BUB + 3); }          // the cream darkens to amber
        if (i < 8) { if (i == 1 || i == 4) tile(T_BUB1, FZ_BUB + (i >> 2)); }   // the shimmer, then the bubbles pop and are gone
        else if (i == 8) tile(T_BUB1, FZ_BUB + 2);
        else if (i == 11) tile(T_BUB1, FZ_FILL);
        if (i < 10) { if (i == 6) tile(T_BUB2, FZ_BUB + 4); }
        else if (i == 10) tile(T_BUB2, FZ_BUB + 5);
        else if (i == 13) tile(T_BUB2, FZ_FILL);
        music_tick();
    }
    for (c = 0; c < 20; c++) { b[c] = TILE_PANEL_TOP; e[c] = TILE_PANEL_BOT; }   // the banner window as the scene left it: panel, its three kept rows, panel,
    for (i = 0; i < 3; i++) {                                    // two rows a frame through the VBlank queue (the window is gone: nothing to see)
        vq_frame_begin();
        if (!i) { vq_add(0, b, 0, 32, 20); vq_add(0, HR_ROWS, 0, 33, 20); }
        else if (i == 1) { vq_add(0, HR_ROWS + 20, 0, 34, 20); vq_add(0, HR_ROWS + 40, 0, 35, 20); }
        else vq_add(0, e, 0, 36, 20);
        vq_frame_end();
        vsync();
        music_tick();
    }
    WY_REG = BANNER_WY; LYC_REG = lyc;
    if (overlay_on) SHOW_WIN; else HIDE_WIN;
    if (lcdc & LCDCF_OBJON) SHOW_SPRITES;
    volume(7);
    if (in_milkrun()) {
        CRITICAL { remove_LCD(lcd_isr); add_LCD(mr_lcd_isr); }
        SCX_REG = 0;
    }
}
