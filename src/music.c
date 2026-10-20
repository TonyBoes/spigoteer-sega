// Music engine glue (hUGEDriver) and the sound-effect engine. ROM bank 2: the driver code, the order tables and
// instruments (build/music_data.c) and this file. hUGEDriver reads patterns through plain pointers, so it only sees data in
// the bank it runs from, or in WRAM. Every tune's patterns sit in a ROM bank (the venue tunes' in bank 10, the jingles' in 24) and
// music_tick copies them into WRAM (mus_buf_a: the jingle or the level's venue tune; mus_buf_b: the show tune, copied once and kept),
// a slice per frame, before a tune starts. A streamed tune (tune_t.buf 3: the title, 20 orders and looping, bank 23; the credits tune,
// 10 orders, bank 22) has more orders than the buffer's four: it starts with the first 8 patterns and music_tick copies each later
// order over the slot of the order two before it as it plays (see tick); its harmony is in the same bank as its blob.
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
static uint8_t mus_active;       // the driver is running a tune: 1 a looping one, 2 a jingle (it stops after its frames)
static uint8_t muted;            // bit n: driver channel n muted (cache of the driver's mask)
static uint8_t loaded[3] = { TUNE_NONE, TUNE_NONE, TUNE_NONE };   // [buffer]: the tune whose patterns are in it
#define BUFI(b) ((b) == 3 ? 1 : (b))   // a streamed tune (buf 3) is in buffer A
static uint8_t ld_tune = TUNE_NONE;   // tune whose patterns are being copied (TUNE_NONE: no copy running)
static uint8_t ld_play;               // start it when the copy is done (else it is a preload)
static const uint8_t *groove;         // the running tune's drum loop (NULL: none)
static uint8_t swing;                 // the running tune's swing mask (0 none): src/music.h tune_t.groove
static uint8_t g_pos, g_cnt;          // groove row, frames until it advances
static uint8_t g_step;                // the groove drum struck last, its NR43 steps still to follow: drum id (1-6) << 2 | frames since the hit (1, 2); 0: none (one byte)
extern unsigned char hUGE_ticks_per_row, hUGE_tick, hUGE_row, hUGE_row_break, hUGE_next_order, hUGE_current_order;   // the driver's tempo, as hUGE_init set it (exported for this: CREDITS.md)
uint8_t music_fast;                   // 1: a venue tune plays one frame a row faster (story: TWIST_FAST_TUNE)
static uint8_t fast_now;              // the running tune plays fast
static uint16_t ld_pos;               // bytes copied so far
extern const uint16_t hUGE_note_table[];   // the driver's 72 periods (exported for this: CREDITS.md)
static const uint8_t *harm;           // the running tune's channel-1 harmony track (bank HARM_BANK; a streamed tune's: its blob's bank), NULL: none
static const uint8_t *h_ptr;          // its next event
static uint8_t h_inst[5];             // duty A, envelope A, duty B, envelope B (the track's header), then the track's ROM bank
static uint8_t h_note;                // the current event's note byte (HARM_REST: a rest)
static uint8_t h_rows, h_cnt;         // rows left in the event, frames left in the row
static uint8_t h_sound;               // 1: the current harmony note sounds on channel 1 (0: rest, or an effect took it)
#define LOAD_PLAY_BYTES    384     // per frame while the music waits for its patterns (no driver tick runs then)
#define LOAD_PRELOAD_BYTES  96     // per frame while the driver also ticks
#define FAST_TUNE(t) ((t) >= TUNE_VENUE0 && (t) < TUNE_COUNT)   // the tunes a story twist can speed up (not the credits tune)
#define FRAME_TIMA          69     // one frame (1/59.73 s) in 4096 Hz timer counts (68.6)

typedef struct { uint16_t freq; uint8_t len; int8_t slide; } sfx_step_t;   // CH1: 11-bit period; CH4: NR43
typedef struct { uint8_t ch; uint8_t duty; uint8_t env; uint8_t nsteps; const sfx_step_t *steps; } sfx_def_t;

// Periods are computed (period = 2048 - 131072/Hz); the effects were designed on paper and never listened to.
static const sfx_step_t s_fill[]   = { {1524, 24, 11} };                  // 250 Hz rising to ~490 Hz over the 24-frame fill
static const sfx_step_t s_launch[] = { {1950, 14, -45} };                 // fast downward sweep, 25% pulse, decaying
static const sfx_step_t s_catch[]  = { {1982, 3, 0}, {2004, 8, 0} };      // two high pings
static const sfx_step_t s_break[]  = { {0x35, 6, 0}, {0x45, 8, 0}, {0x55, 8, 0} };   // noise crash, falling in pitch
static const sfx_step_t s_serve[]  = { {1798, 3, 0}, {1849, 3, 0}, {1881, 3, 0}, {1923, 8, 0} };   // C5 E5 G5 C6
static const sfx_step_t s_coin[]   = { {1915, 5, 0}, {1949, 10, 0} };     // B5 then E6 a fourth up, the "ba-ding": the second note 5 frames after the first (it was 3: too close to hear as two)
static const sfx_step_t s_life[]   = { {1714, 8, 0}, {1650, 8, 0}, {1547, 16, -6} };   // G4 E4 C4, sagging
static const sfx_step_t s_shake[]  = { {0x2B, 2, 0}, {0x3B, 2, 0}, {0x2B, 2, 0}, {0x3B, 2, 0} };   // noise rattle
// extra life (owner request): a bright C-major fanfare above the serve's arpeggio, ending in a G6 / C7 shimmer that
// rings out: C6 E6 G6 C7, G6 C7, G6 C7 (held); 33 frames (0.55 s) on a 25% pulse
static const sfx_step_t s_extra[]  = { {1923, 3, 0}, {1949, 3, 0}, {1964, 3, 0}, {1985, 5, 0},
                                       {1964, 3, 0}, {1985, 3, 0}, {1964, 3, 0}, {1985, 10, 0} };
// Taiko Pour's drum, noise layer (channel 4, NR43 values; src/tk.c adds the pitched body on a pulse channel and keeps the
// tune's own groove, harmony and melody behind it: TAIKO_VARIANT, src/music.h). Counting the start frame DON lasts 8 frames
// and KA 4 in the T2 set (variant 0, the noise alone: a 2-frame knock then a boom, the clock sliding from 1024 Hz down to
// 146 Hz, 15-bit LFSR; KA a bright tick then a 7-bit crack at ~2 kHz, envelope 0xF1). In the D sets (1-3) the noise is only
// the layer under the pulse: DON a 2-frame knock, KA a tick and a crack, 3 frames (envelope 0xC1).
#if TAIKO_VARIANT == 0
#define TK_ENV 0xF1
static const sfx_step_t s_don[]    = { {0x62, 2, 0}, {0x81, 7, 1} };
static const sfx_step_t s_ka[]     = { {0x10, 2, 0}, {0x09, 3, 0} };
#else
#define TK_ENV 0xC1
static const sfx_step_t s_don[]    = { {0x62, 2, 0}, {0x74, 1, 0} };
static const sfx_step_t s_ka[]     = { {0x10, 2, 0}, {0x09, 2, 0} };
#endif
// Duke's engine (channel 4, envelope 0xD0: loud, no decay, ends 50 frames later like the throttle-twist tell): a
// tonal 7-bit-LFSR growl whose pitch climbs in five steps of 10 frames, 43 / 64 / 86 / 129 / 258 Hz.
// The whoosh (the bosses' and stories'; channel 4, 8 frames, envelope 0xA1: a rush of air): the
// noise clock climbs 128 -> 512 -> 2 kHz-ish in three steps (NR43 0x53, 0x33, 0x13) as the decay fades it out.
static const sfx_step_t s_whoosh[] = { {0x53, 3, 0}, {0x33, 3, 0}, {0x13, 2, 0} };
// The bar change's swish (src/pour.c bar_change; channel 4, 4 frames, envelope 0x41: volume 4 of 15, fading by 1 a step):
// a short quiet high hiss, 15-bit noise clock at ~65 kHz / 2 (NR43 0x12). The whoosh stays for the bosses and the stories.
static const sfx_step_t s_swish[]  = { {0x12, 4, 0} };
// The perfect pour's chime (story; src/mugs.c launch_mug plays it INSTEAD of SFX_LAUNCH when the release is perfect; channel 1, 15 frames,
// 50% pulse, envelope 0xA2: volume 10 of 15, a slow decay): a soft two-note "ting", G6 then D7 (a fifth up, ~1.57 kHz and ~2.35 kHz), the
// second note ringing out. Gentler and lower than the catch's two high pings and the coin's ba-ding; short enough to land on the release.
#if defined(POUR_SFX_A) || defined(POUR_SFX_B) || defined(POUR_SFX_C)
// Playtest candidates for a more celebratory perfect pour (owner 2026-10-19; make POUR_SFX=A|B|C). All channel 1, 12.5% pulse (the glassiest
// duty), envelope 0xD2 (volume 13, a slow decay: a little above the serve's 10 and the coin's 12). D major, a rising arpeggio to the octave:
// D6 F#6 A6 D7, the first note sweeping up into pitch over its 4 frames (the software slide: period +14 a frame).
//   A: 4+3+3+9 = 19 frames.   B: A with the last note shortened to 5, then D7 echoed twice at falling volume (0x82, 0x42): 25 frames.
//   C: A, plus a quiet 6-frame noise shimmer on channel 4 (s_shimmer, below), started with the first note.
#ifdef POUR_SFX_B
static const sfx_step_t s_perfect[] = { {1895, 4, 14}, {1959, 3, 0}, {1973, 3, 0}, {1992, 5, 0}, {1992, 4, 0}, {1992, 6, 0} };
#else
static const sfx_step_t s_perfect[] = { {1895, 4, 14}, {1959, 3, 0}, {1973, 3, 0}, {1992, 9, 0} };
#endif
#else
static const sfx_step_t s_perfect[] = { {1964, 3, 0}, {1992, 12, 0} };
#endif
#ifdef POUR_SFX_C
static const sfx_step_t s_shimmer[] = { {0x11, 3, 0}, {0x10, 3, 0} };           // channel 4: high bright noise, volume 5 fading out
static const sfx_def_t d_shimmer = { 3, 0x00, 0x51, 2, s_shimmer };
#endif
#ifdef POUR_STREAK
uint8_t pour_streak;                 // consecutive perfect pours + 1 (0: the last pour was not perfect), capped at POUR_STREAK_MAX + 1; src/mugs.c launch_mug
static uint16_t pour_up(uint16_t p) {   // the period p raised pour_streak-1 whole tones: the wave length x 0.8906 (2^-1/6 = 0.8909) each
    uint16_t d = 2048 - p;
    uint8_t n = pour_streak;
    while (--n) d = d - (d >> 3) + (d >> 6);
    return 2048 - d;
}
#endif
static const sfx_step_t s_rev[]    = { {0x4B, 10, 0}, {0x4A, 10, 0}, {0x3B, 10, 0}, {0x3A, 10, 0}, {0x39, 10, 0} };

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
    { 3, 0x00, TK_ENV, N(s_don),  s_don },
    { 3, 0x00, TK_ENV, N(s_ka),   s_ka },
    { 3, 0x00, 0xD0, N(s_rev),    s_rev },
    { 3, 0x00, 0xA1, N(s_whoosh), s_whoosh },
    { 3, 0x00, 0x41, N(s_swish),  s_swish },
#if defined(POUR_SFX_A) || defined(POUR_SFX_B) || defined(POUR_SFX_C)
    { 0, 0x00, 0xD2,  N(s_perfect), s_perfect },       // (the playtest candidate; two spaces so tests/test_harmony.py's row pattern sees only the shipped chime)
#else
    { 0, 0x80, 0xA2, N(s_perfect), s_perfect },
#endif
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
    if (ld_play > 1) ld_play = 0;
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
    uint8_t keep = hUGE_mute_mask & TK_HOLD;    // Taiko Pour's flags (src/tk.c) outlive a tune restart
    hUGE_init(tunes[tune].song);    // clears the driver's channel mute mask
    fast_now = music_fast && FAST_TUNE(tune);
    hUGE_ticks_per_row -= fast_now;   // (the groove below follows: one frame less a row)
    hUGE_mute_mask = keep | (muted = 1) | ((keep >> 5) & 2);     // channel 1 is harm_tick's: the driver leaves it alone (set directly: no note cut,
                                    // so an effect still sounding there plays on)
    if (tunes[tune].start) {        // a pickup: the first pass begins mid-song.  Make the driver believe it is on the last
                                    // tick of a row that ends in a jump to the start (order + 1, row + 1: how it stores them)
        hUGE_tick = hUGE_ticks_per_row - 1;
        hUGE_next_order = (tunes[tune].start >> 6) + 1;
        hUGE_row_break = (tunes[tune].start & 63) + 1;
        hUGE_dosound();             // that tick: the jump happens now, so the pump's first tick is the start row's tick 0
    }
    mus_active = 1 + !tunes[tune].loop;
    music_frames = 0;
    groove = tunes[tune].groove; g_pos = 0; g_cnt = 1; g_step = 0;   // the groove's first row falls on the song's first row
    swing = groove && groove[1] > 15 ? groove[1] : 0;       // (a groove's second byte: a tempo is at most 15, over that it is a swing mask)
    harm_off();
    harm = harm_tab[tune]; h_rows = 0; h_cnt = 1;           // so does the harmony's first event
    if (harm) {
        h_inst[4] = tunes[tune].buf == 3 ? tunes[tune].bank : HARM_BANK;
        mus_copy(h_inst[4], harm, h_inst, 4); h_ptr = harm + 4;   // (a tune with a pickup, start: gen_music stores its track from that row on)
    }
    mute_unless_sfx(3, 1);          // a sound effect that is still sounding keeps channel 4
}

static void begin_load(uint8_t tune, uint8_t play) {
    ld_tune = tune; ld_pos = 0; ld_play = play;
    loaded[BUFI(tunes[tune].buf)] = TUNE_NONE;
}

extern uint8_t story_on;
void music_play(uint8_t tune) BANKED {
    uint8_t buf, later = tune & MUSIC_LATER;        // MUSIC_LATER: an already-loaded tune starts with the next frame's tick, not this one's
    tune &= ~MUSIC_LATER;
    buf = tunes[tune].buf;
    if (story_on) tune_heard(tune);                 // the soundtrack player's unlocks (save.c), music on or off
    if (sound_on && cur_tune == tune && tunes[tune].loop && (mus_active || ld_tune == tune)
        && fast_now == (music_fast && FAST_TUNE(tune))) return;   // (a speed change restarts it)
    cur_tune = tune;
    if (!sound_on) return;
    if (loaded[BUFI(buf)] != tune || buf == 3) {      // (a streamed tune overwrites its own buffer as it plays: always copied afresh)
        if (ld_tune == tune) {                      // its preload is running: keep the bytes copied so far
            silence_music(); ld_tune = tune; ld_play = 1;
            return;
        }
        silence_music();
        begin_load(tune, 1);
        return;
    }
    if (ld_tune != TUNE_NONE && ld_play) ld_tune = TUNE_NONE;       // a tune that was still loading is superseded
    if (later && ld_tune == TUNE_NONE) {                            // a copy already done: the start waits one idle tick (tick(), ld_play 3 -> 2 -> start;
        ld_play = 3;                                                // the frame of a show starting or ending is already a busy one). It lives in tick()'s
        return;                                                     // no-load branch: the load frames (the dearest ones, test_music_cpu) pay nothing for it
    }
    if (ld_play > 1) ld_play = 0;                                   // (a start now cancels a waiting one)
    start_song(tune);
}

uint16_t music_tune_frames(uint8_t tune) BANKED { return tunes[tune].frames; }   // the credits roll's timeline is a share of this

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
    uint8_t env = v->def->env;
    v->freq = s->freq; v->slide = s->slide; v->left = s->len;
#ifdef POUR_STREAK
    if (v->def == &sfx_defs[SFX_PERFECT] && pour_streak > 1) v->freq = pour_up(v->freq);
#endif
#ifdef POUR_SFX_B
    if (v->def == &sfx_defs[SFX_PERFECT] && v->step >= 4) env = (v->step == 4) ? 0x82 : 0x42;   // the echoes
#endif
    if (v->def->ch == 0) {
        NR10_REG = 0;
        NR11_REG = v->def->duty;
        NR12_REG = env;
        NR13_REG = (uint8_t)v->freq;
        NR14_REG = 0x80 | (v->freq >> 8);
    } else {
        NR41_REG = 0;
        NR42_REG = v->def->env;
        NR43_REG = (uint8_t)v->freq;
        NR44_REG = 0x80;
    }
}

#ifdef POUR_SFX_C
static void shimmer_start(void) {       // under the chime; never over a channel-4 effect that is sounding (a crash, a rev...)
    voice_t *w = &voice[1];
    if (w->busy) return;
    w->def = &d_shimmer; w->step = 0; w->busy = 1;
    set_mute(3, 1);
    step_begin(w);
}
#endif

static void sfx_start(uint8_t id) {
    voice_t *v = &voice[sfx_defs[id].ch ? 1 : 0];
    if (v->busy && v->def == &sfx_defs[SFX_EXTRA] && id != SFX_EXTRA) return;   // the extra life is not cut short
    if (v->busy && id >= SFX_WHOOSH && sfx_defs[id].ch) return;     // the whoosh and the swish never cuts a crash or a drum off (channel 4)
    v->def = &sfx_defs[id];
    v->step = 0;
    v->busy = 1;
    set_mute(v->def->ch, 1);        // the driver lets go of the channel (and cuts its note) before we write
    step_begin(v);
#ifdef POUR_SFX_C
    if (id == SFX_PERFECT) shimmer_start();
#endif
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
static void groove_row(void) {      // (tick calls it on the frame the row counter runs out)
    uint8_t d;
    g_cnt = hUGE_ticks_per_row;      // this row's length, as the driver has just set it
    d = groove[2 + g_pos];
    if (++g_pos == groove[0]) g_pos = 0;
#ifdef POUR_SFX_C
    if (d && voice[1].busy && voice[1].def == &d_shimmer) voice[1].busy = 0;   // a groove drum cuts the shimmer short
#endif
    if (d && !voice[1].busy && !(hUGE_mute_mask & TK_NOGROOVE)) {
        const uint8_t *k = drum_kit[d - 1];
        NR41_REG = k[0]; NR42_REG = k[1]; NR43_REG = k[2]; NR44_REG = k[3];
        g_step = d << 2 | 1;
    }
}

// The hit's clock moves on the two frames after it (a kick's thump drops in pitch, a snare's crack becomes its body: the same
// steps the drum tables give hUGEDriver's pattern drums); an effect that took channel 4 meanwhile keeps it.
static void groove_step(void) {
    if (!voice[1].busy) NR43_REG = drum_kit[(g_step >> 2) - 1][3 + (g_step & 3)];
    if ((g_step & 3) == 2) g_step = 0;
    else g_step++;
}

static void harm_note(void) {
    uint16_t p = hUGE_note_table[h_note & 0x7F];
    const uint8_t *in = &h_inst[(h_note & 0x80) ? 2 : 0];
    if (hUGE_mute_mask & TK_NOHARM) return;      // Taiko Pour keeps the harmony quiet (the counters run on, h_sound stays 0)
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
            ev = harm_peek(h_inst[4], h_ptr);
            if (!(ev >> 8)) {                            // the end of the track: from the top, as the driver loops
                h_ptr = harm + 4;
                ev = harm_peek(h_inst[4], h_ptr);
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

static void sfx_dispatch(uint16_t req) {
    uint8_t id;
    sfx_req = 0;
    for (id = 1; req; id++, req >>= 1)              // ascending: on one channel the highest id requested wins
        if (req & 1) sfx_start(id);
}

// Copies the next slice of a tune's patterns to WRAM. Returns 1 when the tune started (this frame's tick is done).
static uint8_t load_step(void) {
    const tune_t *t = &tunes[ld_tune];
    uint16_t n = t->bytes - ld_pos;
    uint16_t cap = ld_play ? LOAD_PLAY_BYTES : LOAD_PRELOAD_BYTES;
    if (n > cap) n = cap;
    if (n) mus_copy(t->bank, t->blob + ld_pos, (t->buf == 2 ? mus_buf_b : mus_buf_a) + ld_pos, n);
    ld_pos += n;
    if (ld_pos >= t->bytes && !(ld_play && t->start && n)) {      // (a pickup tune starts a frame after its last slice: its start tick, one more driver tick, would make that frame 5 400 M-cycles)
        uint8_t done = ld_tune;
        loaded[BUFI(t->buf)] = done;
        ld_tune = TUNE_NONE;
        if (ld_play) { start_song(done); voice_tick(0); voice_tick(1); return 1; }
    }
    return 0;
}

// One frame of the music. A frame where no row begins does as little as it can: the groove and the harmony only act on
// their row counters running out (or, for the harmony, an effect on channel 1 / a note to bring back), and the sound
// effects' voices are only stepped while one is sounding.
static void tick(void) {
    uint16_t req = sfx_req;
    if (req) sfx_dispatch(req);
    if (ld_tune != TUNE_NONE) {
        if (load_step()) return;
    } else if (ld_play > 1) {
        if (--ld_play == 1) { start_song(cur_tune); voice_tick(0); voice_tick(1); return; }   // MUSIC_LATER's start (cur_tune is the tune asked for)
    } else if (mus_active && loaded[2] != TUNE_SHOW && sound_on)
        begin_load(TUNE_SHOW, 0);                                   // the show tune is copied once, while a level plays
    if (mus_active) {
        if (swing && !hUGE_tick)        // a swung tune: this row's length (bit n of the mask: the rows n mod 8 are a frame shorter)
            hUGE_ticks_per_row = tunes[cur_tune].song->tempo - fast_now - ((swing >> (hUGE_row & 7)) & 1);
        hUGE_dosound();
        if (hUGE_tick == STREAM_TICK && tunes[cur_tune].buf == 3) {  // a streamed tune: while order k plays (the driver counts orders by 2), order k+2 goes
            uint8_t r = hUGE_row - 2;                                 // over the buffer slot of order k-2, which is done: one slice on each of the order's
            if (r < STREAM_COPY_ROWS) {                               // rows 2 .. 2 + STREAM_COPY_ROWS - 1, on a plain tick (tick 1 is the row tick's own
                const tune_t *c = &tunes[cur_tune];                   // call, the dearest one: the copy made it 24 lines)
                uint8_t n = *c->song->order_cnt >> 1, k2 = (hUGE_current_order >> 1) + 2;
                if (k2 >= n) { if (c->loop) k2 -= n; else r = STREAM_COPY_ROWS; }   // the end: a looping tune wraps (order 0 over slot 0, ...), a jingle stops copying
                if (r < STREAM_COPY_ROWS) {
                    uint16_t o = (uint16_t)r * STREAM_SLICE;
                    mus_copy(c->bank, c->blob + (uint16_t)k2 * STREAM_ORDER_BYTES + o,
                             mus_buf_a + (uint16_t)(k2 & 3) * STREAM_ORDER_BYTES + o, STREAM_SLICE);
                }
            }
        }
        if (groove && !--g_cnt) groove_row();
        else if (g_step) groove_step();
        if (harm) {
            if (voice[0].busy || h_cnt == 1 || !h_sound) harm_tick();
            else h_cnt--;
        }
        music_frames++;
        if (mus_active > 1 && music_frames >= tunes[cur_tune].frames) {
            cur_tune = TUNE_NONE;
            silence_music();
        }
    }
    if (voice[0].busy) voice_tick(0);
    if (voice[1].busy) voice_tick(1);
}

// A menu screen's rebuild (LCD off, nothing else running) copies a tune's patterns into WRAM at once instead of 384 bytes
// a frame, so the tune starts with the screen's first pump and not four frames after it (music_play: the title tune after
// a game, a boss fight or the soundtrack player overwrote its buffer). Nothing to do when no such load is running.
void music_load_now(void) BANKED {
    while (ld_tune != TUNE_NONE && ld_play)
        if (load_step()) break;
}

// The game's frame tick (main.c, once per main loop). The timer's reload register TMA (0 at rest; the timer never overflows
// in a frame) holds two flags and a number so that the common frame reads one register: bit 0, a pump ticked in this pass (that
// was this frame's tick, so the loop's own is refused unless a half frame of real time has passed since it); bit 1, the pause
// menu is open (pause.c, as
// PAUSE_NR51): with the tune playing, bass and drums (channels 3, 4) are on the mix, the effects held: a request is dropped,
// and while an effect still owns channel 4 it stays off it (the bass alone; channel 1 is never on the pause mix).
void music_tick(void) BANKED {
    uint8_t f = TMA_REG;
    if (f) {
        if ((f & 2) && NR51_REG) {
            sfx_req = 0;
            NR51_REG = voice[1].busy ? 0x44 : 0xCC;
        }
        if (f & 1) {
            TMA_REG = f & 2;
            if (TIMA_REG < (f & 0xFC) + FRAME_TIMA / 2) return;   // (under half a frame since the pump's tick, that carried its lateness in TIMA: no tick, however it was timed)
        }
    }
    TIMA_REG = 0;        // (zeroed before the tick, not after: the pump's clock then runs from this tick's START, as music_pump's own remainder does; a tick's cost, 8 to 20 lines by the row, no longer moves the next pumped tick)
    tick();
}

// A long LCD-off load (the title's, the top-5 table's) is one main-loop pass of several frames, and the music only
// ticks once per pass: the tune stalled for those frames (owner: the title tune hitched at every attract switch).
// Such loads call this between their steps: when a frame's time (the timer, FRAME_TIMA counts at 4096 Hz since the
// last tick) has passed, the music ticks once and the remainder carries over. Polled, no timer interrupt.
void music_pump(void) BANKED {
    uint8_t t = TIMA_REG;
    if (t < FRAME_TIMA) return;
    if (*(volatile uint8_t *)0xFFF0) {                // the pause menu: the tune stands still when NR51 is 0 (a game clocked by music_frames), else as music_tick
        if (!NR51_REG) return;
        sfx_req = 0;
        NR51_REG = voice[1].busy ? 0x44 : 0xCC;
    }
    tick();
    t -= FRAME_TIMA;
    TIMA_REG = t;                                     // (the remainder carries over: it is how late this tick was)
    TMA_REG = (TMA_REG & 2) | 1 | (t & 0xFC);         // (bits 2-7: that lateness, rounded down to 4 counts: TIMA minus it is the real time since this tick, see music_tick)
}
