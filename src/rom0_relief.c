// ROM0 relief (asm pass batch 2): code that ran from ROM0 and is not hot enough to deserve it, moved to bank 21 (pinned: it is
// the roomy one). Behaviour is unchanged; each is called through the banked trampoline.
#pragma bank 21
#include <gb/gb.h>
#include <stdint.h>
#include "game.h"

extern uint8_t story_arc;
extern uint32_t score, extra_at;
extern uint8_t score_digits[6];
extern uint8_t hud_dirty;
void prep_hud(void);

static const uint8_t dancer_x[NUM_DANCERS] = { 24, 72, 120 };   // screen x of the left edge, across the stage
#define DANCER_OAM_Y (STAGE_LAST_ROW * 8 - 24 + 16)   // OAM y of a dancer's top entries: art 24 px tall, feet on the platform

// What the dancer entries must show: 0x80 | dance frame << 3 | bit k: dancer k is on stage. They pop in one
// after another at the start of the show and leave in the same order at the end.
static uint8_t dancer_look(void) {
    uint16_t left = show_timer, elapsed = SHOW_FRAMES - show_timer;
    uint8_t sig = 0x80 | (dancer_frame << 3);
    if (elapsed >= 1 * DANCER_STAGGER && left > 1 * DANCER_STAGGER) sig |= 1;
    if (elapsed >= 2 * DANCER_STAGGER && left > 2 * DANCER_STAGGER) sig |= 2;
    if (elapsed >= 3 * DANCER_STAGGER && left > 3 * DANCER_STAGGER) sig |= 4;
    return sig;
}

// OAM 28..39: the performers on the platform, 4 entries each (16x24 art, feet on the top of row STAGE_LAST_ROW). Their
// tiles come from the venue's show table (tools/gen_art.py show_tiles): a dance shows row dancer_frame for all three,
// a band shows performer k's own row 2k + (beat & 1) (pose A on even beats, B on odd ones).
static void draw_dancers(uint8_t sig) {
    OAM_item_t *o = shadow_OAM + OAM_DANCERS;
    const uint8_t *t;
    uint8_t k, flags, x;
    flags = is_cgb ? OBJPAL_DANCER : 0;
    for (k = 0; k < NUM_DANCERS; k++, o += 4) {
        if (!(sig & (1 << k))) { o[0].y = o[1].y = o[2].y = o[3].y = 0; continue; }
        t = venue.show_tile[(venue.show_band & 1) ? (k << 1) | (dancer_frame & 1) : dancer_frame];
        x = dancer_x[k] + 8;
        o[0].y = DANCER_OAM_Y;      o[0].x = x;     o[0].tile = OBJ_DANCER + t[0]; o[0].prop = flags;
        o[1].y = DANCER_OAM_Y;      o[1].x = x + 8; o[1].tile = OBJ_DANCER + t[1]; o[1].prop = flags;
        o[2].y = DANCER_OAM_Y + 16; o[2].x = x;     o[2].tile = OBJ_DANCER + t[2]; o[2].prop = flags;
        o[3].y = DANCER_OAM_Y + 16; o[3].x = x + 8; o[3].tile = OBJ_DANCER + t[3]; o[3].prop = flags;
    }
}


// One call a frame while the show runs (render.c draw_stage_fx): compute what the dancer entries must show and rewrite them only
// when that changed (dancer_sig).
void dancers_step(void) BANKED {
    uint8_t sig = dancer_look();
    if (sig == dancer_sig) return;               // the entries already show exactly this
    dancer_sig = sig;
    draw_dancers(sig);
}

// score as 32-bit total (for tests) plus decimal digits (no division in VBlank)
void add_score(uint16_t n) BANKED {
    // The HUD digits are kept in step with `score`. Digits come off n by repeated subtraction of constants: SDCC's
    // 16-bit divide costs ~600 cycles a call, and a patron serve (this, plus the tip roll, plus a redraw) is one of
    // the heaviest frames of the game.
    uint8_t d4 = 0, d3 = 0, d2 = 0, d1 = 0, d, carry;
    if (story_arc & 6) n = story_pts(n);              // a STORY run's difficulty scales every score as it is added (save.c)
    score += n;
    if (extra_at && score >= extra_at) extra_life();   // ARCADE / CLASSIC (story.c)
    while (n >= 10000) { n -= 10000; d4++; }
    while (n >= 1000)  { n -= 1000;  d3++; }
    while (n >= 100)   { n -= 100;   d2++; }
    d = (uint8_t)n;                                  // now n < 100
    while (d >= 10) { d -= 10; d1++; }
    // digit by digit from the ones (score_digits[5]) up; [0] is the 100000s
    d += score_digits[5];
    carry = d >= 10; score_digits[5] = carry ? d - 10 : d;
    d = score_digits[4] + d1 + carry;
    carry = d >= 10; score_digits[4] = carry ? d - 10 : d;
    d = score_digits[3] + d2 + carry;
    carry = d >= 10; score_digits[3] = carry ? d - 10 : d;
    d = score_digits[2] + d3 + carry;
    carry = d >= 10; score_digits[2] = carry ? d - 10 : d;
    d = score_digits[1] + d4 + carry;
    carry = d >= 10; score_digits[1] = carry ? d - 10 : d;
    d = score_digits[0] + carry;
    score_digits[0] = d >= 10 ? d - 10 : d;
    hud_dirty |= HUD_SCORE;
    prep_hud();
}

