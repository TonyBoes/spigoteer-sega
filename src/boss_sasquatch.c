// The Sasquatch, the lumber lodge's boss (docs/minigames_bosses.md 3.5; art approved 2026-10-11, look A round 2).
// His row is boss.c rows[2]: 32 px, step 90, push 8, hands 2, meter 12; gulp 8 (he downs a coffee "instantly") and
// sip 0: each empty goes as soon as the fair-empties schedule allows, and it slides back at 1 px a frame (his bar is
// a fast-empty bar: boss.c boss_mugs). Holding two, the third coffee passes him and breaks (the hands rule).
// His own empties keep only SASQ_GAP frames between them (the game's floor; the lodge's 108 would make him mostly a
// holder); the regulars' empties still keep the level's empty_gap from his, and his from theirs (boss.c boss_send).
//
// GONE TO THE WOODS (owner 2026-10-14: "he goes invisible for a bit and then shows up in another row"), every
// SASQ_EVERY frames of walking (boss_special_t counts them down):
//   1. DUCK, at least SASQ_DUCK frames: he sinks behind the counter (the DUCK pose, the crest lowered: HAT_DUCK) and
//      stands (BS_TELL); he still drinks a coffee that reaches him. He leaves only when every full mug on
//      his bar has reached him (caught, or passed him on a full hand) and every empty on it has been caught
//      at the tap (SASQ_WAITMAX frames more at most): no mug or empty is lost to his leaving. A mug thrown once he is gone is the player's risk.
//   2. GONE, SASQ_GONE frames (BS_JUMP + BP_HIDE: his bar is plain wall, no topper, no catch, no empty sent): the target
//      bar (any but his own) shows his FOOTPRINTS (the landing marker slot, blinking) at the x he will stand on (16 / 32 / 48):
//      the whole 1.1 s is the warning. The regulars are steered off both bars (boss_pattern). A mug sent to his old bar while
//      he is away slides to its left end and breaks (the engine's rule for a bar without a catcher): the bar is visibly empty.
//   3. POP, SASQ_POP frames: boss_to_bar(target, x): he bursts up (BURST2: leaves and splinters), the thud; regulars still
//      standing on that bar are scared off (no score, no penalty); his meter and held empties come with him. Then WALK.
// A lost life brings him back to bar 2 at x 16 (the marker gone), his meter kept.
//
// ENTRANCE (X2 "through the back wall"; BEV_INTRO, BG only, no sprite): on the fight's first start (BEV_LOAD) three thuds
// come closer (the wall is bare: the engine draws the footprints only on a bar he is not on), a fist punches through the wall (BURST1), he roars out in flying
// splinters (BURST2) and lands at x 16; the level's 90-frame intro runs from there (intro_timer is held until the landing).
// The bartender is held at bar 0's tap while it runs. Start it for a later arrival by setting sasq.ent = 1 (BEV_RESET puts
// him away first).
// Test hooks (WRAM: his state is the struct sasquatch_t in BOSS_OWN): sasq.phase, .t, .target, .land, .vanishes, .ent.
#pragma bank 255
#include "boss.h"
#include "boss_sasquatch_art.h"
#include "boss_load.h"
BOSS_CAST_FN(boss_sasquatch_cast)   // the credits' cast card (src/credits.c)
#include "music.h"

#define SASQ_GAP      80          // frames between two of his own empties' arrivals (spec 3.5)
#define SASQ_BAR       2          // his home bar (boss.c rows[2]) and start x
#define SASQ_X        16
#define SASQ_EVERY   360          // frames of walking between two vanishes
#define SASQ_DUCK     36          // the tell
#define SASQ_WAITMAX 150          // the wait for the earlier mugs and his empties still sliding back (<= ~100 frames)
#define SASQ_GONE     66          // away: the footprints' warning
#define SASQ_POP      14          // the burst
#define HAT_DUCK       4          // topper tile offset: the HAT_DUCK frame (after HAT_STILL, HAT_BOB)
#define BP_DUCK       BP_EXTRA    // gen_boss BOSSES sasquatch extra: DUCK, BURST1, BURST2
#define BP_BURST1     (BP_EXTRA + 1)
#define BP_BURST2     (BP_EXTRA + 2)
#define ENT_BURST1    40          // the entrance's frames: the fist, the roar, the landing
#define ENT_BURST2    50
#define ENT_LAND      60

enum { SQ_WALK, SQ_DUCK, SQ_GONE, SQ_POP };

typedef struct {
    uint8_t phase;      // SQ_* (tests)
    uint8_t t;          // frames in the phase (stops at 255)
    uint8_t target;     // the bar he will pop up on (tests)
    uint8_t land;       // the x he will stand on (tests)
    uint8_t vanishes;   // vanishes this fight (tests)
    uint8_t ent;        // the entrance: 0 none (or over), else the next frame's number + 1 (tests)
} sasquatch_t;
#define sasq (*(sasquatch_t *)BOSS_OWN)
#if 6 > BOSS_OWN_N
#error "the Sasquatch's state: BOSS_OWN_N"
#endif

static const uint8_t land_x[3] = { 16, 32, 48 };

static void to_walk(void) {
    sasq.phase = SQ_WALK; sasq.t = 0;
    boss_special_t = SASQ_EVERY;
    boss_xpose = 0;
    BOSS_TOPPER_T = 0;
    boss_mark(BOSS_NONE, 0);
    if (boss_state != BS_OUTRO) boss_state = BS_WALK;
}

static void to_duck(void) {
    sasq.phase = SQ_DUCK; sasq.t = 0;
    boss_special_t = 0;
    boss_xpose = BP_DUCK;
    BOSS_TOPPER_T = HAT_DUCK;
    boss_state = BS_TELL;
}

// Any full mug still on its way to him (on his bar, right of his catching edge) and any empty sliding back on his bar.
static uint8_t waiting(void) {
    uint8_t i, edge = boss_x + boss_width() - 8;   // (the last 8 px: caught below his edge - 3)
    for (i = 0; i != MAX_MUGS; i++)
        if (mug_bar[i] == boss_bar && ((mug_state[i] == MUG_FULL && mug_x[i] >= edge)
                                      || mug_state[i] == MUG_EMPTY)) return 1;   // (an empty still sliding back needs the bartender here)
    return 0;
}

static void vanish(void) {
    uint8_t r;
    sasq.phase = SQ_GONE; sasq.t = 0;
    boss_state = BS_JUMP;
    boss_push = 0;
    boss_xpose = BP_HIDE;
    BOSS_TOPPER_T = 0;
    do r = next_rand() & 3; while (r == boss_bar);
    sasq.target = r;
    do r = next_rand() & 3; while (r == 3);
    sasq.land = land_x[r];
    boss_mark(sasq.target, sasq.land >> 3);
    boss_pattern(sasq.target);
    sasq.vanishes++;
    SFX(SFX_WHOOSH);
}

static void pop(void) {
    boss_mark(BOSS_NONE, 0);
    boss_xpose = BP_BURST2;
    boss_state = BS_WALK;
    boss_to_bar(sasq.target, sasq.land);
    SFX(SFX_SHAKE);                                       // the thud
    sasq.phase = SQ_POP; sasq.t = 0;
}

// BEV_INTRO, every frame while intro_timer runs and the entrance is on.
static void ent_frame(void) {
    uint8_t t = sasq.ent - 1;
    fill_timer = 0; fill_stage = 0;                          // (the bartender stays where he is: main.c skips his input while he is held)
    bartender_frame = BT_IDLE; catch_pose = 0; bt_bob = 0;
    if (t < ENT_LAND) intro_timer = INTRO_FRAMES;         // (held: the intro's 90 frames start at the landing)
    if (t < ENT_BURST1) {
        if (!(t & 15)) SFX(SFX_SHAKE);                    // the thuds, nearer
    } else if (t == ENT_BURST1) {
        boss_xpose = BP_BURST1;
        SFX(SFX_SHAKE);
    } else if (t == ENT_BURST2) {
        boss_xpose = BP_BURST2;
        SFX(SFX_WHOOSH);
    } else if (t == ENT_LAND) {
        intro_timer = INTRO_FRAMES - 1;                   // (as the level's first frame leaves it)
        boss_xpose = 0; boss_state = BS_WALK;
        boss_to_bar(boss_bar, SASQ_X);
        to_walk();
        SFX(SFX_SHAKE);
        sasq.ent = 0;
        return;
    }
    sasq.ent++;
}

uint8_t boss_sasquatch(uint8_t ev, uint8_t arg) BANKED {
    (void)arg;
    switch (ev) {
    case BEV_SET:
        boss_art_set();
        boss_fast_empty = 1;
        boss_own_gap = SASQ_GAP;
        sasq.vanishes = 0; sasq.ent = 0;
        to_walk();
        break;
    case BEV_RESET:
        if (boss_bar != SASQ_BAR) boss_to_bar(SASQ_BAR, SASQ_X);
        to_walk();
        if (sasq.ent) { boss_state = BS_JUMP; boss_xpose = BP_HIDE; }   // (the entrance: not on his bar yet)
        break;
    case BEV_LOAD:
        boss_art_load();
        break;
    case BEV_ENTER:                      // E9: the warm-up is over (his bar is empty): the back wall
        sasq.ent = 1;
        return 1;
    case BEV_INTRO:
        if (sasq.ent) ent_frame();
        break;
    case BEV_TELL:
        if (sasq.phase == SQ_WALK) to_duck();
        break;
    case BEV_OUTRO:
        to_walk();
        break;
    case BEV_FRAME:
        if (sasq.t != 255) sasq.t++;
        switch (sasq.phase) {
        case SQ_WALK:
            if (boss_special_t && !--boss_special_t) to_duck();
            break;
        case SQ_DUCK:
            if (sasq.t >= SASQ_DUCK && (!waiting() || sasq.t >= SASQ_DUCK + SASQ_WAITMAX)) vanish();
            else if (boss_state == BS_WALK) boss_state = BS_TELL;   // (a gulp is over: he stands again)
            break;
        case SQ_GONE:
            if (sasq.t & 4) boss_mark(BOSS_NONE, 0); else boss_mark(sasq.target, sasq.land >> 3);   // (blinking)
            if (sasq.t >= SASQ_GONE) pop();
            break;
        case SQ_POP:
            if (sasq.t >= SASQ_POP) to_walk();
            break;
        }
        break;
    }
    return 0;
}
