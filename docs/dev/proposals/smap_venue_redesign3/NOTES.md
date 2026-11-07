# Story-map venue art, round 3 (proposals only)

Nothing here touches `assets/`; no goldens. Sheets (round 2 | round 3, DMG above and Color below, x3): `mountain_sheet.png` (one column: DMG rows then Color rows), `stadium_sheet.png`, `cow_sheet.png`, `zoo_sheet.png`, `range_vertical_sheet.png`, `range_horizontal_sheet.png`. Sources in `src/` (typed grids; `src/` also holds round 2's files, which round 3 imports as the baseline). Lint inputs: `out/r3/lint` (scratch, not committed).

## Unique DMG tiles against round 2 (piece area, ground tiles free, same counter as round 2)

| piece | round 2 | round 3 | note |
|---|---|---|---|
| Space mountain A, no runway | 86 | **86** | same as round 2 (base 16, mountain 70) |
| Space mountain A with angled runway (variant) | - | **90** | runway costs **+4** (it is not free, so it is a separate variant) |
| Stadium A | 41 | **37** | quality pass saved 4 |
| Milk bar (A + C's bottle + lot) | 40 (A) | **44** | the lot costs +4 (pavement, kerb, stall lines); C's bottle replaces A's board at no change |
| Zoo A, thin neck | 37 | **38** | the neck now has two widths (4 and 6 wide): +1 |
| Zoo B, thin neck | 44 | **45** | same, +1 |
| Vertical range pieces (new) | kit 26 (6 pieces, horizontal only) | **13** for a straight column of ANY length (2 to 5 checked); 15 for a 5-peak zigzag column; 11 for the single peak; 11 for the 4-peak staggered row | desert and snowy are the SAME DMG tiles (35 of 35 cells identical) |

Palettes: unchanged from round 2 (mountain BASE + SALOON; stadium STADIUM + PARK; milk bar COW only; zoo ZOO + ZOOGATE unmerged; range SALOON or IGLOO). DMG first: every value decision below was made on the grey rows, Color only recolours.

## 1. Mountain A (the mountain itself is round 2's A, pixel for pixel; only the base changed)

- **Tower top.** No cross. A thin mast at the cab's left end with a small lamp box (ink ring, light centre), and a radar dish at the right (a face-on disc, lit upper left, a feed pin on top, on a short post). The tower body is round 2's, unchanged.
- **Hangar.** Round 2's igloo-like dome (28 x 15) is replaced by a low, wide shed, 32 x 14: a shallow arched roof (outline runs 3, 2, 1) with vertical ribs, an eave line and its shadow row, straight walls, two big sliding door leaves (navy, a lit edge and a rib on each, centre seam), a light kick band and a hazard-stripe band at the foot of the doors. It stands on the same foot row (y 63). 16 tiles for the base, same as round 2.
- **Runway.** Costs +4 tiles at the best slope I found (1 row per 2 columns; the other slopes I tried cost +6 to +10), so it is the separate variant `mountain_a3r`: a 5-row strip rising 26 degrees from the lower left toward the tower base, passing behind the hangar's right end, asphalt navy with a lit edge, a shade edge and a dashed centre line. To fit it the hangar and tower stand 8 px higher (foot y 55) in this variant, which changes no tile. Honest reading: it reads as an angled road leading to the tower; the lower end is cut flat by the bottom of the piece. If the owner wants it, the way to make it free is to drop about 4 tiles elsewhere (the strata dashes).

## 2. Stadium A, quality pass (kept A: stands, masts, wedge, diamond, no scoreboard)

Checklist and what changed:
- **Clean lines / the diamond's proportions.** Round 2's foul lines ran at 2 rows per 3 columns while the base paths ran at 1 per 2, so each line kinked where it met first or third base. Now ONE straight line per side at 1 per 2, lying on the home-to-first and home-to-third paths (their lower row is the line), so lines and diamond share one slope; the line is 2 px thick like the paths all the way out.
- **Home.** The pointed wedge tip is replaced by a rounded dirt apron around the plate (typed 9 rows, 20 wide at most): a ballpark's home area instead of a pennant tip.
- **Light towers.** Pole redrawn with a lit side (navy) and an ink side instead of two ink columns; heads unchanged.
- **DMG value separation.** Unchanged and checked: grass 1 / dirt 2 / chalk 0 / ink 3; the apron (2) against the concrete (0) is the strongest edge on the piece, on purpose: it is the end of the field.
- **Field and stands at 1x.** Untouched (stands stepped in whole cells, spectators as dots).
- 41 -> 37 tiles.

## 3. Milk bar (A's building, C's bottle, a parking lot)

A's diner, roof, MILK BAR band, windows, door, cow and bikes are round 2 A, unchanged. The cow-board pylon is replaced by round 2 C's milk bottle on the same pole (pink cap, chrome glass, spotted pink label), centred on the pole. The lot: a pavement slab (chrome 1) x 34 to 93, y 56 to 71, ink outline, a 1 px shade row under the diner (on Color that row is the neon pink: a glow), painted stall lines in pink every 24 px (3 cells, so the stalls are the same tiles), the two bikes parked between the lines. 44 tiles.

## 4. Zoo, A and B with a thinner giraffe neck

The owner's "c" is not one of the options shown, so both are delivered. The neck was 8 px wide (6 inside); now 4 px wide (2 inside) under the head, widening to 6 (4 inside) for the last cell row above the fence, with the spots re-typed (patches 2 px wide and single dots). Head, gate, fence, bamboo and bush unchanged. If 4 px is too thin it is one typed row table (`NECK4` in `src/zoo_parts.py`) to widen.

## 5. Range pieces that work vertically (new `mtn_vert.py`)

One hand-typed peak, 32 x 24 (24 rows of 32 characters): two summits (main apex and a lower one on its shoulder, a saddle between), each with its own crease, lit left and shaded right, ragged cap, strata dashes and dark marks, a rounded foot. It is stacked by PASTING the same typed peak every 16 px (copying my own work). Because the foot is rounded and each peak is lower than the one behind, the back peak's feet show as lobes at the sides and the outline waves in at every saddle: "overlapping peaks stepping back"; the top peak has nothing behind it and the last has its foot closed in ink (end caps). Round 2's pieces cannot do this: stacked, whole 8 px cells replace each other and leave white holes (left of `range_vertical_sheet.png`).
- Vertical: a straight column (peaks directly below each other) and a zigzag column (each peak 8 px right or left of the one above: a chain; costs 2 more tiles). Any length: the tiles repeat (13 for a straight column, 15 for the zigzag).
- Horizontal: the same peak alone, staggered up or down one cell row (`range_horizontal_sheet.png`): 11 tiles for four peaks.
- Desert and snowy share every DMG tile; only the palette differs (cap: sun-bleached crest or snow).
- My first draft (a single cone, 28 wide) read as a tent or haystack when stacked; the twin summit and the saddle fixed that.

## Self-audit (gb-pixel-art)

| check | result |
|---|---|
| Hand-placed | The hangar, the dish, the lamp, the giraffe neck rows, the vertical peak (24 typed rows), the home apron and foul-line formulas, the lot and its lines are typed in `src/*.py`. Helpers: `rect/hl/vl/box` (one typed run or block), `C.paste` (pastes typed rows), `mtn_vert.stack/column/row` (paste my typed peak at typed places), `C.render/tile_count` (preview, count). The mountain's skyline fill is round 2's `mtn_kit` helper, untouched (see Deviations). |
| Clean-up pass by hand | Done. Log: mountain peak row 8 corner (17,8) made shaded to remove an L-double; the dish ring's feed dot (an L-double at (45,30)) moved to a pin on top; hangar roof crest highlight removed (made two roof cells differ: -1 tile); lamp moved into the mast's cell row (-1 tile); lot sides first flared (read like a podium), then back to a rectangle; vertical peak: first draft cone rejected, shaded-face stripe narrowed in rows 15 to 22 (it read as a road). |
| 1x comparison with the quality bar | Compared at 1x with the igloo option 1 and zoo A of round 1 (same sheet style): stadium, zoo and the vertical column hold up; the dish and the runway are the roughest. |
| Lint | `gb_art_lint` PASS on all 10 files, DMG and Color. Remaining warnings: orphan pixels (tufts, bases, spectators, strata ends: intended), L-doubles only in round 1 / round 2 art kept as the owner picked it (cow: bikes, wheels, bottle shoulder, 19; zoo: stone, bush, 3) and 4 isolated 2x2 squares in the zoo (round 1 art); Color palette order warnings are the existing COW and PARK palettes (idx 0 is the biome ground, not the lightest). |
| DMG value separation | Hangar: roof 1 with 2 ribs against ink, doors 2 against walls 1, hazard band 1/3; dish 1 inside ink; lot 1 against meadow 0 with ink outline, stall lines 2; peak: lit 1 / shaded 2 / ink 3 / ground 0, caps 0. |
| Periodic patterns | Roof ribs period 4, door leaves identical, stall lines period 24, neck rows period 8, peak stacking period 16: all tile-aligned. |
| Squint test 1x, DMG and Color | Hangar reads as a shed with big doors at 1x, not an igloo. Dish reads as a disc on a post (weak). Lot reads as a slab; stalls read. Columns read as a chain of peaks. |
| Tiled preview | The repeating unit here is the 16 px stack, so I checked the stacked columns (2 to 5 peaks) instead of `tiled_preview.py` on a tile. |
| Owner's liked pieces untouched | Mountain A's mountain, stadium A's stands and diamond, milk bar A's diner, zoo gate: unchanged. |

## Deviations from the skill

- Skill: "Code may not decide pixels ... shape or ellipse fills". The mountain A body is round 2's `mtn_kit.peak` fill between typed skyline runs (flagged in round 2, unchanged). The home apron and foul lines are typed row/column formulas (first column and width per row; the line's row as a typed function of x): I typed the numbers, a loop writes them. The vertical peak itself is fully typed row by row.
- Skill: "Show art in the real engine (make BUILD=out/b_real ... scratch builds)": not done; pieces are rendered with the repo's own world renderer on the biome ground (same palette and tile code), as in round 2.
- Skill: "For batches ... deliver ONE figure first and stop for approval": the brief asked for five items together.
- Skill references: environments.md, linework.md, light-and-form.md read before drawing; palettes.md, hardware.md, sprites.md and the figures not re-read (round 2 read them; no sprites).

## Self-judgement (strict)

- Strong: stadium A quality pass (one slope, rounded home, clean), zoo A and B (the thin neck is what he asked for; B's neck against the bamboo needs the spots to tell them apart, they do), the vertical range in a zigzag column.
- Acceptable: hangar (reads as a hangar, but the door detail is busy at 1x and the roof arc is a little boxy), milk bar (the slab and stalls read; paving and chrome are the same colour so the lot is separated only by ink and the shade row), the vertical straight column (a stack of identical peaks is a stamp: use the zigzag or vary the peak).
- Weak: the radar dish (a flat disc, not obviously a dish), the angled runway (it costs +4 tiles and is a thin diagonal stripe, cut by the piece's bottom edge), the peaks are wide (30 px) and bulky; only one peak shape exists, so long columns repeat.

## Questions for the layout and the programmer, with working assumptions

1. Vertical pieces are 4 cells wide (5 for the zigzag) and 3 cells tall plus 2 per extra peak; assumed the layout can place a pre-composed column as one piece (like the mountain), not as separate cell-level pieces: separate placement would replace overlapping cells, as in the left of `range_vertical_sheet.png`.
2. Desert and snowy share DMG tiles and differ by palette only: assumed the generator picks the palette per cell (as in round 2).
3. The runway variant raises the hangar and tower 8 px (foot y 55): assumed the base can stand 8 px behind the mountain's foot line.
4. The milk bar lot adds 4 tiles; the bottle replaces the board and keeps the same footprint (96 x 72).
