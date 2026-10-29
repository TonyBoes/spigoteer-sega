---
name: gfx-atlas-artifact
description: Old Graphics Atlas page retired 2026-10-26, deleted 2026-10-29; the Palette Plan page (Ekc9oYWEQb4APdLTaqXG4H) is now the Graphics Atlas; make atlas still feeds it
metadata:
  type: project
---

Owner, 2026-10-26: "At this point we can drop the graphics atlas. I think I have all I need in the palette plan. Let's make it the new graphics atlas."

- The old atlas page (was https://claude.ai/artifact/RLQysU9fNNbcZR2TS8x5XZ) was deleted 2026-10-29.
- The Palette Plan page, same URL https://claude.ai/artifact/Ekc9oYWEQb4APdLTaqXG4H, is titled "Graphics Atlas" now.
- `make atlas` (tools/gfx_atlas/) still runs: it writes out/atlas/data, which the new page's build.py reads.

**Why:** the Palette Plan grew boss, scene and tile-grid sections and covers what he uses.
**How to apply:** after merges touching art, palettes, patrons or screens: `make atlas`, then `python3 tools/artifacts/palette_plan/build.py`, republish to Ekc9… only. Keep the old atlas's rule on the new page: summary first, detail behind toggles.

Related: [[palette-plan-artifact]].
