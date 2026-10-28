// The second tip coin (owner 2026-10-25: at most TWO tips at a time). The first coin is tip_timer / tip_bar / tip_x as ever; the second
// lives in story_scratch (WRAM is full; src/scratch.h SCR_TIP2_AT, in the fight's group), and only means something while the first one
// is out: every place that forgets a tip clears tip_timer, which takes the second with it (tip.c packs them: the first slot fills first).
#ifndef TIP2_H
#define TIP2_H
#include "game.h"
#include "scratch.h"

struct tip2 { uint16_t t; uint8_t bar, x; };
#define TIP2 ((struct tip2 *)(story_scratch + SCR_TIP2_AT))

#define OAM_COIN2  (OAM_COIN - 1)       // OAM 26 (the mugs end below it, game.h OAM_MUG_END)
#endif
