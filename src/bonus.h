// Bonus rounds: the M6 shell game with six cans (bonus.c), M12 Perfect Pour and Tip Shower (bonus2.c). Lives in its own ROM bank (autobanked);
// main.c only calls these two trampolines.
#ifndef BONUS_H
#define BONUS_H
#include <gb/gb.h>
#include <stdint.h>

extern uint8_t bonus_round;        // bonus rounds played so far (1 during the first)
extern uint8_t bonus_kind;         // M12: this round's game: 0 can shake-up, 1 Perfect Pour, 2 Tip Shower ((bonus_round - 1) % 3)
extern uint8_t bonus_phase, bonus_timer;   // every round ends in phase 4 (PH_RESULT / PH_END) after ~130 frames
void bonus_enter(void) BANKED;     // LCD-off redraw of the bonus scene; the caller sets game_state
uint8_t bonus_update(uint8_t pressed) BANKED;   // one frame; returns 1 when the round is over
void bonus2_enter(void) BANKED;    // src/bonus2.c (M12): LCD off, after bonus_enter's common setup
uint8_t bonus2_update(void) BANKED;
#endif
