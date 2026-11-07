# Story map import, stage 1: one integrated proposal (nothing in src/ or assets/)

Rebuild: `python3 -I docs/dev/proposals/smap_import/build.py` (about 2 min; writes under `out/smap_import`; the A5 scratch `smap_layout_a5/src` it regenerates is untracked).
Files: `mapctx.py` (the integrated world), `dump_scenes.py` + `scenes/` (the pieces as cell lists), `measure.py` (A5 generator on the integrated world), `renders.py`, `anim_run.py` (the approved animation build on this map), `numbers/*.json`, `sheet_whole_map.png` (Color | DMG dark | DMG light, x2), `sheet_pieces_1..5.png` (approved sheet | integrated close-up x3, Color, DMG dark, DMG light for water pieces).

## Merges (all `--no-ff`, no conflicts)
A5 (2b2fce68), anim (dc5c1781; it already contained fountain, stadium, igloo, airbase, milk bar and A5 via its own merges), milk bar (353dde97), stadium BLEND 8950c018 (PLAZA a2bbbc76 is NOT in), fountain 8608d684, airbase e898c707 and igloo (already ancestors: "Already up to date"). Git never conflicted. The choices live in the composition (mapctx.py):
- Cells two pieces touched: only the stadium's five right-hand field cells (11,5) (11,6) (11,7) (12,6) (12,7) (the BLEND palette edit over the paste: GRASS palette, as approved). No other piece overlaps another.
- Cells overwritten from A5: igloo 37 ground + 15 ROAD cells (the piece's lower rows carry its own snow drifts and a road strip over the road's north border; road centre strip kept, Sal's path should still walk, stage 2 to confirm), milk bar 113 ground + 20 ROAD cells (the lot; generator venue-over-road assert needs the lot exemption, as briefed) + 1 cow venue cell, airbase 131 ground + 3 decor, stadium 91 ground + 1 venue, stadium walkway edits 7 ground + 2 road, tea cell (34,59) tea to tea@g.
- Milk bar: final build (sign B raised, 4 px left, 104 px wide picture at cell (49,47)), body on `base`, pasture replaces the hay field.
- Airbase moved (see below).

## Placeholder boxes (owner: "Nope the maps got those big stand in rectangles.") -- fixed in the second commit
Boxes left on the integrated map after stage 1: only the three hatched RANGE boxes of A5 (`lay.RANGES`): A cells (17,0) 15x4, B (34,0) 14x5, C (48,0) 16x5 (assumed 26, 30, 36 tiles, palette igloo). The space lounge (`ph_space` 22x12 at (10,33)) and the ballpark (`ph_stadium`) boxes were already replaced by the airbase and the stadium; every other venue (bistro, igloo, saloon, lodge, factory, zoo, tea, town, cow) is real art. No placeholder without approved art remains.
Ranges now: the round 3 peak (`smap_venue_redesign3/src/mtn_vert.py`, owner 11-06), pasted by `dump_scenes.py range_a|b|c`, nothing redrawn. A (4 rows) one staggered row, desert (saloon palette), peaks at px (0,8) (24,0) (48,8) (72,0) (88,8); B (5 rows) two tiers, snowy: back (16,0) (48,0) (80,0), front (0,16) (32,16) (64,16); C (5 rows) two tiers, snowy: back (0,0) (32,0) (64,0) (96,0), front (16,16) (48,16) (80,16). Pasted back (higher) to front, cells with no peak pixel keep the map ground; the falls and river source (rows 5 and below) are untouched. Choice: desert only for A (above the bistro), B and C snowy next to the igloo and the snow edge. Doubt: partly filled cells carry the range palette's ground (sand or snow), so the desert range shows a sandy halo on the grass (a palette with grass as index 0 would turn the caps green; not done).
Tiles: DMG 749 (was 758 with the boxes), range pieces cost less than the boxes' assumed 92; palettes per 21x19 window 8 (worst at (25,1)), 0 over; 22x20 region 9; table 20 entries (19 with the fountain broken); generator OK.

## Two forced choices (supervisor please look)
1. **Airbase at cell (4, 34)** (was (6, 36) in the animation import, dump position (9, 36)). Reason A: the milk bar sign now puts a COW cell at x 49, which, with the airbase's `base` cells at x 29..30, made 12 windows hold 9 palettes (tea, base, cow, tea@g, farm, saloon, town1, water, grass). Two cells west clears them (0 windows over). Reason B: replacing A5's 22x12 placeholder (70 distinct tiles) with the sparse picture left a 259-cell flat tile in a 22x20 window (limit 239). Fix: the airbase's all-blank cells keep the map's own desert ground (mode nonblank: ground tufts show; base and saloon share index 0 f8e090, so Color is unchanged) and the piece sits 2 cells higher (rows 34..42, two sand rows between the runway and the road): 238. y 35 gives 243, y 36 gives 247 (fail). Alternative if the owner wants it on the road: about 8 more desert decor cells above it. The animation items follow (airbase item rows/view moved by text patch in `anim_run.py`).
2. **Palette table is 20 entries, not 19**: A5's 18, plus PARK (stadium) and `base` (airbase + milk bar body; A5 had spent `base` on town1@g). In the BROKEN fountain state `town4` is unused (19 entries), but the working state needs it. story_scratch re-lay needs +6 B for 20 (free: 2 B at 238..239 and 9 B at 291..299, so it still fits: A_PSLOT 214, A_PUSE 234, A_ATTR_UI 242, A_IDA 262, A_PSTG 284 ends 293, 7 B before A_XSTG 300; verify in stage 2).

## Numbers (A5 generator on the integrated map)
| | DMG dark, fountain working | DMG light | DMG dark, fountain broken |
|---|---|---|---|
| DMG tiles, whole map | 796 | 797 | 791 |
| worst 21x19 view (limit 176) | 143 at (39,8) | 143 | 143 |
| worst 22x20 view | 152 at (38,7) | 152 | 152 |
| flat tile uses in a 22x20 window (limit 239) | 238 | 238 | 238 |
| Color tiles / slots | 854 / 352 | 854 / 352 | 849 / 352 |
| palettes per 21x19 window (max 8) | 8, 0 windows over | 8, 0 | 8, 0 |
| palettes in a 22x20 window (not a limit) | 9 | 9 | 9 |
| palette table entries | 20 | 20 | 19 |
Generator: BUDGET OK, 0 cells snapped (it asserts every cell's palette is in the table), hint conflicts 0. A5 alone was 562 DMG tiles, worst view 133. The Color-only parts: the tea cell, the 20-entry table; DMG has no palette limit, its budget is the tile pool above.

## Animation (the approved items on this map; DMG and Color the same tile bytes)
104 new tile images in ROM (water 6, falls and foot 38 incl. 6 replacing static tiles, fountain 6, bunting 6, stadium flag 4, airbase 4, lodge smoke 8, igloo smoke 3, factory 15, cow tails 6, logs 8), 14 new tile ids (lodge 2, factory 2, cows 2, logs 8), 11 items. DMG VBlank peak, tiles (16 B each) per view: river top 5 (80 B), town 5 (80), lodge 3 (48), factory 3 (48), milk bar 2 (32), airbase 1 (16), stadium 2 (32), igloo 6 (96, the worst real view), river scrolled 5 (80), logs 3 (48); everything at once 21 (cannot happen). Identical to the animation notes, so nothing on the integrated map changed the cadence. The fountain's streams animate only in the working state.

## Doubts
- 749 DMG tiles whole map (A5 562) is the real cost of real art over the placeholders; the engine pool per view is fine (143 of 176).
- The 22x20 palette count of 9 is the loaded region, not a screen; the generator does not check it. Stage 2 should confirm the engine only needs 8 for what is shown.
- Igloo/road overlap and the flat-tile fix above are layout judgement calls.
- Stage 2 not started; no engine files touched.

## Stage 1c (owner: "Round the corners on the road. Also need a little bit of variation in mountain tiles. Don't need mountain above bistro.")
- Road corners: 18 of 24 rounded, outer arc radius 8 with the kerb following it, inner ground corner radius 6; hand-typed NW tiles, other three by flips (roads_round.py). Outer cells use town1@g, ground cells town1 or town1@g: no new palette, table stays 20. Color curve has no cream line (a new palette broke the 8-per-window limit).
- Left square: (35,44) (37,46) (50,46) (palette-limited windows) and (52,44) (61,27) (61,47) (cells holding art).
- Range A removed; the ground is grass with five pines (same density). Bush (16,104) moved to (24,104).
- Ranges B and C: four peak variants (approved peak, typed single summit, shorter, taller), mixed so no two neighbours match (range_peaks.py).
- Numbers dark/light/broken: DMG tiles 796/797/791, Color 854/854/849 in 352 slots; worst 21x19 view 143, 22x20 view 152; palettes per window 8, 0 over; 22x20 region 9; table 20 (19 broken); flat uses 238. Cost: roads +17 tiles, ranges +30.
- Doubts: 6 corners stay square; pale cream patches where the ground is sand/snow/zoo green; ranges B and C sit on snow-coloured ground.
- Sheets: sheet_1c_corners.png, sheet_1c_ranges.png, sheet_whole_map.png.
