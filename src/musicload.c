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

// The channel-1 harmony's next event (note, rows) from its bank (src/music.c harm_tick): two bytes, cheaper than mus_copy.
uint16_t harm_peek(const uint8_t *p) {
    uint8_t saved = CURRENT_BANK;
    uint8_t b = HARM_BANK;
    uint16_t v;
    if (cur_tune == TUNE_CREDITS) b = CREDITS_BANK;     // (the credits tune's harmony is in its blob's bank)
    SWITCH_ROM(b);
    v = *(const uint16_t *)p;
    SWITCH_ROM(saved);
    return v;
}
