// The Sumo, the teahouse's boss (docs/minigames_bosses.md 3.9; art approved 2026-10-11, look 2 round 2, the curved belt).
// His row is boss.c rows[7]: 40 px, start 24, bar 1, step 192 (frames per step: see the beat), push 0, gulp 0, hands 2
// (unused: no limit, below), sip 90, meter 6; his topknot is the topper.
//
// A PUSHING MATCH (owner 2026-10-15: "no drink limits ... he has to be pushed out of the bar to lose ... knocked back
// with every throw"). He loses by RING-OUT: shoved to the bar's left end (x 0). He wins by reaching the tap (x 96: a life).
//   - No drink limit: boss_cap is 250, every cup that reaches him is drunk, no hands rule. (His empties still come back one
//     per sip, through boss.c's fair-empties schedule, so a throw-and-catch rhythm stays the player's job.)
//   - The HUD meter FILLS with drinks (a pint a cup, left to right; the engine's pints, EMPTY / HALF / FULL tiles, plus two
//     one-pip tiles built at load for an odd target) and its length is the TARGET: SUMO_START (6) pips, then one fewer each
//     time it fills, down to 1 (then every cup is a knock-back). boss_hp is the cups still to go this cycle (>= 1; 0 only at
//     the ring-out, which hands the fight to the engine's outro), sumo.cyc the target.
//   - A full meter: it blinks full for SUMO_FLASH frames (drum), the next target appears, and he is KNOCKED BACK SUMO_KNOCK
//     (32) px in four 8 px hops (the WINCE pose), then dazed (no steps) until SUMO_STAGGER (44) frames are over. The knock
//     cancels a charge. When it takes him to x 0 he is out: SUMO_OUT frames at the wall (WINCE, the crowd), boss_hp 0,
//     and BEV_OUTRO leaves him gone (BP_HIDE: shoved out the door), not happy.
//
// The beat: he steps 8 px (boss_advance: the STOMP pose, the thud) on the teahouse tune's beat, once every SUMO period
// = the row's step (192 frames: 16 rows of "sakura" at its 12 frames a row, two bars of the taiko groove, which divide the
// tune's 1344 frames; Practice's HARD: 144), counted on src/music.c's music_frames (so a step lands on the same row of the
// tune every time, whatever happened between); with the music off, his own clock. boss_step is 0 in his fight: the
// engine's stomp timer is off, he moves only here. He steps only walking (not in the tell, the charge, the knock or the
// hmph): a beat he cannot take is skipped, the next one comes a period later.
//
// The charge, every SUMO_EVERY frames of walking (boss_special_t counts them down):
//   1. TELL, SUMO_TELL frames: the SHIKO stamp pose, he stands (BS_TELL). Any cup now cancels the charge: the HMPH
//      pose for SUMO_HMPH frames (he stands, BS_SPECIAL), then he walks and the timer starts over.
//   2. CHARGE: 16 px in 8 frames (two boss_advance stomps, one every 4 frames; BS_SPECIAL); then he walks again.
//
// ENTRANCE, "the ring ritual" (the model is Duke's: BEV_LOAD arms it for the fight's first start, BEV_INTRO runs it while
// the level's intro_timer is held, BEV_DRAW draws its sprites; the bartender and the cups are held as in Duke's): the bar
// is empty; at frame SE_IN he walks in from the left wall in three heavy steps (x 0 -> 24); he lifts a leg (SHIKO) and
// throws SALT (two grains of OBJ_DUST's scatter tile arcing over the counter), stamps (the picture shakes, dust at his
// feet, the drum), lifts the other leg and stamps again, harder, then the fight begins SE_TAIL frames on.
// Test hooks (WRAM: his state is the struct sumo_t in BOSS_OWN, not variables of his own): sumo.phase, sumo.cyc,
// sumo.cycles, sumo.knock, sumo.out, sumo.ent.
#pragma bank 255
#define BOSS_WANT_METER      // (boss_art.h: the meter tiles, recoloured here)
#include "boss.h"
#include "boss_sumo_art.h"
#include "boss_load.h"
BOSS_CAST_FN(boss_sumo_cast)   // the credits' cast card (src/credits.c)
#include "music.h"

#define BP_SHIKO      BP_EXTRA       // gen_boss BOSSES sumo extra: SHIKO, HMPH
#define BP_HMPH       (BP_EXTRA + 1)
#define SUMO_START      6            // the first target: cups to fill the meter
#define SUMO_KNOCK     32            // px a full meter knocks him back
#define SUMO_STAGGER   44            // frames of the knock-back and the daze
#define SUMO_FLASH     24            // frames the full meter blinks before the new target
#define SUMO_OUT       24            // frames at the wall before he is gone
#define SUMO_HIT_POSE  16            // frames of the "hit" pose (GULP) after a cup
#define SUMO_EVERY    480            // frames of walking between two charges
#define SUMO_TELL      60            // the shiko stamp
#define SUMO_HOP        4            // frames per 8 px of the charge and the knock-back
#define SUMO_HOPS       2            // 16 px
#define SUMO_HMPH      30            // the charge called off
#define CAP_ANY       250            // boss_cap: no drink limit
#define SOLO_BG       246            // the one-pip tiles: empty, full (BOSS_ICE_BG's: the Sumo has no ice)
#define SUMO_HUD      (story_scratch + SCR_CAP_AT)   // the HUD row's 8 tiles (the queue copies from WRAM; Duke's staging buffer is here too)

enum { SU_WALK, SU_TELL, SU_CHARGE, SU_HMPH, SU_KNOCK, SU_OUT };

typedef struct {
    uint8_t  phase;      // SU_* (tests)
    uint8_t  t;          // frames in the phase
    uint8_t  cyc;        // the meter's target now: 6, 5 ... 1 (tests)
    uint8_t  flash;      // frames the full meter still blinks
    uint8_t  old;        // the target that just filled
    uint8_t  knock;      // px of knock-back still to go (tests)
    uint8_t  cycles;     // meters filled this fight (tests)
    uint8_t  cancels;    // charges called off by a cup (tests)
    uint8_t  charges;    // charges made (tests)
    uint8_t  period;     // frames per step (the row's step, HARD's)
    uint8_t  beat_f;     // frames into the period
    uint16_t last_mf;    // music_frames at the last look
    uint8_t  pose_t;     // frames of the hit pose left
    uint8_t  ent;        // the entrance: 0 none (or over), else the next frame's number + 1 (tests)
    uint8_t  out;        // 1: the ring-out has happened (he is gone)
    uint8_t  shown;      // the HUD's key as last drawn (255: draw again)
} sumo_t;
#define sumo (*(sumo_t *)BOSS_OWN)
typedef char sumo_own_fits[sizeof(sumo_t) <= BOSS_OWN_N ? 1 : -1];   // (his state is in BOSS_OWN: boss.h; sizeof, not a number typed twice)
#if 8 > SCR_CAP_N || SOLO_BG + 2 > BOSS_MARK_BG
#error "the Sumo's HUD row buffer or its one-pip tiles"
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

// The meter: sumo.cyc pips, boss_hp of them still to fill (a pip a cup, left to right), 2 a tile; a full meter blinks (full /
// blank) as the old target. Drawn when its key changes (the engine's boss_hud draws its own after a test hook: BEV_TELL
// asks for a redraw).
static void hud(void) {
    uint8_t *h = SUMO_HUD, n = sumo.cyc, f, k, t, key;
    f = boss_hp > n ? 0 : n - boss_hp;
    if (sumo.flash) { n = sumo.old; f = n; }
    key = boss_hp + (sumo.cyc << 3) + (sumo.flash ? 64 + ((sumo.flash & 4) << 5) : 0);
    if (key == sumo.shown) return;
    sumo.shown = key;
    h[0] = BOSS_HUD_BG;
    for (k = 0; k < 7; k++) {
        t = 2 * k;
        if (t + 1 < n) h[1 + k] = BOSS_HUD_BG + (f >= t + 2 ? 3 : f > t ? 2 : 1);
        else if (t < n) h[1 + k] = SOLO_BG + (f > t);
        else h[1 + k] = TILE_HUD_BLANK;
        if (sumo.flash && (sumo.flash & 4) && h[1 + k] != TILE_HUD_BLANK) h[1 + k] = TILE_HUD_BLANK;
    }
    vq_add(0, h, 12, HUD_ROW, 8);
}

static void to_walk(void) {
    sumo.phase = SU_WALK; sumo.t = 0;
    boss_special_t = SUMO_EVERY;
    boss_xpose = sumo.out ? BP_HIDE : 0;
    if (boss_state == BS_TELL || boss_state == BS_SPECIAL) boss_state = BS_WALK;
}

static void to_tell(void) {
    sumo.phase = SU_TELL; sumo.t = 0;
    boss_special_t = 0;
    boss_xpose = BP_SHIKO;
    sumo.pose_t = 0;
}

// He moves to x (a multiple of 8) at once, his columns redrawn: the knock-back's hops and the entrance's steps (boss.c's
// boss_move is private, and boss_advance's stomp timer only counts down once the intro is over).
static void move_to(uint8_t x) {
    uint8_t oc = boss_col, nc = x >> 3;
    boss_x = x; boss_col = nc;
    if (nc < oc) mark_dirty_attrs(boss_bar, nc, oc + 5);
    else mark_dirty_attrs(boss_bar, oc, nc + 5);
}

// The meter is full: the knock-back begins, and the next target (one fewer, never under 1) starts empty.
static void filled(void) {
    sumo.cycles++;
    sumo.old = sumo.cyc; sumo.flash = SUMO_FLASH;
    if (sumo.cyc > 1) sumo.cyc--;
    boss_hp = sumo.cyc;
    sumo.knock = SUMO_KNOCK;
    sumo.phase = SU_KNOCK; sumo.t = 0;
    boss_special_t = 0;
    boss_xpose = BP_WINCE;
    boss_state = BS_SPECIAL;
    SFX(SFX_DON);
}

static void to_out(void) {
    sumo.phase = SU_OUT; sumo.t = 0;
    sumo.knock = 0;
    SFX(SFX_DON);
}

// ---- the entrance ----
#define SE_IN        20                 // he walks in from the left wall
#define SE_STEP      12                 // frames per heavy step (x 0 -> 24: steps at SE_IN + 12, 24, 36)
#define SE_SALT      68                 // the leg goes up, the salt flies (20 frames)
#define SE_STAMP1    88                 // the first stamp
#define SE_LEG2     104
#define SE_STAMP2   120                 // the second, harder
#define SE_BOW      136
#define SE_END      148                 // the ritual is over
#define SE_TAIL      30                 // intro frames left for the fight to start
#define SE_SALT_N    20
#define SE_DUST_N    12
#define SE_SHAKE1     6                 // frames the picture shakes after stamp 1 (2 px), stamp 2 (3 px: 10)
#define SE_SHAKE2    10

static void shake(uint8_t t) {          // the picture's jolt: SCY 0 / 2 on stamp 1's frames, 0 / 3 on stamp 2's
    uint8_t k = 0;
    if (t >= SE_STAMP1 && t < SE_STAMP1 + SE_SHAKE1) k = (t & 1) ? 2 : 0;
    else if (t >= SE_STAMP2 && t < SE_STAMP2 + SE_SHAKE2) k = (t & 1) ? 3 : 0;
    SCY_REG = k;
}

// BEV_INTRO: the ritual's clock. The player is held (the bartender at bar 0's tap, nothing poured) and no cup may be his.
static void ent_frame(void) {
    uint8_t t = sumo.ent - 1;
    fill_timer = 0; fill_stage = 0;                          // (the bartender stays where he is: main.c skips his input while he is held)
    bartender_frame = BT_IDLE; catch_pose = 0; bt_bob = 0;
    if (t < SE_END) intro_timer = INTRO_FRAMES;           // (held until the ritual is over)
    if (t == 0) {
        boss_cap = 0;                                      // (no catch: boss_limit)
        boss_to_bar(boss_bar, 0);                          // hidden (BEV_RESET: BP_HIDE), at the wall
        SFX(SFX_DON);
    } else if (t == SE_IN) {
        boss_xpose = BP_WALK;                              // he is there: standing at the left wall
        mark_dirty_attrs(boss_bar, 0, 20);
    } else if (t == SE_IN + SE_STEP || t == SE_IN + 2 * SE_STEP || t == SE_IN + 3 * SE_STEP) {
        move_to(boss_x + 8);
        boss_xpose = BP_STOMP;
        SFX(SFX_SHAKE);
    } else if (t == SE_SALT) {
        boss_xpose = BP_SHIKO;
        SFX(SFX_KA);
    } else if (t == SE_STAMP1 || t == SE_STAMP2) {
        boss_xpose = BP_STOMP;
        SFX(SFX_SHAKE); SFX(SFX_DON);
        if (t == SE_STAMP2) SFX(SFX_KA);
    } else if (t == SE_LEG2) {
        boss_xpose = BP_SHIKO;
    } else if (t == SE_BOW || t == SE_STAMP1 + 8 || t == SE_STAMP2 + 8
               || t == SE_IN + SE_STEP + 6 || t == SE_IN + 2 * SE_STEP + 6 || t == SE_IN + 3 * SE_STEP + 6) {
        boss_xpose = BP_WALK;
    }
    shake(t);
    if (t >= SE_END) {
        SCY_REG = 0;
        boss_cap = CAP_ANY;
        boss_state = BS_WALK; boss_xpose = BP_WALK;
        intro_timer = SE_TAIL;
        sumo.ent = 0;
        to_walk();
        beat_sync();
        return;
    }
    sumo.ent++;
}

// BEV_DRAW: the salt and the dust, two OAM entries (the perfect cue's and the coin's: neither is on screen in a fight's
// intro), the dust puff's frames from OBJ_DUST (frame 2 is the scatter: the salt), drawn last (boss_draw)
static void ent_draw(void) {
    OAM_item_t *a = shadow_OAM + OAM_CUE, *b = shadow_OAM + OAM_COIN;
    uint8_t t, y = bar_oam_y[boss_bar], prop = is_cgb ? OBJPAL_BARTENDER : 0, k;
    int8_t d;
    a->y = 0; b->y = 0;
    if (sumo.ent < 2) return;
    t = sumo.ent - 2;
    if (t >= SE_SALT && t < SE_SALT + SE_SALT_N) {         // the toss: his hand (right of him), over the counter
        k = t - SE_SALT;
        d = (int8_t)(((int16_t)(k - 8) * (k - 8) * 3) >> 4) - 12;
        a->y = y + d; a->x = boss_x + 8 + 34 + 2 * k; a->tile = OBJ_DUST + 4; a->prop = prop;
        if (k > 3) {
            k -= 3;
            d = (int8_t)(((int16_t)(k - 8) * (k - 8) * 3) >> 4) - 12;
            b->y = y + d + 4; b->x = boss_x + 8 + 38 + 2 * k; b->tile = OBJ_DUST + 4; b->prop = prop;
        }
    } else if ((t >= SE_STAMP1 && t < SE_STAMP1 + SE_DUST_N) || (t >= SE_STAMP2 && t < SE_STAMP2 + SE_DUST_N)) {
        k = (t - (t >= SE_STAMP2 ? SE_STAMP2 : SE_STAMP1)) >> 2;     // the puff opens: frames 0, 1, 2
        a->y = y + 8; a->x = boss_x + 8 + 2; a->tile = OBJ_DUST + 2 * k; a->prop = prop | S_FLIPX;
        b->y = y + 8; b->x = boss_x + 8 + 30; b->tile = OBJ_DUST + 2 * k; b->prop = prop;
    }
}

uint8_t boss_sumo(uint8_t ev, uint8_t arg) BANKED {
    switch (ev) {
    case BEV_SET:
        boss_art_set();
        sumo.period = boss_step;                 // (192, HARD 144: whole rows of the teahouse tune)
        boss_step = 0;                           // the engine's stomp timer off: he steps on the beat (below)
        boss_cap = CAP_ANY;                      // no drink limit
        sumo.cyc = SUMO_START; boss_hp = SUMO_START;
        sumo.cycles = sumo.cancels = sumo.charges = 0;
        sumo.out = 0; sumo.ent = 0; sumo.flash = 0;
        sumo.shown = 255;
        /* fall through */
    case BEV_RESET:
        sumo.pose_t = 0; sumo.knock = 0; sumo.flash = 0;
        sumo.shown = 255;
        SCY_REG = 0;
        to_walk();
        if (sumo.ent) { boss_state = BS_JUMP; boss_xpose = BP_HIDE; }   // (the entrance: not on his bar yet)
        beat_sync();
        break;
    case BEV_LOAD:
        boss_art_load();
        boss_ld(2, SOLO_BG, 2, boss_meter_tiles, CURRENT_BANK);   // the one-pip tiles: the engine's EMPTY / HALF pint on the left, the band's colour on the right (kind 2: each byte & 0xF0 | 0x0F)
        break;
    case BEV_ENTER:                              // (E9: after the warm-up) the ritual
        sumo.ent = 1;
        return 1;
    case BEV_INTRO:
        if (sumo.ent) ent_frame();
        break;
    case BEV_DRAW:
        if (sumo.ent || shadow_OAM[OAM_COIN].y) ent_draw();
        break;
    case BEV_BEGIN:
        sumo.shown = 255;
        hud();
        break;
    case BEV_TELL:
        if (sumo.phase == SU_WALK) to_tell();
        sumo.shown = 255;                        // (the engine draws its own meter after a test hook)
        break;
    case BEV_CATCH:                              // he takes every cup himself: no hands rule
        perfect_catch(arg);
        mug_state[arg] = MUG_FREE;
        add_score(serve_score);
        SFX(SFX_SERVE);
        if (boss_hold < CAP_ANY - 1 && !boss_hold++) boss_sip_t = 0;
        boss_hits++;
        if (sumo.phase == SU_KNOCK || sumo.phase == SU_OUT) {
            if (boss_hp > 1) boss_hp--;          // (a cup in the stagger: a pip, never the end of the meter)
        } else {
            if (sumo.phase == SU_TELL) {         // the charge called off
                sumo.phase = SU_HMPH; sumo.t = 0;
                boss_xpose = BP_HMPH;
                sumo.cancels++;
            } else if (sumo.phase == SU_WALK) {
                boss_xpose = BP_GULP;            // the hit pose (he does not stop)
                sumo.pose_t = SUMO_HIT_POSE;
            }
            if (boss_hp) boss_hp--;
            if (!boss_hp) filled();
        }
        return 1;
    case BEV_OUTRO:
        sumo.phase = SU_WALK; sumo.flash = 0; sumo.knock = 0;
        boss_xpose = sumo.out ? BP_HIDE : 0;
        if (sumo.out) shadow_OAM[OAM_DANCERS].y = 0;   // (the topper: boss_draw may not run again before the outro's screens)
        sumo.shown = 255;
        hud();
        SCY_REG = 0;
        break;
    case BEV_FRAME:
        if (sumo.t != 255) sumo.t++;
        if (sumo.flash) sumo.flash--;
        if (sumo.pose_t && !--sumo.pose_t && boss_xpose == BP_GULP) boss_xpose = 0;
        if (beat() && sumo.phase == SU_WALK && boss_state == BS_WALK) boss_advance();
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
        case SU_KNOCK:
            if (sumo.knock && !(sumo.t % SUMO_HOP)) {
                move_to(boss_x - 8);
                sumo.knock -= 8;
                if (!boss_x) { to_out(); break; }
            }
            if (sumo.t >= SUMO_STAGGER) to_walk();
            break;
        case SU_OUT:
            if (sumo.t >= SUMO_OUT) {
                sumo.out = 1;
                boss_hp = 0;                     // out: the engine's outro takes it from here
                SFX(SFX_SERVE); SFX(SFX_KA);
            }
            break;
        }
        if (sumo.phase == SU_TELL && boss_state == BS_WALK) boss_state = BS_TELL;   // (he stands)
        else if (sumo.phase >= SU_CHARGE && (boss_state == BS_WALK || boss_state == BS_TELL)) boss_state = BS_SPECIAL;
        hud();
        break;
    }
    return 0;
}
