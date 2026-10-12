// Duke, the Chrome Cow's boss (docs/minigames_bosses.md 3.12; art approved 2026-10-12, round 6: H2's leather back with H1's
// forked, braided beard). His row is boss.c rows[6]: 40 px, start 16, bar 1, step 0 (the engine's stomp is off), push 16,
// gulp 20, hands 2, sip 45, meter 12; his helmet is the topper (OBJ 7: red with a white stripe, set here).
//
// Owner change to the design: he STANDS behind the bar like Big Tex, with NO bike in the fight (the bike belongs to his
// entrance, which is not built). The doc's bike behaviours became standing ones:
//   IDLE   after his entry, his last catch or his last lurch: IDLE_150 frames while his meter is 12-9, 120 at 8-5, 90 at
//          4-1 (the shake is nearly full and he gets impatient). The idle pose "shakes with the engine": WALK / STOMP
//          every 8 frames (the topper bobs with STOMP).
//   REV    the tell, DUKE_REV 50 frames: he winds an invisible throttle (TELL1 / TELL2 every 8 frames: his fist at
//          shoulder height twisting, motion arcs, a roaring mouth), SFX_SHAKE, the helmet jumping 1 px every 4 frames
//          (the topper's HAT_BOB frame is the 1 px lower one); he stands (BS_TELL).
//   LURCH  16 px in 8 frames (two boss_advance hops 4 frames apart), the TELL2 pose, then IDLE again from 0. The doc's
//          exhaust puffs, black smoke and entry skid belong to the bike and are not built.
// A catch: the common one (meter -1, push 16 px = two hops, the gulp 20 frames), and the idle clock starts again from 0.
// A catch during the REV stalls him: the lurch is off; he shows WINCE while pushed and then GULP, 20 frames in all
// (DUKE_STALL), then IDLE from 0. Landing a glass on the first frame of the rev always beats it (40 frames to reach him).
// His gang: the regulars come in the venue's Last call "chord" (three bars at once, a breather, three more) on the three
// bars that are not his, at the boss fight's spawn interval; no mosh pit (boss.c sets the twist to 0).
// Test hooks (WRAM: his state is the struct duke_t in BOSS_OWN, no variable of his own): duke.phase, duke.t.
#pragma bank 255
#include "boss.h"
#include "boss_duke_art.h"
#include "boss_load.h"
#include "music.h"
#include "story.h"

extern uint8_t pat_pos, pat_buf[STORY_PAT_MAX];   // (story.c) the arrival pattern patrons.c follows while pat_len

#define BP_TELL1     BP_EXTRA           // gen_boss BOSSES duke extra: TELL1, TELL2
#define BP_TELL2     (BP_EXTRA + 1)
#define IDLE_HI      150                // meter 12-9
#define IDLE_MID     120                // 8-5
#define IDLE_LO       90                // 4-1
#define DUKE_REV      50
#define DUKE_HOP       4                // frames per 8 px of the lurch
#define DUKE_LURCH     8                // 16 px
#define DUKE_STALL    20
#define POSE_FRAMES    8                // the idle shake and the tell's two poses
#define HAT_DOWN       2                // topper tile offset: HAT_BOB, 1 px lower
#define CHORD_N        6
#if BOSS_ART_COLS != 5 || CHORD_N > STORY_PAT_MAX
#error "Duke: a 40 px body, the chord fits the pattern buffer"
#endif

enum { DP_IDLE, DP_REV, DP_LURCH, DP_STALL };

typedef struct {
    uint8_t phase;      // DP_* (tests)
    uint8_t t;          // frames in the phase (stops at 255)
    uint8_t revs;       // revs begun this fight (tests)
    uint8_t lurches;    // lurches made (tests)
    uint8_t stalls;     // revs a catch stalled (tests)
} duke_t;
#define duke (*(duke_t *)BOSS_OWN)
#if 5 > BOSS_OWN_N
#error "Duke's state: BOSS_OWN_N"
#endif

static uint8_t idle_len(void) {
    return boss_hp >= 9 ? IDLE_HI : boss_hp >= 5 ? IDLE_MID : IDLE_LO;
}

static void to_idle(void) {
    duke.phase = DP_IDLE; duke.t = 0;
    boss_xpose = 0;
    BOSS_TOPPER_T = 0;
    if (boss_state == BS_TELL || boss_state == BS_SPECIAL) boss_state = BS_WALK;
}

static void to_rev(void) {
    duke.phase = DP_REV; duke.t = 0;
    duke.revs++;
    boss_xpose = BP_TELL1;
    SFX(SFX_SHAKE);
}

// The regulars: the chord on the three free bars (a, b, c): a and b at once, c after a breather, c and b and then a once
// more with a breather (wait codes 1 short, 3 four intervals, as the venue's "chord").
static void chord(void) {
    static const uint8_t cycle[CHORD_N][2] = { {0, 1}, {1, 1}, {2, 3}, {2, 1}, {1, 1}, {0, 3} };
    uint8_t free_bar[3], i, k = 0;
    for (i = 0; i != NUM_BARS; i++) if (i != boss_bar) free_bar[k++] = i;
    for (i = 0; i != CHORD_N; i++) pat_buf[i] = free_bar[cycle[i][0]] | (cycle[i][1] << 4);
    pat_len = CHORD_N; pat_pos = 0; pat_bar = pat_buf[0] & 3;
}

uint8_t boss_duke(uint8_t ev, uint8_t arg) BANKED {
    (void)arg;
    switch (ev) {
    case BEV_SET:
        boss_art_set();
        duke.revs = duke.lurches = duke.stalls = 0;
        to_idle();
        break;
    case BEV_RESET:
        to_idle();
        break;
    case BEV_LOAD:
        boss_art_load();
        if (is_cgb) {                    // the helmet's own colours (red shell, white stripe, dark outline) in OBJ 7
            palette_t p;
            p[0] = 0; p[1] = RGB(29, 7, 7); p[2] = RGB(31, 31, 31); p[3] = RGB(3, 2, 4);
            set_sprite_palette(OBJPAL_PATRON_C, 1, p);
        }
        break;
    case BEV_BEGIN:
        chord();
        break;
    case BEV_TELL:
        if (duke.phase == DP_IDLE) to_rev();
        break;
    case BEV_CATCH:                      // (then the common catch: meter -1, push 16, the gulp)
        if (duke.phase == DP_REV) {
            duke.phase = DP_STALL; duke.t = 0;
            duke.stalls++;
            boss_xpose = 0;              // WINCE while pushed, then GULP
            BOSS_TOPPER_T = 0;
            boss_state = BS_WALK;
        } else if (duke.phase == DP_IDLE) duke.t = 0;
        break;                           // (a catch in the lurch: it finishes, then idle from 0)
    case BEV_OUTRO:
        to_idle();
        break;
    case BEV_FRAME:
        if (duke.t != 255) duke.t++;
        switch (duke.phase) {
        case DP_IDLE:
            if (duke.t >= idle_len() && boss_state == BS_WALK && !boss_push) to_rev();
            else boss_xpose = boss_state == BS_WALK && (duke.t & POSE_FRAMES) ? BP_STOMP : 0;
            break;
        case DP_REV:
            if (duke.t >= DUKE_REV) {
                duke.phase = DP_LURCH; duke.t = 0;
                duke.lurches++;
                boss_xpose = BP_TELL2;
                BOSS_TOPPER_T = 0;
                boss_advance();
            } else {
                boss_xpose = duke.t & POSE_FRAMES ? BP_TELL2 : BP_TELL1;
                BOSS_TOPPER_T = duke.t & DUKE_HOP ? HAT_DOWN : 0;
            }
            break;
        case DP_LURCH:
            if (duke.t == DUKE_HOP) boss_advance();
            if (duke.t >= DUKE_LURCH) to_idle();
            break;
        case DP_STALL:
            if (duke.t >= DUKE_STALL) to_idle();
            break;
        }
        if (duke.phase == DP_REV && boss_state == BS_WALK) boss_state = BS_TELL;       // (he stands)
        else if (duke.phase == DP_LURCH && (boss_state == BS_WALK || boss_state == BS_TELL)) boss_state = BS_SPECIAL;
        break;
    }
    return 0;
}
