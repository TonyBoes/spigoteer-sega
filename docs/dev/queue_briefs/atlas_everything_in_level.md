BRIEF (queued 2026-10-21; next free slot): the graphics atlas shows EVERYTHING a level can use, not just one sampled moment.

Owner: "The atlas should show information for everything used in a level--not just for the screenshot that it includes. So it should show patron palettes for when they become sprites, etc."

Tool: tools/gfx_atlas/ (build.py, capture.py, analyze.py, scenes.py, summary.py, freepal.py, page.html); `make atlas` writes out/atlas/. Repo rules: CLAUDE.md, plus scratchpad/decisions/rules_code.txt. No game code changes.

For every level screen (the 10 ARCADE venues and the CLASSIC levels), drive the game through EVERY sprite-producing event during capture and record each event's sprites, palettes and tiles. Use the test hooks and pokes the tests already use:
- lifted patrons A, B and C: lift_hook_op / lift_hook_p (src/lift.c test hook; tests/test_lift.py shows it), with each variant lifted at least once, including the enhanced variant where the venue has one (OBJ 4 + bank-1 tiles);
- patrons entering from the left edge (LIFT_EDGE sprites) and leaving (served);
- full mugs sliding, empties returning, a mug held while drinking (all poses), the fill glass at the tap;
- a breaking glass (MUG_BREAKING) and its shards falling into the bar below;
- the tip coin on the counter, and its blink;
- the dancers' show (OBJ 5 swapped to the show palette; the dancers' frames);
- the PERFECT cue (OAM_CUE) where a level can show it (STORY), and any pour/streak sprites;
- the bartender's frames: idle, walk, fill (also used for slide and catch), fail;
- the pocketed-tip HUD icon (BG) and any HUD changes.

Then, per level, the page shows:
- "Everything this level can draw":
  - per OBJ slot, its colours, plus every sprite drawn with it in ANY event (the "Sprites using it" column becomes complete, grouped by event, e.g. "lifted patron B", "breaking glass", "show dancers");
  - per BG slot likewise, with the tiles that use it.
- the tiles loaded for the level: all OBJ and BG tiles the level loads, marked by what uses them, including event-only ones.
- a short event strip: a small still or GIF of each event, so the owner sees the patron as a sprite, the glass breaking, the show, etc.
- The "Free sprite palettes" table now cross-checks against this complete capture. A slot that is FREE must show no sprite in any event; warn otherwise.
- Keep the existing "screenshot" still as the level's representative picture, but label the panels "everything this level can use (all events)", so it's clear they are not just that screenshot.

Keep the file count ≤ 480 (pack event images into the per-screen PNG) and the run deterministic. Check in the headless Chromium under scratchpad/browser_test/ (CDP script approach as the previous atlas agent did). Copy out/atlas/ to scratchpad/gfx_atlas/, commit, and report.
