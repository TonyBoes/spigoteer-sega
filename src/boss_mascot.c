// The Mascot, the stadium's boss (docs/minigames_bosses.md 3.4; art approved 2026-10-11: the red foam bull "Stampede").
// His row is boss.c rows[1]: 32 px, start x 16, bar 1, step 100, push 8, gulp 24, hands 2, sip 45, meter 10.
//
// His leap, every MASCOT_EVERY frame of walking (boss_special_t counts them down):
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
// (the spec's boss_target_bar), mascot.land (boss_land_x) and mascot.ent (the entrance).
//
// ENTRANCE (E8, 2026-10-15; a PROPOSAL for the owner to judge, built like Duke's: BEV_INTRO + BEV_DRAW, the fight's first start
// only): "fired from the T-shirt cannon". The landing marker shows on his spot (frame 6) and the cannon fires (SFX_WHOOSH,
// frame 22): Stampede tumbles in from the top-left corner as a spinning red ball (BALL, a 16x16 sprite: 2 entries, flipped
// in X and Y for the four turns; OBJ 108-111, loaded with the fight), falls on the marker (frame 58), bounces once and lands
// (frame 74): the thud, the CROUCH pose for 10 frames, then the HAPPY pose, finger up, for 40 (SFX_SERVE: the crowd). 124
// frames. BS_JUMP + BP_HIDE until he lands (nothing of his on his bar, no catch); boss_to_bar(boss_bar, 16) at the landing; the
// intro's 90 frames start at the last frame (intro_timer is held until then). The bartender is held at bar 0's tap, no
// pouring, meanwhile. At most 2 entries on any line from this entrance.
#pragma bank 255
#include "boss.h"
#include "boss_mascot_art.h"
#include "boss_load.h"
BOSS_CAST_FN(boss_mascot_cast)   // the credits' cast card (src/credits.c)
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

#define ENT_MARK        6                // the entrance: the marker shows
#define ENT_FIRE       22                // the cannon fires: the ball is on its way
#define ENT_FALL       36                // frames of the fall (x -16 -> 24, y -16 -> his wall's top)
#define ENT_BOUNCE     16                // frames of the one bounce
#define ENT_LAND       (ENT_FIRE + ENT_FALL + ENT_BOUNCE)   // 74: he lands (CROUCH)
#define ENT_CHEER      (ENT_LAND + 10)   // 84: HAPPY
#define ENT_END        (ENT_CHEER + 40)  // 124: the last frame
#define ENT_OAM        (OAM_FILL + 1)    // the mugs' first entry: nothing is in the air during the entrance
#define ENT_OAM_N       2
#define ENT_X0        (-16)              // the ball's start (screen px), and where it lands (his columns 3-4)
#define ENT_X1         24
#if ENT_OAM + ENT_OAM_N > OAM_MUG_END || BOSS_ART_SPR_PAIRS != 2 || BOSS_SPR_TILE0 != 108 || ENT_END > 250
#error "the Mascot's entrance: the OAM entries, the ball's tile pairs or the clock"
#endif

enum { MP_WALK, MP_TELL, MP_WAIT, MP_AIR };

typedef struct {
    uint8_t phase;      // MP_* (tests)
    uint8_t t;          // frames in the phase
    uint8_t target;     // the bar he will land on (the spec's boss_target_bar; tests)
    uint8_t land;       // the landing x (the spec's boss_land_x; tests)
    uint8_t leaps;      // leaps this fight (tests)
    uint8_t wm;         // the earlier mugs are those on his bar at x <= wm (it falls MUG_SPEED_FULL a frame, as they do)
    uint8_t ent;        // the entrance: 0 none (or over), else the next frame's number + 1 (tests)
} mascot_t;
#define mascot (*(mascot_t *)BOSS_OWN)
#if 7 > BOSS_OWN_N
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

// ---- the entrance ----
// BEV_DRAW: the ball for the frame the logic just reached (boss_draw, after every other sprite): it falls from the top-left
// corner onto his marker with its spin (a turn every 3 frames), bounces once (the spin half as quick) and is gone as he lands.
static void ent_draw(void) {
    OAM_item_t *o = shadow_OAM + ENT_OAM, *top = o + ENT_OAM_N, *end = shadow_OAM + OAM_MUG_END - 2 * lift_total;
    uint8_t t = mascot.ent - 2, k, n, spin, prop, ly = bar_oam_y[boss_bar];       // (his wall's top, as OAM y: screen + 16)
    int16_t x, y;
    const uint8_t *c;
    if (mascot.ent < 2) return;
    if (end > top) end = top;
    if (t >= ENT_FIRE && t < ENT_LAND) {
        k = t - ENT_FIRE;
        if (k < ENT_FALL) {                            // x: straight across; y: gravity (the square of the time)
            x = ENT_X0 + (int16_t)(((ENT_X1 - ENT_X0) * (uint16_t)k) / ENT_FALL);
            y = (int16_t)(((uint16_t)((k * k) >> 4) * (uint8_t)(ly - 16 + 16)) / ((ENT_FALL * ENT_FALL) >> 4)) - 16;   // (to his wall's top at k = ENT_FALL)
            spin = k / 3;
        } else {
            n = k - ENT_FALL;                          // 0..15: up 16 px and down
            x = ENT_X1;
            y = ly - 16 - ((n * (ENT_BOUNCE - n)) >> 2);
            spin = (ENT_FALL / 3) + (n >> 2);
        }
        c = boss_spr_cells + (uint16_t)boss_spr_first[SPR_BALL] * 3;
        n = boss_spr_first[SPR_BALL + 1] - boss_spr_first[SPR_BALL];
        for (; n && o != end; n--, c += 3) {
            prop = is_cgb ? OBJPAL_PATRON_C : S_PALETTE;
            k = c[0];                                  // dx: 0 or 8 (mirrored: the cells swap places)
            if (spin & 1) { prop |= S_FLIPX; k = 8 - k; }
            if (spin & 2) prop |= S_FLIPY;
            if ((uint16_t)(x + k + 8 - 1) >= 167 || y < -15) continue;     // (off the screen: left out)
            o->y = (uint8_t)(y + 16); o->x = (uint8_t)(x + k + 8);
            o->tile = BOSS_SPR_TILE0 + (c[2] << 1); o->prop = prop;
            o++;
        }
    }
    for (; o != top; o++) o->y = 0;
}

// BEV_INTRO, every frame while intro_timer runs: the entrance's clock and what happens at its frames. The player's input is
// undone (the bartender stays at bar 0's tap, nothing is poured) until he has landed and cheered.
static void ent_frame(void) {
    uint8_t t = mascot.ent - 1, i;
    fill_timer = 0; fill_stage = 0;                          // (the bartender stays where he is: main.c skips his input while he is held)
    bartender_frame = BT_IDLE; catch_pose = 0; bt_bob = 0;
    if (t < ENT_END) intro_timer = INTRO_FRAMES;            // (held: the intro's 90 frames start at the last frame)
    if (t == ENT_MARK) boss_mark(boss_bar, 3);              // the landing marker, columns 3-4
    if (t == ENT_FIRE) SFX(SFX_WHOOSH);
    if (t == ENT_LAND) {
        boss_xpose = BP_CROUCH; BOSS_TOPPER_T = HAT_CROUCH;
        boss_mark(BOSS_NONE, 0);
        boss_to_bar(boss_bar, MASCOT_X);                    // his BG body (CROUCH) at x 16
        SFX(SFX_SHAKE);
    }
    if (t == ENT_CHEER) { boss_xpose = BP_HAPPY; BOSS_TOPPER_T = 0; SFX(SFX_SERVE); }
    if (t == ENT_END) {
        intro_timer = INTRO_FRAMES - 1;                      // (as the level's first frame leaves it: the fight starts 89 frames on)
        boss_xpose = 0; boss_state = BS_WALK;                // (E9: the entrance is over: boss.c starts the fight)
        for (i = 0; i != ENT_OAM_N; i++) shadow_OAM[ENT_OAM + i].y = 0;
        mascot.ent = 0;
        return;
    }
    mascot.ent++;
}

uint8_t boss_mascot(uint8_t ev, uint8_t arg) BANKED {
    (void)arg;
    switch (ev) {
    case BEV_SET:
        boss_art_set();
        mascot.leaps = 0;
        mascot.ent = 0;
        to_walk();
        break;
    case BEV_RESET:
        if (boss_bar != MASCOT_BAR) boss_to_bar(MASCOT_BAR, MASCOT_X);
        to_walk();
        if (mascot.ent) { boss_state = BS_JUMP; boss_xpose = BP_HIDE; }   // (the entrance: not on his bar yet)
        break;
    case BEV_LOAD:
        boss_art_load();
        BOSS_OBJ(BOSS_SPR_TILE0, BOSS_ART_SPR_PAIRS * 2, boss_spr_tiles);   // the ball (OBJ 108-111: the show's tiles, none in a fight)
        break;
    case BEV_ENTER:                                          // (E9: after the warm-up)
        mascot.ent = 1;
        return 1;
    case BEV_INTRO:
        if (mascot.ent) ent_frame();
        break;
    case BEV_DRAW:
        if (mascot.ent) ent_draw();
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
