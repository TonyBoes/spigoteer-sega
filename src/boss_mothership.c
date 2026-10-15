// The Mothership, the space lounge's boss (docs/minigames_bosses.md 3.10; art approved 2026-10-11: look A "silver saucer").
// His row is boss.c rows[9]: 40 px (the saucer 32 + the grab arm 8), start x 16, bar 1, step 100, push 8, gulp 24, hands 2,
// sip 45, meter 14 = phase 1's 8 drinks + phase 2's 6 (the doc's proposal: 14 drinks, the most of any boss).
//
// PHASE 1, the saucer. He hovers and stomps like any boss (the STOMP pose is the bob). Every MS_EVERY frames of walking:
//   1. TELL, MS_TELL frames: the antenna blinks (HAT_BOB every 4 frames), he stands (BS_TELL). A random other bar is the target and
//      the landing x one of 16 / 32 / 48 (boss_mark: the BEAM, a 16 px column of BG tiles under where the saucer will be, drawn over
//      the target bar's patrons); the regulars stop coming to the target bar (boss_pattern).
//   2. WAIT (as the Mascot): he teleports only when the tell has run AND every full mug that was on his bar when it began has
//      reached him (at most MS_WAITMAX more frames).
//   3. GONE, MS_GONE frames (BS_JUMP, BP_HIDE): no body, no topper, nothing caught.
//   4. He is on the target bar at the landing x (boss_to_bar: its regulars scared off, meter and hands along), walking again.
// PHASE 2, at meter 6 (the eighth drink): FLASH, MS_FLASH frames of the HAPPY pose blinking with the hover (the lights glow magenta;
// the burp bubble), he stands (a glass thrown in it is still drunk, but the meter is set to 6 at the split whatever it did). Then the split: the saucer is gone for good and three mini aliens
// stand on three different bars at x 24 (the saucer's bar first), hurried (patron_hurry: 1.5x the level's speed). Each wants
// TWO drinks and is served out wherever he stands when the second lands (the first push-back is the doc's 16 px, and a mini
// pushed to the left end by it is NOT served early: the engine's "pushed back to ENTRY_X is served" is held off for the first
// drink; they come in at x 24, not the doc's 16, so that a glass thrown the moment they appear cannot serve them early). All three served: the meter is empty and the outro plays. A mini at the tap costs a life like any patron; after
// the freeze the remaining minis come back in at x 24. The HUD meter shows the drinks still wanted (2 a mini, less the ones
// a mini has had). Regulars keep coming at half the rate (the spawn interval doubled).
// Changes from the doc, for the engine (PLAN.md "Mothership as built"):
//   - variant C's tiles are the saucer's body in phase 1 (25 column pairs do not fit the doc's 23 free ids), so the split
//     reloads the group's whole patron tile set and variant C's palettes with the LCD off for a frame (the minis' art);
//   - he stays in the engine as a hidden boss on a bar of his own (the one bar without a mini, boss_to_bar): the engine's "his
//     bar is his" rule needs one, so a glass thrown on that bar is never caught and breaks (the player's mistake), and no
//     regular or mini comes to it;
//   - the minis are not made by the boss engine's regulars: every regular on the screen is cleared in the reload's blank frame.
// E7 (owner 2026-10-15: "not threatening for the last boss"), phase 1 only:
//   PASSENGERS: every landing releases two alien passengers (ordinary patrons, variant A / B) at x 24 on two bars that are not his
//     (a bar whose entry is crowded is skipped; none while 12 patrons are live: the 16 slots keep a margin). They are served like
//     any patron, count for CLEAR THE BAR, cost a life at the tap; the split wipes them with the rest of the screen.
//   STUN RAY: the bartender stays on one bar RAY_STAY frames: the ship CHARGEs RAY_CHARGE frames (the HAPPY pose, the antenna
//     blinking, SFX_REV, and the beam column blinking on HIS bar under his feet, faster for the last half); if he is still on
//     that bar the beam fires (the GULP pose, SFX_KA) and he is STUNned RAY_STUN frames (BT_FAIL, no walk / bar change / pour:
//     joy is overwritten so next frame's `pressed` is empty, and his place is put back every frame; mugs keep sliding). Any bar
//     change in the charge dodges it. The teleport clock waits while the ray cycle runs.
//   ENTRANCE (BEV_LOAD, the fight's first start, BEV_INTRO as Duke's): the beam lights on his bar, the lights flicker (CGB the bar
//     palettes dim, DMG BGP), a hum, then he blinks into the beam and lands (ENT_LAND frames), then the intro's 90 frames.
// Test hooks (WRAM: his state is the struct mothership_t in BOSS_OWN, no variable of his own): mothership.phase, .minis, ...
#pragma bank 255
#include "boss.h"
#include "boss_mothership_art.h"
#include "boss_load.h"
#include "music.h"

extern uint8_t cur_group;

#define HAT_BOB_T       2                // topper tile offset: HAT_BOB (the antenna lit, no stomp bob)
#define MS_BAR          1                // his home bar (boss.c rows[9])
#define MS_X           16                // and start x
#define MS_EVERY      300                // frames of walking between two teleports
#define MS_TELL        60
#define MS_WAITMAX     60
#define MS_GONE        10
#define MS_FLASH       40
#define MS_BLINK        4                // the flash's and the antenna's half period
#define SPLIT_HP        6                // the meter at the split: phase 2's 6 drinks (3 minis x 2)
#define MINI_X         24                // ENTRY_X + 8: a first drink never pushes one into the engine's served-at-the-left-end
#define MINI_PUSH      16                // the minis' push-back per drink (px)
#define MINIS           3
#define MINI_VARIANT    2                // patron variant C: only the minis (a fight's regulars are A / B)
#define ENTRY_PLUS      1
#define DROPS           2                // passengers per landing
#define DROP_X         24                // (as the minis' entry)
#define DROP_CROWD     40                // a patron left of this on the bar: the entry is crowded
#define LIVE_MAX       12                // no passenger while this many patrons are live
#define RAY_STAY      270                // frames on one bar before the ship takes aim
#define RAY_CHARGE     60
#define RAY_STUN       90
#define RAY_BEAM       14                // frames the beam stays lit in the stun (the GULP pose)
#define CALM_RAY        1                // ms.calm bits (tests): no ray, no passengers
#define CALM_DROP       2
#define ENT_LAND       64                // the entrance: the landing frame (0-43 the beam and the flicker, 44-63 he blinks in)
#define ENT_BLINK      44
#define ENT_HUM        20
#define DIM_BGP      0xF9
#define DIM_MASK   0x3DEF                // (c >> 1) & mask: each 5 bit channel halved
#if BOSS_ART_COLS != 5 || BOSS_ART_FX != 4
#error "Mothership: a 40 px body and the beam's two column pairs"
#endif

enum { MP_WALK, MP_TELL, MP_WAIT, MP_GONE, MP_FLASH, MP_MINIS };
enum { RY_IDLE, RY_CHARGE, RY_STUN };
extern uint8_t joy;

typedef struct {
    uint8_t phase;      // MP_* (tests)
    uint8_t t;          // frames in the phase (stops at 255)
    uint8_t target;     // the bar he will teleport to (tests)
    uint8_t land;       // the landing x (tests)
    uint8_t jumps;      // teleports made this fight (tests)
    uint8_t wm;         // the earlier mugs are those on his bar at x <= wm (it falls MUG_SPEED_FULL a frame, as they do)
    uint8_t minis;      // phase 2: minis still to be served (3..0)
    uint8_t dead;       // phase 2: his hidden bar (no mini, no regular)
    uint8_t ray;        // RY_* (tests)
    uint8_t rt;         // frames in the ray's state
    uint16_t stay;      // frames the bartender has been on bar sbar (tests)
    uint8_t sbar;       // the bar he is counted on (the stun holds him there)
    uint8_t sx;         // his x when stunned
    uint8_t stuns;      // stuns this fight (tests)
    uint8_t drops;      // passengers released this fight (tests)
    uint8_t ent;        // the entrance: 0 none (or over), else the next frame's number + 1 (tests)
    uint8_t calm;       // CALM_* (tests)
} mothership_t;
#define ms (*(mothership_t *)BOSS_OWN)
#if 18 > BOSS_OWN_N
#error "the Mothership's state: BOSS_OWN_N"
#endif

static const uint8_t land_x[3] = { 16, 32, 48 };

static void to_walk(void) {
    ms.phase = MP_WALK; ms.t = 0;
    boss_special_t = MS_EVERY;
    boss_xpose = 0;
    BOSS_TOPPER_T = 0;
    boss_mark(BOSS_NONE, 0);
    if (boss_state != BS_OUTRO) boss_state = BS_WALK;
}

static void to_tell(void) {
    uint8_t i, r, wm = 0;
    ms.phase = MP_TELL; ms.t = 0;
    boss_special_t = 0;
    do r = next_rand() & 3; while (r == boss_bar);
    ms.target = r;
    do r = next_rand() & 3; while (r == 3);
    ms.land = land_x[r];
    boss_mark(ms.target, (ms.land >> 3) + 2);           // (under the saucer's middle: columns 2, 3 of its 5)
    boss_pattern(ms.target);
    for (i = 0; i != MAX_MUGS; i++)                       // the mugs already on his bar: the rightmost is the watermark
        if (mug_state[i] == MUG_FULL && mug_bar[i] == boss_bar && mug_x[i] > wm) wm = mug_x[i];
    ms.wm = wm;
    boss_state = BS_TELL;
    SFX(SFX_SHAKE);
}

// The earlier mugs still on their way to him (on his bar, at or left of the watermark, right of his catching edge).
static uint8_t waiting(void) {
    uint8_t i, edge = boss_x + boss_width();
    for (i = 0; i != MAX_MUGS; i++)
        if (mug_state[i] == MUG_FULL && mug_bar[i] == boss_bar && mug_x[i] <= ms.wm && mug_x[i] >= edge) return 1;
    return 0;
}

static void vanish(void) {
    ms.phase = MP_GONE; ms.t = 0;
    boss_state = BS_JUMP;
    boss_push = 0;
    boss_xpose = BP_HIDE;
    BOSS_TOPPER_T = 0;
}

static void drop_passengers(void);

static void land(void) {
    boss_xpose = 0;
    boss_state = BS_WALK;
    boss_mark(BOSS_NONE, 0);
    boss_to_bar(ms.target, ms.land);
    SFX(SFX_SHAKE);
    ms.jumps++;
    ms.stay = 0; ms.sbar = bar;
    drop_passengers();
    to_walk();
}

// ---- the stun ray ----
// The bartender held where he is (a stun, the entrance): joy is overwritten, so next frame's `pressed` is only START (the pause
// stays his), and his place and pour are put back every frame; `frame` is his pose.
static void hold(uint8_t frame) {
    joy = 0x7F;
    bar = ms.sbar; bartender_x = ms.sx; bartender_frac = 0;
    fill_timer = 0; fill_stage = 0; catch_pose = 0; bt_bob = 0; facing = 0;
    bartender_frame = frame;
}

// The beam column on his bar under his feet (on) or away.
static void beam_on(uint8_t on) {
    uint8_t c = (bartender_x + 4) >> 3;
    if (on) { if (BOSS_MARK_BAR != bar || BOSS_MARK_COL != c) boss_mark(bar, c); }
    else if (BOSS_MARK_BAR != BOSS_NONE) boss_mark(BOSS_NONE, 0);
}

// The ray's cycle ends (dodged, over, or the ship has other things to do): the count starts again on this bar.
static void ray_off(void) {
    if (ms.ray) {
        ms.ray = RY_IDLE;
        boss_mark(BOSS_NONE, 0);
        boss_xpose = 0;
        BOSS_TOPPER_T = 0;
    }
    ms.stay = 0; ms.sbar = bar;
}

// Phase 1, every frame: count his time on one bar, charge, fire, stun.
static void ray_frame(void) {
    uint8_t r;
    if (ms.ray != RY_STUN && bar != ms.sbar) ray_off();                      // a bar change: counted afresh, a charge dodged
    if (ms.ray == RY_IDLE) {
        if (ms.stay != 0xFFFF) ms.stay++;
        if (ms.stay >= RAY_STAY && ms.phase == MP_WALK && !(ms.calm & CALM_RAY)) { ms.ray = RY_CHARGE; ms.rt = 0; SFX(SFX_REV); }
        return;
    }
    r = ++ms.rt;
    if (ms.ray == RY_CHARGE) {
        boss_xpose = BP_HAPPY;
        BOSS_TOPPER_T = r & 4 ? HAT_BOB_T : 0;
        beam_on(!(r & (r < RAY_CHARGE / 2 ? 8 : 4)));
        if (r < RAY_CHARGE) return;
        ms.ray = RY_STUN; ms.rt = 0; ms.sx = bartender_x; ms.stuns++;            // he is still here: the beam fires
        beam_on(1);
        boss_xpose = BP_GULP;
        BOSS_TOPPER_T = 0;
        SFX(SFX_KA);
    } else if (r == RAY_BEAM) {
        beam_on(0);
        boss_xpose = 0;
    } else if (r >= RAY_STUN) { ray_off(); return; }
    hold(BT_FAIL);
}

// ---- the passengers ----
// Two alien passengers off the ship, on the two bars that are not his and have the fewer patrons (the busiest of the three gets
// none: the load spreads), if the bar's entry is clear and the slots allow.
static void drop_passengers(void) {
    uint8_t p, b, k = next_rand(), live = 0, n = DROPS, i, crowd[NUM_BARS], cnt[NUM_BARS], busy = BOSS_NONE;
    if (ms.calm & CALM_DROP) return;
    for (b = 0; b != NUM_BARS; b++) crowd[b] = cnt[b] = 0;
    for (p = 0; p != MAX_PATRONS; p++) {
        if (!patron_state[p]) continue;
        live++;
        b = patron_bar[p] & (NUM_BARS - 1);
        if (patron_state[p] != PATRON_LEAVING) cnt[b]++;
        if (patron_x[p] < DROP_CROWD) crowd[b] = 1;
    }
    for (i = 0; i != NUM_BARS; i++) {                     // (from a random bar: a tie for busiest is broken by chance)
        b = (k + i) & (NUM_BARS - 1);
        if (b != boss_bar && (busy == BOSS_NONE || cnt[b] > cnt[busy])) busy = b;
    }
    for (b = 0; b != NUM_BARS && n && live < LIVE_MAX; b++) {
        if (b == boss_bar || b == busy || crowd[b]) continue;
        if (!add_patron(b, DROP_X, next_rand() & 1)) continue;
        n--; live++; ms.drops++;
    }
    if (n != DROPS) SFX(SFX_COIN);
}

// ---- the entrance ----
// The room's lights: CGB the bar palette (its wall and counter) halved or back, DMG the BG's shades.
static void lights(uint8_t dim) {
    palette_t p;
    uint8_t i;
    if (!is_cgb) { BGP_REG = dim ? DIM_BGP : 0xE4; return; }
    for (i = 0; i != 4; i++) p[i] = dim ? (venue.pal[VENUE_PAL_BAR][i] >> 1) & DIM_MASK : venue.pal[VENUE_PAL_BAR][i];
    set_bkg_palette(BGPAL_BAR, 1, p);
}

// BEV_INTRO every frame while intro_timer runs: the tractor beam's column on his bar, the lights flicker, a hum, he blinks into
// the beam and lands. The bartender is held (idle) and the intro's clock waits until he has landed.
static void ent_frame(void) {
    uint8_t f = ms.ent - 1;
    if (!f) { ms.sbar = bar; ms.sx = bartender_x; SFX(SFX_WHOOSH); boss_mark(boss_bar, (MS_X >> 3) + 2); }
    hold(BT_IDLE);
    if (f < ENT_LAND) intro_timer = INTRO_FRAMES;
    if (f == ENT_HUM) SFX(SFX_REV);
    if (f < ENT_BLINK) { if (f >= 4 && !(f & 3)) lights((f >> 2) & 1); }
    else if (f < ENT_LAND) {                                  // (the beam fades as he blinks in: it would hide half of him)
        if (f == ENT_BLINK) { lights(0); boss_mark(BOSS_NONE, 0); }
        boss_xpose = f & 2 ? BP_HAPPY : BP_HIDE;
    }
    else {
        lights(0);
        boss_mark(BOSS_NONE, 0);
        boss_xpose = 0; boss_state = BS_WALK;
        boss_to_bar(boss_bar, MS_X);
        to_walk();
        SFX(SFX_SHAKE);
        intro_timer = INTRO_FRAMES - 1;                  // (as the level's first frame leaves it)
        ms.ent = 0;
        return;
    }
    ms.ent++;
}

static void to_flash(void) {
    ray_off();
    ms.phase = MP_FLASH; ms.t = 0;
    boss_special_t = 0;
    boss_mark(BOSS_NONE, 0);
    BOSS_TOPPER_T = 0;
    SFX(SFX_SERVE);
}

// One mini on bar b at MINI_X, hurried: the first free patron slot.
static void put_mini(uint8_t b) {
    uint8_t p = 0;
    while (patron_state[p] != PATRON_NONE) if (++p == MAX_PATRONS) return;
    if (!add_patron(b, MINI_X, MINI_VARIANT)) return;
    patron_hurry[p] = 1;                                  // (1: alive; 2: served and counted, minis_frame)
}

// The minis still to be served, one to a bar that is not his hidden one (first: the bar that goes first, or BOSS_NONE).
static void add_minis(uint8_t first) {
    uint8_t n = ms.minis, b;
    if (first != BOSS_NONE && n) { put_mini(first); n--; }
    for (b = 0; b != NUM_BARS && n; b++)
        if (b != ms.dead && b != first) { put_mini(b); n--; }
}

// The split: the group's patron tiles (variant C's, the minis' art, over the saucer's body) and variant C's palettes with the LCD
// off (the frame goes white: every regular is gone with it), his hidden bar chosen, the three minis in.
static void split(void) {
    uint8_t p, old = boss_bar, f;
    palette_t pal;
    do f = next_rand() & 3; while (f == old);
    ms.dead = f;
    display_off();
    load_patron_tiles(cur_group, PATRON_TILE_BASE);
    if (is_cgb) {
        patron_pal_get(cur_group, MINI_VARIANT, pal);
        pal[0] = venue.pal[VENUE_PAL_BAR][0];
        set_bkg_palette(BGPAL_PATRON + MINI_VARIANT, 1, pal);
        pal[0] = 0;
        set_sprite_palette(OBJPAL_PATRON_C, 1, pal);
    }
    for (p = 0; p != MAX_PATRONS; p++) if (patron_state[p]) remove_patron(p);
    LCDC_REG |= LCDCF_ON;
    boss_hold = 0; boss_queue = 0; boss_push = 0;
    boss_state = BS_JUMP;
    boss_xpose = BP_HIDE;
    BOSS_TOPPER_T = 0;
    boss_to_bar(f, MS_X);                                 // (his bar's wall is plain again; no regular comes to his hidden bar)
    start_per_bar = 0;                                    // (a life lost: no regulars standing where the minis come in)
    spawn_interval <<= 1;                                 // regulars at half the rate
    pushback_px = MINI_PUSH;
    if (!hurry_speed) hurry_speed = patron_speed + (patron_speed >> 1);
    ms.phase = MP_MINIS; ms.t = 0;
    ms.minis = MINIS;
    boss_hp = SPLIT_HP;
    add_minis(old);
    boss_hud_now();
}

// Phase 2, every frame: count the minis served, serve the ones with a second drink, hold off the early served-out, and show the
// drinks still wanted. 0 minis left: the meter is empty (boss.c boss_frame: the outro).
static void minis_frame(void) {
    uint8_t p, st, want, left = ms.minis;
    for (p = 0; p != MAX_PATRONS; p++) {
        st = patron_state[p];
        if (st == PATRON_NONE || patron_variant[p] != MINI_VARIANT || patron_hurry[p] != 1) continue;
        if ((st == PATRON_PUSHED || st == PATRON_DRINKING) && patron_drinks[p] >= 2) {   // the second drink: served out wherever he stands
                                                              // (DRINKING too: a push that stops at once, patrons.c push_for, never shows PUSHED)
            patron_state[p] = PATRON_LEAVING; patron_aux[p] = 0; patron_timer[p] = 0;
            add_score(serve_score);
            SFX(SFX_SERVE);
            st = PATRON_LEAVING;
        } else if (st == PATRON_PUSHED && patron_aux[p] && patron_x[p] <= ENTRY_X + ENTRY_PLUS) {
            patron_aux[p] = 0;                                   // (pushed to the left end by the first drink: he drinks there)
        }
        if (st == PATRON_LEAVING) { patron_hurry[p] = 2; left--; }   // (engine-served ones count too)
    }
    ms.minis = left;
    want = left << 1;
    for (p = 0; p != MAX_PATRONS; p++) {
        st = patron_state[p];
        if (st == PATRON_NONE || st == PATRON_LEAVING || patron_variant[p] != MINI_VARIANT || patron_hurry[p] != 1) continue;
        want -= patron_drinks[p] > 1 ? 1 : patron_drinks[p];
    }
    if (want != boss_hp) { boss_hp = want; boss_hud_now(); }
}

uint8_t boss_mothership(uint8_t ev, uint8_t arg) BANKED {
    (void)arg;
    switch (ev) {
    case BEV_SET:
        boss_art_set();
        ms.jumps = 0; ms.minis = 0; ms.dead = BOSS_NONE;
        ms.ray = RY_IDLE; ms.stay = 0; ms.sbar = 0; ms.stuns = 0; ms.drops = 0; ms.ent = 0; ms.calm = 0;
        to_walk();
        break;
    case BEV_RESET:
        ray_off();
        if (ms.ent) { boss_state = BS_JUMP; boss_xpose = BP_HIDE; break; }   // (the entrance: not on his bar yet)
        if (ms.phase >= MP_MINIS) {                           // phase 2: the minis not served yet come back in
            boss_state = BS_JUMP;
            boss_xpose = BP_HIDE;
            add_minis(BOSS_NONE);
            break;
        }
        if (ms.phase == MP_FLASH) { ms.t = 0; break; }        // (a life lost in the flash: it starts again, where he is)
        if (boss_bar != MS_BAR) boss_to_bar(MS_BAR, MS_X);
        to_walk();
        break;
    case BEV_LOAD:
        boss_art_load();
        ms.ent = 1;                                           // (the first start's entrance; a lost life does not load again)
        break;
    case BEV_INTRO:
        if (ms.ent) ent_frame();
        break;
    case BEV_TELL:
        if (ms.phase == MP_WALK) { ray_off(); to_tell(); }
        break;
    case BEV_OUTRO:
        ray_off();
        if (ms.phase < MP_FLASH) to_walk();
        else if (ms.phase == MP_FLASH) boss_xpose = 0;
        break;
    case BEV_FRAME:
        if (ms.t != 255) ms.t++;
        if (ms.phase < MP_FLASH && boss_hp <= SPLIT_HP && boss_hp && boss_state != BS_OUTRO) to_flash();
        if (ms.phase < MP_FLASH) ray_frame();
        switch (ms.phase) {
        case MP_WALK:
            if (!ms.ray && boss_special_t && !--boss_special_t) to_tell();
            break;
        case MP_TELL:
        case MP_WAIT:
            ms.wm = ms.wm > MUG_SPEED_FULL ? ms.wm - MUG_SPEED_FULL : 0;
            BOSS_TOPPER_T = ms.t & MS_BLINK ? HAT_BOB_T : 0;
            if (ms.phase == MP_TELL && ms.t >= MS_TELL) ms.phase = MP_WAIT;
            if (ms.phase == MP_WAIT && (!waiting() || ms.t >= MS_TELL + MS_WAITMAX)) vanish();
            else if (boss_state == BS_WALK) boss_state = BS_TELL;   // (a gulp is over: he stands again)
            break;
        case MP_GONE:
            if (ms.t >= MS_GONE) land();
            break;
        case MP_FLASH:
            if (ms.t >= MS_FLASH) { split(); break; }
            boss_xpose = ms.t & MS_BLINK ? 0 : BP_HAPPY;
            if (boss_state == BS_WALK) boss_state = BS_SPECIAL;
            break;
        case MP_MINIS:
            minis_frame();
            break;
        }
        break;
    }
    return 0;
}
