---
name: palette-plan-artifact
description: Graphics Atlas page (formerly OBJ Palette Plan; renamed 2026-10-26) (freeing CGB sprite palettes for extra patrons); update PLAN/LOG in its build.py on every palette decision
metadata:
  type: project
---

Owner, 2026-10-21: a planning page for freeing OBJ palettes so new unique patrons get their own. It tracks each OBJ slot's use, the patron looks per slot, the free count, and when BG palettes must change too.

URL: https://claude.ai/artifact/Ekc9oYWEQb4APdLTaqXG4H. Source: tools/artifacts/palette_plan/build.py, with the hand-kept PLAN / IDEAS / LOG; the colours come from out/atlas/data.

Key fact: a patron walks the bar as BG tiles (BG 2/3/4) and only becomes a sprite when lifted (OBJ 3/6/7, same colours 1-3). So every patron look costs one OBJ and one BG palette. BG is full in all venues, so the binding limit is BG.

**How to apply:** when the owner decides a palette change, edit PLAN and add a LOG line, run build.py, republish to the same URL, and commit. After art or palette merges, `make atlas`, then rebuild.

Owner decision 2026-10-21: drop the patrons' enhanced looks (M14a: ROSIE, BOXY) after the next patron revision; queued in scratchpad QUEUE.md; the page shows them struck through (DROP_ENHANCED).

The extra patrons are Color-only, with their tiles in CGB VRAM bank 1; the DMG keeps 3 per venue (see [[gbc-enhanced-direction]]).

Related: [[gfx-atlas-artifact]], [[artifact-sources-in-repo]].
