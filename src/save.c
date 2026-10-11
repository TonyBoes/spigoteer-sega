// Saved high scores, the story progress and the soundtrack unlocks: cartridge SRAM, MBC5+RAM+BATTERY.
// M10b: a top-5 table with 3-letter initials; M11b: the story progress next to it; story shifts: the step reached;
// bonus menu: the soundtrack's unlocked tunes; the 10th venue: version 6 (the chapters and tunes in the new order).
// Layout at 0xA000 (version 6):
//   0..3 magic "TPR6", then 5 entries of 6 bytes from 4: 3 initials ('A'..'Z' or ' '), score (3 bytes, little
//   endian, <= 999999), best first; 34 story progress (chapters cleared, 0..10; the design's "Pour-Off won" would be
//   11); 35 the furthest step reached in the next chapter (0..STORY_STEPS-1: its steps before it were done at least
//   once; a venue restart never lowers it; 0 when the story is complete); 36..37 the unlocked tunes (16-bit little
//   endian, bit t = TUNE_t of music.h; bit 0, the title tune, always set; bit 15, above TUNE_COUNT, is kept as it is);
//   38 checksum (0x5A + bytes 0..37), 39 its complement. CONTINUE on the title: progress 1..9, or progress 0 with a
//   step reached; it starts that chapter over (lives are not saved: story.c).
//   A step of chapter k is reached (a later practice mode may offer it) when k < progress, or k == progress and the
//   step <= the step reached. Practice best scores, when they come, go in their own block from 0x40 with its own
//   magic and checksum (no version change here: a bad block then loses only the bests).
//   The unlocks are never cleared: a new story resets bytes 34/35 (as it always did) but not 36/37.
// Unlock rule (bonus menu, soundtrack player): the title tune always; any tune once it plays in story mode (a venue
// tune when its PRE scene starts, a jingle when first heard: tune_heard, called by music_play); clearing chapter 1
// also unlocks the four jingles (CLEAR, OVER, BONUS, SHOW: BONUS and SHOW may never play in a story). A story run
// started from the debug select (save_lock) writes nothing: neither progress nor unlocks.
// Migration (written back as version 6 at once, save_migrated set). Versions 3-5 counted 9 chapters in the old order
// (... 6 factory, 7 teahouse, 8 space, 9 zoo); the old chapters 7-9 are 8, 10 and 9 in the new order, so no count
// above 6 maps onto it: an old progress p <= 5 is kept with its step, p >= 6 becomes 6 with step 0 (the first chapter
// not cleared is The Chrome Cow; an old step at p = 6 counted the teahouse's steps). A complete old story shows
// CONTINUE again, at The Chrome Cow's PRE scene (old_progress).
//   version 5 (bonus menu: "TPR5", bytes 0..37 as version 6, progress 0..9): the unlocks moved to the new tune order
//   (the old venue tunes 6, 7, 8 = teahouse, space, zoo are 7, 9, 8 now; old bits 14-15 dropped) plus the unlocks
//   the mapped progress implies (save_migrated = 5);
//   version 4 (story shifts: "TPR4", bytes 0..35, 36 checksum = 0x5A + bytes 0..35, 37 complement)
//   (save_migrated = 4);
//   version 3 (M11b: "TPR3", the same bytes, 35 reserved 0): step 0 = the PRE scene of the first chapter not cleared,
//   as before (save_migrated = 3);
//   version 2 (M10b: "TPR2", the same table, 34 checksum = 0x5A + bytes 0..33, 35 complement): the table kept, no
//   story progress (save_migrated = 2);
//   version 1 (M7: "TPR1", 4..7 hi score LE, 8 checksum = 0x5A + bytes 0..7, 9 complement): entry 1 with the
//   initials "SPG" (save_migrated = 1).
//   Unlocks of a version 1-4 save (progress_unlocks): the venues of the chapters cleared, the next chapter's venue when
//   one of its steps was reached, the jingles once chapter 1 is cleared; the title tune.
// Anything that does not check out loads as an empty table with no story progress and only the title tune.
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
uint8_t  save_migrated;             // the boot converted an old save: its version 1..5 (tests)
uint8_t  story_progress;            // M11b: story chapters cleared (0..10)
uint8_t  story_reached;             // story shifts: the furthest step reached in chapter story_progress (0..STORY_STEPS-1)
uint16_t tune_unlocked;             // bonus menu: bit t = tune t unlocked in the soundtrack player (saved, never cleared)
uint8_t  save_lock;                 // 1: a debug-select story run: story_save / tune_heard write nothing (title_enter clears it)

#define SRAM ((volatile uint8_t *)0xA000)
#define HI_MAX 999999UL
#define V2_LEN   (4 + TOP_N * 6)    // 34: bytes covered by the checksum (version 2)
#define V3_STORY V2_LEN             // 34: the story progress (versions 3-6)
#define V4_STEP  (V2_LEN + 1)       // 35: the step reached (version 4; version 3: reserved 0)
#define V3_LEN   (V2_LEN + 2)       // 36: bytes covered by the checksum (versions 3, 4)
#define V5_TUNES V3_LEN             // 36, 37: the unlocked tunes (versions 5, 6)
#define V5_LEN   (V3_LEN + 2)       // 38: bytes covered by the checksum (versions 5, 6)
#define JINGLES  ((1 << TUNE_CLEAR) | (1 << TUNE_OVER) | (1 << TUNE_BONUS) | (1 << TUNE_SHOW))
#define STORY_MAX STORY_CHAPTERS
#define OLD_STORY_MAX 9             // versions 3-5: nine chapters (the order before the 10th venue)
#define OLD_KEPT 6                  // their progress p < 6 means the same chapters today; p >= 6 becomes 6, step 0
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

// The unlocks a story progress implies (an old save's, and every story_save): the title tune; the venues of the
// chapters cleared, and of chapter p when one of its steps was reached; the jingles once chapter 1 is cleared.
static uint16_t progress_unlocks(uint8_t p, uint8_t r) {
    uint16_t m = 1 << TUNE_TITLE;
    uint8_t c, n = r && p < STORY_MAX ? p + 1 : p;
    for (c = 0; c < n; c++) m |= (uint16_t)1 << (TUNE_VENUE0 + c);
    if (p) m |= JINGLES;
    return m;
}

// 1: SRAM holds a well-formed version-6 (or, v '5' / '4' / '3' / '2', version-5 / 4 / 3 / 2) table (copied into the
// working copy). Versions 3-5 counted nine chapters.
static uint8_t load_table(uint8_t ver) {
    uint8_t i, k, max = ver == '6' ? STORY_MAX : OLD_STORY_MAX;
    volatile uint8_t *e;
    uint32_t v, prev = HI_MAX;
    if (!magic(ver)) return 0;
    if (ver >= '4') {
        if (!sum_ok(ver >= '5' ? V5_LEN : V3_LEN) || SRAM[V3_STORY] > max || SRAM[V4_STEP] >= STORY_STEPS) return 0;
        if (SRAM[V3_STORY] == max && SRAM[V4_STEP]) return 0;
    } else if (ver == '3') {
        if (!sum_ok(V3_LEN) || SRAM[V3_STORY] > max) return 0;
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

// A version 3-5 save's progress (nine chapters, the old order) in today's chapters: see the top of the file.
static void old_progress(uint8_t p, uint8_t r) {
    if (p >= OLD_KEPT) { p = OLD_KEPT; r = 0; }
    story_progress = p; story_reached = r;
}

// A version-5 save's unlocks (the old tune order: venues cowboys .. robots, ninjas, aliens, zoo) in today's order.
#define OLD_BIT(g) ((uint16_t)1 << (TUNE_VENUE0 + (g)))
static uint16_t old_tunes(uint16_t m) {
    uint16_t t = m & (OLD_BIT(6) - 1);           // the title, the jingles, the show and venues 0-5 keep their bits
    if (m & OLD_BIT(6)) t |= OLD_BIT(7);         // the teahouse's Sakura Sakura: venue 6 -> 7
    if (m & OLD_BIT(7)) t |= OLD_BIT(9);         // the space lounge's Blue Danube: 7 -> 9
    if (m & OLD_BIT(8)) t |= OLD_BIT(8);         // the zoo's Pop Goes the Weasel: 8 -> 8
    return t;
}

void hi_load(void) BANKED {
    uint16_t old = 0;
    ENABLE_RAM;
    SWITCH_RAM(0);
    clear_table();
    save_migrated = 0;
    tune_unlocked = 0;
    story_progress = 0; story_reached = 0;
    if (load_table('6')) {
        story_progress = SRAM[V3_STORY]; story_reached = SRAM[V4_STEP];
        tune_unlocked = SRAM[V5_TUNES] | ((uint16_t)SRAM[V5_TUNES + 1] << 8);
    } else if (load_table('5')) {
        old_progress(SRAM[V3_STORY], SRAM[V4_STEP]); save_migrated = 5;
        old = old_tunes(SRAM[V5_TUNES] | ((uint16_t)SRAM[V5_TUNES + 1] << 8));
    } else if (load_table('4')) { old_progress(SRAM[V3_STORY], SRAM[V4_STEP]); save_migrated = 4; }
    else if (load_table('3')) { old_progress(SRAM[V3_STORY], 0); save_migrated = 3; }   // (a failed load copies nothing)
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
    if (save_migrated) tune_unlocked = old | progress_unlocks(story_progress, story_reached);
    tune_unlocked |= 1 << TUNE_TITLE;
    if (save_migrated) hi_save();
}

void hi_save(void) BANKED {
    uint8_t i, k, c;
    volatile uint8_t *e;
    uint32_t v;
    ENABLE_RAM;
    SWITCH_RAM(0);
    SRAM[0] = 'T'; SRAM[1] = 'P'; SRAM[2] = 'R'; SRAM[3] = '6';
    for (i = 0; i < TOP_N; i++) {
        e = SRAM + 4 + i * 6;
        for (k = 0; k < 3; k++) e[k] = top_names[i * 3 + k];
        v = top_scores[i];
        e[3] = (uint8_t)v; e[4] = (uint8_t)(v >> 8); e[5] = (uint8_t)(v >> 16);
    }
    SRAM[V3_STORY] = story_progress; SRAM[V4_STEP] = story_reached;
    SRAM[V5_TUNES] = (uint8_t)tune_unlocked; SRAM[V5_TUNES + 1] = (uint8_t)(tune_unlocked >> 8);
    c = checksum(V5_LEN);
    SRAM[V5_LEN] = c; SRAM[V5_LEN + 1] = ~c;
    DISABLE_RAM;
}

// M11b: the story progress (chapters cleared; story shifts: and the step reached in the next one), saved with the table,
// and the unlocks it implies. Nothing in a debug-select run (save_lock): the real progress stays as it was.
void story_save(uint8_t chapters, uint8_t step) BANKED {
    if (save_lock) return;
    story_progress = chapters; story_reached = step;
    tune_unlocked |= progress_unlocks(chapters, step);
    hi_save();
}

// music_play, in story mode: tune t was heard. A new unlock is saved at once (once per tune, ever).
void tune_heard(uint8_t t) BANKED {
    uint16_t m;
    if (save_lock || t >= TUNE_COUNT) return;
    m = (uint16_t)1 << t;
    if (tune_unlocked & m) return;
    tune_unlocked |= m;
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
