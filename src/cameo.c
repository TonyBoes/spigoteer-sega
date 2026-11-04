// Story cameos (owner-approved 2026-11-04): Sasquatch, Leo and the UFO beam-up in the story scenes.
// story.c calls cam_load (scene start, LCD off), cam_page (every page turn, before Dregs's gag) and cam_frame (every scene frame).
// State: win_rows[4] (the goal banner's last row, unused in a scene): [0] the page's cue (0 none), [1] its frame (0-255, stops at 255),
// [2] OAM entries written last frame, [3] the Spigoteer's top OAM y as drawn by scene_enter, [4] the next OAM entry while drawing.
// OAM 20-39 (Dregs's gag range: a cue page is never a gag page). OBJ tiles: cameo_art.h. CGB OBJ palettes 7 (the boss / the UFO and
// its beam) and 6 (the valve), written once at scene start; DMG OBP1 (the bosses, as in their fights) and OBP0 (the UFO, as on the map).
#pragma bank 255
#include <gb/gb.h>
#include <gb/cgb.h>
#include <stdint.h>

#include "game.h"
#include "story.h"
#include "cameo_art.h"

extern uint8_t win_rows[5][20];
#define ST       (win_rows[4])
#define OAM0     20
#define RGB15(r, g, b) ((uint16_t)((r) | ((g) << 5) | ((b) << 10)))
#define P8(r, g, b) RGB15((r) >> 3, (g) >> 3, (b) >> 3)

static const uint16_t pal_sq[4]    = { 0, P8(0xE8, 0xB8, 0x78), P8(0x5C, 0x2C, 0x14), P8(0x14, 0x08, 0x04) };   // sasquatch.txt "pal"
static const uint16_t pal_leo[4]   = { 0, P8(0xF8, 0xD0, 0x60), P8(0xC8, 0x60, 0x18), P8(0x30, 0x18, 0x08) };   // leo.txt "PAL"
static const uint16_t pal_ufo[4]   = { 0, P8(0xF0, 0xF8, 0xF8), P8(0x70, 0x98, 0xD8), P8(0x18, 0x18, 0x40) };   // obj_ufo.png
static const uint16_t pal_valve[4] = { 0, P8(0xF8, 0xF0, 0xA0), P8(0xE8, 0xA8, 0x28), P8(0x14, 0x0C, 0x24) };   // intro_pieces.txt keys

enum { CU_NONE, CU_PRE_WAVE, CU_HANDOVER, CU_SNEAK, CU_WAVE, CU_LEO_CROWN, CU_LEO_PURR, CU_LEO_PLACED, CU_CROWNED, CU_UP, CU_DOWN };
// scene, page (0-based), cue
static const uint8_t cues[] = {
    SC_PRE_LUMBER, 2, CU_PRE_WAVE,  SC_PRE_LUMBER, 3, CU_PRE_WAVE,
    SC_POST_LUMBER, 1, CU_HANDOVER, SC_POST_LUMBER, 2, CU_SNEAK, SC_POST_LUMBER, 3, CU_WAVE,
    SC_PRE_ZOO, 3, CU_LEO_CROWN,
    SC_POST_ZOO, 0, CU_LEO_PURR,    SC_POST_ZOO, 1, CU_LEO_PLACED,  SC_POST_ZOO, 2, CU_CROWNED,
    SC_PRE_SPACE, 0, CU_UP,         SC_PRE_SPACE, 1, CU_DOWN,
    255 };

#define BAR_Y(b) (40 + 24 * (b))   // a bar's first wall row (layout.h BAR_TOP_Y)

#define n        (win_rows[4][4])   // the next OAM entry while drawing (no WRAM of its own)

static void fig(const uint8_t *f, int16_t x, int16_t y, uint8_t prop) {
    uint8_t k = f[0];
    OAM_item_t *o;
    f++;
    while (k--) {
        int16_t ex = x + (int8_t)f[0], ey = y + (int8_t)f[1];
        if (n < 40) {
            o = shadow_OAM + n++;
            if (ex < -7 || ex > 159 || ey < -15 || ey > 143) o->y = 0;
            else { o->y = (uint8_t)(ey + 16); o->x = (uint8_t)(ex + 8); o->tile = f[2]; o->prop = prop | (f[3] ? S_FLIPX : 0); }
        }
        f += 4;
    }
}

static void sal_y(uint8_t up, uint8_t show) {    // the Spigoteer's 4 entries, raised by up px, or hidden
    uint8_t i, y = ST[3] - up;
    for (i = 0; i < 4; i++) shadow_OAM[i].y = show ? (i < 2 ? y : y + 16) : 0;
}

void cam_load(uint8_t s) BANKED {                // LCD off, after the venue / Dregs's gag tiles
    uint8_t v = (s - 1) >> 1;
    ST[0] = 0; ST[2] = 0; ST[3] = shadow_OAM[0].y;
    if (!is_cgb && (v == 2 || v == 8 || v == 9)) OBP1_REG = OBP1_PLAY;   // DMG: 0xE4 (a PRE scene leaves the title's 0xC4)
    if (v == 2) {
        set_sprite_data(CAM_LUMBER_BASE, CAM_LUMBER_N, cam_tiles_lumber);
        if (is_cgb) { set_sprite_palette(7, 1, pal_sq); set_sprite_palette(6, 1, pal_valve); }
    } else if (v == 8) {
        set_sprite_data(CAM_ZOO_BASE, CAM_ZOO_N, cam_tiles_zoo);
        if (is_cgb) set_sprite_palette(7, 1, pal_leo);
    } else if (v == 9) {
        set_sprite_data(CAM_SPACE_BASE, CAM_SPACE_N, cam_tiles_space);
        if (is_cgb) set_sprite_palette(7, 1, pal_ufo);
    }
}

void cam_page(uint8_t s, uint8_t page) BANKED {
    const uint8_t *c = cues;
    uint8_t i;
    if (ST[0] == CU_UP || ST[0] == CU_DOWN) sal_y(0, 1);   // the Spigoteer back at his tap
    for (i = 0; i < ST[2]; i++) shadow_OAM[OAM0 + i].y = 0;
    ST[0] = 0; ST[1] = 0; ST[2] = 0;
    for (; c[0] != 255; c += 3) if (c[0] == s && c[1] == page) { ST[0] = c[2]; break; }
}

void cam_frame(void) BANKED {
    uint8_t t = ST[1], i, pb = is_cgb ? 7 : S_PALETTE, pv = is_cgb ? 6 : S_PALETTE, pu = is_cgb ? 7 : 0, rows;
    int16_t x, y;
    if (!ST[0]) return;
    n = OAM0;
    switch (ST[0]) {
    case CU_PRE_WAVE:                            // behind June: up on the back bar, waving (HAPPY)
    case CU_WAVE:                                // at Dregs: the same
        fig(cf_sq_happy, 84, BAR_Y(0), pb); fig(cf_sq_hat, 84 + 12, BAR_Y(0) - 8, pb);
        if (ST[0] == CU_WAVE) fig(cf_valve, 104, 68, pv);
        break;
    case CU_HANDOVER:                            // beside the Spigoteer, the valve up in his waving hand; then it is on the counter and he ducks off left
        if (t < 90) {
            fig(cf_sq_happy, 88, BAR_Y(1), pb); fig(cf_sq_hat, 88 + 12, BAR_Y(1) - 8, pb);
            fig(cf_valve, 88 + 24, BAR_Y(1) - 14, pv);
        } else {
            fig(cf_valve, 104, 68, pv);
            x = 88 - (int16_t)(t - 90) / 2;
            fig(cf_sq_duck, x, BAR_Y(1) - ((t >> 3) & 1), pb);
        }
        break;
    case CU_SNEAK:                               // "no such thing": only crest, brow and eyes over the back bar, tiptoe bob
        fig(cf_valve, 104, 68, pv);
        fig(cf_sq_duck, 84, BAR_Y(0) - ((t >> 3) & 1), pb);   // (the back bar: on the bottom bar his eyes sat on the text box's edge)
        break;
    case CU_LEO_CROWN:                           // on the back bar, crowned (WALK)
        fig(cf_leo_walk, 84, BAR_Y(0), pb); fig(cf_leo_hat, 84 + 6, BAR_Y(0) - 8, pb);
        break;
    case CU_LEO_PURR:                            // beside the Spigoteer, crowned, purring (HAPPY)
        fig(cf_leo_happy, 88, BAR_Y(1), pb); fig(cf_leo_hat, 88 + 6, BAR_Y(1) - 8, pb);
        break;
    case CU_LEO_PLACED:                          // the crown on the Spigoteer's head (its band on his hair's top row), Leo's paw still up
        fig(cf_leo_happy, 88, BAR_Y(1), pb);
        /* fall through */
    case CU_CROWNED:
        fig(cf_leo_hat, TAP_X + 3, (int16_t)ST[3] - 16 - 8, pb);
        break;
    case CU_UP:                                  // the UFO flies in, beams down, the Spigoteer rises into it, it flies off
    case CU_DOWN:                                // the same backwards: he is set down at his tap
        if (t < 30) x = ST[0] == CU_UP ? 116 + (30 - t) * 2 : 116 - (30 - t) * 2;
        else if (t < 96) x = 116;
        else x = ST[0] == CU_UP ? 116 - (t - 96) * 3 : 116 + (t - 96) * 3;
        y = 39 + ((t >> 4) & 1);
        rows = t < 30 ? 0 : t < 34 ? 1 : t < 38 ? 2 : t < 80 ? 3 : t < 84 ? 2 : t < 88 ? 1 : 0;
        if (rows) {                              // the beam, band by band from the top (entries 0-2 band 0, 3-5 band 1, 6-8 band 2)
            uint8_t keep = cf_beam[0];
            {                                    // (a copy of the beam's entry list, cut to the bands shown)
                uint8_t tmp[1 + 9 * 4];
                tmp[0] = rows * 3 > keep ? keep : rows * 3;
                for (i = 0; i < tmp[0] * 4; i++) tmp[1 + i] = cf_beam[1 + i];
                fig(tmp, 116, y + 11, is_cgb ? 7 : S_PALETTE);   // (DMG: OBP1, dark-grey edges and light-grey rings on the white wall)
            }
        }
        fig(cf_ufo, x, y, pu);
        if (ST[0] == CU_UP) {
            if (t < 44) sal_y(0, 1);
            else if (t < 74) sal_y((t - 44) / 2, 1);
            else sal_y(0, 0);
        } else {
            if (t < 44) sal_y(0, 0);
            else if (t < 74) sal_y(15 - (t - 44) / 2, 1);
            else sal_y(0, 1);
        }
        break;
    }
    for (i = n; i < OAM0 + ST[2]; i++) shadow_OAM[i].y = 0;
    ST[2] = n - OAM0;
    if (t < 255) ST[1] = t + 1;
}
