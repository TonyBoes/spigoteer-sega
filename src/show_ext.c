// Per-performer shows and the Color show pool (owner Q14 A, 2026-11-03: bigger shows on Color, smaller on the DMG).
// Format: tools/gen_art.py (per-performer shows). A venue with venue.show_band bit 4 has a "block" after its 32 show tiles (and the two
// extra show palettes when bit 3): the DMG's performers, each on its own loop of frames, optionally X-flipped by the OAM flag. With bit 5
// a second block follows that Color uses instead (frames of up to 24 px wide whose tiles are 8x16 quarters in VRAM bank 1, OAM bit 3)
// and then the pool section that load_venue puts into bank 1 (LCD off).
// Block: [0] size, [1] figure width, [2] beat period, [3..5] loop length | flip << 4 (performer k), [6..29] the loops' frame ids (8 each),
// [30..] per frame 4 x (tile, pos): pos bit 7 none, bits 0-1 cell column, bit 2 cell row (lines 0-15 / 16-23), bit 3 bank 1 (tile = its id)
// else tile = offset from OBJ_DANCER. Beat = DANCE_STEP (0..period-1). No WRAM: the block is read from the venue's bank on each change.
#pragma bank 255
#include <gb/gb.h>
#include <stdint.h>
#include "game.h"
#include "scratch.h"
#include "music.h"

#define EXT_HEAD   30
#define EXT_OAM_B1 0x08

static const uint8_t ext_x[NUM_DANCERS] = { 24, 72, 120 };               // as rom0_relief.c dancer_x / dancer_pal
static const uint8_t ext_pal[NUM_DANCERS] = { OBJPAL_DANCER, 4, 3 };
#define EXT_OAM_Y (STAGE_LAST_ROW * 8 - 24 + 16)

// The block this screen uses: Color takes its own when the venue has one.
static const uint8_t *ext_block(void) {
    const uint8_t *p = venue.show_tiles + DANCER_TILE_COUNT * 16 + ((venue.show_band & 8) ? 16 : 0);
    uint8_t sz;
    if (is_cgb && (venue.show_band & 0x20)) { far_copy(&sz, p, 1, venue_bank); p += sz; }
    return p;
}

// The three performers' OAM entries (OAM_DANCERS..): sig as rom0_relief.c dancer_look (bit k: performer k is up).
void show_ext_draw(uint8_t sig) BANKED {
    uint8_t h[EXT_HEAD], r[8], k, e, f, n, hd, w, x, pos, flags;
    const uint8_t *p = ext_block();
    OAM_item_t *o = shadow_OAM + OAM_DANCERS;
    far_copy(h, p, EXT_HEAD, venue_bank);
    w = h[1];
    for (k = 0; k < NUM_DANCERS; k++, o += 4) {
        if (!(sig & (1 << k))) { o[0].y = o[1].y = o[2].y = o[3].y = 0; continue; }
        hd = h[3 + k];
        n = hd & 15;
        f = DANCE_STEP;
        while (f >= n) f -= n;                                   // (the beat modulo this performer's loop length)
        far_copy(r, p + EXT_HEAD + ((uint16_t)h[6 + (k << 3) + f] << 3), 8, venue_bank);
        flags = (is_cgb ? (OBJX_ON ? ext_pal[k] : OBJPAL_DANCER) : 0) | ((hd & 16) ? S_FLIPX : 0);
        x = ext_x[k] + 8 - ((w - 16) >> 1);                      // (a 24 px figure reaches 4 px past the 16 px one's edges)
        for (e = 0; e < 4; e++) {
            pos = r[2 * e + 1];
            if (pos & 0x80) { o[e].y = 0; continue; }
            n = (pos & 3) << 3;
            o[e].y = EXT_OAM_Y + ((pos & 4) ? 16 : 0);
            o[e].x = x + ((hd & 16) ? (uint8_t)(w - 8 - n) : n);
            o[e].tile = (pos & EXT_OAM_B1) ? r[2 * e] : (uint8_t)(OBJ_DANCER + r[2 * e]);
            o[e].prop = flags | (pos & EXT_OAM_B1);
        }
    }
}

// A dance beat (rom0_relief.c dance_next): the beat counts to the block's period; dancer_frame just changes (render.c's quick check compares it).
void show_ext_next(void) BANKED {
    uint8_t per, i = DANCE_STEP + 1;
    far_copy(&per, ext_block() + 2, 1, venue_bank);
    DANCE_STEP = i >= per ? 0 : i;
    dancer_frame = (dancer_frame + 1) & 3;
}

// The Color pool into VRAM bank 1 (load_venue, LCD off, Color only): [segments n] [first OBJ id, tiles] x n, then the tiles, after the Color block.
void show_pool_load(void) BANKED {
    uint8_t ns, i, d[8], sz;
    const uint8_t *p = ext_block();
    far_copy(&sz, p, 1, venue_bank);
    p += sz;
    far_copy(&ns, p, 1, venue_bank);
    far_copy(d, p + 1, 2 * ns, venue_bank);
    p += 1 + 2 * ns;
    VBK_REG = VBK_BANK_1;
    for (i = 0; i < ns; i++) {
        spr_data_far(d[2 * i], d[2 * i + 1], p, venue_bank);
        p += (uint16_t)d[2 * i + 1] << 4;
        music_pump();
    }
    VBK_REG = VBK_BANK_0;
}
