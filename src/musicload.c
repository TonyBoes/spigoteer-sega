// Copies a song's pattern blob from its ROM bank into WRAM (src/music.c). This must be a plain, unbanked
// function: it switches the ROM bank under the caller (music.c runs from bank 2).
#include <gb/gb.h>
#include <stdint.h>
#include <string.h>
#include "music.h"

void mus_copy(uint8_t bank, const uint8_t *src, uint8_t *dst, uint16_t n) {
    uint8_t saved = CURRENT_BANK;
    SWITCH_ROM(bank);
    memcpy(dst, src, n);
    SWITCH_ROM(saved);
}
