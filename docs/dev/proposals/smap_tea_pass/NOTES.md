# Teahouse quality pass (proposal; nothing in src/, assets/ or the default map output changed)

Owner: "Give the teahouse a quality pass." Same building: footprint 12 x 7 cells at (24, 55), both roofs, door curtain, lantern, stones, cherry tree, TEA / TEA_B palettes, tea cell (34, 59) on tea@g.

## Swap in
- Art: `v_tea_pass.py` (drop-in for `tools/smap_world/v_tea.py`, same `build(dmg)`; every row typed by hand, changes marked `# PASS`). To adopt: copy it over `v_tea.py`.
- Env switch for scratch builds: `SMAP_TEA_PASS=1` with `render.py`, `measure_pass.py`, `count.py` (they `import swap`, which puts `v_tea_pass` in place of `v_tea`). Without the variable nothing changes.
- Sheets: `sheet_x6.png` (before | after x6, Color over DMG), `sheet_ctx.png` (before | after in the map x3). `sheet.py` builds them from `render.py` output.

## Flaws seen, and what was done (only these)
1. Roofs had no outline: one ink pixel at the end of each row, so the exposed top of every step (4 4 4 4 3 2 px, and 6 px at the lower roof's top) ran bare against the moss. Both roofs now have the full ink staircase.
2. Upper roof ridge had no top edge: new 6 px ink cap on row 1.
3. Upper roof eave had no bottom outline except under the wall (x26..53): row 9 now ink x15..64.
4. Lit edge hugged the outline (constant 2 px cream band, reading as dashes): now tapers 2 3 3 2 2 1 1 (upper) and 3 3 2 2 1 1 (lower), light from the top left like the lodge, saloon and bistro.
5. Shoji wall panels were 5, 5 and 9 rows tall (one tall hole): rails now at 33 38 43 48, panels 5 4 4 4, the last rail is a sill.
6. Veranda was two flat dark rows: row 50 is now the lit top plane (shade 1), row 51 the front face, so it reads as a platform and gets the bright top edge.
7. Lantern base overlapped the veranda's left end (rows 48-49 fused into one blob): lantern moved two rows up (paste y 36), base now clear of the deck.
Left alone on purpose: roof interior (calm, no tile texture added), the eave shadow row 25, upturned eave whiskers (4 px, deliberate), door and curtain, the tree, the stones (they touch the veranda and the road kerb as before), palettes and cell palette assignment.

## Numbers (stage 1 generator, `measure_pass.py`, fountain working, dark water)
| | before | after |
|---|---|---|
| DMG tiles, whole map | 797 | 797 |
| Color tiles | 859 | 859 |
| Color slots | 352 | 352 |
| worst 21x19 view / 22x20 view | 143 / 152 | 143 / 152 |
| flat tile uses in a 22x20 window (limit 239) | 238 | 238 |
| palettes per 21x19 window (max 8), windows over | 8, 0 | 8, 0 |
| palette table entries | 21 | 21 |
| generator | OK | OK |
Picture alone (lint, 96 x 56, DMG): 65 unique tiles exact / 51 flips merged before, 64 / 49 after. Lint orphan pixels 26 before, 6 after (the 4 eave whiskers and 2 tree sparkles, all deliberate). Lint RESULT PASS both.
The rail move (33 39 -> 33 38 43 48) is also what keeps the tile count: a rail at 44 alone made +1 DMG and +2 Color tiles; the sill row at 48 makes two veranda-end cells identical again.

## Doubts
- The cream veranda top plane is the boldest visible change; if too bright, row 50 can go back to shade 2 (the tile count does not depend on it).
- Lantern now stands one row above the deck's top edge; a level base would need the veranda's end moved.
