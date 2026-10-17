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
// READABLE STATES (owner 2026-10-14: "it was hard to tell what status he was in"; docs/minigames_bosses.md 3.6, DESIGN in the
// task notes): FREE = the WALK / STOMP pose (a smile, the open palm out over a checked napkin); SAVOURING = GULP (glass up, a
// perfect drink was just taken); HOLDING his empty = the HOLD / HOLDHOP poses (eye shut, the empty glass in his hand: the
// engine's hand column is not used); TASTING or sending a drink back = TASTE (frown, flat hand). A drink that reaches him while he
// is busy is waved back with the TASTE pose for CRIT_NO frames and a speech bubble beside him ("NO!" for a perfect drink,
// "BAD" for a sloppy one; the banner window would cover his bar), and a sloppy one he tastes shows "BAD" too.
// ENTRANCE (first start of the fight, BEV_INTRO like Duke's): a silver cloche slides along his counter, a bell dings and the lid
// flies off: there he is, hand out. Sprites in OAM 30.. (no show runs in a fight) from his hat tiles (gen_boss hats).
// Every return goes by boss_send, so the fair-empties schedule holds for it like for an empty (its travel at 1 px a
// frame): two of anything never reach the tap end closer than the level's empty_gap.
#pragma bank 255
#include "boss.h"
#include "boss_critic_art.h"
#include "boss_load.h"
#include "music.h"

#define BP_TASTE     BP_EXTRA  // gen_boss BOSSES critic extra: TASTE
#define CRIT_WIN     12        // the perfect window in his fight (frames; pour.c POUR_WIN_START..+CRIT_WIN-1)
#define CRIT_TASTE   30        // frames he tastes a sloppy drink before sending it back
#define CRIT_QUEUE    3        // drinks waiting to go back at most (then a drink passes him)

#define BP_HOLD      (BP_EXTRA + 1)   // extra poses HOLD, HOLDHOP (gen_boss)
#define BP_HOLDHOP   (BP_EXTRA + 2)
#define CRIT_NO      24        // frames of the refusing gesture (the TASTE pose) after a drink is waved back
#define CRIT_BUB     44        // frames the speech bubble stays
#define H_END         4        // topper tile offsets (OBJ_TOPPER +): the hats in gen_boss order after STILL, BOB
#define H_MID         6
#define H_GLINT       8
#define H_NO          10       // NO_L, NO_R
#define H_BAD         14       // BAD_L, BAD_R
#define OAM_CRIT      (OAM_DANCERS + 2)   // 30..: the bubble (2) / the cloche (4) and the glint (29 is the engine's hand mug; 37-39 its capacity indicator)
#define E_SLIDE       30       // entrance: the cloche reaches his spot
#define E_BELL        34       // the bell (SFX_COIN) and the glint
#define E_LIFT        46       // the lid flies off, he is there
#define E_END         72       // its last frame

typedef struct {
    uint8_t px;        // his x last frame (a step forward = a stomp)
    uint8_t dip;       // frames of the stomp's lower pose left
    uint8_t no;        // frames of the refusing gesture left
    uint8_t bub;       // frames the bubble has left
    uint8_t bubk;      // 0 "NO!", 1 "BAD"
    uint8_t ent;       // the entrance: 0 none, else the next frame's number + 1 (tests)
} critic_t;
#define crit (*(critic_t *)BOSS_OWN)
#if 6 > BOSS_OWN_N
#error "the Critic's state: BOSS_OWN_N"
#endif

uint8_t crit_taste;            // frames of tasting left (tests)
uint8_t crit_sloppy, crit_waved;   // drinks tasted / waved back this fight (tests)

static void crit_look(void) {
    if (crit.no || crit_taste) boss_xpose = BP_TASTE;                  // refusing / tasting
    else if (boss_state == BS_GULP) boss_xpose = 0;                    // savouring: GULP
    else if (boss_queue) boss_xpose = BP_TASTE;                        // sending drinks back
    else if (boss_hold) boss_xpose = crit.dip ? BP_HOLDHOP : BP_HOLD;  // holding his empty
    else boss_xpose = 0;                                               // free: WALK / STOMP
}

static void bubble(void) {
    OAM_item_t *o = shadow_OAM + OAM_CRIT;
    uint8_t x = boss_x + 46, t = crit.bubk ? H_BAD : H_NO;
    if (!crit.bub || x > 152 || boss_state == BS_OUTRO) { o[0].y = o[1].y = 0; return; }
    o[0].y = o[1].y = bar_oam_y[boss_bar] - 1;
    o[0].x = x; o[1].x = x + 8;
    o[0].tile = OBJ_TOPPER + t; o[1].tile = OBJ_TOPPER + t + 2;
    o[0].prop = o[1].prop = is_cgb ? OBJPAL_PATRON_C : S_PALETTE;
}

static void ent_clear(void) {
    uint8_t i;
    for (i = 0; i != 6; i++) shadow_OAM[OAM_CRIT + i].y = 0;
}

// BEV_DRAW: the entrance's sprites (the cloche: END, MID, MID flipped, END flipped; the glint)
static void ent_draw(void) {
    OAM_item_t *o = shadow_OAM + OAM_CRIT;
    uint8_t t = crit.ent - 2, k, prop = is_cgb ? OBJPAL_COIN : S_PALETTE;
    int16_t x = 16, y = bar_oam_y[boss_bar];
    static const uint8_t tl[4] = { H_END, H_MID, H_MID, H_END };
    if (crit.ent < 2) return;
    if (t < E_SLIDE) x = -32 + (uint8_t)((t * 8 + 2) / 5);
    else if (t >= E_BELL && t < E_LIFT) y += (t >> 1) & 1;          // the lid rattles
    if (t >= E_LIFT) y -= (int16_t)(t - E_LIFT + 1) * 4;
    for (k = 0; k != 4; k++, o++) {
        int16_t cx = x + 8 + k * 8;
        if (y < 16 || cx < 1 || cx > 167) { o->y = 0; continue; }
        o->y = (uint8_t)y; o->x = (uint8_t)cx; o->tile = OBJ_TOPPER + tl[k]; o->prop = prop | (k > 1 ? 0x20 : 0);
    }
    o->y = 0;
    if (t >= E_BELL && t < E_LIFT + 10 && (t & 2)) { o->y = bar_oam_y[boss_bar] - 12; o->x = 16 + 8 + 12 + (t >= E_LIFT ? 8 : 0); o->tile = OBJ_TOPPER + H_GLINT; o->prop = is_cgb ? OBJPAL_PATRON_C : S_PALETTE; }
}

// BEV_INTRO: the entrance's clock; the bartender stays at bar 0's tap until it is over
static void ent_frame(void) {
    uint8_t t = crit.ent - 1;
    fill_timer = 0; fill_stage = 0;                          // (the bartender stays where he is: main.c skips his input while he is held)
    bartender_frame = BT_IDLE; catch_pose = 0; bt_bob = 0;
    if (t < E_LIFT) intro_timer = INTRO_FRAMES;
    if (t == E_BELL) SFX(SFX_COIN);
    if (t == E_LIFT) {
        intro_timer = INTRO_FRAMES - 1;
        boss_xpose = 0;
        boss_to_bar(boss_bar, 16);
        SFX(SFX_SHAKE);
    }
    if (t >= E_END) { crit.ent = 0; boss_state = BS_WALK; ent_clear(); return; }   // (E9: over: boss.c starts the fight)
    crit.ent++;
}

uint8_t boss_critic(uint8_t ev, uint8_t arg) BANKED {
    uint8_t busy;
    switch (ev) {
    case BEV_SET:
        boss_art_set();
        boss_cap = boss_hands + CRIT_QUEUE;
        boss_returns = 1;
        crit_sloppy = crit_waved = 0;
        crit.ent = 0;
        /* fall through */
    case BEV_RESET:
        crit_taste = 0;
        crit.no = crit.bub = crit.dip = 0; crit.px = boss_x;
        boss_xpose = 0;
        ent_clear();
        if (crit.ent) { boss_state = BS_JUMP; boss_xpose = BP_HIDE; }   // (the entrance: not on his bar yet)
        break;
    case BEV_LOAD:
        boss_art_load();
        if (is_cgb) {                    // the cloche's silver in OBJ 5 (no tips in a fight)
            palette_t p;
            p[0] = 0; p[1] = RGB(30, 31, 31); p[2] = RGB(15, 17, 21); p[3] = RGB(3, 4, 7);
            set_sprite_palette(OBJPAL_COIN, 1, p);
        }
        break;
    case BEV_ENTER:                      // (E9: after the warm-up)
        crit.ent = 1;
        return 1;
    case BEV_INTRO:
        if (crit.ent) ent_frame();
        break;
    case BEV_DRAW:
        if (crit.ent) ent_draw();
        break;
    case BEV_BEGIN:
        pour_win = CRIT_WIN;                     // (after pour_load's POUR_WIN_LEN at the fight's start)
        break;
    case BEV_OUTRO:
        crit.no = crit.bub = 0;
        bubble();
        break;
    case BEV_CATCH:
        busy = boss_hold || crit_taste || boss_queue;
        if (mug_timer[arg] == 1 && !busy) return 0;   // perfect, and free: the common catch
        crit.bubk = mug_timer[arg] != 1;             // "BAD" for a sloppy drink, "NO!" for a perfect one that came too soon
        crit.bub = CRIT_BUB;
        mug_state[arg] = MUG_FREE;
        boss_queue++;
        if (busy) { crit_waved++; crit.no = CRIT_NO; }
        else {
            crit_sloppy++;
            crit_taste = CRIT_TASTE;
            boss_state = BS_SPECIAL; boss_t = 0;     // (he stands while he tastes)
        }
        crit_look();
        return 1;
    case BEV_ROOM:                               // busy or tasting: whatever reaches him is waved back (no room)
        if (boss_hold || crit_taste || boss_queue) return ROOM_FREE(0);
        break;                                   // (free: the engine counts his one hand: a perfect drink is taken)
    case BEV_FRAME:
        if (boss_x > crit.px) crit.dip = 8;
        else if (crit.dip) crit.dip--;
        crit.px = boss_x;
        if (crit.no) crit.no--;
        if (crit.bub) crit.bub--;
        if (crit_taste) {
            if (!--crit_taste && boss_state == BS_SPECIAL) { boss_state = BS_WALK; boss_t = 0; }
        } else if (boss_queue && boss_send(MUG_RETURN)) boss_queue--;
        crit_look();
        bubble();
        break;
    }
    return 0;
}
