# Falls v2: two options for the mountain-to-river interface (proposal only, nothing in assets/)

Owner: the falls look like they come out of a door in the mountain; the foot walls jut at odd angles.

Sheets here: `sheet_wide.png` (wide window x4, NOW / A / B stacked, Color above DMG), `sheet_close.png` (x6 close-up, falls steps 0..3, NOW | A | B), `falls_v2.gif` (180-frame loop, 50 ms, NOW | A | B, one shared palette, no strobing: only small water cells change).

## What changed (both options)
- The cave mouth and the snow-ground rock ledge (cells 45..49 of row 5) are gone. Row 5 is the map's own grass again; the two falls cells of row 5 are the approved art again (water palette, grass banks). All new art is on y 39 and above, in cells that already take `igloo`: no palette change.
- The approved column, foam lip and pool glints are untouched, same timing. Water on the face reuses the approved streak columns (FALL_COLS, 3 rows a step, 4 frames).
- **A**: small cleft (5x3) at y 21..23 on the right of the lit face, a thread of water (2 px, shadow groove on its left) that widens 2-3-4 and fans into the column; rock shelves (shade band over an ink underline) step down toward the water from both sides.
- **B**: notch under the snow cap (y 15..16), a gully with dark walls that jogs 3 times, a lip with flanking ink and a splash, a fan into the column; a diagonal rib on the left and a boulder on the right.
- Art is typed in `falls_art.py` (runs of characters per row); `falls_v2.py` only writes it. Hook: `big_mountain.py` reads `SMAP_FALLS=A|B` instead of the cave.

## Numbers (measure.py on the integrated map, A' + B; tile max raised to 2000 to count)
| | DMG tiles | Color ids | worst DMG 21x19 view | palettes worst / windows over 8 |
|---|---|---|---|---|
| NOW (cave) | 974 | 1039 | 170 (the brief's 171 includes +1) | 8 / 0 |
| A | 972 | 1037 | 169 | 8 / 0 |
| B | 972 | 1037 | 169 | 8 / 0 |
- Worst view is at cells (1,41), far from the falls; the falls windows are lower. Nothing over 172. Color ids 2 fewer than now (the snow ledge cells are gone), well inside the ~100 spare.
- **Animated cells**: A 3 ((47,3), (46,4), (47,4)), B 3 (same cells); the upper cleft/gully water is static. Images: 4 per cell, so 12 images, 9 beyond the map tiles. The approved falls cells keep their 6 images. B's static gully water is frozen above y 24.
- **DMG VBlank peak: does not rise, 6 tiles / 96 B (igloo view).** The cascade cells step at video frame 4 mod 9. The approved falls step at 0 and 6 mod 9; glints and igloo smoke only at multiples of 15 (residues 0, 3, 6 mod 9). Frames 4 mod 9 carry no other write, so the new peak there is 3 tiles. The river-top view stays 5. Not simulated with the engine; reasoning from items.py phases.
- Color vs DMG: both fit DMG (same indices; DMG light water foam 0 / water 1). The row-5 rim reads 1 through `to_dmg` as before.

## Self-audit
| Check | Result |
|---|---|
| Hand-placed | PASS: typed runs in falls_art.py; code writes them. Water value per pixel comes from the approved streak pattern at my chosen column |
| Clean-up pass | PARTIAL: stray tiny boulders and white ledge tops removed, shelves made 2-row bands, cone widened gradually; no full pass at 1x |
| 1x vs quality bar | looked at the igloo-era mountain beside it; the shelves still read evenly spaced |
| Lint | FAIL: not run (no PNG asset; the art is a map patch) |
| Palettes / tiles | PASS: 8 per window, 0 over; tiles above |
| Squint DMG / Color | falls read first; A's thread is light on mid grey |

## Doubts
- The foot rocks are modest: ground below the foot is grass, so no rock can go below y 39 without a new palette. Shelves are slightly regular (staircase banding).
- B's gully is rigid and dark; A is cleaner. The static upper gully looks still beside the moving fan.
- Water streak columns jag in the 3-4 px thread. Lint not run.
- Deviation: the stock contact_sheet.py labels use a tiny font; the owner's "labels readable" rule made me draw my own.
