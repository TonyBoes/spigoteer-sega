// The Prototype, the robot factory's boss (docs/minigames_bosses.md 3.8; art approved 2026-10-11, look B "the hauler").
// His row is boss.c rows[5]: 32 px, start x 16, bar 2, step 100, push 8, gulp 20, hands 2, sip 45, meter 12.
//
// One cycle (own.t counts its frames; he walks and drinks like any boss in GREEN, stands through the rest):
//   GREEN  0-239    the lamp on his antenna is solid, he takes batteries as ever.
//   YELLOW 240-299  the tell: the lamp is a ring (HAT frame LAMP_RING), he stands but still takes a battery.
//   RED    300-449  the lamp is an X, the RED pose (screen X, arm up), his bar's conveyor runs right (the approved K5 stripes + K6 arrows: tiles
//                   BOSS_ICE_BG, 2 frames, the counter's attributes the keg's palette 7, the counter row rewritten every 6 frames through the VBlank queue, the first write together with the attributes):
//                   every full battery on his bar turns round at once (MUG_RETURN, 1 px a frame to the right), and one
//                   that reaches him bounces the same way; the bartender catches a returned battery as an empty at the
//                   tap (it breaks past the tap end: a life). The fair-empties schedule (next_arrival) is pushed past
//                   every returned battery's arrival plus empty_gap, so no regular's empty is due with them. The last
//                   60 frames show the landing marker on the next bar (a random other bar; the Mascot's marker tiles)
//                   at his columns, and the regulars stop coming to it.
//   RIDE   450-459  the conveyor stops, his body is gone (BS_JUMP, BP_HIDE), nothing is caught or sent.
//   at 460 he appears on the marked bar at the same x (boss_to_bar: its regulars scared off, meter and hands with him)
//   and the cycle starts again in GREEN.
// A hit never happens in RED (a battery that reaches him bounces: no meter, no push-back). A lost life: the counter row is
// restored, he is back on bar 2 at x 16 in GREEN, the meter kept.
// CGB: the lamp's colour 2 is green (OBJ 7), yellow (OBJ 5) or red (OBJ 4) by phase (BOSS_TOPPER_PAL); DMG reads by shape.
// Test hooks (WRAM: his state is the struct prototype_t in BOSS_OWN): proto.t, and boss_light (the spec's name) is
// proto.t's phase: 0 green, 1 yellow, 2 red.
//
// ENTRANCE (E8, 2026-10-15; a PROPOSAL for the owner to judge, built like Duke's: BEV_INTRO + BEV_DRAW, the fight's first start
// only): "lowered by the overhead crane, then powers up". His body is sprites made from his own body tiles (the BG's column
// pairs, usable as 8x16 OBJ tiles: no new body art), hanging by his lamp from the crane's yoke (HOOK) and chain (CHAIN, stacked
// cells that run off the top of the screen): the crane lowers him 2.5 px a frame to his bar (frames 8-56), the clunk (SFX_SHAKE,
// frame 56), the yoke and chain rise away (60-83), the lamp is the red X (frames 0-83), blinks to the yellow ring with the first
// sparks (84; SFX_COIN), the body shaking, and lights solid green (96; SFX_EXTRA) with sparks all round (SPARK1 / SPARK2 at
// his shoulders, alternating every 2 frames from 84 to 110); at frame 124 boss_to_bar(boss_bar, 16) puts the BG body under the
// sprites (the engine's topper is the same lamp, green) and the intro's 90 frames start there (intro_timer is held until
// then). BS_JUMP + BP_HIDE meanwhile (nothing of his on his bar, no catch), the bartender held at bar 0's tap, no pouring.
// proto.t is the entrance's clock too: ENT_T0 + the next frame's number + 1 until it is over (then 0, as the fight starts).
// CGB: all eight OBJ palettes have a use in this fight, so the body sprites wear OBJ palette 5 (the yellow lamp's: his
// orange panels show yellow-orange until the BG body takes over); the yoke and chain only use colours 1 and 3.
// Tiles: CHAIN, HOOK, SPARK1 / SPARK2 = 5 pairs at OBJ 108-117 (the show's, none in a fight). OAM: at most 14 entries (5
// chain, 2 yoke, 4 body, the lamp, 2 sparks) in the mugs' entries (5-25).
#pragma bank 255
#include "boss.h"
#include "boss_prototype_art.h"
#include "boss_load.h"
BOSS_CAST_FN(boss_prototype_cast)   // the credits' cast card (src/credits.c)
#include "music.h"

#define BP_RED        BP_EXTRA           // gen_boss BOSSES prototype extra: RED
#define HAT_RING        4                // topper tile offsets (gen_boss `hats`): LAMP_RING, LAMP_X
#define HAT_X           6
#define PROTO_BAR       2                // his home bar (boss.c rows[5])
#define PROTO_X        16                // and start x
#define T_YELLOW      240
#define T_RED         300
#define T_MARK        390                // RED's last 60 frames
#define T_RIDE        450
#define T_LAND        460
#define ENT_T0       1000                // proto.t while the entrance runs (it is over, proto.t 0, when the fight starts)
#define ENT_DOWN0       8                // the crane starts lowering
#define ENT_CLUNK      56                // he is on his bar
#define ENT_UP0        60                // the yoke and chain rise
#define ENT_YELLOW     84                // the lamp's ring, the first sparks
#define ENT_GREEN      96                // the lamp is lit
#define ENT_SPARKS_END 110
#define ENT_LAND      124                // the last frame: his BG body under the sprites
#define ENT_OAM       (OAM_FILL + 1)     // the mugs' first entry: nothing is in the air during the entrance
#define ENT_OAM_N      16
#define CONV_COLS      18                // the counter's columns 0-17 (18-19: the keg)
#define CONV_EVERY      6                // frames per arrow step (the BEV_FRAME test below is written for 6)
#if BOSS_ART_CONV != 2 || BOSS_ART_CONV_SRC > 2
#error "the Prototype's conveyor: 2 frames, at most 2 counter tile ids"
#endif
#if ENT_OAM + ENT_OAM_N > OAM_MUG_END || BOSS_ART_SPR_PAIRS != 5 || BOSS_SPR_TILE0 != 108 || ENT_LAND > 250 || BOSS_ART_COLS != 4
#error "the Prototype's entrance: the OAM entries, the sprite tiles, the clock or a 32 px body"
#endif

typedef struct {
    uint16_t t;                          // frames in the cycle (tests)
    uint8_t  row[CONV_COLS];             // the conveyor's counter row, as last written
} prototype_t;
#define proto (*(prototype_t *)BOSS_OWN)
typedef char prototype_own_fits[sizeof(prototype_t) <= BOSS_OWN_N ? 1 : -1];   // (his state is in BOSS_OWN: boss.h; sizeof, not a number typed twice)

static uint8_t counter_y(void) {
    return BAR_COUNTER_ROW(boss_bar);
}

// The 18 counter attributes: BG palette 7 (BGPAL_BAR_B, the keg's yellow / steel / dark: the conveyor's colours) while the belt
// runs, the venue's own after. CGB only. The VBlank queue (bank 1) with the LCD on, VRAM with it off. The source must be in WRAM
// (the queue is drained in VBlank, when another ROM bank is mapped): the belt's 7s are BELT_ATTR, 18 bytes of story_scratch
// (free in a fight, no WRAM of their own), so they can wait in the queue beside proto.row's tiles: the belt's first tiles and
// its palette go out in the same VBlank (to_red), never one frame apart.
#define BELT_ATTR  (story_scratch + SCR_BELT_AT)
#if CONV_COLS > SCR_BELT_N
#error "the belt's attributes: SCR_BELT_N (src/scratch.h)"
#endif
static void counter_attr(uint8_t belt) {
    const uint8_t *src = venue.bar_attr + BAR_COUNTER_DROW * 20;
    uint8_t k;
    if (!is_cgb) return;
    if (belt) {
        uint8_t *d = BELT_ATTR;
        for (k = 0; k != CONV_COLS; k++) *d++ = BGPAL_BAR_B;
        src = BELT_ATTR;
    }
    if (LCDC_REG & LCDCF_ON) vq_add(1, src, 0, counter_y(), CONV_COLS);
    else {
        VBK_REG = VBK_BANK_1;
        vram_put(0, counter_y(), src, CONV_COLS);
        VBK_REG = VBK_BANK_0;
    }
}

// The counter row of his bar: the conveyor's tiles at frame f (f 0 or 1: the venue's counter tiles replaced), or (f 2)
// the venue's own row. The VBlank queue with the LCD on, VRAM with it off.
static void counter_put(uint8_t f) {
    const uint8_t *src = venue.bar_map + BAR_COUNTER_DROW * 20;
    if (f < 2) {                         // (running pointers and hoisted ids: the old indexed loop with an inner loop took about twice the ticks)
        uint8_t *d = proto.row, k, v, c0 = boss_conv_src[0], c1 = boss_conv_src[BOSS_ART_CONV_SRC - 1], n = BOSS_ICE_BG + f;
        for (k = 0; k != CONV_COLS; k++) {
            v = *src++;
            *d++ = (v == c0 || v == c1) ? n : v;
        }
        src = proto.row;
    }
    if (LCDC_REG & LCDCF_ON) vq_add(0, src, 0, counter_y(), CONV_COLS); else vram_put(0, counter_y(), src, CONV_COLS);
    if (f == 2) counter_attr(0);         // (the belt's end: the venue's own palette back)
}

static uint8_t on_belt(void) {           // the conveyor is drawn on his bar
    return proto.t >= T_RED && proto.t < T_RIDE;
}

static void to_green(void) {
    proto.t = 0;
    boss_special_t = 0;
    boss_xpose = 0;
    BOSS_TOPPER_T = 0; BOSS_TOPPER_PAL = 0;
    boss_cap = boss_hands;
    boss_state = BS_WALK;
}

// A battery that reaches him in RED, or that RED found on his bar, turns round: MUG_RETURN from where it is, and no
// regular's empty is due at the tap before it has arrived and a gap has passed.
static void turn_round(uint8_t i) {
    uint16_t t = (uint8_t)(bar_tap[boss_bar] - mug_x[i]);
    mug_state[i] = MUG_RETURN;
    mug_events++;
    t += empty_gap;
    if (t > next_arrival) next_arrival = t;
}

static void to_red(void) {
    uint8_t i;
    boss_xpose = BP_RED;
    BOSS_TOPPER_T = HAT_X; BOSS_TOPPER_PAL = OBJPAL_ENH;
    boss_cap = 255;                      // he "catches" every battery that reaches him (BEV_CATCH bounces it)
    for (i = 0; i != MAX_MUGS; i++)
        if (mug_state[i] == MUG_FULL && mug_bar[i] == boss_bar) turn_round(i);
    boss_state = BS_SPECIAL;
    counter_put(0);                      // the belt's first tiles and its palette: the same VBlank (tiles queued first)
    counter_attr(1);
}

static void stand(void) {                // YELLOW, RED: he stands (a gulp is over)
    if (boss_state == BS_WALK) boss_state = boss_xpose == BP_RED ? BS_SPECIAL : BS_TELL;
}

// ---- the entrance ----
static uint8_t pair_id(uint8_t p) {
    return p < BOSS_PAIRS_A ? BOSS_BG_A + (p << 1) : BOSS_BG_B + ((uint8_t)(p - BOSS_PAIRS_A) << 1);
}

// The entrance's sprite frame f (the art file's blocks: CHAIN, HOOK, SPARK1, SPARK2) at screen (x, y) into OAM from o (up to
// `end`); a cell off the screen is left out (the hardware counts every entry on a line, seen or not).
static OAM_item_t *ent_put(OAM_item_t *o, OAM_item_t *end, uint8_t f, int16_t x, int16_t y, uint8_t prop) {
    const uint8_t *c = boss_spr_cells + (uint16_t)boss_spr_first[f] * 3;
    uint8_t n = boss_spr_first[f + 1] - boss_spr_first[f];
    int16_t cx, cy;
    for (; n && o != end; n--, c += 3) {
        cx = x + c[0] + 8; cy = y + c[1];
        if ((uint16_t)(cx - 1) >= 167 || cy < -15 || cy > 143) continue;
        o->y = (uint8_t)(cy + 16); o->x = (uint8_t)cx; o->tile = BOSS_SPR_TILE0 + (c[2] << 1); o->prop = prop;
        o++;
    }
    return o;
}

// BEV_DRAW: the entrance's sprites for the frame the logic just reached (boss_draw, after every other sprite): the crane lowers
// him 2.5 px a frame by his lamp (the yoke, a chain up off the screen), lets go and rises; the lamp lights red -> yellow -> green
// and the sparks fly from his shoulders.
static void ent_draw(void) {
    OAM_item_t *o = shadow_OAM + ENT_OAM, *top = o + ENT_OAM_N, *end = shadow_OAM + OAM_MUG_END - 2 * lift_total;
    uint8_t t = (uint8_t)(proto.t - ENT_T0) - 2, k, lamp, up = 0, sp;
    uint8_t body = is_cgb ? OBJPAL_COIN : S_PALETTE, steel = is_cgb ? OBJPAL_PATRON_C : S_PALETTE;
    int16_t by, hy, cy, ly = bar_oam_y[boss_bar] - 16;
    if (proto.t < ENT_T0 + 2) return;
    if (end > top) end = top;
    by = t < ENT_DOWN0 ? ly - 120 : t >= ENT_CLUNK ? ly : ly - 120 + ((((uint8_t)(t - ENT_DOWN0)) * 5) >> 1);
    sp = t >= ENT_YELLOW && t <= ENT_SPARKS_END;
    if (sp && (t & 2)) by++;                                   // (the power-up's shake)
    for (k = 0; k != BOSS_ART_COLS && o != end; k++) {         // his body: the BG's own tiles as sprites
        o->y = (uint8_t)(by + 16); o->x = 8 + 16 + (k << 3); o->tile = pair_id(boss_art_pose[BP_WALK][k]); o->prop = body;
        o++;
    }
    lamp = t < ENT_YELLOW ? HAT_X : t < ENT_GREEN ? HAT_RING : 0;       // his lamp: the topper's tiles over his head
    if (o != end) {
        o->y = (uint8_t)(by + 8); o->x = 8 + 16 + 8; o->tile = OBJ_TOPPER + lamp;
        o->prop = !is_cgb ? S_PALETTE : t < ENT_YELLOW ? OBJPAL_ENH : t < ENT_GREEN ? OBJPAL_COIN : OBJPAL_PATRON_C;
        o++;
    }
    if (t >= ENT_UP0) up = t >= ENT_UP0 + 24 ? 255 : (uint8_t)(t - ENT_UP0) << 2;
    if (up != 255) {                                           // the crane: the yoke around the lamp, the chain above it
        hy = by - 14 - up;
        o = ent_put(o, end, SPR_HOOK, 16 + 4, hy, steel);
        for (cy = hy - 16; cy > -16; cy -= 16) o = ent_put(o, end, SPR_CHAIN, 16 + 8, cy, steel);
    }
    if (sp) {                                                  // the sparks, one frame each at his shoulders, swapping every 2 frames
        o = ent_put(o, end, (t & 2) ? SPR_SPARK1 : SPR_SPARK2, 16 - 7, by - 2, body);
        o = ent_put(o, end, (t & 2) ? SPR_SPARK2 : SPR_SPARK1, 16 + 32 - 1, by + 2, body);
    }
    for (; o != top; o++) o->y = 0;
}

// BEV_INTRO, every frame while intro_timer runs: the entrance's clock and what happens at its frames. The player's input is
// undone (the bartender stays at bar 0's tap, nothing is poured) until he stands on his bar.
static void ent_frame(void) {
    uint8_t t = (uint8_t)(proto.t - ENT_T0) - 1, i;
    fill_timer = 0; fill_stage = 0;                          // (the bartender stays where he is: main.c skips his input while he is held)
    bartender_frame = BT_IDLE; catch_pose = 0; bt_bob = 0;
    if (t < ENT_LAND) intro_timer = INTRO_FRAMES;            // (held: the intro's 90 frames start at the last frame)
    if (t == ENT_CLUNK) SFX(SFX_SHAKE);
    if (t == ENT_YELLOW) SFX(SFX_COIN);
    if (t == ENT_GREEN) SFX(SFX_EXTRA);
    if (t == ENT_LAND) {
        intro_timer = INTRO_FRAMES - 1;                      // (as the level's first frame leaves it: the fight starts 89 frames on)
        boss_state = BS_WALK;                                // (E9: over: boss.c starts the fight)
        to_green();                                          // (proto.t 0: the cycle's first frame is the fight's)
        boss_to_bar(boss_bar, PROTO_X);                      // his BG body (WALK) at x 16, under where the sprites were
        for (i = 0; i != ENT_OAM_N; i++) shadow_OAM[ENT_OAM + i].y = 0;
        return;
    }
    proto.t++;
}

uint8_t boss_prototype(uint8_t ev, uint8_t arg) BANKED {
    uint8_t b;
    switch (ev) {
    case BEV_SET:
        boss_art_set();
        boss_returns = 1;                // (boss.c boss_mugs moves every MUG_RETURN)
        to_green();
        break;
    case BEV_RESET:
        if (on_belt()) counter_put(2);
        if (boss_bar != PROTO_BAR) boss_to_bar(PROTO_BAR, PROTO_X);
        boss_mark(BOSS_NONE, 0);
        if (proto.t >= ENT_T0) { boss_state = BS_JUMP; boss_xpose = BP_HIDE; }   // (the entrance: not on his bar yet)
        else to_green();
        break;
    case BEV_LOAD:
        boss_art_load();
        BOSS_BG(BOSS_ICE_BG, BOSS_ART_CONV, boss_conv_tiles);
        BOSS_OBJ(BOSS_SPR_TILE0, BOSS_ART_SPR_PAIRS * 2, boss_spr_tiles);   // the entrance's crane and sparks (OBJ 108-117)
        if (is_cgb) {                    // the lamp's colour 2 per phase: palettes are written with the LCD off only
            palette_t p;                 // (the logic runs in the picture, not in VBlank), so one OBJ palette each
            p[0] = 0; p[1] = boss_art_pal[1]; p[3] = boss_art_pal[3];
            p[2] = RGB(5, 27, 5); boss_ldpal(1, OBJPAL_PATRON_C, p);   // green: OBJ 7 (the engine's topper)
            p[2] = RGB(31, 25, 0); boss_ldpal(1, OBJPAL_COIN, p);      // yellow: OBJ 5 (no coin / show in a fight)
            p[2] = RGB(31, 3, 3); boss_ldpal(1, OBJPAL_ENH, p);        // red: OBJ 4 (an enhanced patron's; a fight
        }                                                                       // only has variants A / B)
        break;
    case BEV_ENTER:                                          // (E9: after the warm-up)
        proto.t = ENT_T0 + 1;
        return 1;
    case BEV_INTRO:
        if (proto.t >= ENT_T0) ent_frame();
        break;
    case BEV_DRAW:
        if (proto.t >= ENT_T0) ent_draw();
        break;
    case BEV_TELL:
        if (proto.t < T_YELLOW) proto.t = T_YELLOW - 1;   // (the next frame starts the yellow)
        break;
    case BEV_CATCH:
        if (!on_belt()) return 0;
        turn_round(arg);                 // RED: the battery bounces
        return 1;
    case BEV_OUTRO:
        if (on_belt()) counter_put(2);
        boss_mark(BOSS_NONE, 0);
        proto.t = 0;
        BOSS_TOPPER_T = 0; BOSS_TOPPER_PAL = 0;
        boss_xpose = 0;
        break;
    case BEV_FRAME:
        proto.t++;
        if (proto.t == T_YELLOW) { BOSS_TOPPER_T = HAT_RING; BOSS_TOPPER_PAL = OBJPAL_COIN; }
        else if (proto.t == T_RED) to_red();
        else if (proto.t == T_MARK) {
            do b = next_rand() & 3; while (b == boss_bar);
            boss_mark(b, boss_col);
            boss_pattern(b);
        } else if (proto.t == T_RIDE) {
            counter_put(2);
            boss_xpose = BP_HIDE;
            BOSS_TOPPER_T = 0; BOSS_TOPPER_PAL = 0;
            boss_cap = boss_hands;
            boss_state = BS_JUMP;
        } else if (proto.t == T_LAND) {
            b = BOSS_MARK_BAR;
            boss_mark(BOSS_NONE, 0);
            to_green();
            boss_to_bar(b, boss_x);
            SFX(SFX_SHAKE);
            break;
        }
        if (proto.t >= T_YELLOW && proto.t < T_RIDE) stand();
        if (on_belt()) {                 // every CONV_EVERY frames after T_RED's own (to_red). No division (SDCC's cost ~30 DIV ticks a RED frame):
            b = (uint8_t)(proto.t - T_RED);                    // d = 3m exactly when (uint8_t)(d * 171) = m <= 85 (171 = 3^-1 mod 256), and
            if (b && !(b & 1)) {                               // 6 | d when d is even too; the step number d / 6 is m / 2 (CONV_EVERY 6)
                b *= 171;
                if (b <= 85) counter_put((b >> 1) & 1);
            }
        }
        break;
    }
    return 0;
}
