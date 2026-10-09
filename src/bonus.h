// Bonus round (M6): the shell game with six cans. Lives in its own ROM bank (autobanked);
// main.c only calls these two trampolines.
#ifndef BONUS_H
#define BONUS_H
#include <gb/gb.h>
#include <stdint.h>

extern uint8_t bonus_round;        // bonus rounds played so far (1 during the first)
void bonus_enter(void) BANKED;     // LCD-off redraw of the bonus scene; the caller sets game_state
uint8_t bonus_update(uint8_t pressed) BANKED;   // one frame; returns 1 when the round is over
#endif
