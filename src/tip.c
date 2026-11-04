// Tips: a served patron may drop a coin (maybe_tip: banked, it was ROM0 code in patrons.c), and the second coin's frame: counting down and picking up (tip_step) and
// drawing (tip_draw2), called from main.c / render.c only while a second coin lies there, so one coin or none costs what it always did.
//   - At most TWO coins at a time in ARCADE and STORY (owner 2026-10-25): the second is TIP2 (tip2.h). CLASSIC and the harness keep one (tip_pocket 0).
//   - GUS (the Saloon's look 2) ALWAYS tips there (owner 2026-10-22): no roll, so no random number is drawn for him. A tip_chance of 0 still means "never"
//     (the harness and a boss fight set it), and no coin comes while two lie there, or during a show unless the pocket is on and empty (pocket.c).
#pragma bank 255
#include <gb/gb.h>
#include <stdint.h>

#include "game.h"
#include "music.h"
#include "tip2.h"

extern uint8_t cur_group;

// A served patron's tip (level.c push_for: the push that serves him). The coin drops under him where he stands as the mug lands and the push takes him
// away, so it is his and shows while he is still on the screen (owner 2026-10-17).
void maybe_tip(uint8_t p) BANKED {
    struct tip2 *t = TIP2;
    if (tip_first || (show_timer && tip_pocket != TILE_HUD_BLANK)) return;   // (CLASSIC: not before the level's first tip, send_empty)
    if (tip_timer && (!tip_pocket || t->t)) return;                          // one coin there already (CLASSIC: one at a time), or two
    if (!tip_chance) return;                                                 // 0 never (and draws no random number)
    if (!(tip_pocket && !cur_group && (patron_variant[p] & 7) == 2 && !(debug_from_title & TUNE_GUS_ROLLS)) &&   // GUS: always (unless the debug TUNING page says not)
        tip_chance != 255 && next_rand() >= tip_chance) return;
    if (tip_timer) { t->t = TIP_FRAMES; t->bar = patron_bar[p]; t->x = patron_x[p] + 4; return; }
    t->t = 0;
    tip_timer = TIP_FRAMES;
    tip_bar = patron_bar[p];
    tip_x = patron_x[p] + 4;                            // (centred under him, as classic_tip puts the first one)
}

// One frame of a coin: it counts down, and the bartender picks it up by standing on it (16 px span overlapping its 8 px). 1: picked up.
static uint8_t coin_step(uint16_t *t, uint8_t b, uint8_t x, uint8_t skip) {
    if (!*t) return 0;
    (*t)--;
    if (*t && !skip && bar == b && bartender_x < (uint8_t)(x + 8) && (uint8_t)(bartender_x + 16) > x) { *t = 0; return 1; }
    return 0;
}

// (main.c, while a coin lies there) one pick-up a frame: the first coin has the right of way
void tip_step(void) BANKED {
    struct tip2 *t = TIP2;
    uint8_t a = coin_step(&tip_timer, tip_bar, tip_x, 0);
    if (tip_pocket) {
        a |= coin_step(&t->t, t->bar, t->x, a);
        if (!tip_timer && t->t) { tip_timer = t->t; tip_bar = t->bar; tip_x = t->x; t->t = 0; }   // (the first slot fills first)
    }
    if (a) {
        add_score(TIP_SCORE);
        SFX(SFX_COIN);
        start_show();
    }
}

// The coin on its bar's counter (blinks in its last second, glints every half second): OAM 27, the second one OAM 26.
static void coin_draw(OAM_item_t *o, uint16_t t, uint8_t b, uint8_t x) {
    if (!t || (t < TIP_BLINK && (t & 4))) { o->y = 0; return; }
    o->y = bar_oam_y[b] + MUG_DY;
    o->x = x + 8;
    o->tile = OBJ_COIN + (((t >> 3) & 7) == 0 ? 2 : 0);
    o->prop = OBJPAL_BARTENDER;          // (owner Q37: Sal's palette reads as pale gold; OBJ 5 is the show's alone. DMG: palette 0 too)
}

void tip_draw2(void) BANKED {
    struct tip2 *t = TIP2;
    coin_draw(shadow_OAM + OAM_COIN2, tip_timer ? t->t : 0, t->bar, t->x);   // (the first coin: render.c draw_coin)
}
