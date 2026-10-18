// What src/music.c expects from the rest of the game (save.c, story): nothing, for the CPU rig.
#pragma bank 255
#include <gb/gb.h>
#include <stdint.h>
uint8_t story_on = 0;
void tune_heard(uint8_t t) BANKED { (void)t; }
