// Big Tex, the saloon's boss (docs/minigames_bosses.md 3.3): the tutorial boss, the engine's common rules and no
// special. His row is boss.c rows[0]; this file holds his art (build/boss_big_tex_art.h) in its own bank.
//
// ENTRANCE (E8, 2026-10-15; a PROPOSAL for the owner to judge, built like Duke's: BEV_INTRO + BEV_DRAW, the fight's first start
// only): "the swagger". He walks in from the left edge of the screen, the spurs jingling (SFX_COIN every 16 frames), then stops
// at his bar, bows and tips his ten-gallon hat (the WHOLE hat, crown and brim, pops 8-10 px up and drops back: four sprites over his BARE pose,
// the STOMP body with a bare head, or, on a frame where a line has no room for nine, only the crown as before; the body bobs one row: his STOMP pose; SFX_SERVE
// is the cheer; a thud as he settles on his bar). 138 frames: 12 of empty bar, 75 walking (0.75 px a frame, the bob every 8), 11 standing, 30 tipping, a pause.
// He is drawn as sprites from his own body tiles (the BG's column pairs at BG 162.., which an 8x16 sprite can use as well: no
// new tiles, no OAM beyond 6 entries, colours of OBJ palette 7 = BG palette 4's) in BS_JUMP + BP_HIDE (nothing of his on his
// bar, no catch); at the last frame boss_to_bar(boss_bar, 16) puts the BG body exactly under the sprites and the intro's 90
// frames start there (intro_timer is held until then), the fight as it was. The bartender is held at bar 0's tap, no
// pouring, until then. Test hook (WRAM: BOSS_OWN, no variable of his own): tex.ent (0 none or over, else the next frame's
// number + 1).
#pragma bank 255
#include "boss.h"
#include "boss_big_tex_art.h"
#include "boss_load.h"
BOSS_CAST_FN(boss_big_tex_cast)   // the credits' cast card (src/credits.c)
#include "music.h"

typedef struct {
    uint8_t ent;        // the entrance: 0 none (or over), else the next frame's number + 1 (tests)
} big_tex_t;
#define tex (*(big_tex_t *)BOSS_OWN)

#define ENT_START    12                 // the first frame he is on screen (he is at x -40)
#define ENT_WALKEND  87                 // he has reached x 16 (75 frames, 3 px every 4)
#define ENT_TIP      98                 // the hat tip: 15 steps of 2 frames
#define ENT_LAND    138                 // the last frame: his BG body under the sprites
#define ENT_OAM     (OAM_FILL + 1)      // the mugs' first entry: nothing is in the air during the entrance
#define ENT_OAM_N     9                 // the five body columns and the whole hat (4 sprites) while it is up
#define HAT_POP       4                 // topper tile offset: HAT_POP0..3 (gen_boss `hats` after STILL, BOB), 2 tiles each
#define TEX_HAT_DX   16                 // boss.c rows[0].hat_dx
#if ENT_OAM + ENT_OAM_N > OAM_MUG_END || BOSS_ART_COLS != 5
#error "Big Tex's entrance: the OAM entries or a 40 px body"
#endif

static const uint8_t tip_dy[15] = { 0, 8, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 8, 0 };   // the hat's lift in px, per 2 frames: it pops off 8 px at once (an 8x16 sprite's 16
                                                                                             // lines then end above his head: the hat's four sprites never share a line with his five) and drops back

static uint8_t pair_id(uint8_t p) {
    return p < BOSS_PAIRS_A ? BOSS_BG_A + (p << 1) : BOSS_BG_B + ((uint8_t)(p - BOSS_PAIRS_A) << 1);
}

// His pose (WALK / STOMP: the bob) and left edge at entrance frame t, and the hat's lift
static uint8_t ent_pose(uint8_t t) {
    uint8_t k;
    if (t >= ENT_TIP && t < ENT_TIP + 30) {
        k = (t - ENT_TIP) >> 1;
        return k >= 1 && k <= 13 ? BP_STOMP : BP_WALK;      // (he bows over the tip: while the hat is up)
    }
    return t >= ENT_START && t < ENT_WALKEND && (t & 8) ? BP_STOMP : BP_WALK;
}

// 1 if the whole hat may be drawn now (crown and brim: four sprites over the lines from its y `hy` down, the body's five from `y`): on each
// of the eight 4-line bands from `hy` the hat's 4 and the body's 5 where they reach it, plus every other entry in OAM that touches
// the band (an upper bound, as boss.c's bands), must stay within LINE_OBJ_MAX.
static uint8_t pop_fits(uint8_t hy, uint8_t y) {
    OAM_item_t *o = shadow_OAM;
    uint8_t n[8], k = 40, j, r = y - hy;
    for (j = 0; j != 8; j++) n[j] = (j < 4 ? 4 : 0) + ((uint8_t)(r - 4 * j + 15) < 19 ? BOSS_ART_COLS : 0);   // (the body touches the band: its lines r..r+15)
    do {
        if (o->y && (o < shadow_OAM + ENT_OAM || o >= shadow_OAM + ENT_OAM + ENT_OAM_N) && (uint8_t)(o->y - hy + 15) < 47) {
            uint8_t d = o->y - hy;
            for (j = 0; j != 8; j++)
                if ((uint8_t)(d - 4 * j + 15) < 19) n[j]++;
        }
        o++;
    } while (--k);
    for (j = 0; j != 8; j++)
        if (n[j] > LINE_OBJ_MAX) return 0;
    return 1;
}

// BEV_DRAW: his sprites for the frame the logic just reached (boss_draw, after every other sprite)
static void ent_draw(void) {
    OAM_item_t *o = shadow_OAM + ENT_OAM, *top = o + ENT_OAM_N, *end = shadow_OAM + OAM_MUG_END - 2 * lift_total;
    uint8_t t = tex.ent - 2, k, pose, y = bar_oam_y[boss_bar], pal = is_cgb ? OBJPAL_PATRON_C : S_PALETTE, lift = 0;
    int16_t bx, cx;
    if (tex.ent < 2) return;
    if (end > top) end = top;
    if (t >= ENT_START) {
        bx = t >= ENT_WALKEND ? 16 : -40 + ((((uint8_t)(t - ENT_START)) * 3) >> 2);
        pose = ent_pose(t);
        if (t >= ENT_TIP && t < ENT_TIP + 30) lift = tip_dy[(t - ENT_TIP) >> 1];
        if (lift && end - o >= BOSS_ART_COLS + 4 && pop_fits(y - 8 - lift, y)) {   // the whole hat is off: his bare head under it
            pose = BP_EXTRA;
            for (k = 0; k != 4; k++) {
                cx = bx + (k << 3) + 8;
                if ((uint16_t)(cx - 1) >= 167) continue;
                o->y = y - 8 - lift; o->x = (uint8_t)cx; o->prop = pal; o->tile = OBJ_TOPPER + HAT_POP + (k << 1);
                o++;
            }
            lift = 0;
        }
        for (k = 0; k != BOSS_ART_COLS && o != end; k++) {
            cx = bx + (k << 3) + 8;
            if ((uint16_t)(cx - 1) >= 167) continue;      // (off the screen: left out; the hardware counts every entry on a line)
            o->y = y; o->x = (uint8_t)cx; o->tile = pair_id(boss_art_pose[pose][k]); o->prop = pal;
            o++;
        }
        cx = bx + TEX_HAT_DX + 8;
        if (pose != BP_EXTRA && o != end && (uint16_t)(cx - 1) < 167) {   // (no room for the whole hat: only its crown lifts, as it did)
            o->y = y - 8 - lift; o->x = (uint8_t)cx; o->prop = pal;
            o->tile = OBJ_TOPPER + (pose == BP_STOMP && !lift ? 2 : 0);
            o++;
        }
    }
    for (; o != top; o++) o->y = 0;
}

// BEV_INTRO, every frame while intro_timer runs: the entrance's clock and what happens at its frames. The player's input is
// undone (the bartender stays at bar 0's tap, nothing is poured) until he is on his bar.
static void ent_frame(void) {
    uint8_t t = tex.ent - 1, i;
    fill_timer = 0; fill_stage = 0;                          // (the bartender stays where he is: main.c skips his input while he is held)
    bartender_frame = BT_IDLE; catch_pose = 0; bt_bob = 0;
    if (t < ENT_LAND) intro_timer = INTRO_FRAMES;           // (held: the intro's 90 frames start at the landing)
    if (t >= ENT_START && t < ENT_WALKEND && !(t & 15)) SFX(SFX_COIN);       // the spurs
    if (t == ENT_TIP + 6) SFX(SFX_SERVE);                                      // the cheer, as the hat is up
    if (t == ENT_LAND) {
        intro_timer = INTRO_FRAMES - 1;                      // (as the level's first frame leaves it: the fight starts 89 frames on)
        boss_xpose = 0; boss_state = BS_WALK;
        boss_to_bar(boss_bar, 16);                           // his BG body (WALK) at x 16, under where the sprites were
        for (i = 0; i != ENT_OAM_N; i++) shadow_OAM[ENT_OAM + i].y = 0;
        SFX(SFX_SHAKE);                                      // (the boots settle)
        tex.ent = 0;
        return;
    }
    tex.ent++;
}

uint8_t boss_big_tex(uint8_t ev, uint8_t arg) BANKED {
    (void)arg;
    switch (ev) {
    case BEV_SET:
        boss_art_set();
        tex.ent = 0;
        break;
    case BEV_LOAD:
        boss_art_load();
        break;
    case BEV_ENTER:                                         // (E9: after the warm-up)
        tex.ent = 1;
        return 1;
    case BEV_RESET:
        if (tex.ent) { boss_state = BS_JUMP; boss_xpose = BP_HIDE; }   // (the entrance: not on his bar yet)
        break;
    case BEV_INTRO:
        if (tex.ent) ent_frame();
        break;
    case BEV_DRAW:
        if (tex.ent) ent_draw();
        break;
    }
    return 0;
}
