// The Prototype, the robot factory's boss (docs/minigames_bosses.md 3.8; art approved 2026-10-11, look B "the hauler").
// His row is boss.c rows[5]: 32 px, start x 16, bar 2, step 100, push 8, gulp 20, hands 2, sip 45, meter 12.
//
// One cycle (own.t counts its frames; he walks and drinks like any boss in GREEN, stands through the rest):
//   GREEN  0-239    the lamp on his antenna is solid, he takes batteries as ever.
//   YELLOW 240-299  the tell: the lamp is a ring (HAT frame LAMP_RING), he stands but still takes a battery.
//   RED    300-449  the lamp is an X, the RED pose (screen X, arm up), his bar's conveyor runs right (the approved K5 stripes + K6 arrows: tiles
//                   BOSS_ICE_BG, 2 frames, the counter's attributes the keg's palette 7, the counter row rewritten every 6 frames through the VBlank queue):
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
#pragma bank 255
#include "boss.h"
#include "boss_prototype_art.h"
#include "boss_load.h"
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
#define CONV_COLS      18                // the counter's columns 0-17 (18-19: the keg)
#define CONV_EVERY      6                // frames per arrow step
#if BOSS_ART_CONV != 2 || BOSS_ART_CONV_SRC > 2
#error "the Prototype's conveyor: 2 frames, at most 2 counter tile ids"
#endif

typedef struct {
    uint16_t t;                          // frames in the cycle (tests)
    uint8_t  row[CONV_COLS];             // the conveyor's counter row, as last written
} prototype_t;
#define proto (*(prototype_t *)BOSS_OWN)
#if 2 + CONV_COLS > BOSS_OWN_N
#error "the Prototype's state: BOSS_OWN_N"
#endif

static uint8_t counter_y(void) {
    return BAR_COUNTER_ROW(boss_bar);
}

// The 18 counter attributes: BG palette 7 (BGPAL_BAR_B, the keg's yellow / steel / dark: the conveyor's colours) while the belt
// runs, the venue's own after. CGB only. The VBlank queue (bank 1) with the LCD on, VRAM with it off. The source must be in WRAM
// (the queue is drained in VBlank, when another ROM bank is mapped): the belt's 7s are proto.row, filled here, so the next
// write into proto.row (counter_put) is at least a frame later (the first belt frame is one frame after the RED start).
static void counter_attr(uint8_t belt) {
    const uint8_t *src = venue.bar_attr + BAR_COUNTER_DROW * 20;
    uint8_t k;
    if (!is_cgb) return;
    if (belt) {
        for (k = 0; k != CONV_COLS; k++) proto.row[k] = BGPAL_BAR_B;
        src = proto.row;
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
    uint8_t k, j;
    if (f < 2) {
        for (k = 0; k != CONV_COLS; k++) {
            proto.row[k] = src[k];
            for (j = 0; j != BOSS_ART_CONV_SRC; j++) if (boss_conv_src[j] == src[k]) proto.row[k] = BOSS_ICE_BG + f;
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
    counter_attr(1);                     // (the belt's tiles follow in this frame's BEV_FRAME: counter_put)
}

static void stand(void) {                // YELLOW, RED: he stands (a gulp is over)
    if (boss_state == BS_WALK) boss_state = boss_xpose == BP_RED ? BS_SPECIAL : BS_TELL;
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
        to_green();
        break;
    case BEV_LOAD:
        boss_art_load();
        set_bkg_data(BOSS_ICE_BG, BOSS_ART_CONV, boss_conv_tiles);
        if (is_cgb) {                    // the lamp's colour 2 per phase: palettes are written with the LCD off only
            palette_t p;                 // (the logic runs in the picture, not in VBlank), so one OBJ palette each
            p[0] = 0; p[1] = boss_art_pal[1]; p[3] = boss_art_pal[3];
            p[2] = RGB(5, 27, 5); set_sprite_palette(OBJPAL_PATRON_C, 1, p);   // green: OBJ 7 (the engine's topper)
            p[2] = RGB(31, 25, 0); set_sprite_palette(OBJPAL_COIN, 1, p);      // yellow: OBJ 5 (no coin / show in a fight)
            p[2] = RGB(31, 3, 3); set_sprite_palette(OBJPAL_ENH, 1, p);        // red: OBJ 4 (an enhanced patron's; a fight
        }                                                                       // only has variants A / B)
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
        if (on_belt() && (uint8_t)(proto.t - T_RED - 1) % CONV_EVERY == 0) counter_put(((uint8_t)(proto.t - T_RED - 1) / CONV_EVERY) & 1);   // (from T_RED + 1: the attributes' frame is T_RED)
        break;
    }
    return 0;
}
