// SETTINGS > SCREEN BRIGHT (src/bright.h): the lift itself, in a banked file so ROM0 only holds the small pal_put (main.c).
// bright_tbl[i] = round(31 * (i / 31) ^ 0.7): strictly rising through the darks (0..16), so dark colours stay apart, and never falling; 0 and 31 are fixed (black and white, the fades' ends,
// do not move). tests/test_bright.py recomputes it and finds it in the ROM.
#pragma bank 255
#include <gb/gb.h>
#include <gb/cgb.h>
#include <stdint.h>
#include "game.h"
#include "palettes.h"
#include "looks.h"

static const uint8_t bright_tbl[32] = { 0, 3, 5, 6, 7, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 20, 21, 22, 23, 24, 24, 25, 26, 27, 27, 28, 29, 30, 30, 31 };

uint16_t bright_col(uint16_t c) BANKED {
    return bright_tbl[c & 31] | ((uint16_t)bright_tbl[(c >> 5) & 31] << 5) | ((uint16_t)bright_tbl[(c >> 10) & 31] << 10);
}

void pal_lift(uint16_t *q) BANKED {                       // four colours, in place
    q[0] = bright_col(q[0]); q[1] = bright_col(q[1]); q[2] = bright_col(q[2]); q[3] = bright_col(q[3]);
}

void pal_put_b(uint8_t first, uint8_t n, uint16_t *q) BANKED {   // (first | 0x80: OBJ)
    uint8_t k;
    for (k = 0; k < n; k++) pal_lift(q + 4 * k);
    if (first & 0x80) (set_sprite_palette)(first & 0x7F, n, q); else (set_bkg_palette)(first, n, q);
}

// BRIGHT: the show's colours (OBJ palette 5) lifted into pal5_lifted (the VBlank writes it raw: render.c pal5_write).
void pal5_lift(void) BANKED {
    uint8_t i;
    for (i = 0; i < 4; i++) pal5_lifted[i] = bright_col(venue.pal[VENUE_PAL_SHOW][i]);
}
// The generated venues give OBJ palette 5 back to palette instance 4 after a show: its colours (lifted when BRIGHT) into pal5_lifted, which the VBlank writes raw.
void pal5_inst4(uint8_t g) BANKED {
    uint8_t i, r = looks_pal_get(g, 4, pal5_lifted);       // (1 / 2: the venue's full / empty mug colours, dst untouched)
    for (i = 0; i < 4; i++) {
        if (r) pal5_lifted[i] = venue.pal[r == 1 ? VENUE_PAL_DRINK_FULL : VENUE_PAL_DRINK_EMPTY][i];
        pal5_lifted[i] = BRIGHTEN(pal5_lifted[i]);
    }
}
