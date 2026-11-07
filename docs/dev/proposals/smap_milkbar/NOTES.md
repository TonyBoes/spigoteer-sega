# Milk bar: lot and bikes, round 4 (proposal only)

Owner: "Parking lot and motorcycles don't need to be the same color as the building on the milk bar. Let's also have them parked vertically in the spaces, not horizontally across. Or do them at a slant view."

Nothing here touches `assets/`; no goldens; `make` still builds. Sheets: `milkbar_sheet.png` (round 3 | upright | slant; DMG row, Color row, lot close-ups x6), `milkbar_options_paving.png`, `milkbar_options_palette.png`. Sources in `src/` (`cow_lot.py` is the art; `sheet.py`, `options.py`, `export.py` render; `common.py`, `kit.py`, `cow_c.py`, `cow_a3.py` are round 3's files, with `ROOT` pointed at this worktree).

## What changed, what did not

- Building, bottle sign, cow: round 3's `cow_a3`, pixel for pixel. `sheet.py` compares every pixel outside the lot rectangle with round 3: 0 changed pixels in both layouts.
- Lot: whole cells x 32 to 95, y 56 to 71 (8 x 2 cells), its own cell palette. Round 3's lot was x 34 to 93 with an ink outline and a front kerb; this one has no outline, no kerb, and runs off the bottom of the piece (open front). Paving is shade 0 (lighter than round 3's 1). A 1 px shade row (2) under the diner stays.
- Bikes: new top-down art, nose-in (front wheel toward the diner), seen from above and behind: tyre, mirrors, bars with chrome, tank with a chrome stripe, seat, chrome pipes, tail. Two designs: a plain one and a chopper (sissy bar). Bays: 3 bikes (bay 1, 3, 4 upright; 1, 3, 5 slanted), the bays in front of the door and the cow stay empty.
- (a) UPRIGHT: eight vertical bays, one cell (8 px) apart, a line on the left of each bay, one on the right edge. (b) SLANT: bays angled one column per two rows (runs 2,2,2,2,2,2,2,1), leaning to the upper right, nose-in; each bike is typed row by row with its own offset.

## Palette (Color)

The map's palette table is full, so the lot reuses one. I counted the palettes in every 21 x 19 window that holds the whole lot (`tools/smap_world/world2.py`, `palsnap.window_counts`): the worst window already has 8. Adding a palette to those windows stays at 8 for: COW, FACTORY, FARM, GRASS, TEA, TOWN1, TOWN5; every other palette makes 9. **Pick: FACTORY** (light grey, steel blue-grey, slate, ink: tarmac, grey paint lines, slate-blue bikes): grey is the one colour nothing near the milk bar uses, so the lot separates from the pink diner, the green meadow and the cream road. TOWN5 (cream, peach, gold, ink: gold tanks, livelier bikes, but a sandy lot) and TOWN1 (the road's own colours, muted) are on `milkbar_options_palette.png`; both also cost no slot. No new slot is needed. FACTORY is not in the lot's windows everywhere today, but the count above includes it. DMG: shading only; the same shades.

Index use in the lot: 0 paving, 1 lines and chrome, 2 shade row and tank, 3 ink.

## Unique DMG tiles (project counter: piece area, blank cells and ground tiles free)

| | whole milk bar | lot cells only (16 cells) |
|---|---|---|
| Round 3 | 44 | 10 |
| UPRIGHT, 3 bikes, 2 designs | **41** | 7 |
| SLANT, 3 bikes, 2 designs | **41** | 7 |
| either, one bike design only | 40 | 6 |
| no bikes (bays only) | upright 38, slant 36 | 4 and 2 |

Both layouts are 3 tiles cheaper than round 3. An upright bike is 2 tiles (one cell column); a slanted bike is 4 (it spills into the next cell). The lint counts 42 (it also counts the all-blank cell).

## Color only?

Nothing. All of it works on DMG with shading only; the cell palette is the only Color-only part (on DMG the lot is the same tiles). The cell palette needs the lot's cells to carry their own attribute: the lot is whole cells (x 32 to 95), so no cell mixes meadow and lot.

## DMG reading (honest)

Paving 0 is the same shade as the meadow, so on DMG the lot has no body of its own: it reads as bays (lines and bikes) under the diner, and the upright lines look a little like posts hanging from the building. The slant lines do not (they lean). If that is too faint, `milkbar_options_paving.png` shows two fixes: grey paving (shade 1, white lines; reads clearly as a lot, and is the same shade round 3 had but with no outline, so it is not a box), and a 25 percent grain (busy; I rejected it).

## Integration problem (supervisor)

The piece is 96 x 72 at cell (39, 23), so it covers cell rows 23 to 31. In the generated world the trunk road runs on cell rows 30 and 31 for x 39 to 50, so the lot's cells (x 43 to 50, y 30 and 31) are road cells today (their palette is TOWN1). The lot needs the venue 2 rows higher or the road lower; not touched here.

## Self-audit (gb-pixel-art)

| check | result |
|---|---|
| Hand-placed | The bays (`UP_*`, `SL_*`, the line runs) are typed grids in `src/cow_lot.py`; the line positions of the slant are a typed run list; `clear_lot` and the line loops only write my typed rows. The paving-1 preview in the options sheet exchanges shades 0 and 1 inside the lot (a mechanical preview of my own grid; the bikes' chrome would be redone by hand if it were picked). |
| Clean-up pass by hand | Done. Log: bike tail slate pixel (an orphan) made ink in both designs and both layouts; grain paving tried and removed (busy, hid the lines); bikes: first draft had no mirrors and no chrome pipes, they read as dark beetles, mirrors and pipes added; right edge line added to the upright lot; lot sides first an outline, removed (open). |
| 1x comparison with the quality bar | Compared with round 3 (the owner-liked side-view bikes) in the same sheet at x3 and 1x; the igloo was not re-opened: the new bikes are rougher than round 3's side-view bikes (they are 7 x 13 px); the slanted ones read as motorcycles, the upright ones as bugs at 1x. |
| Lint | `gb_art_lint` PASS, DMG and Color, both layouts. Warnings left: 3 L-doubles at (12,16), (19,17), (50,34) (the bottle, round 3, unchanged); 0 orphans in the lot (my own check); Color palette order warning is the existing COW palette. |
| Colours per tile, palettes | 2 palettes on the piece (COW, FACTORY); the lot cells use FACTORY only; no new slot. |
| Squint test 1x, DMG and Color | Color: the lot is a grey patch with dark bikes, clearly separate from the pink building. DMG: bikes read first, the paving is faint (see above). |
| Banding / squares / strays | Slant line runs are regular (2 per column step); no 2x2 squares in the lot; bike mirrors are connected to the grips. |
| Owner's liked pieces untouched | Building, bottle, cow: 0 changed pixels. The bikes are redrawn because the layout changed; the owner asked for this. |

## Deviations from the skill

- Skill: "Show art in the real engine (make BUILD=out/b_real ... scratch builds)": not done; rendered with the repo's own world renderer on the farm ground, as in round 3.
- Skill: "Code may not decide pixels ... shape or ellipse fills": the bay lines are written by loops over my typed run list and column list (one typed run each); the bikes are typed.

## Unsure

- Whether 7 x 13 px top-down bikes are recognisable enough; the owner may prefer a 3/4 or front view at a larger size, which needs more than 16 px of lot height.
- DMG presence of the lot (above).
- The bay pitch of 8 px is chosen for tile reuse; a wider pitch would cost tiles.
