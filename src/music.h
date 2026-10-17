// Music and sound effects (M7). The hUGEDriver code, the order tables and the jingles live in ROM bank 2;
// the pattern data of the title, show and venue tunes sits in ROM bank 10 and is copied into WRAM when a tune
// starts (the driver reads patterns through plain pointers, so it cannot read another bank itself).
#ifndef MUSIC_H
#define MUSIC_H
#include <gb/gb.h>
#include <stdint.h>
#include "hUGEDriver.h"

// TUNE_VENUE0 + g is the gameplay tune of patron group g (cowboys, sports, lumberjacks, chefs, divers, robots, punks,
// ninjas, zoo, aliens: tools/songs.py VENUES); TUNE_SHOW plays while a show runs.
// TUNE_COUNT: the tunes the soundtrack player lists and the save unlocks (bits of tune_unlocked); TUNE_CREDITS (the credits roll's
// tune, src/credits.c) comes after them and is in neither; TUNE_ALL sizes the tune tables.
enum { TUNE_TITLE, TUNE_CLEAR, TUNE_OVER, TUNE_BONUS, TUNE_SHOW, TUNE_VENUE0, TUNE_COUNT = TUNE_VENUE0 + 10, TUNE_CREDITS = TUNE_COUNT, TUNE_ALL, TUNE_NONE = 255 };
enum { SFX_NONE, SFX_FILL, SFX_LAUNCH, SFX_CATCH, SFX_BREAK, SFX_SERVE, SFX_COIN, SFX_LIFE, SFX_SHAKE, SFX_EXTRA, SFX_DON, SFX_KA, SFX_REV, SFX_WHOOSH, SFX_SWISH, SFX_COUNT };   // (14 of the 16 request bits)

typedef struct {
    const hUGESong_t *song;
    uint8_t  loop;          // 1: repeats forever, 0: jingle that stops after `frames`
    uint16_t frames;        // length of one pass
    uint8_t  buf;           // 0: patterns are in bank 2; 1: copy them to mus_buf_a (title, venue tunes); 2: to mus_buf_b (show)
    uint8_t  bank;          // ROM bank of the pattern blob
    const uint8_t *blob;    // pattern blob (buffer != 0)
    uint16_t bytes;         // its size
    const uint8_t *groove;  // NULL, or a drum loop src/music.c plays on channel 4: {rows, frames per row (over 15: a swing mask, bit n = the rows n mod 8 are a frame shorter than the song's tempo), one byte per row: 0 none, 1 kick, 2 snare, 3 hat}
    uint8_t  start;         // row of the song (0-255) the first play begins on (tools/songs.py song(start=)); the loop wraps to row 0
} tune_t;
extern const tune_t tunes[TUNE_ALL];
// The credits tune is longer than buffer A (CREDITS_ORDERS orders of a melody and a bass pattern; the buffer holds four orders): its blob
// (bank CREDITS_BANK, a bank of its own that also holds the tune's harmony) stores every order's pair, in order. The first four orders
// (tune_t.bytes) are copied before it starts; then, while order k plays, music_tick copies order k+2 over the buffer slot of order k-2
// (played by then), one slice of CREDITS_SLICE bytes on each of CREDITS_COPY_ROWS rows. tools/gen_music.py checks these numbers.
#define CREDITS_BANK        22
#define CREDITS_ORDERS      10
#define CREDITS_ORDER_BYTES (2 * 192)                                   // a melody and a bass pattern (192: 64 rows of 3 bytes)
#define CREDITS_COPY_ROWS   8                                           // the rows of an order the copy is spread over
#define CREDITS_SLICE       (CREDITS_ORDER_BYTES / CREDITS_COPY_ROWS)   // bytes copied on each of them
typedef char credits_slice_check[CREDITS_ORDER_BYTES % CREDITS_COPY_ROWS == 0 && CREDITS_SLICE <= 255 ? 1 : -1];
// Channel 1 harmony voice (music step 5): played by src/music.c itself, not by hUGEDriver (a fourth pattern per order
// would not fit WRAM). harm_tab[tune]: NULL or the tune's track in ROM bank HARM_BANK (the credits tune's: CREDITS_BANK): duty A, envelope A, duty B,
// envelope B (NR11, NR12), then events of two bytes, note (bits 0-6: hUGE note index or HARM_REST; bit 7: instrument
// B) and rows (1..255); rows 0 ends the track (it starts again, in step with the driver's loop). tools/gen_music.py.
#define HARM_BANK 10
#define HARM_REST 0x7F
extern const unsigned char * const harm_tab[TUNE_ALL];
// Taiko Pour (src/tk.c) sets spare bits of hUGE_mute_mask (the driver only reads bits 0-3) while it runs: the tune's own
// drum groove steps aside (TK_NOGROOVE), the channel-1 harmony stays silent (TK_NOHARM), the melody is out (TK_NOMELODY:
// start_song turns it into the driver's channel-2 mute bit); start_song keeps them (TK_HOLD) across a tune restart.
#define TK_NOGROOVE 0x10
#define TK_NOHARM   0x20
#define TK_NOMELODY 0x40
#define TK_HOLD     0x70
// TAIKO_VARIANT: which sound balance Taiko Pour has (make DEBUGFLAGS="-DDEBUG_MENU -DTAIKO_VARIANT=n"):
//   0 T2 (the old one): the player's DON / KA are noise hits on channel 4, the tune's groove steps aside, the rest plays
//   1 D1: DON / KA are pulse drums on channel 2 over a noise layer; the melody is out, the koto harmony (ch 1) and the bass stay
//   2 D2: pulse drums on channels 2 and 1 together; melody and harmony out: only the bass line and the beat
//   3 D3 (default): drums on channel 1; the melody plays only on the downbeats of each half bar, the harmony is out
#ifndef TAIKO_VARIANT
#define TAIKO_VARIANT 3
#endif
extern const unsigned char drum_kit[3][4];         // NR41, NR42, NR43, NR44 of kick, snare, hat (build/music_data.c)
extern unsigned char mus_buf_a[], mus_buf_b[];     // WRAM pattern buffers (build/music_data.c)
void mus_copy(uint8_t bank, const uint8_t *src, uint8_t *dst, uint16_t n);   // unbanked (src/musicload.c)
uint16_t harm_peek(const uint8_t *p);       // unbanked (src/musicload.c): p[0] | p[1] << 8 from the running tune's harmony bank (HARM_BANK, the credits tune's: CREDITS_BANK)

extern uint8_t sound_on;        // music enabled (SELECT on the title toggles it)
extern uint8_t last_sfx;        // id of the SFX started last (SFX_*), for tests
extern uint8_t sfx_count[SFX_COUNT];   // how many times each SFX was started
extern uint8_t cur_tune;        // TUNE_* playing (TUNE_NONE: silence)
extern uint16_t music_frames;   // frames the music engine has ticked since the last tune started
extern uint8_t music_fast;      // 1: venue tunes play one frame a row faster (a story shift's TWIST_FAST_TUNE: the band
                                // speeds up in The Chrome Cow's Last call); set before the music_play that starts it

void music_init(void) BANKED;               // sound hardware on, no tune
void music_play(uint8_t tune) BANKED;       // start a tune (a looping tune already playing is left alone). A tune whose patterns
                                            // are not in WRAM yet starts a few frames later (music_tick copies them first)
void music_stop(void) BANKED;
void music_set_on(uint8_t on) BANKED;       // sound_on, then start/stop the current tune accordingly
void music_tick(void) BANKED;               // once per frame, after the VBlank queue drain
void music_load_now(void) BANKED;           // LCD off: finish the pattern copy music_play began (the tune starts at once)
void music_pump(void) BANKED;               // inside a long LCD-off load: music_tick when a frame's time has passed
                                            // since the last tick (the timer, polled), so the tune does not stall

// Starting an effect from game code costs a few cycles: the request is only noted here and the registers are
// written by music_tick() after the frame's logic (the worst frames have no spare time). `id` must be a constant.
#define SFX(id) do { last_sfx = (id); sfx_count[(id)]++; sfx_req |= (uint16_t)1 << ((id) - 1); } while (0)
extern uint16_t sfx_req;        // bit (id-1): effect id requested since the last music_tick (16 bits: up to 16 effects)
extern uint16_t music_late;      // frames whose music tick was postponed because the frame was nearly full
#define MUSIC_LATEST_LY 124     // one tick takes up to ~16 lines (a row start with all channels busy): not started when the frame's logic ended on line 124..143

// src/save.c (M10b; the three modes: SRAM version 7): one top 5 with initials per mode, table t = MODE_ARCADE /
// MODE_STORY / MODE_CLASSIC (game.h; the LEVEL harness counts as ARCADE), each its own SRAM block; hi_score / hi_digits
// mirror entry 1 of the table hi_pick chose (the title's HI line)
#define TOP_N 5
#define TOP_TABLES 3
extern uint8_t  top_names[TOP_TABLES * TOP_N * 3];
extern uint32_t top_scores[TOP_TABLES * TOP_N];
extern uint8_t  score_tbl;                  // the table top_rank / top_insert and the table screen (scores.c) work on
void hi_load(void) BANKED;                  // SRAM -> the tables and the story (a bad block: that part empty; v3-v6 migrate)
void hi_save(void) BANKED;                  // everything -> SRAM (the main block and the three tables)
void hi_pick(uint8_t t) BANKED;             // hi_score / hi_digits = table t's best
void split6(uint8_t *d, uint32_t v) BANKED; // d[0..5] = v's six low decimal digits, 0-9 (no 32-bit division: fast)
uint8_t top_rank(uint32_t s) BANKED;        // where s would go in table score_tbl (TOP_N: not in the table)
uint8_t top_insert(uint32_t s, const uint8_t *n) BANKED;   // insert into table score_tbl with initials n[0..2]; the rank
extern uint8_t story_progress;              // M11b: story chapters cleared (0..10), saved next to the table
extern uint8_t story_reached;               // story shifts: the step reached in chapter story_progress (save.c)
void story_save(uint8_t chapters, uint8_t step) BANKED;   // story_progress / story_reached, then the whole save
void bar_mode_save(void) BANKED;                       // SETTINGS > BAR CHANGE: the mode in level_dirs (KEEP_POS) into SRAM
void save_erase(void) BANKED;                          // SETTINGS > ERASE DATA, confirmed: all of SRAM zeroed, the working copies reloaded (a blank cartridge)
uint8_t debug_unlocked(void) BANKED;                   // the DEBUG MENU is unlocked (SRAM "DU"; a -DDEBUG_UNLOCKED build: always)
void debug_unlock(void) BANKED;                        // ... and kept (src/debug.c's trigger on the title)
void venue_score_put(uint8_t ch, uint32_t s) BANKED;     // a venue was entered with score s: kept for CONTINUE (not in a debug / ARCADE run)
uint32_t venue_score_get(uint8_t ch) BANKED;             // CONTINUE: the score kept for chapter ch (0 when none)
extern uint16_t tune_unlocked;              // bonus menu: bit t = tune t playable in the soundtrack player (SRAM v5 on)
extern uint8_t  save_lock;                  // 1: a debug-select story run writes nothing to SRAM (title_enter clears it)
void tune_heard(uint8_t t) BANKED;          // music_play in story mode: unlock tune t (saved by the next TUNE_FLUSH / story_save when heard in a shift, at once elsewhere)
extern uint8_t  save_migrated;              // (save.c) bit 7 = TUNE_DIRTY: a tune unlock heard in a shift is not saved yet
#define TUNE_DIRTY 0x80
#define TUNE_FLUSH() do { if (save_migrated & TUNE_DIRTY) hi_save(); } while (0)   // at a quiet moment (a shift's start, the title): saves it
#endif
