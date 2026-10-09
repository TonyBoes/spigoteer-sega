// Music and sound effects (M7). The hUGEDriver code, the order tables and the jingles live in ROM bank 2;
// the pattern data of the title, show and venue tunes sits in ROM bank 3 and is copied into WRAM when a tune
// starts (the driver reads patterns through plain pointers, so it cannot read another bank itself).
#ifndef MUSIC_H
#define MUSIC_H
#include <gb/gb.h>
#include <stdint.h>
#include "hUGEDriver.h"

// TUNE_VENUE0 + g is the gameplay tune of patron group g (cowboys, sports, lumberjacks, chefs, divers, robots, ninjas,
// aliens, zoo); TUNE_SHOW plays while a show runs.
enum { TUNE_TITLE, TUNE_CLEAR, TUNE_OVER, TUNE_BONUS, TUNE_SHOW, TUNE_VENUE0, TUNE_COUNT = TUNE_VENUE0 + 9, TUNE_NONE = 255 };
enum { SFX_NONE, SFX_FILL, SFX_LAUNCH, SFX_CATCH, SFX_BREAK, SFX_SERVE, SFX_COIN, SFX_LIFE, SFX_SHAKE, SFX_COUNT };

typedef struct {
    const hUGESong_t *song;
    uint8_t  loop;          // 1: repeats forever, 0: jingle that stops after `frames`
    uint16_t frames;        // length of one pass
    uint8_t  buf;           // 0: patterns are in bank 2; 1: copy them to mus_buf_a (title, venue tunes); 2: to mus_buf_b (show)
    uint8_t  bank;          // ROM bank of the pattern blob
    const uint8_t *blob;    // pattern blob (buffer != 0)
    uint16_t bytes;         // its size
    const uint8_t *groove;  // NULL, or a drum loop src/music.c plays on channel 4: {rows, frames per row, one byte per row: 0 none, 1 kick, 2 snare, 3 hat}
} tune_t;
extern const tune_t tunes[TUNE_COUNT];
extern const unsigned char drum_kit[3][4];         // NR41, NR42, NR43, NR44 of kick, snare, hat (build/music_data.c)
extern unsigned char mus_buf_a[], mus_buf_b[];     // WRAM pattern buffers (build/music_data.c)
void mus_copy(uint8_t bank, const uint8_t *src, uint8_t *dst, uint16_t n);   // unbanked (src/musicload.c)

extern uint8_t sound_on;        // music enabled (SELECT on the title toggles it)
extern uint8_t last_sfx;        // id of the SFX started last (SFX_*), for tests
extern uint8_t sfx_count[SFX_COUNT];   // how many times each SFX was started
extern uint8_t cur_tune;        // TUNE_* playing (TUNE_NONE: silence)
extern uint16_t music_frames;   // frames the music engine has ticked since the last tune started

void music_init(void) BANKED;               // sound hardware on, no tune
void music_play(uint8_t tune) BANKED;       // start a tune (a looping tune already playing is left alone). A tune whose patterns
                                            // are not in WRAM yet starts a few frames later (music_tick copies them first)
void music_stop(void) BANKED;
void music_set_on(uint8_t on) BANKED;       // sound_on, then start/stop the current tune accordingly
void music_tick(void) BANKED;               // once per frame, after the VBlank queue drain

// Starting an effect from game code costs a few cycles: the request is only noted here and the registers are
// written by music_tick() after the frame's logic (the worst frames have no spare time). `id` must be a constant.
#define SFX(id) do { last_sfx = (id); sfx_count[(id)]++; sfx_req |= (uint8_t)(1 << ((id) - 1)); } while (0)
extern uint8_t sfx_req;         // bit (id-1): effect id requested since the last music_tick
extern uint16_t music_late;      // frames whose music tick was postponed because the frame was nearly full
#define MUSIC_LATEST_LY 124     // one tick takes up to ~16 lines (a row start with all channels busy): not started when the frame's logic ended on line 124..143

void hi_load(void) BANKED;                  // SRAM -> hi_score / hi_digits (0 when invalid)
void hi_save(void) BANKED;                  // hi_score -> SRAM
#endif
