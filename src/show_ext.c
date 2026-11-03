// Per-performer shows and the Color show pool (owner Q14 A, 2026-11-03: bigger shows on Color, smaller on the DMG).
// Format: tools/gen_art.py (per-performer shows). A venue with venue.show_band bit 4 has a "block" after its 32 show tiles (and the two
// extra show palettes when bit 3): the DMG's performers, each on its own loop of frames, optionally X-flipped by the OAM flag. With bit 5
// a second block follows that Color uses instead (frames of up to 24 px wide whose tiles are 8x16 quarters in VRAM bank 1, OAM bit 3)
// and then the pool section that load_venue puts into bank 1 (LCD off).
// Block: [0..1] size, [2] beat period, then per beat a row of 6 bytes (performer k's record offset at 2k), then the 16-byte records: 4 finished OAM entries
// (y + 1 or 0, x from the figure's left edge, tile, prop) that the draw copies into shadow OAM and offsets by the performer's place. Beat = DANCE_STEP (0..period-1).
// No WRAM: the block is read from the venue's bank on each change.
#pragma bank 255
#include <gb/gb.h>
#include <stdint.h>
#include "game.h"
#include "scratch.h"
#include "music.h"

#if OBJ_DANCER != 96
#error "tools/gen_art.py OBJ_DANCER (the records' bank 0 tile ids)"
#endif

static const uint8_t ext_x[NUM_DANCERS] = { 24, 72, 120 };               // as rom0_relief.c dancer_x / dancer_pal
static const uint8_t ext_pal[NUM_DANCERS] = { OBJPAL_DANCER, 4, 3 };
#define EXT_OAM_Y (STAGE_LAST_ROW * 8 - 24 + 16)

// The block this screen uses: Color takes its own when the venue has one.
static const uint8_t *ext_block(void) {
    const uint8_t *p = venue.show_tiles + DANCER_TILE_COUNT * 16 + ((venue.show_band & 8) ? 16 : 0);
    if (is_cgb && (venue.show_band & 0x20)) p += venue.show_tile[5][0] | (uint16_t)venue.show_tile[5][1] << 8;     // (gen_art.py: the DMG block's size)
    return p;
}

// Performer k's four OAM entries (OAM_DANCERS + 4k..): sig as rom0_relief.c dancer_look (bit k: performer k is up). One performer a call, a frame apart
// (rom0_relief.c dancers_step): the beat's row names the record, the record is copied into shadow OAM and moved to the performer's place.
void show_ext_draw(uint8_t sig, uint8_t k) BANKED {
    uint16_t off, s = DANCE_STEP;
    uint8_t e, x, flags;
    const uint8_t *p = ext_block();
    OAM_item_t *o = shadow_OAM + OAM_DANCERS + (k << 2);
    if (!(sig & (1 << k))) { o[0].y = o[1].y = o[2].y = o[3].y = 0; return; }
    far_copy(&off, p + 3 + (s << 2) + (s << 1) + (k << 1), 2, venue_bank);
    far_copy(o, p + off, 16, venue_bank);
    flags = is_cgb ? (OBJX_ON ? ext_pal[k] : OBJPAL_DANCER) : 0;
    x = ext_x[k];
    for (e = 0; e < 4; e++, o++) {
        if (!o->y) continue;
        o->y += EXT_OAM_Y - 1;
        o->x += x;
        o->prop |= flags;
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
    uint8_t ns, i, d[8];
    uint16_t sz;
    const uint8_t *p = ext_block();
    far_copy(&sz, p, 2, venue_bank);
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
