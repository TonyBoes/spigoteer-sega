// Debug level select (build flag DEBUG_MENU), moved out of src/main.c (ROM0) into a switchable bank: opening the box
// and stepping it. src/main.c keeps the per-frame START + SELECT combo watch (debug_watch) and the state.
//
// Mode-aware (owner 2026-10-10): the box selects in the mode it was opened in.
//   - Arcade ("LEVEL nn"): opened in arcade play, or on the title with the cursor on any item but STORY / CONTINUE
//     (PLAY's submenu: ARCADE; the top level and the BONUS / SETTINGS submenus open the arcade box as before).
//     Left/Down and Right/Up change the level (1..DEBUG_LEVELS, wrapping); A starts it from scratch (start_new_game).
//   - Story ("STORY c STEP"): opened in story play (story_on), or on the title with PLAY's cursor on STORY (chapter 1,
//     its PRE scene) or CONTINUE (the saved chapter: its first step when one was reached, else its PRE scene). The
//     positions of a chapter are its PRE scene, the steps of the story's sequence the engine can play (story_step_get:
//     a STEP_SKIP step only when story_unskip names it), its POST scene. Left/Right change the chapter (1..10, wrapping;
//     the position kept, or the next playable one), Up/Down the position (wrapping). A starts it with the story's
//     rules (story_debug_start, src/story.c: a fresh score, the venue's 3 lives, its goals and perfect pour; a POST
//     scene goes on to the next chapter as usual). Such a run writes nothing to SRAM (save.c save_lock, cleared by
//     the title): no story progress, no soundtrack unlocks, so a playtest jump never unlocks what was not earned.
//   B closes the box (back to the title, or unpauses).
#pragma bank 255
#include <gb/gb.h>
#include <stdint.h>

#include "game.h"
#include "music.h"
#include "story.h"

#ifdef DEBUG_MENU
#define DEBUG_LEVELS       20
#define POS_POST          (STORY_STEPS + 1)    // positions: 0 PRE, 1..STORY_STEPS the steps, POS_POST
extern uint8_t debug_menu_open, debug_level, debug_from_title, debug_toggled;
extern uint8_t overlay_on, level, story_chapter, story_step;
uint8_t debug_story;               // 1: the box selects a story position
uint8_t debug_chapter;             // its chapter (0..STORY_CHAPTERS-1)
uint8_t debug_pos;                 // its position (0 PRE, 1..STORY_STEPS step pos-1, POS_POST)
void story_debug_start(uint8_t ch, uint8_t pos) BANKED;   // src/story.c

static const char *const step_label[4] = { "OPEN", "HAPPY", "LAST", "" };   // a shift's index (STEP_INDEX)

// 1: position p of chapter ch can be started
static uint8_t pos_ok(uint8_t ch, uint8_t p) {
    if (p == 0 || p == POS_POST) return 1;
    return !(story_step_get(ch, p - 1) & STEP_SKIP) || ((story_unskip >> (p - 1)) & 1);
}

// the next position from p in direction d (+1 / -1, wrapping) that can be started
static uint8_t pos_next(uint8_t ch, uint8_t p, int8_t d) {
    do p = d > 0 ? (p == POS_POST ? 0 : p + 1) : (p == 0 ? POS_POST : p - 1);
    while (!pos_ok(ch, p));
    return p;
}

static void debug_show(void) {
    char s[21];
    const char *n;
    uint8_t i = 0, k;
    if (!debug_story) {
        s[0] = 'L'; s[1] = 'E'; s[2] = 'V'; s[3] = 'E'; s[4] = 'L'; s[5] = ' ';
        s[6] = '0' + debug_level / 10; s[7] = '0' + debug_level % 10; s[8] = 0;
        show_overlay(s);
        return;
    }
    for (n = "STORY "; *n; n++) s[i++] = *n;
    if (debug_chapter >= 9) { s[i++] = '1'; s[i++] = '0' + debug_chapter - 9; }   // chapter 10
    else s[i++] = '1' + debug_chapter;
    s[i++] = ' ';
    if (debug_pos == 0) n = "PRE";
    else if (debug_pos == POS_POST) n = "POST";
    else {
        k = story_step_get(debug_chapter, debug_pos - 1);
        n = (k & STEP_KIND) == STEP_MINI ? "MINI" : (k & STEP_KIND) == STEP_BOSS ? "BOSS" : step_label[k & 3];
    }
    while (*n) s[i++] = *n++;
    s[i] = 0;
    show_overlay(s);
}

void debug_open(void) BANKED {
    uint8_t k;
    debug_from_title = game_state == GS_TITLE;
    debug_story = 0;
    if (debug_from_title) {
        debug_level = 1;
        if (debug_toggled) title_music_toggle();     // the SELECT that began the combo toggled the music: undo
        k = title_items[title_sel];
        if (k == K_STORY) { debug_story = 1; debug_chapter = 0; debug_pos = 0; }
        else if (k == K_CONTINUE) {                  // as CONTINUE starts it (story.c story_begin)
            debug_story = 1;
            debug_chapter = story_progress < STORY_CHAPTERS ? story_progress : STORY_CHAPTERS - 1;
            debug_pos = story_reached ? pos_next(debug_chapter, 0, 1) : 0;
        }
    } else if (story_on) {                           // in story play: where the story is
        debug_story = 1;
        debug_chapter = story_chapter;
        debug_pos = story_step + 1;
        if (!pos_ok(debug_chapter, debug_pos)) debug_pos = pos_next(debug_chapter, debug_pos, 1);
    } else debug_level = level < DEBUG_LEVELS ? level : DEBUG_LEVELS;
    debug_toggled = 0;
    game_state = GS_DEBUG;
    debug_menu_open = 1;
    debug_show();
}

// story mode: Left/Right the chapter, Up/Down the position
static void story_keys(uint8_t pressed) {
    uint8_t c = debug_chapter, p = debug_pos;
    if (pressed & J_RIGHT) c = c == STORY_CHAPTERS - 1 ? 0 : c + 1;
    else if (pressed & J_LEFT) c = c == 0 ? STORY_CHAPTERS - 1 : c - 1;
    if (c != debug_chapter && !pos_ok(c, p)) p = pos_next(c, p, 1);
    if (pressed & J_DOWN) p = pos_next(c, p, 1);
    else if (pressed & J_UP) p = pos_next(c, p, -1);
    if (c != debug_chapter || p != debug_pos) { debug_chapter = c; debug_pos = p; debug_show(); }
}

// 1: A started a level (the frame is over)
uint8_t debug_step(uint8_t pressed) BANKED {
    uint8_t l = debug_level;
    if (debug_story) story_keys(pressed);
    else {
        if (pressed & (J_RIGHT | J_UP)) l = l == DEBUG_LEVELS ? 1 : l + 1;
        else if (pressed & (J_LEFT | J_DOWN)) l = l == 1 ? DEBUG_LEVELS : l - 1;
        if (l != debug_level) { debug_level = l; debug_show(); }
    }
    if (pressed & J_A) {
        debug_menu_open = 0;
        if (debug_story) { overlay_on = 0; save_lock = 1; story_debug_start(debug_chapter, debug_pos); }
        else { play_mode = MODE_LEVEL; start_new_game(l); }
        return 1;
    }
    if (pressed & J_B) {
        debug_menu_open = 0; overlay_on = 0;
        game_state = debug_from_title ? GS_TITLE : GS_PLAYING;
    }
    return 0;
}
#endif
