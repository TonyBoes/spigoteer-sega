// Saved high scores, the story progress and the soundtrack unlocks: cartridge SRAM, MBC5+RAM+BATTERY.
// M10b: a top-5 table with 3-letter initials; M11b: the story progress; story shifts: the step reached; bonus menu: the
// soundtrack's unlocked tunes; the 10th venue: version 6; the three modes: version 7, one top 5 per mode, each in its
// own block, so a bad block empties only that table (owner 2026-10-11).
// Layout at 0xA000 (version 7):
//   0x00 the main block: 0..3 magic "TPR7"; 4 story progress (chapters cleared, 0..10; bits 6-7: the STORY's difficulty, 0 NORMAL, 1 HARD, 2 EASY,
//   set when the story is first saved, kept by every other save; an older save has them clear: NORMAL); 5 the furthest step reached in
//   the next chapter (0..STORY_STEPS-1: its steps before it were done at least once; a venue restart never lowers it;
//   0 when the story is complete); 6..7 the unlocked tunes (16-bit little endian, bit t = TUNE_t of music.h; bit 0, the
//   title tune, always set; bit 15, above TUNE_COUNT, is kept as it is); 8 checksum (0x5A + bytes 0..7), 9 its
//   complement. CONTINUE on the title: progress 1..9, or progress 0 with a step reached; it starts that chapter over
//   (lives are not saved: story.c).
//   0x12 the BAR CHANGE setting "BC" (SETTINGS; 2026-10-16): 0..1 magic, 2 the mode (1 KEEP, else SNAP), 3 checksum (0x5A + bytes 0..2), 4 its
//   complement; no block, a bad checksum or any other mode reads as SNAP.
//   0x18 the DEBUG MENU unlock "DU" (2026-10-16; SETTINGS > DEBUG MENU and the open gesture: src/debug.c): 0..1 magic, 2 the flag (1 unlocked, else
//   locked), 3 checksum (0x5A + bytes 0..2), 4 its complement; no block, a bad checksum or any other flag reads as LOCKED. ERASE DATA (save_erase)
//   zeroes the whole 8 KB, so it locks the menu again with everything else.
//   0x1E the story map "SM" (2026-10-18: src/smap.c): 0..1 magic, 2 the stop Sal stands at (0..10: a venue = its chapter, 10 the town), 3 the flags (bits 0-2:
//   festival game k played since it unlocked, so its "!" is gone; bits 4-6: it won GOLD in the current story run, each a life for the Pour-Off; the other bits must be
//   0), 4 the checksum (0x5A + bytes 0..3), 5 its complement; no block or a bad one reads as no stop and no flags (CONTINUE puts Sal at the next venue).
//   A new story starts the flags again. Written when the map is left and when a gold is counted; nothing in a debug-select run or ARCADE (save_lock).
//   0x28 the boss cards seen "BK" (2026-10-17: the first time a boss appears the game opens his HOW TO PLAY card, src/boss.c): 0..1 magic, 2..3 the
//   venues whose boss card was shown (bit v, little endian; only bits below BOSS_COUNT), 4 the checksum (0x5A + bytes 0..3), 5 its complement; no
//   block, a bad checksum or a bit at or above BOSS_COUNT reads as no card seen (every card shows once more). Nothing is written in a debug-select run.
//   0x30 the SCREEN setting "SC" (2026-10-21; SETTINGS > SCREEN NORMAL / BRIGHT, Color only: src/title.c, src/main_cold.c screen_load): 0..1 magic, 2 the choice
//   (1 NORMAL, 2 BRIGHT), 3 checksum (0x5A + bytes 0..2), 4 its complement. No block, a bad checksum or any other value reads as NOT CHOSEN: the boot then
//   is NORMAL, and a Game Boy Advance asks once at the title (title.c TM_SCR; the pick is written here, and so is every later change in SETTINGS: a choice is never
//   overwritten by a default). A DMG never reads or writes it. ERASE DATA clears it with the rest (a GBA asks again). Older saves have no block: they read as not chosen.
//   0x0A the venue-start score "SV" (owner 2026-10-14: CONTINUE returns to the venue's start with 3 lives and the score the player
//   had when they entered it): 0..1 magic "SV"; 2 the chapter it belongs to; 3..5 the score (LE, <= 999999); 6 checksum (0x5A +
//   bytes 0..5), 7 its complement. Written when a venue is entered (a PRE scene's end, a chapter cleared: story.c) and read by
//   CONTINUE, which takes it only when its chapter is the one to continue; anything else (an older save without the block, a bad
//   checksum, another chapter, a score above 999999) reads as score 0. Not in a debug-select run or ARCADE (save_lock).
//   0x40 Practice (BONUS > MINI GAMES and BOSS RUSH): 0..3 magic "MGP2"; 4..5 the mini-games reached (16-bit little
//   endian, bit g = mini-game g, MG_* of src/mg.h; only bits below MG_PLANNED are ever set); 6..6+MG_PLANNED-1 the best
//   medal of each (a byte: MEDAL_* in bits 0-1 for NORMAL, 2-3 for HARD, 4-5 for EASY, owner 2026-10-15: Practice's difficulties; a byte above 63
//   is bad; an older save has bits 4-5 clear: no EASY medals, and its medals read as NORMAL); 16..43 the boss rush's part (RUSH_SAVE_N bytes, src/rush.h RSV_*): 16..17 the bosses
//   beaten in STORY or ARCADE (LE, bit v = venue v's boss; only bits below BOSS_COUNT), 18..37 each boss's fastest rush
//   win in frames (LE, 0 none), 38..40 ALL's best score (LE, <= 999999), 41..42 that run's frames, 43 its bosses beaten
//   (<= BOSS_COUNT); 44 the checksum (0x5A + bytes 0..43), 45 its complement. A block that does not check out (magic,
//   checksum, a medal above GOLD, a bit at or above MG_PLANNED or BOSS_COUNT, a score or count out of range) loads as
//   nothing reached, no medals and an empty rush part; the other blocks are unaffected, and it is only written when it
//   changes (mg_record, boss_beaten, rush_store), so a bad one stays until then. Version 1 ("MGP1": bytes 0..15 as
//   now, 16 its checksum over 0..15, 17 the complement; 2026-10-11 to 12) is migrated at boot: its mini-games kept,
//   the rush part empty, written back as "MGP2" at once.
//   A mini-game is reached when STORY or ARCADE starts it (mg_enter in MG_STORY mode); its best medal is any mode's
//   (Practice too). A debug-select run (save_lock == SAVE_LOCK_DEBUG) records nothing; ARCADE's save_lock (1) does not
//   stop it (the owner's rule: reached in STORY or ARCADE).
//   0x70 the bonus rounds' block "MGB1" (BONUS > MINI GAMES lists the shake-up, Perfect Pour and Tip Shower; the HOW TO PLAY cards; 2026-10-14):
//   0..3 magic; 4 the rounds played in ARCADE or CLASSIC (bit k, k = 0 shake-up, 1 Perfect Pour, 2 Tip Shower: the Practice unlock);
//   5 their best medals (2 bits each, k * 2); 6..7 the cards seen (16-bit little endian, bit = the mini-game's id, ids from 15 up (the
//   stub, 16) share bit 15); 8 the checksum (0x5A + bytes 0..7), 9 its complement. It sits in the gap after the Practice block
//   (0x40..0x6D) and before the tables (0x80), so MGP2 is untouched; a block that does not check out (magic, checksum, a bit above
//   the three rounds, a medal field above 3 -- impossible in two bits, the byte's top two bits must be 0) reads as nothing played,
//   no medals and no card seen, and is rewritten on the next change. Nothing is written in a debug-select run.
//   0x7A the bonus rounds' EASY / HARD medals "MD" (6 bytes, the last gap before the tables): 0..1 magic, 2 the EASY medals, 3 the HARD medals
//   (2 bits a round as MGB1's byte 5, round k at k * 2; the top two bits must be 0), 4 the checksum (0x5A + bytes 0..3), 5 its complement. NORMAL
//   medals stay in MGB1. A block that does not check out (an older save has none) reads as no EASY or HARD medals; MGB1 and the rest are unaffected.
//   0x80 ARCADE, 0xC0 STORY, 0x100 CLASSIC: a top 5 each (TBL_AT(t), t = MODE_*): 0..3 magic "HSA1" / "HSS1" / "HSC2" (P5: CLASSIC's
//   (STORY's table marks a score made in HARD with bit 7 of the first initial and in EASY with bit 7 of the second)
//   "HSC1" held the stand-in's scores and now loads as an empty table),
//   5 entries of 6 bytes from 4: 3 initials ('A'..'Z' or ' '), score (3 bytes, little endian, <= 999999), best first;
//   34 checksum (0x5A + bytes 0..33), 35 its complement. A block that does not check out (magic, checksum, letters,
//   range, order) loads as an empty table; the others and the main block are unaffected. ARCADE: the ARCADE game overs
//   (and the LEVEL harness's); STORY: the story's score when its credits end; CLASSIC: CLASSIC's game overs.
//   A step of chapter k is reached (a later practice mode may offer it) when k < progress, or k == progress and the
//   step <= the step reached. The unlocks are never cleared: a new story resets bytes 4/5 (as it always did), not 6/7.
// Unlock rule (bonus menu, soundtrack player): the title tune always; any tune once it plays in story mode (a venue
// tune when its PRE scene starts, a jingle when first heard: tune_heard, called by music_play); clearing chapter 1
// also unlocks the four jingles (CLEAR, OVER, BONUS, SHOW: BONUS and SHOW may never play in a story). A story run
// started from the debug select, and every ARCADE run (save_lock), writes neither progress nor unlocks.
// Migration (written back as version 7 at once, save_migrated = the old version). Every older version's top 5 is
// dropped (owner 2026-10-11, Q4: the old arcade was a different game; the tables start fresh); the story progress and
// the unlocks are kept:
//   version 6 ("TPR6": 4..33 the old table, 34 progress 0..10, 35 the step, 36..37 the tunes, 38 checksum = 0x5A +
//   bytes 0..37, 39 complement): progress, step and tunes as they were (save_migrated = 6).
//   Versions 3-5 counted 9 chapters in the old order (... 6 factory, 7 teahouse, 8 space, 9 zoo); the old chapters 7-9
//   are 8, 10 and 9 in the new order, so no count above 6 maps onto it: an old progress p <= 5 is kept with its step,
//   p >= 6 becomes 6 with step 0 (the first chapter not cleared is The Chrome Cow; an old step at p = 6 counted the
//   teahouse's steps). A complete old story shows CONTINUE again, at The Chrome Cow's PRE scene (old_progress).
//   version 5 ("TPR5", bytes 0..37 as version 6, progress 0..9): the unlocks moved to the new tune order (the old venue
//   tunes 6, 7, 8 = teahouse, space, zoo are 7, 9, 8 now; old bits 14-15 dropped) plus the unlocks the mapped progress
//   implies; version 4 ("TPR4", bytes 0..35, 36 checksum = 0x5A + bytes 0..35, 37 complement); version 3 ("TPR3", the
//   same bytes, 35 reserved 0): step 0 = the PRE scene of the first chapter not cleared, as before.
//   Unlocks of a version 3-4 save (progress_unlocks): the venues of the chapters cleared, the next chapter's venue when
//   one of its steps was reached, the jingles once chapter 1 is cleared; the title tune.
//   Versions 1 and 2 held nothing but a hi score table: they load as a fresh cartridge.
//   The story's order changed on 2026-11-07 (the bistro and the igloo before the lumber lodge: chapters 3, 4, 5 = bistro, igloo, lodge, venue ids unchanged): a version 7 save
//   without the stamp (byte 5 bit 7, set by every save from now on) counts its progress in the old order. Old 0, 1 and 5..10 chapters cleared are the same set of venues as now; old 3 (saloon,
//   stadium, lodge) is 2 now, keeping its step (the next chapter is the bistro either way); old 4 (+ the bistro) is 3, keeping its step (the igloo is next either way); old 2
//   (the next chapter was the lodge) is 2 with step 0. Tunes (by venue) and the tables are untouched; the story map's flags and the venue-start score are read as
//   they are (a stop or score of another chapter reads as none). save_migrated = 7, written back stamped at once.
// Anything that does not check out loads as no story progress and only the title tune.
// The working copy (top_names / top_scores, table t from entry t * TOP_N) is in WRAM; hi_score / hi_digits mirror
// entry 1 of the table hi_pick chose (the title's HI line).
#pragma bank 255
#include <gb/gb.h>
#include <stdint.h>
#include "game.h"
#include "music.h"
#include "story.h"
#include "mg.h"
#include "order.h"

extern uint32_t hi_score;
extern uint8_t  hi_digits[6];

uint8_t  top_names[TOP_TABLES * TOP_N * 3];      // 3 initials per entry, ASCII
uint32_t top_scores[TOP_TABLES * TOP_N];         // best first
uint8_t  score_tbl;                 // the table top_rank / top_insert / the table screen work on (MODE_*)
uint8_t  save_migrated;             // the boot converted an old save: its version 3..6 (tests); bit 7: a tune unlock is not saved yet
                                    // (TUNE_DIRTY, music.h: tune_heard sets it, hi_save clears it, TUNE_FLUSH saves: no new global in a full WRAM)
uint8_t  story_progress;            // M11b: story chapters cleared (0..10)
uint8_t  story_reached;             // story shifts: the furthest step reached in chapter story_progress (0..STORY_STEPS-1)
uint16_t tune_unlocked;             // bonus menu: bit t = tune t unlocked in the soundtrack player (saved, never cleared)
uint8_t  save_lock;                 // 1: a debug-select story run or ARCADE: story_save / tune_heard write nothing

#define SRAM ((volatile uint8_t *)0xA000)
#define HI_MAX 999999UL
#define V7_STORY 4                  // the main block: progress, step, tunes (2), checksum, complement
#define V7_STEP  5
#define PROG_MASK 0x1F              // byte 4's bits 0-4 the progress (0..10); bit 5 FIN_BIT: the story was finished once (credits reached; set by the finale, never cleared,
                                    // not even by a new story: an older save has it clear, its progress never reached 32); bits 6-7 the story's difficulty (DIFF_*; 3 reads as NORMAL)
#define FIN_BIT   0x20
#define TUNE_FIN  2                 // in memory the finished-once fact is bit 1 of tune_unlocked (the old jingle bit; save_all moves it to FIN_BIT and writes it cleared)
#define V7_TUNES 6
#define SV_AT    0x0A               // the venue-start score block (see the top): magic, chapter, score x3, checksum, complement
#define SV_LEN   6
#define BC_AT    0x12               // the BAR CHANGE setting "BC" (SETTINGS, 2026-10-16): 0..1 magic, 2 the mode (0 SNAP, 1 KEEP), 3 checksum, 4 complement
#define BC_LEN   3
#define DU_AT    0x18               // the DEBUG MENU unlock "DU" (see the top): 0..1 magic, 2 the flag, 3 checksum, 4 complement
#define DU_LEN   3
#define V7_LEN   8                 // bytes covered by the main block's checksum
#define STEP_STAMP 0x80             // byte 5 bit 7: the save was made with the story's order of 2026-11-07 (saloon, stadium, bistro, igloo, lodge ...); a save without it is of the old order (hi_load)
#define STEP_SAVED (STORY_STEPS + 1)  // a saved step below this reads (before the boss joined Last call, 2026-10-17, a venue had a fifth step: 4); it is clamped to the last
#define STEP_CLAMP(r) ((r) >= STORY_STEPS ? STORY_STEPS - 1 : (r))
#define BK_AT    0x28               // the boss cards seen "BK": 0..1 magic, 2..3 bit v = venue v's boss card was shown (LE; bits below BOSS_COUNT), 4 checksum, 5 complement
#define BK_LEN   4
#define SC_AT    0x30               // the SCREEN setting "SC": 0..1 magic, 2 the choice (1 NORMAL, 2 BRIGHT), 3 checksum, 4 complement
#define SC_LEN   3
#if BK_AT + BK_LEN + 2 > SC_AT || SC_AT + SC_LEN + 2 > 0x40
#error "the SCREEN block overlaps its neighbours"
#endif
#define SM_AT    0x1E               // the story map "SM": 0..1 magic, 2 the stop, 3 the flags, 4 checksum, 5 complement
#define SM_LEN   4
#if SM_AT + SM_LEN + 2 > BK_AT || DU_AT + DU_LEN + 2 > SM_AT
#error "the map block overlaps its neighbours"
#endif
#define TBL_AT(t) (0x80 + (uint16_t)(t) * 0x40)
#define TBL_LEN  (4 + TOP_N * 6)    // 34: bytes of a table block covered by its checksum
#define V3_STORY 34                 // versions 3-6: the story progress
#define V4_STEP  35                 // the step reached (version 4 on; version 3: reserved 0)
#define V3_LEN   36                 // bytes covered by the checksum (versions 3, 4)
#define V5_TUNES 36                 // 36, 37: the unlocked tunes (versions 5, 6)
#define V5_LEN   38                 // bytes covered by the checksum (versions 5, 6)
#define JINGLES  (1 << TUNE_SHOW)    // (Level Clear, Game Over and Bonus Round left the stored bits: tune_open derives them from the story's end)
#define TUNE_STORED 0xFFF1           // the bits tune_unlocked keeps: the title (0), the show tune (4), the venues (5-14), the map (15); bits 1-3 were the jingles'
                                    // (a version 7 save's are dropped on load: they unlock nothing now), 16 and up have no bit
#define STORY_MAX STORY_CHAPTERS
#define OLD_STORY_MAX 9             // versions 3-5: nine chapters (the order before the 10th venue)
#define OLD_KEPT 6                  // their progress p < 6 means the same chapters today; p >= 6 becomes 6, step 0

static const uint8_t tbl_letter[TOP_TABLES] = { 'A', 'S', 'C' };   // the table blocks' magic "HS??" (MODE_* order)
// ... and its version: CLASSIC's is 2 since P5 (its version-1 block held the stand-in's scores: a mismatch loads empty)
static const uint8_t tbl_ver[TOP_TABLES] = { '1', '1', '2' };

uint16_t mg_unlocked;               // Practice: bit g = mini-game g reached in STORY or ARCADE
uint8_t  mg_best[MG_PLANNED];       // Practice: the best medal per mini-game
#define PR_AT    0x40
#define PR_MEDAL 6
#define PR1_LEN  (PR_MEDAL + MG_PLANNED)   // bytes covered by an "MGP1" block's checksum (the mini-games' part)
#define PR_RUSH  PR1_LEN                   // the boss rush's part (src/rush.h RSV_*)
#define PR_LEN   (PR_RUSH + RUSH_SAVE_N)   // bytes covered by the Practice block's checksum ("MGP2")
#define RSV_BITS      0                    // (src/rush.h: the rush part's layout)
#define RSV_ALL_SCORE (2 + 2 * BOSS_COUNT)
#define RSV_ALL_N     (RSV_ALL_SCORE + 5)
#if RSV_ALL_N + 1 != RUSH_SAVE_N || PR_AT + PR_LEN + 2 > 0x80
#error "the Practice block: the rush part's layout (src/rush.h) or its room before the tables at 0x80"
#endif

#define BX_AT    0x70               // the bonus rounds' block "MGB1" (4 bytes of data after the magic: reached, medals, seen x2)
#define BX_LEN   8
#define DX_AT    (BX_AT + BX_LEN + 2) // the bonus rounds' EASY and HARD medals "MD": 0..1 magic, 2 the EASY medals, 3 the HARD medals (2 bits a round, as MGB1's byte 5), 4 checksum, 5 complement
#define DX_LEN   4
#if PR_AT + PR_LEN + 2 > BX_AT || DX_AT + DX_LEN + 2 > 0x80
#error "the bonus blocks do not fit between the Practice block and the tables"
#endif

static uint8_t checksum(volatile uint8_t *b, uint8_t n) {
    uint8_t i, s = 0x5A;
    for (i = 0; i < n; i++) s += b[i];
    return s;
}

static uint8_t sum_ok(volatile uint8_t *b, uint8_t n) {
    uint8_t c = checksum(b, n);
    return b[n] == c && b[n + 1] == (uint8_t)~c;
}

static void sum_put(volatile uint8_t *b, uint8_t n) {
    uint8_t c = checksum(b, n);
    b[n] = c; b[n + 1] = ~c;
}

static uint8_t magic(uint8_t version) {
    return SRAM[0] == 'T' && SRAM[1] == 'P' && SRAM[2] == 'R' && SRAM[3] == version;
}

static uint8_t valid_char(uint8_t c) {         // (bit 7 of the first two initials is the STORY table's E / H mark, see the top)
    c &= 0x7F;
    return c == ' ' || (c >= 'A' && c <= 'Z');
}

// d[0..5] = the six low decimal digits of v (values 0-9), by subtracting powers of ten. The % 10 and / 10 loop it
// replaces called SDCC's 32-bit division twelve times, about one frame of CPU per score: the top-5 table took ~9
// frames with the LCD off and the title tune stalled across the attract switch (music ticks once per main loop).
static const uint32_t pow10[6] = { 100000UL, 10000UL, 1000UL, 100UL, 10UL, 1UL };
void split6(uint8_t *d, uint32_t v) BANKED {
    uint8_t i, n;
    while (v > HI_MAX) v -= HI_MAX + 1;
    for (i = 0; i < 6; i++) {
        for (n = 0; v >= pow10[i]; n++) v -= pow10[i];
        d[i] = n;
    }
}

// hi_score / hi_digits = table t's entry 1
void hi_pick(uint8_t t) BANKED {
    uint32_t v = top_scores[t * TOP_N];
    uint8_t i;
    hi_score = v;
    // (still the 32-bit division: split6 here would be ~1 frame faster when the PLAY cursor changes the HI line, and
    // that lag frame is in the debug_story golden's timing; left as it is)
    for (i = 6; i != 0; i--) { hi_digits[i - 1] = (uint8_t)(v % 10); v /= 10; music_pump(); }   // (each 32-bit division takes a fifth of a frame: the tune ticks between them)
}

// The unlocks a story progress implies (an old save's, and every story_save): the title tune; the venues of the
// chapters cleared, and of chapter p when one of its steps was reached; the jingles once chapter 1 is cleared.
static uint16_t progress_unlocks(uint8_t p, uint8_t r) {
    uint16_t m = 1 << TUNE_TITLE;
    uint8_t c, n = r && p < STORY_MAX ? p + 1 : p;
    for (c = 0; c < n; c++) m |= (uint16_t)1 << (TUNE_VENUE0 + VEN(c));
    if (p) m |= JINGLES;
    return m;
}

// Table t's block, if it checks out, into its (empty) working copy
static void load_tbl(uint8_t t) {
    volatile uint8_t *b = SRAM + TBL_AT(t), *e;
    uint8_t i, k, *nm = top_names + t * (TOP_N * 3);
    uint32_t v, prev = HI_MAX, *sc = top_scores + t * TOP_N;
    if (b[0] != 'H' || b[1] != 'S' || b[2] != tbl_letter[t] || b[3] != tbl_ver[t] || !sum_ok(b, TBL_LEN)) return;
    for (i = 0, e = b + 4; i < TOP_N; i++, e += 6) {
        for (k = 0; k < 3; k++) if (!valid_char(e[k])) return;
        v = (uint32_t)e[3] | ((uint32_t)e[4] << 8) | ((uint32_t)e[5] << 16);
        if (v > prev) return;               // out of range (the first one) or out of order
        prev = v;
    }
    for (i = 0, e = b + 4; i < TOP_N; i++, e += 6) {
        for (k = 0; k < 3; k++) nm[i * 3 + k] = e[k];
        sc[i] = (uint32_t)e[3] | ((uint32_t)e[4] << 8) | ((uint32_t)e[5] << 16);
    }
}

// 1: SRAM holds a well-formed version 3-6 main block (its table is not looked at: it is dropped). Versions 3-5
// counted nine chapters.
static uint8_t old_ok(uint8_t ver) {
    uint8_t max = ver == '6' ? STORY_MAX : OLD_STORY_MAX;
    if (!magic(ver)) return 0;
    if (ver >= '4') {
        if (!sum_ok(SRAM, ver >= '5' ? V5_LEN : V3_LEN) || SRAM[V3_STORY] > max || SRAM[V4_STEP] >= STEP_SAVED) return 0;
        if (SRAM[V3_STORY] == max && SRAM[V4_STEP]) return 0;
    } else if (!sum_ok(SRAM, V3_LEN) || SRAM[V3_STORY] > max) return 0;
    return 1;
}

// A version 3-5 save's progress (nine chapters, the old order) in today's chapters: see the top of the file.
static void old_progress(uint8_t p, uint8_t r) {
    if (p >= OLD_KEPT) { p = OLD_KEPT; r = 0; }
    story_progress = p; story_reached = STEP_CLAMP(r);
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

// Practice's block (RAM enabled): its version ('1' or '2') if it checks out, else 0
static uint8_t pr_version(void) {
    volatile uint8_t *b = SRAM + PR_AT, *r = b + PR_RUSH;
    uint8_t g, v;
    if (b[0] != 'M' || b[1] != 'G' || b[2] != 'P') return 0;
    v = b[3];
    if (v == '1') { if (!sum_ok(b, PR1_LEN)) return 0; }
    else if (v != '2' || !sum_ok(b, PR_LEN)) return 0;
    if ((b[4] | ((uint16_t)b[5] << 8)) >> MG_PLANNED) return 0;
    for (g = 0; g < MG_PLANNED; g++) if (b[PR_MEDAL + g] > 63) return 0;   // (bits 0-1 NORMAL, 2-3 HARD, 4-5 EASY)
    if (v == '1') return v;
    if ((r[RSV_BITS] | ((uint16_t)r[RSV_BITS + 1] << 8)) >> BOSS_COUNT || r[RSV_ALL_N] > BOSS_COUNT
        || (r[RSV_ALL_SCORE] | ((uint32_t)r[RSV_ALL_SCORE + 1] << 8) | ((uint32_t)r[RSV_ALL_SCORE + 2] << 16)) > HI_MAX)
        return 0;
    return v;
}

// The block written (RAM enabled): "MGP2", the mini-games' part from WRAM, the rush part from src (0: as it is in a
// good "MGP2" block, else empty), the checksum.
static void pr_write(const uint8_t *src) {
    volatile uint8_t *b = SRAM + PR_AT;
    uint8_t g, keep = pr_version() == '2';
    for (g = 0; g < RUSH_SAVE_N; g++) b[PR_RUSH + g] = src ? src[g] : keep ? b[PR_RUSH + g] : 0;
    b[0] = 'M'; b[1] = 'G'; b[2] = 'P'; b[3] = '2';
    b[4] = (uint8_t)mg_unlocked; b[5] = (uint8_t)(mg_unlocked >> 8);
    for (g = 0; g < MG_PLANNED; g++) b[PR_MEDAL + g] = mg_best[g];
    sum_put(b, PR_LEN);
}

// Practice's block, if it checks out, into mg_unlocked / mg_best (RAM enabled; they start empty); an "MGP1" block is
// written back as "MGP2" with an empty rush part (its mini-games kept)
static void load_pr(void) {
    volatile uint8_t *b = SRAM + PR_AT;
    uint8_t g, v = pr_version();
    if (!v) return;
    mg_unlocked = b[4] | ((uint16_t)b[5] << 8);
    for (g = 0; g < MG_PLANNED; g++) mg_best[g] = b[PR_MEDAL + g];
    if (v == '1') pr_write(0);
}

// Mini-game g was reached (medal 0) or played to `medal`: the unlock bit, the best medal; the block is written only
// when one of them changes (the rush part kept). Nothing in a debug-select run, nothing for the stub (g >= MG_PLANNED).
void mg_record(uint8_t g, uint8_t medal) BANKED {
    uint16_t m = (uint16_t)1 << g;
    uint8_t sh = MG_DIFF * 2;                    // a medal per difficulty (bits 0-1 NORMAL, 2-3 HARD, 4-5 EASY of the game's byte)
    if (g >= MG_SHAKEUP) { bonus_record(g - MG_SHAKEUP, medal); return; }   // (the old bonus rounds: their own block; ids 12..14, else ignored there)
    if (save_lock == SAVE_LOCK_DEBUG || g >= MG_PLANNED || EASY_RUN) return;   // (an EASY story: no reach, no medal)
    if (medal ? medal <= ((mg_best[g] >> sh) & 3) : (mg_unlocked & m) != 0) return;
    if (medal) mg_best[g] = (mg_best[g] & ~(3 << sh)) | (medal << sh); else mg_unlocked |= m;
    ENABLE_RAM;
    SWITCH_RAM(0);
    pr_write(0);
    DISABLE_RAM;
}

// The bonus block (RAM enabled): its 4 data bytes into d (zeros when it does not check out)
static void bx_get(uint8_t *d) {
    volatile uint8_t *b = SRAM + BX_AT;
    uint8_t i, ok = b[0] == 'M' && b[1] == 'G' && b[2] == 'B' && b[3] == '1' && sum_ok(b, BX_LEN) && !(b[4] >> MG_BONUS_N) && !(b[5] >> 6);
    for (i = 0; i < 4; i++) d[i] = ok ? b[4 + i] : 0;
}

static void bx_put(const uint8_t *d) {
    volatile uint8_t *b = SRAM + BX_AT;
    uint8_t i;
    b[0] = 'M'; b[1] = 'G'; b[2] = 'B'; b[3] = '1';
    for (i = 0; i < 4; i++) b[4 + i] = d[i];
    sum_put(b, BX_LEN);
}

// The EASY and HARD medals block (RAM enabled): d[0] the EASY medals, d[1] the HARD ones (zeros when it does not check out: an older save)
static void dx_get(uint8_t *d) {
    volatile uint8_t *b = SRAM + DX_AT;
    uint8_t i, ok = b[0] == 'M' && b[1] == 'D' && sum_ok(b, DX_LEN) && !(b[2] >> 6) && !(b[3] >> 6);
    for (i = 0; i < 2; i++) d[i] = ok ? b[2 + i] : 0;
}

static void dx_put(const uint8_t *d) {
    volatile uint8_t *b = SRAM + DX_AT;
    b[0] = 'M'; b[1] = 'D'; b[2] = d[0]; b[3] = d[1];
    sum_put(b, DX_LEN);
}

// Bonus round k's best medal (MEDAL_*) in difficulty `diff` (mg.h MG_D_*)
uint8_t bonus_best(uint8_t k, uint8_t diff) BANKED {
    uint8_t d[2], m, i;
    if (diff == MG_D_NORMAL) return (bonus_info(k) >> 1) & 3;
    ENABLE_RAM;
    SWITCH_RAM(0);
    dx_get(d);
    DISABLE_RAM;
    m = d[diff == MG_D_EASY ? 0 : 1];
    for (i = 0; i < k; i++) m >>= 2;
    return m & 3;
}

// Bonus round k: bit 0 played in ARCADE / CLASSIC, bits 1-2 its best medal
uint8_t bonus_info(uint8_t k) BANKED {
    uint8_t d[4], m, p, i;
    ENABLE_RAM;
    SWITCH_RAM(0);
    bx_get(d);
    DISABLE_RAM;
    m = d[1]; p = d[0];
    for (i = 0; i < k; i++) { m >>= 2; p >>= 1; }   // (the medals: 2 bits a round, the played bits 1)
    return (p & 1) | ((m & 3) << 1);
}

// Round k was played (medal 0: ARCADE / CLASSIC reached it) or earned `medal` (a better one is kept): written only when something changes
void bonus_record(uint8_t k, uint8_t medal) BANKED {
    uint8_t d[4], mask = 3, m = medal, old, was = 1, i, x = medal ? MG_DIFF : MG_D_NORMAL;
    if (save_lock == SAVE_LOCK_DEBUG || k >= MG_BONUS_N) return;
    ENABLE_RAM;
    SWITCH_RAM(0);
    if (x != MG_D_NORMAL) {                      // an EASY or HARD medal: its own block (the played bit is set by NORMAL / ARCADE / CLASSIC)
        dx_get(d);
        x = x == MG_D_EASY ? 0 : 1;
        old = d[x];
        for (i = 0; i < k; i++) { mask <<= 2; m <<= 2; old >>= 2; }
        if (medal > (old & 3)) { d[x] = (d[x] & ~mask) | m; dx_put(d); }
        DISABLE_RAM;
        return;
    }
    bx_get(d);
    old = d[1];
    for (i = 0; i < k; i++) { mask <<= 2; m <<= 2; old >>= 2; was <<= 1; }   // (round k's 2 bits, its played bit)
    old &= 3;
    if (!(d[0] & was) || medal > old) {
        d[0] |= was;
        if (medal > old) d[1] = (d[1] & ~mask) | m;
        bx_put(d);
    }
    DISABLE_RAM;
}

// The HOW TO PLAY card of mini-game `id` (the cards are a bit each: ids from 15 up share bit 15). (Loops, not variable shifts: SDCC gave a
// wrong byte for `x << sh` with a run-time shift here.)
static uint16_t card_bit(uint8_t id) {
    uint16_t m = 1;
    if (id > 15) id = 15;
    while (id--) m <<= 1;
    return m;
}

uint8_t card_seen(uint8_t id) BANKED {
    uint8_t d[4];
    ENABLE_RAM;
    SWITCH_RAM(0);
    bx_get(d);
    DISABLE_RAM;
    return ((d[2] | ((uint16_t)d[3] << 8)) & card_bit(id)) != 0;
}

void card_mark(uint8_t id) BANKED {
    uint8_t d[4];
    uint16_t m = card_bit(id);
    if (save_lock == SAVE_LOCK_DEBUG) return;
    ENABLE_RAM;
    SWITCH_RAM(0);
    bx_get(d);
    d[2] |= (uint8_t)m; d[3] |= (uint8_t)(m >> 8);
    bx_put(d);
    DISABLE_RAM;
}

// BOSS RUSH (src/rush.c): the rush part of the block into dst[RUSH_SAVE_N] (all 0 when the block does not check out
// or is not "MGP2"). Kept out of WRAM: the rush reads it when its menu opens.
void rush_load(uint8_t *dst) BANKED {
    volatile uint8_t *b = SRAM + PR_AT + PR_RUSH;
    uint8_t i, ok;
    ENABLE_RAM;
    SWITCH_RAM(0);
    ok = pr_version() == '2';
    for (i = 0; i < RUSH_SAVE_N; i++) dst[i] = ok ? b[i] : 0;
    DISABLE_RAM;
}

// ... and written (with the mini-games' part from WRAM, as a good block has them)
void rush_store(const uint8_t *src) BANKED {
    ENABLE_RAM;
    SWITCH_RAM(0);
    pr_write(src);
    DISABLE_RAM;
}

// The story's SP_OUTRO in STORY or ARCADE: venue v's boss was beaten; BOSS RUSH lists him from now on. Written only
// when the bit is new; nothing in a debug-select run (ARCADE's save_lock 1 does not stop it: "beaten in STORY or
// ARCADE").
void boss_beaten(uint8_t v) BANKED {
    uint8_t r[RUSH_SAVE_N];
    uint16_t m;
    if (save_lock == SAVE_LOCK_DEBUG || v >= BOSS_COUNT || EASY_RUN) return;   // (an EASY story: he is not listed in BOSS RUSH)
    rush_load(r);
    m = r[RSV_BITS] | ((uint16_t)r[RSV_BITS + 1] << 8);
    if ((m >> v) & 1) return;
    m |= (uint16_t)1 << v;
    r[RSV_BITS] = (uint8_t)m; r[RSV_BITS + 1] = (uint8_t)(m >> 8);
    rush_store(r);
}

void hi_load(void) BANKED {
    uint16_t old = 0;
    uint8_t t, reorder = 0;
    volatile uint8_t *b;
    ENABLE_RAM;
    SWITCH_RAM(0);
    mg_unlocked = 0;
    for (t = 0; t < MG_PLANNED; t++) mg_best[t] = MEDAL_NONE;
    load_pr();
    for (t = 0; t < TOP_TABLES * TOP_N * 3; t++) top_names[t] = ' ';
    for (t = 0; t < TOP_TABLES * TOP_N; t++) top_scores[t] = 0;
    save_migrated = 0;
    tune_unlocked = 0;
    story_progress = 0; story_reached = 0;
    if (magic('7')) {
        if (sum_ok(SRAM, V7_LEN) && (SRAM[V7_STORY] & PROG_MASK) <= STORY_MAX && (SRAM[V7_STEP] & ~STEP_STAMP) < STEP_SAVED
            && !((SRAM[V7_STORY] & PROG_MASK) == STORY_MAX && (SRAM[V7_STEP] & ~STEP_STAMP) > 1)) {   // (chapter 10 cleared, step 1: the finale is not done yet; CONTINUE returns to the map)
            story_progress = SRAM[V7_STORY] & PROG_MASK; story_reached = STEP_CLAMP(SRAM[V7_STEP] & ~STEP_STAMP);
            tune_unlocked = ((SRAM[V7_TUNES] | ((uint16_t)SRAM[V7_TUNES + 1] << 8)) & TUNE_STORED) | (SRAM[V7_STORY] & FIN_BIT ? TUNE_FIN : 0);
            reorder = !(SRAM[V7_STEP] & STEP_STAMP);                     // (a save of the old order: below)
        }
        for (t = 0; t < TOP_TABLES; t++) load_tbl(t);   // each on its own (a bad main block keeps the tables)
    } else if (old_ok('6')) {
        story_progress = SRAM[V3_STORY]; story_reached = STEP_CLAMP(SRAM[V4_STEP]); save_migrated = 6; reorder = 1;
        old = SRAM[V5_TUNES] | ((uint16_t)SRAM[V5_TUNES + 1] << 8);
    } else if (old_ok('5')) {
        old_progress(SRAM[V3_STORY], SRAM[V4_STEP]); save_migrated = 5; reorder = 1;
        old = old_tunes(SRAM[V5_TUNES] | ((uint16_t)SRAM[V5_TUNES + 1] << 8));
    } else if (old_ok('4')) { old_progress(SRAM[V3_STORY], SRAM[V4_STEP]); save_migrated = 4; reorder = 1; }
    else if (old_ok('3')) { old_progress(SRAM[V3_STORY], 0); save_migrated = 3; reorder = 1; }
    if (reorder && story_progress > 1 && story_progress < 5) {      // progress in the order before 2026-11-07 (lodge, bistro, igloo): see the top of the file
        if (story_progress == 2) story_reached = 0;                  // (the old chapter 3 was the lodge: its steps are not the bistro's)
        else story_progress--;                                       // (old 3 cleared saloon, stadium, lodge: now 2; old 4 added the bistro: now 3; the next chapter is the same venue)
        if (!save_migrated) { save_migrated = 7; old = tune_unlocked; }   // (a version 7 save: its tunes are kept as they are)
    }
    b = SRAM + BC_AT;
    if (b[0] == 'B' && b[1] == 'C' && b[2] == 1 && sum_ok(b, BC_LEN)) level_dirs |= KEEP_POS;
    DISABLE_RAM;
    hi_pick(MODE_ARCADE);
    if (save_migrated) tune_unlocked = (old | progress_unlocks(story_progress, story_reached)) & (save_migrated == 7 ? TUNE_STORED | TUNE_FIN : TUNE_STORED);   // (an older save's bit 1 was a jingle's: dropped; a version 7 save's is the finished-once fact)
    tune_unlocked = (tune_unlocked | 1 << TUNE_TITLE) & (TUNE_STORED | TUNE_FIN);
    if (save_migrated) hi_save();
}

// SETTINGS > BAR CHANGE: the mode now in level_dirs (KEEP_POS) is kept (the debug box's START flips the bit without saving)
void bar_mode_save(void) BANKED {
    volatile uint8_t *b = SRAM + BC_AT;
    ENABLE_RAM;
    SWITCH_RAM(0);
    b[0] = 'B'; b[1] = 'C'; b[2] = (level_dirs & KEEP_POS) ? 1 : 0;
    sum_put(b, BC_LEN);
    DISABLE_RAM;
}

// SETTINGS > SCREEN: 1 NORMAL / 2 BRIGHT as saved, 0 when the player never chose (NORMAL; a GBA asks: main_cold.c screen_load)
uint8_t screen_saved(void) BANKED {
    volatile uint8_t *b = SRAM + SC_AT;
    uint8_t m = 0;
    ENABLE_RAM;
    SWITCH_RAM(0);
    if (b[0] == 'S' && b[1] == 'C' && (b[2] == 1 || b[2] == 2) && sum_ok(b, SC_LEN)) m = b[2];
    DISABLE_RAM;
    return m;
}

void screen_save(void) BANKED {                                // the choice now in _is_GBA bit 1
    volatile uint8_t *b = SRAM + SC_AT;
    ENABLE_RAM;
    SWITCH_RAM(0);
    b[0] = 'S'; b[1] = 'C'; b[2] = SCR_BRIGHT() ? 2 : 1;
    sum_put(b, SC_LEN);
    DISABLE_RAM;
}

// DEBUG MENU unlocked? (src/debug.c, SETTINGS' DEBUG line, the open gesture). A build with -DDEBUG_UNLOCKED is always unlocked.
uint8_t debug_unlocked(void) BANKED {
#ifdef DEBUG_UNLOCKED
    return 1;
#else
    volatile uint8_t *b = SRAM + DU_AT;
    uint8_t u;
    ENABLE_RAM;
    SWITCH_RAM(0);
    u = b[0] == 'D' && b[1] == 'U' && b[2] == 1 && sum_ok(b, DU_LEN);
    DISABLE_RAM;
    return u;
#endif
}

void debug_unlock(void) BANKED {
    volatile uint8_t *b = SRAM + DU_AT;
    ENABLE_RAM;
    SWITCH_RAM(0);
    b[0] = 'D'; b[1] = 'U'; b[2] = 1;
    sum_put(b, DU_LEN);
    DISABLE_RAM;
}

// The boss cards seen (src/boss.c fight_start): has venue v's boss's HOW TO PLAY card been shown, and the mark that it was.
static uint16_t bk_get(void) {
    volatile uint8_t *b = SRAM + BK_AT;
    uint16_t m = 0;
    if (b[0] == 'B' && b[1] == 'K' && sum_ok(b, BK_LEN) && !(b[3] >> (BOSS_COUNT - 8))) m = b[2] | ((uint16_t)b[3] << 8);
    return m;
}

uint8_t boss_card_seen(uint8_t v) BANKED {
    uint16_t m;
    ENABLE_RAM;
    SWITCH_RAM(0);
    m = bk_get();
    DISABLE_RAM;
    while (v--) m >>= 1;
    return (uint8_t)(m & 1);
}

void boss_card_mark(uint8_t v) BANKED {
    volatile uint8_t *b = SRAM + BK_AT;
    uint16_t m = 1;
    if (save_lock == SAVE_LOCK_DEBUG) return;
    while (v--) m <<= 1;
    ENABLE_RAM;
    SWITCH_RAM(0);
    m |= bk_get();
    b[0] = 'B'; b[1] = 'K'; b[2] = (uint8_t)m; b[3] = (uint8_t)(m >> 8);
    sum_put(b, BK_LEN);
    DISABLE_RAM;
}

// SETTINGS > ERASE DATA, confirmed: the cartridge as it left the factory. The whole 8 KB of SRAM is zeroed (every block above, the ones
// of older versions and anything unknown: none checks out, so every table, the story, the unlocks, the medals, BAR CHANGE and the
// debug unlock read as on a blank cartridge), then the working copies are loaded from it again (hi_load: everything empty, KEEP off).
void save_erase(void) BANKED {
    volatile uint8_t *p = SRAM;
    uint16_t n;
    ENABLE_RAM;
    SWITCH_RAM(0);
    for (n = 0; n < 0x2000; n++) { p[n] = 0; if (!(n & 0x1FF)) music_pump(); }
    DISABLE_RAM;
    level_dirs &= ~KEEP_POS;
    save_lock = 0;
    hi_load();
    screen_load();                               // (the SCREEN choice is gone with the rest: the hardware's default; the caller writes the palettes again: title.c)
}

// The save: the main block with the story's difficulty `d` (DIFF_*; 0xFF: the one the block holds now, NORMAL when there is none), the three tables
static void save_all(uint8_t d) {
    uint8_t i, k, t, *nm;
    volatile uint8_t *b, *e;
    uint32_t v, *sc;
    save_migrated &= ~TUNE_DIRTY;                // (whatever tune_unlocked holds goes in below)
    ENABLE_RAM;
    SWITCH_RAM(0);
    if (d == 0xFF) d = magic('7') && sum_ok(SRAM, V7_LEN) ? SRAM[V7_STORY] >> 6 : 0;   // (before the magic is rewritten)
    SRAM[0] = 'T'; SRAM[1] = 'P'; SRAM[2] = 'R'; SRAM[3] = '7';
    SRAM[V7_STORY] = story_progress | (d == 3 ? 0 : d << 6) | (tune_unlocked & TUNE_FIN ? FIN_BIT : 0); SRAM[V7_STEP] = story_reached | STEP_STAMP;
    SRAM[V7_TUNES] = (uint8_t)tune_unlocked & ~TUNE_FIN; SRAM[V7_TUNES + 1] = (uint8_t)(tune_unlocked >> 8);
    sum_put(SRAM, V7_LEN);
    for (t = 0; t < TOP_TABLES; t++) {
        b = SRAM + TBL_AT(t);
        nm = top_names + t * (TOP_N * 3); sc = top_scores + t * TOP_N;
        b[0] = 'H'; b[1] = 'S'; b[2] = tbl_letter[t]; b[3] = tbl_ver[t];
        for (i = 0, e = b + 4; i < TOP_N; i++, e += 6) {
            for (k = 0; k < 3; k++) e[k] = nm[i * 3 + k];
            v = sc[i];
            e[3] = (uint8_t)v; e[4] = (uint8_t)(v >> 8); e[5] = (uint8_t)(v >> 16);
        }
        sum_put(b, TBL_LEN);
        music_pump();                           // (the three tables take most of a frame: the tune ticks between them)
    }
    DISABLE_RAM;
}

void hi_save(void) BANKED {
    save_all(0xFF);                              // (the difficulty stays as saved: only a story_save, the progress it belongs to, changes it)
}

// M11b: the story progress (chapters cleared; story shifts: and the step reached in the next one), saved with the rest,
// and the unlocks it implies. Nothing in a debug-select run or ARCADE (save_lock): the real progress stays as it was.
void story_save(uint8_t chapters, uint8_t step) BANKED {
    if (save_lock) return;
    story_progress = chapters; story_reached = step;
    if (!EASY_RUN) tune_unlocked |= progress_unlocks(chapters, step) | (chapters == STORY_MAX && !step ? TUNE_FIN : 0);   // (the finale done: the credits were reached, for good)   // (EASY: the progress is kept for CONTINUE, nothing unlocks)
    save_all(RUN_DIFF);                          // (a STORY run: its difficulty goes with the progress)
}

// Is CONTINUE offered: a story saved part way (a shift or a chapter cleared, not all ten), or a quit debug-select run to resume
// (story_chapter | DEBUG_RESUME, set by pause.c's QUIT; main_cold.c clears it at start-up: WRAM is not zero on a real Game Boy)?
extern uint8_t story_chapter;
uint8_t can_continue(void) BANKED {
    return ((story_progress || story_reached) && story_progress < STORY_CHAPTERS) || (story_progress == STORY_CHAPTERS && story_reached)
           || (story_chapter & DEBUG_RESUME);   // (all ten venues cleared, the finale not done: the map, for the Pour-Off)
}

// CONTINUE's difficulty: what the saved story was started in (an older save, a bad block, a bad code: NORMAL)
uint8_t story_diff_saved(void) BANKED {
    uint8_t d = 0;
    ENABLE_RAM;
    SWITCH_RAM(0);
    if (magic('7') && sum_ok(SRAM, V7_LEN)) d = SRAM[V7_STORY] >> 6;
    DISABLE_RAM;
    return d == 3 ? 0 : d;
}

// A STORY run's points n as the difficulty scales them, live, in add_score: EASY half, HARD one and a half, NORMAL as they are (game.h
// (game.h). Rounded to the nearest 5 (half up) so a score stays a multiple of 5 as the game's are; 16-bit only.
uint16_t story_pts(uint16_t n) BANKED {
    if (RUN_DIFF == DIFF_EASY) return (n + 5) / 10 * 5;
    if (RUN_DIFF == DIFF_HARD) return (3 * n + 5) / 10 * 5;
    return n;
}

// A venue (chapter ch) is entered with `s` on the score: kept for CONTINUE. Nothing in a debug-select run or ARCADE.
void venue_score_put(uint8_t ch, uint32_t s) BANKED {
    volatile uint8_t *b = SRAM + SV_AT;
    if (save_lock) return;
    ENABLE_RAM;
    SWITCH_RAM(0);
    b[0] = 'S'; b[1] = 'V'; b[2] = ch;
    b[3] = (uint8_t)s; b[4] = (uint8_t)(s >> 8); b[5] = (uint8_t)(s >> 16);
    sum_put(b, SV_LEN);
    DISABLE_RAM;
}

// ... and CONTINUE's: the score kept for chapter ch (0 when there is none, it is for another chapter or it does not check out)
uint32_t venue_score_get(uint8_t ch) BANKED {
    volatile uint8_t *b = SRAM + SV_AT;
    uint32_t s = 0;
    ENABLE_RAM;
    SWITCH_RAM(0);
    if (b[0] == 'S' && b[1] == 'V' && b[2] == ch && sum_ok(b, SV_LEN)) {
        s = (uint32_t)b[3] | ((uint32_t)b[4] << 8) | ((uint32_t)b[5] << 16);
        if (s > HI_MAX) s = 0;
    }
    DISABLE_RAM;
    return s;
}

// The story map's block (src/smap.c): the stop and the festival flags into d[0], d[1]; 255 and 0 when the block does not check out
void sm_get(uint8_t *d) BANKED {
    volatile uint8_t *b = SRAM + SM_AT;
    ENABLE_RAM;
    SWITCH_RAM(0);
    if (b[0] == 'S' && b[1] == 'M' && sum_ok(b, SM_LEN) && b[2] <= 10 && !(b[3] & 0x88)) { d[0] = b[2]; d[1] = b[3]; }
    else { d[0] = 255; d[1] = 0; }
    DISABLE_RAM;
}

void sm_put(uint8_t stop, uint8_t flags) BANKED {
    volatile uint8_t *b = SRAM + SM_AT;
    if (save_lock) return;
    ENABLE_RAM;
    SWITCH_RAM(0);
    b[0] = 'S'; b[1] = 'M'; b[2] = stop; b[3] = flags;
    sum_put(b, SM_LEN);
    DISABLE_RAM;
}

// The story's credits are reached at least once: the finale done (story_end saves 10 chapters, step 0) in a story that was not on EASY (it unlocks nothing); a persistent fact. Level Clear, Game Over, Bonus Round, the credits tune and the bonus Easy Winners are unlocked by this and by nothing stored (owner Q52).
static uint8_t credits_reached(void) {
    return (uint8_t)tune_unlocked & TUNE_FIN;      // set by the finale of a story not on EASY, saved in byte 4 (FIN_BIT), kept through a new story
}

// The soundtrack player: tune t unlocked? The title always; the derived tunes by credits_reached; the others by their bit.
uint8_t tune_open(uint8_t t) BANKED {
    if (t == TUNE_TITLE) return 1;
    if (TUNE_DERIVED(t)) return credits_reached();
    return (uint8_t)(tune_unlocked >> t) & 1;
}

// music_play, in story mode: tune t was heard. A new unlock heard in a shift (GS_PLAYING .. GS_LEVEL_CLEAR) is marked and saved at the next quiet moment (TUNE_FLUSH: a
// shift's start, the title, any story_save), not mid-frame: the save takes 113 lines. Elsewhere (scenes, menus) it is saved at once. A power-off before then loses the unlock only.
void tune_heard(uint8_t t) BANKED {
    uint16_t m;
    if (save_lock || t >= TUNE_MAP + 1 || TUNE_DERIVED(t) || EASY_RUN) return;   // (an EASY story unlocks nothing; the derived tunes have no bit)
    m = (uint16_t)1 << t;
    if (tune_unlocked & m) return;
    tune_unlocked |= m;
    if (game_state >= GS_PLAYING && game_state <= GS_LEVEL_CLEAR) { save_migrated |= TUNE_DIRTY; return; }   // in a shift: later
    hi_save();                                   // (a scene, a menu: at once, as before)
}


// Where a score would go in table score_tbl: 0..TOP_N-1, or TOP_N when it does not make it. A tie goes below the
// older entry; a score of 0 never enters.
uint8_t top_rank(uint32_t s) BANKED {
    uint8_t i;
    uint32_t *sc = top_scores + score_tbl * TOP_N;
    if (s == 0) return TOP_N;
    for (i = 0; i < TOP_N; i++) if (s > sc[i]) return i;
    return TOP_N;
}

// Insert a score with the initials n[0..2] into table score_tbl at its rank (the last entry drops out); returns the
// rank (TOP_N: not inserted). The caller saves.
uint8_t top_insert(uint32_t s, const uint8_t *n) BANKED {
    uint8_t r = top_rank(s), i, *nm = top_names + score_tbl * (TOP_N * 3);
    uint32_t *sc = top_scores + score_tbl * TOP_N;
    if (r >= TOP_N) return TOP_N;
    for (i = TOP_N - 1; i > r; i--) {
        sc[i] = sc[i - 1];
        nm[i * 3] = nm[i * 3 - 3]; nm[i * 3 + 1] = nm[i * 3 - 2]; nm[i * 3 + 2] = nm[i * 3 - 1];
    }
    sc[r] = s;
    nm[r * 3] = n[0]; nm[r * 3 + 1] = n[1]; nm[r * 3 + 2] = n[2];
    hi_pick(score_tbl);
    return r;
}
