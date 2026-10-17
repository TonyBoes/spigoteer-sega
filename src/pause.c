// The pause menu (owner 2026-10-14), every mode: START in a level (main.c GS_PLAYING) or in a mini-game's INTRO / COUNT / PLAY
// (mg.c mg_update) opens it; game_state is GS_PAUSED while it shows, so nothing moves. The music goes on, down to the bass and the
// drums (channels 3 and 4: NR51 MENU_MIX) and the effects held silent; where the game is clocked by the tune (Taiko Pour, the Sumo's
// fight: music_frames) it stands still and silent (NR51 0) and main.c does not tick it.
//
//   a level (6-row window)      a mini-game (5 rows)         the question: a level (6 rows) | a mini-game (5)
//   panel                        panel                        panel                           panel
//   (blank)                      > RESUME                     ARE YOU SURE?                   ARE YOU SURE?
//   > RESUME                       HOW TO PLAY                (blank)                           YES
//     QUIT TO MENU                 QUIT TO MENU                 YES                           > NO
//   (blank)                      panel                      > NO                            panel
//   panel                                                   panel
//
// Each block is centred between the panels: two items in the level's 4 text rows (one blank row above and below), the question
// and its two answers (with a blank row between) filling them; three items, or the question without the blank row, in the
// mini-game's 3 text rows (the window ends one row sooner: LYC WY + 38 instead of + 46, as the goal banner).
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
// No flicker: the window rows are only rewritten in VBlank (the window is on screen from line BANNER_WY on, and a write through
// set_win_tiles, one byte per HBlank, took the beam past them): a cursor move changes the two mark tiles, anything else builds its
// rows in a buffer and copies them at the start of the next VBlank (the first lines are the 10 where VRAM is free), with the new LYC.
#pragma bank 255
#include <gb/gb.h>
#include <gb/cgb.h>
#include <stdint.h>
#include <string.h>

#include "game.h"
#include "music.h"
#include "mg.h"
#include "boss.h"

BANKREF_EXTERN(art_tiles)
extern const uint8_t bar_tiles[];
extern uint8_t state_timer, overlay_on, story_phase, new_rank, story_chapter, save_lock;
extern uint32_t score;

#ifndef CARD_FADE
#define CARD_FADE    1                      // the card opens and closes through the white fade of src/trans.c (owner 2026-10-17: try it); -DCARD_FADE=0: the LCD-off cut
#endif
#define PAUSE_MINI   0x80
#define PAUSE_OBJ    0x40                   // the sprites were on when the card hid them
#define PAUSE_PAGE   0x30                   // (bits 4-5: the card page, step 0x10)
#define PAUSE_CARD   8                      // the card shows
#define PAUSE_ASK    4                      // the question
#define NO_CARD      255
#define WIN_ROWS     6
#define WIN_LYC(s)   (BANNER_WY + (((s) & PAUSE_MINI) ? 38 : 46))   // 40 px (5 rows) or 48 (6: as mg.c RES_LYC); main.c mr_lcd_isr's twin
#define MENU_MIX     0xCC                   // NR51 while paused: channels 3 (the bass) and 4 (the drums) on both sides; music.c's music_tick
                                            // drops it to 0x44 while an effect still owns channel 4
#define SUMO_VENUE   7                      // boss_id of the Sumo (teahouse): his beat is counted on music_frames
#define COL_ITEM     3                      // the arrow's column; the item's text follows at COL_ITEM + 2

static const uint8_t qmark_tile[16] = { 0xFF,0xFF, 0xC3,0xC3, 0xBD,0xBD, 0xFD,0xFD, 0xFB,0xFB, 0xF7,0xF7, 0xFF,0xFF, 0xF7,0xF7 };
static const uint8_t arrow_tile[16] = { 0xFF,0xFF, 0xDF,0xDF, 0xCF,0xCF, 0xC7,0xC7, 0xCF,0xCF, 0xDF,0xDF, 0xFF,0xFF, 0xFF,0xFF };

static uint8_t gl(char c) {
    return c == '?' ? TILE_GLYPH_J : c == '>' ? TILE_GLYPH_Z : glyph_for(c);
}

// The menu's words as tiles (a length, then the tiles): a row costs a copy, not a banked glyph_for call a letter (~400 cycles each, ~10k
// cycles a rewrite: it ran the frame so long that the tune's tick came 0.26 frame late after QUIT / NO).
#define G(c) TILE_GLYPH_##c
#define SP   TILE_HUD_BLANK
static const uint8_t w_resume[] = { 6, G(R), G(E), G(S), G(U), G(M), G(E) };
static const uint8_t w_how[]    = { 11, G(H), G(O), G(W), SP, G(T), G(O), SP, G(P), G(L), G(A), G(Y) };
static const uint8_t w_quit[]   = { 12, G(Q), G(U), G(I), G(T), SP, G(T), G(O), SP, G(M), G(E), G(N), G(U) };
static const uint8_t w_yes[]    = { 3, G(Y), G(E), G(S) };
static const uint8_t w_no[]     = { 2, G(N), G(O) };
static const uint8_t w_sure[]   = { 13, G(A), G(R), G(E), SP, G(Y), G(O), G(U), SP, G(S), G(U), G(R), G(E), TILE_GLYPH_J };   // (J: the '?' while paused)

// the tiles t (length first) at COL_ITEM + 2 after `mark` at COL_ITEM, or centred (col 255, no mark), into the blank row buffer b (20 tiles)
static void put(uint8_t *b, uint8_t col, uint8_t mark, const uint8_t *t) {
    uint8_t i = 0, n = *t++;
    if (col == 255) col = (uint8_t)(20 - n) >> 1;
    else b[COL_ITEM] = mark;
    for (; i < n; i++) b[col + i] = t[i];
}

static void fill_row(uint8_t r, uint8_t t) {
    uint8_t b[20], i;
    for (i = 0; i < 20; i++) b[i] = t;
    set_win_tiles(0, r, 20, 1, b);
    music_pump();                                // (a row takes up to half a frame: it waits for the VRAM)
}

// the HOW TO PLAY card of this context (mg.h's G_* id, or MG_BOSS_CARD + the boss's id), or NO_CARD (a level with no boss).
static uint8_t pause_card(uint8_t s) {
    return (s & PAUSE_MINI) ? mg_game : boss_on ? MG_BOSS_CARD + boss_id : NO_CARD;   // (a boss fight: his hint page, mg_card.c)
}

static const uint8_t *const names[] = { w_resume, w_how, w_quit, w_yes, w_no };

// where the items are in menu state s: the first item's window row, and the item the cursor is on
// (a boss fight lists three items like a mini-game, on rows 1-3 of its 6-row window; the other levels two, on rows 2-3)
#define three(s) (((s) & PAUSE_MINI) || (boss_on && !((s) & PAUSE_ASK)))
static uint8_t first_row(uint8_t s) { return (three(s) ? 1 : 2) + ((s & PAUSE_ASK) != 0); }
static uint8_t cursor_item(uint8_t s) { return (s & PAUSE_ASK) || three(s) ? s & 3 : (s & 3) >> 1; }

// window rows 1-5 for menu state s into b (100 tiles). Level: a 6-row window, the bottom panel on row 5; two items on rows 2-3,
// the question on row 1 and its answers on 3-4 (a blank row between). Mini-game: a 5-row window, the panel on row 4; three items
// on rows 1-3, the question on row 1 and its answers on 2-3.
static void build(uint8_t s, uint8_t *b) {
    uint8_t i, n = three(s) && !(s & PAUSE_ASK) ? 3 : 2, sel = cursor_item(s), r = first_row(s);
    uint8_t base = (s & PAUSE_ASK) ? 3 : 0, step = (s & PAUSE_ASK) || three(s) ? 1 : 2;
    uint8_t pr = (s & PAUSE_MINI) ? 4 : 5;
    uint8_t *p = b, j;
    for (j = 0; j < 4; j++) {                    // (a pump every 25 tiles: the fills and the text below take most of a frame, and the tune's tick falls
        for (i = 0; i < 25; i++) *p++ = TILE_HUD_BLANK;   // due about line 9: with the first pump at line 48 it came 0.26 frame late after QUIT / NO)
        music_pump();
    }
    for (i = 0; i < 20; i++) b[(pr - 1) * 20 + i] = TILE_PANEL_BOT;
    music_pump();
    if (s & PAUSE_ASK) put(b, 255, 0, w_sure);
    for (i = 0; i < n; i++) put(b + (r - 1 + i) * 20, COL_ITEM + 2, i == sel ? TILE_GLYPH_Z : TILE_HUD_BLANK, names[base + i * step]);
}

// The window is on screen from line BANNER_WY to its LYC (WY + 38 or 46), and a write through set_win_tiles waits for VRAM (a byte per
// HBlank when the beam is drawing). So the window's rows are only written once the beam is below it (LY 111 on) or above (to LY 8), and
// a few dozen bytes done by LY ~40 of the next frame are in before the window is drawn again: nothing half-drawn is ever seen. The
// update runs from VBlank on, so there is normally no wait here.
static void quiet_start(void) {
    if (LCDC_REG & LCDCF_ON) while (LY_REG >= 8 && LY_REG < BANNER_WY + 47) music_pump();     // (the tune ticks while the beam crosses the window)
}

// menu state s on the window (rows 1-5 and the LYC that ends it); state_timer is s from then on.
// hidden: the window is not showing (open, the card closed): all five rows at once. Else only the text columns of the text rows
// (the panel rows do not change).
static void apply(uint8_t s, uint8_t hidden) {
    uint8_t b[100], i;
    build(s, b);
    if (hidden) {
        for (i = 0; i < 5; i++) { set_win_tiles(0, i + 1, 20, 1, b + i * 20); music_pump(); }   // (hidden: each row waits for the VRAM, a fifth of a frame)
    } else {
        quiet_start();
        for (i = 0; i < ((s & PAUSE_MINI) ? 3 : 4); i++) set_win_tiles(COL_ITEM, i + 1, 14, 1, b + i * 20 + COL_ITEM);
        if (overlay_on) {                        // (lcd_isr hid it at the menu's last line; shown from VBlank on or while the beam is above its top: below that it would start under the beam)
            while (LY_REG >= BANNER_WY && LY_REG < 144) music_pump();
            SHOW_WIN;
        }
    }
    state_timer = s;
    if (!((s & PAUSE_MINI) && mg_id == MG_MILKRUN)) LYC_REG = WIN_LYC(s);   // (Milk Run's handler: main.c mr_lcd_isr)
}

// the cursor moves within the menu (or YES / NO): only the two mark tiles change
static void move_mark(uint8_t from, uint8_t to) {
    uint8_t a = gl(' '), z = gl('>'), r = first_row(to);
    quiet_start();
    set_win_tiles(COL_ITEM, r + cursor_item(from), 1, 1, &a);
    set_win_tiles(COL_ITEM, r + cursor_item(to), 1, 1, &z);
    state_timer = to;
}

static void glyphs_back(void) {
    bkg_data_far(TILE_GLYPH_J, TILE_GLYPH_Z - TILE_GLYPH_J + 1, bar_tiles + (uint16_t)(TILE_GLYPH_J - TILE_GENERIC_BASE) * 16, BANK(art_tiles));
}

// The card and the menu swap with the LCD off (owner 2026-10-15: the paused game showed for several frames while the card drew): the
// menu stays up until the LCD goes off (lcd_off_p waits for the next VBlank, the tune pumped), the new screen is built in one pass
// with the music pumped, and the LCD comes on with the window already covering what it covers: no frame shows the game in between.
// (Milk Run's handler: LYC at 144 / the menu's end and SCX 0 as the frame before its split would have them.)
static void lcd_back(uint8_t lyc) {
    if (mg_id == MG_MILKRUN) { SCX_REG = 0; LYC_REG = lyc; }
    SHOW_WIN;                                    // (lcd_isr hid it at the menu's last line; main.c's update shows it from the next frame)
#if CARD_FADE
    trans_card_in();                             // (the new screen's palettes kept, the screen white, the LCD on, and faded in)
#else
    DISPLAY_ON;
#endif
}

#if CARD_FADE
#define CARD_OFF() trans_card_out()              // (fades to white, the LCD off in it)
#else
#define CARD_OFF() DISPLAY_OFF
#endif

static void card_open(void) {
    uint8_t s = state_timer;
    CARD_OFF();
    glyphs_back();                               // (the card's text may use J and Z)
    if (LCDC_REG & LCDCF_OBJON) s |= PAUSE_OBJ;
    state_timer = s | PAUSE_CARD;
    HIDE_SPRITES;
    WY_REG = 0;                                  // the window over the whole screen: no LYC end
    mg_card_win_open(pause_card(s));
    if (!(mg_id == MG_MILKRUN)) LYC_REG = 255;   // (Milk Run's handler: main.c mr_lcd_isr takes PAUSE_CARD into account)
    lcd_back(144);
}

static void card_close(void) {
    uint8_t s = state_timer;
    CARD_OFF();
    mg_card_win_close();
    WY_REG = BANNER_WY;
    if (s & PAUSE_OBJ) SHOW_SPRITES;
    set_bkg_data(TILE_GLYPH_J, 1, qmark_tile);
    set_bkg_data(TILE_GLYPH_Z, 1, arrow_tile);
    fill_row(0, TILE_PANEL_TOP);
    apply(s & (PAUSE_MINI | 3), 1);
    lcd_back(WIN_LYC(s));
}

void pause_open(void) BANKED {
    uint8_t i, mini = game_state == GS_MINI;
    end_note();                                  // (a note moved WY and LYC; its row 32 is the menu's now)
    overlay_on = 0; HIDE_WIN;                    // (hidden while its rows are written; shown again by main.c's next update)
    state_timer = mini ? PAUSE_MINI : 0;
    game_state = GS_PAUSED;
    i = NR51_REG;                                // the music plays on as the bass and the drums (main.c ticks it while NR51 is not 0); where
    TMA_REG |= 2;                                // (the menu is open: music.c's flag)
    PAUSE_NR51 = i ? i : 0xFF;                   // the game counts music_frames it stands still, silent (NR51 0, no tick)
    NR51_REG = (mini && mg_id == MG_TAIKO) || (boss_on && boss_id == SUMO_VENUE) ? 0 : MENU_MIX;
    for (i = 0; i < 40; i++)                     // what the window covers (as mg.c's result window)
        if (shadow_OAM[i].y > BANNER_WY && shadow_OAM[i].y < BANNER_WY + 64) shadow_OAM[i].y = 0;
    oam_touched();
    set_bkg_data(TILE_GLYPH_J, 1, qmark_tile);
    set_bkg_data(TILE_GLYPH_Z, 1, arrow_tile);
    fill_row(0, TILE_PANEL_TOP);
    if (is_cgb) {                                // the window's rows in the HUD palette
        uint8_t b[20];
        for (i = 0; i < 20; i++) b[i] = BGPAL_HUD;
        VBK_REG = VBK_BANK_1;
        for (i = 0; i < WIN_ROWS; i++) { set_win_tiles(0, i, 20, 1, b); music_pump(); }
        VBK_REG = VBK_BANK_0;
    }
    apply(state_timer, 1);                       // (Milk Run's handler walks LYC itself)
    overlay_on = 1;
}

// the sound, the two letters' tiles and the banner window (panel, a blank text row, panel; its LYC) as they were
static void put_back(void) {
    overlay_on = 0; HIDE_WIN;                    // (first: the window is gone before its rows change)
    if (!NR51_REG) TIMA_REG = 0;                 // (the tune stood still, the timer ran on: no catch-up ticks from the pumps below; a clocked game's beat is the ticks)
    NR51_REG = PAUSE_NR51; PAUSE_NR51 = 0; TMA_REG &= ~2;
    glyphs_back();
    fill_row(0, TILE_PANEL_TOP);                 // (win_init's banner)
    fill_row(1, TILE_HUD_BLANK);
    fill_row(2, TILE_PANEL_BOT);
    if (!((state_timer & PAUSE_MINI) && mg_id == MG_MILKRUN)) LYC_REG = BANNER_LYC;
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
    if (story_on && !(story_arc & 1)) {              // STORY: the title; CONTINUE starts from the last save
        story_on = 0; story_arc = 0; hud_pal_reset();   // (the run's difficulty and the HUD colour it tinted end here)
        if (save_lock == SAVE_LOCK_DEBUG) story_chapter |= DEBUG_RESUME;   // a debug-select run saved nothing: CONTINUE resumes it (story_begin)
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
        move_mark(s, (s & ~3) | c);
    } else if (pressed & (J_START | J_B)) {
        if (s & PAUSE_ASK) apply(m | 2, 0);                                        // back to the menu, the cursor on QUIT
        else pause_close();
    } else if (pressed & J_A) {
        if (!(s & PAUSE_ASK)) {
            if (c == 0) pause_close();
            else if (c == 1) card_open();
            else apply(m | PAUSE_ASK | 1, 0);                                     // the question, the cursor on NO
        } else if (c == 0) {                     // YES
            quit();
            return 1;
        } else apply(m | 2, 0);                                                    // NO
    }
    return 0;
}
