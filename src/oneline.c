// The one-line menu style's shared pieces (src/oneline.h): the tiles, the selection line's band and arrows, the hint row, the direction keys with hold-to-repeat.
// Banked. No string of a caller's bank is read here (a banked call maps this bank in): the callers put their own text and call ol_glyph for each letter.
#pragma bank 255
#include <gb/gb.h>
#include <gb/cgb.h>
#include <stdint.h>

#define ONELINE_C
#include "game.h"
#include "story.h"
#include "oneline.h"
#include "list_keys.h"          // static const uint8_t list_key_tiles[]: the A and B buttons (and the D-pad's right press, unused here)
#include "ol_tiles.h"           // static const uint8_t ol_tiles[OL_N * 16] (assets/art/ol_tiles.txt, ol_icons.txt)

#define OL_DELAY  18            // a held LEFT / RIGHT repeats after this many frames ...
#define OL_RATE    5            // ... then every this many
#define OL_FLASH   7            // frames an arrow stays kicked out after a press
#define OL_BOB    16            // frames the arrows spend out, then in

typedef char ol_fits[(OL_T_ICON + 3 < TILE_GENERIC_BASE && sizeof(struct ol_state) == SCR_OL_N) ? 1 : -1];

void ol_load(void) BANKED {
    set_bkg_data(OL_T, OL_N, ol_tiles);
    set_bkg_data(OL_KEY_A, 2, list_key_tiles);
    OL->hold = OL->flash = OL->key = OL->bob = OL->t = 0;
}

uint8_t ol_glyph(char c) BANKED {
    if ((uint8_t)(c - 'A') < 26) return glyph_az[(uint8_t)(c - 'A')];   // (letters first: the common case)
    switch (c) {
    case ' ': return TILE_HUD_BLANK;
    case '.': return ST_GLYPH_PERIOD; case ',': return ST_GLYPH_COMMA; case '!': return ST_GLYPH_EXCL;
    case '?': return ST_GLYPH_QUEST; case '\'': return ST_GLYPH_APOS; case '-': return ST_GLYPH_HYPHEN;
    case ':': return ST_GLYPH_COLON; case '/': return OL_T_SLASH;
    }
    return GLYPH_FAST(c, glyph_for(c));
}

void ol_arrows(uint8_t *r) BANKED {
    uint8_t kick = OL->flash ? OL->key : 0;     // out by a pixel while the bob is out, and on the side just pressed
    r[0] = OL_T + (OL->bob || (kick & J_LEFT) ? 2 : 0);
    r[19] = OL_T + 1 + (OL->bob || (kick & J_RIGHT) ? 2 : 0);
}

void ol_hint(uint8_t *r, uint8_t a) BANKED {
    const char *w;
    uint8_t i;
    ol_blank(r);
    if (a != OL_A_NONE) {
        r[2] = OL_KEY_A;
        w = a == OL_A_STOP ? "STOP" : "PLAY";
        for (i = 0; i < 4; i++) r[4 + i] = ol_glyph(w[i]);
    }
    r[11] = OL_KEY_B;
    w = "BACK";
    for (i = 0; i < 4; i++) r[13 + i] = ol_glyph(w[i]);
}

// LCD off, after list_frame: rows 2 and 4 are the panel's light lines, row 3 the band (list_frame left it a wall row): on CGB all three in the panel's
// palette, the arrows' cells in arrow_pal. The caller writes row 3's tiles (ol_arrows, the name). A DMG has one palette: the two light lines and the arrows.
void ol_band(uint8_t arrow_pal) BANKED {
    uint8_t x, r[20];
    for (x = 0; x < 20; x++) r[x] = TILE_PANEL_TOP;
    set_bkg_tiles(0, OL_ROW_BAND - 1, 20, 1, r);
    for (x = 0; x < 20; x++) r[x] = TILE_PANEL_BOT;
    set_bkg_tiles(0, OL_ROW_BAND + 1, 20, 1, r);
    if (!is_cgb) return;
    VBK_REG = VBK_BANK_1;
    for (x = 0; x < 20; x++) r[x] = SKIN_PAL_FOOT;
    set_bkg_tiles(0, OL_ROW_BAND - 1, 20, 1, r);
    set_bkg_tiles(0, OL_ROW_BAND + 1, 20, 1, r);
    r[0] = r[19] = arrow_pal;
    set_bkg_tiles(0, OL_ROW_BAND, 20, 1, r);
    VBK_REG = VBK_BANK_0;
}

// A press answers at once; a held LEFT / RIGHT repeats after OL_DELAY frames, then every OL_RATE. UP / DOWN never repeat.
uint8_t ol_key(uint8_t pressed, uint8_t held) BANKED {
    uint8_t k;
    pressed &= J_LEFT | J_RIGHT | J_UP | J_DOWN;
    if (pressed) {
        k = pressed & J_LEFT ? J_LEFT : pressed & J_RIGHT ? J_RIGHT : pressed & J_UP ? J_UP : J_DOWN;
        OL->hold = OL_DELAY; OL->flash = OL_FLASH; OL->key = k;
        return k;
    }
    k = held & (J_LEFT | J_RIGHT);
    if (k == J_LEFT || k == J_RIGHT) {
        if (OL->hold) OL->hold--;
        if (!OL->hold) { OL->hold = OL_RATE; OL->flash = OL_FLASH; OL->key = k; return k; }
    }
    return 0;
}

uint8_t ol_tick(void) BANKED {
    uint8_t moved = 0;
    if (OL->flash && !--OL->flash) moved = 1;
    if (!(++OL->t & (OL_BOB - 1))) { OL->bob ^= 1; moved = 1; }
    return moved;
}

char *ol_counter(char *d, uint8_t i, uint8_t n) BANKED {
    if (i >= 10) *d++ = '0' + i / 10;
    *d++ = '0' + i % 10;
    *d++ = ' '; *d++ = '/'; *d++ = ' ';
    if (n >= 10) *d++ = '0' + n / 10;
    *d++ = '0' + n % 10;
    *d = 0;
    return d;
}

uint8_t ol_wrap(uint8_t s, uint8_t n, int8_t d) BANKED {
    int16_t v = (int16_t)s + d;
    while (v < 0) v += n;
    while (v >= n) v -= n;
    return (uint8_t)v;
}
