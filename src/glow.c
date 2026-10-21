// Glow around light sources, prototype A (owner 2026-10-17: "a glow effect around fire and other game light sources"; make GLOW=A).
// A slow pulse of the light's BG palette, bistro only: stage palette B (BGPAL_STAGE_B) holds the oven's fire, its brick edge and the two wall
// lamps (the orange/cream), so colours 0 and 1 of it cycle between their own value and a brighter warm one: 5 levels up and 3 back, a step
// every 16 frames (a 2.1 s breath). CGB only: on a DMG every BG tile shares BGP, so a shade pulse would breathe the whole screen; the DMG gets nothing.
// Palette RAM is written in VBlank only: glow_tick runs first in update(), right after the vsync, and gives up on a frame that is already past
// line 150. No WRAM (frame_counter is the clock), no tile ids, nothing when GLOW_A is not defined.
#pragma bank 255
#include <gb/gb.h>
#include <gb/cgb.h>
#include <stdint.h>

#include "game.h"

#ifdef GLOW_A
extern uint8_t frame_counter;
#define VENUE_BISTRO 3

static const uint16_t pulse0[5] = { 0x537F, 0x579F, 0x5B9F, 0x63BF, 0x67DF };   // colour 0: cream (31,27,20) -> (31,30,25)
static const uint16_t pulse1[5] = { 0x1DFA, 0x223B, 0x265C, 0x2A9E, 0x2EDF };   // colour 1: orange (26,15,7) -> (31,22,11)

void glow_tick(void) BANKED {
    uint8_t ph, ly;
    uint16_t c0, c1;
    if (!is_cgb || venue_id != VENUE_BISTRO || !sa_on || (frame_counter & 15) > 2) return;   // (a step lasts 16 frames: written on 3 of them, in case one is late)
    ly = LY_REG;
    if (ly < 144 || ly > 150) return;
    ph = (frame_counter >> 4) & 7;                         // 0..7: up 0 1 2 3 4, back 3 2 1
    if (ph > 4) ph = 8 - ph;
    c0 = BRIGHTEN(pulse0[ph]); c1 = BRIGHTEN(pulse1[ph]);
    BCPS_REG = 0x80 | (BGPAL_STAGE_B << 3);
    BCPD_REG = (uint8_t)c0; BCPD_REG = (uint8_t)(c0 >> 8);
    BCPD_REG = (uint8_t)c1; BCPD_REG = (uint8_t)(c1 >> 8);
}
#endif
