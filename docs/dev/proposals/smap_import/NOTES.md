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
