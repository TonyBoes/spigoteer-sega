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

static void volume(uint8_t v) { if (game_state != GS_PAUSED) NR50_REG = v * 0x11; }   // (the pause card's fades leave the volume alone: the pause mix plays on)
static void keep_win(void) { if (game_state == GS_PAUSED && overlay_on) SHOW_WIN; }     // (the pause card's fades: the main loop that shows the menu's window each frame is not running)

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
static const uint8_t k_in[5] = { 1, 2, 4, 5, 7 };
static const uint8_t kc_out[2] = { 5, 2 };                 // the pause card's fades (owner 2026-10-17: much faster): two big steps of 2 frames each way
static const uint8_t kc_in[2] = { 3, 6 };          // the fade-in, then the saved colours exactly (k 8)

#define FAST_ON    (game_state == GS_PAUSED || (TRANS & TR_FAST))   // the pause card's fast fades and the menu screen changes' (trans_menu): the same steps
#define FADING     (TRANS & (TR_VMASK | TR_FAST))

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

static uint8_t pal_gap(void) { uint8_t ly = LY_REG; return ly >= 144 && ly <= 152; }   // still room in the VBlank for one more read

static void burst(uint8_t obj) {                             // RES -> BG (0) or OBJ (1) palette RAM, 24 cycles a byte: one VBlank holds it
    CRITICAL {
        if (obj) { OCPS_REG = 0x80; BW64(OCPD_REG) }
        else { BCPS_REG = 0x80; BW64(BCPD_REG) }
    }
}

// One frame: wait for a VBlank with room for a burst / a read (lines 144-149 for a burst, to 152 for a read; a frame that ran late waits for the next, the music ticking through it),
// then burst group g (0 BG, 1 OBJ; 2 nothing). Returns the frames it took.
static uint8_t vframe(uint8_t g) {
    uint8_t f = 0, ly;
    for (;;) {
        vsync(); f++;
        keep_win();
        ly = LY_REG;
        if (ly >= 144 && ly <= (g < 2 ? 149 : 152)) break;   // (a burst is ~1540 cycles and must be over before line 153 ends: 149 at the latest)
        music_tick();
    }
    if (g < 2) burst(g);
    return f;
}

// the frame's volume and music, after its VBlank work
static void fa_tail(uint8_t f, uint8_t n, uint8_t rise) {
    if (rise < 2) { if (rise) vol_in(f, n); else vol_out(f, n); }   // (rise 2: the tune's volume is left alone: the credits' cast cards)
    if (game_state != GS_PAUSED || NR51_REG) music_tick();   // (a pause with the tune standing still, NR51 0: no tick, as main.c)
}

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

// The scene's 64 colours into o (stash 0: from palette RAM; 1: from the VRAM bank-1 stash)
// Palette RAM and VRAM read 0xFF in mode 3 (a real LCD; PyBoy does not model it). A read loop in C costs 50-100 cycles a byte, so a frame's worth
// does not fit the VBlank: each frame reads until LY leaves lines 144-152 (pal_gap) and the next frame goes on from where it stopped.
static uint8_t pal_in(uint8_t *o, uint8_t stash, uint8_t n, uint8_t rise) {
    uint8_t c = 0, i, f = 0;
    while (c < (stash ? 128 : 64)) {
        f += vframe(2);
        if (stash) {
            CRITICAL {
                VBK_REG = VBK_BANK_1;
                do { o[c] = STASH[c]; c++; } while (c < 128 && pal_gap());
                VBK_REG = VBK_BANK_0;
            }
        } else {
            uint8_t *q = o + (c << 1);
            do {                                                 // (the card's fade waits for this: a colour costs ~100 cycles, ~7 a frame)
                i = (c & 31) << 1;
                if (c < 32) { BCPS_REG = i; *q++ = BCPD_REG; BCPS_REG = i | 1; *q++ = BCPD_REG; }
                else { OCPS_REG = i; *q++ = OCPD_REG; OCPS_REG = i | 1; *q++ = OCPD_REG; }
                c++;
            } while (c < 64 && pal_gap());
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
        keep_win();
        if (f == 1) dset(o, k);
        fa_tail(f0 + f, n, rise);
    }
    return fr;
}

static void cgb_cover(uint8_t v) {
    uint8_t s, f, fast = FAST_ON, n = fast ? 4 + 2 * 2 : 4 + 6 * FADE_STEP + (v == V_AMBER ? 3 * FADE_STEP : 0), o[128];
    uint16_t t = v == V_AMBER ? COL_A : COL_W;
    f = pal_in(o, 0, n, 0);
    if (fast) for (s = 0; s < 2; s++) f += cstep(o, kc_out[s], t, 0, 2, f, n, 0);
    else for (s = 0; s < 6; s++) f += cstep(o, k_out[s], t, 0, FADE_STEP, f, n, 0);
    if (v == V_AMBER) for (s = 0; s < 3; s++) f += cstep(0, k_amb[s], COL_W, COL_A, FADE_STEP, f, n, 0);
    volume(0);
    lcd_off_p();                                                 // (TR_WANT is already clear: the plain way) the LCD goes off in the white
    if (game_state != GS_PAUSED) music_pump();                   // (the tick that fell due while the LCD went off)
    BCPS_REG = 0x80;                                             // the scene's own colours back (LCD off: palette RAM is free)
    for (s = 0; s < 64; s++) BCPD_REG = o[s];
    if (game_state != GS_PAUSED) music_pump();
    OCPS_REG = 0x80;
    for (s = 0; s < 64; s++) OCPD_REG = o[64 + s];
}

static void dmg_cover(void) {
    uint8_t s, f = 0, o[3], fr = FAST_ON ? 2 : FADE_DMG;   // (the pause card's fades: 2 frames a shade)
    o[0] = BGP_REG; o[1] = OBP0_REG; o[2] = OBP1_REG;
    for (s = 1; s <= 3; s++) f += dstep(o, s, fr, f, 3 * fr, 0);
    volume(0);
    lcd_off_p();
    if (game_state != GS_PAUSED) music_pump();
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
    uint8_t s, f = 0, n, o[128], fast = FAST_ON;
    if (game_state != GS_PAUSED) music_tick();                   // (the tick the main loop would give straight after DISPLAY_ON: the first vsync below is ~1 frame away)
    if (is_cgb) {
        n = fast ? 4 + 2 * 2 + 2 : 4 + 5 * FADE_STEP + 2;
        f = pal_in(o, 1, n, 1);                                  // (4 frames of white while the colours are read back)
        if (fast) for (s = 0; s < 2; s++) f += cstep(o, kc_in[s], COL_W, 0, 2, f, n, 1);
        else for (s = 0; s < 5; s++) f += cstep(o, k_in[s], COL_W, 0, FADE_STEP, f, n, 1);
        cstep(o, 8, 0, 0, 2, f, n, 1);
    } else {
        uint8_t fr = fast ? 2 : FADE_DMG;
        n = 2 + 2 * fr + 1;
        for (s = 0; s < (fast ? 1 : 2); s++) { vsync(); keep_win(); f++; fa_tail(f, n, 1); }
        f += dstep(HR_PAL, 2, fr, f, n, 1);
        f += dstep(HR_PAL, 1, fr, f, n, 1);
        dstep(HR_PAL, 0, 1, f, n, 1);
    }
    TRANS &= ~(TR_PEND | TR_ARMED | TR_FAST);
    volume(7);
    if (game_state != GS_PAUSED) TMA_REG |= 1;                   // (the last frame ticked: the main loop's tick straight after is refused, music_tick)
}

// The pause menu's HOW TO PLAY card (src/pause.c CARD_FADE): the white fade F1 over the pause screen, whatever the variant of the scene changes. Out: the picture fades
// to white and the LCD goes off in it (the palettes back as they were), the caller builds the other screen; arm: its palettes are kept and painted white (LCD still off);
// in: the LCD is on, the new colours fade in. The tune plays on as the pause mix (volume() is quiet in a pause; fa_tail ticks it; a tune that stands still, NR51 0, stays still).
void trans_card_out(void) BANKED {
    keep_win();                                                  // (the main loop shows the menu's window after the update: this frame's too)
    music_tick();                                                // (this frame's tick: the pause logic that called us never reaches the main loop's)
    if (is_cgb) cgb_cover(V_WHITE); else dmg_cover();
}

static void tick_sync(void) {
    if (NR51_REG) while (TIMA_REG > 23) music_pump();            // (the LCD comes on a third of a frame after a tick: the first fade-in tick follows ~1.3 frames later, not 1.9)
}

// After the build, LCD still off, the window and registers set: the new screen's colours are read back at once (the LCD is off: no VBlank to wait for, no stash in VRAM),
// the palettes painted white, the LCD on and the colours faded in. (A read outside VBlank with the LCD on, STAT-checked, was tried: SameBoy returned 0xFF for some, a
// washed-out picture: tests/test_fade_hw.py.)
void trans_card_in(void) BANKED {
    uint8_t c, i, s, f = 0, n = 8, o[128];
    if (!is_cgb) {
        fade_arm();
        tick_sync();
        DISPLAY_ON;
        fade_reveal();
        return;
    }
    for (c = 0; c < 64; c++) {
        i = (c & 31) << 1;
        if (c < 32) { BCPS_REG = i; o[c << 1] = BCPD_REG; BCPS_REG = i | 1; o[(c << 1) | 1] = BCPD_REG; }
        else { OCPS_REG = i; o[c << 1] = OCPD_REG; OCPS_REG = i | 1; o[(c << 1) | 1] = OCPD_REG; }
    }
    BCPS_REG = 0x80;
    for (c = 0; c < 32; c++) { BCPD_REG = 0xFF; BCPD_REG = 0x7F; }
    OCPS_REG = 0x80;
    for (c = 0; c < 32; c++) { OCPD_REG = 0xFF; OCPD_REG = 0x7F; }
    tick_sync();
    DISPLAY_ON;
    vsync(); keep_win(); f++; fa_tail(f, n, 1);                  // (the LCD's first frame is not whole: white)
    for (s = 0; s < 2; s++) f += cstep(o, kc_in[s], COL_W, 0, 2, f, n, 1);
    cstep(o, 8, 0, 0, 2, f, n, 1);
    volume(7);
}

// A menu screen change (owner 2026-10-17: "quick palette fade transition for menu flashes too"): the next DISPLAY_OFF is the white fade F1 at the pause card's
// fast steps (FAST_ON), whatever variant the scene changes use. Not over the pause menu, not where a scene change is already wanted, not with the LCD off or the
// transitions off (tests).
void trans_menu(void) BANKED {
    if ((LCDC_REG & LCDCF_ON) && game_state != GS_PAUSED && !(TRANS & (TR_WANT | TR_OFF))) TRANS |= TR_WANT | TR_FAST;
}

void trans_cover(void) BANKED {
    uint8_t i, j, wy, rows = 0, v = (TRANS & TR_FAST) ? V_WHITE : (TRANS >> TR_VSHIFT) & 3;
    uint8_t b[20];
#ifdef TRANS_CYCLE                                               // the debug ROM: each transition takes the next fade, SELECT held repeats the last
    if (!(TRANS & TR_FAST) && !(joypad() & J_SELECT)) v = v == V_WHITE ? V_AMBER : V_WHITE;
    if (!(TRANS & TR_FAST)) TRANS = (TRANS & ~TR_VMASK) | (v << TR_VSHIFT);
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
    if (FADING) { fade_arm(); music_load_now(); volume(0); TRANS |= TR_ARMED; return; }
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
    if (FADING) { fade_reveal(); return; }
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

// ---- the credits' cast cards (src/credits.c): the picture fades to the band colour and back, the tune playing on (rise 2: no volume) -------------------
// Same machinery as the white fades: palette RAM is written only by the unrolled bursts in the VBlank (vframe), a step is computed in the active part
// of the frame. The caller keeps the card's colours in RAM (o) and never writes palette RAM itself, so the card can be built behind the faded screen.
//   CGB: o = the 128 bytes of palette RAM, BG then OBJ. DMG: o[0..2] = BGP, OBP0, OBP1, stepped shade by shade toward black (the band's shade).
#define CAST_DMG   3                              // frames a DMG step takes
static const uint8_t k_co[4] = { 5, 3, 1, 0 };    // out: eighths of the card's colour kept (0: flat band)
static const uint8_t k_ci[4] = { 1, 3, 5, 8 };    // in, then the card's colours exactly (k 8)

static uint8_t ddark(uint8_t p, uint8_t k) {      // a DMG palette k shades darker
    uint8_t r = 0, i, s;
    for (i = 0; i < 8; i += 2) {
        s = ((p >> i) & 3) + k;
        r |= (s > 3 ? 3 : s) << i;
    }
    return r;
}

// The tune keeps its time through a fade, frame for frame: the main loop ticks at line 18 of every frame, and so does the fade (once a frame, inside
// the long compute; the tick of the frame the call began in first, and the next frame's left to the loop when it ends), so there is no stall when it
// begins and no bunched tick when it ends (a tick at the VBlank instead was ~1.9 frames after the loop's, then ~0.1 before it: an audible hitch a card).
#define TICK_LY 18
#define COL_WHITE 0x7FFF
static void group_t(const uint8_t *o, uint8_t k, uint8_t tick, uint8_t skip6) {   // group(): the 32 colours (most of a frame) toward white, the frame's tick at line 18 inside it
    uint8_t i, a = k & 4, b = k & 2, c = k & 1;
    uint16_t kk = COL_WHITE - part(COL_WHITE, k), w, r;
    uint16_t *q = (uint16_t *)RES;
    const uint16_t *p = (const uint16_t *)o;
    for (i = 0; i < 32; i++) {
        if (tick && (i & 1) && LY_REG >= TICK_LY && LY_REG < 100) { music_tick(); tick = 0; }
        w = *p++;
        if (k == 8 || (skip6 && (i >> 2) == 6)) r = w;                 // (skip6: BG palette 6, the cast cards' header, is left as it is)
        else {
            r = kk;
            if (a) r += (w >> 1) & 0x3DEF;
            if (b) r += (w >> 2) & 0x1CE7;
            if (c) r += (w >> 3) & 0x0C63;
        }
        *q++ = r;
    }
}

static void tick18(void) {
    while (LY_REG >= TICK_LY) ;                                // (from the VBlank: the next frame's line 18)
    while (LY_REG < TICK_LY) ;
    music_tick();
}

static uint8_t dlite(uint8_t p, uint8_t k) {                   // a DMG palette k shades lighter
    uint8_t r = 0, i, s;
    for (i = 0; i < 8; i += 2) {
        s = (p >> i) & 3;
        r |= (s > k ? s - k : 0) << i;
    }
    return r;
}

uint8_t trans_cast(uint8_t *o, uint8_t in, uint8_t hdr) BANKED {      // in 0: the card's colours to white; 1: from white back. Returns the frames it took
    uint8_t s, f = 0, fr, k, g;
    if (LY_REG < TICK_LY) { while (LY_REG < TICK_LY) ; music_tick(); }   // (this frame's tick: the call began before line 18, the loop's would come after us)
    else music_tick();
    if (is_cgb) {
        for (s = 0; s < 4; s++) {
            if (joypad() & (J_B | J_START)) break;             // (B / START cut a fade short: the caller sees the press)
            k = in ? k_ci[s] : k_co[s];
            for (g = 0; g < 2; g++) {
                group_t(g ? o + 64 : o, k, s || g, !g && !hdr);            // (the first group's frame has had its tick)
                f += vframe(g);
            }
        }
    } else {
        for (s = 0; s < 3; s++) {
            if (joypad() & (J_B | J_START)) break;
            k = in ? 2 - s : s + 1;
            for (fr = 0; fr < CAST_DMG; fr++) {
                vsync(); f++;
                if (!fr) {
                    story_scratch[69] = dlite(o[0], k);                // (the card's BGP; the header's too unless it stays: main.c cast_isr)
                    if (hdr) story_scratch[68] = story_scratch[69];
                    OBP0_REG = dlite(o[1], k); OBP1_REG = dlite(o[2], k);
                }
                if (s < 2 || fr < CAST_DMG - 1) tick18();
            }
        }
    }
    while (LY_REG >= 8) ;                                      // (back at the top of the next frame, as the loop's own logic: its tick follows at line 18)
    return f;
}

void trans_cast_set(uint8_t *o) BANKED {                  // the colours in o to the hardware at once (in the VBlank)
    if (is_cgb) { group(o, 8, 0, 0); vframe(0); group(o + 64, 8, 0, 0); vframe(1); }
    else { BGP_REG = o[0]; OBP0_REG = o[1]; OBP1_REG = o[2]; }
}
