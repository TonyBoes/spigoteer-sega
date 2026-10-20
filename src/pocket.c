// The pocketed tip (owner's playtest notes 2026-10-18: "picking up a tip during a show pockets it, and B triggers a show at any time").
//   - A tip picked up while a show runs is kept instead of wasted: one slot. start_show (show.c) calls pocket_take for it. A tip can lie on
//     the floor during a show only while the pocket is on and empty (patrons.c maybe_tip), so with a tip already pocketed nothing changes.
//   - B in play starts a show from the pocket, when no show runs and the play is live (not the level's end, not a boss fight: no shows there),
//     and empties it. START still pauses (pause_or_pocket, main.c's GS_PLAYING).
//   - ARCADE and STORY only. CLASSIC stays authentic (tip_pocket 0: every test reads it as before), and so do the harness and BOSS RUSH.
//   - Emptied when the level ends (enter_level_clear, a story boss fight that starts in place); a lost life keeps it (it was earned; the
//     life's reset takes the coin and the show away as ever).
//   - HUD: the coin's icon at row 0, column 9 (BG id POCKET_TILE, art assets/art/hud_icons.txt POCKET), drawn through the VBlank queue from
//     the byte tip_pocket itself, which holds the tile id (game.h).
#pragma bank 255
#include <gb/gb.h>
#include <stdint.h>

#include "game.h"

uint8_t tip_pocket;

// the level's load (LCD off): ARCADE and STORY switch the pocket on, empty; the icon's tile
void pocket_level(void) BANKED {
    tip_pocket = (play_mode == MODE_ARCADE || play_mode == MODE_STORY) ? TILE_HUD_BLANK : 0;
    if (tip_pocket) hud_icon_load(POCKET_TILE, HUD_ICON_POCKET);
}

static void pocket_draw(void) {
    if (LCDC_REG & LCDCF_ON) vq_add(0, &tip_pocket, POCKET_COL, HUD_ROW, 1);
}

void pocket_take(void) BANKED {
    tip_pocket = POCKET_TILE;
    pocket_draw();
}

void pocket_clear(void) BANKED {
    if (tip_pocket != POCKET_TILE) return;
    tip_pocket = TILE_HUD_BLANK;
    pocket_draw();
}

// GS_PLAYING with START or B pressed: START opens the pause menu (returns 1: the frame ends); B starts a show from the pocket (0: the frame goes on)
uint8_t pause_or_pocket(uint8_t pressed) BANKED {
    if (pressed & J_START) { pause_open(); return 1; }
    if (tip_pocket == POCKET_TILE && !show_timer && !level_clear && !boss_on && !life_lost) {
        pocket_clear();
        start_show();
    }
    return 0;
}
