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
