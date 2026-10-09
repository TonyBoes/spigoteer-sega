// Bonus round: a shell game. Six cans stand on one long counter; five get shaken one at a
// time in random order, the sixth is left calm. The cans then swap places in pairs, hopping
// over each other, and the player picks the calm one. Right: it opens, +3000. Wrong: the
// picked can bursts and sprays foam at the bartender.
//
// Own screen (LCD off to enter). Sprite budget: foam 0-2, cursor 3, bartender 4-7, cans 8-13.
// Cans, foam and cursor are on different scanline bands except the foam crossing the can band
// (6 cans + 3 foam = 9 <= 10 per line).
#pragma bank 255
#include <gb/gb.h>
#include <gb/cgb.h>
#include <stdint.h>

#include "art.h"
#include "bonus.h"
#include "can_tiles.h"      // static const uint8_t bonus_tiles[]: this bank's own art data

// ---- shared with main.c (bank 0) ----
extern uint8_t is_cgb, level, overlay_on, hud_dirty, life_lost, vq_count, vram_pending;
extern uint32_t score;
extern uint8_t next_rand(void);
extern void add_score(uint16_t n);
extern void draw_hud(void);
extern void clear_dirty(void);
extern void vram_put(uint8_t x, uint8_t y, const uint8_t *src, uint8_t n);
extern uint8_t glyph_for(char c);
extern void vq_add(uint8_t bank, const uint8_t *src, uint8_t x, uint8_t y, uint8_t n);

// ---- layout (screen px unless noted) ----
#define OBJ_BONUS        96     // first OBJ tile: the dancers' 32 tiles (96..127) are borrowed and reloaded by main
#define OBJ_FOAM         (OBJ_BONUS + CAN_TILE_COUNT)
#define OBJ_CURSOR       (OBJ_FOAM + FOAM_FRAMES * 2)
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
#define BT_CATCH_F        5
#define BT_FAIL_F         6
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

static uint8_t can_dy[NUM_CANS];      // hop height now
static uint8_t order[5], oi;          // shake order
uint8_t  bonus_timer;               // frames in the current step
static uint8_t swap_a, swap_b, swap_t;
static uint8_t txt[20];
static uint8_t rowbuf[20];

static void make_text(const char *s) {
    uint8_t n = 0, i;
    for (i = 0; i < 20; i++) txt[i] = TILE_HUD_BLANK;
    while (s[n]) n++;
    for (i = 0; i < n; i++) txt[((20 - n) >> 1) + i] = glyph_for(s[i]);
}

static void say(const char *s) {      // during play: through the VBlank queue
    make_text(s);
    vq_add(0, txt, 0, TEXT_ROW, 20);
}

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
}

// whole screen, LCD off
static void draw_scene(void) {
    uint8_t y, i;
    draw_hud();
    for (y = 1; y < 18; y++) {
        if (y == TEXT_ROW) { make_text("BONUS ROUND"); vram_put(0, y, txt, 20); continue; }
        for (i = 0; i < 20; i++)
            rowbuf[i] = y == 17 ? TILE_FLOOR : y == COUNTER_ROW ? TILE_COUNTER
                      : (y & 1) && (i & 1) ? TILE_WALL2 : TILE_WALL;
        vram_put(0, y, rowbuf, 20);
    }
    if (is_cgb) {
        VBK_REG = VBK_BANK_1;
        for (y = 1; y < 18; y++) {
            for (i = 0; i < 20; i++) rowbuf[i] = y == TEXT_ROW ? 1 : 0;      // BG palette 1 = HUD, 0 = wall/counter
            vram_put(0, y, rowbuf, 20);
        }
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

void bonus_enter(void) BANKED {
    uint8_t i;
    DISPLAY_OFF;
    overlay_on = 0; HIDE_WIN; vq_count = 0; hud_dirty = 0; life_lost = 0; vram_pending = 0;
    clear_dirty();
    for (i = 0; i < 40; i++) shadow_OAM[i].y = 0;
    set_sprite_data(OBJ_BONUS, BONUS_TILE_COUNT, bonus_tiles);
    if (is_cgb) load_palettes();
    draw_scene();

    bonus_round++;
    bonus_phase = PH_SHOW; bonus_won = 0; bonus_moving = 0; bonus_swaps_done = 0;
    bonus_swaps_total = 6 + bonus_round;
    bonus_swap_dur = bonus_round < 3 ? 30 : (bonus_round < 6 ? 34 - 4 * bonus_round : 14);   // rounds 1-2 slow, then 22, 18, 14
    bonus_calm_can = next_rand() % NUM_CANS;
    bonus_calm = bonus_calm_can;
    bonus_cursor = 2;
    for (i = 0; i < NUM_CANS; i++) {
        slot_can[i] = i; can_pos[i] = slot_x(i); can_frame[i] = CF_STILL; can_shake[i] = 0;
        can_shaken[i] = 0; can_dy[i] = 0;
    }
    shuffle_order();
    oi = 0; bonus_timer = 0; swap_t = 0;
    DISPLAY_ON;
}

// ---- drawing ----
static void spr(uint8_t i, uint8_t x, uint8_t y, uint8_t tile, uint8_t prop) {
    OAM_item_t *o = &shadow_OAM[i];
    o->y = y; o->x = x; o->tile = tile; o->prop = prop;
}

static void draw(void) {
    uint8_t i, f, base, k, bf = BT_IDLE_F, x, y;
    for (i = 0; i < NUM_CANS; i++) {
        x = can_pos[i];
        f = can_frame[i];
        if (can_shake[i]) x += (f == CF_LEFT) ? 0xFF : 1;          // +-1 px wiggle
        spr(8 + i, x + 8, CAN_TOP + 16 - can_dy[i], OBJ_BONUS + 2 * f, OBJPAL_CAN);
    }
    // cursor: only while choosing / after the pick
    if (bonus_phase >= PH_CHOOSE) spr(3, slot_x(bonus_cursor) + 8, CURSOR_Y + 16 + ((bonus_timer >> 3) & 1), OBJ_CURSOR, OBJPAL_FOAM);
    else shadow_OAM[3].y = 0;
    // foam spray at the bartender after a wrong pick
    if (bonus_phase == PH_RESULT && !bonus_won) {
        bf = BT_FAIL_F;
        for (k = 0; k < 3; k++) {
            int16_t t = (int16_t)bonus_timer - 8 * k - 6;           // travel 30 frames, staggered
            int16_t sx = can_pos[bonus_picked] + 8, sy = CAN_TOP + 4;
            int16_t tx = BT_X + 8 + 4 + (k - 1) * 5, ty = BT_TOP + 10 + k * 2;
            if (t < 0) { shadow_OAM[k].y = 0; continue; }
            if (t > 30) t = 30;
            x = (uint8_t)(sx + (tx - sx) * t / 30);
            y = (uint8_t)(sy + (ty - sy) * t / 30 - (t * (30 - t)) / 20);   // arc
            spr(k, x, y, OBJ_FOAM + 2 * (k & 1), OBJPAL_FOAM);
        }
    } else {
        for (k = 0; k < 3; k++) shadow_OAM[k].y = 0;
    }
    if (bonus_phase == PH_RESULT && bonus_won) bf = BT_CATCH_F;
    base = bf * BARTENDER_TILES_PER_FRAME;       // OBJ tiles 0.. hold the bartender frames
    spr(4, BT_X + 8,  BT_TOP + 16, base,     0);
    spr(5, BT_X + 16, BT_TOP + 16, base + 2, 0);
    spr(6, BT_X + 8,  BT_TOP + 32, base + 4, 0);
    spr(7, BT_X + 16, BT_TOP + 32, base + 6, 0);
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
    int16_t span;
    swap_t++;
    ax = slot_x(swap_a); bx = slot_x(swap_b);
    span = (int16_t)bx - ax;
    can_pos[ca] = (uint8_t)(ax + span * swap_t / dur);
    can_pos[cb] = (uint8_t)(bx - span * swap_t / dur);
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
    bonus_timer++;
    switch (bonus_phase) {
    case PH_SHOW:
        if (bonus_timer >= SHOW_LEN) { bonus_phase = PH_SHAKE; bonus_timer = 0; say("ONE STAYS CALM"); }
        break;
    case PH_SHAKE:
        c = order[oi];
        if (bonus_timer == 1) { can_shake[c] = 1; can_shaken[c] = 1; }
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
        else if (bonus_timer >= (bonus_swaps_done ? bonus_swap_dur / 4 : 20)) start_swap();
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
                add_score(BONUS_SCORE);
                say("WINNER 3000");
            } else {
                can_frame[bonus_picked] = CF_BURST;
                say("OH NO");
            }
        }
        break;
    case PH_RESULT:
        if (bonus_timer >= RESULT_LEN) return 1;
        break;
    }
    draw();
    return 0;
}
