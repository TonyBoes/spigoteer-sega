// Music engine glue (hUGEDriver) and the sound-effect engine. ROM bank 2: the driver code, the order tables and
// instruments (build/music_data.c), the jingles' patterns and this file. hUGEDriver reads patterns through plain
// pointers, so it only sees data in the bank it runs from, or in WRAM. The title, show and venue tunes are too big
// for bank 2: their patterns sit in ROM bank 3 and music_tick copies them into WRAM (mus_buf_a: the title or the
// level's venue tune; mus_buf_b: the show tune, copied once and kept), a slice per frame, before a tune starts.
// The music uses channels 2 and 3 (melody, bass) and 4 (percussion in most tunes). Sound
// effects own channels 1 and 4: while one plays, the driver is told to leave that channel alone
// (hUGE_mute_channel) and the effect writes the registers itself, after the driver's tick.
#pragma bank 2
#include <gb/gb.h>
#include <stdint.h>
#include "music.h"

uint8_t  sound_on = 1;
uint8_t  last_sfx;
uint8_t  sfx_count[SFX_COUNT];
uint8_t  cur_tune = TUNE_NONE;
uint16_t music_frames;
uint8_t  sfx_req;
uint16_t music_late;
static uint8_t mus_active;       // the driver is running a tune
static uint8_t muted;            // bit n: driver channel n muted (cache of the driver's mask)
static uint8_t loaded[3] = { TUNE_NONE, TUNE_NONE, TUNE_NONE };   // [buffer]: the tune whose patterns are in it
static uint8_t ld_tune = TUNE_NONE;   // tune whose patterns are being copied (TUNE_NONE: no copy running)
static uint8_t ld_play;               // start it when the copy is done (else it is a preload)
static const uint8_t *groove;         // the running tune's drum loop (NULL: none)
static uint8_t g_pos, g_cnt;          // groove row, frames until it advances
static uint16_t ld_pos;               // bytes copied so far
#define LOAD_PLAY_BYTES    384     // per frame while the music waits for its patterns (no driver tick runs then)
#define LOAD_PRELOAD_BYTES  96     // per frame while the driver also ticks

typedef struct { uint16_t freq; uint8_t len; int8_t slide; } sfx_step_t;   // CH1: 11-bit period; CH4: NR43
typedef struct { uint8_t ch; uint8_t duty; uint8_t env; uint8_t nsteps; const sfx_step_t *steps; } sfx_def_t;

// Periods are computed (period = 2048 - 131072/Hz); the effects were designed on paper and never listened to.
static const sfx_step_t s_fill[]   = { {1524, 24, 11} };                  // 250 Hz rising to ~490 Hz over the 24-frame fill
static const sfx_step_t s_launch[] = { {1950, 14, -45} };                 // fast downward sweep, 25% pulse, decaying
static const sfx_step_t s_catch[]  = { {1982, 3, 0}, {2004, 8, 0} };      // two high pings
static const sfx_step_t s_break[]  = { {0x35, 6, 0}, {0x45, 8, 0}, {0x55, 8, 0} };   // noise crash, falling in pitch
static const sfx_step_t s_serve[]  = { {1798, 3, 0}, {1849, 3, 0}, {1881, 3, 0}, {1923, 8, 0} };   // C5 E5 G5 C6
static const sfx_step_t s_coin[]   = { {1915, 3, 0}, {1949, 10, 0} };     // B5 then E6
static const sfx_step_t s_life[]   = { {1714, 8, 0}, {1650, 8, 0}, {1547, 16, -6} };   // G4 E4 C4, sagging
static const sfx_step_t s_shake[]  = { {0x2B, 2, 0}, {0x3B, 2, 0}, {0x2B, 2, 0}, {0x3B, 2, 0} };   // noise rattle

#define N(a) (sizeof(a) / sizeof((a)[0]))
static const sfx_def_t sfx_defs[SFX_COUNT] = {
    { 0, 0, 0, 0, 0 },
    { 0, 0x80, 0x80, N(s_fill),   s_fill },
    { 0, 0x40, 0xA1, N(s_launch), s_launch },
    { 0, 0x80, 0xC2, N(s_catch),  s_catch },
    { 3, 0x00, 0xD2, N(s_break),  s_break },
    { 0, 0x80, 0xA1, N(s_serve),  s_serve },
    { 0, 0x80, 0xC1, N(s_coin),   s_coin },
    { 0, 0x40, 0xA3, N(s_life),   s_life },
    { 3, 0x00, 0x91, N(s_shake),  s_shake },
};

typedef struct {
    uint8_t busy;
    const sfx_def_t *def;
    uint8_t step, left;
    uint16_t freq;
    int8_t slide;
} voice_t;
static voice_t voice[2];          // 0: channel 1, 1: channel 4

static void set_mute(uint8_t ch, uint8_t m) {
    uint8_t bit = 1 << ch;
    if (((muted & bit) != 0) == (m != 0)) return;
    if (m) muted |= bit; else muted &= ~bit;
    hUGE_mute_channel(ch, m);
}

static void mute_unless_sfx(uint8_t ch, uint8_t v) {
    set_mute(ch, !mus_active || voice[v].busy);
}

static void silence_music(void) {
    mus_active = 0; ld_tune = TUNE_NONE;
    set_mute(0, 1); set_mute(1, 1); set_mute(2, 1); set_mute(3, 1);
}

void music_init(void) BANKED {
    NR52_REG = 0x80;           // sound on
    NR51_REG = 0xFF;           // every channel to both sides
    NR50_REG = 0x77;           // full master volume
    sound_on = 1; cur_tune = TUNE_NONE; mus_active = 0; muted = 0;
    loaded[1] = loaded[2] = ld_tune = TUNE_NONE;
}

static void start_song(uint8_t tune) {
    hUGE_init(tunes[tune].song);    // clears the driver's channel mute mask
    muted = 0;
    mus_active = 1;
    music_frames = 0;
    groove = tunes[tune].groove; g_pos = 0; g_cnt = 1;      // the groove's first row falls on the song's first row
    mute_unless_sfx(0, 0);          // a sound effect that is still sounding keeps its channels
    mute_unless_sfx(3, 1);
}

static void begin_load(uint8_t tune, uint8_t play) {
    ld_tune = tune; ld_pos = 0; ld_play = play;
    loaded[tunes[tune].buf] = TUNE_NONE;
}

extern uint8_t story_on;
void music_play(uint8_t tune) BANKED {
    uint8_t buf = tunes[tune].buf;
    if (story_on) tune_heard(tune);                 // the soundtrack player's unlocks (save.c), music on or off
    if (sound_on && cur_tune == tune && tunes[tune].loop && (mus_active || ld_tune == tune)) return;
    cur_tune = tune;
    if (!sound_on) return;
    if (buf && loaded[buf] != tune) {
        if (ld_tune == tune) {                      // its preload is running: keep the bytes copied so far
            silence_music(); ld_tune = tune; ld_play = 1;
            return;
        }
        silence_music();
        begin_load(tune, 1);
        return;
    }
    if (ld_tune != TUNE_NONE && ld_play) ld_tune = TUNE_NONE;       // a tune that was still loading is superseded
    start_song(tune);
}

void music_stop(void) BANKED {
    cur_tune = TUNE_NONE;
    silence_music();
}

void music_set_on(uint8_t on) BANKED {
    sound_on = on;
    if (!on) { silence_music(); return; }
    if (cur_tune != TUNE_NONE) music_play(cur_tune);
}

static void step_begin(voice_t *v) {
    const sfx_step_t *s = &v->def->steps[v->step];
    v->freq = s->freq; v->slide = s->slide; v->left = s->len;
    if (v->def->ch == 0) {
        NR10_REG = 0;
        NR11_REG = v->def->duty;
        NR12_REG = v->def->env;
        NR13_REG = (uint8_t)v->freq;
        NR14_REG = 0x80 | (v->freq >> 8);
    } else {
        NR41_REG = 0;
        NR42_REG = v->def->env;
        NR43_REG = (uint8_t)v->freq;
        NR44_REG = 0x80;
    }
}

static void sfx_start(uint8_t id) {
    voice_t *v = &voice[sfx_defs[id].ch ? 1 : 0];
    v->def = &sfx_defs[id];
    v->step = 0;
    v->busy = 1;
    set_mute(v->def->ch, 1);        // the driver lets go of the channel (and cuts its note) before we write
    step_begin(v);
}

static void voice_tick(uint8_t i) {
    voice_t *v = &voice[i];
    if (!v->busy) return;
    if (--v->left == 0) {
        if (++v->step < v->def->nsteps) { step_begin(v); return; }
        if (i == 0) NR12_REG = 0; else NR42_REG = 0;     // DAC off: silent
        v->busy = 0;
        mute_unless_sfx(i ? 3 : 0, i);
        return;
    }
    if (v->slide) {
        v->freq += v->slide;
        if (i == 0) { NR13_REG = (uint8_t)v->freq; NR14_REG = (v->freq >> 8) & 7; }   // no trigger bit: just retune
        else NR43_REG = (uint8_t)v->freq;
    }
}

// A tune's groove is a drum loop played here instead of by hUGEDriver (which would need a pattern per order in WRAM):
// one row every `tempo` frames, counted in step with the driver's own rows. A sound effect on channel 4 wins.
static void groove_tick(void) {
    uint8_t d;
    if (!groove || --g_cnt) return;
    g_cnt = groove[1];
    d = groove[2 + g_pos];
    if (++g_pos == groove[0]) g_pos = 0;
    if (d && !voice[1].busy) {
        const uint8_t *k = drum_kit[d - 1];
        NR41_REG = k[0]; NR42_REG = k[1]; NR43_REG = k[2]; NR44_REG = k[3];
    }
}

void music_tick(void) BANKED {
    uint8_t id, req = sfx_req;
    if (req) {
        sfx_req = 0;
        for (id = 1; id < SFX_COUNT; id++)          // ascending: on one channel the highest id requested wins
            if (req & (1 << (id - 1))) sfx_start(id);
    }
    if (ld_tune != TUNE_NONE) {
        const tune_t *t = &tunes[ld_tune];
        uint16_t n = t->bytes - ld_pos;
        uint16_t cap = ld_play ? LOAD_PLAY_BYTES : LOAD_PRELOAD_BYTES;
        if (n > cap) n = cap;
        mus_copy(t->bank, t->blob + ld_pos, (t->buf == 1 ? mus_buf_a : mus_buf_b) + ld_pos, n);
        ld_pos += n;
        if (ld_pos >= t->bytes) {
            uint8_t done = ld_tune;
            loaded[t->buf] = done;
            ld_tune = TUNE_NONE;
            if (ld_play) { start_song(done); voice_tick(0); voice_tick(1); return; }
        }
    } else if (mus_active && loaded[2] != TUNE_SHOW && sound_on)
        begin_load(TUNE_SHOW, 0);                                   // the show tune is copied once, while a level plays
    if (mus_active) {
        hUGE_dosound();
        groove_tick();
        music_frames++;
        if (!tunes[cur_tune].loop && music_frames >= tunes[cur_tune].frames) {
            cur_tune = TUNE_NONE;
            silence_music();
        }
    }
    voice_tick(0);
    voice_tick(1);
}
