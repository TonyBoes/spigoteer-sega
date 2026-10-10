// Saved high scores and the story progress: cartridge SRAM, MBC5+RAM+BATTERY.
// M10b: a top-5 table with 3-letter initials; M11b: the story progress next to it; story shifts: the step reached.
// Layout at 0xA000 (version 4):
//   0..3 magic "TPR4", then 5 entries of 6 bytes from 4: 3 initials ('A'..'Z' or ' '), score (3 bytes, little
//   endian, <= 999999), best first; 34 story progress (chapters cleared, 0..9); 35 the furthest step reached in the
//   next chapter (0..STORY_STEPS-1: its steps before it were done at least once; a venue restart never lowers it; 0
//   when the story is complete); 36 checksum (0x5A + bytes 0..35), 37 its complement. CONTINUE on the title: progress
//   1..8, or progress 0 with a step reached; it starts that chapter over (lives are not saved: story.c).
//   A step of chapter k is reached (a later practice mode may offer it) when k < progress, or k == progress and the
//   step <= the step reached. Practice best scores, when they come, go in their own block from 0x40 with its own
//   magic and checksum (no version change here: a bad block then loses only the bests).
// Migration (written back as version 4 at once, save_migrated set):
//   version 3 (M11b: "TPR3", the same bytes, 35 reserved 0): chapters cleared kept, step 0 = the PRE scene of the
//   first chapter not cleared, as before (save_migrated = 3);
//   version 2 (M10b: "TPR2", the same table, 34 checksum = 0x5A + bytes 0..33, 35 complement): the table kept, no
//   story progress (save_migrated = 2);
//   version 1 (M7: "TPR1", 4..7 hi score LE, 8 checksum = 0x5A + bytes 0..7, 9 complement): entry 1 with the
//   initials "SPG" (save_migrated = 1).
// Anything that does not check out loads as an empty table with no story progress.
// The working copy (top_names / top_scores) is in WRAM; hi_score / hi_digits mirror entry 1 for the title.
#pragma bank 255
#include <gb/gb.h>
#include <stdint.h>
#include "music.h"
#include "story.h"

extern uint32_t hi_score;
extern uint8_t  hi_digits[6];

uint8_t  top_names[TOP_N * 3];      // 3 initials per entry, ASCII
uint32_t top_scores[TOP_N];         // best first
uint8_t  save_migrated;             // the boot converted an old save: 1 from version 1, 2 / 3 from version 2 / 3 (tests)
uint8_t  story_progress;            // M11b: story chapters cleared (0..9)
uint8_t  story_reached;             // story shifts: the furthest step reached in chapter story_progress (0..STORY_STEPS-1)

#define SRAM ((volatile uint8_t *)0xA000)
#define HI_MAX 999999UL
#define V2_LEN   (4 + TOP_N * 6)    // 34: bytes covered by the checksum (version 2)
#define V3_STORY V2_LEN             // 34: the story progress (versions 3, 4)
#define V4_STEP  (V2_LEN + 1)       // 35: the step reached (version 4; version 3: reserved 0)
#define V3_LEN   (V2_LEN + 2)       // 36: bytes covered by the checksum (versions 3, 4)
#define STORY_MAX STORY_CHAPTERS
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

// 1: SRAM holds a well-formed version-4 (or, v '3' / '2', version-3 / 2) table (copied into the working copy)
static uint8_t load_table(uint8_t ver) {
    uint8_t i, k;
    volatile uint8_t *e;
    uint32_t v, prev = HI_MAX;
    if (!magic(ver)) return 0;
    if (ver == '4') {
        if (!sum_ok(V3_LEN) || SRAM[V3_STORY] > STORY_MAX || SRAM[V4_STEP] >= STORY_STEPS) return 0;
        if (SRAM[V3_STORY] == STORY_MAX && SRAM[V4_STEP]) return 0;
    } else if (ver == '3') {
        if (!sum_ok(V3_LEN) || SRAM[V3_STORY] > STORY_MAX) return 0;
    } else if (!sum_ok(V2_LEN)) return 0;
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
    story_progress = 0; story_reached = 0;
    if (load_table('4')) { story_progress = SRAM[V3_STORY]; story_reached = SRAM[V4_STEP]; }
    else if (load_table('3')) { story_progress = SRAM[V3_STORY]; save_migrated = 3; }   // (a failed load copies nothing)
    else {
        clear_table();
        if (load_table('2')) save_migrated = 2;
        else {
            clear_table();
            if (load_v1()) save_migrated = 1;
        }
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
    SRAM[0] = 'T'; SRAM[1] = 'P'; SRAM[2] = 'R'; SRAM[3] = '4';
    for (i = 0; i < TOP_N; i++) {
        e = SRAM + 4 + i * 6;
        for (k = 0; k < 3; k++) e[k] = top_names[i * 3 + k];
        v = top_scores[i];
        e[3] = (uint8_t)v; e[4] = (uint8_t)(v >> 8); e[5] = (uint8_t)(v >> 16);
    }
    SRAM[V3_STORY] = story_progress; SRAM[V4_STEP] = story_reached;
    c = checksum(V3_LEN);
    SRAM[V3_LEN] = c; SRAM[V3_LEN + 1] = ~c;
    DISABLE_RAM;
}

// M11b: the story progress (chapters cleared; story shifts: and the step reached in the next one), saved with the table
void story_save(uint8_t chapters, uint8_t step) BANKED {
    story_progress = chapters; story_reached = step;
    hi_save();
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
