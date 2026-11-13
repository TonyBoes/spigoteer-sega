// Music CPU rig (tools/music_rig.py; never part of the game ROM).  Plays the tune the host writes into aud_req (PyBoy memory) through the
// real src/music.c + hUGEDriver + the generated build/music_*.c, once a frame, and meters every music_tick call with DIV (64 M-cycles a count).
#include <gb/gb.h>
#include <stdint.h>
#include "music.h"

volatile uint8_t aud_req;
volatile uint8_t aud_nr51;       // 0: leave NR51 alone; else written after every tick (0xCC: the pause menu's bass + drums)
static uint8_t aud_cur;
volatile uint16_t aud_cyc_sum;   // DIV counts spent in music_tick since the host zeroed it, the last call's, and the worst
volatile uint8_t aud_cyc_max, aud_cyc_last;

void main(void) {
    aud_req = 254; aud_cur = 253; aud_nr51 = 0;
    music_init();
    while (1) {
        if (aud_req != aud_cur) {
            aud_cur = aud_req;
            if (aud_cur == 255) music_stop(); else if (aud_cur < TUNE_ALL) music_play(aud_cur);
        }
        vsync();
        {
            uint8_t d0 = DIV_REG, d;
            music_tick();
            d = DIV_REG - d0;
            aud_cyc_sum += d; aud_cyc_last = d;
            if (d > aud_cyc_max) aud_cyc_max = d;
        }
        if (aud_nr51) NR51_REG = aud_nr51;
    }
}
