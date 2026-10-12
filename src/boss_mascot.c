// The Mascot, the stadium's boss (docs/minigames_bosses.md 3.4; art approved 2026-10-11: the red foam bull "Stampede").
// His row is boss.c rows[1]: 32 px, start x 16, bar 1, step 100, push 8, gulp 24, hands 2, sip 45, meter 10.
//
// His leap, every MASCOT_EVERY frames of walking (boss_special_t counts them down):
//   1. TELL, MASCOT_TELL frames: the CROUCH pose (and the crown tuft one row lower), he stands (BS_TELL). A random other
//      bar is the target and the landing x one of 16 / 32 / 48 (boss_mark: the 2-column dust MARKER on the target bar's
//      wall, drawn over its patrons); the regulars stop coming to the target bar (boss_pattern).
//   2. WAIT: he leaps only when the tell has run AND every full mug that was on his bar when the tell began has reached
//      him (it is caught, or it has passed him). A mug thrown during the crouch is the player's risk: if he leaves first
//      it slides to the left end and breaks (the common rule for a mug on a bar without a catcher). At most
//      MASCOT_WAITMAX frames of waiting.
//   3. AIR, MASCOT_AIR frames (BS_JUMP): his body is gone, two dust puffs (PUFF1, PUFF2) where he stood, no topper, no catch.
//   4. LANDING: boss_to_bar(target, land): his body on the target bar with the thud, its regulars scared off (leaving:
//      no score, no penalty), meter and hands with him, a held empty is sent from there when the schedule allows.
// A hit in the tell shows GULP / WINCE as usual and the push-back moves him on his bar (the landing x stays); a lost life
// brings him back to bar 1 at x 16 walking (the marker gone), his meter kept.
// Test hooks (WRAM: his state is the struct mascot_t in BOSS_OWN, not variables of its own): mascot.phase, mascot.target
// (the spec's boss_target_bar) and mascot.land (boss_land_x).
#pragma bank 255
#include "boss.h"
#include "boss_mascot_art.h"
#include "boss_load.h"
#include "music.h"

#define BP_CROUCH     BP_EXTRA           // gen_boss BOSSES mascot extra: CROUCH, PUFF1, PUFF2
#define BP_PUFF1      (BP_EXTRA + 1)
#define BP_PUFF2      (BP_EXTRA + 2)
#define MASCOT_BAR      1                // his home bar (boss.c rows[1])
#define MASCOT_X       16                // and start x
#define MASCOT_EVERY  300                // frames of walking between two leaps
#define MASCOT_TELL    60                // the crouch and the marker
#define MASCOT_WAITMAX 60                // the wait for the earlier mugs (a mug needs <= ~44 frames)
#define MASCOT_AIR     20                // frames away from any bar
#define HAT_CROUCH      2                // topper tile offset: HAT_BOB (one row lower, no bob)

enum { MP_WALK, MP_TELL, MP_WAIT, MP_AIR };

typedef struct {
    uint8_t phase;      // MP_* (tests)
    uint8_t t;          // frames in the phase
    uint8_t target;     // the bar he will land on (the spec's boss_target_bar; tests)
    uint8_t land;       // the landing x (the spec's boss_land_x; tests)
    uint8_t leaps;      // leaps this fight (tests)
    uint8_t wm;         // the earlier mugs are those on his bar at x <= wm (it falls MUG_SPEED_FULL a frame, as they do)
} mascot_t;
#define mascot (*(mascot_t *)BOSS_OWN)
#if 6 > BOSS_OWN_N
#error "the Mascot's state: BOSS_OWN_N"
#endif

static const uint8_t land_x[3] = { 16, 32, 48 };

static void to_walk(void) {
    mascot.phase = MP_WALK; mascot.t = 0;
    boss_special_t = MASCOT_EVERY;
    boss_xpose = 0;
    BOSS_TOPPER_T = 0;
    boss_mark(BOSS_NONE, 0);
    if (boss_state != BS_OUTRO) boss_state = BS_WALK;
}

static void to_tell(void) {
    uint8_t i, r, wm = 0;
    mascot.phase = MP_TELL; mascot.t = 0;
    boss_special_t = 0;
    boss_xpose = BP_CROUCH;
    BOSS_TOPPER_T = HAT_CROUCH;
    do r = next_rand() & 3; while (r == boss_bar);
    mascot.target = r;
    do r = next_rand() & 3; while (r == 3);
    mascot.land = land_x[r];
    boss_mark(mascot.target, mascot.land >> 3);
    boss_pattern(mascot.target);
    for (i = 0; i != MAX_MUGS; i++)                       // the mugs already on his bar: the rightmost is the watermark
        if (mug_state[i] == MUG_FULL && mug_bar[i] == boss_bar && mug_x[i] > wm) wm = mug_x[i];
    mascot.wm = wm;
    boss_state = BS_TELL;
}

// The earlier mugs still on their way to him (on his bar, at or left of the watermark, right of his catching edge).
static uint8_t waiting(void) {
    uint8_t i, edge = boss_x + boss_width();
    for (i = 0; i != MAX_MUGS; i++)
        if (mug_state[i] == MUG_FULL && mug_bar[i] == boss_bar && mug_x[i] <= mascot.wm && mug_x[i] >= edge) return 1;
    return 0;
}

static void leap(void) {
    mascot.phase = MP_AIR; mascot.t = 0;
    boss_state = BS_JUMP;
    boss_push = 0;
    boss_xpose = BP_PUFF1;
    BOSS_TOPPER_T = 0;
}

static void land(void) {
    boss_xpose = 0;
    boss_state = BS_WALK;
    boss_mark(BOSS_NONE, 0);
    boss_to_bar(mascot.target, mascot.land);
    SFX(SFX_SHAKE);                                       // the thud
    mascot.leaps++;
    to_walk();
}

uint8_t boss_mascot(uint8_t ev, uint8_t arg) BANKED {
    (void)arg;
    switch (ev) {
    case BEV_SET:
        boss_art_set();
        mascot.leaps = 0;
        to_walk();
        break;
    case BEV_RESET:
        if (boss_bar != MASCOT_BAR) boss_to_bar(MASCOT_BAR, MASCOT_X);
        to_walk();
        break;
    case BEV_LOAD:
        boss_art_load();
        break;
    case BEV_TELL:
        if (mascot.phase == MP_WALK) to_tell();
        break;
    case BEV_OUTRO:
        to_walk();
        break;
    case BEV_FRAME:
        if (mascot.t != 255) mascot.t++;
        switch (mascot.phase) {
        case MP_WALK:
            if (boss_special_t && !--boss_special_t) to_tell();
            break;
        case MP_TELL:
        case MP_WAIT:
            mascot.wm = mascot.wm > MUG_SPEED_FULL ? mascot.wm - MUG_SPEED_FULL : 0;
            if (mascot.phase == MP_TELL && mascot.t >= MASCOT_TELL) mascot.phase = MP_WAIT;
            if (mascot.phase == MP_WAIT && (!waiting() || mascot.t >= MASCOT_TELL + MASCOT_WAITMAX)) leap();
            else if (boss_state == BS_WALK) boss_state = BS_TELL;   // (a gulp is over: he stands again)
            break;
        case MP_AIR:
            if (mascot.t == MASCOT_AIR / 2) boss_xpose = BP_PUFF2;
            if (mascot.t >= MASCOT_AIR) land();
            break;
        }
        break;
    }
    return 0;
}
