# Zoo bamboo (owner 11-11): bush out, and a proposal to share the map bamboo's tiles

Pictures (open these): `pics/part1_bush_out_engine.png`, `pics/closeup_x4.png`, `pics/option1_engine.png`, `pics/option2_engine.png`.

## Part 1 (done, committed with the assets): `tools/dev/smap_zoo_bush.py`
The bush at cells (3..5, 59..60) is gone on both maps. Row 59 gets the stalk tile back (the middle stalk's foot was hidden by the bush; the left and right stalks were bitten by it), so all three stalks end on one line with their node flare as the foot; row 60 is plain grass (colour 0). Nothing else changes; palettes are untouched.

## Part 2 (proposal, not imported): `smap_zoo_bamboo_opt.py 1|2 [--apply]`
The map's scattered bamboo is the 2 x 3 clump at (13..14, 50..52) (three stalks, 16 px wide: top, middle, foot tiles, six tiles each used once) plus 2 x 2 and single-stalk clumps with no middle tile (so they cannot be stacked tall). The zoo grove is rebuilt from the big clump's six tiles: top row 54, middle rows 55..58 (middle, foot, middle, foot tile), foot row 59. Stalk tops 432 / 438 / 440 px (old 429 / 440 / 447), foot line unchanged.
- Option 1: clump on cells x = 3..4 (left edge as now). Option 2: x = 4..5 (against the gate).
- Honest note: it reads as a slimmer, denser grove of ringed stalks with leaf ticks (3 px stalks, 16 px wide) instead of the three fat capped stalks (24 px wide). Same height, same place, same tile family as the clumps nearby; not the same drawing.
- Covers Part 1's area: yes, it clears cells (3..5, 53..60) first, so it does not need `smap_zoo_bush.py` (both are idempotent and can run in either order only if the option runs last).

## Numbers (generator `tools/gen_smap_world.py`, route-plan proof run on each variant by `measure.py`)
| variant | DMG tiles | Color tiles (ids) | worst 21x19 DMG | 22x20 | palettes per window | route proof |
|---|---|---|---|---|---|---|
| before Part 1 (main) | 903 | 845 | 164 | 181 | 10 (22x20: 11) | proved |
| Part 1 | 899 (-4) | 841 (-4) | 164 | 181 | 10 (11) | proved |
| Part 1 + option 1 | 894 (-9) | 836 (-9) | 164 | 181 | 10 (11) | proved |
| Part 1 + option 2 | 894 (-9) | 836 (-9) | 164 | 181 | 10 (11) | proved |

Option vs Part 1: 5 DMG tiles and 5 Color ids saved (the grove's own tiles: cap, two bud tops, node/flare middle; the clump tiles are already on the map). Palette change: none (all cells stay `zoo`; the Color worst view stays 8 of 8 elsewhere). Busiest view: unchanged (164 / 181 is elsewhere on the map); the busiest 21x19 window holding the grove stays at 128 tiles by a plain unique-block count (the grove's views are not near the worst). Animated cells untouched.
