// Bonus round: a shell game. Six cans stand on one long counter; five get shaken one at a
// time in random order, the sixth is left calm. The cans then swap places in pairs, hopping
// over each other, and the player picks the calm one. Right: it opens, +3000. Wrong: the
// picked can bursts: a soda geyser shoots straight up from it, peaks and holds, then droplets
// rain down and spread over the whole screen (counter, floor and a few on the bartender).
// M12: the rounds rotate (bonus_kind): 1st shake-up, 2nd Perfect Pour, 3rd Tip Shower, then again; the other two are
// in src/bonus2.c and this file only hands over to it. The shake-up's difficulty counts shake-ups, not rounds.
//
// Own screen (LCD off to enter). Sprite budget: bartender-bound drops 0-2 (in front of him), cursor 3,
// bartender 4-7, cans 8-13, counter/floor drops 14-22, geyser column 30-33. In the lose result draw() counts
// sprites per scanline and hides a drop rather than let any line pass 10.
#pragma bank 255
#include <gb/gb.h>
#include <gb/cgb.h>
#include <stdint.h>

#include "art.h"
#include "bonus.h"
#include "music.h"
#include "can_tiles.h"      // static const uint8_t bonus_tiles[]: this bank's own art data

// ---- shared with main.c (bank 0) ----
extern uint8_t game_state;                  // GS_MINI inside the framework (Practice)
#define GS_MINI 13                          // (game.h enum: tests/test_mg.py pins it too)
extern uint8_t is_cgb, level, overlay_on, hud_dirty, life_lost, vram_pending;
extern uint8_t play_mode;                   // src/story.c (game.h MODE_*)
#define MODE_CLASSIC 2
extern void vq_reset(void);
extern uint32_t score;
extern uint8_t next_rand(void);
extern void add_score(uint16_t n) BANKED;
extern void draw_hud(void) BANKED;          // src/main_cold.c
extern void bonus_record(uint8_t k, uint8_t medal) BANKED;   // src/save.c: round k was played (unlocks it in Practice)
extern uint8_t *mg_say(uint8_t row, const char *s);   // main.c (ROM0)
extern void clear_dirty(void);
extern void vram_put(uint8_t x, uint8_t y, const uint8_t *src, uint8_t n);
extern void vq_add(uint8_t bank, const uint8_t *src, uint8_t x, uint8_t y, uint8_t n);
void venue_backdrop(uint8_t first, uint8_t counter_row) BANKED;   // venue.c

// ---- layout (screen px unless noted) ----
#define OBJ_BONUS        96     // first OBJ tile: the show performers' 32 tiles (96..127) are borrowed; the next level's
                                // load_venue() reloads them
#define OBJ_CURSOR       (OBJ_BONUS + CAN_TILE_COUNT)
#define OBJ_GEYSER       (OBJ_CURSOR + 2)                 // left halves A, B, cap; right halves are +6
#define OBJ_DROP         (OBJ_GEYSER + GEYSER_FRAMES * 2) // tall, round, splat
#define OBJ_CAT          (OBJ_DROP + DROP_FRAMES * 2)     // 4 walk frames (leg step A / B, tail down / up): left half, right half (8x16 each)
#define GEY_BASE         (CAN_TOP + 6)      // screen y of the burst can's mouth
#define GEY_MAX          56                 // geyser peak height, px
#define GEY_OAM          30                 // 8 entries: 4 rows of left/right halves
#define NUM_DROPS        12
#define DROP_SY          (GEY_BASE - GEY_MAX)   // y of the head of the full column: where drops leave
#define DROP_T0          20                 // first drop leaves the geyser head this many frames after the burst
#define DROP_GAP          3
#define SPLAT_LEN        20
#define OBJPAL_CAN       6
#define OBJPAL_FOAM      7      // foam and cursor
#define CAN_X0           16
#define CAN_DX           24
#define CAN_TOP          72     // can art top; base sits on the counter row (y 88)
#define COUNTER_ROW      11
#define TEXT_ROW          4
#define CURSOR_Y         (CAN_TOP - 18)     // arrow tip 2 px above the can
#define BT_X             72
#define BT_TOP           112                // bartender 16x24, feet on the floor row (y 136)
#define BT_IDLE_F         0
#define BT_WALK1          1
#define CAT_TOP          73                 // level 3's bar cat 16x16 (feet row 14): its feet on the counter top (y 88) like the cans'
#define CAT_END         176                 // the walk's clock / 4 when its tail has left the screen
#define OBJPAL_CAT        5
#define BT_CATCH_F        3                 // Sal's PICTURE index (bartender.txt: catch shows the fill picture)
#define BT_FAIL_F         4                 // the fail picture
#define NUM_CANS          6
#define HOP_H            16

#define SHOW_LEN         60
#define SHAKE_LEN        30
#define SHAKE_GAP        12
#define RESULT_LEN       130
#define BONUS_SCORE    3000
enum { PH_SHOW, PH_SHAKE, PH_SWAP, PH_CHOOSE, PH_RESULT };
enum { CF_STILL, CF_LEFT, CF_RIGHT, CF_BURST, CF_OPEN };

uint8_t  bonus_round;
uint8_t  bonus_kind;           // 0 this file's shake-up, 1 / 2 the rounds in bonus2.c
uint8_t  bonus_phase;          // PH_*
uint8_t  bonus_calm;           // slot (0..5, left to right) where the calm can stands now (updated when a swap lands)
uint8_t  bonus_calm_can;       // the calm can's identity (index into can_pos[])
uint8_t  bonus_cursor;         // slot under the arrow
uint8_t  bonus_won;
uint8_t  bonus_picked;         // can identity the player chose
uint8_t  can_pos[NUM_CANS];    // screen x of each can (by identity)
uint8_t  can_frame[NUM_CANS];  // CF_*
uint8_t  can_shake[NUM_CANS];  // 1 while that can is being shaken
uint8_t  can_shaken[NUM_CANS]; // 1 once it has been shaken (the calm one never is)
uint8_t  bonus_moving;         // 1 while a swap is in flight
uint8_t  bonus_swaps_done, bonus_swaps_total;
uint8_t  bonus_swap_dur;       // frames per swap this round
uint8_t  slot_can[NUM_CANS];   // which can stands in each slot (logical, updated when a swap lands)

// the rain, by launch order: where each drop lands (screen x, y of its centre), how long it flies, and its launch
// speed up (-) in 1/256 px per frame; gravity is DROP_G. Landing at tt = T is exact: y = sy + vy0*T + G*T*(T-1)/2.
// Bartender drops (y 122..133 on x 78..84) are the three that use OAM 0-2; the rest hit the counter (y 90) or the floor (y 140).
#define DROP_G 48
static const uint8_t drop_tx[NUM_DROPS]   = { 14, 110,  78,  40, 146, 124,  82,  22, 100,  58,  80, 140 };
static const uint8_t drop_ty[NUM_DROPS]   = { 90, 140, 122, 140,  90, 140, 128, 140,  90, 140, 133, 140 };
static const uint8_t drop_T[NUM_DROPS]    = { 38,  43,  43,  48,  36,  47,  43,  48,  39,  44,  45,  45 };
static const int16_t drop_vy0[NUM_DROPS]  = {-430,-305,-413,-499,-356,-461,-377,-499,-466,-345,-425,-385 };
static const uint8_t drop_oam[NUM_DROPS]  = { 14,  15,   0,  16,  17,  18,   1,  19,  20,  21,   2,  22 };
static uint16_t drop_x[NUM_DROPS];                                   // 8.8 fixed point, screen x of the centre (wraps fine for signed vx)
static int16_t  drop_y[NUM_DROPS], drop_vx[NUM_DROPS], drop_vy[NUM_DROPS];   // y relative to the geyser head, 8.8; vx 8.8

static uint8_t can_dy[NUM_CANS];      // hop height now
static uint8_t order[5], oi;          // shake order
uint8_t  bonus_timer;               // frames in the current step
static uint8_t swap_a, swap_b, swap_t;
static uint8_t rowbuf[20];

#define say(s) mg_say(TEXT_ROW, s)    // (main.c, ROM0: the string stays in this bank) queued, or written with the LCD off

static uint8_t slot_x(uint8_t slot) { return CAN_X0 + CAN_DX * slot; }

static void load_palettes(void) {
    uint16_t p[4];
    p[0] = 0;
    p[1] = 30 | (30 << 5) | (28 << 10);      // silver
    p[2] = 25 | (6 << 5) | (6 << 10);        // red body
    p[3] = 4 | (2 << 5) | (4 << 10);
    set_sprite_palette(OBJPAL_CAN, 1, p);
    p[1] = 31 | (30 << 5) | (26 << 10);      // cream foam
    p[2] = 31 | (24 << 5) | (4 << 10);       // gold (cursor)
    p[3] = 8 | (4 << 5) | (2 << 10);
    set_sprite_palette(OBJPAL_FOAM, 1, p);
    p[1] = 30 | (19 << 5) | (9 << 10);       // the bar cat: ginger coat, stripes (the saloon stage's #f09848, #702840, #181030)
    p[2] = 14 | (5 << 5) | (8 << 10);
    p[3] = 3 | (2 << 5) | (6 << 10);
    set_sprite_palette(OBJPAL_CAT, 1, p);
}

// whole screen, LCD off. The round is played in the venue of the level just cleared (its BG tiles and palettes
// are still loaded): its plain wall, one counter row, its floor.
static void draw_scene(uint8_t prac) {
    uint8_t i;
    if (!prac) { draw_hud(); venue_backdrop(1, COUNTER_ROW); }
    say("BONUS ROUND");
    if (is_cgb) {
        VBK_REG = VBK_BANK_1;
        for (i = 0; i < 20; i++) rowbuf[i] = 1;      // BG palette 1 = HUD
        vram_put(0, TEXT_ROW, rowbuf, 20);
        VBK_REG = VBK_BANK_0;
    }
}

static void shuffle_order(void) {
    uint8_t i, j, n = 0, t;
    for (i = 0; i < NUM_CANS; i++) if (i != bonus_calm_can) order[n++] = i;
    for (i = 4; i > 0; i--) {
        j = next_rand() % (i + 1);
        t = order[i]; order[i] = order[j]; order[j] = t;
    }
}

// One round's state: the pace, the cans, the shake order. Practice (the mini-game framework) plays three levels of it, bonus_round counting
// them (1..3): each swaps faster (30, 22, 14 frames) and more often (7, 9, 11 swaps). ARCADE / CLASSIC play one round as ever.
// Practice's three levels per difficulty (indexed by BONUS_DIFF: NORMAL, HARD, EASY): the swaps a level adds to 6 (the first 7, 9, 11 on NORMAL) and the
// frames a swap takes (30, 22, 14 on NORMAL).
static const uint8_t shake_n[3][3]   = { { 1, 3, 5 }, { 3, 5, 7 },    { 1, 2, 3 } };
static const uint8_t shake_dur[3][3] = { { 30, 22, 14 }, { 26, 18, 10 }, { 38, 30, 22 } };

static void setup_round(uint8_t prac, uint8_t classic) {
    uint8_t i, n;
    bonus_won = 0; bonus_moving = 0; bonus_swaps_done = 0;
    if (prac) {                                                 // (the difficulty's table, TUNING.md: bonus_round 1..3; game_state is not GS_MINI yet: mg_mode is the round's)
        i = (mg_mode >> 1) & 3;
        n = shake_n[i][bonus_round - 1];
        bonus_swap_dur = shake_dur[i][bonus_round - 1];
    } else if (classic) {                                       // P5: faster every round: 30, 28, ... 14 frames a swap,
        n = bonus_round < 9 ? bonus_round : 9;                  // a swap more each time (7 .. 15)
        bonus_swap_dur = 32 - 2 * n;
    } else {
        n = (uint8_t)((uint8_t)(bonus_round + 2) / 3);         // shake-ups so far, this one included (1 in round 1, 2 in round 4, ...)
        bonus_swap_dur = n < 3 ? 30 : (n < 6 ? 34 - 4 * n : 14);   // shake-ups 1-2 slow, then 22, 18, 14
    }
    bonus_swaps_total = 6 + n;
    bonus_calm_can = next_rand() % NUM_CANS;
    bonus_calm = bonus_calm_can;
    bonus_cursor = 2;
    for (i = 0; i < NUM_CANS; i++) {
        slot_can[i] = i; can_pos[i] = slot_x(i); can_frame[i] = CF_STILL; can_shake[i] = 0;
        can_shaken[i] = 0; can_dy[i] = 0;
    }
    shuffle_order();
    oi = 0; swap_t = 0; drop_x[0] = 0;
}

#define NO_KIND 255            // enter(): the round the rotation gives (ARCADE, CLASSIC)

// The round's scene, LCD off. In ARCADE / CLASSIC (kind NO_KIND) the rotation picks it, it is recorded as played (BONUS > MINI GAMES lists it
// from then on: save.c) and the HUD, the backdrop and DISPLAY_ON are this file's. In Practice (kind 0..2: mg.c has drawn the HUD and the
// backdrop and turns the LCD on itself) the round is the same, its banner's 90 frames left to the framework's card.
static void enter(uint8_t kind) {
    uint8_t i, prac = kind != NO_KIND, classic = !prac && play_mode == MODE_CLASSIC;
    DISPLAY_OFF;
    overlay_on = 0; HIDE_WIN; vq_reset(); hud_dirty = 0; life_lost = 0; vram_pending = 0;
    clear_dirty();
    for (i = 0; i < 40; i++) shadow_OAM[i].y = 0;
    if (prac) bonus_round = kind;                               // (the first shake-up's pace; ++ below gives the round that makes `kind`)
    bonus_round++;
    bonus_kind = prac ? kind : classic ? 0 : (uint8_t)((uint8_t)(bonus_round - 1) % 3);   // M12: shake-up, Perfect
                                                                // Pour, Tip Shower, again (CLASSIC: the shake-up only)
    if (!prac) bonus_record(bonus_kind, 0);                     // played in ARCADE or CLASSIC: unlocked for Practice
    music_play(TUNE_BONUS);
    bonus_phase = PH_SHOW; bonus_timer = prac && bonus_kind ? BONUS_BANNER_LEN : 0;   // (Practice: the card was the banner)
    if (bonus_kind) {                                           // the other two rounds: src/bonus2.c
        if (!prac) draw_hud();
        venue_backdrop(1, bonus_kind == 1 ? COUNTER_ROW : 18);   // Tip Shower: no counter, the coins fall from the ceiling
        bonus2_enter();
        if (!prac) DISPLAY_ON;
        return;
    }
    set_sprite_data(OBJ_BONUS, BONUS_TILE_COUNT, bonus_tiles);
    if (is_cgb) load_palettes();
    draw_scene(prac);

    setup_round(prac, classic);
    if (!prac) DISPLAY_ON;
}

void bonus_enter(void) BANKED { enter(NO_KIND); }
void bonus_practice(uint8_t kind) BANKED { enter(kind); }

// ---- drawing ----
static void spr(uint8_t i, uint8_t x, uint8_t y, uint8_t tile, uint8_t prop) {
    OAM_item_t *o = &shadow_OAM[i];
    o->y = y; o->x = x; o->tile = tile; o->prop = prop;
}


static uint8_t geyser_h(uint8_t t) {      // column height: eases up, holds with a wobble, then collapses
    if (t < 18) return GEY_MAX - (uint8_t)((GEY_MAX * (uint16_t)(17 - t + 1) * (17 - t + 1)) / 324u);
    if (t < 50) return GEY_MAX - ((t >> 2) & 1) * 3;
    if (t < 64) return (uint8_t)((GEY_MAX * (uint16_t)(64 - t)) / 14u);
    return 0;
}

static void draw_geyser(void) {
    uint8_t t = bonus_timer, h = geyser_h(t), n, j, i, f, T, a, e, o, cA, cB, cC, maxA, inA, inB, inC;
    int16_t top, y, sx;
    top = GEY_BASE - h;
    if (h < 16) { top = GEY_BASE - 16; }                // never poke below the can mouth
    n = h ? (h + 15) >> 4 : 0;
    // The head (cap) sits at the top of the column; below it n-1 body pairs stack up from the can mouth. Only the head
    // overlaps the pair under it, so at most two pairs (4 sprites) share a line.
    for (j = 0; j < 4; j++) {
        if (j < n) {
            y = j == 0 ? top : GEY_BASE - 16 - 16 * (j - 1);
            f = j == 0 ? 2 : (((t >> 1) + j) & 1);
            spr(GEY_OAM + 2 * j,     can_pos[bonus_picked] + 4,  (uint8_t)(y + 16), OBJ_GEYSER + 2 * f,     OBJPAL_FOAM);
            spr(GEY_OAM + 2 * j + 1, can_pos[bonus_picked] + 12, (uint8_t)(y + 16), OBJ_GEYSER + 6 + 2 * f, OBJPAL_FOAM);
        } else { shadow_OAM[GEY_OAM + 2 * j].y = 0; shadow_OAM[GEY_OAM + 2 * j + 1].y = 0; }
    }
    // Scanline budget (10 per line), by zones. Zone A, the can band y 72..87: 6 cans + the geyser's bottom pair (2) leave room
    // for 2 drops. Zone B, the bartender's rows y 112..143: his 2 leave 8. Zone C, everything else (the geyser alone puts at most
    // 4 on a line there, because its pairs overlap pairwise at most): 6 drops. A drop is counted in every zone its 16 lines touch,
    // and refused (hidden this frame) when a zone is full, so no line can pass 10 whatever the arcs do.
    sx = can_pos[bonus_picked] + 4;                     // can centre
    cA = cB = cC = 0;
    maxA = n == 2 ? 0 : 2;                              // head over the bottom pair: 4 geyser sprites in the can band
    for (i = 0; i < NUM_DROPS; i++) {
        o = drop_oam[i];
        T = drop_T[i];
        a = t - (DROP_T0 + DROP_GAP * i);               // frames since this drop left the head (wraps when not yet launched)
        if (t < DROP_T0 + DROP_GAP * i || a >= T + SPLAT_LEN) { shadow_OAM[o].y = 0; continue; }
        if (!a) {                                       // leaves the head of the geyser
            drop_x[i] = (uint16_t)sx << 8; drop_y[i] = 0; drop_vy[i] = drop_vy0[i];
            drop_vx[i] = (((int16_t)drop_tx[i] - sx) * 32 / T) * 8;   // 1/256 precision without overflowing int16
        } else if (a < T) {                             // gravity, with the sideways drift
            drop_x[i] += drop_vx[i]; drop_y[i] += drop_vy[i]; drop_vy[i] += DROP_G;
        } else { drop_x[i] = (uint16_t)drop_tx[i] << 8; drop_y[i] = (int16_t)((drop_ty[i] - DROP_SY) << 8); }
        e = DROP_SY + 8 + ((int8_t *)&drop_y[i])[1];    // OAM y of an entry whose centre is the drop's
        // Scanline budget (10 per line), by zones. Zone A, the can band y 72..87: 6 cans + the geyser's bottom pair (2) leave room
        // for 2 drops. Zone B, the bartender's rows y 112..143: his 2 leave 8. Zone C, everything above y 128 but the can band
        // (the geyser alone puts at most 4 on a line there, its pairs overlapping pairwise at most): 6 drops. A drop is counted in
        // every zone its 16 lines touch and hidden this frame when a zone is full, so no line can pass 10 whatever the arcs do.
        inA = e > CAN_TOP && e < CAN_TOP + 32;
        inB = e > BT_TOP;
        inC = e < BT_TOP + 16;
        if ((inA && cA >= maxA) || (inB && cB >= 8) || (inC && cC >= 6)) { shadow_OAM[o].y = 0; continue; }
        cA += inA; cB += inB; cC += inC;
        spr(o, ((uint8_t *)&drop_x[i])[1] + 4, e, a >= T ? OBJ_DROP + 4 : OBJ_DROP + ((a >> 2) & 1) * 2, OBJPAL_FOAM);
    }
}

static void draw(void) {
    uint8_t i, f, base, k, bf = BT_IDLE_F, x;
    for (i = 0; i < NUM_CANS; i++) {
        x = can_pos[i];
        f = can_frame[i];
        if (can_shake[i]) x += (f == CF_LEFT) ? 0xFF : 1;          // +-1 px wiggle
        spr(8 + i, x + 8, CAN_TOP + 16 - can_dy[i], OBJ_BONUS + 2 * f, OBJPAL_CAN);
    }
    // cursor: only while choosing / after the pick
    if (bonus_phase >= PH_CHOOSE && !(bonus_phase == PH_RESULT && !bonus_won)) spr(3, slot_x(bonus_cursor) + 8, CURSOR_Y + 16 + ((bonus_timer >> 3) & 1), OBJ_CURSOR, OBJPAL_FOAM);
    else shadow_OAM[3].y = 0;
    // wrong pick: soda geyser, then the rain
    if (bonus_phase == PH_RESULT && !bonus_won) {
        bf = BT_FAIL_F;
        draw_geyser();
    } else {
        for (k = 0; k < NUM_DROPS; k++) shadow_OAM[drop_oam[k]].y = 0;
        for (k = 0; k < 8; k++) shadow_OAM[GEY_OAM + k].y = 0;
    }
    if ((bonus_phase == PH_SWAP || bonus_phase == PH_CHOOSE) && game_state == GS_MINI && bonus_round == 3 && drop_x[0] < CAT_END * 4) {
        drop_x[0] += 4;                                         // level 3's distraction: the bar cat walks along the counter top behind the cans
        x = (uint8_t)(drop_x[0] >> 2);                          // (OAM 30-31, behind the cans' 8-13), 1 px a frame from the swaps' start, head
        f = ((x >> 3) & 1) | (((x + (x >> 1)) >> 3) & 1) << 1;  // (bit 0 the legs, bit 1 the tail wave on its own clock) first from off the left edge, off the right edge before the choice (drop_x[0] is
        base = OBJ_CAT + 4 * f;                                 // the walk's clock, x its head's OAM x; the cat is 16 wide, x - 8 its tail's)
        if (x >= 8) spr(GEY_OAM, x - 8, CAT_TOP + 16, base, OBJPAL_CAT); else shadow_OAM[GEY_OAM].y = 0;
        if (x < 168) spr(GEY_OAM + 1, x, CAT_TOP + 16, base + 2, OBJPAL_CAT); else shadow_OAM[GEY_OAM + 1].y = 0;
    }
    if (bonus_phase == PH_RESULT && bonus_won) bf = BT_CATCH_F;
    base = bf * BARTENDER_TILES_PER_FRAME;       // OBJ tiles 0.. hold the bartender frames
    spr(4, (uint8_t)(BT_X + 8),  (uint8_t)(BT_TOP + 16), base,     0);
    spr(5, (uint8_t)(BT_X + 16), (uint8_t)(BT_TOP + 16), base + 2, 0);
    spr(6, (uint8_t)(BT_X + 8),  (uint8_t)(BT_TOP + 32), base + 4, 0);
    spr(7, (uint8_t)(BT_X + 16), (uint8_t)(BT_TOP + 32), base + 6, 0);
}

// ---- logic ----
static void start_swap(void) {
    swap_a = next_rand() % NUM_CANS;
    swap_b = (swap_a + 1 + next_rand() % (NUM_CANS - 1)) % NUM_CANS;
    swap_t = 0;
    bonus_moving = 1;
}

static void step_swap(void) {
    uint8_t ca = slot_can[swap_a], cb = slot_can[swap_b], dur = bonus_swap_dur, ax, bx, h;
    int16_t span, q;
    swap_t++;
    ax = slot_x(swap_a); bx = slot_x(swap_b);
    span = (int16_t)bx - ax;
    q = span * swap_t / dur;           // (one multiply and divide for both cans)
    can_pos[ca] = (uint8_t)(ax + q);
    can_pos[cb] = (uint8_t)(bx - q);
    h = (uint8_t)(((uint16_t)swap_t * (dur - swap_t) * 64u) / ((uint16_t)dur * dur));
    can_dy[ca] = h;                    // ca hops over, cb slides underneath
    if (swap_t >= dur) {
        slot_can[swap_a] = cb; slot_can[swap_b] = ca;
        can_pos[ca] = bx; can_pos[cb] = ax; can_dy[ca] = 0;
        bonus_calm = slot_can[swap_a] == bonus_calm_can ? swap_a : slot_can[swap_b] == bonus_calm_can ? swap_b : bonus_calm;
        bonus_moving = 0;
        bonus_swaps_done++;
        swap_t = 0;
        bonus_timer = 0;
    }
}

uint8_t bonus_update(uint8_t pressed) BANKED {
    uint8_t c;
    if (bonus_kind) return bonus2_update();
    bonus_timer++;
    switch (bonus_phase) {
    case PH_SHOW:
        if (bonus_timer >= SHOW_LEN) { bonus_phase = PH_SHAKE; bonus_timer = 0; say("ONE STAYS CALM"); }
        break;
    case PH_SHAKE:
        c = order[oi];
        if (bonus_timer == 1) { can_shake[c] = 1; can_shaken[c] = 1; }
        if (bonus_timer % 6 == 1 && bonus_timer < SHAKE_LEN) SFX(SFX_SHAKE);
        if (can_shake[c]) {
            can_frame[c] = ((bonus_timer / 3) & 1) ? CF_RIGHT : CF_LEFT;
            if (bonus_timer > SHAKE_LEN) { can_shake[c] = 0; can_frame[c] = CF_STILL; }
        }
        if (bonus_timer >= SHAKE_LEN + SHAKE_GAP) {
            bonus_timer = 0;
            if (++oi >= 5) { bonus_phase = PH_SWAP; say("WATCH THE CAN"); }
        }
        break;
    case PH_SWAP:
        if (bonus_moving) step_swap();
        else if (bonus_swaps_done >= bonus_swaps_total) { bonus_phase = PH_CHOOSE; bonus_timer = 0; say("PICK THE CALM CAN"); }
        else if (bonus_timer >= (bonus_swaps_done ? (uint16_t)bonus_swap_dur / 4 : 20)) start_swap();
        break;
    case PH_CHOOSE:
        if ((pressed & J_LEFT) && bonus_cursor) bonus_cursor--;
        else if ((pressed & J_RIGHT) && bonus_cursor < NUM_CANS - 1) bonus_cursor++;
        if (pressed & J_A) {
            bonus_picked = slot_can[bonus_cursor];
            bonus_phase = PH_RESULT; bonus_timer = 0;
            if (bonus_picked == bonus_calm_can) {
                bonus_won = 1;
                can_frame[bonus_picked] = CF_OPEN;
                SFX(SFX_COIN);
                if (game_state != GS_MINI) { add_score(BONUS_SCORE); say("WINNER 3000"); }
                else {                                          // Practice: 1000 a level (the medal's thresholds, mg.h), 3000 in all
                    add_score(BONUS_SCORE / 3);
                    say(bonus_round < 3 ? "LEVEL CLEARED" : "WINNER 3000");
                }
            } else {
                can_frame[bonus_picked] = CF_BURST;
                SFX(SFX_BREAK);
                say("OH NO");
            }
        }
        break;
    case PH_RESULT:
        if (bonus_won && game_state == GS_MINI && bonus_round < 3) {     // Practice: on to the next, faster level
            if (bonus_timer >= 70) {
                bonus_round++;
                setup_round(1, 0);
                bonus_phase = PH_SHOW; bonus_timer = 0;
                say(bonus_round == 2 ? "LEVEL 2" : "LEVEL 3");
            }
        } else if (bonus_timer >= RESULT_LEN) return 1;
        break;
    }
    draw();
    return 0;
}
