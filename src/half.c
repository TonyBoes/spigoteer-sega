// 30 fps on the DMG (owner 2026-10-21). The heaviest levels (a crowd of 16 patrons) do not fit one frame of the 4 MHz DMG: the game used to
// drop every second VBlank and ran at half speed. In half-rate mode the game keeps its speed and its rules and the picture is what
// updates every other VBlank: main.c update() runs the LOGIC (play_frame, story_play: input, the bartender, mugs, patrons, spawns, catches,
// timers) in every VBlank, and the DRAWING (the crowd chooser lift_frame, queue_vram, the OAM writes, the HUD) in every second one, for
// both steps' changes together. Music and effects tick once a VBlank as ever. The picture is chosen from the state after the second
// step, so everything it shows is as consistent as a normal frame's; a patron simply moves 2 px between pictures.
// A step that ends the level or a life, or opens a fight, is drawn at once; the fight itself runs every frame at full rate.
// A drawn step that overruns its VBlank is not lost: the next, short step starts at once (main.c main(): the pair still fits two VBlanks; a
// VBlank lost to the race between the check and frame_wait's flag is made up the same way, HALF_OWED). So the drawn step's own lateness
// gates are off in this mode (the chooser's CHOOSER_LY_LATE in lift.c, the bars' QUEUE_LY_LATE in render.c): a long picture is paid for by
// the short step after it, and the chooser then runs for one bar in every picture, which at 60 fps it could not (9-40 % of the pictures
// had a BG pair sharing a column without its flags; 2-4 % at 30 fps). Rules that live in the drawing code (src/pour.c) have a logic-only
// half (half_step below), and the round robin of bars counts pictures (lift.c: frame_counter >> 1).
// What is not the same: a served patron sliding out stands still until his BG copy is off the screen (patrons.c leaving_step looks at the
// copy list, which goes out with the picture), up to a step longer.
// On when HALF_ON (game.h) is set by half_decide(), called at a level's load (level.c start_level) and by the debug menu's line (src/debug.c):
// the DMG only, and there either the menu's FORCE ON / FORCE OFF or AUTO: the levels the measurements below found too heavy for 60 fps.
#pragma bank 255
#include <gb/gb.h>
#include <stdint.h>

#include "game.h"

extern uint8_t level, cur_group, arcade_loop;

// AUTO: on where the DMG's 60 fps frame is late too often. The measurement (a peak crowd at the level's bar caps, the bartender on the
// level-8 script, 2500 frames, 4 starting alignments; "late" = emulated frames per game step - 1): the threshold is 30 % late, where the
// game plays visibly slow. CLASSIC rows over it: 5 (31-51 %), 7 (34-50 %), 8-26 (59-89 %); under it: 1-4 (5-30 %), 6 (14-24 %). Every other
// mode's peaks (ARCADE's loop-4 Last call at 8 / 10 / 12 patrons 15 / 28 / 21 %, STORY's shifts 1-13 %) stay under it: they run at 60 fps.
// Bit n - 1 of HALF_ROWS: CLASSIC row n.
#define HALF_ROWS 0x3FFFFD0UL
static uint8_t half_auto(void) {
    uint8_t row = level;
    if (play_mode != MODE_CLASSIC) return 0;
    while (row > CLASSIC_ROWS) row -= 13;               // (level 27 on: wave 2's rows again, classic.c row_of)
    return (HALF_ROWS >> (row - 1)) & 1;
}

void half_decide(void) BANKED {
    uint8_t f = (HALF >> HALF_FORCE_SHIFT) & 3, on;
    if (is_cgb) on = 0;                          // (the CGB runs at double speed instead)
    else if (f) on = f == 1;
    else on = half_auto();
    HALF = (HALF & ~HALF_ON) | on;
}

// A logic-only step (main.c half_skip): the rules and timers that live in the drawing code (src/pour.c) go on at the game's speed.
void half_step(void) BANKED {
    if (story_on | cue_t) pour_skip();
}

// The main loop's wait for the next step while HALF_ON (or HALF_OWED is left over). A step that ran past a VBlank has used that VBlank's
// time, so the next step starts at once, not a whole frame later (the drawn step is the long one, the logic-only step after it the short one,
// so the pair fits two VBlanks). A step that ends just before a VBlank and is overtaken between the check and frame_wait's flag clear loses
// that VBlank: the next step starts at once, too (HALF_OWED). Only while playing: the other states wait as ever.
extern uint8_t frame_t0;
void half_wait(void) BANKED {
    if (HALF & HALF_OWED) { HALF &= ~HALF_OWED; return; }
    if (game_state != GS_PLAYING || !(HALF & HALF_ON)) { frame_wait(); return; }
    if ((uint8_t)sys_time != frame_t0) return;                    // (the last step ran past a VBlank)
    frame_wait();
    if ((uint8_t)((uint8_t)sys_time - frame_t0) > 1) HALF |= HALF_OWED;
}
