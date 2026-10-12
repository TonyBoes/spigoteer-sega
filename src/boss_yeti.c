// The Yeti, the igloo's boss (docs/minigames_bosses.md 3.7; art approved 2026-10-11, look 1 round 2).
// His row is boss.c rows[4]: 32 px, step 100, push 8, gulp 30, hands 2, sip 60, meter 12.
//
// His special, icy breath, every YETI_EVERY frames of walking (boss_special_t counts them down):
//   1. TELL, YETI_TELL frames: the INHALE pose (cheeks puffed), he stands (BS_TELL); frost creeps along his bar's
//      counter from his side (the left end), YETI_CREEP_COLS columns every YETI_CREEP frames, through the VBlank queue:
//      the counter row's tiles swap to their icy copies (gen_boss `ice`: BG 246.., a light streak pattern; on DMG it
//      reads by pattern, not only by colour). All ICE_COLS counter columns are icy when the tell ends.
//   2. ICY, YETI_ICY frames (boss_icy counts them): the BLOW pose for YETI_BLOW frames, then he stands (BS_SPECIAL, no
//      stomp); on his bar full mugs slide 3 px a frame and empties 1 px a frame (boss_fast_full / boss_fast_empty: your
//      drinks reach him sooner, his empties come back sooner). A held empty may go at once (its sip wait is over).
//   3. THAW: the counter tiles swap back, half of them a frame (2 frames); then he walks again.
// Fair empties across the speed change: an empty must arrive at the tap end before the ice starts or ends, so its
// whole trip is at one speed and its arrival is the one the schedule booked. boss_window says so: walking, the frames
// left to the ice (special_t + the tell); in the tell and the thaw none (0); icy, the ice's frames left.
// A catch during the tell or the ice shows the GULP / WINCE poses as usual; the tell's pose comes back after the gulp.
#pragma bank 255
#include "boss.h"
#include "boss_yeti_art.h"
#include "boss_load.h"

#define BP_INHALE        BP_EXTRA        // gen_boss BOSSES yeti extra: INHALE, BLOW
#define BP_BLOW          (BP_EXTRA + 1)
#define YETI_EVERY       360             // frames of walking between two breaths
#define YETI_TELL         50             // the inhale (the frost creeping)
#define YETI_ICY         180             // the ice
#define YETI_BLOW         30             // the BLOW pose at the ice's start
#define YETI_CREEP        12             // frames per frost step
#define YETI_CREEP_COLS    4             // columns per frost step
#define ICE_COLS          18             // the counter's columns 0-17 (18-19: the keg)
#if BOSS_ART_ICE > BOSS_ICE_MAX
#error "the Yeti's icy counter tiles"
#endif

enum { YP_WALK, YP_TELL, YP_ICY, YP_THAW };

uint8_t yeti_phase;            // YP_* (tests)
uint8_t boss_icy;              // frames of ice left (spec 3.7's test hook)
uint8_t yeti_cols;             // counter columns frosted (from column 0)
static uint8_t yeti_t;         // frames in the phase
#define ice_row BOSS_OWN       // [ICE_COLS] the icy counter row (the venue's counter tiles mapped to their icy copies)
#if ICE_COLS > BOSS_OWN_N
#error "the Yeti's icy row: BOSS_OWN_N"
#endif

static uint8_t counter_y(void) {
    return BAR_COUNTER_ROW(boss_bar);
}

// Counter columns c0..c0+n-1 to icy (ice) or back to the venue's tiles: the VBlank queue (LCD on) or VRAM.
static void counter_put(uint8_t c0, uint8_t n, uint8_t ice) {
    const uint8_t *src = ice ? ice_row + c0 : venue.bar_map + BAR_COUNTER_DROW * 20 + c0;
    if (!n) return;
    if (LCDC_REG & LCDCF_ON) vq_add(0, src, c0, counter_y(), n); else vram_put(c0, counter_y(), src, n);
}

static void frost_to(uint8_t cols) {             // the frost reaches `cols` columns
    if (cols > ICE_COLS) cols = ICE_COLS;
    if (cols > yeti_cols) { counter_put(yeti_cols, cols - yeti_cols, 1); yeti_cols = cols; }
}

static void thaw_all(void) {                     // every icy column back at once (a reset, the outro)
    counter_put(0, yeti_cols, 0);
    yeti_cols = 0;
}

static void walk_window(void) {
    boss_window = boss_special_t + YETI_TELL;
}

static void to_walk(void) {
    yeti_phase = YP_WALK; yeti_t = 0;
    boss_special_t = YETI_EVERY;
    boss_fast_full = boss_fast_empty = 0;
    boss_icy = 0;
    boss_xpose = 0;
    if (boss_state == BS_TELL || boss_state == BS_SPECIAL) boss_state = BS_WALK;
    walk_window();
}

static void to_tell(void) {
    yeti_phase = YP_TELL; yeti_t = 0;
    boss_special_t = 0;
    boss_window = 0;
    boss_xpose = BP_INHALE;
    frost_to(YETI_CREEP_COLS);
}

static void to_icy(void) {
    yeti_phase = YP_ICY; yeti_t = 0;
    frost_to(ICE_COLS);
    boss_icy = YETI_ICY;
    boss_fast_full = boss_fast_empty = 1;
    boss_xpose = BP_BLOW;
    boss_sip_t = 255;                            // a held empty may go at once (if the schedule allows)
    boss_window = YETI_ICY;
}

uint8_t boss_yeti(uint8_t ev, uint8_t arg) BANKED {
    uint8_t k;
    (void)arg;
    switch (ev) {
    case BEV_SET:
        boss_art_set();
        yeti_cols = 0;
        /* fall through */
    case BEV_RESET:
        if (yeti_cols) thaw_all();
        to_walk();
        break;
    case BEV_LOAD:
        boss_art_load();
        set_bkg_data(BOSS_ICE_BG, BOSS_ART_ICE, boss_ice_tiles);
        for (k = 0; k != ICE_COLS; k++) {
            uint8_t t = venue.bar_map[BAR_COUNTER_DROW * 20 + k], j;
            ice_row[k] = t;
            for (j = 0; j != BOSS_ART_ICE; j++) if (boss_ice_src[j] == t) ice_row[k] = BOSS_ICE_BG + j;
        }
        yeti_cols = 0;                           // (the level load drew the venue's counter)
        break;
    case BEV_TELL:
        if (yeti_phase == YP_WALK) to_tell();
        break;
    case BEV_OUTRO:
        thaw_all();
        boss_fast_full = boss_fast_empty = 0;
        boss_icy = 0;
        break;
    case BEV_FRAME:
        yeti_t++;
        switch (yeti_phase) {
        case YP_WALK:
            if (boss_special_t && !--boss_special_t) to_tell();
            else walk_window();
            break;
        case YP_TELL:
            if (yeti_t >= YETI_TELL) to_icy();
            else if (!(yeti_t % YETI_CREEP)) frost_to(yeti_cols + YETI_CREEP_COLS);
            break;
        case YP_ICY:
            if (yeti_t == YETI_BLOW) boss_xpose = 0;
            boss_window = --boss_icy;
            if (!boss_icy) {                     // the thaw: half the counter now, half next frame
                yeti_phase = YP_THAW; yeti_t = 0;
                boss_fast_full = boss_fast_empty = 0;
                boss_window = 0;
                counter_put(0, ICE_COLS / 2, 0);
            }
            break;
        case YP_THAW:
            counter_put(ICE_COLS / 2, ICE_COLS - ICE_COLS / 2, 0);
            yeti_cols = 0;
            to_walk();
            break;
        }
        if (yeti_phase == YP_TELL && boss_state == BS_WALK) boss_state = BS_TELL;   // (a gulp is over: he stands again)
        else if (yeti_phase >= YP_ICY && (boss_state == BS_WALK || boss_state == BS_TELL)) boss_state = BS_SPECIAL;
        break;
    }
    return 0;
}
