// Show stage lighting, the wash (owner 2026-11-03: "The wash is good enough. No sweeps."): Color only. See src/lights.c.
#ifndef SHOWLIGHTS_H
#define SHOWLIGHTS_H
#include <gb/gb.h>
#include "game.h"
#include "scratch.h"
// 16 bytes of story_scratch: the dimmed colours of BG palettes 5 and 6, written by the VBlank (render.c pal5_write). They sit on the first half of the fades'
// OBJ-colour source (SCR_OBJXC, scratch.h), which a scene fade (the pause card) rewrites with chain_cols while three show palettes run: level.c obj_cols then clears
// SHOWLT_STAMP, and trans.c pal_in drops the VBlank request, so a fade neither shows the buffer's old content nor leaves lights_frame trusting it.
#define SHOWLT_N     16
#define SHOWLT_BUF   OBJX_CO                       // (game.h: story_scratch[SCR_OBJXC_AT = 32 ..47])
#define SHOWLT_STAMP (story_scratch[SCR_LTST_AT])  // the tint the buffer holds + 1 (a steady frame skips), 0: rebuild it (a fade, or something overwrote it); tint + 5: a blend holds it (builds every other frame)
#define SHOWLT_REQ   4                             // pal5_req bit: "write the buffer this VBlank"
#define LT_LY_MAX    84                            // main.c calls lights_frame only before this line (a rebuild is up to ~30 lines in double speed: it must end before VBlank, line 144)
void lights_frame(void) BANKED;                    // src/lights.c: once a frame while a show plays (main.c, after the music tick)
#endif
