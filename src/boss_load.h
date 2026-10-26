// A boss file's loaders over its own generated art (build/boss_<name>_art.h: boss_art_body, boss_art_pose, ...), in
// the boss file's bank: #include it after that header, in src/boss_<name>.c only.
#ifndef BOSS_LOAD_H
#define BOSS_LOAD_H
#include <gb/cgb.h>
#include "palettes.h"

#if BOSS_ART_POSES > BOSS_POSES_MAX || BOSS_ART_COLS > BOSS_W_MAX || BOSS_ART_PAIRS > BOSS_PAIRS_MAX \
    || BOSS_ART_HAT_TILES > 2 * BOSS_HATS_MAX
#error "boss art: too many poses, columns or column pairs for the engine"
#endif

// BEV_SET: his pose table into the engine's WRAM copy (boss.c boss_look reads it every pose change)
static void boss_art_set(void) {
    uint8_t p, k;
    for (p = 0; p != BOSS_ART_POSES; p++)
        for (k = 0; k != BOSS_ART_COLS; k++) boss_map[p * BOSS_W_MAX + k] = boss_art_pose[p][k];
#ifdef BOSS_ART_SWAY
    for (k = 0; k != BOSS_ART_COLS; k++) boss_map[BP_SWAY * BOSS_W_MAX + k] = boss_art_sway[k];
#endif
}

// BEV_LOAD (LCD off, after start_level loaded every patron variant): his body's column pairs over variant C's tiles
// and the back views, the HUD face, the topper's frames; CGB his palettes (colour 0 the venue's wall): BG palette 4 for
// the body, OBJ palette 7 (lifted variant C's) for the topper. DMG: OBP1 is lift_level_init's 0xE4, the BG's shades.
static void boss_art_load(void) {
    palette_t p;
    BOSS_BG((uint8_t)BOSS_BG_A, (BOSS_ART_PAIRS > BOSS_PAIRS_A ? BOSS_PAIRS_A : BOSS_ART_PAIRS) << 1, boss_art_body);
#if BOSS_ART_PAIRS > BOSS_PAIRS_A
    BOSS_BG((uint8_t)BOSS_BG_B, (BOSS_ART_PAIRS - BOSS_PAIRS_A) << 1, boss_art_body + BOSS_PAIRS_A * 32);
#endif
    BOSS_BG(BOSS_HUD_BG, 1, boss_art_icon);
    BOSS_OBJ(OBJ_TOPPER, BOSS_ART_HAT_TILES, boss_art_hat);   // HAT_STILL, HAT_BOB (and his `hats`)
#ifdef BOSS_ART_TILT_T
    BOSS_OBJ(BOSS_ART_TILT_T, 4, boss_art_tilt);               // his hand mug's 45 degree tilt (gen_boss `tilt`; boss.c hand_tilt)
#endif
#ifdef BOSS_ART_FX
    BOSS_BG(BOSS_MARK_BG, BOSS_ART_FX, boss_art_fx);           // the landing marker (gen_boss `fx`)
#endif
    if (!is_cgb) return;
    p[0] = venue.pal[VENUE_PAL_BAR][0];
    p[1] = boss_art_pal[1]; p[2] = boss_art_pal[2]; p[3] = boss_art_pal[3];
    boss_ldpal(0, BOSS_PAL, p);
    p[0] = 0;
    boss_ldpal(1, OBJPAL_PATRON_C, p);
}
// The credits' cast card (src/credits.c) takes his body from his own art file, in his bank: one banked function per boss file, BOSS_CAST_FN(name).
// cmd 0: body tile a (16 bytes) into dst, copied (a DMG card remaps it); 1: the tile pair of column b in pose a; 2: the topper's four tiles
// (STILL, BOB) into dst; 3: dst[0] columns, dst[1] tile pairs, dst[2..7] his colours 1-3 (little endian); 4: body tile a straight to BG tile b;
// 5: the topper's tile a straight to OBJ tile b. (A byte loop in C is ~70 cycles a byte: the card's build takes a tile a unit and writes it direct.)
#define BOSS_CAST_FN(fn) \
uint8_t fn(uint8_t cmd, uint8_t a, uint8_t b, uint8_t *dst) BANKED { \
    uint8_t i, n = 0; \
    uint16_t left; \
    const uint8_t *src; \
    if (cmd == 0) { \
        left = BOSS_ART_PAIRS * 32 - (uint16_t)a * 16; \
        n = left > 16 ? 16 : (uint8_t)left; \
        src = boss_art_body + (uint16_t)a * 16; \
        for (i = 0; i != n; i++) dst[i] = src[i]; \
        return n >> 4; \
    } \
    if (cmd == 4) { set_bkg_data(b, 1, boss_art_body + (uint16_t)a * 16); return 0; } \
    if (cmd == 5) { set_sprite_data(b, 1, boss_art_hat + (uint16_t)a * 16); return 0; } \
    if (cmd == 1) return boss_art_pose[a][b]; \
    if (cmd == 2) { for (i = 0; i != 64; i++) dst[i] = boss_art_hat[i]; return 0; } \
    dst[0] = BOSS_ART_COLS; dst[1] = BOSS_ART_PAIRS; \
    for (i = 0; i != 3; i++) { dst[2 + 2 * i] = (uint8_t)boss_art_pal[1 + i]; dst[3 + 2 * i] = boss_art_pal[1 + i] >> 8; } \
    return 0; \
}
#endif
