// THE POUR-OFF (src/po.c): the story's finale race against Dregs. Its state lives in the mini-game union (src/mg.h, over
// story.c's backdrop buffer: no new WRAM global); the tests read it at story_scratch + offset (tests/po_helpers.py).
#ifndef PO_H
#define PO_H
#include <stdint.h>

#define PO_SEATS       12       // 3 a bar: x 40, 72, 104
#define PO_MUGS        16       // at most 4 a bar (both directions, sliding and held)
#define PO_WIN         20       // the race: first to this
#define PO_LIVES        3

enum { PS_EMPTY, PS_THIRSTY, PS_DRINKING };                    // a seat
enum { PM_FREE, PM_FULL, PM_HELD, PM_EMPTY, PM_BREAK };       // a mug
enum { PD_IDLE, PD_THINK, PD_FILL, PD_SLIDE, PD_WAIT };        // Dregs's state
enum { PR_PLAY, PR_WIN, PR_DREGS, PR_LIVES };                  // how it ended (po.res)
// the knobs (po.tune[], copied from the const table at entry: a test may poke them)
enum { PT_THINK0, PT_THINK15, PT_LEAD, PT_TRAIL, PT_REACT, PT_AHEAD, PT_COMIC, PT_SLIP };

struct po_seat {                // 7 bytes
    uint8_t st;                 // PS_*
    uint8_t t;                  // thirsty: patience, 2 frames a tick (240: 480 frames); drinking: frames drunk
    uint8_t v;                  // the patron's look 0..2 (the crowd table's)
    uint8_t who;                // drinking: who slid the drink: 0 you, 1 Dregs
    uint8_t pf;                 // drinking: the drink was a PERFECT pour
    uint8_t sh;                 // 1: drawn swaying (2 px over)
    uint8_t dirty;              // 1: its BG columns are to be queued again
};
struct po_mug {                 // 5 bytes
    uint8_t st;                 // PM_*
    uint8_t x;                  // screen px of its left edge
    uint8_t bar;
    uint8_t own;                // 0 yours, 1 Dregs's
    uint8_t aux;                // full: 1 PERFECT; held: its seat; empty / break: frames since
};
struct po_you {                 // the Spigoteer (main.c play_frame's variables)
    uint8_t x, frac, bar, facing, frame, fill, pour_t, pq, slide, catch_pose, walk_t, walk_ph, bob, hold, at_tap;
    uint8_t score, pour_bar;
};
struct po_dregs {
    uint8_t x, bar, frame, st, t, tbar, react, rbar, slip, catch_pose, hold, score;
};

struct po_state {               // tests/po_helpers.py: offsets by order (po_state_fits in src/po.c checks the ones it reads)
    uint8_t res;                // +0 PR_*
    uint8_t started;            // +1 the first play frame has put the banner rows back
    uint8_t spawn_t;            // +2 frames to the next patron
    uint8_t note_t;             // +3 frames left of the banner note (THANKS ...)
    uint8_t anim;               // +4 frames counted
    uint8_t cue_t, cue_x, cue_y;   // +5 the PERFECT cue (frames left; OAM x, y)
    uint8_t served;             // +8 patrons served in all (the spawn interval's clock, tests)
    uint8_t hudq;               // +9 1: the race score on the HUD is to be queued
    uint8_t cue_ok;             // (the cue fits on its lines: counted every 4th frame)
    uint8_t cnt[4];             // +11 mugs on each bar (the one pass over the mugs, mugs_step, counts them for the next frame)
    uint8_t dfull[4];           // +15 Dregs's full drinks in flight on each bar
    uint8_t eta, ebar;          // +19 his nearest empty: frames until it reaches his end (255: none), its bar
    uint8_t tune[8];            // +21 the knobs
    struct po_you y;            // +29
    struct po_dregs d;          // +29 + 17 = +46
    struct po_seat seat[PO_SEATS];
    struct po_mug mug[PO_MUGS];
    uint8_t sbuf[PO_SEATS][6];  // a seat's two rows of 3 tiles (VBlank queue source)
    uint8_t sattr[PO_SEATS][6]; // and its CGB attributes (per row)
    uint8_t hud[7];             // "Y12 D10" (VBlank queue source)
    uint8_t wall[2][20], wattr[2][20], hattr[20];   // the stage rows the banner covers, as they are; the HUD's colours
};

#endif
