// The Sasquatch, the lumber lodge's boss (docs/minigames_bosses.md 3.5; art approved 2026-10-11, look A round 2).
// His row is boss.c rows[2]: 32 px, step 90, push 8, hands 2, meter 12; gulp 8 (he downs a coffee "instantly") and
// sip 0: each empty goes as soon as the fair-empties schedule allows, and it slides back at 1 px a frame (his bar is
// a fast-empty bar: boss.c boss_mugs). Holding two, the third coffee passes him and breaks (the hands rule).
// His own empties keep only SASQ_GAP frames between them (the game's floor; the lodge's 108 would make him mostly a
// holder); the regulars' empties still keep the level's empty_gap from his, and his from theirs (boss.c boss_send).
// No special, so no tell: the rule is visible all fight long (his empties are the fast ones).
#pragma bank 255
#include "boss.h"
#include "boss_sasquatch_art.h"
#include "boss_load.h"

#define SASQ_GAP  80          // frames between two of his own empties' arrivals (spec 3.5)

uint8_t boss_sasquatch(uint8_t ev, uint8_t arg) BANKED {
    (void)arg;
    if (ev == BEV_SET) {
        boss_art_set();
        boss_fast_empty = 1;
        boss_own_gap = SASQ_GAP;
    } else if (ev == BEV_LOAD) boss_art_load();
    return 0;
}
