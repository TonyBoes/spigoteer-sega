// The mini-game framework (docs/minigames_bosses.md 2.1; "Mini-game framework as built" in PLAN.md).
//
//   mg_enter(id, mode)  LCD off: hides every sprite, the HUD (score; the timer at columns 16-19), the venue backdrop, the
//                       game's own screen (its enter), the two banner rows (name, instruction), GS_MINI
//   MG_CARD    (the first time a game is played: its full HOW TO PLAY card, src/mg_card.c, waits for A; the game's own screen is set
//              up after it. Seen cards are a bit a game in the save: save.c "MGB1".)
//   MG_INTRO   90 frames: the banner (the short card: the name and one line; A skips it at once)
//   MG_COUNT   60 frames: READY, then GO (A skips it in practice only)
//   MG_PLAY    the game's update; the HUD timer counts down when the game has one (time up: MG_END)
//   MG_END     60 frames: the game's outro (its update still runs)
//   MG_RESULT  the result window (window rows 32-37: panel, name, score, medal word, prompt, panel; the text centred in
//              columns 4-19, the medal's 4x4 icon at columns 0-3 of rows 1-4), drawn 2 rows a frame, then shown; the
//              medal's points go to the score, a gold medal in the story is a life (story_bonus_life). Story: "A CONTINUE" (only after 60 frames shown) -> story_level_done, the next step,
//              whatever the medal (mini-games never block the story). Practice: "A RETRY B MENU" (B: the list,
//              BONUS > MINI GAMES, src/mg_list.c). The medal is recorded for Practice's list (save.c mg_record).
// Poking mg_phase = MG_RESULT ends any game (as the bonus rounds' phase 4). Nothing borrowed is restored here: the next
// level load puts back the patron tiles, the show's OBJ tiles, the palettes and OBP1 (as after a bonus round). Only the
// window's rows (32-34 as win_init left them) and its LYC are put back when the mini-game is left.
#pragma bank 255
#include <gb/gb.h>
#include <gb/cgb.h>
#include <stdint.h>

#include "game.h"
#include "music.h"
#include "mg.h"
#include "bonus.h"
#include "mg_art.h"         // this bank's own art: the medal icon (assets/art/mg_medal.txt)
typedef char mg_icon_tiles_match[(MG_ICON_TILES == 3 * MG_ICON_N * MG_ICON_N) ? 1 : -1];   // static assert (mg.h)

BANKREF_EXTERN(art_tiles)
extern const uint8_t bar_tiles[];
extern uint8_t overlay_on, score_digits[6];
extern uint32_t score;

#define MG_INTRO_LEN    90
#define MG_COUNT_LEN    60
#define MG_GO_AT        30
#define MG_END_LEN      60
#define MG_RESULT_MIN   63      // story: A is taken once the window has shown 60 frames (it takes 3 to draw)
#define RES_ROW         32      // the window's map rows 32..37
#define RES_ROWS         6
#define RES_LYC         (BANNER_WY + 46)   // the window is 48 px tall (as GOAL_LYC for the goal banner's 40)
#define ICON_COL         0      // the medal icon: MG_ICON_N x MG_ICON_N tiles at columns 0-3 of window rows 1-4
#define TEXT_SHIFT      (MG_ICON_N / 2)   // the text: mg_say centres it in columns 0-19, this moves it to the centre
                                // of columns 4-19 (so a line in the window has at most 16 characters)
#define MG_ICON_PAL      4      // CGB BG palette of the icon (written when the result shows, in VBlank)
#define TIMER_COL       16      // HUD: blank, the hourglass, 2 digits (a timer never passes 99 s)
// the games built (mg_game): mg.h's G_*: G_STUB the stub, G_QD Quick Draw, G_BS Battery Sort, G_OU Order Up!, G_MR Milk Run, G_LR Log Roll,
// G_AD Asteroid Delivery, G_TK Taiko Pour, G_MM Marshmallow Drop, G_MK Monkey Business, G_TS T-Shirt Cannon, G_PO the Pour-Off, and the old
// bonus rounds G_B0 the can shake-up, G_B1 Perfect Pour, G_B2 Tip Shower
#define OBP0_BOOT     0xD0      // OBP0 as main_cold.c sets it once at boot (Milk Run's DMG look changes it)

// ---- state (globals => symbols the tests read) ----
uint8_t  mg_id;                 // the id mg_enter was given (MG_*, mg.h)
uint8_t  mg_mode;               // MG_STORY, MG_PRACTICE (| MG_HARD)
uint8_t  mg_phase;              // MG_*
uint8_t  mg_medal;              // MEDAL_* (set when the result shows)
uint8_t  mg_t;                  // frames in this phase
uint8_t  mg_game;               // the game that plays (index into the tables below)
uint16_t mg_timer, mg_score, mg_seed, mg_seed_force;
static uint8_t res_on, res_row, last_secs;
static uint8_t tbuf[4], res_buf[20];
static char res_txt[2][14];

// per game: the banner, the medal thresholds on mg_score (bronze, silver, gold)
static const char *const mg_name[MG_GAMES]  = { "GREEN LIGHT", "QUICK DRAW", "BATTERY SORT", "ORDER UP!",
                                                "MILK RUN", "LOG ROLL", "ASTEROID DELIVERY", "TAIKO POUR", "MARSHMALLOW DROP", "MONKEY BUSINESS", "SHIRT CANNON", "THE POUR OFF",
                                                "CAN SHAKE UP", "PERFECT POUR", "TIP SHOWER" };
static const char *const mg_instr[MG_GAMES] = { "PRESS A ON GREEN", "PRESS A OR B ON DRAW", "LEFT FULL RIGHT DEAD",
                                                "REPEAT THE ORDER", "UP DOWN LANE A TOSS",
                                                "TAP AGAINST THE ROLL", "STEER AND LAND SOFT", "A TOP LANE B BOTTOM",
                                                "MOVE THEN A DROPS", "A SHOO NOT PARROTS", "A POWER THEN A FIRE", "FIRST TO 20 SERVES",
                                                "PICK THE CALM CAN", "FILL TO THE LINE", "CATCH THE TIPS" };
static const uint16_t medal_at[MG_GAMES][3] = { { 1500, 3000, 4000 }, { 0, 0, 0 },   // (Quick Draw: qd_medal)
                                                { 2000, 4000, 6000 }, { 0, 0, 0 },   // (Order Up!: ou_medal)
                                                { 0, 0, 0 }, { 0, 0, 0 }, { 0, 0, 0 }, { 0, 0, 0 },   // (Milk Run: mr_medal, Log Roll: lr_medal, Asteroid Delivery: ad_medal, Taiko Pour: tk_medal)
                                                { MM_MEDAL_BRONZE, MM_MEDAL_SILVER, MM_MEDAL_GOLD },   // Marshmallow Drop (the generic path; mg.h)
                                                { 2500, 5000, 8000 },   // Monkey Business: the score (the spec said 1200 / 2500 / 4000, "tune": PLAN.md)
                                                { 1500, 2100, 2700 },   // T-Shirt Cannon: the score (10 shirts x 300: 5, 7, 9 perfect catches)
                                                { 0, 0, 0 },   // the Pour-Off: no medal
                                                { BONUS_SHAKE_BRONZE, BONUS_SHAKE_SILVER, BONUS_SHAKE_GOLD },   // the bonus rounds: the points they earned (mg.h)
                                                { BONUS_POUR_BRONZE, BONUS_POUR_SILVER, BONUS_POUR_GOLD },
                                                { BONUS_TIPS_BRONZE, BONUS_TIPS_SILVER, BONUS_TIPS_GOLD } };
// each planned game's venue (the id is not the venue: the two lists need not keep one order), and the reverse
static const uint8_t mg_venue[MG_PLANNED] = { 0, 1, 2, 3, 4, 5, 6, 7, 8, 9 };
static const uint8_t venue_mg[MG_PLANNED] = { MG_QUICKDRAW, MG_TSHIRT, MG_LOGROLL, MG_ORDERUP, MG_MARSHMALLOW, MG_BATTERY,
                                              MG_MILKRUN, MG_TAIKO, MG_MONKEY, MG_ASTEROID };
static const uint16_t medal_pts[4] = { 0, 500, 1500, 3000 };
static const char *const medal_word[4] = { "NO MEDAL", "BRONZE ", "SILVER ", "GOLD " };
// CGB: the icon's metal (colours 0-2: highlight, disc, ribbon / numeral) on the HUD band (colour 3, main_cold.c)
#define RGB15(r, g, b) ((uint16_t)((r) | ((g) << 5) | ((b) << 10)))
static const uint16_t medal_pal[4][4] = {
    { RGB15(31, 31, 22), RGB15(31, 23, 4),  RGB15(20, 11, 2),  RGB15(3, 2, 8) },   // gold
    { RGB15(31, 31, 31), RGB15(21, 22, 24), RGB15(10, 11, 14), RGB15(3, 2, 8) },   // silver
    { RGB15(31, 23, 16), RGB15(23, 13, 5),  RGB15(13, 6, 2),   RGB15(3, 2, 8) },   // bronze
    { RGB15(31, 29, 22), RGB15(24, 20, 10), RGB15(29, 20, 4),  RGB15(3, 2, 8) },   // none: the HUD's own (blank cells)
};

// ---- helpers for the games ------------------------------------------------------------------------------------
void mg_points(uint16_t n) BANKED {
    mg_score += n;
    add_score(n);
}

void mg_finish(void) BANKED {
    if (mg_phase != MG_PLAY) return;
    mg_phase = MG_END; mg_t = 0;
}

uint8_t mg_rand(void) BANKED {
    uint16_t s = mg_seed;
    s ^= s << 7;
    s ^= s >> 9;
    s ^= s << 8;
    mg_seed = s;
    return (uint8_t)s;
}

void mg_spigoteer(uint8_t x, uint8_t y, uint8_t frame, uint8_t left, uint8_t oam) BANKED {
    uint8_t base = frame * BARTENDER_TILES_PER_FRAME, xa = x + 8, xb = x + 16, fl = 0;
    OAM_item_t *o = shadow_OAM + oam;
    if (left) { xa = x + 16; xb = x + 8; fl = S_FLIPX; }
    y += 16;
    o->y = y;      o->x = xa; o->tile = base;     o->prop = fl; o++;
    o->y = y;      o->x = xb; o->tile = base + 2; o->prop = fl; o++;
    o->y = y + 16; o->x = xa; o->tile = base + 4; o->prop = fl; o++;
    o->y = y + 16; o->x = xb; o->tile = base + 6; o->prop = fl;
}

void mg_number(char *dst, uint16_t n) BANKED {
    char t[5];
    uint8_t k = 0;
    do { t[k++] = '0' + n % 10; n /= 10; } while (n);
    while (k) *dst++ = t[--k];
    *dst = 0;
}

uint8_t mg_of_venue(uint8_t venue) BANKED {
    return venue < MG_PLANNED ? venue_mg[venue] : MG_STUB;
}

// Milk Run swaps its own LYC handler in for lcd_isr and adds a VBlank one (mr_enter); every other screen has lcd_isr only
static void lcd_normal(void) {
    CRITICAL {
        remove_LCD(mr_lcd_isr);
        remove_LCD(lcd_isr);
        add_LCD(lcd_isr);
        remove_VBL(mr_vbl);
    }
}

// ---- the framework -------------------------------------------------------------------------------------------
static void fill(uint8_t *d, uint8_t v, uint8_t n) { while (n--) *d++ = v; }

static void hud_timer(void) {                    // the hourglass + seconds (2 digits) at HUD columns 17-19 (column 16 stays blank)
    uint8_t s = last_secs, t = 0;
    while (s >= 10) { s -= 10; t++; }
    tbuf[0] = TILE_HUD_BLANK; tbuf[1] = MG_HOURGLASS; tbuf[2] = TILE_GLYPH_0 + t; tbuf[3] = TILE_GLYPH_0 + s;
    if (LCDC_REG & LCDCF_ON) vq_add(0, tbuf, TIMER_COL, HUD_ROW, 4); else vram_put(TIMER_COL, HUD_ROW, tbuf, 4);
}

static uint8_t secs_left(void) { return (uint8_t)((mg_timer + 59) / 60); }

void mg_hourglass_load(uint8_t id) BANKED {
    set_bkg_data(id, 1, hourglass_tile);
}

static void attr_rows(uint8_t y, uint8_t n) {    // LCD off, CGB: rows y.. in the HUD colours
    fill(row_buf, BGPAL_HUD, 20);
    VBK_REG = VBK_BANK_1;
    while (n--) vram_put(0, y++, row_buf, 20);
    VBK_REG = VBK_BANK_0;
}

// The screen's first part, LCD off: everything of the last screen put away, the game chosen (also for the card). Returns the venue.
static uint8_t prelude(uint8_t id, uint8_t mode) {
    DISPLAY_OFF;
    overlay_on = 0; HIDE_WIN; LYC_REG = BANNER_LYC; SCX_REG = 0;
    vq_reset(); hud_dirty = 0; vram_pending = 0; life_lost = 0;
    clear_dirty();
    clear_patrons(); clear_mugs();
    tip_timer = 0; show_timer = 0;
    hide_all_sprites();
    mg_id = id; mg_mode = mode;
    mg_game = id == MG_QUICKDRAW ? G_QD : G_STUB;   // a planned game not built yet plays the stub
    if (id == MG_BATTERY) mg_game = G_BS;
    if (id == MG_ORDERUP) mg_game = G_OU;
    if (id == MG_MILKRUN) mg_game = G_MR;
    if (id == MG_LOGROLL) mg_game = G_LR;
    if (id == MG_ASTEROID) mg_game = G_AD;
    if (id == MG_TAIKO) mg_game = G_TK;
    if (id == MG_MARSHMALLOW) mg_game = G_MM;
    if (id == MG_MONKEY) mg_game = G_MK;
    if (id == MG_TSHIRT) mg_game = G_TS;
    if (id == MG_POUROFF) mg_game = G_PO;         // (the finale: the saloon's venue, no medal, no result window)
    if (id >= MG_SHAKEUP && id < MG_SHAKEUP + MG_BONUS_N) mg_game = G_B0 + id - MG_SHAKEUP;   // (the old bonus rounds: the saloon's backdrop)
    if (!is_cgb) OBP0_REG = OBP0_BOOT;           // (Milk Run changes it: a game that is not it starts from the boot's)
    lcd_normal();                                // (and has the LYC / VBlank handlers it left)
    return id < MG_PLANNED ? mg_venue[id] : 0;   // (the stub, the bonus rounds: the saloon)
}

static void mg_begin(uint8_t id, uint8_t mode);

// Starts game `id`: the first time, its full HOW TO PLAY card (mg_card.c; the venue and the generic tiles are loaded for it, the game's own
// screen waits for A: MG_CARD); after that mg_begin's screen with the short card, the banner.
void mg_enter(uint8_t id, uint8_t mode) BANKED {
    uint8_t v;
    if (card_seen(id)) { mg_begin(id, mode); return; }
    v = prelude(id, mode);
    mg_phase = MG_CARD; mg_t = 0; res_on = 0;
    load_venue(v);
    bkg_data_far(TILE_GENERIC_BASE, GENERIC_TILE_COUNT, bar_tiles, BANK(art_tiles));
    mg_score = 0;                                // (the card page; mg_begin zeroes it again)
    mg_card_draw(mg_game, mg_mode != MG_STORY);
    card_mark(id);
    game_state = GS_MINI;
    DISPLAY_ON;
}

static void mg_begin(uint8_t id, uint8_t mode) {
    uint8_t v = prelude(id, mode), i;
    if (mode == MG_STORY) mg_record(id, MEDAL_NONE);   // STORY or ARCADE reached it: Practice lists it (save.c)
    else {                                       // practice: the score starts from 0 (story: it carries on)
        extra_at = 0;                            // (no extra lives by score here)
        score = 0;
        for (i = 0; i < 6; i++) score_digits[i] = 0;
    }
    mg_seed = mg_seed_force;
    if (!mg_seed) { mg_seed = (uint16_t)next_rand() << 8; mg_seed |= next_rand(); }
    if (!mg_seed) mg_seed = 0xACE1;
    mg_score = 0; mg_medal = MEDAL_NONE; mg_timer = 0; mg_phase = MG_INTRO; mg_t = 0;
    res_on = 0; say_bang = 0;
    // the screen: the venue's tiles and palettes, the HUD glyphs, the medal icon, the HUD, the plain backdrop
    load_venue(v);
    bkg_data_far(TILE_GENERIC_BASE, GENERIC_TILE_COUNT, bar_tiles, BANK(art_tiles));
    set_bkg_data(MG_BG, MG_ICON_TILES, medal_tiles);
    set_bkg_data(MG_HOURGLASS, 1, hourglass_tile);
    draw_hud();
    venue_backdrop(1, MG_COUNTER_ROW);
    if (is_cgb) {
        attr_rows(HUD_ROW, 1);
        attr_rows(MG_TEXT_A, 2);
        attr_rows(RES_ROW, RES_ROWS);            // the result window; its icon's cells in the medal palette
        fill(row_buf, MG_ICON_PAL, MG_ICON_N);
        VBK_REG = VBK_BANK_1;
        for (i = 1; i <= MG_ICON_N; i++) vram_put(ICON_COL, RES_ROW + i, row_buf, MG_ICON_N);
        VBK_REG = VBK_BANK_0;
    }
    fill(tbuf, TILE_HUD_BLANK, 4);
    vram_put(TIMER_COL, HUD_ROW, tbuf, 4);       // no level number on a mini-game's HUD (a game may draw there)
    switch (mg_game) {                           // the game's own screen (it may set mg_timer)
    case G_QD: qd_enter(); break;
    case G_BS: bs_enter(); break;
    case G_OU: ou_enter(); break;
    case G_MR: mr_enter(); break;
    case G_LR: lr_enter(); break;
    case G_AD: ad_enter(); break;
    case G_TK: tk_enter(); break;
    case G_MM: mm_enter(); break;
    case G_MK: mk_enter(); break;
    case G_TS: ts_enter(); break;
    case G_PO: po_enter(); break;
    case G_B0: case G_B1: case G_B2: bonus_practice(mg_game - G_B0); break;   // (src/bonus.c: its own scene and jingle, on this HUD and backdrop)
    default: stub_enter(); break;
    }
    i = *(uint8_t *)(0x9800 + HUD_ROW * 32 + 8);   // (LCD off) a game whose own HUD took the lives digit's column (8) takes the head too
    if (i != lives_tiles[1]) { i = TILE_HUD_BLANK; vram_put(7, HUD_ROW, &i, 1); }
    if (mg_timer) { last_secs = secs_left(); hud_timer(); }
    mg_say(MG_TEXT_A, mg_name[mg_game]);         // (LCD off: written at once)
    mg_say(MG_TEXT_B, mg_instr[mg_game]);
    if (mg_game < G_B0) music_play(TUNE_VENUE0 + v);   // (a bonus round plays the bonus jingle: bonus_practice)
    game_state = GS_MINI;
    DISPLAY_ON;
}

static void game_update(uint8_t pressed) {
    switch (mg_game) {
    case G_QD: qd_update(pressed); break;
    case G_BS: bs_update(pressed); break;
    case G_OU: ou_update(pressed); break;
    case G_MR: mr_update(pressed); break;
    case G_LR: lr_update(pressed); break;
    case G_AD: ad_update(pressed); break;
    case G_TK: tk_update(pressed); break;
    case G_MM: mm_update(pressed); break;
    case G_MK: mk_update(pressed); break;
    case G_TS: ts_update(pressed); break;
    case G_PO: po_update(pressed); break;
    case G_B0: case G_B1: case G_B2:             // the old bonus rounds: 1 when the round is over (their own end banner has run)
        if (bonus_update(pressed)) { mg_phase = MG_RESULT; res_on = 0; }
        break;
    default: stub_update(pressed); break;
    }
}

// the result's first frame (also when a test poked mg_phase = MG_RESULT): the medal, its points, the window's text
static void result_begin(void) {
    uint8_t m = MEDAL_NONE;
    const uint16_t *at = medal_at[mg_game];
    char *d;
    const char *w;
    if (mg_game >= G_B0) mg_score = (uint16_t)score;   // (a practice round starts the score from 0: the points it earned)
    if (mg_game == G_QD) m = qd_medal();
    else if (mg_game == G_OU) m = ou_medal();
    else if (mg_game == G_MR) m = mr_medal();
    else if (mg_game == G_LR) m = lr_medal();
    else if (mg_game == G_AD) m = ad_medal();
    else if (mg_game == G_TK) m = tk_medal();
    else while (m < 3 && mg_score >= at[m]) m++;
    mg_medal = m;
    mg_record(mg_id, m);                         // the best medal (Practice's list; any mode)
    if (is_cgb) set_bkg_palette(MG_ICON_PAL, 1, medal_pal[MEDAL_GOLD - m]);   // (the top of the frame: VBlank)
    if (m) {
        add_score(medal_pts[m]);
        SFX(SFX_COIN);
        if (m == MEDAL_GOLD && mg_mode == MG_STORY) story_bonus_life();       // owner: +1 life for the venue
    }
    d = res_txt[0];                              // "SCORE n"
    for (w = "SCORE "; *w; ) *d++ = *w++;
    mg_number(d, mg_score);
    d = res_txt[1];                              // "GOLD 3000" / "NO MEDAL"
    for (w = medal_word[m]; *w; ) *d++ = *w++;
    *d = 0;
    if (m) mg_number(d, medal_pts[m]);
    for (m = 0; m < 40; m++) if (shadow_OAM[m].y > BANNER_WY && shadow_OAM[m].y < BANNER_WY + 64) shadow_OAM[m].y = 0;
    res_on = 1; res_row = 0; mg_t = 0;
}

static void result_row(uint8_t r) {             // queue window row r (0..5)
    uint8_t *b, t, k;
    const char *s;
    switch (r) {
    case 0: case 5:
        fill(res_buf, r ? TILE_PANEL_BOT : TILE_PANEL_TOP, 20);
        vq_add(0, res_buf, 0, RES_ROW + r, 20);
        return;
    case 1: s = mg_game == G_AD ? "ASTEROIDS" : mg_name[mg_game]; break;   // (the window holds 16 letters: "ASTEROID DELIVERY" is 17)
    case 4: s = mg_mode == MG_STORY ? "A CONTINUE" : "A RETRY B MENU"; break;
    default: s = res_txt[r - 2]; break;          // rows 2, 3: the score, the medal
    }
    b = mg_say(RES_ROW + r, s);                  // queued: the row is copied at VBlank, so it may still change here
    for (k = 19; k >= TEXT_SHIFT; k--) b[k] = b[k - TEXT_SHIFT];
    fill(b, TILE_HUD_BLANK, TEXT_SHIFT);
    if (!mg_medal) return;                       // the icon's row of tiles at its left
    t = MG_BG + (MEDAL_GOLD - mg_medal) * (MG_ICON_N * MG_ICON_N) + (r - 1) * MG_ICON_N;
    for (k = 0; k < MG_ICON_N; k++) b[ICON_COL + k] = t + k;
}

// the window's rows as win_init left them, the banner's LYC; LCD off (the next screen turns it on)
static void mg_leave(void) {
    if (mg_game == G_TK) tk_leave();
    DISPLAY_OFF;
    overlay_on = 0; HIDE_WIN; LYC_REG = BANNER_LYC;
    SCX_REG = 0;                                 // (Milk Run's street)
    if (!is_cgb) OBP0_REG = OBP0_BOOT;           // (Milk Run's rider)
    lcd_normal();
    vq_reset();
    hide_all_sprites();
    say_bang = 0;                                // (a game's own '!' tile goes with the level load)
    fill(row_buf, TILE_PANEL_TOP, 20); vram_put(0, RES_ROW, row_buf, 20);
    fill(row_buf, TILE_HUD_BLANK, 20); vram_put(0, RES_ROW + 1, row_buf, 20);
    fill(row_buf, TILE_PANEL_BOT, 20); vram_put(0, RES_ROW + 2, row_buf, 20);
    if (is_cgb) attr_rows(RES_ROW, RES_ROWS);
}

// the pause menu's QUIT TO MENU (src/pause.c): the same leave as a finished game's
void mg_abort(void) BANKED { mg_leave(); }

static uint8_t result_frame(uint8_t pressed) {
    if (mg_game == G_PO) {                       // the Pour-Off has no result window: won -> FINALE_B, lost -> the Pour-Off again
        if (MG->po.res == PR_WIN) { mg_leave(); story_pouroff_done(); }
        else mg_enter(mg_id, mg_mode);
        return 1;
    }
    if (!res_on) result_begin();
    if (res_row < RES_ROWS) {
        result_row(res_row++);
        result_row(res_row++);
        if (res_row == RES_ROWS) {
            overlay_on = 1;
            if (mg_game != G_MR) LYC_REG = RES_LYC;      // (Milk Run's lcd_isr walks LYC itself and picks RES_LYC)
        }
        return 0;
    }
    if (mg_mode == MG_STORY) {
        if (!(pressed & J_A) || mg_t < MG_RESULT_MIN) return 0;
        mg_leave();
        story_level_done();                      // the next step (the Last call), or the POST scene
        return 1;
    }
    if (pressed & J_A) { mg_enter(mg_id, mg_mode); return 1; }
    if (pressed & J_B) { mg_leave(); mg_list_enter(); return 1; }   // back to BONUS > MINI GAMES
    return 0;
}

static uint8_t mg_frame(uint8_t pressed);

// One mini-game frame, with the VBlank OAM DMA off while it runs (as main.c does for GS_PLAYING): every game clears and
// rewrites its sprite entries here, and a frame that runs past the start of VBlank would put a half-written list on the
// screen (the flicker of Log Roll's late frames). The DMA is off only inside this call: the last complete list stays up.
uint8_t mg_update(uint8_t pressed) BANKED {
    uint8_t left;
    if ((pressed & J_START) && mg_phase <= MG_PLAY) { pause_open(); return 0; }   // the pause menu (src/pause.c; not over the result)
    DISABLE_OAM_DMA;
    left = mg_frame(pressed);
    ENABLE_OAM_DMA;
    return left;
}

static uint8_t mg_frame(uint8_t pressed) {
    uint8_t s;
    if (mg_t < 255) mg_t++;
    switch (mg_phase) {
    case MG_CARD:                                // the full card: A starts the game (its screen is built now, the banner after it)
        s = mg_mode != MG_STORY;                 // from BONUS > MINI GAMES: B goes back to the list (as the pause menu QUIT), no medal
        if ((pressed & J_B) && s) { mg_leave(); mg_list_enter(); return 1; }
        if (pressed & (J_A | J_B)) {             // A (B too where there is no list) turns the page, or starts the game after the last
            if ((uint8_t)mg_score + 1 < mg_card_pages(mg_game)) { mg_score++; mg_card_page(mg_game, (uint8_t)mg_score, s); mg_t = 0; }
            else mg_begin(mg_id, mg_mode);
            break;
        }
        if (!(mg_t & 31)) mg_card_prompt(mg_game, (uint8_t)mg_score, s, !(mg_t & 32));   // (blinks)
        break;
    case MG_INTRO:
        if (mg_t >= MG_INTRO_LEN || (pressed & J_A)) {   // the short card: A skips it at once
            if (mg_game >= G_B0) {               // a bonus round has no count-in: its own banner and phases follow
                mg_phase = MG_PLAY; mg_t = 0;
                if (mg_game == G_B0) { mg_say(MG_TEXT_A, ""); mg_say(MG_TEXT_B, ""); }
                break;
            }
            mg_phase = MG_COUNT; mg_t = 0;
            mg_say(MG_TEXT_A, "READY"); mg_say(MG_TEXT_B, "");
        }
        break;
    case MG_COUNT:
        if (mg_t == MG_GO_AT) mg_say(MG_TEXT_A, "GO");
        if (mg_t >= MG_COUNT_LEN || ((pressed & J_A) && mg_mode != MG_STORY)) {
            mg_phase = MG_PLAY; mg_t = 0;
            mg_say(MG_TEXT_A, ""); mg_say(MG_TEXT_B, "");
        }
        break;
    case MG_PLAY:
        game_update(pressed);
        if (mg_timer && mg_phase == MG_PLAY) {
            if (--mg_timer == 0) { mg_say(MG_TEXT_A, "TIME UP"); mg_finish(); }
            if ((s = secs_left()) != last_secs) { last_secs = s; hud_timer(); }
        }
        break;
    case MG_END:
        game_update(pressed);
        if (mg_t >= MG_END_LEN) { mg_phase = MG_RESULT; res_on = 0; }
        break;
    default:
        return result_frame(pressed);
    }
    return 0;
}
