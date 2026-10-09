// Music and sound effects (M7). Everything here lives in ROM bank 2 together with the hUGEDriver code
// and the song data (the driver reads patterns through plain pointers, so they must share a bank).
#ifndef MUSIC_H
#define MUSIC_H
#include <gb/gb.h>
#include <stdint.h>
#include "hUGEDriver.h"

enum { TUNE_TITLE, TUNE_GAME, TUNE_CLEAR, TUNE_OVER, TUNE_BONUS, TUNE_COUNT, TUNE_NONE = 255 };
enum { SFX_NONE, SFX_FILL, SFX_LAUNCH, SFX_CATCH, SFX_BREAK, SFX_SERVE, SFX_COIN, SFX_LIFE, SFX_SHAKE, SFX_COUNT };

typedef struct {
    const hUGESong_t *song;
    uint8_t  loop;          // 1: repeats forever, 0: jingle that stops after `frames`
    uint16_t frames;        // length of one pass
} tune_t;
extern const tune_t tunes[TUNE_COUNT];

extern uint8_t sound_on;        // music enabled (SELECT on the title toggles it)
extern uint8_t last_sfx;        // id of the SFX started last (SFX_*), for tests
extern uint8_t sfx_count[SFX_COUNT];   // how many times each SFX was started
extern uint8_t cur_tune;        // TUNE_* playing (TUNE_NONE: silence)
extern uint16_t music_frames;   // frames the music engine has ticked since the last tune started

void music_init(void) BANKED;               // sound hardware on, no tune
void music_play(uint8_t tune) BANKED;       // start a tune (a looping tune already playing is left alone)
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
