// Bonus rounds 2 and 3 (M12), rotating with the can shake-up (bonus.c): round 1 shake-up, 2 Perfect Pour,
// 3 Tip Shower, then again. bonus.c's bonus_enter() / bonus_update() hand over to this file when bonus_kind != 0.
// Both rounds stand in the venue backdrop like the shake-up, show a two-line banner (name, instruction) first, and end
// in bonus_phase PH_END (4, the shake-up's PH_RESULT) for BONUS_END_LEN frames, so the same poke ends any round.
//
// PERFECT POUR: a tall glass (BG tiles, its interior colour 0) under a tap. Hold A: the beer (sprites drawn behind BG
// colours 1-3, so they only show inside the glass) rises 1 px per POUR_RATE frames with a FOAM_POUR px head. Release:
// the head keeps rising FOAM_RISE px more. The final level (beer + foam) against the line: within 1 px PERFECT +3000,
// within 4 px GOOD +1500, past the rim SPILL (foam heap over the rim, streaks down the outside), else TOO LOW / TOO HIGH.
// Three glasses, each with its own line height.
//   OAM: bartender 4-7, dome 8-9 (in front of the beer), beer 10-13, foam 14-15, stream 16-18, arrows 19-20,
//   spill streaks 21-24, tap 25-27. At most 9 on a line (2 columns x beer 2 + foam 1, stream 1, arrows 2).
// TIP SHOWER: the bartender walks the floor with a tray held in front of him at waist height (1.75 px per frame; D5b, owner
// 2026-10-15: it was over his head). Coins and rotten tomatoes fall
// at varied x and speeds. A coin on a clean tray: +100. A tomato on the tray: it is dirty for TRAY_DIRTY frames and
// catches nothing. TIPS_TIME frames, timer on the banner.
//   OAM: falling items 4-10 (at most TS_ITEMS), tray 11-14, bartender 15-18. The tray's 4 entries (the art is 24 wide in a 32-wide
//   frame) sit on the same x as his two (a tie on DMG, where the smaller x wins, goes to the lower index) and have lower indexes, so
//   the tray is in front of him on both models; the items have the lowest, so a coin falls in front of him (on a DMG a coin
//   whose x is a little past his left half still goes behind it for a few frames: sprite priority there is by x).
//   On the tray's lines: 2 (him) + 4 (tray) + the items on that line (the items are at least 14 frames apart): <= 10.
#pragma bank 255
#include <gb/gb.h>
#include <gb/cgb.h>
#include <stdint.h>

#include "game.h"
#include "bonus.h"
#include "palettes.h"
#include "music.h"
#include "bonus2_art.h"     // this bank's own art data

extern uint8_t joy;

#define OBJ_B2          96      // the show performers' OBJ tiles (96..127) are borrowed, as in the shake-up
#define B2_BG           (BAR_TILE_COUNT + 48)   // BG ids over the patron tiles (no patrons here; the level load reloads them); from MG_GAME_BG (mg.h):
                                                // BONUS > MINI GAMES runs the round with the framework's medal icon in 77..124 for its result window
#define OPAL_DRINK      6
#define OPAL_RED        7
#define OPAL_TAP        3                   // the tap: the game's old glass palette (slot 3 is a lifted patron's in play, M13a)
#define BPAL_GLASS      BGPAL_PATRON        // the level load sets the patron palettes again
#define COUNTER_ROW     11
#define TEXT_ROW_A      2
#define TEXT_ROW_B      3
#define BT_X            72
#define BT_OAM_Y        (112 + 16)
#define BANNER_LEN      BONUS_BANNER_LEN
#define BONUS_END_LEN   130
#define PH_END          4

// ---- Perfect Pour ----
enum { PP_INTRO, PP_READY, PP_POUR, PP_SETTLE };
enum { PR_NONE, PR_PERFECT, PR_GOOD, PR_LOW, PR_HIGH, PR_SPILL };
#define GLASS_COL       9
#define GLASS_ROW       6
#define PG_X         (GLASS_COL * 8)
#define RIM_Y           (GLASS_ROW * 8)      // 48
#define INNER_BOT       (RIM_Y + 32)         // 80: interior bottom (the base starts here)
#define GLASS_H         32
#define TAP_Y           32
#define POUR_RATE       4       // frames per px of beer (NORMAL)
// Perfect Pour per difficulty (indexed by BONUS_DIFF: NORMAL, HARD, EASY; ARCADE / CLASSIC play NORMAL), TUNING.md: frames per px of beer and the
// PERFECT and GOOD windows (px off the line).
static const uint8_t pour_rate[3] = { POUR_RATE, 3, 5 }, pour_perfect[3] = { 1, 1, 2 }, pour_good[3] = { 4, 3, 5 };
#define FOAM_POUR       3       // head while pouring
#define FOAM_RISE       4       // ... and how much more it rises after the release
#define FOAM_RISE_STEP  8       // frames per px of that rise
#define READY_MAX       360     // a glass nobody pours is judged empty after this long
#define RESULT_SHOW     100
#define NUM_GLASSES     3
#define F_LIQ 0
#define F_HALF 1
#define F_FOAM 2
#define F_DOME 3
#define F_STREAK 4
#define F_HEAD 5
#define F_TAPA 6
#define F_TAPB 7
#define F_TAPB_OPEN 8
#define F_TAPC 9
#define F_STREAM 10
#define F_ARROW 11
#define PT(f)           (OBJ_B2 + 2 * (f))

// ---- Tip Shower ----
#define TS_ITEMS        7
#define TS_COIN         1
#define TS_TOMATO       2
#define TS_SPLAT        3
#define TRAY_OAM_Y      (BT_OAM_Y + 8)    // the tray frame covers his body rows 8-23 (belt height; D5b was 12-27, owner 2026-10-15: a bit higher)
#define TRAY_SURFACE    125     // screen y of the tray's top (his body row 13)
#define OAM_ITEMS       4
#define OAM_TRAY        11
#define OAM_BT_TIPS     15
#define FLOOR_Y         136
#define TS_TOP          32      // items appear under the banner
#define TIPS_TIME       1200    // 20 s
#define TRAY_DIRTY      60
// Tip Shower per difficulty (indexed by BONUS_DIFF: NORMAL, HARD, EASY; ARCADE / CLASSIC play NORMAL), TUNING.md: frames to the next item (+ 0..15), a tomato
// when (random & mask) < tomatoes, an item's speed (vbase + 0..vrange - 1, 1/16 px a frame), and the frames a tomato dirties the tray.
static const struct { uint8_t spawn, mask, tomatoes, vbase, vrange, dirty; } tips_tune[3] = {
    { 14, 3, 1, 12, 17, TRAY_DIRTY }, { 10, 7, 3, 16, 21, 90 }, { 18, 7, 1, 10, 13, 36 },
};
#define TIPT            tips_tune[BONUS_DIFF()]
#define TRAY_MIN        8
#define TRAY_MAX        136
#define TIP_VALUE       100
#define TT_TRAY         0
#define TT_TRAY_DIRTY   4
#define TT_TOMATO       8
#define TT_SPLAT        9
#define TTL(f)          (OBJ_B2 + 2 * (f))

extern uint8_t bonus_phase, bonus_timer;

uint8_t  pour_glass;        // 0..2
uint8_t  pour_target;       // index into pour_target_px[]
uint8_t  pour_line;         // the line, px above the interior's bottom
uint8_t  pour_liquid;       // beer, px
uint8_t  pour_foam;         // foam head, px
uint8_t  pour_rise;         // foam still to rise after the release, px
uint8_t  pour_result;       // PR_* of the glass just judged
uint8_t  pour_sub;          // frame counter of the beer and foam steps
uint8_t  pour_spill_t;      // frames since the spill
uint16_t pour_wait;         // frames in PP_READY
uint16_t bonus2_total;      // points this round

uint8_t  tray_x, tray_frac, tray_dirty, tray_left, tray_walk;
uint8_t  tips_caught, tips_tomatoes;
uint16_t tips_time;         // frames left
uint8_t  tips_spawn;        // frames to the next item
uint8_t  ts_type[TS_ITEMS], ts_x[TS_ITEMS], ts_v[TS_ITEMS];   // ts_v: 1/16 px per frame (a splat: frames left)
uint16_t ts_y[TS_ITEMS];    // screen y of the art's top, 1/16 px

static uint8_t glass_buf[2], line_buf[2];
static uint8_t last_secs;

// the text rows: main.c's mg_say (ROM0, so the strings stay in this bank); '!' is this round's own tile (say_bang)
#define sayA(s) mg_say(TEXT_ROW_A, s)
#define sayB(s) mg_say(TEXT_ROW_B, s)

// "<word> <n>" with n written in place of the '#' run at the end of s (its length = the digits shown)
static void say_num(uint8_t row, const char *s, uint16_t n) {
    static char tmp[20];
    uint8_t i = 0, j;
    while (s[i]) { tmp[i] = s[i]; i++; }
    tmp[i] = 0;
    static const uint16_t pw[5] = { 1, 10, 100, 1000, 10000 };
    uint8_t k, d;
    for (j = i; j && tmp[j - 1] == '#'; j--) ;
    k = i - j;                                   // the digits shown (1..4); n keeps its low k digits, as n % 10 per digit did
    while (n >= pw[k]) n -= pw[k];
    while (k--) {                                // (digit by subtraction: the 16-bit divide and modulo cost 71 lines once)
        for (d = 0; n >= pw[k]; d++) n -= pw[k];
        tmp[i - 1 - k] = '0' + d;
    }
    mg_say(row, tmp);
}

static void spr(uint8_t i, uint8_t x, uint8_t y, uint8_t tile, uint8_t prop) {
    OAM_item_t *o = &shadow_OAM[i];
    o->y = y; o->x = x; o->tile = tile; o->prop = prop;
}

static void hide(uint8_t i, uint8_t n) { while (n--) shadow_OAM[i++].y = 0; }

static void draw_bt(uint8_t o, uint8_t x, uint8_t f, uint8_t left) {     // OAM o..o+3
    uint8_t base = BT_PIC(f) * BARTENDER_TILES_PER_FRAME, xa = x + 8, xb = x + 16, fl = 0;
    if (left) { xa = x + 16; xb = x + 8; fl = S_FLIPX; }
    spr(o, xa, (uint8_t)BT_OAM_Y,      base,     fl);
    spr(o + 1, xb, (uint8_t)BT_OAM_Y,      base + 2, fl);
    spr(o + 2, xa, (uint8_t)(BT_OAM_Y + 16), base + 4, fl);
    spr(o + 3, xb, (uint8_t)(BT_OAM_Y + 16), base + 6, fl);
}

static void load_palettes(void) {
    uint16_t p[4];
    if (!is_cgb) { OBP1_REG = 0xE0; return; }     // DMG: OBP1 idx1 white, idx2 dark grey, idx3 black (tomatoes, dirty tray)
    p[0] = 0;
    p[1] = RGB8(248, 240, 208);                   // cream foam
    p[2] = RGB8(224, 152, 32);                    // amber beer
    p[3] = RGB8(80, 48, 16);
    set_sprite_palette(OPAL_DRINK, 1, p);
    p[1] = RGB8(240, 240, 232);
    p[2] = RGB8(216, 48, 32);                     // tomato red, the line arrows
    p[3] = RGB8(48, 24, 16);
    set_sprite_palette(OPAL_RED, 1, p);
    p[0] = RGB8(216, 232, 240);                   // the glass: pale interior, white highlight, red line, dark outline
    p[1] = RGB8(255, 255, 255);
    p[2] = RGB8(224, 48, 48);
    p[3] = RGB8(40, 48, 64);
    set_bkg_palette(BPAL_GLASS, 1, p);
    pal_get(PAL_GLASS, p); set_sprite_palette(OPAL_TAP, 1, p);  // M13a: the game's slots 3 and 5 hold a patron and the show
    pal_get(PAL_COIN, p); set_sprite_palette(OBJPAL_COIN, 1, p);   // (the level load puts them back; coin_pal itself may hold the lifted show, render.c pal5_check)
    pal5_cur = 1;
}

static void banner(const char *a, const char *b) {   // LCD off: the two text rows in the HUD colours
    uint8_t i;
    sayA(a);                                          // (LCD off: mg_say writes them at once)
    sayB(b);
    if (is_cgb) {
        VBK_REG = VBK_BANK_1;
        for (i = 0; i < 20; i++) row_buf[i] = BGPAL_HUD;
        vram_put(0, TEXT_ROW_A, row_buf, 20);
        vram_put(0, TEXT_ROW_B, row_buf, 20);
        VBK_REG = VBK_BANK_0;
    }
}

// ================================ PERFECT POUR ================================
static void set_line(uint8_t k, uint8_t now) {   // the glass's line row: k's line tiles (now: LCD off)
    uint8_t r = pour_line_row[k];
    line_buf[0] = B2_BG + 10 + 2 * k; line_buf[1] = line_buf[0] + 1;
    if (now) vram_put(GLASS_COL, GLASS_ROW + r, line_buf, 2);
    else vq_add(0, line_buf, GLASS_COL, GLASS_ROW + r, 2);
}

static void clear_line(uint8_t k) {              // put the plain glass back on k's line row (through the queue)
    uint8_t r = pour_line_row[k];
    glass_buf[0] = B2_BG + 2 * r; glass_buf[1] = glass_buf[0] + 1;
    vq_add(0, glass_buf, GLASS_COL, GLASS_ROW + r, 2);
}

static uint8_t pour_used;        // targets this round (bit k)

static void pour_next_target(void) {    // a line not used yet this round, and not next to the last one
    uint8_t k;
    if (!pour_glass) pour_used = 0;
    do k = next_rand() % POUR_TARGETS;
    while (((pour_used >> k) & 1) || (pour_glass && (k + 1 == pour_target || k == pour_target + 1)));
    pour_used |= 1 << k;
    pour_target = k;
    pour_line = pour_target_px[k];
}

static void pour_new_glass(uint8_t now) {
    uint8_t old = pour_target;
    pour_next_target();
    if (!now) clear_line(old);
    set_line(pour_target, now);
    pour_liquid = 0; pour_foam = 0; pour_rise = 0; pour_result = PR_NONE; pour_sub = 0; pour_spill_t = 0; pour_wait = 0;
}

static void pour_enter(void) {
    uint8_t r, t[2];
    set_sprite_data(OBJ_B2, POUR_OBJ_TILES, pour_obj_tiles);
    banner("PERFECT POUR", "FILL TO THE LINE");
    for (r = 0; r < 5; r++) {
        t[0] = B2_BG + 2 * r; t[1] = t[0] + 1;
        vram_put(GLASS_COL, GLASS_ROW + r, t, 2);
    }
    if (is_cgb) {
        VBK_REG = VBK_BANK_1;
        t[0] = t[1] = BPAL_GLASS;
        for (r = 0; r < 5; r++) vram_put(GLASS_COL, GLASS_ROW + r, t, 2);
        VBK_REG = VBK_BANK_0;
    }
    pour_glass = 0; pour_target = 0;
    pour_new_glass(1);
}

static void pour_judge(void) {
    uint8_t lv = pour_liquid + pour_foam, d;
    d = lv > pour_line ? lv - pour_line : pour_line - lv;
    if (lv > GLASS_H) pour_result = PR_SPILL;
    else if (d <= pour_perfect[BONUS_DIFF()]) pour_result = PR_PERFECT;
    else if (d <= pour_good[BONUS_DIFF()]) pour_result = PR_GOOD;
    else pour_result = lv < pour_line ? PR_LOW : PR_HIGH;
    bonus_timer = 0;
    switch (pour_result) {
    case PR_PERFECT: add_score(3000); bonus2_total += 3000; SFX(SFX_COIN); sayB("PERFECT! 3000"); break;
    case PR_GOOD:    add_score(1500); bonus2_total += 1500; SFX(SFX_SERVE); sayB("GOOD 1500"); break;
    case PR_SPILL:   SFX(SFX_BREAK); sayB("SPILL!"); break;
    case PR_LOW:     sayB("TOO LOW"); break;
    default:         sayB("TOO HIGH"); break;
    }
}

static void pour_spill_check(void) {
    if (pour_liquid + pour_foam > GLASS_H) {
        if (pour_liquid > GLASS_H - 2) pour_liquid = GLASS_H - 2;
        pour_rise = 0;
        bonus_phase = PP_SETTLE;
        pour_judge();
    }
}

static void draw_pour(void) {
    uint8_t L = pour_liquid, T = L + pour_foam, x, y, k, pal = OPAL_DRINK, pr = S_PRIORITY | OPAL_DRINK;
    uint8_t spilled = pour_result == PR_SPILL, pouring = bonus_phase == PP_POUR;
    if (!is_cgb) { pal = 0; pr = S_PRIORITY; }
    // dome (in front of the beer) and the spill streaks
    if (spilled) {
        spr(8, PG_X + 8,  RIM_Y - 6 + 16, PT(F_DOME), pal | S_FLIPX);
        spr(9, PG_X + 16, RIM_Y - 6 + 16, PT(F_DOME), pal);
        y = RIM_Y + 16;
        spr(21, PG_X,      y, PT(F_STREAK), pal | S_FLIPX);
        spr(22, PG_X + 24, y, PT(F_STREAK), pal);
        k = pour_spill_t >> 1; if (k > 24) k = 24;
        spr(23, PG_X,      y + k, PT(F_HEAD), pal | S_FLIPX);
        spr(24, PG_X + 24, y + k, PT(F_HEAD), pal);
    } else { hide(8, 2); hide(21, 4); }
    // beer: A from the bottom, B up to the level when it is above 16 px
    if (!L) hide(10, 4);
    else {
        y = INNER_BOT + 16 - (L > 16 ? 16 : L);
        k = L <= 8 ? PT(F_HALF) : PT(F_LIQ);
        spr(10, PG_X + 8, y, k, pr); spr(11, PG_X + 16, y, k, pr);
        if (L > 16) { y = INNER_BOT + 16 - L; spr(12, PG_X + 8, y, PT(F_LIQ), pr); spr(13, PG_X + 16, y, PT(F_LIQ), pr); }
        else hide(12, 2);
    }
    if (pour_foam && !spilled) {
        y = INNER_BOT + 16 - T;
        spr(14, PG_X + 8, y, PT(F_FOAM), pr); spr(15, PG_X + 16, y, PT(F_FOAM), pr);
    } else hide(14, 2);
    // the stream: tap to the glass (in front), then inside the glass (behind the BG, and behind the beer)
    if (pouring) {
        spr(16, PG_X + 16, TAP_Y + 12 + 16, PT(F_STREAM), pal);
        spr(17, PG_X + 16, RIM_Y + 12 + 16, PT(F_STREAM), pr);
        if (L < 16) spr(18, PG_X + 16, RIM_Y + 16 + 16, PT(F_STREAM), pr); else hide(18, 1);
    } else hide(16, 3);
    // line arrows (tip row 3 on the line)
    if (!spilled) {
        y = INNER_BOT - pour_line - 3 + 16;
        k = is_cgb ? OPAL_RED : 0;
        spr(19, PG_X,      y, PT(F_ARROW), k);
        spr(20, PG_X + 24, y, PT(F_ARROW), k | S_FLIPX);
    } else hide(19, 2);
    // the tap
    k = is_cgb ? OPAL_TAP : 0;
    x = PG_X;
    spr(25, x,      TAP_Y + 16, PT(F_TAPA), k);
    spr(26, x + 8,  TAP_Y + 16, pouring ? PT(F_TAPB_OPEN) : PT(F_TAPB), k);
    spr(27, x + 16, TAP_Y + 16, PT(F_TAPC), k);
    // and the bartender
    draw_bt(4, BT_X, pour_result == PR_SPILL ? BT_FAIL : pour_result == PR_PERFECT ? BT_CATCH : pouring ? BT_FILL : BT_IDLE, 0);
}

static uint8_t pour_update(void) {
    uint8_t held = joy & J_A;
    switch (bonus_phase) {
    case PP_INTRO:
        if (bonus_timer >= BANNER_LEN) { bonus_phase = PP_READY; bonus_timer = 0; say_num(TEXT_ROW_A, "GLASS #", 1); }
        break;
    case PP_READY:
        if (held) { bonus_phase = PP_POUR; pour_sub = 0; SFX(SFX_FILL); }
        else if (++pour_wait >= READY_MAX) { bonus_phase = PP_SETTLE; pour_judge(); }
        break;
    case PP_POUR:
        if (!held) { bonus_phase = PP_SETTLE; bonus_timer = 0; pour_sub = 0; pour_rise = pour_liquid ? FOAM_RISE : 0; break; }
        if (++pour_sub >= pour_rate[BONUS_DIFF()]) {
            pour_sub = 0;
            pour_liquid++;
            if (pour_foam < FOAM_POUR && pour_liquid >= 2 * (pour_foam + 1)) pour_foam++;
            if (!(pour_liquid & 3)) SFX(SFX_FILL);
            pour_spill_check();
        }
        break;
    case PP_SETTLE:
        if (pour_result == PR_NONE) {
            if (!pour_rise) pour_judge();
            else if (++pour_sub >= FOAM_RISE_STEP) { pour_sub = 0; pour_foam++; pour_rise--; pour_spill_check(); }
            break;
        }
        if (pour_result == PR_SPILL) pour_spill_t++;
        if (bonus_timer >= RESULT_SHOW) {
            bonus_timer = 0;
            if (++pour_glass >= NUM_GLASSES) {
                bonus_phase = PH_END;
                sayA("POUR BONUS"); say_num(TEXT_ROW_B, "BONUS ####", bonus2_total);
                pour_liquid = pour_foam = 0; pour_result = PR_NONE;
            } else {
                pour_new_glass(0);
                bonus_phase = PP_READY;
                say_num(TEXT_ROW_A, "GLASS #", pour_glass + 1);
                sayB("FILL TO THE LINE");
            }
        }
        break;
    }
    draw_pour();
    return 0;
}

// ================================ TIP SHOWER ================================
static void tips_enter(void) {
    uint8_t i;
    set_sprite_data(OBJ_B2, TIPS_OBJ_TILES, tips_obj_tiles);
    banner("TIP SHOWER", "CATCH THE TIPS");
    tray_x = BT_X; tray_frac = 0; tray_dirty = 0; tray_left = 0; tray_walk = 0;
    tips_caught = 0; tips_tomatoes = 0; tips_time = TIPS_TIME; tips_spawn = 10; last_secs = 0;
    for (i = 0; i < TS_ITEMS; i++) ts_type[i] = 0;
}

static void tips_spawn_item(void) {
    uint8_t i, r;
    for (i = 0; i < TS_ITEMS; i++) if (!ts_type[i]) break;
    if (i == TS_ITEMS) return;
    r = next_rand();
    ts_type[i] = (r & TIPT.mask) < TIPT.tomatoes ? TS_TOMATO : TS_COIN;
    ts_x[i] = 8 + next_rand() % 145;                  // 8..152
    ts_v[i] = TIPT.vbase + next_rand() % TIPT.vrange;                  // 0.75 .. 1.75 px per frame
    ts_y[i] = TS_TOP << 4;
}

static void tips_items(void) {
    uint8_t i, bot0, bot1, cx;
    for (i = 0; i < TS_ITEMS; i++) {
        if (!ts_type[i]) continue;
        if (ts_type[i] == TS_SPLAT) { if (!--ts_v[i]) ts_type[i] = 0; continue; }
        bot0 = (uint8_t)(ts_y[i] >> 4) + 8;
        ts_y[i] += ts_v[i];
        bot1 = (uint8_t)(ts_y[i] >> 4) + 8;
        cx = ts_x[i] + 4;
        if (bot0 < TRAY_SURFACE && bot1 >= TRAY_SURFACE && cx + 4 >= tray_x && cx <= tray_x + 20) {   // the tray spans x-4..x+19
            if (ts_type[i] == TS_TOMATO) {
                ts_type[i] = 0; tray_dirty = TIPT.dirty; tips_tomatoes++; SFX(SFX_BREAK);
                continue;
            }
            if (!tray_dirty) {
                ts_type[i] = 0; tips_caught++; add_score(TIP_VALUE); bonus2_total += TIP_VALUE; SFX(SFX_COIN);
                say_num(TEXT_ROW_B, "COINS ##", tips_caught);
                continue;
            }
        }
        if (bot1 >= FLOOR_Y) {
            if (ts_type[i] == TS_TOMATO) { ts_type[i] = TS_SPLAT; ts_v[i] = 20; ts_y[i] = (uint16_t)(FLOOR_Y - 16) << 4; }
            else ts_type[i] = 0;
        }
    }
}

static void draw_tips(void) {
    uint8_t i, f, o = OAM_ITEMS, pal, k;
    // the tray at his waist: clean (palette 0) or dirty (the red palette, OBP1 on DMG)
    f = tray_dirty ? TT_TRAY_DIRTY : TT_TRAY;
    pal = tray_dirty ? (is_cgb ? OPAL_RED : S_PALETTE) : 0;
    for (k = 0; k < 4; k++) spr(OAM_TRAY + k, tray_x + 8 * k, (uint8_t)TRAY_OAM_Y, TTL(f + k), pal);   // (x - 8 + 8 on the OAM's offset)
    for (i = 0; i < TS_ITEMS; i++, o++) {
        switch (ts_type[i]) {
        case TS_COIN:   spr(o, ts_x[i] + 8, (uint8_t)(ts_y[i] >> 4) + 8, OBJ_COIN + ((ts_v[i] + (bonus_timer >> 3)) & 2), is_cgb ? OBJPAL_COIN : 0); break;
        case TS_TOMATO: spr(o, ts_x[i] + 8, (uint8_t)(ts_y[i] >> 4) + 16, TTL(TT_TOMATO), is_cgb ? OPAL_RED : S_PALETTE); break;
        case TS_SPLAT:  spr(o, ts_x[i] + 8, (uint8_t)(ts_y[i] >> 4) + 16, TTL(TT_SPLAT), is_cgb ? OPAL_RED : S_PALETTE); break;
        default:        shadow_OAM[o].y = 0;
        }
    }
    f = BT_IDLE;
    if (tray_dirty > TIPT.dirty - 20) f = BT_FAIL;
    else if (tray_walk) f = (tray_walk & 8) ? BT_WALK1 : BT_WALK2;
    draw_bt(OAM_BT_TIPS, tray_x, f, tray_left);
}

static uint8_t tips_update(void) {
    uint8_t s, i;
    switch (bonus_phase) {
    case 0:
        if (bonus_timer >= BANNER_LEN) {
            bonus_phase = 1; bonus_timer = 0;
            say_num(TEXT_ROW_A, "TIME ##", 20); say_num(TEXT_ROW_B, "COINS ##", 0);
            last_secs = 20;
        }
        break;
    case 1:
        // the walk: 1.75 px per frame
        tray_walk = 0;
        if (joy & J_LEFT) {
            tray_left = 1;
            s = tray_frac; tray_frac -= 192; i = 1 + (tray_frac > s);
            tray_x = tray_x > TRAY_MIN + i ? tray_x - i : TRAY_MIN;
            tray_walk = (uint8_t)(bonus_timer | 1);
        } else if (joy & J_RIGHT) {
            tray_left = 0;
            s = tray_frac; tray_frac += 192; i = 1 + (tray_frac < s);
            tray_x = tray_x + i < TRAY_MAX ? tray_x + i : TRAY_MAX;
            tray_walk = (uint8_t)(bonus_timer | 1);
        }
        if (tray_dirty) tray_dirty--;
        if (!--tips_spawn) { tips_spawn_item(); tips_spawn = TIPT.spawn + (next_rand() & 15); }
        tips_items();
        tips_time--;
        s = last_secs;                           // (ceil(tips_time / 60): re-derived only when tips_time leaves the last value's 60-frame band)
        { uint16_t hi = ((uint16_t)s << 6) - ((uint16_t)s << 2); if (tips_time > hi || tips_time + 60 <= hi) s = (uint8_t)((tips_time + 59) / 60); }
        if (s != last_secs) { last_secs = s; say_num(TEXT_ROW_A, "TIME ##", s); }
        if (!tips_time) {
            bonus_phase = PH_END; bonus_timer = 0; tray_dirty = 0;
            for (i = 0; i < TS_ITEMS; i++) ts_type[i] = 0;
            sayA("TIME UP"); say_num(TEXT_ROW_B, "BONUS ####", bonus2_total);
            SFX(SFX_SERVE);
        }
        break;
    }
    draw_tips();
    return 0;
}

// ================================ entry points ================================
// LCD is off; bonus.c has drawn the HUD and the venue backdrop and hidden every sprite.
void bonus2_enter(void) BANKED {
    load_palettes();
    set_bkg_data(B2_BG, B2_BG_TILES, b2_bg_tiles);
    say_bang = (uint8_t)(B2_BG + B2_BANG);                   // mg_say draws '!' with this round's tile
    bonus2_total = 0;
    if (bonus_kind == 1) pour_enter(); else tips_enter();
    if (bonus_kind == 1) draw_pour(); else draw_tips();
}

uint8_t bonus2_update(void) BANKED {
    bonus_timer++;
    if (bonus_phase == PH_END) {
        if (bonus_timer >= BONUS_END_LEN) {
            if (!is_cgb) OBP1_REG = OBP1_MENU;  // OBP1 as before the round (the level load sets OBP1_PLAY)
            say_bang = 0;                       // its tile goes with the level load
            return 1;
        }
        if (bonus_kind == 1) draw_pour(); else draw_tips();
        return 0;
    }
    return bonus_kind == 1 ? pour_update() : tips_update();
}
