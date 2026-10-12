// A boss file's loaders over its own generated art (build/boss_<name>_art.h: boss_art_body, boss_art_pose, ...), in
// the boss file's bank: #include it after that header, in src/boss_<name>.c only.
#ifndef BOSS_LOAD_H
#define BOSS_LOAD_H
#include <gb/cgb.h>
#include "palettes.h"

#if BOSS_ART_POSES > BOSS_POSES_MAX || BOSS_ART_COLS > BOSS_W_MAX || BOSS_ART_PAIRS > BOSS_PAIRS_MAX
#error "boss art: too many poses, columns or column pairs for the engine"
#endif

// BEV_SET: his pose table and hand column into the engine's WRAM copy (boss.c boss_look reads it every pose change)
static void boss_art_set(void) {
    uint8_t p, k;
    for (p = 0; p != BOSS_ART_POSES; p++)
        for (k = 0; k != BOSS_ART_COLS; k++) boss_map[p][k] = boss_art_pose[p][k];
    for (k = 0; k != 4; k++) boss_hand[k] = boss_art_hand[k];
    boss_npose = BOSS_ART_POSES;
}

// BEV_LOAD (LCD off, after start_level loaded every patron variant): his body's column pairs over variant C's tiles
// and the back views, the HUD face, the topper's frames; CGB his palettes (colour 0 the venue's wall): BG palette 4 for
// the body, OBJ palette 7 (lifted variant C's) for the topper. DMG: OBP1 is lift_level_init's 0xE4, the BG's shades.
static void boss_art_load(void) {
    palette_t p;
    set_bkg_data(BOSS_BG_A, (BOSS_ART_PAIRS > BOSS_PAIRS_A ? BOSS_PAIRS_A : BOSS_ART_PAIRS) << 1, boss_art_body);
#if BOSS_ART_PAIRS > BOSS_PAIRS_A
    set_bkg_data(BOSS_BG_B, (BOSS_ART_PAIRS - BOSS_PAIRS_A) << 1, boss_art_body + BOSS_PAIRS_A * 32);
#endif
    set_bkg_data(BOSS_HUD_BG, 1, boss_art_icon);
    set_sprite_data(OBJ_TOPPER, 4, boss_art_hat);
    if (!is_cgb) return;
    p[0] = venue.pal[VENUE_PAL_BAR][0];
    p[1] = boss_art_pal[1]; p[2] = boss_art_pal[2]; p[3] = boss_art_pal[3];
    set_bkg_palette(BOSS_PAL, 1, p);
    p[0] = 0;
    set_sprite_palette(OBJPAL_PATRON_C, 1, p);
}
#endif
