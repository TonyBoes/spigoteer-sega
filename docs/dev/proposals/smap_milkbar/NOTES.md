# Milk bar round 4e (current): the same lot and 3/4 bikes, checked in the A5 layout

Owner: "Milk bar maps are not helpful as they are not the current layout." `milkbar_sheet5.png`: the milk bar alone (DMG, Color x3), then in the A5 map around it (DMG, Color x3). The map shots come from the A5 scratch generator (`docs/dev/proposals/smap_layout_a5/src`, rebuilt with its `mk_src.py` and `mk_a5.py`, env `SMAP_LAYOUT=lay_A5 SMAP_FOG=none`; `src/a5env.py` here sets that up, `src/sheet5.py` renders). Art unchanged from round 4d (`src/cow_lot4.py`): building, sign and cow identical, 3/4 bikes, slanted bays.

**Where it sits in A5.** Venue cell (50, 55) on the 64 x 70 map: the piece covers cells x 50..61, rows 55..63. The road that passes it is the ring road's south lane, cell rows 62 and 63, running west to the tea house and east to the ring's east edge road (cells x 62 and 63, running north). The lot rows of the piece (y 56..71) are those two road rows, as in the old layout, so the answer is the same: the lot is the south lane widened up to the diner (road tiles, TOWN1 on Color: no new palette; the road's south kerb runs straight through; the north kerb ends at the lot's west edge, x 54). What is better in A5: the lot's east end (cell x 61) meets the east road's junction (x 62, 63) head on, so the lot is a bay along the lane between the junction and the cow.

**Re-check of the fit issues in A5**
1. Piece width: **fixed by A5.** The block east of the old piece is free: the building ends at x 59 (old 80 px piece) and cells x 60 and 61 are free ground before the east road at x 62; the 96 px piece needs exactly x 50..61. It fits (in the old layout it did not).
2. Cow on road cells: **still open.** The cow (piece (18, 58)) stands on cells x 52 and 53, rows 62 and 63, which are road cells; the map shot draws it over the road. The cow must move up a row or those two cells need a cow-over-road look. Also `STOP_LOCAL_X["cow"] = 18` puts Sal's stop at x 418 = cell 52, right under the cow.
3. Venue-over-road assert (`assert (cx, cy) not in self.roads` in `world2.build`): **still fires**, the piece covers road cells x 54..61 (lot) and x 52, 53 (cow), rows 62, 63. The lot and cow cells need an exemption, and the engine must keep the lot cells walkable, because the cow-to-tea leg walks along feet row y 508 (cell row 63), through the lot.
4. Palette windows: the lot cells use TOWN1, which the road already uses (the generator's windows are 8 at worst there), the building's cells stay COW; no new slot. I did not re-run the generator's window probe with the piece in place (the A5 scratch generator pastes the old 80 x 56 `v_cow`, so the real check needs the 96 x 72 piece wired into a layout).

**Tiles (DMG, project counter):** the piece 45; the old `v_cow` that A5 pastes today is 44 and round 3's milk bar is 44, so +1. The map totals (A5 547) were not recomputed with the piece pasted.

Rounds 4c/4d below are kept for history; their map shots use the old layout and are superseded.

# Milk bar: round 4d (current): 3/4 bikes, the lot joined to the road (proposal only)

Owner: "The bikes need to be 3/4 angled toward venue. Parking lot is ok, but needs to be logically connected to the rest of the map." Sheet: `milkbar_sheet4.png` (round 4c A | NEW; DMG and Color at x3; then both in the real map around the milk bar, x3). Sources: `src/cow_lot4.py` (art), `src/sheet4.py` (renders the map shots from `world2.WORLD`). Building, bottle, cow: round 3 pixel for pixel (0 changed outside the lot rectangle).

**How the lot joins the road.** The trunk road runs on cell rows 30 and 31, which are exactly the piece's lot rows (y 56..71), so the lot IS the road: the road widened to the diner with its north kerb removed. Paving is the game's own road tile rows (`tiles.ROAD` F1 speckle above, the ES south edge below: body, white line at y 69, kerb at y 70 and 71), so the south edge runs straight on into the road at both ends, and the road's north kerb simply ends where the lot begins (the mouth of the driveway). **On Color the lot cells use the road's palette TOWN1** (cream, skin, lilac, ink), which the road already uses: no new slot. On DMG it is the road's own speckled mid-grey. The bays are painted on the road: white lines at 45 degrees, leaning up and right toward the door, 20 px apart, and the bikes park between them.

**Bikes.** Three typed 3/4 bikes heading up and right toward the door, seen from behind and the left: the rear wheel a tall ellipse at lower left, the front wheel a smaller ellipse at upper right, bars with mirror tips over it, fork, tank (lit stripe), seat, engine block and exhaust between. 16 x 12 px, all three are the same drawing (copies of my own). Open-ring wheels so the road shows through and they read as wheels.

**Unique DMG tiles** (project counter; round 3 = 44): NEW **45** (+1); lot cells only 11 against round 3's 10. (4c A was 40.) The lint counts 46 (it counts the blank cell). Lint PASS DMG and Color; warnings are the road tile's own speckle (orphans, the game's tile), the bar corner L-doubles and the bottle's, unchanged.

**What the map shot shows, and what has to be fixed in the import round (not fixed here):**
1. The piece is 96 x 72, 12 x 9 cells at (39, 23); the block between the two roads is 11 x 7 cells (x 39..49, rows 23..29), and the old Chrome Cow piece was 80 x 56. The piece's last cell column (x 50) sits on the N-S road (x 50, 51): in the shot the N-S road narrows to one cell beside the building, and the lot's last cell overwrites the junction cell. The building (or the piece) is one cell too wide for this block; I did not trim it (the building must stay identical).
2. The cow stands at piece (18, 58), on cells x 41 and 42, rows 30 and 31, which are road cells: the shot draws it over the road (its meadow index 0 left transparent). In the game those two cells need the cow moved up to the meadow, or the cow's cells given the road's palette.
3. The lot's rows 30 and 31 replace road cells x 43..50: the walkable road under the diner stays walkable only if the engine treats the lot cells as road (Sal's feet line is y 252, inside the lot's lower row). The generator's `assert (cx, cy) not in self.roads` fires for this piece; it needs the lot cells exempt.

**Self-audit (round 4d).**

| check | result |
|---|---|
| Hand-placed | Bike rows, the two wheel rings and the bay-line formula (45 degrees, typed offsets) are in `src/cow_lot4.py`; the paving rows are the game's own road tile rows, copied. The wheel's size was found with a scaffold first (a rotated-ellipse printout in `out/mb`, not delivered); the delivered wheels are typed rings, not the scaffold. |
| Clean-up pass by hand | Done. Log: first draft (5 x 5 diagonal wheels with a white plus hub) read as dice and the bike as a blob: replaced by open rings; second draft (12 x 12, wheels touching the body) still a blob: wheelbase opened up to 16 x 12; bay pitch 22 did not fit three bikes in 64 px: 20; the bike was moved right inside its bay so the tank does not touch the bay line. |
| 1x comparison with the quality bar | Against round 3's bikes at 1x in the same sheet: the new bikes are smaller and ruder (12 px tall); they read as motorcycles heading up and right, not as clearly as round 3's side views. This is the weakest part. |
| Squint test | The road reads first, the lot is clearly the road, three dark bikes on it. |
| Palette | TOWN1 for the lot cells, COW for the building: no new slot. |

Earlier rounds below are kept for history.

# Milk bar: lot and bikes, round 4c (proposal only; supersedes the earlier sheets in this folder)

Owner: "Milk bar perspective seems off on both because it doesn't match anything else really.  Ideas?" The whole map is front-on with a little top showing, so no top-down and no sheared bikes. `milkbar_sheet3.png` is the current sheet: round 3 | A | B | C, DMG row and Color row at x3, then lot close-ups at x4. (`milkbar_sheet.png`, `milkbar_sheet2.png`, `milkbar_options_*.png` are earlier, superseded rounds kept for history.) Sources: `src/cow_lot.py` (art), `src/sheet.py`, `src/export.py`; `common.py`, `kit.py`, `cow_c.py`, `cow_a3.py` are round 3's files with `ROOT` pointed at this worktree. Nothing in `assets/`, no goldens.

Building, bottle sign and cow: round 3 pixel for pixel (0 changed pixels outside the lot rectangle x 32..95, y 56..71, checked in `sheet.py` for A, B and C).

## The three proposals (all front-on)

- **A rear view.** Three bikes seen from behind, nose-in to the diner: mirrors, a front tyre peeking between the stalks, wide bars, tank, seat, tail light, fender, a narrow dark rear tyre. Two drawings (chunky, slim) in bays 1, 3, 5. The lot is a shallow strip of grey paving (shade 1) across the diner's width, a shade row under the diner, short white bay lines (y 63 to 71) running up toward the diner, open front, no outline.
- **B side view in a row.** Three side-on bikes along the front (round 3's bike layout redrawn: ink tyres with a white rim, tank with a lit stripe, seat, engine block, fork, headlight, bars), the middle one a chopper with a sissy bar, 2 px lower (nearer) and in front of its neighbours, each bike touching the next by about 1 px. On the same grey strip, no bays, no outline.
- **C props, no lot.** Two side-on bikes (plain and chopper) on kickstands on the meadow beside the door. No paving at all.

## Palette (Color)

The map's palette table is full; I reused palettes already in the map (counted per 21 x 19 window around the milk bar: the worst window has 8 today, and adding FACTORY or FARM keeps it at 8).
- A, B: **FACTORY** (light grey, steel, slate, ink). Index use: 0 white (paint, rims, lights), 1 paving, 2 slate and shade row, 3 ink. Grey paving, white paint, as the supervisor chose.
- C: **FARM** (meadow, gold, brown, dark brown): the bikes' cells take the ground's own palette, because a bike over meadow needs index 0 to be the meadow green. Gold chrome and brown tanks. FARM is the farm biome's own ground palette, so no new slot.
- DMG: shading only; same tiles. Nothing is Color-only except the cell palettes.

## Unique DMG tiles (project counter; round 3 = 44)

| | whole milk bar | note |
|---|---|---|
| Round 3 | 44 | |
| A rear view | **40** | -4 |
| B side view row | **47** | +3 (three 21 px bikes, two designs, none repeat on the 8 px grid) |
| C props | **43** | -1 |

(The lint counts one more in each because it counts the all-blank cell: 41, 48, 44.)

## Judgement

- A is cheapest and the closest to "narrow upright shapes", but the bikes are 7 px wide and read as small dark figures; the white bay lines make the paving readable on DMG.
- B is the richest: the side view is the one view the map already uses for the cow, and the overlap gives depth. It costs +3 tiles and the row is busy (rings, bars and mirrors all ink).
- C is the lightest: no lot at all, props like the bottle and cow; the bikes read best here (no paving behind them). On DMG they are ink on white and read clearly.
- My pick: C if the owner wants the milk bar to look like the rest of the map (every other venue has loose props, not a lot); B if he wants the biker bar to read as busy.

## Self-audit (gb-pixel-art)

| check | result |
|---|---|
| Hand-placed | Bikes are typed run specs and pixel lists in `src/cow_lot.py` (`SIDE`, `WHEEL`, `REAR_*`, `SISSY`, `KICK`); the strip, bay lines and shade row are typed runs written by short loops. Nothing computed from a fill. |
| Clean-up pass by hand | Done. Log: top-down and sheared bikes dropped (they read as bugs, then as a diagonal smear); rear bikes got a 2 px front tyre (no orphan), a 2 px tank stripe (no orphan) and a narrow dark rear tyre instead of a ring; side bike overlap cut from 3 px to 1 (it fused the wheels into a blob). |
| 1x comparison with the quality bar | Against round 3's side-view bikes at 1x: B and C are comparable, the mirrors and bars on my bikes look like antennae at 1x (the weakest part); A is rougher. |
| Lint | `gb_art_lint` PASS, DMG and Color, A, B, C. Warnings left: L-doubles in the round wheels' corner steps (inherited from round 3's wheel shape) and the bottle's 3 (unchanged round 3); orphans are the tail lights and mirror tips (deliberate single pixels); Color palette order is the existing COW palette. |
| Squint test 1x, DMG and Color | A: grey strip with three dark figures. B: a dark busy row on grey. C: two dark bikes on the meadow beside the door. |
| Owner's liked pieces untouched | Yes: 0 changed pixels outside the lot rectangle. |

## Integration problem for the import round (not fixed here)

The piece is 96 x 72 at cell (39, 23), so it covers cell rows 23 to 31. In the generated world the trunk road runs on cell rows 30 and 31 for x 39 to 50, so the lot's cells (x 43 to 50, y 30 and 31) are road cells today (palette TOWN1), and A and B's grey strip would collide with the road there. The venue needs to move 2 rows up, or the road down, or the lot be cut to one cell row. C is the least affected (props only).

## Deviations from the skill

- "Show art in the real engine (make BUILD=out/b_real ... scratch builds)": not done; rendered with the repo's own world renderer on the farm ground, as in round 3.
- "Code may not decide pixels ... shape or ellipse fills": the paving strip and bay lines are filled by loops over typed rectangles and run lists; the bikes are typed.

## Unsure

- Whether 21 px side bikes in a 16 px strip leave enough room to read as "parked in front"; a taller strip costs a cell row.
- C's bikes in FARM colours (gold and brown) are not "grey/steel"; a grey-steel prop on meadow would need a new palette with a meadow index 0.
