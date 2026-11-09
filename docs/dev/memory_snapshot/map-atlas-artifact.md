---
name: map-atlas-artifact
description: Map Atlas page (owner ask 11-08): story map tiles/palettes/walk load; rebuild with make map-atlas and republish after every map merge
metadata:
  type: reference
---
Map Atlas: https://claude.ai/artifact/X2U5TjT71iXsqsZw12Yuvu. Owner asked for it 11-08 ("something like the atlas's for the map ... where the hitches and slowdowns are ... where sections are overloaded and where they are light") because he suspects we protect unimportant map items.

**How to apply:** after every story-map merge run `make` then `make map-atlas` on main and republish out/map_atlas/index.html with img/*.png (root out/map_atlas) to the same URL. Use its findings when weighing map palette/tile trade-offs instead of protecting every piece. Related: [[gfx-atlas-artifact]], [[story-map-decisions]].
