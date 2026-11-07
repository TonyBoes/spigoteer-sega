# Map town fountain as a miniature of the story square's (proposal, nothing imported to assets/)

Owner 11-06: "With the fountain, can you make it look like a miniature version of the one in the story scenes?"
Base: layout A5 (branch `worktree-agent-a9eca06ceee777aa2`, merged here), DMG light water, its 172 town touches kept except the ones about the old fountain.

Sheets: `sheet_fountain.png` (story crop | now | option 1 | option 2; DMG row, Color row; then the whole town, DMG and Color; x4) and `sheet_engine.png` (real engine, scratch ROMs, town stop, DMG over Color, x3).

## The story fountain (assets/story_map/world/finale_a.txt)
Gold tap statue (crown, T handle, bent spout with a drip, lever knob on the left) on stepped plinths, a pale funnel bowl, a plain column, a wide low basin with a lip and four ink-divided panels, and two thin streams from the bowl's rim ends into side pools.

## What the two options draw (all typed in `src/v_town_fx.py`, no generated pixel)
Both: tap statue with a T handle, neck, body with a lever knob, a spout arm that turns down at its end (water falls from it), collar and two plinth steps, a 14-wide funnel bowl with an overhanging rim, a 6-wide column, a pedestal foot standing in the water, a pale panelled basin (ink back rim, 3 rows of water, ink lip and two cream rows, panels with dividers every 8 px, lilac shade row, ink base) and a 2-wide jet from the spout into the basin. Light from the top left.
- Option 1 (tight): no cap on the handle, basin x 40 to 63 (24 wide, 3 panels).
- Option 2 (larger): domed cap above the handle, basin x 40 to 71 (32 wide, 4 panels like the story's).
Neither touches the hall; the basin starts on the hall's right edge line (x 40) and, as the old trough did, runs over the tavern's lower wall. Statue top: y 22 (option 1), y 20 (option 2); the old tap's top was y 24. The A5 hand-typed touches at the old trough (the x 41 joint, the foot pixels, the spigot lights) are gone because the pixels they patched are redrawn; the flag and tower touches are kept.

## Numbers (generator line of the scratch engine build, `tools/gen_smap_world.py`)
| | now (A5) | option 1 | option 2 |
|---|---|---|---|
| DMG unique tiles | 546 | 548 | 547 |
| DMG worst 21x19 window (limit 176) | 133 | 135 | 134 |
| DMG 22x20 window | 138 | 139 | 138 |
| Color tiles / slots | 618 / 352 | 619 / 352 | 619 / 352 |
| palettes per window (cap 8), snapped cells | 8, 0 | 8, 0 | 8, 0 |
| town block unique cells (12 x 9) | 74 | 76 | 75 |
| ROM0 free by the linker map | 477 | 477 | 477 |
Lint (`gb_art_lint.py`, DMG, the fountain's 32 x 48 crop): PASS for both; warnings: 3 L-doubles (two are the hall's and the tavern's existing outlines, one is the bowl rim's deliberate overhang corner at (43,37)) and 5 orphans (the cream glints in the jet and the water, deliberate). Color has no lint run (one palette per cell, not a strip); its checks are the generator's: 8 palettes per window, no snap.
DMG or Color: all of it is on both. Nothing is Color only. WRAM and ROM0 unchanged (picture data only, banked).

## Cell rules that shaped the drawing (this is why it is not a copy of the story art)
1. Cells with air round them take `town1@g` (grass as index 0): terracotta, lilac, ink only, so the statue, bowl and column are terracotta and lilac, not gold. Gold would need `town5@g` (a 19th palette) or a cream wall behind the statue. The lodge palette has a honey gold with grass index 0 and would cost no table slot, but it makes 23 windows pass 8 palettes (tried, then dropped).
2. Water (`town4`, index 1 blue) cannot share a cell with terracotta or air: the water is the basin (y 48 to 63, no air in those cells) and the jet over the tavern wall (x 56 to 63), so the spout nozzle ends at y 31 and the stack stays in x 42 to 55 below that. The story's two side streams from the bowl rim would fall through air cells, so they are not possible; one jet instead.
3. The column's lower part, standing in the water, is cream and lilac stone (a foot block) because terracotta cannot be in a water cell.

## Clean-up log (by hand, after the first render)
Lamp-post proportions: bowl widened to 14 with an overhanging rim and a stepped funnel; crown (read as a rook) replaced by a domed cap in option 2; double ink row between plinth and rim removed (the plinth's last row is the rim); lever knob rounded; right half of body, bar, plinth and bowl shaded lilac so the DMG statue is darker than the bowl; basin made tall (16 rows, as the old trough) after the first 8-row slab read as a plate; water glints cut to one pair per 8 px; jet drift retyped to a 1:1, 1:2, 1:3 run rhythm and its glints spread.

## Self-audit (gb-pixel-art)
| Check | Result | Evidence |
|---|---|---|
| Hand-placed pixels only | PASS | typed grids in `src/v_town_fx.py`; `v_town_base.py` is `tools/smap_world/v_town.py` with lines 163 to 179 cut (no pixel added); scripts only transcribe, render, count |
| Clean-up pass by hand | PASS | log above |
| 1x comparison with the bar | PASS | `sheet_engine.png` against the A5 town as it is, and the story crop |
| References read before drawing | PASS | environments.md "Three-quarter objects ... a short contact shadow"; linework.md "Remove L-shaped doubles"; light-and-form.md "Hard surfaces have flat planes: one shade per face"; palettes.md "Each 8x8 background tile uses exactly one palette" |
| Lint | PASS with warnings | above |
| Colours per tile, palettes, tile count | PASS | table above |
| Squint test at 1x, DMG and Color | PASS | the statue reads first (dark lilac against the white sky), then the white basin; the jet is a light line on the dark tavern wall |
| Banding, squares, strays | PASS | glints are single pixels or pairs on purpose; no 2x2 blocks |
| Light direction | PASS | top left: terracotta lit side, lilac shade side |
| Footprint | PASS with a flag | the fountain covers the same area as the old trough (x 40 to 71 or 63, y 48 to 63) and a stack above; the tavern wall's left strip (x 56 to 63) holds the jet as before |
| Engine questions | none | no engine change (picture data only) |

## Doubts
- Not gold (rule 1 above). The owner decides: accept terracotta (as A5's tap already is), or spend a palette (the supervisor's call; WRAM is full) or add a cream wall behind the statue.
- One jet, no side streams.
- The stop marker sprite sits on the basin's lip as it does on the old trough.
- The statue is squat (body 5 rows): the stack is bounded by the nozzle at y 31 and the basin top at y 48.

## Rebuild
`python3 -I docs/dev/proposals/smap_layout_a5/mk_src.py`, then `mk_a5.py` (scratch, untracked outputs); then `python3 -I run.py 1|2|cur OUTDIR [probe_presnap.py|metrics.py]` renders and counts; `town_png.py` writes the indexed DMG strip for the lint; `engshot.py` takes the engine pictures from a scratch ROM (`GB_ROM=...`). The scratch engine build is a copy of the repo with the A5 `src/` files over `tools/smap_world/`, `engine_scratch.patch` applied, `SMAP_LAYOUT=lay_A5 SMAP_FOG=none SMAP_WATERDMG=light SMAP_FOUNTAIN=1|2`, venue module `v_town_fx` (the copy's `lay_A5.py` reads `SMAP_TOWNMOD`).

## Round 2 (owner: "for most of the game, the fountain will be broken. and the water doesn't seem to flow right out of the nozzle.")
Sheet: `sheet_broken.png` (story broken crop | opt 1 broken | opt 1 working | opt 2 broken | opt 2 working, DMG and Color x4, and the whole town broken for both). `sheet_engine.png` still shows round 1's jet (the engine ROMs were not rebuilt for the jet fix).

**Jet fix (both options, hand-typed pixels only):** the nozzle's bottom row is now solid ink (a lip) and the first two water rows sit directly under the mouth at x 56 and 57, so the water touches the opening and starts straight down, then drifts right (x 56, 56, 57, 57, 58, 58, 58, 59 ...), then falls into the basin. The cream glint no longer sits on the first row. Foam moved to x 60 to 63 under the new landing.

**Broken state** (`SMAP_BROKEN=1`, same file): the statue is a jagged two-spike stub of the body (y 30 to 33) on the same collar and plinth steps; arm, handle, cap, lever and jet are gone; bowl, column, foot block and basin walls are identical to the working state. The basin is dry, not still: still blue water reads as a working fountain at 1x, while the lilac floor (DMG 88 against the water's 168) reads as empty, like the story's dry basin. The story's night colours are not part of this (the map is by day).

| | opt 1 working | opt 1 broken | opt 2 working | opt 2 broken |
|---|---|---|---|---|
| DMG unique tiles (546 now) | 548 | 545 | 547 | 544 |
| DMG worst 21x19 window | 135 | 132 | 134 | 131 |
| DMG 22x20 window | 139 | 137 | 138 | 137 |
| Color tiles / slots | 619 / 352 | 616 / 352 | 619 / 352 | 616 / 352 |
| palettes per window | 8 | 8 | 8 | 8 |
Cells that differ between the broken and the working state (pixels; the palette table is the same): option 1: 11 cells, option 2: 12. In picture cells (x, y of the 12 x 9 town block, add (31, 19) for the map): option 1 (5,2) (6,2) (5,3) (6,3) (7,3) (5,4) (7,4) (7,5) (5,6) (6,6) (7,6); option 2 the same plus (8,6). That is the statue's and arm's cells, the jet's cells and the basin water band. Cells whose palette would differ between the states: none by the engine's table, but the broken top cells are all air (town1@g with only index 0) and could take the grass palette if the swap code prefers.
Lint of the broken picture was not rerun (the same grids with fewer pixels). The swap is not implemented in the engine.
