// Big Tex, the saloon's boss (docs/minigames_bosses.md 3.3): the tutorial boss, the engine's common rules and no
// special. His row is boss.c rows[0]; this file holds his art (build/boss_big_tex_art.h) in its own bank.
#pragma bank 255
#include "boss.h"
#include "boss_big_tex_art.h"
#include "boss_load.h"

uint8_t boss_big_tex(uint8_t ev, uint8_t arg) BANKED {
    (void)arg;
    if (ev == BEV_SET) boss_art_set();
    else if (ev == BEV_LOAD) boss_art_load();
    return 0;
}
