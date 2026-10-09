// Saved hi score (M7): cartridge SRAM, MBC5+RAM+BATTERY. Layout at 0xA000:
//   0..3 magic "TPR1", 4..7 hi score (little endian), 8 checksum, 9 its complement.
// Anything that does not check out loads as 0. Same fixed bank as the music (small, keeps ROM bank use low).
#pragma bank 2
#include <gb/gb.h>
#include <stdint.h>
#include "music.h"

extern uint32_t hi_score;
extern uint8_t  hi_digits[6];

#define SRAM ((volatile uint8_t *)0xA000)
#define HI_MAX 999999UL

static uint8_t checksum(void) {
    uint8_t i, s = 0x5A;
    for (i = 0; i < 8; i++) s += SRAM[i];
    return s;
}

static void make_digits(void) {
    uint32_t v = hi_score;
    uint8_t i;
    for (i = 6; i != 0; i--) { hi_digits[i - 1] = (uint8_t)(v % 10); v /= 10; }
}

void hi_load(void) BANKED {
    uint8_t ok;
    uint32_t v;
    ENABLE_RAM;
    SWITCH_RAM(0);
    ok = SRAM[0] == 'T' && SRAM[1] == 'P' && SRAM[2] == 'R' && SRAM[3] == '1';
    if (ok) {
        uint8_t c = checksum();
        ok = SRAM[8] == c && SRAM[9] == (uint8_t)~c;
    }
    v = 0;
    if (ok) {
        v = (uint32_t)SRAM[4] | ((uint32_t)SRAM[5] << 8) | ((uint32_t)SRAM[6] << 16) | ((uint32_t)SRAM[7] << 24);
        if (v > HI_MAX) v = 0;
    }
    DISABLE_RAM;
    hi_score = v;
    make_digits();
}

void hi_save(void) BANKED {
    uint8_t c;
    ENABLE_RAM;
    SWITCH_RAM(0);
    SRAM[0] = 'T'; SRAM[1] = 'P'; SRAM[2] = 'R'; SRAM[3] = '1';
    SRAM[4] = (uint8_t)hi_score; SRAM[5] = (uint8_t)(hi_score >> 8);
    SRAM[6] = (uint8_t)(hi_score >> 16); SRAM[7] = (uint8_t)(hi_score >> 24);
    c = checksum();
    SRAM[8] = c; SRAM[9] = ~c;
    DISABLE_RAM;
}
