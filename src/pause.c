// The pause menu (owner 2026-10-14), every mode: START in a level (main.c GS_PLAYING) or in a mini-game's INTRO / COUNT / PLAY
// (mg.c mg_update) opens it; game_state is GS_PAUSED while it shows, so nothing moves and main.c does not tick the music (PAUSE_NR51 set).
//
//   PAUSE                        PAUSE                        ARE YOU SURE?
//   > RESUME                     > RESUME                       YES
//     QUIT TO MENU                 HOW TO PLAY                > NO
//                                  QUIT TO MENU
//
// (the middle one in a mini-game: the HOW TO PLAY card, src/mg_card.c, over the whole screen; A turns its pages, A on the last or B comes
// back to the menu. pause_card() is the hook that says which card the context has, NO_CARD for none: bar levels and bosses today.)
// Up / Down choose, A takes it, START or B resume (in the question: back to the menu). QUIT TO MENU asks first (NO is the
// cursor). YES ends the run through the same exits as finishing it:
//   - a mini-game: mg.c's own leave (tk_leave, OBP0, the LCD handlers, the sprites), then BONUS > MINI GAMES (practice, no
//     medal recorded), or as the story / ARCADE run it is part of;
//   - STORY (shifts, boss fights, the Pour-Off): the title. Nothing is saved here: the progress is what story.c saved at the
//     start of the venue / shift (story_save in story_level_done), so CONTINUE starts from that;
//   - ARCADE, CLASSIC (and the LEVEL harness): the run ends as a game over does: the score into the mode's top 5, the
//     initials when it made it (scores_after_game), else the title;
//   - BOSS RUSH: the BOSS RUSH menu, no time recorded.
//
// The window is the result window's size (6 rows, window map rows 0-5 = map rows 32-37, LYC at BANNER_WY + 46: Milk Run's
// handler picks it too, main.c mr_lcd_isr), written straight to the window map (GBDK's set_win_tiles waits for VRAM).
// The HUD glyph set has no '?' and no arrow: two rarely used letters' tiles (J, Z: no text on a playing screen has one)
// take them while paused and are put back from the shared tiles when the pause ends.
// State, no WRAM of its own: state_timer (idle while playing or paused) holds the menu: bits 0-1 the cursor (0 RESUME, 1 HOW TO PLAY,
// 2 QUIT; in the question 0 YES, 1 NO), bit 2 the question, bit 3 the card is showing, bits 4-5 its page, bit 6 the sprites were on
// (the card switches them off), bit 7 a mini-game paused. The sound's NR51 is kept in HRAM 0xFFF0 (game.h PAUSE_NR51; the linker uses 0xFF80-0xFF92 only); it is also the "menu is open" flag.
#pragma bank 255
#include <gb/gb.h>
#include <gb/cgb.h>
#include <stdint.h>

#include "game.h"
#include "music.h"
#include "mg.h"
#include "boss.h"

BANKREF_EXTERN(art_tiles)
extern const uint8_t bar_tiles[];
extern uint8_t state_timer, overlay_on, story_phase, new_rank;
extern uint32_t score;

#define PAUSE_MINI   0x80
#define PAUSE_OBJ    0x40                   // the sprites were on when the card hid them
#define PAUSE_PAGE   0x30                   // (bits 4-5: the card page, step 0x10)
#define PAUSE_CARD   8                      // the card shows
#define PAUSE_ASK    4                      // the question
#define NO_CARD      255
#define WIN_ROWS     6
#define WIN_LYC      (BANNER_WY + 46)       // the window is 48 px tall (as mg.c RES_LYC)
#define COL_ITEM     3                      // the arrow's column; the item's text follows at COL_ITEM + 2

static const uint8_t qmark_tile[16] = { 0xFF,0xFF, 0xC3,0xC3, 0xBD,0xBD, 0xFD,0xFD, 0xFB,0xFB, 0xF7,0xF7, 0xFF,0xFF, 0xF7,0xF7 };
static const uint8_t arrow_tile[16] = { 0xFF,0xFF, 0xDF,0xDF, 0xCF,0xCF, 0xC7,0xC7, 0xCF,0xCF, 0xDF,0xDF, 0xFF,0xFF, 0xFF,0xFF };

static uint8_t gl(char c) {
    return c == '?' ? TILE_GLYPH_J : c == '>' ? TILE_GLYPH_Z : glyph_for(c);
}

// window row r: blank, `mark` at COL_ITEM and s after it (col 255: s centred, no mark)
static void line(uint8_t r, uint8_t col, char mark, const char *s) {
    uint8_t b[20], i = 0, n = 0;
    const char *e = s;
    while (e[n]) n++;
    for (i = 0; i < 20; i++) b[i] = TILE_HUD_BLANK;
    if (col == 255) col = (uint8_t)(20 - n) >> 1;
    else b[COL_ITEM] = gl(mark);
    for (i = 0; i < n; i++) b[col + i] = gl(s[i]);
    set_win_tiles(0, r, 20, 1, b);
}

static void fill_row(uint8_t r, uint8_t t) {
    uint8_t b[20], i;
    for (i = 0; i < 20; i++) b[i] = t;
    set_win_tiles(0, r, 20, 1, b);
}

// the HOW TO PLAY card of this context (mg.h's G_* id), or NO_CARD. A later batch gives bosses their hint pages here.
static uint8_t pause_card(uint8_t s) {
    return (s & PAUSE_MINI) ? mg_game : NO_CARD;
}

// the changing rows (1-4) for the menu state s
static void draw(uint8_t s) {
    uint8_t c = s & 3;
    line(1, 255, ' ', (s & PAUSE_ASK) ? "ARE YOU SURE?" : "PAUSE");
    if (s & PAUSE_ASK) {
        fill_row(2, TILE_HUD_BLANK);
        line(3, COL_ITEM + 2, c ? ' ' : '>', "YES");
        line(4, COL_ITEM + 2, c ? '>' : ' ', "NO");
    } else if (pause_card(s) != NO_CARD) {       // three items on rows 2-4
        line(2, COL_ITEM + 2, c == 0 ? '>' : ' ', "RESUME");
        line(3, COL_ITEM + 2, c == 1 ? '>' : ' ', "HOW TO PLAY");
        line(4, COL_ITEM + 2, c == 2 ? '>' : ' ', "QUIT TO MENU");
    } else {                                     // two, on rows 3-4
        fill_row(2, TILE_HUD_BLANK);
        line(3, COL_ITEM + 2, c == 0 ? '>' : ' ', "RESUME");
        line(4, COL_ITEM + 2, c == 2 ? '>' : ' ', "QUIT TO MENU");
    }
}

static void glyphs_back(void) {
    bkg_data_far(TILE_GLYPH_J, TILE_GLYPH_Z - TILE_GLYPH_J + 1, bar_tiles + (uint16_t)(TILE_GLYPH_J - TILE_GENERIC_BASE) * 16, BANK(art_tiles));
}

static void card_open(void) {
    uint8_t s = state_timer;
    HIDE_WIN;                                    // (hidden while the card is drawn, a few frames; main.c's update shows it again)
    glyphs_back();                               // (the card's text may use J and Z)
    if (LCDC_REG & LCDCF_OBJON) s |= PAUSE_OBJ;
    state_timer = s | PAUSE_CARD;
    HIDE_SPRITES;
    WY_REG = 0;                                  // the window over the whole screen: no LYC end
    mg_card_win_open(pause_card(s));
    if (!(mg_id == MG_MILKRUN)) LYC_REG = 255;   // (Milk Run's handler: main.c mr_lcd_isr takes PAUSE_CARD into account)
}

static void card_close(void) {
    uint8_t s = state_timer;
    HIDE_WIN;
    mg_card_win_close();
    WY_REG = BANNER_WY;
    if (!(mg_id == MG_MILKRUN)) LYC_REG = WIN_LYC;
    if (s & PAUSE_OBJ) SHOW_SPRITES;
    set_bkg_data(TILE_GLYPH_J, 1, qmark_tile);
    set_bkg_data(TILE_GLYPH_Z, 1, arrow_tile);
    fill_row(0, TILE_PANEL_TOP);
    fill_row(5, TILE_PANEL_BOT);
    state_timer = s & (PAUSE_MINI | 3);
    draw(state_timer);
}

void pause_open(void) BANKED {
    uint8_t i, mini = game_state == GS_MINI;
    state_timer = mini ? PAUSE_MINI : 0;
    game_state = GS_PAUSED;
    i = NR51_REG;                                // the music is not ticked meanwhile (main.c: while NR51 is 0); its channels
    PAUSE_NR51 = i ? i : 0xFF;                   // go quiet and come back
    NR51_REG = 0;
    for (i = 0; i < 40; i++)                     // what the window covers (as mg.c's result window)
        if (shadow_OAM[i].y > BANNER_WY && shadow_OAM[i].y < BANNER_WY + 64) shadow_OAM[i].y = 0;
    oam_touched();
    set_bkg_data(TILE_GLYPH_J, 1, qmark_tile);
    set_bkg_data(TILE_GLYPH_Z, 1, arrow_tile);
    fill_row(0, TILE_PANEL_TOP);
    fill_row(5, TILE_PANEL_BOT);
    draw(state_timer);
    if (is_cgb) {                                // the window's rows in the HUD palette
        uint8_t b[20];
        for (i = 0; i < 20; i++) b[i] = BGPAL_HUD;
        VBK_REG = VBK_BANK_1;
        for (i = 0; i < WIN_ROWS; i++) set_win_tiles(0, i, 20, 1, b);
        VBK_REG = VBK_BANK_0;
    }
    if (!(mini && mg_id == MG_MILKRUN)) LYC_REG = WIN_LYC;   // (Milk Run's handler walks LYC itself)
    overlay_on = 1;
}

// the sound, the two letters' tiles and the banner window (panel, a blank text row, panel; its LYC) as they were
static void put_back(void) {
    NR51_REG = PAUSE_NR51; PAUSE_NR51 = 0;
    glyphs_back();
    fill_row(0, TILE_PANEL_TOP);                 // (win_init's banner)
    fill_row(1, TILE_HUD_BLANK);
    fill_row(2, TILE_PANEL_BOT);
    if (!((state_timer & PAUSE_MINI) && mg_id == MG_MILKRUN)) LYC_REG = BANNER_LYC;
    overlay_on = 0; HIDE_WIN;
}

// RESUME (and the debug box, main.c's combo): everything as it was, back to the game
void pause_close(void) BANKED {
    uint8_t mini = state_timer & PAUSE_MINI;
    put_back();
    game_state = mini ? GS_MINI : GS_PLAYING;
}

// YES: the run (or the mini-game) ends
static void quit(void) {
    uint8_t aaa[3];
    put_back();                                  // (before the leave: Taiko's tk_leave sets its own NR51)
    if (state_timer & PAUSE_MINI) {
        mg_abort();                              // mg.c's normal leave: LCD off, OBP0, handlers, sprites, Taiko's mask
        if (mg_mode != MG_STORY) { mg_list_enter(); return; }   // BONUS > MINI GAMES: back to the list, no medal
    } else if (play_mode == MODE_RUSH) {
        rush_quit();                             // the BOSS RUSH menu, no time recorded
        return;
    }
    boss_set(BOSS_NONE);
    story_phase = 0;                             // (SP_OFF)
    if (story_on && !story_arc) {                // STORY: the title; CONTINUE starts from the last save
        story_on = 0;
        title_enter();
        return;
    }
    story_on = 0; story_arc = 0;                 // ARCADE / CLASSIC / the harness: as enter_game_over, then the title
    score_tbl = play_mode == MODE_LEVEL ? MODE_ARCADE : play_mode;
    aaa[0] = aaa[1] = aaa[2] = 'A';
    new_rank = top_insert(score, aaa);
    if (new_rank < TOP_N) { hi_save(); scores_after_game(); }   // the initials, then the table, then the title
    else title_enter();
}

// every GS_PAUSED frame. 1: the screen changed (the run is over)
uint8_t pause_update(uint8_t pressed) BANKED {
    uint8_t s = state_timer, c = s & 3, m = s & PAUSE_MINI;
    if (!PAUSE_NR51) return 0;                   // (no menu open: a test poked game_state = GS_PAUSED for a frame)
    if (s & PAUSE_CARD) {                        // the HOW TO PLAY card: A turns the page (on the last it closes), B and START close it
        if ((pressed & J_A) && ((s & PAUSE_PAGE) >> 4) + 1 < mg_card_pages(pause_card(s))) {
            state_timer = s + 0x10;
            mg_card_page(pause_card(s), (state_timer & PAUSE_PAGE) >> 4, 2);
        } else if (pressed & (J_A | J_B | J_START)) card_close();
        return 0;
    }
    if (pressed & (J_UP | J_DOWN)) {
        if (s & PAUSE_ASK) c ^= 1;
        else if (pressed & J_DOWN) { c = c == 2 ? 0 : c + 1; if (c == 1 && pause_card(s) == NO_CARD) c = 2; }
        else { c = c == 0 ? 2 : c - 1; if (c == 1 && pause_card(s) == NO_CARD) c = 0; }
        state_timer = (s & ~3) | c;
        draw(state_timer);
    } else if (pressed & (J_START | J_B)) {
        if (s & PAUSE_ASK) { state_timer = m | 2; draw(state_timer); }          // back to the menu, the cursor on QUIT
        else pause_close();
    } else if (pressed & J_A) {
        if (!(s & PAUSE_ASK)) {
            if (c == 0) pause_close();
            else if (c == 1) card_open();
            else { state_timer = m | PAUSE_ASK | 1; draw(state_timer); }        // the question, the cursor on NO
        } else if (c == 0) {                     // YES
            quit();
            return 1;
        } else { state_timer = m | 2; draw(state_timer); }                      // NO
    }
    return 0;
}
