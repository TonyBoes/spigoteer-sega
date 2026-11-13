// Music and sound effects (M7). The hUGEDriver code, the order tables and the jingles live in ROM bank 2;
// the pattern data of the title, show and venue tunes sits in ROM bank 10 and is copied into WRAM when a tune
// starts (the driver reads patterns through plain pointers, so it cannot read another bank itself).
#ifndef MUSIC_H
#define MUSIC_H
#include <gb/gb.h>
#include <stdint.h>
#include "hUGEDriver.h"

// Color double speed (src/main_cold.c boot_init switches once at boot): the CPU-clock timer (TAC 4096 Hz) then counts 8192 Hz. DS_NOW reads the
// speed from KEY1 bit 7 (a DMG reads 0xFF there: is_cgb first), no variable; DS_SCALE(n) is a 4096 Hz count n as the running speed counts it.
// Every use is the music's frame timer (music.c, title.c, trans.c): everything else waits on LY, which does not change with the CPU speed.
extern uint8_t is_cgb;
#define DS_NOW         (is_cgb && (KEY1_REG & 0x80))
#define DS_SCALE(n)    (DS_NOW ? (n) * 2 : (n))

// TUNE_VENUE0 + g is the gameplay tune of patron group g (cowboys, sports, lumberjacks, chefs, divers, robots, punks,
// ninjas, zoo, aliens: tools/songs.py VENUES); TUNE_SHOW plays while a show runs.
// TUNE_MAP is the story map's tune (Swipesy), TUNE_CREDITS the credits roll's (The Easy Winners, src/credits.c), TUNE_EWFAST a faster Easy Winners that only the soundtrack
// player plays. TUNE_COUNT: the tunes the soundtrack player lists and TUNE_ALL sizes the tune tables (the same 18). Unlocks (src/save.c tune_open): the title always; the
// stored bits of tune_unlocked (16 bits: tunes 0-15, TUNE_STORED) for the show tune, the ten venues and the map; Level Clear, Game Over, Bonus Round, the credits tune and
// the fast Easy Winners (TUNE_DERIVED: no bit) once the story's credits are reached (save.c credits_reached: the story complete).
enum { TUNE_TITLE, TUNE_CLEAR, TUNE_OVER, TUNE_BONUS, TUNE_SHOW, TUNE_VENUE0, TUNE_VENUE_END = TUNE_VENUE0 + 10, TUNE_MAP = TUNE_VENUE_END, TUNE_CREDITS, TUNE_EWFAST,
       TUNE_COUNT, TUNE_ALL = TUNE_COUNT, TUNE_NONE = 255 };
#define TUNE_DERIVED(t) (((t) >= TUNE_CLEAR && (t) <= TUNE_BONUS) || (t) >= TUNE_CREDITS)   // unlocked by the story's end, not by a stored bit
enum { SFX_NONE, SFX_FILL, SFX_LAUNCH, SFX_CATCH, SFX_BREAK, SFX_SERVE, SFX_COIN, SFX_LIFE, SFX_SHAKE, SFX_EXTRA, SFX_DON, SFX_KA, SFX_REV, SFX_WHOOSH, SFX_SWISH, SFX_PERFECT, SFX_COUNT };   // (15 of the 16 request bits)

typedef struct {
    const hUGESong_t *song;
    uint8_t  loop;          // 1: repeats forever, 0: jingle that stops after `frames`
    uint16_t frames;        // length of one pass
    uint8_t  buf;           // 1: copy the patterns to mus_buf_a (the jingles, venue tunes); 2: to mus_buf_b (show); 3: a streamed tune in mus_buf_a (the title, the credits)
    uint8_t  bank;          // ROM bank of the pattern blob
    const uint8_t *blob;    // pattern blob (buffer != 0)
    uint16_t bytes;         // its size
    const uint8_t *groove;  // NULL, a DRUM TRACK (first byte TRACK_MARK: see src/music.c trk_fetch), or a drum loop src/music.c plays on channel 4: {rows, frames per row (over 15: a swing mask, bit n = the rows n mod 8 are a frame shorter than the song's tempo), one byte per row: 0 none, 1 kick, 2 snare, 3 hat}
    uint8_t  start;         // row of the song (0-255) the first play begins on (tools/songs.py song(start=)); the loop wraps to row 0
} tune_t;
#define TRACK_MARK 255      // tools/gen_music.py TRACK_MARK: a groove header starting with it is a drum track (the credits tune)
#define TRACK_TICK 5        // the tick of a row (after the driver's tick counter reads it) a track's next byte is read on: a plain one that is not STREAM_TICK; the tune's rows are 6 frames or more
extern const tune_t tunes[TUNE_ALL];
// The title tune (20 orders, looping) and the credits tune (10 orders, once) are longer than buffer A (a streamed tune: tune_t.buf 3; the buffer
// holds four orders of a melody and a bass pattern). Each has a bank of its own (tune_t.bank) with its blob, one pattern pair per order in order,
// and its harmony. The first four orders (tune_t.bytes) are copied before it starts; then, while order k plays, music_tick copies order k+2 (mod the
// order count: the title wraps, the credits stop) over the buffer slot of order k-2 (played by then), one slice of STREAM_SLICE bytes on
// each of STREAM_COPY_ROWS rows, on tick STREAM_TICK of the row (a plain tick: tick 1 follows the row tick, the dearest call).
// tools/gen_music.py checks these numbers.
#define STREAM_ORDER_BYTES (2 * 192)                                   // a melody and a bass pattern (192: 64 rows of 3 bytes)
#define STREAM_COPY_ROWS   8                                           // the rows of an order the copy is spread over (rows 2 .. 9)
#define STREAM_SLICE       (STREAM_ORDER_BYTES / STREAM_COPY_ROWS)     // bytes copied on each of them
#define STREAM_TICK        3
typedef char stream_slice_check[STREAM_ORDER_BYTES % STREAM_COPY_ROWS == 0 && STREAM_SLICE <= 255 ? 1 : -1];
// Channel 1 harmony voice (music step 5): played by src/music.c itself, not by hUGEDriver (a fourth pattern per order
// would not fit WRAM). harm_tab[tune]: NULL or the tune's track in ROM bank HARM_BANK (a streamed tune's: its blob's bank, tune_t.bank): duty A, envelope A, duty B,
// envelope B (NR11, NR12), then events of two bytes, note (bits 0-6: hUGE note index or HARM_REST; bit 7: instrument
// B) and rows (1..255); rows 0 ends the track (it starts again, in step with the driver's loop). tools/gen_music.py.
#define HARM_BANK 24
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
extern const unsigned char drum_kit[6][6];         // NR41, NR42, NR43, NR44, NR43 +1 and +2 frames of b n t o m x (build/music_data.c)
extern unsigned char mus_buf_a[], mus_buf_b[];     // WRAM pattern buffers (build/music_data.c)
void mus_copy(uint8_t bank, const uint8_t *src, uint8_t *dst, uint16_t n);   // unbanked (src/musicload.c)
uint16_t harm_peek(uint8_t bank, const uint8_t *p);   // unbanked (src/musicload.c): p[0] | p[1] << 8 from the harmony's ROM bank (HARM_BANK, a streamed tune's: its blob's)

extern uint8_t sound_on;        // music enabled (SELECT on the title toggles it)
extern uint8_t pour_streak;     // perfect pours in a row, capped at 3 (0: none): src/mugs.c launch_mug sets it, src/music.c reads it (1: the chime, 2: a tone up, 3: the x2 chime)
extern uint8_t last_sfx;        // id of the SFX started last (SFX_*), for tests
extern uint8_t sfx_count[SFX_COUNT];   // how many times each SFX was started
extern uint8_t cur_tune;        // TUNE_* playing (TUNE_NONE: silence)
extern uint16_t music_frames;   // frames the music engine has ticked since the last tune started
extern uint8_t music_fast;      // 1: venue tunes play one frame a row faster (a story shift's TWIST_FAST_TUNE: the band
                                // speeds up in The Chrome Cow's Last call); set before the music_play that starts it

void music_init(void) BANKED;               // sound hardware on, no tune
#define MUSIC_LATER 0x80                        // OR-ed into the tune: if it is already loaded, it starts one frame later (spreads a busy frame)
void music_play(uint8_t tune) BANKED;       // start a tune (a looping tune already playing is left alone). A tune whose patterns
                                            // are not in WRAM yet starts a few frames later (music_tick copies them first)
uint16_t music_tune_frames(uint8_t tune) BANKED;   // one pass of the tune, in frames (orders x 64 rows x its tempo)
void music_stop(void) BANKED;
void music_set_on(uint8_t on) BANKED;       // sound_on, then start/stop the current tune accordingly
void music_tick(void) BANKED;               // once per frame, after the VBlank queue drain
void music_load_now(void) BANKED;           // LCD off: finish the pattern copy music_play began (the tune starts at once)
void music_load_now_p(void) BANKED;         // the same, pumping between the slices
void music_pump_cr(void) BANKED;            // the credits roll's pump: music_pump, but not in the picture's last lines (src/music.c)
void music_pump(void) BANKED;               // inside a long LCD-off load: music_tick when a frame's time has passed
                                            // since the last tick (the timer, polled), so the tune does not stall

// Starting an effect from game code costs a few cycles: the request is only noted here and the registers are
// written by music_tick() after the frame's logic (the worst frames have no spare time). `id` must be a constant.
#define SFX(id) do { last_sfx = (id); sfx_count[(id)]++; sfx_req |= (uint16_t)1 << ((id) - 1); } while (0)
extern uint16_t sfx_req;        // bit (id-1): effect id requested since the last music_tick (16 bits: up to 16 effects)
extern uint16_t music_late;      // frames whose music tick was postponed because the frame was nearly full
#define MUSIC_LATEST_LY 120     // one tick takes up to ~18 lines (a show-tune row start with the lead, bass and a drum table running: measured 18 in game, 16.8 in the audition harness); a tick started after line 120 could run into VBlank (documentation: main.c ticks every frame and counts those that began after VBlank in music_late)

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
uint8_t tune_open(uint8_t t) BANKED;        // the soundtrack player: is tune t unlocked (save.c)
extern uint16_t tune_unlocked;              // bonus menu: bit t = tune t playable in the soundtrack player (SRAM v5 on)
extern uint8_t  save_lock;                  // 1: a debug-select story run writes nothing to SRAM (title_enter clears it)
void tune_heard(uint8_t t) BANKED;          // music_play in story mode: unlock tune t (saved by the next TUNE_FLUSH / story_save when heard in a shift, at once elsewhere)
extern uint8_t  save_migrated;              // (save.c) bit 7 = TUNE_DIRTY: a tune unlock heard in a shift is not saved yet
#define TUNE_DIRTY 0x80
#define TUNE_FLUSH() do { if (save_migrated & TUNE_DIRTY) hi_save(); } while (0)   // at a quiet moment (a shift's start, the title): saves it
#endif
