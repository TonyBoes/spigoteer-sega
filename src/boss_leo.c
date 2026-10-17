// Leo the Lion, the jungle zoo's boss (docs/minigames_bosses.md 3.11; art approved 2026-10-11, round 2: the patron lion
// scaled up, crowned). His row is boss.c rows[8]: 32 px, step 80, push 8, gulp 30, hands 2, sip 60, meter 14.
//
// His roar, every LEO_EVERY frames of walking (boss_special_t counts them down):
//   1. TELL, LEO_TELL frames: the INHALE pose (the mane puffed out), "!!" (gen_boss leo `tiles` BANG at BG 246-247) in
//      the column right of him on his bar's wall rows (boss_cols[4]: a 32 px boss's 5th column is his special's, so
//      it is stamped with him in his palette and follows a push-back); he stands (BS_TELL). A second to stop throwing.
//   2. ROAR, LEO_ROAR frames: the ROAR pose and SFX_SHAKE; he stands (BS_SPECIAL). On its first frame:
//      - every regular walker all on the screen (on every bar) is pushed back LEO_PUSH px: the push-back's own movement
//        (PATRON_PUSHED, 1 px a frame) with no mug in his hand, never past ENTRY_X (where a push would serve him), so no
//        score, no served count, no thirst; when the push is used up he walks on (leo.mask: patrons.c would start his
//        drink, and he has none);
//      - the SHOCKWAVE starts (E6): from his right edge it sweeps right along every bar, LEO_WAVE px a frame, drawn as two
//        arcs a bar (OAM 30-37, the dancers' unused entries; assets/art/leo_fx.txt). Every FULL mug it passes, on any bar,
//        is blown back: it becomes a MUG_RETURN (boss.c boss_mugs: 1 px a frame to the right, caught by the bartender at
//        that bar's tap end like an empty, EMPTY score, nothing for his meter, and a life if it gets past: the Critic's
//        sent-back drink). A mug launched while the front is at the spout is blown at once.
//   3. The "!!" goes, he walks again, LEO_EVERY to the next roar.
// A catch during the tell or the roar shows GULP / WINCE as usual and his pose comes back after it; a push-back takes
// the "!!" along. A lost life ends a roar (he starts over walking).
// ENTRANCE (E6, on the fight's first start like Duke's: BEV_LOAD sets leo.ent, BEV_INTRO runs it, boss.c holds nothing):
// a flaming circus hoop appears over the left end of his bar, he flies in from off the left edge in an arc through it
// (his ROAR pose as sprites), lands on his bar at x 16 (boss_to_bar), roars (the wave, a visual only) and the hoop goes.
// While it plays he is BS_JUMP + BP_HIDE (no body, no catch), the bartender is held at bar 0's tap and nothing is poured.
// Test hooks (WRAM: his state is the struct leo_t in BOSS_OWN, not variables of his own): leo.phase is the spec's
// boss_roar (0 walking, 1 the tell, 2 the roar).
#pragma bank 255
#include "boss.h"
#include "boss_leo_art.h"
#include "boss_load.h"
#include "leo_fx_art.h"
#include "music.h"

#define BP_INHALE   BP_EXTRA         // gen_boss BOSSES leo extra: INHALE, ROAR
#define BP_ROAR     (BP_EXTRA + 1)
#define LEO_EVERY   420              // frames of walking between two roars
#define LEO_TELL     60              // the inhale and the "!!"
#define LEO_ROAR     30              // the roar
#define LEO_PUSH     16              // px every walker is pushed back
#define LEO_WAVE      5              // px a frame the shockwave's front moves (bar-local x)
#define WAVE_REACH   10              // a mug within this many px behind the front is blown (the front and a mug close at <= 6 a frame)
#define WAVE_GAP     14              // the trailing arc's distance behind the front
#define WAVE_END    176              // the front is off the bars
#define BANG_K       4               // boss_cols[] index of the "!!" column (right of his 4 columns)
#define BANG_BG      BOSS_ICE_BG     // its top tile (bottom: + 1)
#define BANG_NONE    255
#define FX_BUSY       4              // mugs alive from which the optional sprites (the trailing arc, the hoop) are left out
#define OAM_WAVE     (OAM_DANCERS + 2)   // (OAM 29 is the engine's hand mug; 37-39 its capacity indicator: Leo has 2 hands, so 38-39)   // OAM 30-37: the arcs (two a bar) or the entrance's leap and hoop (4 + 4)
#define OAM_WAVE_N   8
#if BOSS_ART_TILES * 2 > BOSS_HUD_BG - BOSS_ICE_BG || BOSS_ART_COLS != BANG_K
#error "Leo's !!: the extra BG tiles (246-251), a 32 px body"
#endif
#if LEO_FX_OBJ + LEO_FX_TILES > OBJ_CAP || NUM_BARS * 2 != OAM_WAVE_N || OAM_WAVE + OAM_WAVE_N > 40
#error "Leo's sprites: OBJ tiles 104-127, OAM 30-37"
#endif
typedef char leo_fx_clear_of_his_hats[(LEO_FX_OBJ >= OBJ_TOPPER + sizeof(boss_art_hat) / 16) ? 1 : -1];   // (his own topper frames, not BOSS_HATS_MAX: each fight loads only its own)

enum { LP_WALK, LP_TELL, LP_ROAR };

// The entrance: frame t = leo.ent - 1
#define ENT_FLY      8               // the hoop shows from 0; he flies from here
#define ENT_AIR     28               // frames in the air
#define ENT_LAND    (ENT_FLY + ENT_AIR)   // the landing frame: his BG body at x 16, the roar and its wave begin
#define ENT_END     (ENT_LAND + LEO_ROAR)
#define HOOP_X      28               // screen x of the hoop's left edge
#define HOOP_UP     27               // px its top is above his bar's top
#define FLY_X0      (-36)            // his x at the take-off (off the left edge), 16 on landing
#define FLY_LIFT    120              // the arc: lift = i * (28 - i) * 120 / 784 (30 px at the top)

typedef struct {
    uint8_t  phase;      // LP_* (the spec's boss_roar; tests)
    uint8_t  t;          // frames in the phase
    uint8_t  roars;      // roars this fight (tests)
    uint8_t  pushed;     // walkers the last roar pushed back (tests)
    uint8_t  blown;      // full mugs the waves have blown back this fight (tests)
    uint8_t  bang_col;   // screen column the "!!" is drawn at (BANG_NONE: not shown)
    uint16_t mask;       // bit p: regular p is sliding back from a roar (he walks on when the push is used up)
    uint8_t  ent;        // the entrance: 0 none (or over), else the next frame's number + 1 (tests)
    uint8_t  wave;       // the shockwave: 0 none, else frames since it began + 1 (tests)
    uint8_t  fx0;        // the front's bar-local x on its first frame
    uint8_t  vis;        // 1: the wave is only a picture (the entrance's landing)
} leo_t;
#define leo (*(leo_t *)BOSS_OWN)
#if 13 > BOSS_OWN_N
#error "Leo's state: BOSS_OWN_N"
#endif

// The "!!" at screen column c (BANG_NONE: off): the old and new columns recomposed (render.c stamps boss_cols[BANG_K]
// at boss_col + BANG_K).
static void bang_at(uint8_t c) {
    if (leo.bang_col != BANG_NONE) mark_dirty_attrs(boss_bar, leo.bang_col, leo.bang_col + 1);
    leo.bang_col = c;
    boss_cols[BANG_K] = c == BANG_NONE ? 0 : BANG_BG;
    if (c != BANG_NONE) mark_dirty_attrs(boss_bar, c, c + 1);
}

// ---- the sprites (OAM 30-37) ----
static void fx_clear(void) {
    uint8_t i;
    for (i = 0; i != OAM_WAVE_N; i++) shadow_OAM[OAM_WAVE + i].y = 0;
}

// Frame f's cells at screen (x, y) into OAM from *np (up to OAM_WAVE + OAM_WAVE_N): a cell off the screen is left out. prop:
// the palette. No line counting here (a frame of this is already close to the budget): the lines stay at 10 because only
// one arc a bar is ever drawn beside 4 or more mugs (a bar holds 6, the bartender 2, the topper 1) and the optional second
// arc and the hoop are left out then (mugs_live >= FX_BUSY).
static void fx_put(uint8_t *np, uint8_t f, int16_t x, uint8_t y, uint8_t prop) {
    const uint8_t *c = leo_fx_cells + ((uint16_t)leo_fx_first[f] << 2);
    uint8_t n = leo_fx_first[f + 1] - leo_fx_first[f], i = *np;
    int16_t cx;
    OAM_item_t *o;
    for (; n && i != OAM_WAVE + OAM_WAVE_N; n--, c += 4) {
        cx = x + 8 + c[0];
        if ((uint16_t)(cx - 1) >= 167) continue;
        o = shadow_OAM + i++;
        o->y = y + 16 + c[1]; o->x = (uint8_t)cx; o->tile = c[2]; o->prop = prop | c[3];
    }
    *np = i;
}

static uint8_t fx_pal(void) {
    return is_cgb ? OBJPAL_PATRON_C : S_PALETTE;
}

// ---- the shockwave ----
static void wave_begin(uint8_t vis) {
    leo.wave = 1;
    leo.vis = vis;
    leo.fx0 = boss_x + 28;
}

// One frame of the wave: blow the full mugs the front is passing, draw the arcs, end it when the front is off the bars.
static void wave_step(void) {
    uint16_t front;
    uint8_t i, b, n = OAM_WAVE, left, y, pal = fx_pal();
    if (!leo.wave) return;
    front = leo.fx0 + (uint16_t)LEO_WAVE * (leo.wave - 1);
    if (front >= WAVE_END) { leo.wave = 0; fx_clear(); return; }
    if (!leo.vis && mugs_live) {
        left = mugs_live;
        for (i = 0; i != MAX_MUGS && left; i++) {
            if (mug_state[i] == MUG_FREE) continue;
            left--;
            if (mug_state[i] == MUG_FULL && mug_x[i] <= front && mug_x[i] + WAVE_REACH >= front) {
                mug_state[i] = MUG_RETURN;                // (boss.c boss_mugs: 1 px a frame back to the bartender)
                leo.blown++;
            }
        }
    }
    fx_clear();
    for (b = 0; b != NUM_BARS; b++) {
        y = bar_oam_y[b] - 16 - 4;                        // (fx_put adds the 16: screen y of the arc's top)
        fx_put(&n, FX_ARC1, front, y, pal);
        if (front >= leo.fx0 + WAVE_GAP && mugs_live < FX_BUSY) fx_put(&n, FX_ARC2, front - WAVE_GAP, y, pal);
    }
    leo.wave++;
}

static void to_walk(void) {
    leo.phase = LP_WALK; leo.t = 0;
    boss_special_t = LEO_EVERY;
    boss_xpose = 0;
    if (boss_state == BS_TELL || boss_state == BS_SPECIAL) boss_state = BS_WALK;
    if (leo.bang_col != BANG_NONE) bang_at(BANG_NONE);
}

static void to_tell(void) {
    leo.phase = LP_TELL; leo.t = 0;
    boss_special_t = 0;
    boss_xpose = BP_INHALE;
    bang_at(boss_col + BANG_K);
}

// The roar's first frame: one pass over the patron pool, and the wave begins.
static void roar(void) {
    uint8_t p, x, d;
    uint16_t bit = 1;
    leo.phase = LP_ROAR; leo.t = 0;
    leo.roars++;
    boss_xpose = BP_ROAR;
    SFX(SFX_SHAKE);
    leo.pushed = 0;
    for (p = 0; p != MAX_PATRONS; p++, bit <<= 1) {
        if (patron_state[p] == PATRON_WALKING) {
            x = patron_x[p];
            if (patron_aux[p] || patron_dist[p] || x <= ENTRY_X) continue;   // (still coming in at the left end)
            d = x - ENTRY_X;
            patron_state[p] = PATRON_PUSHED;
            patron_aux[p] = d > LEO_PUSH ? LEO_PUSH : d;   // (never to ENTRY_X and beyond: that push would serve him)
            patron_frac[p] = 0;
            patron_timer[p] = 0;
            leo.mask |= bit;
            leo.pushed++;
        }
    }
    wave_begin(0);
}

// The walkers the roar pushed: a push used up (patrons.c start_drinking, with no mug) -> he walks on.
static void slid(void) {
    uint8_t p;
    uint16_t bit = 1;
    for (p = 0; p != MAX_PATRONS; p++, bit <<= 1) {
        if (!(leo.mask & bit) || patron_state[p] == PATRON_PUSHED) continue;
        leo.mask &= ~bit;
        if (patron_state[p] == PATRON_DRINKING && patron_mug[p] == NO_SLOT) {
            patron_state[p] = PATRON_WALKING;             // (patrons.c walk_on)
            patron_timer[p] = 0;
            patron_aux[p] = 0;
        }
    }
}

// ---- the entrance ----
// BEV_INTRO, every frame while intro_timer runs: its clock, its sprites, what happens at its frames. The player's input is
// undone (the bartender stays at bar 0's tap, nothing is poured) until it is over.
static void ent_frame(void) {
    uint8_t t = leo.ent - 1, n = OAM_WAVE, pal = fx_pal(), top = bar_oam_y[boss_bar] - 16, i;
    int16_t x;
    fill_timer = 0; fill_stage = 0;                          // (the bartender stays where he is: main.c skips his input while he is held)
    bartender_frame = BT_IDLE; catch_pose = 0; bt_bob = 0;
    if (t < ENT_LAND) {
        intro_timer = INTRO_FRAMES;                           // (held: the intro's 90 frames start at the landing)
        fx_clear();
        if (t >= ENT_FLY) {                                   // he flies in, over the hoop (drawn first: on top)
            i = t - ENT_FLY;
            x = FLY_X0 + (int16_t)((52 * (uint16_t)i) / ENT_AIR);
            fx_put(&n, FX_LEAP, x, top - (uint8_t)(((uint16_t)i * (ENT_AIR - i) * FLY_LIFT) / 784), pal);
        }
        if (mugs_live < FX_BUSY) fx_put(&n, (t / 3) & 1 ? FX_HOOP_B : FX_HOOP_A, HOOP_X, top - HOOP_UP, pal);
    } else {
        if (t == ENT_LAND) {
            fx_clear();                                       // (the hoop burns out)
            intro_timer = INTRO_FRAMES - 1;                   // (as the level's first frame leaves it: the fight starts 89 frames on)
            boss_xpose = BP_ROAR;
            boss_to_bar(boss_bar, 16);                        // his BG body (the ROAR pose) at x 16
            SFX(SFX_SHAKE);
            wave_begin(1);
        }
        wave_step();
        if (t >= ENT_END) {                                   // the wave is off: he stands there, walking from now
            leo.wave = 0; fx_clear();
            boss_state = BS_WALK;                             // (E9: over: boss.c starts the fight)
            to_walk();
            boss_to_bar(boss_bar, 16);                        // (the pose back to WALK)
            leo.ent = 0;
            return;
        }
    }
    leo.ent++;
}

uint8_t boss_leo(uint8_t ev, uint8_t arg) BANKED {
    (void)arg;
    switch (ev) {
    case BEV_SET:
        boss_art_set();
        leo.roars = leo.pushed = leo.blown = 0;
        leo.mask = 0;
        leo.ent = leo.wave = 0;
        leo.bang_col = BANG_NONE;                         // (boss_set cleared boss_cols)
        boss_returns = 1;                                 // (boss.c boss_mugs moves every MUG_RETURN)
        to_walk();
        break;
    case BEV_RESET:
        if (leo.mask) slid();
        leo.wave = 0; fx_clear();
        to_walk();
        if (leo.ent) { boss_state = BS_JUMP; boss_xpose = BP_HIDE; }   // (the entrance: not on his bar yet)
        break;
    case BEV_LOAD:
        boss_art_load();
        set_bkg_data(BANG_BG, BOSS_ART_TILES * 2, boss_art_tiles);
        set_sprite_data(LEO_FX_OBJ, LEO_FX_TILES, leo_fx_tiles);
        break;
    case BEV_ENTER:                                       // (E9: after the warm-up)
        leo.ent = 1;
        return 1;
    case BEV_INTRO:
        if (leo.ent) ent_frame();
        break;
    case BEV_ROOM:                                        // through the roar he sends back what reaches him: no room
        return leo.phase == LP_ROAR ? ROOM_FREE(0) : 0;
    case BEV_TELL:
        if (leo.phase == LP_WALK) to_tell();
        break;
    case BEV_OUTRO:
        leo.wave = 0; fx_clear();
        to_walk();
        break;
    case BEV_FRAME:
        if (leo.t != 255) leo.t++;
        if (leo.mask) slid();
        switch (leo.phase) {
        case LP_WALK:
            if (boss_special_t && !--boss_special_t) to_tell();
            break;
        case LP_TELL:
            if (leo.t >= LEO_TELL) roar();
            break;
        case LP_ROAR:
            if (leo.t >= LEO_ROAR) to_walk();
            break;
        }
        wave_step();
        if (leo.bang_col != BANG_NONE && leo.bang_col != (uint8_t)(boss_col + BANG_K)) bang_at(boss_col + BANG_K);
        if (leo.phase == LP_TELL && boss_state == BS_WALK) boss_state = BS_TELL;   // (a gulp is over: he stands again)
        else if (leo.phase == LP_ROAR && (boss_state == BS_WALK || boss_state == BS_TELL)) boss_state = BS_SPECIAL;
        break;
    }
    return 0;
}
