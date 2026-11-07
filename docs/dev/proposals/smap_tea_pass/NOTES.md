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

## Round 2: texture (owner: "better, but needs more texture"), on the approved map A' (stage 1h, merged at b7fe45af)
`v_tea_pass.py` is now fixes + texture; the fixes alone are kept as `v_tea_pass_v1.py` (bf8d13ff). Env: `SMAP_TEA_PASS=1` (texture) or `v1` (fixes only), `SMAP_TEA_TEX=full|light|none` (default full), `SMAP_AP=1` builds the map as option A' (radii 32 x4 / 24 x8, mountain A, bush x 40). Sheets: `sheet_tex_x6.png`, `sheet_tex_ctx.png` (before = v1, after = texture).
Texture, all typed 8 px course tiles repeated on the absolute column grid, painted only on roof body with 2 px of margin so outlines and the cream taper stay clean, lit from the top left:
- roofs: shingle courses, a 6 px ink joint (gap 2) every 3 rows, the next course shifted 4 px; a 2 px lit cream cap under each joint's left end (lower roof both courses, upper roof the first). The 16 px under the tower stays plain (the tower's shadow, and those two cells already share a tile with the map).
- wall posts: short dark grain dashes in the inner column, staggered left and right.
- veranda: board ends every 16 px (notch on the lit top plane and on the front face, same column).
- stepping stones: a shade-2 shadow on the lower right.
Levels: `light` = roof joints only; `full` = the above.
Cost, real `measure_pass.py` on A' (fountain working, light DMG water): default art 960 DMG / 1022 Color ids; v1 fixes 961 / 1023 (+1 / +1, the 3 rails and eave outlines make shared end tiles unique); **texture light 961 / 1023, full 961 / 1023 (+0 over v1, +1 / +1 over the default map)**. Worst view 156, windows over 8 palettes 0, flat uses 218, generator OK. The texture is free because nearly every cell of the house is already its own tile; the seams, post dashes and stones sit in such cells, and the roof courses are placed so the shared cells (28,57) (29,57) and the pairs (2,6) (3,6) (7,6) keep their tiles.
If the +1 of the fixes must go too, drop the roof end outline fixes 2 and 3 (cells (25,56) (32,56)); not tried.

## Round 3: option B, kawara tile ribs (owner read A as scattered dashes; posts as stray marks)
Env: `SMAP_TEA_PASS=1` with `SMAP_TEA_TEX=A` (round 2 dashes, default) or `B` (ribs); `v1` = fixes only. Merged import tip 1f04da2a: A' is the mapctx default, so `SMAP_AP` is no longer needed. Sheets: `sheet_opts_x6.png` (fixes | A | B, Color over DMG), `sheet_B_ctx.png` (B in the map x3).
B: a hand-typed 8 px tile repeated on the column grid: rib rows `22132213` (a lit cream pixel left of an ink rib line every 4 px, light from the top left) down both roof slopes, painted only on roof body, and the eave rows (y8 upper, y23 lower) `13131313` (round tile ends, light and dark alternating). Wall posts plain. Veranda board ends and stone shadows kept.

**Measure, real `measure_pass.py` on the import default (A'), fountain working, light DMG water** (the generator fails above 1023 Color ids):

| | DMG tiles | Color ids | worst view | windows over 8 | table |
|---|---|---|---|---|---|
| default art | 957 | 1023 | 156 | 0 | 22 |
| fixes (v1) | 957 | 1022 | 156 | 0 | 22 |
| A dashes | 957 | 1022 | 156 | 0 | 22 |
| B ribs | 958 | 1023 | 156 | 0 | 22 |

All generator OK. Which count is right: 1023 Color ids for the default; my round 2 "1022" came from a hand-copied A' env that differed slightly from the real default, so the earlier "+1" for the fixes was measured against the wrong base. My DMG is 957 where the import agent states 958; probably its DMG count differs (fog states or light-water variants); the Color number agrees.

Correction to round 2: on the real default the upper eave end outline made two shared end tiles unique and pushed Color to 1024 (the generator fails). Fixed here: row 9 (upper eave bottom outline) spans x16..63 instead of 15..64, so the end cells keep the default single-pixel tiles. That is why fixes and A are now one id under the default; `v_tea_pass_v1.py` carries the same row. B costs +1 DMG tile and 0 Color ids against the default.
