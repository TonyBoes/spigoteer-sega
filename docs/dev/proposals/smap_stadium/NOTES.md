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

## Wavy flag (owner: "Flag is too flat. Needs to wave or something.")
Hand-typed 10 x 5 flag (`FLAG_FRAMES` in `src/park_s2.py`), pole at x 47: S-wave ink edges, red and white bands, a navy fold shade on the crest, the fly end narrower (3 rows, then a 2-row tip). Frame 0 is the static flag. Files: `stadium_wavy_sheet.png` (final 2 | wavy static), `stadium_wavy_frames_x6.png`, `stadium_flag_wave_DMG.gif`, `stadium_flag_wave_Color.gif` (3 frames, 125 ms = 8 fps, gentle; only about 20 flag pixels change, no flashing). The wave has a spatial period of 6 columns and travels 2 columns a frame, so the 3 frames loop exactly.
- Static: still 60 tiles (the flag cells are the same three cells as before).
- Animation cost (not implemented): the flag lives in cells (5,0) pole only, (6,0) and (7,0). The pole cell is identical in all frames; the other two differ per frame. A BG tile animation therefore rewrites 2 VRAM tile slots (3 frames x 2 = 6 tile images in ROM, 1 pair of which is the static flag; 4 extra over the static piece). VRAM: no extra slot beyond the 2 the static flag already uses. DMG and Color alike, no palette change.
- Doubt: the wavy flag is smaller on screen than the flat one (the fly end narrows, the flag has less area), and the fold shade is subtle at 1x. If it should be bolder, widen the hoist to 5 rows.

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

## On the A5 map: blend into the map (owner: "The baseball stadium needs some care to blend into the map.")
Sheets: `stadium_map_sheet.png` (before | after, the stadium and its neighbours x3, DMG above, Color below), `stadium_map_whole_x1.png` (whole map Color x1, before | after). Sources: `src/mapctx.py` (A5, SMAP_LOG=v1, stadium pasted at cell (1, 1), every cell, as the animation import does), `src/after.py`, `src/edits.py`, `src/mkimgs.py`, `src/map_numbers.py` (needs the scratch `smap_layout_a5/src` from its `mk_src.py` + `mk_a5.py`, not committed). The stadium itself (bowl, stands, pennants, flag, field) is unchanged pixel for pixel.
What changed, nothing else:
1. Ground. The piece's own all-blank cells are not pasted (the map's own ground tile, with its tufts, shows there). STADIUM and PARK now have index 0 = the map's grass (b0d080) instead of pale grey-blue d4d8e4, so the margin pixels of the partly filled cells are the map's ground. DMG is unchanged (index 0 stays shade 0). On Color the white of the coping, the white pennants, the heads, the flag stripe, the plate and the bases is now that pale lime (index 0 is both the ground and the white: the palette has 4 colours); ink, red and navy carry the shapes, the bowl still reads.
2. Field grass. PARK's index 1 is now 6aa048, the map grass (was 68b048): slightly duller field. It is what lets the 5 right-hand field cells use the GRASS palette (below).
3. Connection. A 16 px walkway (12 px inside) from the apron to the road, in the road's own town1 palette: lilac borders, peach, two cream dots, 2 px ink gate pillars with a lit corner; the road's top border opens where it joins (typed in `src/edits.py`). 4 new DMG tiles (2 walkway cells, 2 reshaped road cells).
4. Palettes per window: before 9 in 2 windows ((11,3), (12,3): STADIUM and PARK both there with the bistro, the town and the igloo range's row); after 8 everywhere (probe on the cell map before the generator's snap). To get there the 5 right-hand field cells, map cells (11,5) (11,6) (12,6) (11,7) (12,7), take the existing GRASS palette: the 2 px foul line in those cells is dark green (28603c) instead of tan, for its last 16 px (it reads as a trimmed edge; the left side keeps its tan line: asymmetric).
No new palette-table entry was added by me. Doubt, and it is the supervisor's call: the approved piece needs TWO palettes, STADIUM (the table's slot 9) and PARK, and PARK is not in the A5 18-entry table (the animation notes already said the table needs a 19th entry or a merge). I found no merge: the stands need red and navy, the field green and tan, in separate palettes. So the table still lacks PARK; palettes per window are at 8 only because PARK counts as a palette. The STADIUM slot's colours change to [b0d080, e04030, 283c78, 101428] (only this piece uses the slot).
DMG unique tiles: whole map 606 before, 610 after (+4); worst 21 x 19 window anywhere 133 (unchanged, at (28,19), not the stadium); worst window that shows the stadium 113 before, 117 after (limit 176).
Other changes not made: the wedge's straight diagonal edge and the stands' blocky outer ends are the approved art and are left; they read as a mown field on the lawn now.

### Map blend, second pass (supervisor: no dark foul-line stripe, keep light accents if possible, investigate the PARK slot)
Sheets: `stadium_map_sheet2.png` (2 columns, approved | after, DMG row, Color row, big labels), `stadium_map_whole_x1_2.png`. Superseded: the sheets above (`stadium_map_sheet.png`, `stadium_map_whole_x1.png`).
1. Foul line, symmetric. The five right-hand cells still take the GRASS palette (8 palettes per window), which has no tan, so both sides now end the same way: the outer 16 px of each foul line (x 0 to 15 and 80 to 95) and the two outer tufts (10, 35) and (82, 35) are drawn as field grass (`src/park_map.py`, 78 pixels, typed rule: index 2 to 1 below the stands). The foul line stops 16 px short of the stands on both sides; no dark stripe. This changes DMG too (those line pixels were shade 2, now shade 1). I found no cell layout that keeps both lines tan at 8 palettes: PARK and STADIUM would both be in windows x0 11 and 12 with the bistro, town, igloo row and saloon row.
2. Light accents on Color. Could not keep true white: index 0 of STADIUM and PARK must be the map's grass (the margin pixels share the cell), and a 4-colour palette cannot also hold white; every white pixel is the pale lime b0d080. A cell with white and no ground (the centre pennant cells, the plate cell if its corners were filled) would need a second STADIUM or PARK palette with a pale index 0, which is another table entry. What stays visible: the pennants (lime on navy), the flag stripe (lime between red bands inside ink), the plate and bases (lime on tan, ink corners), the coping (lime between ink lines), the heads (lime dots on navy). DMG keeps real white (shade 0).
3. The PARK slot (investigation, no engine edits).
 (a) A 19th table entry fits in story_scratch without a new WRAM global. Map-mode layout, `src/smap_priv.h:24-29`: A_PCNT 176 (18 x u16 = 36 B, ends 212), A_PSLOT 212 (18 B, ends 230), A_PUSE 230 (8 B, ends 238), 2 free bytes 238..239, A_ATTR_UI 240 (20 B), A_IDA 260 (22 B), A_PSTG 282 (9 B, ends 291), 9 free bytes 291..299, A_XSTG 300. A 19th palette needs +3 bytes (PCNT +2, PSLOT +1): move A_PSLOT to 214, A_PUSE 233, A_ATTR_UI 241, A_IDA 261, A_PSTG 283 (ends 292, 8 B to spare before A_XSTG 300). The fit assert `smap_scratch_fits` (`src/smap_priv.h:46-47`) stays true; no other file names those offsets (grep: `src/smap.c:384,389,397,506,786,787`, `src/smap_eng.c:531-548,569,583,617,643,677,687` use the macros). `SMAPW_NPAL` comes from the generator (`tools/gen_smap_world.py:730`, `len(PAL_NAMES)`), and the cell word holds the palette in bits 10 to 15 (`gen_smap_world.py:119`), room for 63. Cost: 8 bytes of ROM for the colours plus 3 B of scratch re-laid. Not tried in a build.
 (b) Sharing: PARK [b0d080, 6aa048, c09050, 101428] against the table: GRASS [b0d080, 6aa048, 28603c, 142418] shares three colours (index 0, 1 and 3 within a shade); only index 2 differs (dirt tan against dark green). No other entry is close. No slot is free to repurpose: all 18 are used (A5 spent `base` on town1@g); `water`, `bistro@g`, `tea@g` (the old cloud slots, `gen_smap_world.py:57-61`) belong to the river, bistro and tea garden; `tea@g` is the only one that never shares a window with the stadium, but the tea garden needs it.
Numbers after this pass (DMG): whole map 612 tiles (606 approved), worst 21 x 19 window 133 (unchanged, at (28,19)), worst window showing the stadium 118 (113 approved); palettes per window 8 max, 0 over.
