BRIEF (queued 2026-10-21; start when an agent slot frees, FIRST in the queue)

You are implementing a feature in the Game Boy game "Spigoteer" (GBDK-2020 C plus hand-written asm) in your own git worktree (start from current main). Read /workspace/CLAUDE.md, then read and obey /tmp/claude-1000/-workspace/14228534-aec7-4761-a172-2f78e37cb357/scratchpad/decisions/rules_code.txt. Never replace goldens; list any that differ with bounding boxes.

FEATURE: a DMG-only "half-rate" (30 fps) mode for the heaviest levels. The game keeps its normal speed and rules; the picture updates every other frame.

Owner, 2026-10-21. He played a throwaway ROM that simply ran everything every other VBlank: "doesn't feel as smooth, but it doesn't look too bad. It does play really slowly." He wants the slowness gone, so the game keeps normal speed at 30 fps: "write the logic for when a level runs at 30fps on dmg... only activate it when needed. Leave it off in most levels except where you deem it needed. I'll playtest later and tell you if it needs to be turned on anywhere else."

DESIGN (decided; do not double the speed constants):
- In half-rate mode, each displayed frame (every 2 VBlanks) runs the GAME LOGIC TWICE and the DRAWING ONCE.
  - Game rules stay exactly as they are: 1 px steps, timers, catch windows, the pour, input.
  - Input is read for each logic step.
  - Music ticks once per VBlank's worth (twice per displayed frame), so the tempo stays right.
- This needs play_frame() (src/main.c update(), GS_PLAYING) split into a logic part and a draw part.
  - Logic: patrons, mugs, the bartender's rules, catches, spawns, story/arcade rules.
  - Draw: OAM writes (draw_bartender, draw_mugs, draw_lifted), queue_vram's copy list, the HUD, and the crowd chooser lift_frame if it is purely about drawing.
  - Find the real boundary in the code. Some "draw" code also updates state, e.g. redraw marks accumulate and must still be queued once. Dirty spans and quick redraws may accumulate over two logic steps, then be queued once.
- Choose where the crowd chooser runs (once per displayed frame should do) and prove the lifted set stays legal: max 10 sprites per line, BG patrons never sharing columns unflagged. The 1 px logic means a patron may move 2 px between pictures, which is fine.
- DMG only. The CGB is going to double-speed mode (another agent is implementing that now on another branch). The CGB never uses half-rate.
- WRAM: no new globals; use spare bits or the existing unions (see the rules file). ROM0: report its cost. Every asm routine keeps its C version (make cfall).
- Another agent is editing main.c, music.c, pause.c and trans.c for double speed. Keep your changes to the main loop small and well-contained so the merge is easy.

WHEN IT IS ON:
- A per-level flag. Add a debug-menu toggle (src/debug.c): AUTO / FORCE ON / FORCE OFF, so the owner can playtest any level both ways.
- Decide AUTO from measurements:
  - Measure DMG late-frame rates for every CLASSIC level row (src/classic.c classic_table, 26 rows), the ARCADE loops' peak levels, and STORY's heaviest shifts. Use the method in /tmp/claude-1000/-workspace/14228534-aec7-4761-a172-2f78e37cb357/scratchpad/draw2/ (expmeasure.py, run.sh; copy and adapt).
  - Turn it on where today's DMG late rate is high enough that the game visibly runs slow. Propose a threshold, e.g. above 30% late frames in realistic play, and list each level with its number.
  - Expected: CLASSIC's 16-patron levels at least.
- For every level where AUTO turns it on, measure it with the mode on: the late rate (target 0) and the game speed (game frames per second ~60).

TESTS:
- A new tests/test_half_rate.py, DMG:
  - in half-rate the game state after N displayed frames equals the state after 2N normal frames, for the same inputs (positions, timers, score), on a scripted level. This proves the rules are unchanged;
  - music ticks per second are equal;
  - no late frames on the heaviest CLASSIC level;
  - the debug toggle works;
  - CGB never enters half-rate.
- Existing tests: everything stays green. If some test levels now run half-rate on DMG and their frame-pinned goldens move, list them with bounding boxes, explaining that it is timing.
- Run:
  - make -B, make cfall;
  - the full pytest suite. There is no xdist: run test files in parallel processes, as scratchpad/ptest.sh does, pointed at your worktree;
  - make check;
  - RUN_SLOW=1 pytest tests/test_fade_hw.py;
  - GB_ROM=build/game-c.gb on the full suite.
- Build `make unlocked` and copy to /workspace/out/test_roms/spigoteer-halfrate-unlocked.gb.

Report:
- the commits;
- the logic/draw split (what moved where);
- the level table with the before and after late rates, and which levels AUTO enables;
- the tests and goldens;
- the costs;
- anything that felt risky.
Kill every process you start. Don't use `pgrep -f` wait loops.
