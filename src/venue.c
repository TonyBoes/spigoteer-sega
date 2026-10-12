// Themed venues (M9): each level's stage, bar, floor, drink and show performers. The art per theme is generated
// by tools/gen_art.py into build/venue_<theme>.c (one switchable bank each); venue_fetch() copies the theme's
// venue_t (tile data pointers, tilemaps, CGB attributes, palettes) into WRAM, and the functions here put it on
// screen. Screen transitions only: everything here writes VRAM / palettes with the LCD off.
//
// BG tile ids: one pool of VENUE_POOL (36) ids for the theme: its stage tiles from TILE_STAGE_BASE (0) up, its
// bar/keg/spout/floor tiles packed at the top (venue.bar_base = VENUE_POOL - bar_n, never below the title's text ids
// 0..19); the shared HUD tiles follow at TILE_GENERIC_BASE. OBJ: the drink's 10 frames load over the
// mug ids (OBJ_MUG, OBJ_MUG_FILL, OBJ_MUG_DRINK) and the 3 show performers over OBJ_DANCER.
#pragma bank 255
#include <gb/gb.h>
#include <gb/cgb.h>
#include <stdint.h>

#include "game.h"
#include "music.h"

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
    music_pump();                               // (LCD off, several frames: the music ticks on, music.c)
    bkg_data_far(venue.bar_base, venue.bar_n, venue.bar_tiles, venue_bank);
    music_pump();
    // drink frames: full, empty | fill x4 | drink x4 (2 tiles each)
    spr_data_far(OBJ_MUG, MUG_TILE_COUNT, venue.drink_tiles, venue_bank);
    spr_data_far(OBJ_MUG_FILL, MUG_FILL_TILE_COUNT, venue.drink_tiles + MUG_TILE_COUNT * 16, venue_bank);
    spr_data_far(OBJ_MUG_DRINK, MUG_DRINK_TILE_COUNT, venue.drink_tiles + (MUG_TILE_COUNT + MUG_FILL_TILE_COUNT) * 16, venue_bank);
    spr_data_far(OBJ_GLASS, GLASS_TILE_COUNT, venue.drink_tiles + VENUE_DRINK_TILES * 16, venue_bank);   // its crash
    spr_data_far(OBJ_DANCER, DANCER_TILE_COUNT, venue.show_tiles, venue_bank);
    music_pump();
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
        if (bar_dirs & bar_bit[b]) put_both(BAR_COUNTER_ROW(b), ctr_rtile, ctr_rattr);   // an R bar (mirror.c)
        else put_both(BAR_COUNTER_ROW(b), venue.bar_map + 2 * 20, venue.bar_attr + 2 * 20);
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
        if (y & 3) continue;
        music_pump();                           // (a few frames in all: the title tune plays on, music.c)
    }
}

// ---- stage animation ------------------------------------------------------------------------------------------
// A venue with assets/approved/venues/<t>_anim.txt rewrites the pixels of its animated stage tiles (gen_art gives them
// the last, contiguous stage ids anim_first..anim_first + anim_k - 1) on a looped script; tilemap, attributes and
// palettes never change. The frames and the script are copied into WRAM at level load: the copy queue is drained from
// the VBlank interrupt, whatever ROM bank is mapped then. A script step is 4 bytes: the frame's first tile in
// sa_frames (frame * k), the tiles lo..hi-1 that differ from the previous step's frame (gen_art), and the hold in
// frames; hold 0 ends the script. The update itself goes out through render.c queue_stage, 2 tiles per VBlank.
uint8_t sa_frames[SA_BUF];
static uint8_t sa_script[SA_SCRIPT];
static uint8_t *sa_step;
uint8_t sa_on, sa_hold, sa_timer, sa_lo, sa_left, sa_wait;
uint8_t *sa_frame;
uint16_t sa_vram;

void stage_anim_start(void) BANKED {
    sa_left = 0; sa_wait = 0; sa_on = 0;
    if (!venue.anim_k) return;
    far_copy(sa_frames, venue.anim_frames, venue.anim_frames_n, venue_bank);
    far_copy(sa_script, venue.anim_script, venue.anim_script_n, venue_bank);
    sa_vram = 0x9000 + ((uint16_t)venue.anim_first << 4);       // (BG ids 0..127 at 0x9000: LCDC bit 4 clear)
    sa_frame = sa_frames;
    sa_step = sa_script;
    sa_timer = 1;                               // the first step on the first frame of play
    sa_on = 1;
}

// A new step while the last update is still waiting: the pending range grows to cover both and is copied from the
// new frame (the tiles outside both ranges are the same in the two frames), so nothing is lost or queued twice.
void stage_anim_step(void) BANKED {
    uint8_t *s = sa_step;
    uint8_t lo, hi, ph;
    if (!s[3]) s = sa_script;
    sa_frame = sa_frames + ((uint16_t)s[0] << 4);
    lo = s[1]; hi = s[2];
    if (lo != hi) {
        if (sa_left) {
            ph = sa_lo + sa_left;
            if (sa_lo < lo) lo = sa_lo;
            if (ph > hi) hi = ph;
        }
        sa_lo = lo; sa_left = hi - lo;
    }
    sa_timer = s[3];
    sa_step = s + 4;
}
