// Leo the Lion, the jungle zoo's boss (docs/minigames_bosses.md 3.11; art approved 2026-10-11, round 2: the patron lion
// scaled up, crowned). His row is boss.c rows[8]: 32 px, step 80, push 8, gulp 30, hands 2, sip 60, meter 14.
//
// His roar, every LEO_EVERY frames of walking (boss_special_t counts them down):
//   1. TELL, LEO_TELL frames: the INHALE pose (the mane puffed out), "!!" (gen_boss leo `tiles` BANG at BG 246-247) in
//      the column right of him on his bar's wall rows (boss_cols[4]: a 32 px boss's 5th column is his special's, so
//      it is stamped with him in his palette and follows a push-back); he stands (BS_TELL).
//   2. ROAR, LEO_ROAR frames: the ROAR pose and SFX_SHAKE; he stands (BS_SPECIAL). On its first frame he walks the
//      patron list once:
//      - every regular walker all on the screen (on every bar) is pushed back LEO_PUSH px: the push-back's own movement
//        (PATRON_PUSHED, 1 px a frame) with no mug in his hand, never past ENTRY_X (where a push would serve him), so no
//        score, no served count, no thirst; when the push is used up he walks on (leo.mask: patrons.c would start his
//        drink, and he has none);
//      - every drinker still in his minimum drink (DRINK_MIN) finishes it now: his empty goes when the fair schedule
//        allows (patrons.c finished_step / empty_may_go: next_arrival, empty_gap), the wind-up first, as always;
//      - Leo's own held empty may go at once (boss_sip_t), by boss_send: the same schedule.
//      So the wave of empties a roar sets off arrives at the tap end >= empty_gap apart, whoever sent them.
//   3. The "!!" goes, he walks again, LEO_EVERY to the next roar.
// A catch during the tell or the roar shows GULP / WINCE as usual and his pose comes back after it; a push-back takes
// the "!!" along. A lost life ends a roar (he starts over walking).
// Test hooks (WRAM: his state is the struct leo_t in BOSS_OWN, not variables of its own): leo.phase is the spec's
// boss_roar (0 walking, 1 the tell, 2 the roar).
#pragma bank 255
#include "boss.h"
#include "boss_leo_art.h"
#include "boss_load.h"
#include "music.h"

#define BP_INHALE   BP_EXTRA         // gen_boss BOSSES leo extra: INHALE, ROAR
#define BP_ROAR     (BP_EXTRA + 1)
#define LEO_EVERY   420              // frames of walking between two roars
#define LEO_TELL     60              // the inhale and the "!!"
#define LEO_ROAR     30              // the roar
#define LEO_PUSH     16              // px every walker is pushed back
#define BANG_K       4               // boss_cols[] index of the "!!" column (right of his 4 columns)
#define BANG_BG      BOSS_ICE_BG     // its top tile (bottom: + 1)
#define BANG_NONE    255
#if BOSS_ART_TILES * 2 > BOSS_HUD_BG - BOSS_ICE_BG || BOSS_ART_COLS != BANG_K
#error "Leo's !!: the extra BG tiles (246-251), a 32 px body"
#endif

enum { LP_WALK, LP_TELL, LP_ROAR };

typedef struct {
    uint8_t  phase;      // LP_* (the spec's boss_roar; tests)
    uint8_t  t;          // frames in the phase
    uint8_t  roars;      // roars this fight (tests)
    uint8_t  pushed;     // walkers the last roar pushed back (tests)
    uint8_t  hurried;    // drinkers the last roar made finish (tests)
    uint8_t  bang_col;   // screen column the "!!" is drawn at (BANG_NONE: not shown)
    uint16_t mask;       // bit p: regular p is sliding back from a roar (he walks on when the push is used up)
} leo_t;
#define leo (*(leo_t *)BOSS_OWN)
#if 8 > BOSS_OWN_N
#error "Leo's state: BOSS_OWN_N"
#endif

// The "!!" at screen column c (BANG_NONE: off): the old and new columns recomposed (render.c stamps boss_cols[BANG_K]
// at boss_col + BANG_K).
static void bang_at(uint8_t c) {
    if (leo.bang_col != BANG_NONE) mark_dirty_attrs(boss_bar, leo.bang_col, leo.bang_col + 1);
    leo.bang_col = c;
    boss_cols[BANG_K] = c == BANG_NONE ? 0 : BANG_BG;
    if (c != BANG_NONE) mark_dirty_attrs(boss_bar, c, c + 1);
}

static void to_walk(void) {
    leo.phase = LP_WALK; leo.t = 0;
    boss_special_t = LEO_EVERY;
    boss_xpose = 0;
    if (boss_state == BS_TELL || boss_state == BS_SPECIAL) boss_state = BS_WALK;
    if (leo.bang_col != BANG_NONE) bang_at(BANG_NONE);
}

static void to_tell(void) {
    leo.phase = LP_TELL; leo.t = 0;
    boss_special_t = 0;
    boss_xpose = BP_INHALE;
    bang_at(boss_col + BANG_K);
}

// The roar's first frame: one pass over the patron pool.
static void roar(void) {
    uint8_t p, x, d;
    uint16_t bit = 1;
    leo.phase = LP_ROAR; leo.t = 0;
    leo.roars++;
    boss_xpose = BP_ROAR;
    SFX(SFX_SHAKE);
    leo.pushed = leo.hurried = 0;
    for (p = 0; p != MAX_PATRONS; p++, bit <<= 1) {
        if (patron_state[p] == PATRON_WALKING) {
            x = patron_x[p];
            if (patron_aux[p] || patron_dist[p] || x <= ENTRY_X) continue;   // (still coming in at the left end)
            d = x - ENTRY_X;
            patron_state[p] = PATRON_PUSHED;
            patron_aux[p] = d > LEO_PUSH ? LEO_PUSH : d;   // (never to ENTRY_X and beyond: that push would serve him)
            patron_frac[p] = 0;
            patron_timer[p] = 0;
            leo.mask |= bit;
            leo.pushed++;
        } else if (patron_state[p] == PATRON_DRINKING && patron_aux[p] == DRINK_MIN) {
            patron_timer[p] = DRINK_FRAMES - 1;           // his next step finishes the drink (patrons.c finished_step)
            leo.hurried++;
        }
    }
    boss_sip_t = 255;                                     // his own held empty may go now (boss_send: the schedule)
}

// The walkers the roar pushed: a push used up (patrons.c start_drinking, with no mug) -> he walks on.
static void slid(void) {
    uint8_t p;
    uint16_t bit = 1;
    for (p = 0; p != MAX_PATRONS; p++, bit <<= 1) {
        if (!(leo.mask & bit) || patron_state[p] == PATRON_PUSHED) continue;
        leo.mask &= ~bit;
        if (patron_state[p] == PATRON_DRINKING && patron_mug[p] == NO_SLOT) {
            patron_state[p] = PATRON_WALKING;             // (patrons.c walk_on)
            patron_timer[p] = 0;
            patron_aux[p] = 0;
        }
    }
}

uint8_t boss_leo(uint8_t ev, uint8_t arg) BANKED {
    (void)arg;
    switch (ev) {
    case BEV_SET:
        boss_art_set();
        leo.roars = leo.pushed = leo.hurried = 0;
        leo.mask = 0;
        leo.bang_col = BANG_NONE;                         // (boss_set cleared boss_cols)
        to_walk();
        break;
    case BEV_RESET:
        if (leo.mask) slid();
        to_walk();
        break;
    case BEV_LOAD:
        boss_art_load();
        set_bkg_data(BANG_BG, BOSS_ART_TILES * 2, boss_art_tiles);
        break;
    case BEV_TELL:
        if (leo.phase == LP_WALK) to_tell();
        break;
    case BEV_OUTRO:
        to_walk();
        break;
    case BEV_FRAME:
        if (leo.t != 255) leo.t++;
        if (leo.mask) slid();
        switch (leo.phase) {
        case LP_WALK:
            if (boss_special_t && !--boss_special_t) to_tell();
            break;
        case LP_TELL:
            if (leo.t >= LEO_TELL) roar();
            break;
        case LP_ROAR:
            if (leo.t >= LEO_ROAR) to_walk();
            break;
        }
        if (leo.bang_col != BANG_NONE && leo.bang_col != (uint8_t)(boss_col + BANG_K)) bang_at(boss_col + BANG_K);
        if (leo.phase == LP_TELL && boss_state == BS_WALK) boss_state = BS_TELL;   // (a gulp is over: he stands again)
        else if (leo.phase == LP_ROAR && (boss_state == BS_WALK || boss_state == BS_TELL)) boss_state = BS_SPECIAL;
        break;
    }
    return 0;
}
