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

## Round 4: walls on top of roof option B (approved, roof unchanged)
Env: `SMAP_TEA_PASS=1 SMAP_TEA_TEX=BW` (B roof + walls); `B` is the roof alone. Sheets: `sheet_walls_x6.png` (B | B + walls, Color over DMG), `sheet_walls_ctx.png` (x3 in the map, light DMG water, the default).
Done, all inside cells that already own a tile (the repeated panel pairs at x24..31 and x48..55 get identical pixels):
- wall posts: a thin lit grain line (paper shade) down the outer column of each wall post, jogging one column in at a knot (y36-37). The posts are only 2 px wide, so a line in the wood shade is invisible and a dark one read as a black bar; the lit line reads as a lit edge.
- shoji panels: a sparse ordered shade (every 4th pixel, shade 2) on the bottom row of each panel.
Not done: door-post lines (the cream line made the door frame look wide; tried and removed), grain on the beam rows 26-27 (rows 25 and 28 touch it, so a line there reads as a thicker outline), a plinth strip (the wall has none: the sill rail at y48 sits on the veranda ink; a plank or stone hint there would change the pairs (2,6) (3,6) (7,6), which share one tile today: about +1 to +2 Color ids).
Measure, real `measure_pass.py` on the import default: B roof 958 DMG / 1023 Color; B + walls 958 DMG / 1023 Color (+0 over B), worst view 156, 0 windows over 8, table 22, generator OK.

## Round 5: second lantern, door revision (applied level BWD), zen garden (proposal overlay)
Roof B and the walls (81494bd8) are unchanged. Env: `SMAP_TEA_PASS=1 SMAP_TEA_TEX=BWD` = walls + new door + second lantern; `SMAP_TEA_GARDEN=1` additionally lays the garden proposal (`garden.py`, applied by `overlay.py` after mapctx loads; scen_A5 and the import scenery are not edited). Sheets: `sheet_door_x6.png` (before = walls | after = door, lantern, garden, x6, Color over DMG), `sheet_door_ctx.png` (x3 in the map, light DMG water).
- Second lantern: the same LANT piece at x 73, y 36 (first at x 1, y 36): same 8 px column and row phase, so its cells reuse the first lantern's tiles; the column at x80 falls into a tree cell that is already unique. Cost 0 DMG / 0 Color. It touches the tree's left edge (two ink pixels); the other alignments (x 65 hits the wall, x 57 the door posts) do not exist, and y 44 (clear of the tree) puts it on the veranda corner and the road kerb, off the first lantern's line.
- Door: a half-open sliding shoji leaf: ink outline, wood frame, 5 px paper panes in rows of 4 with rails at y33 38 43 48 like the wall panels, the dark interior in a 4 px strip on the right. Same 12 x 21 footprint, only cells that already hold their own tile. Cost 0 / 0. The wall's panel-bottom shade also lands on the leaf's panes (x36 and x40 on the bottom pane rows).
- Garden (proposal): 32 x 16 px at cells (36..39, 58..59), east of the blossom tree, replacing grass and one tuft; tea@g (0 ground, 1 cream gravel, 2 rock brown, 3 ink), light from the top left: ink outline with a brown curb and rounded corners; gravel raked in horizontal lines (ground colour on cream) that run into rings round two rocks, a third pebble between the lines. All 8 cells are unique (rocks and rings break every repeat): **+8 DMG tiles, +8 Color ids**. Measured (import default + door + lantern): DMG 958 -> 966, Color 1023 -> 1031 (the generator fails above 1023, counted with SMAP_TILE_MAX=4096), worst view 156, palettes per 21x19 window 8 with 0 windows over, table 22 (tea@g already in the table). Estimates, not built: a 3 x 2 bed would cost 6; a version with straight rakes in the two middle cells and rocks only at the ends would cost 6 (the two middle cells of each row repeat) but cannot curve the lines round the rocks.
- West alternative: cells (22..23, 59..61) are the only free grass there (bamboo at x21), too small; north of the house rows 52..54 hold bushes and a pine.

## Round 6: noren instead of the door leaf (level BWN, owner: "a fabric flap")
Env `SMAP_TEA_PASS=1 SMAP_TEA_TEX=BWN` (roof B, walls and the second lantern unchanged; the garden overlay is not used). Sheets `sheet_noren_x6.png` (2d212801 door | noren) and `sheet_noren_ctx.png` (x3, light DMG water; the measure log confirms light).
Split noren: rod y29 and heading tape y30 (wood shade), two cream cloth panels x35..38 and x41..44 with a 2 px dark slit, right column of each panel shade 2 (fold/shadow side, light from the top left), hem stitch y38, cloth y39, soft hem y40 with rounded outer corners, dark interior from y41 and through the slit. Covers y29..40 of the 20 rows (60 percent). No mark (4 px panels, it would be noise). The wall panel-bottom shade no longer touches x34..45 (so the door leaf of 2d212801 also loses two shade dots in this build).
Measured on the import default (B + cave, light water, SMAP_TILE_MAX=4096 because Color is over 1024): default art 973 DMG / 1039 Color; walls + door 974 / 1039; noren 974 / 1039 (0 extra ids over the door), worst view 170, palettes per window 8 with 0 over, table 22.

## Round 7: four curtain concepts (owner: "a few different concepts on the curtain")
Keys, with `SMAP_TEA_PASS=1`: `SMAP_TEA_TEX=C1` wide single noren, `C2` darker three-panel noren, `C3` flap tied back, `C4` eave-wide valance; `BWN` is still the round 6 split noren. All keep roof ribs, walls and both lanterns. Sheets: `sheet_curtains_x6.png` (current noren | 1 | 2 | 3 | 4, Color above DMG, x6), `sheet_curtains_ctx.png` (each x3 in the map).
Light water: the dark river in the earlier context sheets came from a stale generated scratch (`smap_layout_a5/src` is untracked and built by mk_src.py + mk_a5.py; mine predated the light-water patch). Regenerated; renders now use the light DMG water. The tile numbers of earlier rounds were measured on that stale scratch: on the regenerated one the import default is 974 DMG / 1039 Color (was 973 in my round 6 report).
- C1: cream cloth across the whole opening on a rod (y29), brown heading tape, a 6 x 6 brown disc mark centred, shade-2 fold on the right, split only in the bottom third (y39-43), hem y43. Opening covered to 75 percent.
- C2: brown cloth (shade 2), three panels (3 / 2 / 3 px) with ink slits, a cream lit left column on each panel, two cream stripes (y32, y39), hangs to y43 (75 percent), the middle panel one row shorter. On DMG the brown reads mid grey against the ink interior; the weakest contrast of the four.
- C3: one cream flap drawn from the rod down to the right jamb, gathered in a column of folds, brown cord at y36, flaring to the hem at y43; the left of the doorway is open and dark.
- C4: the doorway is plain dark and open; a short brown valance (rows y28-31 across x16..63, ink slits every 8 px, cream stripe on y30) hangs under the beam over the shoji tops. Its repeats make cells identical.
Numbers, real `measure_pass.py` on the import default (SMAP_TILE_MAX=4096, light water): default art 974 DMG / 1039 Color; current noren 975 / 1039; C1, C2, C3 975 / 1039 (0 ids over the current noren, all inside already-unique door cells); **C4 969 / 1033 (saves 6 ids: the covered wall-top cells collapse onto shared tiles)**. Worst DMG view 170 of 176 in all, windows over 8 palettes 0, existing palettes only.

## Round 8: C1S

SMAP_TEA_TEX=C1S: C1 with no slit, straight hem on y43, dark doorway only below. 975 DMG / 1039 Color on the import default (SMAP_TILE_MAX=4096, light water), 0 ids over C1. Sheets: sheet_c1s_x6.png, sheet_c1s_ctx.png.
