// ROM0 relief (asm pass batch 2): code that ran from ROM0 and is not hot enough to deserve it, moved to bank 21 (pinned: it is
// the roomy one). Behaviour is unchanged; each is called through the banked trampoline.
#pragma bank 21
#include <gb/gb.h>
#include <stdint.h>
#include "game.h"
#include "scratch.h"

extern uint8_t story_arc;
extern uint32_t score, extra_at;
extern uint8_t score_digits[6];
extern uint8_t hud_dirty;

static const uint8_t dancer_x[NUM_DANCERS] = { 24, 72, 120 };   // screen x of the left edge, across the stage
static const uint8_t dancer_pal[NUM_DANCERS] = { OBJPAL_DANCER, 4, 3 };   // their OBJ palettes when each wears her own (game.h OBJX_ON)
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
    for (k = 0; k < NUM_DANCERS; k++, o += 4) {
        if (!(sig & (1 << k))) { o[0].y = o[1].y = o[2].y = o[3].y = 0; continue; }
        flags = is_cgb ? (OBJX_ON ? dancer_pal[k] : OBJPAL_DANCER) : 0;     // (three show palettes: OBJ 5, 4, 3 left to right, game.h OBJX_*)
        t = venue.show_tile[(venue.show_band & 1) ? (k << 1) | (dancer_frame & 1) : dancer_frame];
        x = dancer_x[k] + 8;
        o[0].y = DANCER_OAM_Y;      o[0].x = x;     o[0].tile = OBJ_DANCER + t[0]; o[0].prop = flags;
        o[1].y = DANCER_OAM_Y;      o[1].x = x + 8; o[1].tile = OBJ_DANCER + t[1]; o[1].prop = flags;
        o[2].y = DANCER_OAM_Y + 16; o[2].x = x;     o[2].tile = OBJ_DANCER + t[2]; o[2].prop = flags;
        o[3].y = DANCER_OAM_Y + 16; o[3].x = x + 8; o[3].tile = OBJ_DANCER + t[3]; o[3].prop = flags;
    }
}


// The dance's steps (tools/gen_art.py step_rows: the venue's rows 4-5, venue.show_tile[4]): byte 0 the loop's length | (intro frame + 1) << 4, bytes 1-2 the loop's frames, 2 bits each.
// A show starts on its intro frame, if the venue has one, else on loop step 0; every DANCER_BEAT after, the next loop step (the intro is not in the loop). A band's frames just count (render.c).
static uint8_t loop_frame(uint8_t i) {
    const uint8_t *t = venue.show_tile[4];
    return (t[1 + (i >> 2)] >> ((i & 3) << 1)) & 3;
}

void dance_start(void) BANKED {                 // a show starts (show.c start_show)
    const uint8_t *t = venue.show_tile[4];
    DANCE_STEP = 0;
    dancer_frame = 0;
    dance_tick = 0;
    if (venue.show_band & 1) return;
    if (t[0] >> 4) { dancer_frame = (t[0] >> 4) - 1; DANCE_STEP = 255; }      // (the intro: the loop's step 0 follows it)
    else dancer_frame = loop_frame(0);
}

void dance_next(void) BANKED {                  // a dance beat (main.c)
    uint8_t i = DANCE_STEP + 1;
    if (OBJX_F & 0xC0) {                        // (the three show palettes' setup, level.c obj_stage: one step a frame for two frames, main.c calls here every frame while dance_tick stays at the beat; the dance itself waits, its count goes on)
        obj_stage();
        dance_tick = (OBJX_F & 0xC0) ? DANCER_BEAT : 3;
        if (!(OBJX_F & 0xC0)) dancer_sig = 0;   // (the dancers up since the start frame wear OBJ 5 still: drawn again with their own palettes)
        return;
    }
    if (venue.show_band & 0x10) { show_ext_next(); return; }    // (per-performer loops: src/show_ext.c)
    if (venue.show_band & 1) { dancer_frame = (dancer_frame + 1) & 3; return; }
    if (i >=(venue.show_tile[4][0] & 15)) i = 0;
    DANCE_STEP = i;
    dancer_frame = loop_frame(i);
}

// One call a frame while the show runs (render.c draw_stage_fx): compute what the dancer entries must show and rewrite them only
// when that changed (dancer_sig).
void dancers_step(void) BANKED {
    uint8_t sig = dancer_look(), k;
    if (venue.show_band & 0x10) {                // (per-performer loops, src/show_ext.c: one performer a frame; dancer_sig bits 5-6 = how many are drawn, bit 7 clear until all three are, so render.c calls on)
        k = dancer_sig;
        if ((k & 0x1F) != (sig & 0x1F)) k = sig & 0x1F;          // (a new look: from performer 0)
        else if (k & 0x80) return;               // all three show exactly this
        show_ext_draw(sig, (k >> 5) & 3);
        k += 0x20;
        dancer_sig = (k & 0x60) == 0x60 ? k | 0x80 : k;
        return;
    }
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


// The bars' two wall rows each, all 20 columns, tiles and (Color) attributes, straight to VRAM: render.c write_all_bars (LCD off, level start; it was a
// static write_span in ROM0). sh_rows: [0] tile ids, [1] attributes, row (bar << 1) | r, 32 wide.
extern uint8_t sh_rows[2][NUM_BARS * 2][32];
void write_all_spans(void) BANKED {
    uint8_t b, r, y;
    for (b = 0; b < NUM_BARS; b++) for (r = 0; r < 2; r++) {
        y = BAR_TOP_ROW(b) + r;
        vram_put(0, y, &sh_rows[0][(b << 1) | r][0], 20);
        if (is_cgb) {
            VBK_REG = VBK_BANK_1;
            vram_put(0, y, &sh_rows[1][(b << 1) | r][0], 20);
            VBK_REG = VBK_BANK_0;
        }
    }
}

// The copy list's dirty bookkeeping, cleared at a level / screen start (most of render.c clear_dirty, which was all in ROM0).
extern uint8_t dirty_x0[NUM_BARS], dirty_x1[NUM_BARS], attr_x0[NUM_BARS], attr_x1[NUM_BARS];
extern uint8_t quick_list[MAX_PATRONS], quick_n, quick_on[MAX_PATRONS];
void clear_dirty_lists(void) BANKED {         // (render.c clear_dirty: the rest of it)
    uint8_t b;
    while (quick_n) quick_on[quick_list[--quick_n]] = 0;
    for (b = 0; b < NUM_BARS; b++) { dirty_x0[b] = 255; dirty_x1[b] = 0; attr_x0[b] = 255; attr_x1[b] = 0; }
}

// Every bar's wall rows composed and written, LCD off only (it was render.c's, in ROM0).
extern uint8_t cz_x0, cz_x1, cz_attrs;
void compose_bar(uint8_t b);
void write_all_bars(void) BANKED {
    uint8_t b;
    cz_x0 = 0; cz_x1 = 20; cz_attrs = is_cgb;
    for (b = 0; b < NUM_BARS; b++) compose_bar(b);
    write_all_spans();
    clear_dirty();
}

uint8_t glass_step(uint8_t i);                   // (mugs.c)

// glass pieces keep falling while the rest of the picture is frozen
void update_glass(void) BANKED {
    uint8_t i, st, live = 0;
    for (i = 0; i != MAX_MUGS; i++) {
        st = mug_state[i];
        if (st == MUG_FREE) continue;
        if (st == MUG_BREAKING) live += glass_step(i);
        else live++;
    }
    mugs_live = live;
}
