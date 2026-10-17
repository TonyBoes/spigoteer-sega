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
//      While it is icy, little sparkles twinkle on the counter (the owner's request): at most SPARK_N (2) at a time, on
//      random even columns (the glint is drawn on the counter tile for even columns, gen_boss SPARK1-4 at BG 248-251; the
//      Yeti has no landing marker). A sparkle swaps its column's tile through the VBlank queue: 4 frames of glint (dot, cross,
//      big cross, dot), SPARK_STEP frames each, then the icy tile again; a new one may start every SPARK_EVERY frames,
//      one in two does (a hash of yeti_t: yeti_t * 37 + 11, no next_rand). Their state is 2 bytes of BOSS_OWN after the icy row: column / 2 + 16 * frame, 255 free.
//   3. THAW: the counter tiles swap back, half of them a frame (2 frames); then he walks again.
// FROZEN TAP (owner 2026-10-14: "the icy bar make mugs slide faster, but I don't see how that is a help or a hindrance"):
// while he is icy (YP_ICY), the tap on HIS bar is frozen. At that tap A starts a fill and the same frame the fill is
// cancelled (fill_timer / fill_stage zeroed from BEV_FRAME) with a thud: no mug is launched at him for the ice's 180
// frames (a held A does not start one again, only a fresh press would, and that is cancelled too). Other bars pour as
// usual, so the ice is the breather it was (he stands, no stomp; a mug launched before the blow still rides the ice at
// 3 px a frame) but the bartender has to spend it elsewhere and be back at his tap for the empties that now return at
// 1 px a frame. The banner "TAP FROZEN" shows for the first YETI_BANNER frames of the ice (the whoosh is the blow's cue).
// ENTRANCE (YP_ENTER, 'frost front'; yeti_t is its clock, no state of its own: BOSS_OWN is full): after the warm-up
// (BEV_ENTER) the igloo wall is bare (BS_JUMP + BP_HIDE, as Duke's entrance) while the counter frosts over left to right
// (ENT_FROST frames, a whoosh); at ENT_APPEAR he steps out of the frost in the BLOW pose (the thud; he catches nothing
// yet: BS_JUMP's rules do not apply once he is there, but nothing is poured in the intro); at ENT_THAW the frost thaws
// (2 frames) and at ENT_LAND he WALKS: intro_timer was held until then, so the intro's 90 frames and the first breath
// (YETI_EVERY away) start there. The player is not held: the bar plays as in any intro.
// Fair empties across the speed change: an empty must arrive at the tap end before the ice starts or ends, so its
// whole trip is at one speed and its arrival is the one the schedule booked. boss_window says so: walking, the frames
// left to the ice (special_t + the tell); in the tell and the thaw none (0); icy, the ice's frames left.
// A catch during the tell or the ice shows the GULP / WINCE poses as usual; the tell's pose comes back after the gulp.
#pragma bank 255
#include "boss.h"
#include "boss_yeti_art.h"
#include "boss_load.h"
#include "music.h"

extern uint8_t overlay_on;

#define BP_INHALE        BP_EXTRA        // gen_boss BOSSES yeti extra: INHALE, BLOW
#define BP_BLOW          (BP_EXTRA + 1)
#define YETI_EVERY       360             // frames of walking between two breaths
#define YETI_TELL         50             // the inhale (the frost creeping)
#define YETI_ICY         180             // the ice
#define YETI_BLOW         30             // the BLOW pose at the ice's start
#define YETI_CREEP        12             // frames per frost step
#define YETI_CREEP_COLS    4             // columns per frost step
#define ICE_COLS          18             // the counter's columns 0-17 (18-19: the keg)
#define SPARK_N            2             // sparkles at once
#define SPARK_EVERY        8             // frames between two chances for a new sparkle
#define SPARK_STEP         4             // frames per glint frame
#define YETI_BANNER       40             // frames of "TAP FROZEN" at the ice's start
#define ENT_FROST         30             // the entrance: the counter frosts over, 3 columns every 5 frames
#define ENT_APPEAR        40             // he steps out of the frost, BLOW
#define ENT_THAW          70             // the frost thaws, he stands
#define ENT_LAND          72             // WALK; the intro's 90 frames start
#if BOSS_ART_ICE > BOSS_ICE_MAX
#error "the Yeti's icy counter tiles"
#endif

enum { YP_WALK, YP_TELL, YP_ICY, YP_THAW, YP_ENTER };

uint8_t yeti_phase;            // YP_* (tests; YP_ENTER: the entrance, yeti_t its frame)
uint8_t boss_icy;              // frames of ice left (spec 3.7's test hook)
uint8_t yeti_cols;             // counter columns frosted (from column 0)
uint8_t yeti_t;                // frames in the phase (tests)
#define ice_row BOSS_OWN       // [ICE_COLS] the icy counter row (the venue's counter tiles mapped to their icy copies)
#define spark ((uint8_t *)BOSS_OWN + ICE_COLS)   // [SPARK_N] column / 2 + 16 * glint frame; SPARK_FREE: none
#define SPARK_FREE 255
#if ICE_COLS + SPARK_N > BOSS_OWN_N
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

static void spark_clear(void) {                  // no sparkles: their columns' entries in ice_row are icy again (the
    uint8_t k;                                   // caller puts the venue's tiles back, or the thaw does)
    for (k = 0; k != SPARK_N; k++) {
        if (spark[k] != SPARK_FREE) ice_row[(spark[k] & 15) << 1] = BOSS_ICE_BG;
        spark[k] = SPARK_FREE;
    }
}

static void thaw_all(void) {                     // every icy column back at once (a reset, the outro)
    counter_put(0, yeti_cols, 0);
    yeti_cols = 0;
    spark_clear();
}

// A sparkle's column shows glint frame f (or the icy tile again: f 4): ice_row's entry is the queue's source.
static void spark_show(uint8_t c, uint8_t f) {
    ice_row[c] = f < BOSS_ART_SPARK ? BOSS_MARK_BG + f : BOSS_ICE_BG;
    if (LCDC_REG & LCDCF_ON) vq_add(0, ice_row + c, c, counter_y(), 1); else vram_put(c, counter_y(), ice_row + c, 1);
}

static void spark_frame(void) {                  // the ice's sparkles, one frame (yeti_t: frames since the ice began)
    uint8_t k, v, c;
    for (k = 0; k != SPARK_N; k++) {
        v = spark[k];
        if (v == SPARK_FREE || yeti_t % SPARK_STEP) continue;
        v += 16;                                 // the next glint frame, or (4) the icy tile again
        c = (v & 15) << 1;
        spark_show(c, v >> 4);
        spark[k] = (v >> 4) < BOSS_ART_SPARK ? v : SPARK_FREE;
    }
    if (yeti_t % SPARK_EVERY) return;
    v = yeti_t * 37 + 11;                        // a tiny hash of the ice's frame count (not next_rand: the game's random
    if (v & 16) return;                          // sequence stays as it was): one chance in two, and the column
    for (k = 0; k != SPARK_N; k++) if (spark[k] == SPARK_FREE) {
        c = (((uint8_t)(v * 5) >> 3) % (ICE_COLS / 2)) << 1;     // (a column already glinting is not icy-plain: skipped)
        if (ice_row[c] != BOSS_ICE_BG) return;
        spark[k] = c >> 1;
        spark_show(c, 0);
        return;
    }
}

static void walk_window(void) {
    boss_window = boss_special_t + YETI_TELL;
}

static void to_walk(void) {
    if (yeti_phase == YP_ENTER) return;          // (the entrance ends it: ent_frame)
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
    SFX(SFX_WHOOSH);
    show_note("TAP FROZEN");          // (a note: the game goes on, the bars stay in view)
    boss_xpose = BP_BLOW;
    boss_sip_t = 255;                            // a held empty may go at once (if the schedule allows)
    boss_window = YETI_ICY;
}

// The entrance's frame (BEV_INTRO, while intro_timer runs): yeti_t counts it.
static void ent_frame(void) {
    uint8_t t = yeti_t;
    if (t < ENT_LAND) intro_timer = INTRO_FRAMES;     // (held: the intro's 90 frames start when he walks)
    if (t == 0) SFX(SFX_WHOOSH);
    if (t < ENT_FROST) {
        if (!(t % 5)) frost_to(yeti_cols + 3);
    } else if (t == ENT_FROST) frost_to(ICE_COLS);
    if (t >= ENT_FROST && t < ENT_THAW) spark_frame();
    if (t == ENT_APPEAR) {
        boss_xpose = BP_BLOW;                         // (boss_state stays BS_ENTER until he walks: nothing is caught, the engine's fight starts then)
        boss_to_bar(boss_bar, 16);                    // his BG body, the topper
        SFX(SFX_SHAKE);
    }
    if (t == ENT_THAW) {
        spark_clear();
        counter_put(0, ICE_COLS / 2, 0);
        boss_xpose = 0;
    }
    if (t == ENT_THAW + 1) { counter_put(ICE_COLS / 2, ICE_COLS - ICE_COLS / 2, 0); yeti_cols = 0; }
    if (t == ENT_LAND) {
        intro_timer = INTRO_FRAMES - 1;               // (as the level's first frame leaves it)
        yeti_phase = YP_WALK;
        boss_state = BS_WALK;                         // (E9: the entrance is over: boss.c starts the fight)
        to_walk();
        return;
    }
    yeti_t++;
}

uint8_t boss_yeti(uint8_t ev, uint8_t arg) BANKED {
    uint8_t k;
    (void)arg;
    switch (ev) {
    case BEV_SET:
        boss_art_set();
        yeti_cols = 0;
        spark[0] = spark[1] = SPARK_FREE;
        yeti_phase = YP_WALK;
        /* fall through */
    case BEV_RESET:
        if (yeti_cols) thaw_all();
        if (yeti_phase == YP_ENTER) { boss_state = BS_JUMP; boss_xpose = BP_HIDE; boss_window = 0; break; }   // (the entrance: not on his bar yet)
        if (yeti_phase == YP_ICY && yeti_t < YETI_BANNER) overlay_on = 0;   // (a life lost within the ice's first frames: its banner)
        yeti_phase = YP_WALK;
        to_walk();
        break;
    case BEV_LOAD:
        boss_art_load();
        set_bkg_data(BOSS_ICE_BG, BOSS_ART_ICE, boss_ice_tiles);
        set_bkg_data(BOSS_MARK_BG, BOSS_ART_SPARK, boss_spark_tiles);
        for (k = 0; k != ICE_COLS; k++) {
            uint8_t t = venue.bar_map[BAR_COUNTER_DROW * 20 + k], j;
            ice_row[k] = t;
            for (j = 0; j != BOSS_ART_ICE; j++) if (boss_ice_src[j] == t) ice_row[k] = BOSS_ICE_BG + j;
        }
        yeti_cols = 0;                           // (the level load drew the venue's counter)
        spark[0] = spark[1] = SPARK_FREE;
        break;
    case BEV_ENTER:                              // E9: the warm-up is over (his bar is empty): the frost front
        yeti_phase = YP_ENTER; yeti_t = 0;
        return 1;
    case BEV_INTRO:
        if (yeti_phase == YP_ENTER) ent_frame();
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
            if (yeti_t == YETI_BANNER) end_note();
            if (bar == boss_bar && fill_timer) {  // the frozen tap: nothing is poured at him
                if (fill_timer == 1) SFX(SFX_SHAKE);
                fill_timer = 0; fill_stage = 0;
            }
            boss_window = --boss_icy;
            if (boss_icy) spark_frame();
            else {                               // the thaw: half the counter now, half next frame
                spark_clear();
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
