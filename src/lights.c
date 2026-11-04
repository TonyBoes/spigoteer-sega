// Show stage lighting, the wash (owner 2026-11-03: "The wash is good enough. No sweeps."), Color only. While a show plays, the stage's BG palettes
// 5 and 6 (text rows 1-4; the HUD, the bars and the performers are other palettes) go dark with a tint that steps with the show's beat. It fades in over
// LT_FADE frames when the show starts and out over the last LT_FADE. Everything is derived from the venue's stage colours through BRIGHTEN, so SCREEN
// BRIGHT still applies. Color at double speed only (DS_NOW: how the ROM runs a Color; see lights_frame). Its cost is kept out of the frame's logic: main.c runs it after the music tick, in the time a
// double-speed frame leaves idle, and a rebuild is ~30000 T-cycles, so it starts only before LT_LY_MAX.
//
// How it gets onto the screen: a stage palette that the mid-frame split reloads (level.c SPLIT_L_ / SPLIT_E_BCPS) is put back from its STG buffer by
// the VBlank (main.c split_vbl3), so the dim colours go into that buffer; one it does not reload (the Saloon's BG 6, a keg-only venue's both) is
// written by pal5_write (render.c) from SHOWLT_BUF, once a VBlank, while a show plays. Nothing is written to palette RAM from here.
#pragma bank 255
#include <stdint.h>
#include "showlights.h"
#include "music.h"                   // DS_NOW

#define LT_FADE   16          // frames of the fade in and out
#define LT_BLEND  16          // frames a tint takes to fade into the next (owner 2026-11-04: no hard cuts; a blend is a rebuild every frame, like the fades)
#define LT_BLEND  16          // frames a tint takes to fade into the next (owner 2026-11-04: no hard cuts); a blend rebuilds every frame, like a fade
#define LT_BEATS  2          // dance beats (DANCER_BEAT frames each) per tint

// THE TINT TABLE: the dark stage's colour is the lit colour times these (red, green, blue, in 32nds), one row per step of the show. Edit the colours here.
static const uint8_t lt_tint[4][3] = {
    { 20, 10, 18 },           // magenta
    { 10, 14, 22 },           // blue
    { 21, 15,  8 },           // amber
    { 10, 21, 11 },           // green (the owner's extra colour)
};

// a * b by shift and add (the library's multiply, divide and modulo cost thousands of cycles a call: the whole rebuild was 29000 T-cycles with them)
static uint16_t mul8(uint8_t a, uint8_t b) {
    uint16_t r = 0, x = a;
    while (b) { if (b & 1) r += x; x <<= 1; b >>= 1; }
    return r;
}
#define MUL8(a, b) mul8((a), (b))
#define LT_STEP   (DANCER_BEAT * LT_BEATS)     // frames per tint
#if LT_STEP != 24 || LT_FADE != 16 || LT_BLEND != 16 || LT_STEP % 8 || SHOW_FRAMES % 8
#error "lights_frame: the fades are 16 frames (>> 4), the steps and the show are whole eights of frames (the steady test counts show_timer's low bits)"
#endif

// The wash (main.c calls it after the music tick, and only on a frame whose line leaves time: LT_LY_MAX). main.c calls on every 8th frame of a show (the tint steps on one of those) and on every frame while SHOWLT_STAMP is 0 (a fade) or above 4 (a blend). A steady call is a few compares: the buffer is rebuilt only when the tint is not the one the stamp says it holds (stamp = tint + 1), in the fades (every frame, stamp 0) and when something
// overwrote the stamp (level.c obj_cols); the VBlank's write is asked for then and every 32 frames (the palette RAM is what the game's other code might have written over). A call main.c skips costs nothing:
// the next call (at most 8 frames on) finds the tint stale and builds.
void lights_frame(void) BANKED {
    uint16_t t = show_timer;
    uint8_t lvl = LT_FADE, i, s, e, u, k = LT_BLEND, n, m[3], *d, *b = (uint8_t *)SHOWLT_BUF;
    const uint8_t *tn, *tp;
    if (!DS_NOW) return;                                                   // (Color at double speed, as shipped: at normal speed the VBlank has no line to spare for the palette write, the copy list's drain starts on line 147 as it is)
    e = (uint8_t)((SHOW_FRAMES - t) >> 3);                                 // (eighths of frames into the show: 0..87)
    n = (uint8_t)((((uint16_t)e << 5) + ((uint16_t)e << 3) + ((uint16_t)e << 1) + e) >> 7);      // (the step's number: e / 3 for e < 88, without a divide: LT_STEP / 8 = 3)
    u = n & 3;                                                             // (its tint)
    if (n) k = (uint8_t)((SHOW_FRAMES - t) - (((uint16_t)n << 4) + ((uint16_t)n << 3)));   // (frames into this step: below LT_BLEND it is still blending in from the last tint)
    if (t > LT_FADE && t <= SHOW_FRAMES - LT_FADE && k >= LT_BLEND) {      // steady
        if (SHOWLT_STAMP == u + 1) {
            if (!((uint8_t)t & 31)) goto ask;
            return;
        }
        SHOWLT_STAMP = u + 1;
    } else {                                                               // a fade or a blend
        if (t > SHOW_FRAMES - LT_FADE) { SHOWLT_STAMP = 0; lvl = (uint8_t)(SHOW_FRAMES - t); }   // (in: 0 at the first frame; the buffer changes every frame, stamp 0)
        else if (t <= LT_FADE) { SHOWLT_STAMP = 0; lvl = (uint8_t)t - 1; }  // (out: the last frame of the show is the lit stage again)
        else {                                                             // (a blend alone builds every other frame: the step is under 2 in a channel, and the cost is half; the stamp is tint + 5 then, main.c calls every frame while it is above 4)
            if (!(k & 1) && SHOWLT_STAMP == u + 5) return;
            SHOWLT_STAMP = u + 5;
        }
    }
    tn = lt_tint[u];
    tp = lt_tint[(u - 1) & 3];
    for (i = 0; i < 3; i++) {
        uint8_t c = tn[i];
        if (k < LT_BLEND) c = (uint8_t)((MUL8(tp[i], LT_BLEND - k) + MUL8(c, k)) >> 4);   // (the tint part way from the last one's)
        m[i] = 32 - (uint8_t)(MUL8(32 - c, lvl) >> 4);                     // (the colour's factor in 32nds: lit 32 .. the tint's own at LT_FADE)
    }
    for (s = 0; s < 2; s++) {
        const uint16_t *q = venue.pal[s ? VENUE_PAL_STAGE_B : VENUE_PAL_STAGE_A];
        uint8_t slot = s ? BGPAL_STAGE_B : BGPAL_STAGE;
        d = b + (s << 3);
        for (i = 0; i < 4; i++) {
            uint16_t c = BRIGHTEN(q[i]);
            c = (MUL8(c & 31, m[0]) >> 5) | ((MUL8((c >> 5) & 31, m[1]) >> 5) << 5) | ((MUL8((c >> 10) & 31, m[2]) >> 5) << 10);
            d[i << 1] = c; d[(i << 1) | 1] = c >> 8;
        }
        CRITICAL {                                                        // (the covered palette's VBlank source: the split ISR reads these)
            if (SPLIT_ON && SPLIT_L_BCPS && ((SPLIT_L_BCPS >> 3) & 7) == slot) for (i = 0; i < 8; i++) SPLIT_STG[i] = d[i];
            if (SPLIT_ON == 3 && SPLIT_E_BCPS && ((SPLIT_E_BCPS >> 3) & 7) == slot) for (i = 0; i < 8; i++) SPLIT_E_STG[i] = d[i];
        }
    }
ask:
    CRITICAL { pal5_req |= SHOWLT_REQ; }                                  // (the VBlank writes the buffer: only when it is whole, the request comes last)
}
