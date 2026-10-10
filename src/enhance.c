// M14a enhanced patron variants (patron review, recommendation 7; tools/gen_art.py enhanced_group has the rule and the
// validator). An enhanced variant draws its top tile row with one BG palette and its bottom row with another (render.c
// pat_row / back_row), and when lifted its left 8x16 column with one OBJ palette and its right column with another
// (lift.c lift_prop[v] / lift_prop[4 + v]); a column whose colours sit at other indices in its OBJ palette draws a
// re-indexed copy of its two tiles from CGB VRAM bank 1 (same tile ids, OAM attribute bit 3). Slots: the extra BG palette
// is the venue's bar_b (BG 7, load_venue), the extra OBJ palette the group's <group>_x (OBJ 4, loaded here).
// DMG: the rows' attributes are not written (render.c) and the lifted entries use OBP1 and the bank-0 tiles, as before.
#pragma bank 6           // (bank 6 has room; autobank put it in bank 3 next to the music patterns)
#include <gb/gb.h>
#include <gb/cgb.h>
#include <stdint.h>

#include "game.h"
#include "palettes.h"
#include "patron_enh.h"     // this bank's own data (tools/gen_art.py)

uint8_t pat_row[8];         // BG palette of variant v's front view: top tile row [v], bottom row [4 + v]
uint8_t back_row[8];        // ... of its back view
static const uint8_t x_ids[PATRON_GROUPS] = PATRON_X_IDS;   // PAL_* id of the group's extra OBJ palette, 255: none

// Level load (LCD off), after lift_level_init: the row palettes, the lifted columns' attributes, OBJ 4 and the bank-1
// lift tiles of group g.
void enhance_load(uint8_t g) BANKED {
    const uint8_t *s = enh_tab[g], *d;
    uint8_t i, n;
    for (i = 0; i < 8; i++) {
        pat_row[i] = s[i];
        back_row[i] = s[8 + i];
        lift_prop[i] = is_cgb ? s[16 + i] : S_PALETTE;
    }
    if (!is_cgb) return;
    if (x_ids[g] != 255) { palette_t p; pal_get(x_ids[g], p); set_sprite_palette(OBJPAL_ENH, 1, p); }
    n = enh_b1_n[g];
    if (!n) return;
    d = enh_b1[g];
    VBK_REG = VBK_BANK_1;
    for (; n; n--, d += 33) set_sprite_data(d[0], 2, d + 1);
    VBK_REG = VBK_BANK_0;
}
