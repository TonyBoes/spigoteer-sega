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

// ---- the palette fades (variants 1 and 2, owner 2026-10-16: the drink's window layer shows the LCD-off white and reads as noise) --------------
// The picture itself fades, no window: F1 to WHITE, F2 through AMBER (the drink) and then white; the LCD goes off in the white (what an off LCD shows, so no
// flash), the new scene is built, the LCD comes on white and the new palettes fade in. Whole fade, no window, no art.
//   DMG: BGP / OBP0 / OBP1 shade by shade (FADE_DMG frames a step); the scene's three palettes are kept in HRAM.
//   CGB: all 64 palette colours, each step a lerp by eighths (part(): the three 5-bit channels shifted together under masks, no multiplies). A colour takes
//        ~2000 cycles in C and palette RAM is only writable in VBlank (~2700 cycles left after the VBlank handler), so a step is computed in the frame's
//        active part into RES (HRAM, one group of 32 colours) and written in the next VBlank by an unrolled burst: BG one frame, OBJ the next.
//        The scene's colours are read into a 128-byte stack buffer in the first 4 frames (16 a VBlank; the picture still stands); the LCD-off then
//        gets them back (a scene that does not rewrite a palette keeps it). trans_arm keeps the NEW scene's colours in VRAM bank 1, tile ids 248-255 (no
//        bank-1 tile reaches them; the LCD is off), paints the palettes white; trans_reveal reads them back (4 white frames) and fades them in.
#define V_WHITE    1
#define V_AMBER    2
#define COL_W      0x7FFF
#define COL_A      0x0E7F                        // amber: R 31 G 19 B 3
#define FADE_STEP  3                              // frames a CGB step takes (at least: compute + the two bursts)
#define FADE_DMG   6
#define STASH      ((volatile uint8_t *)0x8F80)
#define RES        ((uint8_t *)0xFF94)            // HRAM 0xFF94-0xFFD3: the next 32 colours (the drink's banner rows' place; the variants never overlap)
#define HR_PAL     ((uint8_t *)0xFF94)            // DMG: the scene's BGP, OBP0, OBP1
#define HRB(n)     (*(volatile uint8_t *)(0xFF94 + (n)))

static const uint8_t k_out[6] = { 7, 5, 4, 2, 1, 0 };     // eighths of the scene's colour kept, step by step (0: flat)
static const uint8_t k_amb[3] = { 5, 3, 0 };               // amber -> white
static const uint8_t k_in[5] = { 1, 2, 4, 5, 7 };          // the fade-in, then the saved colours exactly (k 8)

static uint16_t part(uint16_t x, uint8_t k) {               // x * k / 8, each channel on its own
    uint16_t r = 0;
    if (k & 4) r += (x >> 1) & 0x3DEF;
    if (k & 2) r += (x >> 2) & 0x1CE7;
    if (k & 1) r += (x >> 3) & 0x0C63;
    return r;
}

static void vol_out(uint8_t f, uint8_t n) { volume(f >= n ? 0 : (uint8_t)((uint16_t)(n - f) * 7 / n)); }
static void vol_in(uint8_t f, uint8_t n) { volume(f >= n ? 7 : (uint8_t)((uint16_t)f * 7 / n)); }

#define BW(r, n) r = HRB(n); r = HRB((n) + 1); r = HRB((n) + 2); r = HRB((n) + 3); r = HRB((n) + 4); r = HRB((n) + 5); r = HRB((n) + 6); r = HRB((n) + 7);
#define BW64(r) BW(r, 0) BW(r, 8) BW(r, 16) BW(r, 24) BW(r, 32) BW(r, 40) BW(r, 48) BW(r, 56)

static void burst(uint8_t obj) {                             // RES -> BG (0) or OBJ (1) palette RAM, 24 cycles a byte: one VBlank holds it
    if (obj) { OCPS_REG = 0x80; BW64(OCPD_REG) }
    else { BCPS_REG = 0x80; BW64(BCPD_REG) }
}

// One frame: wait for a VBlank with room for a burst / a read (lines 144-150; a frame that ran late waits for the next, the music ticking through it),
// then burst group g (0 BG, 1 OBJ; 2 nothing). Returns the frames it took.
static uint8_t vframe(uint8_t g) {
    uint8_t f = 0, ly;
    for (;;) {
        vsync(); f++;
        ly = LY_REG;
        if (ly >= 144 && ly <= 150) break;
        music_tick();
    }
    if (g < 2) burst(g);
    return f;
}

// the frame's volume and music, after its VBlank work
static void fa_tail(uint8_t f, uint8_t n, uint8_t rise) { if (rise) vol_in(f, n); else vol_out(f, n); music_tick(); }

// RES = group g's 32 colours of `o` (64 bytes) at level k toward t; o null: all `base` at level k
static void group(const uint8_t *o, uint8_t k, uint16_t t, uint16_t base) {
    uint8_t i, a = k & 4, b = k & 2, c = k & 1;
    uint16_t kk = t - part(t, k), w, r;
    uint16_t *q = (uint16_t *)RES;
    const uint16_t *p = (const uint16_t *)o;
    for (i = 0; i < 32; i++) {
        w = o ? *p++ : base;
        if (k == 8) r = w;
        else {
            r = kk;
            if (a) r += (w >> 1) & 0x3DEF;
            if (b) r += (w >> 2) & 0x1CE7;
            if (c) r += (w >> 3) & 0x0C63;
        }
        *q++ = r;
    }
}

// One step, all 64 colours of `o` (null: flat `base`) to level k of t, f frames in all of at least minf; f0 / n: the volume's place in the whole fade.
static uint8_t cstep(const uint8_t *o, uint8_t k, uint16_t t, uint16_t base, uint8_t minf, uint8_t f0, uint8_t n, uint8_t rise) {
    uint8_t f = 0;
    group(o, k, t, base);
    f += vframe(0); fa_tail(f0 + f, n, rise);
    group(o ? o + 64 : 0, k, t, base);
    f += vframe(1); fa_tail(f0 + f, n, rise);
    while (f < minf) { f += vframe(2); fa_tail(f0 + f, n, rise); }
    return f;
}

// The scene's 64 colours into o (stash 0: from palette RAM; 1: from the VRAM bank-1 stash), 16 a VBlank: 4 frames
static uint8_t pal_in(uint8_t *o, uint8_t stash, uint8_t n, uint8_t rise) {
    uint8_t q, c, i, f = 0;
    for (q = 0; q < 4; q++) {
        f += vframe(2);
        if (stash) {
            CRITICAL {
                VBK_REG = VBK_BANK_1;
                for (i = 0; i < 32; i++) o[q * 32 + i] = STASH[q * 32 + i];
                VBK_REG = VBK_BANK_0;
            }
        } else {
            for (c = q * 16; c < q * 16 + 16; c++) {
                i = (c & 31) << 1;
                if (c < 32) { BCPS_REG = i; o[c << 1] = BCPD_REG; BCPS_REG = i | 1; o[(c << 1) | 1] = BCPD_REG; }
                else { OCPS_REG = i; o[c << 1] = OCPD_REG; OCPS_REG = i | 1; o[(c << 1) | 1] = OCPD_REG; }
            }
        }
        fa_tail(f, n, rise);
    }
    return f;
}

static uint8_t dfade(uint8_t p, uint8_t k) {               // a DMG palette k shades lighter
    uint8_t r = 0, i, s;
    for (i = 0; i < 8; i += 2) {
        s = (p >> i) & 3;
        if (s > k) r |= (s - k) << i;
    }
    return r;
}

static void dset(const uint8_t *o, uint8_t k) { BGP_REG = dfade(o[0], k); OBP0_REG = dfade(o[1], k); OBP1_REG = dfade(o[2], k); }

static uint8_t dstep(const uint8_t *o, uint8_t k, uint8_t fr, uint8_t f0, uint8_t n, uint8_t rise) {
    uint8_t f;
    for (f = 1; f <= fr; f++) {
        vsync();
        if (f == 1) dset(o, k);
        fa_tail(f0 + f, n, rise);
    }
    return fr;
}

static void cgb_cover(uint8_t v) {
    uint8_t s, f, n = 4 + 6 * FADE_STEP + (v == V_AMBER ? 3 * FADE_STEP : 0), o[128];
    uint16_t t = v == V_AMBER ? COL_A : COL_W;
    f = pal_in(o, 0, n, 0);
    for (s = 0; s < 6; s++) f += cstep(o, k_out[s], t, 0, FADE_STEP, f, n, 0);
    if (v == V_AMBER) for (s = 0; s < 3; s++) f += cstep(0, k_amb[s], COL_W, COL_A, FADE_STEP, f, n, 0);
    volume(0);
    lcd_off_p();                                                 // (TR_WANT is already clear: the plain way) the LCD goes off in the white
    BCPS_REG = 0x80;                                             // the scene's own colours back (LCD off: palette RAM is free)
    for (s = 0; s < 64; s++) BCPD_REG = o[s];
    OCPS_REG = 0x80;
    for (s = 0; s < 64; s++) OCPD_REG = o[64 + s];
}

static void dmg_cover(void) {
    uint8_t s, f = 0, o[3];
    o[0] = BGP_REG; o[1] = OBP0_REG; o[2] = OBP1_REG;
    for (s = 1; s <= 3; s++) f += dstep(o, s, FADE_DMG, f, 3 * FADE_DMG, 0);
    volume(0);
    lcd_off_p();
    dset(o, 0);
}

static void fade_cover(uint8_t v) {
    if (is_cgb) cgb_cover(v); else dmg_cover();
    TRANS |= TR_PEND;
}

static void fade_arm(void) {                                     // LCD off, the new scene's palettes set: keep them, the screen white
    uint8_t c, i, lo, hi, a = TRANS & TR_ARMED;
    uint8_t *h = HR_PAL;
    if (is_cgb) {                                                // (a second arm keeps the first's colours unless the scene set its own since)
        VBK_REG = VBK_BANK_1;
        for (c = 0; c < 64; c++) {
            i = (c & 31) << 1;
            if (c < 32) { BCPS_REG = i; lo = BCPD_REG; BCPS_REG = i | 1; hi = BCPD_REG; BCPS_REG = 0x80 | i; BCPD_REG = 0xFF; BCPD_REG = 0x7F; }
            else { OCPS_REG = i; lo = OCPD_REG; OCPS_REG = i | 1; hi = OCPD_REG; OCPS_REG = 0x80 | i; OCPD_REG = 0xFF; OCPD_REG = 0x7F; }
            if (!a || lo != 0xFF || hi != 0x7F) { STASH[c << 1] = lo; STASH[(c << 1) | 1] = hi; }
        }
        VBK_REG = VBK_BANK_0;
    } else {                                                     // (the same for the DMG palettes: white is 0)
        if (!a || BGP_REG) h[0] = BGP_REG;
        if (!a || OBP0_REG) h[1] = OBP0_REG;
        if (!a || OBP1_REG) h[2] = OBP1_REG;
        BGP_REG = OBP0_REG = OBP1_REG = 0;
    }
}

static void fade_reveal(void) {                                  // LCD on, white: the new scene's colours come in
    uint8_t s, f = 0, n, o[128];
    if (is_cgb) {
        n = 4 + 5 * FADE_STEP + 2;
        f = pal_in(o, 1, n, 1);                                  // (4 frames of white while the colours are read back)
        for (s = 0; s < 5; s++) f += cstep(o, k_in[s], COL_W, 0, FADE_STEP, f, n, 1);
        cstep(o, 8, 0, 0, 2, f, n, 1);
    } else {
        n = 2 + 2 * FADE_DMG + 1;
        for (s = 0; s < 2; s++) { vsync(); f++; fa_tail(f, n, 1); }
        f += dstep(HR_PAL, 2, FADE_DMG, f, n, 1);
        f += dstep(HR_PAL, 1, FADE_DMG, f, n, 1);
        dstep(HR_PAL, 0, 1, f, n, 1);
    }
    TRANS &= ~(TR_PEND | TR_ARMED);
    volume(7);
}

void trans_cover(void) BANKED {
    uint8_t i, j, wy, rows = 0, v = (TRANS >> TR_VSHIFT) & 3;
    uint8_t b[20];
#ifdef TRANS_CYCLE                                               // the debug ROM: each transition takes the next fade, SELECT held repeats the last
    if (!(joypad() & J_SELECT)) v = v == V_WHITE ? V_AMBER : V_WHITE;
    TRANS = (TRANS & ~TR_VMASK) | (v << TR_VSHIFT);
#endif
    music_tick();                                                // (this frame's tick: the logic that called us never reaches the main loop's)
    if (v) { fade_cover(v); return; }
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
    if (TRANS & TR_VMASK) { fade_arm(); music_load_now(); volume(0); TRANS |= TR_ARMED; return; }
    if (!(TRANS & TR_ARMED)) {                                   // (a second arm before the reveal keeps the first's copy)
        HR_LCDC = LCDC_REG; HR_LYC = LYC_REG;
        for (r = 0; r < 3; r++, m += 32)                         // the scene's banner rows 33-35 (LCD off: VRAM can be read)
            for (c = 0; c < 20; c++) *s++ = m[c];
        TRANS |= TR_ARMED;
    }
    music_load_now();                                            // (the new tune's patterns copied at once, not a few frames into the drain)
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
    if (TRANS & TR_VMASK) { fade_reveal(); return; }
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
    dust_load();                                                 // (the drink borrowed BG ids 248-251, the story bar-change puff's OBJ tiles 248-251 too: its own again)
    if (in_milkrun()) {
        CRITICAL { remove_LCD(lcd_isr); add_LCD(mr_lcd_isr); }
        SCX_REG = 0;
    }
}
