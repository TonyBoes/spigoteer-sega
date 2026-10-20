// CLASSIC's end-of-level antics (the three modes, P6; plan: the modes proposal C10; art owner-approved 2026-10-11,
// assets/art/antics/). After LEVEL CLEAR in CLASSIC the bartender, where he stands, tosses a glass in the air, and it
// ends one of six ways at random: he backheels it and it smashes; he backheels it and hurts his foot (he hops); it hits
// a dove, which falls on his head; it lands upside down on his head; it crashes on his head (dazed, stars); or he
// drinks two beers instead. Then the bonus round or the next level, as before.
//
// The clear in CLASSIC: ANT_WAIT frames of the LEVEL CLEAR banner and jingle (the banner lies over bar 1's rows, and
// hides the sprites there), ANT_PRE frames of beat (he stands with the glass in hand, a drumroll builds; owner 2026-10-15),
// the ending (ANT_LEN frames, every ending finishes inside them; a cymbal crash on its result), ANT_HOLD frames on its
// last picture. Nothing else moves in a clear (every patron is served), so the holds cost the player nothing.
// Meanwhile the 32 OBJ tiles (build/antics_art.h) go over the show's (OBJ_DANCER; the next level load or the
// bonus round puts their own back), 8 a frame through GBDK's STAT-waiting copy (safe with the LCD on).
// Sprites: OAM 0-3 him, 5 the glass / its shards, 6 the dove, 7-8 the stars or the two beers: at most 6 on a line. All
// drawn at bar-local x and mirrored on an R bar (168 - X, S_FLIPX), like the play's own sprites (mirror.c).
// The ending comes from its own random byte (antics_rng; the game's next_rand sequence is not touched, so the bonus
// round after a clear plays as it did). Test hook: antics_force 1..6 plays ending n - 1.
#pragma bank 255
#include <gb/gb.h>
#include <stdint.h>

#include "game.h"
#include "music.h"
#include "antics_art.h"

extern uint8_t overlay_on;

#define ANT_WAIT   60
#define ANT_PRE    42               // the beat before the trick (owner 2026-10-15): he poses with the glass, a drumroll builds
#define ANT_LEN   210
#define ANT_HOLD   30
#define ANT_TOSS   52               // the shared toss (every ending but the beers)

enum { AE_SMASH, AE_FOOT, AE_BIRD, AE_HAT, AE_CRASH, AE_BEER, AE_N };
enum { P_IDLE, P_FAIL, P_KICK, P_HOP, P_DAZED, P_DRINK };

uint8_t  antics_force;              // test hook: 1..6 plays ending n - 1 (0: random)
uint8_t  antics_rng = 0x5D;         // the endings' own xorshift
uint8_t  antics_end;                // the ending of this clear (AE_*)
uint16_t antics_t;                  // frames since LEVEL CLEAR
uint8_t  antics_loaded;             // OBJ tiles copied so far

static int16_t bx;                  // where he stands: bar-local x, screen y of his top
static uint8_t by, an_r;            // an_r: his bar is R (drawn mirrored)

#define A_T(n)   ((uint8_t)(OBJ_DANCER + (n)))
#define BT_T(f)  ((uint8_t)(OBJ_BARTENDER + BT_PIC(f) * BARTENDER_TILES_PER_FRAME))
#define FX       S_FLIPX
#define FY       S_FLIPY

// one 8x16 entry at bar-local x, screen y (its top); off the screen: hidden
static void ent(uint8_t k, int16_t x, int16_t y, uint8_t tile, uint8_t prop) {
    OAM_item_t *o = shadow_OAM + k;
    if (x < -7 || x > 159 || y < -15 || y > 143) { o->y = 0; return; }
    o->y = (uint8_t)(y + 16); o->x = (uint8_t)(x + 8); o->tile = tile; o->prop = prop;
    if (an_r) { o->x = 168 - o->x; o->prop ^= S_FLIPX; }
}

static void hide(uint8_t k) { shadow_OAM[k].y = 0; }

// him in pose p, dx / dy from where he stands (art facing the patrons' end, as draw_bartender with facing 0)
static void pose(uint8_t p, int8_t dx, int8_t dy) {
    static const uint8_t top[6] = { BT_T(BT_IDLE), BT_T(BT_FAIL), A_T(ANT_KICK), A_T(ANT_HOP), A_T(ANT_DAZED), A_T(ANT_DRINK) };
    static const uint8_t bot[6] = { BT_T(BT_IDLE) + 4, BT_T(BT_FAIL) + 4, A_T(ANT_KICK) + 4, A_T(ANT_HOP) + 4,
                                    BT_T(BT_IDLE) + 4, BT_T(BT_FAIL) + 4 };
    int16_t x = bx + dx, y = (int16_t)by + dy;
    uint8_t t = top[p], b = bot[p], pr = OBJPAL_BARTENDER;
    ent(0, x, y, t, pr); ent(1, x + 8, y, t + 2, pr);
    ent(2, x, y + 16, b, pr); ent(3, x + 8, y + 16, b + 2, pr);
}

// the empty glass (the venue's empty drink), its shards (the crash frames), the full drink and its drinking poses
static void glass(int16_t x, int16_t y, uint8_t flip) { ent(5, bx + x, (int16_t)by + y, spr_empty_t, spr_empty_p ^ flip); }
static void shard(uint8_t f, int16_t x, int16_t y) { ent(5, bx + x, (int16_t)by + y, OBJ_GLASS + f, spr_empty_p); }
static void bird(uint8_t f, int16_t x, int16_t y, uint8_t flip) { ent(6, bx + x, (int16_t)by + y, A_T(f), OBJPAL_BARTENDER | flip); }
static void beer(uint8_t k, uint8_t f, int16_t x, int16_t y, uint8_t flip) {   // f: 0 full, 1 / 2 tilted, 3 empty
    uint8_t t, p;
    if (f == 0) { t = spr_full_t; p = spr_full_p; }
    else if (f == 3) { t = spr_hempty_t; p = spr_hempty_p; }
    else { t = OBJ_MUG_DRINK + f * 2; p = is_cgb ? OBJPAL_MUG_FULL : 0; }
    ent(k, bx + x, (int16_t)by + y, t, p ^ flip);
}

static int16_t lerp(int16_t a, int16_t b, uint8_t n, uint8_t d) { return a + (int16_t)((b - a) * (int16_t)n) / d; }
static int16_t fall(int16_t a, int16_t b, uint8_t n, uint8_t d) {      // from a down to b (b > a, d <= 24), speeding up
    return a + (int16_t)((uint16_t)(b - a) * (uint16_t)(n * n) / (uint16_t)(d * d));   // ((n / d) squared; 16-bit only)
}

static void sfx_at(uint8_t e, uint8_t at, uint8_t s) { if (e == at) SFX(s); }

// The drumroll and the cymbal crash (owner 2026-10-15). Noise channel 4, written here: the sound bank (music.c, bank 2) has
// 6 B free, too little for two effect definitions, and nothing else uses channel 4 now (the clear jingle has no channel-4
// part and no groove; its last notes are the only music left over the roll, and it ends before the trick).
// roll: a hit every 2 frames from beat frame 4 to 39 (18 hits), the volume growing 5 -> 15 (envelope fast decay), the
// noise clock alternating between two snare-like values.
static void roll(uint8_t b) {
    uint8_t k;
    if (b < 4 || b >= ANT_PRE - 2 || (b & 1)) return;
    k = (b - 4) >> 1;
    NR41_REG = 0;
    NR42_REG = (uint8_t)((5 + ((k * 10) >> 4)) << 4) | 1;
    NR43_REG = (k & 1) ? 0x33 : 0x23;
    NR44_REG = 0x80;
}
// the crash on the result: full volume, a slow decay (~0.7 s), a high hissing 7-bit-LFSR clock
static void cymbal(void) { NR41_REG = 0; NR42_REG = 0xF3; NR43_REG = 0x19; NR44_REG = 0x80; }
static void sting(uint8_t e, uint8_t at) { if (e == at) cymbal(); }

// d = 0..ANT_TOSS-1: he tosses the glass (fail pose), it rises ~32 px easing out, tumbling (alternate flips), and hangs
// upside down at the top. The dove (ending AE_BIRD) flies in from the patrons' side meanwhile.
static void toss(uint8_t d) {
    static const uint8_t tumble[4] = { 0, FX, FX | FY, FY };
    uint8_t k;
    if (d < 12) { pose(P_FAIL, 0, 0); glass(-5, -4, 0); }
    else if (d < 42) {
        k = d - 12;
        pose(P_IDLE, 0, 0);
        glass(lerp(-5, 4, k, 30), -4 - 32 + (int16_t)((uint16_t)32 * (30 - k) * (30 - k) / 900), tumble[(k >> 2) & 3]);
    } else { pose(P_IDLE, 0, 0); glass(4, -36, FY); }
    if (antics_end != AE_BIRD || d < 12) { hide(6); return; }
    if (d < 42) bird(((d / 6) & 1) ? ANT_BIRD_DOWN : ANT_BIRD_UP, lerp(-46, -3, d - 12, 30), -34, 0);
    else bird(ANT_BIRD_DOWN, -3, -35, 0);
}

static void behind(uint8_t e) {                         // the glass falls behind him to his heel (20 frames)
    pose(P_IDLE, 0, 0);
    glass(lerp(4, 15, e, 20), fall(-36, -2, e, 20), FY);
}

static void smash(uint8_t e) {
    if (e < 20) behind(e);
    else if (e < 28) { pose(P_KICK, 0, 0); glass(15, -2, 0); }
    else if (e < 38) { pose(P_KICK, 0, 0); shard(GLASS_SHATTER, 18, -3); sting(e, 28); }
    else { pose(P_FAIL, 0, 0); shard(GLASS_SETTLE, 18, 1); }
}

static void foot(uint8_t e) {
    uint8_t h, i, up;
    if (e < 20) { behind(e); return; }
    if (e < 28) { pose(P_KICK, 0, 0); glass(15, -2, 0); sfx_at(e, 20, SFX_CATCH); return; }
    if (e < 38) { pose(P_KICK, 0, 0); glass(lerp(15, 19, e - 28, 10), lerp(-2, 1, e - 28, 10), 0); return; }
    glass(19, 1, 0);                                     // (intact on the counter behind him)
    h = e - 38; i = 0;
    while (h >= 30 && i < 3) { h -= 30; i++; }           // hop i (4 of them, 30 frames each), then he stands
    up = h < 15 && e < 38 + 120;
    pose(P_HOP, -(int8_t)(2 * i) - (up ? 0 : 2), up ? -3 : 0);
    sting(e, 38); sfx_at(e, 38, SFX_LIFE);
}

static void dove(uint8_t e) {
    if (e < 24) {
        pose(P_IDLE, 0, 0);
        bird(ANT_BIRD_STUN, lerp(-3, 4, e, 24), fall(-35, -8, e, 24), FY);
        glass(lerp(4, -16, e, 24), fall(-36, -3, e, 24), FX);
        sfx_at(e, 0, SFX_CATCH);
        return;
    }
    bird(ANT_BIRD_STUN, 4, -8, 0);                       // on his head
    if (e < 34) { pose(P_IDLE, 0, 0); shard(GLASS_SHATTER, -16, -3); sting(e, 24); }
    else { pose(e < 74 ? P_IDLE : P_FAIL, 0, 0); shard(GLASS_SETTLE, -16, 1); }
}

static void hat(uint8_t e) {
    if (e < 24) { pose(P_IDLE, 0, 0); glass(4, fall(-36, -7, e, 24), FY); return; }
    pose(e < 64 ? P_IDLE : P_FAIL, 0, 0);
    glass(4, e < 28 ? -6 : -7, FY);                      // (a 1 px squash as it lands)
    sting(e, 24); sfx_at(e, 24, SFX_CATCH);
}

static void crash(uint8_t e) {
    uint8_t s, tw;
    if (e < 20) { pose(P_IDLE, 0, 0); glass(4, fall(-36, -10, e, 20), FY); return; }
    if (e < 30) { pose(P_DAZED, 0, 0); shard(GLASS_SHATTER, 4, -10); sting(e, 20); return; }
    e -= 30;
    s = (e >> 4) & 1;                                    // he sways a pixel every 16 frames
    tw = (e >> 3) & 1 ? FY : 0;                          // the stars twinkle every 8
    pose(P_DAZED, s, 0);
    shard(GLASS_SETTLE, -7, 1);
    ent(7, bx + s, (int16_t)by - 11, A_T(ANT_STARS), OBJPAL_BARTENDER | tw);
    ent(8, bx + s + 8, (int16_t)by - 11, A_T(ANT_STARS), OBJPAL_BARTENDER | FX | tw);
}

static void beers(uint8_t d) {                           // no toss: cheers, two gulps, "ahh"
    hide(5); hide(6);
    if (d < 40) { pose(P_FAIL, 0, 0); beer(7, 0, -6, 2, 0); beer(8, 0, 14, 2, FX); return; }
    if (d < 95) { pose(P_DRINK, 0, 0); beer(7, d < 70 ? 1 : 2, -1, 3, FX); beer(8, 0, 14, 2, FX); return; }
    if (d < 105) { pose(P_FAIL, 0, 0); beer(7, 3, -12, 4, 0); beer(8, 0, -6, 2, 0); return; }
    if (d < 160) { pose(P_DRINK, 0, 0); beer(7, 3, -12, 4, 0); beer(8, d < 135 ? 1 : 2, -1, 3, FX); return; }
    pose(P_FAIL, 0, 0); beer(7, 3, -12, 4, 0); beer(8, 3, -20, 4, 0);
    sting(d, 160); sfx_at(d, 160, SFX_SERVE);
}

// enter_level_clear (main_cold.c), CLASSIC: the ending, where he stands
void antics_start(void) BANKED {
    uint8_t r = antics_rng, e;
    r ^= r << 3; r ^= r >> 5; r ^= r << 1;               // (a full-period 8-bit xorshift)
    antics_rng = r;
    e = r;
    while (e >= AE_N) e -= AE_N;
    antics_end = antics_force ? antics_force - 1 : e;
    antics_t = 0; antics_loaded = 0;
    bx = bartender_x; by = bar_oam_y[bar] - 16 + BT_DY;
    an_r = (bar_dirs & bar_bit[bar]) != 0;
}

// every GS_LEVEL_CLEAR frame in CLASSIC (main.c): 1 when the clear is over
uint8_t antics_frame(void) BANKED {
    uint16_t t = antics_t++;
    uint8_t d, k;
    if (antics_loaded < ANT_TILES) {
        set_sprite_data(OBJ_DANCER + antics_loaded, 8, ant_tiles + (uint16_t)antics_loaded * 16);
        antics_loaded += 8;
    }
    if (t < ANT_WAIT) return 0;
    if (t >= ANT_WAIT + ANT_PRE + ANT_LEN) return t + 1 >= ANT_WAIT + ANT_PRE + ANT_LEN + ANT_HOLD;   // (its last picture stays)
    DISABLE_OAM_DMA;                                     // (no half-drawn OAM on the screen)
    if (t == ANT_WAIT) {                                 // the banner goes, the play's sprites with it
        overlay_on = 0;
        for (k = 4; k < 40; k++) hide(k);
        oam_touched();
    }
    d = (uint8_t)(t - ANT_WAIT);
    if (d < ANT_PRE) {                                   // the beat: he holds the first picture (the glass in hand), the roll builds
        if (antics_end == AE_BEER) beers(0); else toss(0);
        roll(d);
        ENABLE_OAM_DMA;
        return 0;
    }
    d -= ANT_PRE;
    if (antics_end == AE_BEER) beers(d);
    else if (d < ANT_TOSS) toss(d);
    else {
        d -= ANT_TOSS;
        if (antics_end == AE_SMASH) smash(d);
        else if (antics_end == AE_FOOT) foot(d);
        else if (antics_end == AE_BIRD) dove(d);
        else if (antics_end == AE_HAT) hat(d);
        else crash(d);
    }
    ENABLE_OAM_DMA;
    return 0;
}
