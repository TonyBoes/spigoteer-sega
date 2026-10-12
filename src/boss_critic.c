// The Food Critic, the bistro's boss (docs/minigames_bosses.md 3.6; art approved 2026-10-11, look 2 "the gourmand").
// His row is boss.c rows[3]: 32 px, step 110, push 16, gulp 60 (savouring), hands 1, sip 90, meter 8.
//
// He only takes a PERFECT pour: the story's perfect pour (src/pour.c: released in the sparkle window, mug_timer 1),
// with the window CRIT_WIN frames long in this fight (spec 3.6: 12; the story's shifts keep the owner's 5, the start
// stays POUR_WIN_START 27, so the press-to-release time is 27..38 frames; the sparkle frame shows all of it).
//   - A perfect drink, his hands free and nothing on his mind: the common catch (meter -1, the perfect bonus and cue,
//     push 16, the GULP pose for 60 frames, then his empty glass held and sent 90 frames on).
//   - A sloppy drink (released outside the window, or carried) while he is free: no meter, no score; he TASTEs it for
//     CRIT_TASTE frames (the TASTE pose: a frown and a flat hand; he stands), then sends it back up the bar as a
//     MUG_RETURN (the full drink, 1 px a frame) for the bartender to catch like an empty; past the right end it breaks
//     (a life).
//   - Hands 1, changed from the default so a busy critic never causes an unseen break (spec 3.6): while he holds his
//     glass, tastes, or has a drink still to send back, any drink that reaches him (perfect or not) is waved back: a
//     MUG_RETURN too, no tasting. He keeps at most CRIT_QUEUE of them waiting (boss_queue, the TASTE pose while any
//     waits); a drink arriving past that slides past him and breaks, as with any full-handed boss.
// Every return goes by boss_send, so the fair-empties schedule holds for it like for an empty (its travel at 1 px a
// frame): two of anything never reach the tap end closer than the level's empty_gap.
#pragma bank 255
#include "boss.h"
#include "boss_critic_art.h"
#include "boss_load.h"

#define BP_TASTE     BP_EXTRA  // gen_boss BOSSES critic extra: TASTE
#define CRIT_WIN     12        // the perfect window in his fight (frames; pour.c POUR_WIN_START..+CRIT_WIN-1)
#define CRIT_TASTE   30        // frames he tastes a sloppy drink before sending it back
#define CRIT_QUEUE    3        // drinks waiting to go back at most (then a drink passes him)

uint8_t crit_taste;            // frames of tasting left (tests)
uint8_t crit_sloppy, crit_waved;   // drinks tasted / waved back this fight (tests)

static void crit_look(void) {
    boss_xpose = (crit_taste || boss_queue) ? BP_TASTE : 0;
}

uint8_t boss_critic(uint8_t ev, uint8_t arg) BANKED {
    uint8_t busy;
    switch (ev) {
    case BEV_SET:
        boss_art_set();
        boss_cap = boss_hands + CRIT_QUEUE;
        boss_returns = 1;
        crit_sloppy = crit_waved = 0;
        /* fall through */
    case BEV_RESET:
        crit_taste = 0;
        boss_xpose = 0;
        break;
    case BEV_LOAD:
        boss_art_load();
        break;
    case BEV_BEGIN:
        pour_win = CRIT_WIN;                     // (after pour_load's POUR_WIN_LEN at the fight's start)
        break;
    case BEV_CATCH:
        busy = boss_hold || crit_taste || boss_queue;
        if (mug_timer[arg] == 1 && !busy) return 0;   // perfect, and free: the common catch
        mug_state[arg] = MUG_FREE;
        boss_queue++;
        if (busy) crit_waved++;
        else {
            crit_sloppy++;
            crit_taste = CRIT_TASTE;
            boss_state = BS_SPECIAL; boss_t = 0;     // (he stands while he tastes)
        }
        crit_look();
        return 1;
    case BEV_FRAME:
        if (crit_taste) {
            if (!--crit_taste && boss_state == BS_SPECIAL) { boss_state = BS_WALK; boss_t = 0; }
        } else if (boss_queue && boss_send(MUG_RETURN)) boss_queue--;
        crit_look();
        break;
    }
    return 0;
}
