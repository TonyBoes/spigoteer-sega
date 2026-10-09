// Saved high scores: cartridge SRAM, MBC5+RAM+BATTERY.
// M10b: a top-5 table with 3-letter initials. Layout at 0xA000 (version 2):
//   0..3 magic "TPR2", then 5 entries of 6 bytes from 4: 3 initials ('A'..'Z' or ' '), score (3 bytes, little
//   endian, <= 999999), best first; 34 checksum (0x5A + bytes 0..33), 35 its complement.
// Migration: a valid version-1 record (M7: "TPR1", 4..7 hi score LE, 8 checksum = 0x5A + bytes 0..7, 9 complement)
// becomes entry 1 with the initials "SPG"; the table is written back as version 2 at once.
// Anything that does not check out loads as an empty table (every score 0, blank initials).
// The working copy (top_names / top_scores) is in WRAM; hi_score / hi_digits mirror entry 1 for the title.
#pragma bank 255
#include <gb/gb.h>
#include <stdint.h>
#include "music.h"

extern uint32_t hi_score;
extern uint8_t  hi_digits[6];

uint8_t  top_names[TOP_N * 3];      // 3 initials per entry, ASCII
uint32_t top_scores[TOP_N];         // best first
uint8_t  save_migrated;             // 1: the boot found a version-1 save and converted it (tests)

#define SRAM ((volatile uint8_t *)0xA000)
#define HI_MAX 999999UL
#define V2_LEN   (4 + TOP_N * 6)    // 34: bytes covered by the checksum
#define V1_LEN   8

static uint8_t checksum(uint8_t n) {
    uint8_t i, s = 0x5A;
    for (i = 0; i < n; i++) s += SRAM[i];
    return s;
}

static uint8_t sum_ok(uint8_t n) {
    uint8_t c = checksum(n);
    return SRAM[n] == c && SRAM[n + 1] == (uint8_t)~c;
}

static uint8_t magic(uint8_t version) {
    return SRAM[0] == 'T' && SRAM[1] == 'P' && SRAM[2] == 'R' && SRAM[3] == version;
}

static uint8_t valid_char(uint8_t c) {
    return c == ' ' || (c >= 'A' && c <= 'Z');
}

// hi_score / hi_digits = entry 1
static void make_hi(void) {
    uint32_t v = top_scores[0];
    uint8_t i;
    hi_score = v;
    for (i = 6; i != 0; i--) { hi_digits[i - 1] = (uint8_t)(v % 10); v /= 10; }
}

static void clear_table(void) {
    uint8_t i;
    for (i = 0; i < TOP_N * 3; i++) top_names[i] = ' ';
    for (i = 0; i < TOP_N; i++) top_scores[i] = 0;
}

// 1: SRAM holds a well-formed version-2 table (copied into the working copy)
static uint8_t load_v2(void) {
    uint8_t i, k;
    volatile uint8_t *e;
    uint32_t v, prev = HI_MAX;
    if (!magic('2') || !sum_ok(V2_LEN)) return 0;
    for (i = 0; i < TOP_N; i++) {
        e = SRAM + 4 + i * 6;
        for (k = 0; k < 3; k++) if (!valid_char(e[k])) return 0;
        v = (uint32_t)e[3] | ((uint32_t)e[4] << 8) | ((uint32_t)e[5] << 16);
        if (v > prev) return 0;             // out of range (the first one) or out of order
        prev = v;
    }
    for (i = 0; i < TOP_N; i++) {
        e = SRAM + 4 + i * 6;
        for (k = 0; k < 3; k++) top_names[i * 3 + k] = e[k];
        top_scores[i] = (uint32_t)e[3] | ((uint32_t)e[4] << 8) | ((uint32_t)e[5] << 16);
    }
    return 1;
}

// 1: SRAM holds a well-formed version-1 hi score (it becomes entry 1, "SPG")
static uint8_t load_v1(void) {
    uint32_t v;
    if (!magic('1') || !sum_ok(V1_LEN)) return 0;
    v = (uint32_t)SRAM[4] | ((uint32_t)SRAM[5] << 8) | ((uint32_t)SRAM[6] << 16) | ((uint32_t)SRAM[7] << 24);
    if (v > HI_MAX) return 0;
    top_names[0] = 'S'; top_names[1] = 'P'; top_names[2] = 'G';
    top_scores[0] = v;
    return 1;
}

void hi_load(void) BANKED {
    ENABLE_RAM;
    SWITCH_RAM(0);
    clear_table();
    save_migrated = 0;
    if (!load_v2()) {
        clear_table();
        if (load_v1()) save_migrated = 1;
    }
    DISABLE_RAM;
    make_hi();
    if (save_migrated) hi_save();
}

void hi_save(void) BANKED {
    uint8_t i, k, c;
    volatile uint8_t *e;
    uint32_t v;
    ENABLE_RAM;
    SWITCH_RAM(0);
    SRAM[0] = 'T'; SRAM[1] = 'P'; SRAM[2] = 'R'; SRAM[3] = '2';
    for (i = 0; i < TOP_N; i++) {
        e = SRAM + 4 + i * 6;
        for (k = 0; k < 3; k++) e[k] = top_names[i * 3 + k];
        v = top_scores[i];
        e[3] = (uint8_t)v; e[4] = (uint8_t)(v >> 8); e[5] = (uint8_t)(v >> 16);
    }
    c = checksum(V2_LEN);
    SRAM[V2_LEN] = c; SRAM[V2_LEN + 1] = ~c;
    DISABLE_RAM;
}

// Where a score would go in the table: 0..TOP_N-1, or TOP_N when it does not make it. A tie goes below the
// older entry; a score of 0 never enters.
uint8_t top_rank(uint32_t s) BANKED {
    uint8_t i;
    if (s == 0) return TOP_N;
    for (i = 0; i < TOP_N; i++) if (s > top_scores[i]) return i;
    return TOP_N;
}

// Insert a score with the initials n[0..2] at its rank (the last entry drops out); returns the rank (TOP_N: not
// inserted). The caller saves.
uint8_t top_insert(uint32_t s, const uint8_t *n) BANKED {
    uint8_t r = top_rank(s), i;
    if (r >= TOP_N) return TOP_N;
    for (i = TOP_N - 1; i > r; i--) {
        top_scores[i] = top_scores[i - 1];
        top_names[i * 3] = top_names[i * 3 - 3]; top_names[i * 3 + 1] = top_names[i * 3 - 2];
        top_names[i * 3 + 2] = top_names[i * 3 - 1];
    }
    top_scores[r] = s;
    top_names[r * 3] = n[0]; top_names[r * 3 + 1] = n[1]; top_names[r * 3 + 2] = n[2];
    make_hi();
    return r;
}
