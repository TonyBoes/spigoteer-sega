# Stadium, round 4: grandstands and pennants (proposal only)

Owner: "Round 3 on the stadium is better, but lets work some more on the stands. Give me some pennants too."
Sheet: `stadium_r4_sheet.png` (round 3 | option 1 | option 2; DMG row, Color row; x3). Sources: `src/` (`python3 sheet.py` rebuilds the sheet and counts; field in `field.py`, stands in `park_s1.py`, `park_s2.py`). Nothing in `assets/`; no goldens.

Unchanged from round 3: the field, foul lines, base paths, bases, mound, tufts, plate, the two light masts, the 96 x 80 footprint, no scoreboard, the STADIUM and PARK palettes.

## Home dirt (both options, DMG fix)
Round 3's apron was solid shade 2 (dark grey). Now a solid shade-2 rim (keeps it apart from the grass) and a 1/2 checker of shades 1 and 2 inside, y 64 to 71 (round 3: y 63 to 71, one row shorter now). DMG reads one step lighter than the paths. **Color only:** that cell row (x 32 to 64, y 64 to 72) takes a new palette PARKHOME = PARK with a pale sand in slot 1 (e0c488) so the checker is sand and dirt, not green and dirt. Costs 1 background palette slot on Color; DMG tile count unchanged (47 and 59 with round 3's apron too).

## Option 1: covered grandstand
Roofed back stand: ink roof edge, a lit top plane, a red and white awning, ink shadow line, roof posts (lit column and ink column) every 16 px, tiers with lit rails (shade 1) between navy risers, a two-row crowd (white and red heads over red and white shirts, two phases), red outfield wall. The roof steps down to each wing along a 45 degree chamfer (8 columns, 8 rows): the angle of the stands round the infield. Pennants: five poles on the roof (ink pole, ink-topped triangular flag, red or navy) at x 8, 32, 48, 64, 80, all on the 8 px grid so they share tiles. Static.

## Option 2: curved bowl with bunting
Open bowl, no roof. The back wall's coping follows a smooth arch (run lengths 12, 6, 5, 4, 3, 3, 2, 2, 1, 1, 1 each side), a navy back wall under it with a string of hanging pennants, white and red alternating, that follows the curve; the tiers' rails curve with the arch over the middle, then run level on the wings (first try curved all the way: the wings turned into staircase banding, so I flattened them); red outfield wall. Pennants: a string of triangles (5 wide, 3 tall), static.

## Unique DMG tiles (stadium, same counter as round 3)
| | tiles | pennants alone |
|---|---|---|
| round 3 | 37 | - |
| option 1 | 47 (+10) | +2 (red and navy flag tile; 45 without) |
| option 2 | 59 (+22) | +1 (58 without; the plain wall it replaces is nearly the same tiles) |

Option 1's cost is the chamfer and the wing cells; option 2's is the curve (every cell along the arch is its own tile).

## DMG and Color
Both fit the DMG (shades: ink 3, navy seats 2, rails and red 1, white 0). Pennants: DMG shows navy as dark grey, red as light grey with an ink edge (option 1) and white and light grey flags on dark grey (option 2). Color-only: only the PARKHOME palette above.

## My pick
Option 1. It reads as a ballpark grandstand at 1x on DMG (roof, awning, posts, tiers, crowd) and costs 12 tiles less, its flags are the clearest pennants, and the 45 degree wings give the angle. Option 2 has the nicer silhouette (a real curve) but the crowd and the roofline get busy on the wings and it costs +22 tiles.

## Final (owner picked option 2, added a flag on top)
Sheets: `stadium_final_sheet.png` (option 2 | final, DMG above, Color below, x3), `stadium_final_top_x6.png` (x6 close-up). Sources: `src/park_s2.py` (final), `src/park_s2_old.py` (as proposed), `src/sheet2.py`.
- Big flag: 9 x 4 ink-outlined red flag with a white stripe on a pole at x 47, on top of the arch centre (static). The pole shows only 2 px below the flag: the arch top is at y 6 and the canvas ends at y 0.
- Home dirt: PARKHOME and the checker are gone. Solid shade 1 (PARK slot 1) inside a 1 px dirt rim: one step lighter than round 3 on DMG, no new Color slot. On Color the inside is grass green, so the apron reads as a dirt-rimmed ring round the plate (doubt). The sections above that mention PARKHOME describe the first proposal.
- Clean-up: no pennants on the steepest wing columns (x 8 to 14, 81 to 87): plain navy wall there; the rest unchanged.
- Tiles: 60 against option 2's 59 (flag +2, plain wing wall and solid apron -1).

## Final 2 (supervisor fix)
Home dirt back to round 3's solid dirt (slot 2, round-3 shape, white plate), PARK only, no new palette; flag and plain wing ends as in Final. Sheets `stadium_final2_sheet.png`, `stadium_final2_top_x6.png`. Flag stays 9 x 4: there is no top margin (arch top y 6, canvas top y 0); a 5-row flag left no visible pole and read as a box, so I reverted. 60 tiles (option 2: 59).

## Self-audit (gb-pixel-art)
| check | result |
|---|---|
| Hand-placed | SEAT8 (8 x 8 crowd tile, typed row by row), ROOF, BACK and FLAGS rows, the arch run lengths, the roof and wall rows per region, the apron rows: typed in `src/`. Code only copies my typed rows to their places (period 8 repeats, own work) and renders. |
| Clean-up pass | Done. Log: option 2 first try curved the tiers all the way, wings became diagonal fragments: tiers now level below row 9; bunting made 5 x 3 (the 3 x 2 first try was unreadable at 1x); gray cornice row dropped (one more seat row); option 1 wing poles moved to x 8 and 80 (same tiles as the centre poles, -2 tiles); apron rows re-typed so the checker parity is one pattern. |
| 1x comparison | Against round 3 on the same sheet and the round-3 sheet's igloo bar: both options hold up at 1x; flags of option 2 are the roughest. |
| Lint | `gb_art_lint` PASS DMG, both. Warnings: orphan pixels (crowd heads, tufts: intended), one 2x2 in option 1 at (93,30) (crowd cell at the right end, left in), two L-doubles in option 2 at (8,17) and (87,17) (the end caps' corners, deliberate). |
| DMG value separation | Awning 1/0 stripes against ink; seats 2 against rails 1; flags 2 or ink-topped 1 on white ground; apron rim 2 against grass 1; wall red (1) against grass (1) is separated by the ink line, as in round 3. |
| Squint test | Roof or coping reads first, then crowd band, then the red wall. |

## Deviations from the skill
- "Show art in the real engine (make BUILD=out/b_real ... scratch builds)": not done; rendered with the repo's world renderer on the biome ground, as in round 3. `make` still builds (no source changed).
- "Code may not decide pixels ... shape fills": the stands are typed row tiles pasted by column rules (roof row per column, wall row per column); the flat tiers are one typed 8 x 8 tile repeated. I typed every row; a loop places them.
- "Deliver ONE figure first": the brief asked for 2 options.

## Doubts
- The chamfer of option 1 makes the wing taller next to the centre than at its outer end; the real stands would not, but it reads as an angle.
- PARKHOME needs a spare BG palette on Color; if none, the alternative is the checker in slot 1 = grass (green flecks in the apron).
- The 1x pennants of option 2 are small; poles in option 1 are clearer.
