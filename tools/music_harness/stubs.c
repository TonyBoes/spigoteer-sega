// What src/music.c expects from the rest of the game (save.c, story): nothing, for the CPU rig.
#pragma bank 255
#include <gb/gb.h>
#include <stdint.h>
uint8_t story_on = 0;
void tune_heard(uint8_t t) BANKED { (void)t; }
uint8_t is_cgb = 0;                       // music.h DS_NOW: the rig is a normal-speed (DMG) ROM
