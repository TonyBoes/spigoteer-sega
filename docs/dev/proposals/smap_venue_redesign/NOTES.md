# Story-map venue redesign: igloo, Chrome Cow, zoo, big mountain (proposals only)

Nothing here touches `assets/`. Sheets (x3, DMG above, Color below, today | option 1 | option 2): `igloo_sheet.png`, `cow_sheet.png`, `zoo_sheet.png`, `mountain_sheet.png`. In place on the current map at x2: `map_in_place.png` (looking picks: igloo 1, cow 2, zoo 1, mountain 2). Repeating patterns tiled 4x4: `out/redesign/tiled_all.png` (scratch, not committed). Every pixel is typed in `src/*.py` (ASCII rows or edge lists); helpers only paste, render, lint and count.

## Unique DMG tiles (piece area only)

| piece | today | option 1 | option 2 |
|---|---|---|---|
| igloo | 44 | 44 | 42 |
| Chrome Cow | 44 | 40 | 45 |
| zoo | 42 | 37 | 36 |
| big mountain | 28 | 24 | 33 |

Why more: cow_2 +1 (the 16x16 cow print is 4 tiles plus punk/biker, worth it for a cow that reads as a cow). mountain_2 +5 (two summits, each with its own lit and shaded face, strata dashes on the 8 px grid); mountain_1 is the cheap alternative at 24.

## Palettes (Color)

Each piece uses its venue's existing palette; index 0 is the biome ground, blank cells take the biome's own ground tufts, so no flat pad.
- Zoo: `MERGE` folds zoogate into zoo today (all green). Both options set `UNMERGE` and use ZOOGATE for gate and trees: +1 palette in windows around x 17-28. With all four picks the worst 21x19 window is 10 palettes (at 19,18) against today's 8; over 8 is a layout issue to settle (see questions). Folded zoo gives no extra palette.
- Cow: the blank cells inside its 9-row footprint should use the COW palette, not the biome's, to avoid another palette in the window.
- Mountain: the Color renders lack today's fence posts along the road; the proposals would need them re-added by the layout (not drawn).

## DMG window pool (176 per 21x19 window)

Worst window with the picks in the current layout: zoo_1 178, zoo_2 180 (over by 2 to 4). The other pieces stay under. The layout redo should free tiles near the zoo or I trim the zoo (tilecheck.py gives the numbers).

## Self-audit table (gb-pixel-art)

| check | result |
|---|---|
| gb_art_lint on all 8 | PASS (warnings: large flat areas of mid grey in dome/mountain faces, intended; ground tufts near edges) |
| 4 DMG values separated at adjacent features | yes: lit 1 / shade 2 / ink 3 / ground 0 on every pair; zoo lion mane vs face separated by value |
| squint test, 1x | igloo 1, cow 2, zoo 1, zoo 2 read at once; igloo 2, cow 1, mountain 2 less so |
| periodic patterns tiled | done (tiled_all.png): ice bricks, cow print, stone, thatch, neck, fence, columns, scree all repeat without seams |
| tile budget stated | yes, above |
| hand-placed | yes; no auto-outline, no mirror, no generated shading |
| owner's liked pieces untouched | nothing owner-liked was redesigned beyond the four asked; other venue parts and the hangar, tower, dish, runway are today's |
| no pad on Color | yes |

## Deviations from the skill

- "Show art in the real engine (make BUILD=out/b_real ... scratch builds)": not done. The pieces are rendered with the repo's own world renderer (`tools/smap_world`, same palette and tile code) and composited onto the current map, not built into a ROM, because the layout is being redone and the generator's window checks would fail on today's layout.
- Skill references: not every reference was re-read after the context was compacted; the method was followed from the skill body.
- Silhouettes are typed as per-row edge lists (`LEFT/RIGHT`, `silh`), still hand-placed, but runs rather than a pixel grid for big outlines.
- Existing parts (cow COW sprite letters, canopy, trunk, door) were reused from today's venues where unchanged.

## Self-judgement (strict)

- Strong: igloo_1 (dome of period-8 ice bricks, chimney and smoke, cocoa board), cow_2 (print cow and neon roof board, bikes), zoo_1 (stone gate, smiling lion), zoo_2 (thatch, giraffe).
- Weak: igloo_2 (bar interior small and low contrast, mug sign reads dark), cow_1 (plain and low), mountain_2 (shaded face thin; first drafts read as a pyramid, twin peaks fixes most of it), zoo_2 (neck thin, bamboo tops read as caps).
- At 1x the mountain options are rough compared with the igloo bar; I would pick mountain_1 if tiles are tight, mountain_2 for the better silhouette.

## Engine questions and assumptions

1. Footprints: cow_2 is 10x9 cells, zoo 12x8, mountain_2 14x9, igloo 10x8; cow_2 overlaps today's roads, so the layout redo must make room (assumed).
2. ZOOGATE unfolding (+1 palette): assumed acceptable if windows stay at 8; with all picks one window reaches 10. Needs the layout.
3. Cow blank cells on the COW palette: assumed possible in the generator.
4. Fence posts on Color for the mountain row: assumed layout re-adds them.
5. Zoo DMG window 178 to 180 over the 176 pool: needs the layout to move something or I trim.
