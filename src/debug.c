// Debug level select (build flag DEBUG_MENU), moved out of src/main.c (ROM0) into a switchable bank: opening the box
// and stepping it. src/main.c keeps the per-frame START + SELECT combo watch (debug_watch) and the state.
#pragma bank 255
#include <gb/gb.h>
#include <stdint.h>

#include "game.h"

#ifdef DEBUG_MENU
#define DEBUG_LEVELS       18
extern uint8_t debug_menu_open, debug_level, debug_from_title, debug_toggled;
extern uint8_t overlay_on, level;
void show_overlay(const char *s);                // src/main.c (ROM0)
void start_new_game(uint8_t lv);

static void debug_show(void) {
    char s[9] = "LEVEL 00";
    s[6] = '0' + debug_level / 10; s[7] = '0' + debug_level % 10;
    show_overlay(s);
}

void debug_open(void) BANKED {
    debug_from_title = game_state == GS_TITLE;
    if (debug_from_title) {
        debug_level = 1;
        if (debug_toggled) title_music_toggle();     // the SELECT that began the combo toggled the music: undo
    } else debug_level = level < DEBUG_LEVELS ? level : DEBUG_LEVELS;
    debug_toggled = 0;
    game_state = GS_DEBUG;
    debug_menu_open = 1;
    debug_show();
}

// 1: A started a level (the frame is over)
uint8_t debug_step(uint8_t pressed) BANKED {
    uint8_t l = debug_level;
    if (pressed & (J_RIGHT | J_UP)) l = l == DEBUG_LEVELS ? 1 : l + 1;
    else if (pressed & (J_LEFT | J_DOWN)) l = l == 1 ? DEBUG_LEVELS : l - 1;
    if (l != debug_level) { debug_level = l; debug_show(); }
    if (pressed & J_A) { debug_menu_open = 0; start_new_game(l); return 1; }
    if (pressed & J_B) {
        debug_menu_open = 0; overlay_on = 0;
        game_state = debug_from_title ? GS_TITLE : GS_PLAYING;
    }
    return 0;
}
#endif
