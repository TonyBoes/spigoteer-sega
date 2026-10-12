// The Sumo, the teahouse's boss (docs/minigames_bosses.md 3.9; art approved 2026-10-11, look 2 round 2, the curved belt).
// His row is boss.c rows[7]: 40 px, start 16, bar 1, step 96 (frames per step: see the beat), push 0, gulp 0, hands 2,
// sip 90, meter 8; his topknot is the topper.
//
// The beat: he steps 8 px (boss_advance: the STOMP pose, the thud) on the teahouse tune's beat, once every SUMO period
// = the row's step (96 frames: 8 rows of "sakura" at its 12 frames a row, one bar of the taiko groove, on its first
// "don"; Practice's HARD: 72, 6 rows), counted on src/music.c's music_frames (so a step lands on the same row of the
// tune every time, whatever happened between); with the music off, his own 96-frame clock. boss_step is 0 in his fight:
// the engine's stomp timer is off, he moves only here. He steps only walking (not while pushed back, in the tell, the
// charge or the hmph): a beat he cannot take is skipped, the next one comes a period later.
//
// The chain: a hit always counts (meter -1, no gulp: he swallows and keeps going; the GULP pose shows SUMO_HIT_POSE
// frames as the "hit" pose). It pushes him back 8 px only when it comes within SUMO_CHAIN (80) frames of his previous
// hit (a "chain"). While a chain is live (<= 80 frames since the last hit) his face on the HUD blinks (8 frames on, 8
// off); it stays when the chain runs out.
//
// The charge, every SUMO_EVERY frames of walking (boss_special_t counts them down):
//   1. TELL, SUMO_TELL frames: the SHIKO stamp pose, he stands (BS_TELL). Any hit now cancels the charge: the HMPH
//      pose for SUMO_HMPH frames (he stands, BS_SPECIAL), then he walks and the timer starts over.
//   2. CHARGE: 24 px in 12 frames (three boss_advance stomps, one every 4 frames; BS_SPECIAL); then he walks again.
// No counter dust: the spec's two dust tiles have no approved art; the SHIKO pose is the tell (a BG pose change, 60
// frames).
// Test hooks (WRAM: his state is the struct sumo_t in BOSS_OWN, not variables of its own): sumo.phase (the spec's
// boss_charge: 0 walking, 1 the tell, 2 the charge, 3 the hmph), sumo.chain (the spec's boss_chain: frames since his
// last hit, 255 none yet or long ago).
#pragma bank 255
#include "boss.h"
#include "boss_sumo_art.h"
#include "boss_load.h"
#include "music.h"

#define BP_SHIKO      BP_EXTRA       // gen_boss BOSSES sumo extra: SHIKO, HMPH
#define BP_HMPH       (BP_EXTRA + 1)
#define SUMO_CHAIN     80            // a hit within this many frames of the last one is chained: it pushes him
#define SUMO_PUSH       8            // px a chained hit pushes him back
#define SUMO_HIT_POSE  16            // frames of the "hit" pose (GULP) after a hit
#define SUMO_EVERY    480            // frames of walking between two charges
#define SUMO_TELL      60            // the shiko stamp
#define SUMO_HOP        4            // frames per 8 px of the charge
#define SUMO_HOPS       3            // 24 px
#define SUMO_HMPH      30            // the charge called off
#define SUMO_BLINK      8            // the HUD face's blink, frames on / off
#define CHAIN_NONE    255

enum { SU_WALK, SU_TELL, SU_CHARGE, SU_HMPH };

typedef struct {
    uint8_t  phase;      // SU_* (the spec's boss_charge; tests)
    uint8_t  t;          // frames in the phase
    uint8_t  chain;      // frames since his last hit (CHAIN_NONE: none yet, or long ago) (the spec's boss_chain)
    uint8_t  chained;    // hits that pushed him this fight (tests)
    uint8_t  singles;    // hits that did not (tests)
    uint8_t  cancels;    // charges called off by a hit (tests)
    uint8_t  charges;    // charges made (tests)
    uint8_t  steps;      // steps on the beat (tests)
    uint8_t  period;     // frames per step (the row's step, HARD's)
    uint8_t  beat_f;     // frames into the period
    uint16_t last_mf;    // music_frames at the last look
    uint8_t  icon;       // the HUD face's tile now (the VBlank queue's source: WRAM)
    uint8_t  pose_t;     // frames of the hit pose left
} sumo_t;
#define sumo (*(sumo_t *)BOSS_OWN)
#if 15 > BOSS_OWN_N
#error "the Sumo's state: BOSS_OWN_N"
#endif

// The beat clock in step with the tune (music_frames), or his own with the music off.
static void beat_sync(void) {
    sumo.last_mf = music_frames;
    sumo.beat_f = sound_on ? (uint8_t)(music_frames % sumo.period) : 0;
}

static uint8_t beat(void) {
    uint16_t mf = music_frames, d;
    if (!sound_on) d = 1;
    else if (mf < sumo.last_mf) { beat_sync(); return 0; }    // (the tune started over)
    else d = mf - sumo.last_mf;
    sumo.last_mf = mf;
    d += sumo.beat_f;
    if (d < sumo.period) { sumo.beat_f = (uint8_t)d; return 0; }
    sumo.beat_f = (uint8_t)(d % sumo.period);
    return 1;
}

static void face(uint8_t t) {                    // the HUD face's tile (column 12)
    if (sumo.icon == t) return;
    sumo.icon = t;
    vq_add(0, &sumo.icon, 12, HUD_ROW, 1);
}

static void to_walk(void) {
    sumo.phase = SU_WALK; sumo.t = 0;
    boss_special_t = SUMO_EVERY;
    boss_xpose = 0;
    if (boss_state == BS_TELL || boss_state == BS_SPECIAL) boss_state = BS_WALK;
}

static void to_tell(void) {
    sumo.phase = SU_TELL; sumo.t = 0;
    boss_special_t = 0;
    boss_xpose = BP_SHIKO;
    sumo.pose_t = 0;
}

uint8_t boss_sumo(uint8_t ev, uint8_t arg) BANKED {
    (void)arg;
    switch (ev) {
    case BEV_SET:
        boss_art_set();
        sumo.period = boss_step;                 // (96, HARD 72: whole rows of the teahouse tune)
        boss_step = 0;                           // the engine's stomp timer off: he steps on the beat (below)
        sumo.chained = sumo.singles = sumo.cancels = sumo.charges = sumo.steps = 0;
        sumo.icon = BOSS_HUD_BG;                 // (boss_begin's boss_hud draws the face)
        /* fall through */
    case BEV_RESET:
        sumo.chain = CHAIN_NONE;
        sumo.pose_t = 0;
        if (LCDC_REG & LCDCF_ON) face(BOSS_HUD_BG);   // (a lost life in mid-blink)
        to_walk();
        beat_sync();
        break;
    case BEV_LOAD:
        boss_art_load();
        break;
    case BEV_TELL:
        if (sumo.phase == SU_WALK) to_tell();
        break;
    case BEV_CATCH:                              // (then the common catch: meter -1, his push 0, gulp 0)
        if (sumo.chain <= SUMO_CHAIN) { boss_push += SUMO_PUSH; sumo.chained++; }
        else sumo.singles++;
        sumo.chain = 0;
        sumo.icon = BOSS_HUD_BG;                 // (boss_hud redraws the face with the meter)
        if (sumo.phase == SU_TELL) {             // the charge called off
            sumo.phase = SU_HMPH; sumo.t = 0;
            boss_xpose = BP_HMPH;
            sumo.cancels++;
        } else if (sumo.phase == SU_WALK) {
            boss_xpose = BP_GULP;                // the hit pose (he does not stop)
            sumo.pose_t = SUMO_HIT_POSE;
        }
        break;
    case BEV_OUTRO:
        sumo.phase = SU_WALK;
        boss_xpose = 0;
        face(BOSS_HUD_BG);
        break;
    case BEV_FRAME:
        if (sumo.t != 255) sumo.t++;
        if (sumo.chain != CHAIN_NONE) sumo.chain++;
        if (sumo.chain <= SUMO_CHAIN) face(sumo.chain & SUMO_BLINK ? TILE_HUD_BLANK : BOSS_HUD_BG);
        else face(BOSS_HUD_BG);
        if (sumo.pose_t && !--sumo.pose_t && boss_xpose == BP_GULP) boss_xpose = 0;
        if (beat() && sumo.phase == SU_WALK && boss_state == BS_WALK && !boss_push) {
            boss_advance();
            sumo.steps++;
        }
        switch (sumo.phase) {
        case SU_WALK:
            if (boss_special_t && !--boss_special_t) to_tell();
            break;
        case SU_TELL:
            if (sumo.t >= SUMO_TELL) {
                sumo.phase = SU_CHARGE; sumo.t = 0;
                boss_xpose = 0;
                sumo.charges++;
            }
            break;
        case SU_CHARGE:
            if (!(sumo.t % SUMO_HOP)) boss_advance();
            if (sumo.t >= SUMO_HOP * SUMO_HOPS) to_walk();
            break;
        case SU_HMPH:
            if (sumo.t >= SUMO_HMPH) to_walk();
            break;
        }
        if (sumo.phase == SU_TELL && boss_state == BS_WALK) boss_state = BS_TELL;   // (he stands)
        else if (sumo.phase >= SU_CHARGE && (boss_state == BS_WALK || boss_state == BS_TELL)) boss_state = BS_SPECIAL;
        break;
    }
    return 0;
}
