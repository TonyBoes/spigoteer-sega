// The mosh pit: The Chrome Cow's twist (chapter 7's Happy hour and Last call; docs/minigames_bosses.md section 9, the
// one deliberate exception to "patrons overlap, never shove"). The owner's words: a served patron sliding back bumps
// the one behind him, who is shoved forward; clear the back one first while the front one drinks.
//
// The rule (9.2):
//   - Bump: after a pushed patron P's 1 px step (patrons.c push_px), the first plain walker Q of his bar behind him
//     with 0 <= P.x - Q.x <= MOSH_CONTACT is bumped: walking, all on the screen (patron_aux 0, x >= ENTRY_X), not
//     watching the show, not being shoved or staggering already. Of several, the nearest (the highest x). Drinkers,
//     pushed and leaving patrons are never bumped. One bump per push: patron_mosh[P] is set by it and cleared when P
//     catches his next glass (caught -> mosh_caught).
//   - Shove: Q goes MOSH_SHOVE_PX toward the tap at MOSH_SPEED px a frame, then staggers on the spot for MOSH_STAGGER
//     frames and walks on. A shove never takes his left edge past mosh_limit (88 Happy hour, 72 Last call: 32 / 48 px
//     short of the tap, so a shove never costs a life by itself), and a step that would put three patrons on one tile
//     column ends it there (walker_pixel's rule). A Q already at the limit is only jostled: the cue, no move. A shove
//     is not a push: Q bumps nobody, so there are no chains; P is not slowed.
//   - The cue (9.3): the shove itself, a milk splash on the counter under the contact column for MOSH_SPLASH frames
//     (venue.splash_tile, assets/art/splash/biker.txt, written through the VBlank queue and put back after), and a
//     channel-4 rattle (SFX_SHAKE).
// Untouched: the fair-empties schedule (a shove moves a walker, never a drinker), served, score, tips, lives.
// Off everywhere else: story.c sets it per shift from the goal's twist bits (gen_story TWISTS), and a boss fight or
// arcade sets 0 (boss_goal's twist is 0; start_new_game).
#pragma bank 255
#include <gb/gb.h>
#include <stdint.h>

#include "game.h"
#include "music.h"
#include "story.h"

extern uint8_t bar_list[NUM_BARS][MAX_PATRONS], bar_n[NUM_BARS];
void build_lists(void);

uint8_t mosh_on;                       // the mosh pit is on (this shift)
uint8_t mosh_limit;                    // a shove never takes a walker's left edge past this x
uint8_t mosh_count;                    // bumps this shift (shoves and jostles; tests)
uint8_t patron_shove[MAX_PATRONS];     // px of his shove still to go
uint8_t patron_stag[MAX_PATRONS];      // frames of his stagger still to go
uint8_t patron_mosh[MAX_PATRONS];      // 1: his push has bumped someone (cleared by his next catch)
uint8_t mosh_splash_t;                 // frames left of the counter splash (0: none on screen)
static uint8_t splash_x, splash_y;     // its tile

void mosh_set(uint8_t twist, uint8_t limit) BANKED {
    uint8_t p;
    mosh_on = (twist & TWIST_MOSH) && venue.splash_tile ? 1 : 0;   // (the venue's bar set has the splash tile)
    mosh_limit = limit;
    mosh_count = 0; mosh_splash_t = 0;
    for (p = 0; p < MAX_PATRONS; p++) patron_shove[p] = patron_stag[p] = patron_mosh[p] = 0;
}

// The counter's own tile back where the splash was (the bar map is the same for every bar).
static void splash_off(void) {
    vq_add(0, &venue.bar_map[BAR_COUNTER_DROW * 20 + splash_x], splash_x, splash_y, 1);
    mosh_splash_t = 0;
}

static void splash_on(uint8_t b, uint8_t x) {
    if (mosh_splash_t) splash_off();
    splash_x = x >> 3;
    if (splash_x > 16) splash_x = 16;            // (the wall runs to column 16: the spout and keg columns stay)
    splash_y = BAR_COUNTER_ROW(b);
    vq_add(0, &venue.splash_tile, splash_x, splash_y, 1);
    mosh_splash_t = MOSH_SPLASH;
}

void mosh_bump(uint8_t p) BANKED {
    const uint8_t *q;
    uint8_t n, s, x, d, best = NO_SLOT, bx = 0, b = patron_bar[p];
    if (!lists_ok) build_lists();
    x = patron_x[p];
    q = bar_list[b];
    for (n = bar_n[b]; n; n--) {
        s = *q++;
        if (s == p || patron_state[s] != PATRON_WALKING || patron_aux[s] || patron_dist[s]) continue;
        if (patron_shove[s] | patron_stag[s]) continue;
        d = patron_x[s];
        if (d < ENTRY_X || d > x || (uint8_t)(x - d) > MOSH_CONTACT) continue;
        if (best == NO_SLOT || d > bx) { best = s; bx = d; }
    }
    if (best == NO_SLOT) return;
    patron_mosh[p] = 1;                          // his one bump for this push
    mosh_count++;
    if (bx < mosh_limit) patron_shove[best] = MOSH_SHOVE_PX;   // (at the limit: jostled only)
    else patron_stag[best] = MOSH_STAGGER;
    splash_on(b, x);
    SFX(SFX_SHAKE);
}

// A shoved walker: MOSH_SPEED px a frame toward the tap until the shove is used up, the limit is reached or a step would
// put three patrons on one tile column; then the stagger (on the spot) counts down. walking_step redraws him after.
void mosh_step(uint8_t p) BANKED {
    uint8_t i, x;
    if (!patron_shove[p]) { patron_stag[p]--; return; }
    for (i = 0; i < MOSH_SPEED; i++) {
        x = patron_x[p];
        if (x >= mosh_limit || (!(x & 7) && col_scan(patron_bar[p], (x >> 3) + 2, p) >= 2)) { patron_shove[p] = 0; break; }
        patron_x[p] = x + 1;
        if (!--patron_shove[p]) break;
    }
    if (!patron_shove[p]) patron_stag[p] = MOSH_STAGGER;
}

void mosh_caught(uint8_t p) BANKED {
    patron_shove[p] = patron_stag[p] = patron_mosh[p] = 0;
}

void mosh_frame(void) BANKED {
    if (mosh_splash_t && !--mosh_splash_t) splash_off();
}
