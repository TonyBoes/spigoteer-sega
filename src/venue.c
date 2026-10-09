// Themed venues (M9): each level's stage, bar, floor, drink and show performers. The art per theme is generated
// by tools/gen_art.py into build/venue_<theme>.c (one switchable bank each); venue_fetch() copies the theme's
// venue_t (tile data pointers, tilemaps, CGB attributes, palettes) into WRAM, and the functions here put it on
// screen. Screen transitions only: everything here writes VRAM / palettes with the LCD off.
//
// BG tile ids: the theme's stage tiles load over TILE_STAGE_BASE (20 ids), its bar/keg/spout/floor tiles over
// TILE_BAR_BASE (16 ids); the shared HUD tiles follow at TILE_GENERIC_BASE. OBJ: the drink's 10 frames load over the
// mug ids (OBJ_MUG, OBJ_MUG_FILL, OBJ_MUG_DRINK) and the 3 show performers over OBJ_DANCER.
#pragma bank 255
#include <gb/gb.h>
#include <gb/cgb.h>
#include <stdint.h>

#include "game.h"

// ROM0 helpers (main.c): copy out of another ROM bank and come back to this one
void far_copy(void *dst, const void *src, uint16_t n, uint8_t bank);
void bkg_data_far(uint8_t first, uint8_t n, const uint8_t *d, uint8_t bank);
void spr_data_far(uint8_t first, uint8_t n, const uint8_t *d, uint8_t bank);

uint8_t venue_id;               // theme loaded now (= patron group of the level; 0 saloon on the title)

// Theme t's tiles, palettes and the bars' base picture (render.c restores it under the patrons). LCD off.
void load_venue(uint8_t t) BANKED {
    uint8_t r, c;
    venue_fetch(t);
    venue_id = t;
    bkg_data_far(TILE_STAGE_BASE, venue.stage_n, venue.stage_tiles, venue_bank);
    bkg_data_far(TILE_BAR_BASE, venue.bar_n, venue.bar_tiles, venue_bank);
    // drink frames: full, empty | fill x4 | drink x4 (2 tiles each)
    spr_data_far(OBJ_MUG, MUG_TILE_COUNT, venue.drink_tiles, venue_bank);
    spr_data_far(OBJ_MUG_FILL, MUG_FILL_TILE_COUNT, venue.drink_tiles + MUG_TILE_COUNT * 16, venue_bank);
    spr_data_far(OBJ_MUG_DRINK, MUG_DRINK_TILE_COUNT, venue.drink_tiles + (MUG_TILE_COUNT + MUG_FILL_TILE_COUNT) * 16, venue_bank);
    spr_data_far(OBJ_DANCER, DANCER_TILE_COUNT, venue.show_tiles, venue_bank);
    for (r = 0; r < 2; r++)
        for (c = 0; c < 20; c++) {
            base_tile[r][c] = venue.bar_map[r * 20 + c];
            base_attr[r][c] = venue.bar_attr[r * 20 + c];
        }
    if (!is_cgb) return;                        // DMG: the fixed grey ramps (the art is luminance-ordered)
    set_bkg_palette(BGPAL_STAGE, 1, venue.pal[VENUE_PAL_STAGE_A]);
    set_bkg_palette(BGPAL_STAGE_B, 1, venue.pal[VENUE_PAL_STAGE_B]);
    set_bkg_palette(BGPAL_BAR, 1, venue.pal[VENUE_PAL_BAR]);
    set_bkg_palette(BGPAL_BAR_B, 1, venue.pal[VENUE_PAL_BAR_B]);
    set_sprite_palette(OBJPAL_MUG_FULL, 1, venue.pal[VENUE_PAL_DRINK_FULL]);
    set_sprite_palette(OBJPAL_MUG_EMPTY, 1, venue.pal[VENUE_PAL_DRINK_EMPTY]);
    set_sprite_palette(OBJPAL_DANCER, 1, venue.pal[VENUE_PAL_SHOW]);
}

static uint8_t vrow[20];

static void put_both(uint8_t y, const uint8_t *tiles, const uint8_t *attrs) {
    set_bkg_tiles(0, y, 20, 1, tiles);
    if (!is_cgb) return;
    VBK_REG = VBK_BANK_1;
    set_bkg_tiles(0, y, 20, 1, attrs);
    VBK_REG = VBK_BANK_0;
}

// The level screen except the patrons' wall rows (render.c's write_all_bars): HUD row attributes, the stage (rows
// 1-4), each bar's counter row and the floor. LCD off.
void draw_venue(void) BANKED {
    uint8_t b, i;
    for (i = 0; i < STAGE_LAST_ROW - STAGE_FIRST_ROW + 1; i++)
        put_both(STAGE_FIRST_ROW + i, venue.stage_map + i * 20, venue.stage_attr + i * 20);
    for (b = 0; b < NUM_BARS; b++)
        put_both(BAR_COUNTER_ROW(b), venue.bar_map + 2 * 20, venue.bar_attr + 2 * 20);
    for (i = 0; i < 20; i++) vrow[i] = venue.floor_tile;
    if (is_cgb) {
        VBK_REG = VBK_BANK_1;
        for (b = 0; b < 20; b++) row_buf[b] = BGPAL_BAR;
        set_bkg_tiles(0, FLOOR_ROW, 20, 1, row_buf);
        for (b = 0; b < 20; b++) row_buf[b] = BGPAL_HUD;
        set_bkg_tiles(0, HUD_ROW, 20, 1, row_buf);
        VBK_REG = VBK_BANK_0;
    }
    set_bkg_tiles(0, FLOOR_ROW, 20, 1, vrow);
}

// A plain wall of the current venue (no keg) from row `first` down: the wall rows' pattern of columns
// 2-16, a counter row at `counter_row`, the floor on row 17. The title screen and the bonus round stand in it. LCD off.
void venue_backdrop(uint8_t first, uint8_t counter_row) BANKED {
    uint8_t y, i, k;
    static uint8_t arow[20];
    for (y = first; y < 18; y++) {
        for (i = 0; i < 20; i++) {
            if (y == FLOOR_ROW) { vrow[i] = venue.floor_tile; arow[i] = BGPAL_BAR; continue; }
            k = y == counter_row ? 40 + 2 + (i & 15) : (y & 1) * 20 + 2 + (i < 15 ? i : i - 15);
            vrow[i] = venue.bar_map[k];
            arow[i] = venue.bar_attr[k];
        }
        put_both(y, vrow, arow);
    }
}
