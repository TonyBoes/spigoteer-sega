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
| DMG tiles, whole map | 797 | 798 | 792 |
| worst 21x19 view (limit 176) | 143 at (39,8) | 143 | 143 |
| worst 22x20 view | 152 at (38,7) | 152 | 152 |
| flat tile uses in a 22x20 window (limit 239) | 238 | 238 | 238 |
| Color tiles / slots | 859 / 352 | 859 / 352 | 854 / 352 |
| palettes per 21x19 window (max 8) | 8, 0 windows over | 8, 0 | 8, 0 |
| palettes in a 22x20 window (not a limit) | 9 | 9 | 9 |
| palette table entries | 21 | 21 | 20 |
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

### Stage 1c review fixes
- Road corners: 13 of 24 rounded. The 5 corners whose outside-of-curve ground showed the road palette cream (sand at (2,27) and (2,61), snow at (61,13), cobble at (37,28), snow at (63,11)) are square again (roads_round.COLOR_CLASH); with the 6 earlier ones 11 stay square (3 palette-limited, 3 hold art, 5 colour clash).
- Ranges B and C stand on one continuous snowfield (snowfield.py): gaps between peaks filled, west edge steps one cell per row, grass tongue to the falls source, a snow fringe below B between the pines. Falls source untouched.
- Numbers: DMG 793/794/788, Color 850/850/845; views 143/152, palettes 8 per window (0 over), 22x20 region 9, table 20 (19 broken), flat uses 238.

### Stage 1c, owner Q113: "make all rounded and show me" -- all 24 corners round (supersedes the 13 of 24 above)
- New table entries: town1@n [snow, peach, lilac, ink] (igloo inner (61,13), outer (63,11)) and town1@z [zoo green, peach, lilac, ink] (inner (2,61)). Re-lay: 21 entries = 3 B each over the 18 of A5 less `tea`; story_scratch still fits (4 B spare of the 7 at 20 entries; 22 would leave 1 B). No new WRAM global.
- `tea` is gone from the table: its two cells (28,56) (29,56) had no index 0 pixel, so they look the same on tea@g (mapctx, zero visual change).
- Existing palettes used: base (sand ground, kerb 98a0b0 for a090b0) at inner (2,27); factory (kerb px 88a090) at (52,44); lodge (kerb px 905830) at (61,27); cow (kerb px e8e0f0) at (61,47).
- Art kept, kerb pixels only: factory (none overlap), cow pen (1 px of the fence top rail at cell (61,47) x5 y2), lodge wood pile (7 px: the pile`s bottom-right corner cell (61,27), x5 y5, x4 y6 x5 y6, x2..5 y7, become kerb).
- Compromises on Color (DMG clean everywhere): (35,44) grass cell, 7 kerb px in grass green; (37,46) and (50,46) keep town1, the outside-of-curve wedge is cream; the three art cells above. The south middle windows hold 8 palettes already, a ninth (town1@g) fails.
- Numbers: DMG 797/798/792 tiles, Color 859/859/854 in 352 slots, views 143/152, palettes per window 8 (0 over), 22x20 region 9, flat uses 238, table 21 (20 with the fountain broken).
- Sheets: sheet_1c_corners.png and sheet_1c_corners_2.png (24 corners x4 before | after, Color over DMG), sheet_1c_compromise.png (x6), sheet_whole_map.png.

### Smooth bends, step 1 (owner on Q113: "I was hoping for the curves to be smooth. Not just rounded.") -- shown, not applied
- bend_smooth.py: the bend of the 16 px road at outer radius 16 or 24 (inner radius R - 16: 0 and 8), constant kerb 2 / line 1 / body, staircases whose runs shrink toward the diagonal and are symmetric (3 3 2 1 1 1 ... for 24), specks following the curve. roads_smooth.py lays them on the 12 bends when env SMAP_CURVE=16 or 24 is set (not the default). curve_sheet.py makes the sheets.
- Cells per bend: R16 2 x 2 (the bend block; the inner corner stays square), R24 3 x 3 (adds two cells of each arm and the ground cell, which gets the inner radius 8).
- Numbers (dark water; square corners 779 DMG / 836 Color, today r8 797 / 859): R16 DMG 791 (+12 over square: 3 tiles x 4 orientations) / Color 853, table 20; R24 DMG 814 (+35) / Color 876, table 21. Worst 21x19 view 143 of 176, 22x20 152, palettes per window 8 with 0 over, flat uses 238 in all three.
- R16 fits all 12 bends. R24 fits 9; the other 3 hit art in the ground cell: bend (50,46) the factory yard (52,44), bend (63,29) the lodge wood pile (61,27), bend (63,45) the cow pen fence (61,47). R24 also rewrites the arm cells, so any later venue or decor on those arm cells collides.
- Color light line: the cream line needs a [ground, peach, lilac, cream] palette (roadg, roadn): +2 entries, 150 windows over 8 (R16) / 156 (R24), so it does not fit. On Color the bend cells that hold ground take the body colour for the line; DMG shows the line.

### Irregular ground seams (owner: "...the effect where you have kind of dithered the gas tiles so it does not look like a straight transition... applied to all the areas where two things meet")
The saloon edge (A5 biome rows 21..27, desert end 12 13 15 14 16 15 17) is a typed staircase of WHOLE ground cells: sand and grass never share a cell. So no mixed cell, no blend palette, no new tile. Same method on every straight run (seam_edges.py, typed rows before the world is built). Seams found by out/smap_import/seams2.py (runs of 3+ cells between two plain ground cells with different index 0).
| seam | cells | before | now |
|---|---|---|---|
| desert / grass, saloon NE | rows 21..27, x 12..17 | staircase (the model) | unchanged |
| grass / desert, saloon north | row 21, x 2..4 and 10..12 | straight, 3 + 3 | row 21 starts x3 and ends x11, row 22 x2..13 |
| desert / grass, airbase sand east | x 28|29 rows 30..33, x 31|32 rows 34..44 | straight 4 and 11 | rows 30..44 typed (ends 28 27 29 28 30 32 30 31 32 30 29 31 32 30 31), none east of x 32 (window x0 33 would gain a ninth palette) |
| grass / desert, airbase sand west | x 1|2 rows 30..44 | straight 15 | rows 30..44 start at x 2 3 4 (typed) |
| grass / jungle (zoo) north | y 49|50 cols 5..9, 11..16; y 50|51 cols 17..19 | straight 5, 6, 3 | rows 49..52 typed, bumps at 7-8, 11-12, 15-16 |
| grass / jungle west strip | x 1|2 rows 64..69 | straight 6 | rows 64..69 start x 2 3 4 |
| jungle / grass (zoo) east | x 20|21 rows 52..55, 57..59, 65..69 | straight runs, notches every 4th row | rows 53..69 end x 19 20 21 22, no rhythm |
| grass / snow (igloo) | rows 5..19, x 49..60 | typed steps (runs of 1 or 2) | unchanged |
| snowfield / grass under ranges B and C | rows 0..5, x 34..63 | stage 1c: stepped west edge, tongue, fringe | unchanged |
| grass / farm | rows 47..54, x 48..50 | typed steps | unchanged (the river bank, not a ground seam, runs along x 47 below) |
| forest / grass, desert / airbase sand, log yard / grass | | same ground colour | not a seam |
| lots (town cobble, stadium paved, bistro, tea, cow pen, factory yard), roads, water banks | | | left alone (not seams for this pass) |
No farm / meadow seam exists: the map has no meadow ground. On DMG sand and grass share the white ground, so a seam shows only as the tuft style changing; the stepped edge is there but quiet.
Numbers (dark / light / broken): DMG tiles 797 / 798 / 792 (the seams cost 0 tiles: the same flat and tuft tiles, only their cells move), worst 21x19 view 143 of 176, 22x20 152, Color 859 / 859 / 854, palettes per window 8 with 0 over in all three, table 21 / 21 / 20, flat uses 238. Sheets: sheet_seams_1.png and sheet_seams_2.png (before | after, x3, Color over DMG), sheet_whole_map.png.

### Stage 1d (owner Q115 and details) -- all shown, none applied. Light water is now the default (Q101); SMAP_WATERDMG=dark restores dark.
Env switches (mapctx.py): SMAP_CURVE=16|24|32|40|48|56|80|96|120|fit, SMAP_CURVE_TRIM, SMAP_BIG=A|B, SMAP_NO_CLUSTERS / SMAP_CLUSTERS=trees,bamboo, SMAP_NO_DESERT / SMAP_DESERT_PIECES=peaks,cacti,none, SMAP_STADIUM_BUSH_X (40 for r32 and up), SMAP_TILE_MAX.
- **Bigger curves (Q115).** bend_smooth.py now has rings for R = 16..120 (outer arc R, inner R-16, kerb 2, line 1; staircases whose runs shrink to the diagonal). The ring lists for R >= 32 came from a scratch dynamic-programming search (out/, not committed) and were pasted after review; the specks are hand-typed polar pairs. roads_smooth.py lays a patch only where its n x n cells are road arms or plain ground; it reports why each bend is skipped.
- Largest radius per bend (blocker is always a venue, art, prop, or the palette limit): (0,11) 40 with the stadium bush moved to x 40; (0,29) 24; (0,45) 96; (0,63) 24; (37,28) 120; (37,46) 24 (palette: the windows round (35,44) hold 8 already); (50,28) 24 (15 px grass prop at (53,30)); (50,46) 16, 24 with trim; (63,11) 40; (63,29) 16, 24 with trim; (63,45) 16, 24 with trim; (63,63) 24 (milk bar art).
- Trim (SMAP_CURVE_TRIM=1, r24): the road covers art only where it overlaps: factory 0 px, lodge 11 px (cell 61,27), cow fence 1 px (61,47).
- Numbers, light water, no other proposals (DMG / Color tiles, worst 21x19, windows over 8, table): none 798 / 859 / 143 / 0 / 21; r16 792 / 853; r24 825 / 885 / 143; r32 827 / 887 / 144; r40 834 / 894 / 148; r48 850 / 911 / 155; r56 854 / 915 / 156; r80 876 / 935 / 160 (all 0 over, table 21). "fit" (each bend its largest): 964 / 1020 tiles, FAILS: 3 windows over 8 palettes at (33..35,41), and Color is 4 tiles under the 1024 tile-id limit before any other proposal. So the whole-map fit set is not shippable as is; uniform r24 to r56 pass. The fit render is shown only to see the shapes (q115_whole_fit.png).
- Anti-aliasing test (SMAP_CURVE_AA): no visible gain at x1 to x3, so not shown.
- Palette compromises: desert-block interior cells in smooth bends use town1 (cream); the bends at (37,46) and (50,46) show that cream block.
- **Desert (owner).** desert_extras.py: five typed peaks (cone, twin, mesa, spire, slope, 14 to 30 px wide), 7 cacti (S, S2, Q, B barrel; 8 px wide), three sand spills across the road (north 27..25, south 47/48 twice). Whole small rocks touching a placement are cleared. Cactus palette `cactus` = [sand, grass 1..3] is a new table entry: 3 B, table 22 of 23, 0 windows over 8. DMG cost of all extras: peaks +37 tiles (worst view 150), cacti +6, spill 0.
- **Zoo bamboo and trees (owner).** clusters.py: fewer round trees between zoo and teahouse, eight typed bamboo clumps (TALL 16x24, MID 16x16, SMALL 8x14, cell aligned so tiles repeat), overlapping tree clusters (RR, RRR, PP, PPP, JJ composited back to front) replacing 16 singles. Bamboo +14 DMG tiles, trees +38. Flat tile uses 219 of 239 with all proposals.
- **Big mountain (owner).** big_mountain.py: 84 x 60 typed igloo-palette peak with a secondary summit, off-screen crop. A = top right corner, B = head of the river. Both fall only on igloo-palette cells. All proposals + A: DMG 919 / Color 980 / worst view 159 at (43,0); + B: 930 / 991 / 157; all with no big mountain 893 / 954 / 157; fountain broken + all 888 / 949. 0 windows over 8, table 22.
- **Light water animation (DMG).** Typed frames read through the light maps: glints and log bob fine; the falls column washes out (foam maps to the land shade). Needs one DMG-typed falls frame set in stage 2.
- Sheets: q115_stadium_close.png, q115_stadium_ctx.png, q115_biggest.png, q115_trims.png, q115_whole_fit.png, sheet_big_mountain_A_color.png and _B_color.png, sheet_desert_after_color.png, sheet_zoo_after_color.png. Raw runs: out/smap_import/mm/*.log.

### Stage 1e (coordinator review of 1d) -- shown, none applied
Replaces the big mountain, tree-cluster and bend-budget numbers of 1d above. The Color tile-id ceiling is 1024 (10-bit id in the cell word) and is the real limit: every table below carries it. Columns: DMG tiles / Color tile ids of 1024 / worst DMG 21x19 view (176 hard, flagged over 165) / windows over 8 palettes / palette-table entries. `generator ok` means the full generator passed; a Color count above 1023 makes it fail at the fog check, so those rows are counted only (SMAP_TILE_MAX=4096). Raw runs: out/smap_import/mm/e_*.log, table by mm_table.py.
- **Big mountain redrawn** (big_mountain.py, 84 x 44, hand-typed per-row outlines): main summit and a lower shoulder summit with a snow valley between, outline steps of 1 to 3 px with no repeated runs, lit/shadow face split along a ridge that jogs 1 px most rows (RIDGE_M, RIDGE_S), the shoulder's own left edge a diagonal ink line that dies into the main ridge (no vertical line), ragged snow caps on both faces, strata dashes, crevice marks, rock spurs on the lower slopes, ragged foot. A and B keep their places (top 4 rows, and for A 16 columns, off the map). The base is pasted behind the front-tier peaks; back-tier peaks under its silhouette are removed (the big one replaces them). Known limit: a front-tier peak that touches a back-tier one is one connected piece and goes with it, so on B no small peak stands over the foot; on A the left-hand ones do. Sheet s1e_bigmountain.png (A | B, Color and DMG).
- **Tree clusters** (clusters.py): tighter offsets so the front canopy covers the back trunk: round pairs (5,6), RR_L (6,0)+(0,6), RRR (5,0)(0,6)(9,6), pine pairs (5,6), PPP (4,0)(0,6)(8,6); new jungle clumps JJJ (128,440) and JJ (80,400) in the zoo (the other zoo candidates hit the zoo building or grass palette and were dropped). Sheets s1e_trees.png (east pines, lawn round, north pines) and s1e_zoo.png, before | after, Color and DMG. Clumps are 2 or 3 trees.
- **DMG versions** of desert (s1e_desert.png), zoo with bamboo (s1e_zoo.png), trees (s1e_trees.png) and the big mountain (s1e_bigmountain.png): every row pair is Color then DMG.
- **Bend budget, everything else on, mountain A, bush at x 40** (before curves, r8 corners: 926 / 987 / 162 / 0 / 22; with B 935 / 996 / 159):
| bends | DMG | Color of 1024 | worst | over 8 | generator ok |
|---|---|---|---|---|---|
| uniform r24 where it fits (9 bends) | 953 | 1013 | 166 | 0 | yes |
| uniform r40 where it fits (4 bends, others stay r8) | 960 | 1020 | 174 | 0 | yes |
| r40 with fallback to 32/24/16 (= the fit set, long sweeps off) | 978 | 1039 | 174 | 0 | no, 15 over |
| same, mountain B | 987 | 1048 | 159 | 0 | no |
| same, trim on | 976 | 1040 | 174 | 0 | no |
| r40 fallback + (0,45) r96 | 1027 | 1084 | 174 | 0 | no |
| r40 fallback + (37,28) r96 | 1027 | 1084 | 181 | 10 | no |
| r40 fallback + (0,45) r96 + (37,28) r96 | 1076 | 1129 | 181 | 10 | no |
| r40 fallback + (0,45) r96 + (37,28) r120 (the ask) | 1090 | 1146 | 188 | 33 | no |
| same, trim on, r96 + r96 | 1074 | 1130 | 181 | 10 | no |
Ways to buy room under 1024 (r40 fallback set, A): no tree clusters 938 / 999 / 174 / 0 ok; no desert peaks (cacti kept) 941 / 1002 / 174 / 0 ok; no bamboo 971 / 1032 no. With (0,45) r96 plus r40 elsewhere: needs bamboo + cacti only (no peaks, no tree clusters) 950 / 1007 / 174 / 0 ok; no extras at all 950 / 1003 / 163 / 0 ok. So the long sweeps and the full set of extras cannot both ship: pick which to drop.
- **Which bend breaks the fit map.** The largest-fit map (no extras) has 3 windows with 9 palettes at (33..35,41). Bisected: (37,28) at r120 is the cause. Same map with (37,28) at r96 (950 / 1003 tiles, 0 over) or r24 (910 / 967, 0 over) passes; dropping (0,45) r96 or (37,46) r24 changes nothing (still 3 over). Its patch reaches row 43, into the windows of the (37,46) bend. With everything on, (37,28) beyond r40 gives 10 windows over (r96) or 33 (r120).
- **Whole map** Color | DMG, light water, everything on, r40 with fallback (note: 15 Color tile ids over 1024), mountain A and B: s1e_whole_c40_A.png, s1e_whole_c40_B.png.
- **For stage 3: the DMG falls frames on light water.** The approved falls frames are typed for dark water (foam 1, water 2). On light water foam maps to 0, the land shade, and the falls column washes out. Stage 3 needs typed DMG foam frames (foam against water at the light shades) for the falls tiles; nothing to do now.

### Stage 1f (coordinator review of 1e) -- shown, none applied. These numbers replace the 1e tables, whose mountain and trees were older.
- **Big mountain cuts fixed.** A: the sliver was a back peak cut by the paste box edge; the box now widens to the nearest empty columns, so a peak is removed whole or left whole (the three peaks left of A's foot are gone, the others stay). B: the snow / grass edge ran 3 cells straight; one typed extra snow cell at (33,3) makes the west edge 36 35 34 33 34 by row. The cell takes the `igloo` palette (already present in the windows), no new tile pixels.
- **Round clusters redrawn** (clusters.py combo): each clump now has exactly one whole tree in front (one trunk); the others show only their canopy (rows 0..9 of the same tree, no trunk) above and to one side, and the front canopy's ink wins where they meet. RR_R, RR_L: canopy peeking up-left or up-right; RRR and JJJ: two canopies behind (left lower, right higher) and one whole tree in front. Pines unchanged. Sheets s1e_trees.png, s1e_zoo.png (before | after, Color and DMG).
- **Measures** (SMAP_TILE_MAX=4096, bush at x 40; DMG / Color ids of 1024 / worst DMG view / windows over 8; generator ok = the full generator passed, Color above 1023 fails it):
| run | DMG | Color of 1024 | worst | over 8 | ok |
|---|---|---|---|---|---|
| everything on, r8 corners, mountain A | 915 | 977 | 156 | 0 | yes |
| same, mountain B | 926 | 988 | 156 | 0 | yes |
| uniform r24, A | 942 | 1003 | 156 | 0 | yes |
| uniform r24, B | 953 | 1014 | 156 | 0 | yes |
| r40 fallback, all extras, A | 967 | 1029 | 159 | 0 | no, 5 over |
| r40 fallback, all extras, B | 978 | 1040 | 159 | 0 | no |
| Option C: (0,45) r96 + r40 fallback + bamboo + cacti + spill, no peaks, no tree clusters, A | 943 | 1000 | 154 | 0 | yes |
| Option C, B | 954 | 1011 | 153 | 0 | yes |
| Option A (read as r40 fallback, all extras): round clusters dropped (RR_R, RR_L, RRR, JJ, JJJ), pine clusters kept, A | 943 | 1004 | 159 | 0 | yes |
| same, B | 954 | 1015 | 159 | 0 | yes |
| same, only the lawn round clusters RR_R, RR_L, RRR dropped (jungle kept), A | 957 | 1019 | 159 | 0 | yes |
| uniform r24, round clusters dropped, A | 918 | 978 | 155 | 0 | yes |
The run scripts are in out/smap_import/ (run_meas11.sh), logs in out/smap_import/mm/f_*.log; table by mm_table.py. SMAP_SKIP_CLUSTERS=RR_R,RR_L,RRR,JJ,JJJ drops clusters by name.

### Stage 1g: saving Color ids under the 1024 ceiling (r40 fallback, all extras, mountain A was 1029, 5 over)
- Why single changes cost more: the Color tile set has no flip merging (a tile is its 64 pixels), so every bend orientation has its own tiles and bends of the same radius share them. One bend at r32 among r40 bends adds a whole new radius set: any one of the four long bends alone at 32 gives 1043 (+14), two give 1025. Only all four together saves.
- **Result: the four long bends (0,11), (0,45), (37,28), (63,11) at r32 instead of r40, everything else unchanged** (the other eight stay 24 / 16, all extras on, mountain A): DMG 960, Color 1022 of 1024, worst view 156, windows over 8: 0, flat uses 218, table 22; generator passes at the real 1024 limit (7 ids saved). Whole map: s1e_whole_s32_A.png. Not invisible: those four bends are 8 px tighter than the r40 shown to the owner.
- Tried and no help: the three r16 bends (50,46), (63,29), (63,45) left at the r8 corner (1029, same count: their tiles are shared), each of them at r16 only, trim at r24 (+1).
- Mountain B on the same set: DMG 971 / Color 1033 / worst 156, fails (B costs 11 ids more than A). Cheapest ways to give B room: drop the round tree clusters (about 25 ids), or the desert peaks (about 37), or take the long bends to r24 (uniform r24 with B is 1014).
- Mountain B's right foot ends in a straight vertical ink edge against the grass; to be fixed only if B is picked.

### Stage 1h: no bend at r16 (owner: r24 is the minimum). Replaces the 1g option sets.
(50,46), (63,29), (63,45) go to r24 with the trims (factory 0 px, lodge 11 px in cell (61,27), cow fence 1 px in (61,47)); every bend is now r24 or larger (mapctx SMAP_RADII "x,y:24!" means exactly that radius, else the bend keeps the r8 corner; all 12 bends laid in every run below). Mountain A, bush at x 40, trims on. DMG tiles / Color ids of 1024 / worst DMG view / windows over 8 / generator at the real 1024 limit:
| option | DMG | Color | worst | over 8 | gen |
|---|---|---|---|---|---|
| A': four long bends (0,11) (0,45) (37,28) (63,11) at r32, the other eight at r24 with trims, all extras (peaks, cacti, spill, bamboo, tree clusters) | 958 | 1023 | 156 | 0 | passes |
| C': (0,45) r96, the other three long at r40, the other eight r24 with trims, bamboo, cacti, spill, no peaks, no tree clusters | 941 | 1001 | 154 | 0 | passes |
| C' + pine clusters | 953 | 1013 | 159 | 0 | passes |
| C' + pine + round clusters (RR_R, RR_L, RRR, JJ, JJJ) | 977 | 1038 | 159 | 0 | fails (15 over) |
The round clusters cost 25 ids, the 10 ids of room after the pines do not cover them; no subset was tried. Sheets: s1e_whole_Ap.png, s1e_whole_Cp.png, s1e_whole_Cp_pine.png (Color | DMG), s1e_trims.png (lodge and cow, r8 corner without trim | r24 with trim, Color and DMG, x4). The factory yard needs no trim at r24 (0 px).

### Stage 1i: A' is the default map (owner Q115 a, Q113 yes, Q117 larger window)
- **Default.** mapctx.py now builds A' when no switch is set: the four long bends (0,11) (0,45) (37,28) (63,11) at r32, every other bend at r24 with the trims, all extras, big mountain A, stadium bush at x 40, light water. build.py and measure.py use it unchanged. Overrides: SMAP_CURVE=none (r8 corners), SMAP_CURVE=24, SMAP_BIG=none|B, SMAP_CURVE_TRIM=0, SMAP_RADII=.... Default run at the real 1024 limit: DMG 958, Color 1023, worst view 156, 0 windows over 8, table 22, generator passes. Stage 2 not started (the owner's go is pending).
- **B's right foot fixed**: the outline ran 8 rows straight at x 83; the mountain is now 90 wide and the right edge keeps flaring diagonally to the foot (83 84 85 85 86 87 87 88). B: DMG 969, Color 1034, 11 over A'.
- **Windowed views** (window_view.py): 40 cells wide, 20 tall, centred on the mountain, x4 (1312 px wide; x2 would be 640 px), Color above DMG: s1e_window_A.png (cells 24..63), s1e_window_B.png (cells 20..59).
- **Cheapest ways to fit B** (each from A' plus B, Color ids; limit 1023): drop the desert slope peak and the S cactus: 1023 (passes); drop the lawn round clusters RR_L, RR_R, RRR and the jungle JJ: 1018 (passes); drop all tree clusters: 997; the four long bends at r24 instead of r32: about 1007 (visible, the owner wanted bigger curves). Not applied.
- **Savings on A' for the teahouse pass** (measured one at a time, ids saved; none is invisible, each removes something shown): cactus Q or barrel 1, cactus S or S2 2, bamboo SMALL 3, TALL or MID 6, pine cluster PP or PPP 6, peaks mesa 6, cone 7, spire 7, twin 8, slope 9, lawn round cluster RR_L 8, RR_R, RRR, JJ, JJJ 1 each, spill 0. Combined, and not additive: RR_R + RRR + JJ + JJJ together 17 (1006), all five round clusters 25 (998); four long bends at r24 27 (996, visible). Cheapest, least visible: revert RR_R, RRR, JJ, JJJ to their single trees (17 ids). No invisible saving exists: the Color tile set has no flip merging and no duplicate tiles.

### Stage 1j: mountain B chosen (owner Q117: "I like b more, but waterfall should be coming out of mountain")
- **Placement.** B moved 32 px east (x 312..401, top 4 rows off the map) so its right flank stands over the head of the falls. It stands over the remaining back-tier range peaks and behind the remaining front-tier ones; five range peaks that stand mostly inside its outline are taken out and their neighbours repainted whole (REPLACED_B: back x 320, 352, 384, front x 304, 336). The right foot keeps its diagonal flare (no vertical edge). No river is drawn above the mountain.
- **Falls from the mountain** (falls_cave.py, typed): a rock ledge steps down from the foot to the falls' top row (map row 5, y 40..47, x 360..391, flaring edges), with a dark cave mouth (10 px wide, 12 rows from y 36, widening 6 / 8 / 10 px, two deep flecks) over the channel (x 371..380). The water comes out of the dark in the mouth's bottom four rows (the first in shadow) and drops into the untouched falls tiles of row 6 and the pool. The two falls cells of row 5, (46,5) and (47,5), and the ledge cells (45..49,5) take the `igloo` palette (flow pixels in the DMG light indices: foam 0, water 1; on Color pale blue 104 168 216 against the water palette's 88 160 216). The grass tufts and a bush that stood in those cells go.
- **Animation.** The approved falls streaks (FALL_COLS, step 3 rows, 4 frames, 9 video frames a step, copied unchanged) run through the mouth. The two row-5 cells keep 4 images each (frame 0 is the map tile) and now carry the rock and mouth pixels: 6 animation images, the same count as the approved FL_A and FR_A, so +0 extra images and +0 animated cells. DMG VBlank peak per view is unchanged at 6 tiles (96 B, the igloo view). Map tile cost of the cave: +2 Color and +2 DMG ids over B without it. falls_frames.py makes the strip and GIF (s1e_falls_strip.png, s1e_falls_anim.gif, x6, Color above DMG). On DMG light water the row-6 falls and the pool stay flat grey (foam and water share the light shade): the stage 3 note on typed DMG foam frames still stands.
- **Numbers, A' with B and the falls from the mountain** (DMG / Color ids of 1024 / worst DMG view / over 8): 973 / 1038 / 170 / 0, 15 over the 1023 maximum (generator fails); the teahouse at +1 makes 1039, 16 over. B without the cave 971 / 1036. The worst DMG view is 170, over the 165 flag and under 176. (A' with A for reference: 958 / 1023 / 156.)
- **Ways under 1024** (each measured with B + cave; the teahouse +1 is on top; none applied):
| way | what visibly goes | DMG | Color | with teahouse +1 |
|---|---|---|---|---|
| four round clumps back to single trees (RR_R, RRR, JJ, JJJ) | those four clusters (the RR_L lawn pair and the pines stay) | 957 | 1021 | 1022 |
| two desert peaks out: twin and slope | the two biggest peaks beside the airbase | 956 | 1021 | 1022 |
| one peak and one cactus: slope and S | only the slope peak and one cactus | 962 | 1027 | does not fit |
| the four long bends at r24 instead of r32 | the four sweeping curves are 8 px tighter | 946 | 1011 | 1012 |
| slope and cone peaks out | two peaks | 957 | 1022 | 1023 |
| four round clumps and the S2 cactus | one cactus more | 955 | 1019 | 1020 |
The rework itself frees nothing: the river cells it covers had no tiles of their own. mapctx.py now defaults to B, so the default map fails the generator by 15 until the owner picks one of these.
- Sheets: s1e_window_B.png (40 x 20 cells, x4, Color above DMG), s1e_falls_strip.png and s1e_falls_anim.gif.

### Stage 1k: the approved foam is back, DMG light-water falls typed (owner: "What happened to the foam and such I approved earlier?")
- **What was wrong.** The integrated map never carried the approved falls art (it lives in smap_anim as new static tiles), and stage 1j's strip drew the lower falls without the approved foot rows, the foam lip and the pool glints. falls_cave.static_art now pastes the approved frame 0 into the map: row 6 (streaks and the foot rows 12..15), the foam lip cells (46,7) and (47,7), and the glint tiles at (46,8) and (47,8) (the splash arcs go). The art is read from smap_anim/items.py itself (fall_rows, foot_tile, WS), so it is the approved art exactly, same frames and timing (falls step 9 video frames, lip 6 frames after it, glints on their 30-frame pace). The column starts at the cave mouth: the approved rows 4..15 are visible (rows 0..3 are inside the cave).
- **DMG light water, typed now.** Foam and land 0 (248), water 1 (168). The approved streaks read as grey on a light column; the one addition is the bank rim of the falls column (cell column 3 left, 4 right, rows 5 and 6), which reads 1 on DMG so the column keeps an edge against the white land (`falls_cave.to_dmg`). The lip is foam 0 against the pool's 1: its ragged lower edge and the drifting specks show, its sides melt into the land as the pool does. The pool glints are 0 dashes on 1.
- **Animation images: unchanged.** The same approved cells animate (FL_A, FL_B, FR_A, FR_B with the two row-5 cells now carrying the mountain, the foot lip cells, two glint tiles), no extra images or cells; DMG VBlank peak stays 6 tiles (96 B) in the igloo view. The DMG frames are the same tile count as the Color ones (typed through to_dmg), so nothing is added.
- **Other water animations on DMG light water** (anim_light.py, unchanged): pond and lake glints are 0 on 1 (step 80 in DMG shade units, visible); the floating logs keep their white waterline against 1 and the dark body (max change from rest 224). Nothing went flat, nothing changed.
- **Numbers**, B + cave + approved falls static art on A' (DMG / Color / worst DMG view / over 8): 975 / 1040 / 171 / 0 (the pasted approved tiles add 2 over the 1j count; 1040 is 17 over the 1023 maximum once the teahouse +1 is added). Ways under, measured now with the teahouse +1 on top (must be at most 1023):

| way | what visibly goes | DMG | Color | with teahouse +1 |
|---|---|---|---|---|
| four round clumps back to single trees, and one cactus (S) | the 4 clumps and one cactus | 957 | 1021 | 1022 fits |
| four round clumps back to single trees, and the slope peak | the 4 clumps and one desert peak | 950 | 1014 | 1015 fits |
| twin, slope and S out | two big peaks and one cactus | 956 | 1021 | 1022 fits |
| four long bends at r24 instead of r32 | the four sweeps 8 px tighter | 948 | 1013 | 1014 fits |
| four round clumps alone | the 4 clumps | 959 | 1023 | 1024 does not fit |
| twin and slope out | two peaks | 958 | 1023 | 1024 does not fit |
| slope and cone out | two peaks | 959 | 1024 | does not fit |

- Sheets: s1e_falls_strip.png (falls steps 0..3: cave Color, cave DMG, approved 02_falls Color, approved DMG, x6), s1e_falls_anim.gif (50 ms a picture, the 180-frame loop, cave left and approved right, Color above DMG), s1e_window_B.png.

### Stage 1l: audit of every approved animation item against the integrated map (coordinator, after the falls)
Method (audit_anim.py, audit_verify.py): the items of smap_anim/items.py are built on a scene read from the integrated map. Building an item applies its NEW STATIC tiles to that scene and some items carry `edits`; the pixels that differ between the map and the scene afterwards are exactly the approved frame 0 art the map lacked. anim_static.py pastes them (Color: the typed index; DMG light water: glint and water cells 1 to 0, 2 to 1; log cells keep the map's own DMG rows for every row the sunk pose shares with the old tile and type the new waterline foam 1 to 0, 2 to 1; lodge and cows are the same indices on DMG). mapctx runs it last (SMAP_NO_ANIM_STATIC=1 turns it off, anim_light.py needs that). audit_verify.py then checks, for every tile animation, that the cells the engine table rewrites hold exactly the approved frame 0 tile.

| item | in the map before | animated cells (after the paste) | pasted |
|---|---|---|---|
| 01 water shimmer, pond glints (WA, WB) | no (old glint art) | 40: (40,53) (40,61) (40,66) (40,69) (41,53) (41,54) (41,66) (41,67) (42,51) (42,53) (42,59) (42,66) (43,51) (43,56) (43,60) (43,69) (44,55) (44,56) (44,59) (44,69) (45,42) (45,48) (45,49) (45,52) (45,55) (45,61) (45,65) (46,15) (46,16) (46,28) (46,35) (46,38) (46,51) (46,67) (46,68) (47,33) (56,34) (57,33); pool (46,8) (47,8) by falls_cave | the 40 cells, new glint tiles |
| 02 falls, lip, pool glints | no | row 5 two cells, (46,6) (47,6), lip (46,7) (47,7), (46,8) (47,8) | stage 1k |
| 03 fountain streams and basin | yes | (36,24) (37,24) (36,25) (37,25) | none |
| 04a bunting | yes | (33..39,20) | none |
| 04b stadium flag | yes | (7,1) (8,1) | none |
| 05 airbase dish and lamp | yes | (9,36) dish, (8,36) lamp (airbase at (4,34)) | none |
| 06a lodge smoke | no (old tan puff) | (58,19) (59,19), palette water; tan puff in (58,20) (59,20) erased | 4 cells |
| 06b factory smoke | yes | (60,37) (60,38) (61,38) (52,37) (52,38) (53,38); (60,37) and (52,37) start from blank sky | none |
| 06c igloo smoke | yes | (56,5) | none |
| 07 cow tails | no (cows had no tail) | (55,49) (59,52) | the two tail cells |
| 09 six logs half-submerged | no (old floating pose, 12 log cells) | across (42,52) (43,52) (43,57) (44,57) (44,68) (45,68), upright (45,43) (45,44) (46,20) (46,21) (46,29) (46,30); the 6 removed logs are plain water: (48,33) (49,33) (54,33) (55,33) (57,32) (58,32) (42,65) (43,65) (45,46) (45,47) (46,36) (46,37) | 28 log cells |

The approved pieces (stadium BLEND, fountain working and broken, airbase 4i, igloo option 1, milk bar) are in the map through their scenes: no differences. The fountain was audited in its working state (the default); the broken state was not audited. Sheet: s1e_anim_static.png (sunk logs, a removed log, lodge smoke, cow tail, glints; Color above DMG). On DMG light water the sunk logs keep a white waterline and the dark body, the glints are light on mid grey.
Animation images: no change (this only puts frame 0 in the map). DMG VBlank peak per view: unchanged, 6 tiles (96 B), the igloo view.
Own tile ids: the two factory cells (60,37) and (52,37) start from the shared blank sky tile, so the engine table needs an id of their own each: +2 ids on top of the measured count (the approved report lists lodge, factory and cows for this; only the factory's two are blank now).

**True total** B + cave + approved falls + the pasted art, A' (measured 974 DMG, 1039 Color, worst DMG view 170, windows over 8: 0, worst palettes 8): 976 DMG and 1041 Color with the two factory ids; with the teahouse +1, 1042 Color, 19 over the 1023 maximum. Ways under (measured; true = measured + 3 for the factory ids and the teahouse; must be at most 1023, so measured at most 1020). None applied, the owner picks:

| way | what visibly goes | DMG | Color | true Color |
|---|---|---|---|---|
| four round clumps back to single trees, plus the cactus S | the 4 clumps, one cactus | 956 | 1020 | 1023 fits |
| four round clumps, plus the slope peak | 4 clumps, one desert peak | 949 | 1013 | 1016 fits |
| four round clumps, plus the cone peak | 4 clumps, one desert peak | 951 | 1015 | 1018 fits |
| desert twin, slope and S out | two big peaks, one cactus | 955 | 1020 | 1023 fits |
| four long bends at r24 instead of r32 | the four sweeps 8 px tighter | 947 | 1012 | 1015 fits |
| four round clumps alone | the 4 clumps | 958 | 1022 | 1025 does not fit |
| desert twin and slope out | two peaks | 957 | 1022 | 1025 does not fit |
