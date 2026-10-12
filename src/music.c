// Music engine glue (hUGEDriver) and the sound-effect engine. ROM bank 2: the driver code, the order tables and
// instruments (build/music_data.c), the jingles' patterns and this file. hUGEDriver reads patterns through plain
// pointers, so it only sees data in the bank it runs from, or in WRAM. The title, show and venue tunes are too big
// for bank 2: their patterns sit in ROM bank 10 and music_tick copies them into WRAM (mus_buf_a: the title or the
// level's venue tune; mus_buf_b: the show tune, copied once and kept), a slice per frame, before a tune starts.
// The music uses channels 2 and 3 (melody, bass) and 4 (percussion in most tunes) through the driver, and channel 1 for
// a quieter harmony line that harm_tick plays itself (music step 5). Sound effects own channels 1 and 4: while one
// plays, the driver is told to leave channel 4 alone (hUGE_mute_channel) and harm_tick writes nothing to channel 1;
// the effect writes the registers itself, after the music's tick. The driver never touches channel 1 (its mute bit
// stays set while a tune plays; its channel-1 patterns are empty anyway).
#pragma bank 2
#include <gb/gb.h>
#include <stdint.h>
#include "music.h"

uint8_t  sound_on = 1;
uint8_t  last_sfx;
uint8_t  sfx_count[SFX_COUNT];
uint8_t  cur_tune = TUNE_NONE;
uint16_t music_frames;
uint16_t sfx_req;
uint16_t music_late;
static uint8_t mus_active;       // the driver is running a tune
static uint8_t muted;            // bit n: driver channel n muted (cache of the driver's mask)
static uint8_t loaded[3] = { TUNE_NONE, TUNE_NONE, TUNE_NONE };   // [buffer]: the tune whose patterns are in it
static uint8_t ld_tune = TUNE_NONE;   // tune whose patterns are being copied (TUNE_NONE: no copy running)
static uint8_t ld_play;               // start it when the copy is done (else it is a preload)
static const uint8_t *groove;         // the running tune's drum loop (NULL: none)
static uint8_t g_pos, g_cnt;          // groove row, frames until it advances
extern unsigned char hUGE_ticks_per_row;   // the driver's tempo, as hUGE_init set it (exported for this: CREDITS.md)
uint8_t music_fast;                   // 1: a venue tune plays one frame a row faster (story: TWIST_FAST_TUNE)
static uint8_t fast_now;              // the running tune plays fast
static uint16_t ld_pos;               // bytes copied so far
extern const uint16_t hUGE_note_table[];   // the driver's 72 periods (exported for this: CREDITS.md)
static const uint8_t *harm;           // the running tune's channel-1 harmony track (bank HARM_BANK), NULL: none
static const uint8_t *h_ptr;          // its next event
static uint8_t h_inst[4];             // duty A, envelope A, duty B, envelope B (the track's header)
static uint8_t h_note;                // the current event's note byte (HARM_REST: a rest)
static uint8_t h_rows, h_cnt;         // rows left in the event, frames left in the row
static uint8_t h_sound;               // 1: the current harmony note sounds on channel 1 (0: rest, or an effect took it)
#define LOAD_PLAY_BYTES    384     // per frame while the music waits for its patterns (no driver tick runs then)
#define LOAD_PRELOAD_BYTES  96     // per frame while the driver also ticks
#define FRAME_TIMA          69     // one frame (1/59.73 s) in 4096 Hz timer counts (68.6)

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
// extra life (owner request): a bright C-major fanfare above the serve's arpeggio, ending in a G6 / C7 shimmer that
// rings out: C6 E6 G6 C7, G6 C7, G6 C7 (held); 33 frames (0.55 s) on a 25% pulse
static const sfx_step_t s_extra[]  = { {1923, 3, 0}, {1949, 3, 0}, {1964, 3, 0}, {1985, 5, 0},
                                       {1964, 3, 0}, {1985, 3, 0}, {1964, 3, 0}, {1985, 10, 0} };

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
    { 0, 0x40, 0xD2, N(s_extra),  s_extra },
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

static void harm_off(void) {          // the harmony lets go of channel 1 (volume 0, DAC kept on: no click)
    if (h_sound && !voice[0].busy) { NR12_REG = 0x08; NR14_REG = 0x80; }
    h_sound = 0;
}

static void silence_music(void) {
    harm_off(); harm = 0;
    mus_active = 0; ld_tune = TUNE_NONE;
    set_mute(0, 1); set_mute(1, 1); set_mute(2, 1); set_mute(3, 1);
}

void music_init(void) BANKED {
    TMA_REG = 0; TIMA_REG = 0;
    TAC_REG = TACF_START | TACF_4KHZ;   // the frame timer music_pump polls (no interrupt: IE leaves it out)
    NR52_REG = 0x80;           // sound on
    NR51_REG = 0xFF;           // every channel to both sides
    NR50_REG = 0x77;           // full master volume
    sound_on = 1; cur_tune = TUNE_NONE; mus_active = 0; muted = 0;
    loaded[1] = loaded[2] = ld_tune = TUNE_NONE;
}

static void start_song(uint8_t tune) {
    hUGE_init(tunes[tune].song);    // clears the driver's channel mute mask
    fast_now = music_fast && tune >= TUNE_VENUE0;
    hUGE_ticks_per_row -= fast_now;   // (the groove below follows: one frame less a row)
    hUGE_mute_mask = muted = 1;     // channel 1 is harm_tick's: the driver leaves it alone (set directly: no note cut,
                                    // so an effect still sounding there plays on)
    mus_active = 1;
    music_frames = 0;
    groove = tunes[tune].groove; g_pos = 0; g_cnt = 1;      // the groove's first row falls on the song's first row
    harm_off();
    harm = harm_tab[tune]; h_rows = 0; h_cnt = 1;           // so does the harmony's first event
    if (harm) { mus_copy(HARM_BANK, harm, h_inst, 4); h_ptr = harm + 4; }
    mute_unless_sfx(3, 1);          // a sound effect that is still sounding keeps channel 4
}

static void begin_load(uint8_t tune, uint8_t play) {
    ld_tune = tune; ld_pos = 0; ld_play = play;
    loaded[tunes[tune].buf] = TUNE_NONE;
}

extern uint8_t story_on;
void music_play(uint8_t tune) BANKED {
    uint8_t buf = tunes[tune].buf;
    if (story_on) tune_heard(tune);                 // the soundtrack player's unlocks (save.c), music on or off
    if (sound_on && cur_tune == tune && tunes[tune].loop && (mus_active || ld_tune == tune)
        && fast_now == (music_fast && tune >= TUNE_VENUE0)) return;   // (a speed change restarts it)
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
    if (v->busy && v->def == &sfx_defs[SFX_EXTRA] && id != SFX_EXTRA) return;   // the extra life is not cut short
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
        if (i == 0) { NR12_REG = 0x08; NR14_REG = 0x80; }   // channel 1: volume 0, the DAC stays on (the harmony comes
        else NR42_REG = 0;                                  // back on it without the click of a DAC switching); 4: DAC off
        v->busy = 0;
        if (i) mute_unless_sfx(3, 1);    // (channel 1: harm_tick picks the harmony up again by itself)
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
    g_cnt = groove[1] - fast_now;
    d = groove[2 + g_pos];
    if (++g_pos == groove[0]) g_pos = 0;
    if (d && !voice[1].busy) {
        const uint8_t *k = drum_kit[d - 1];
        NR41_REG = k[0]; NR42_REG = k[1]; NR43_REG = k[2]; NR44_REG = k[3];
    }
}

static void harm_note(void) {
    uint16_t p = hUGE_note_table[h_note & 0x7F];
    const uint8_t *in = &h_inst[(h_note & 0x80) ? 2 : 0];
    NR10_REG = 0;
    NR11_REG = in[0];
    NR12_REG = in[1];
    NR13_REG = (uint8_t)p;
    NR14_REG = 0x80 | (uint8_t)(p >> 8);
    h_sound = 1;
}

// The channel-1 harmony (music step 5): one event (a note or a rest of n rows) after another, counted in step with the
// driver's rows like the groove, looping with the tune. While a sound effect has channel 1 nothing is written; when it
// ends, a harmony note with more than a row still to go is struck again, otherwise the next event brings the voice back.
static void harm_tick(void) {
    uint16_t ev;
    if (voice[0].busy) h_sound = 0;                      // the effect has the channel (it overwrote the note)
    if (--h_cnt == 0) {
        h_cnt = hUGE_ticks_per_row;
        if (h_rows == 0 || --h_rows == 0) {
            ev = harm_peek(h_ptr);
            if (!(ev >> 8)) {                            // the end of the track: from the top, as the driver loops
                h_ptr = harm + 4;
                ev = harm_peek(h_ptr);
            }
            h_ptr += 2;
            h_note = (uint8_t)ev; h_rows = ev >> 8;
            if ((h_note & 0x7F) == HARM_REST) harm_off();
            else if (!voice[0].busy) harm_note();
            return;
        }
    }
    if (!h_sound && h_rows > 1 && (h_note & 0x7F) != HARM_REST && !voice[0].busy) harm_note();   // back after an effect
}

static void tick(void) {
    uint8_t id;
    uint16_t req = sfx_req;
    if (req) {
        sfx_req = 0;
        for (id = 1; id < SFX_COUNT; id++)          // ascending: on one channel the highest id requested wins
            if (req & ((uint16_t)1 << (id - 1))) sfx_start(id);
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
        if (harm) harm_tick();
        music_frames++;
        if (!tunes[cur_tune].loop && music_frames >= tunes[cur_tune].frames) {
            cur_tune = TUNE_NONE;
            silence_music();
        }
    }
    voice_tick(0);
    voice_tick(1);
}

// The game's frame tick (main.c, once per main loop). It restarts the frame timer music_pump watches.
void music_tick(void) BANKED {
    tick();
    TIMA_REG = 0;
}

// A long LCD-off load (the title's, the top-5 table's) is one main-loop pass of several frames, and the music only
// ticks once per pass: the tune stalled for those frames (owner: the title tune hitched at every attract switch).
// Such loads call this between their steps: when a frame's time (the timer, FRAME_TIMA counts at 4096 Hz since the
// last tick) has passed, the music ticks once and the remainder carries over. Polled, no timer interrupt.
void music_pump(void) BANKED {
    uint8_t t = TIMA_REG;
    if (t < FRAME_TIMA) return;
    tick();
    TIMA_REG = t - FRAME_TIMA;
}
