# Space mountain hangar, round 4 (proposal only; nothing in assets/, no goldens)

Owner: "round 3 no runway. But do a little more work on the hanger. It looks like a hut. Maybe a runway in front again, with a little plane sitting inside the hanger doors?"

Sheet: `hangar_sheet.png` (x3; the hangar close-ups are pre-doubled so they show x6). Rows: DMG hangar close-ups, Color close-ups, whole mountain DMG, whole mountain Color; columns: round 3 | option 1 | option 2. The angled runway is gone. Peaks, mast, lamp, dish and tower are round 3's code, unchanged. Sources: `src/` (typed grids in `hangar_h.py`; it imports round 3's `base3.py`, `mountain_a.py`).

Both options: hangar 34 x 16 (round 3: 32 x 14), foot on y 63, x 0 to 33 (the tower cab starts at x 36). A strip in front on the piece's last cell row (y 64 to 70): an apron under the doors (x 4 to 29, 2 rows) joining a short runway (x 1 to 50, 5 rows, ink outline, navy asphalt, lit kerb, dashed centre line period 8). It uses only BASE colours 0 to 3: DMG and Color both, nothing is Color only.

- Option 1, arch front: the whole front is one curved arch (Quonset end), rim lit left and shaded right, a wide arched opening (24 wide, navy) with a plane seen head on (tail fin, straight wing, fuselage, two legs, floor shadow).
- Option 2, curved roof and slid doors: a ribbed barrel roof (outline runs 4, 3, 2, 1) over an eave and its shadow row, a hazard lintel, door leaves slid back to both sides, a broad black slot (22 wide) with a side-view plane (tail fin, far wing tip, cockpit window, belly, leg stubs), nose to the right.

## Unique DMG tiles of the mountain piece (same counter as round 3: ground tiles and blank cells free)

| | no strip | with strip | strip costs |
|---|---|---|---|
| Round 3 hangar (no runway shipped) | **86** | 91 | +5 (if it had one) |
| Option 1 arch front | **88** | **93** | +5 |
| Option 2 curved roof | **88** | **93** | +5 |

The bigger hangar and the plane cost +2 over round 3 (the strip sits on the piece's row 8, whose cells were free ground). The strip costs +5: runway cells repeat every 8 px, so the cost is its two ends, the apron joins and the open left edge. DMG lint counts the blank cell too (87 / 94), same offset as round 3.

## Self-audit (gb-pixel-art)

| check | result |
|---|---|
| Hand-placed | Every hangar row, both planes and the strip are typed in `src/hangar_h.py` (strings of 0..3 built from typed runs, `"1" * 12`-style). Scripts only paste (`C.paste`), render, count tiles, make the sheet and the lint PNGs. No fills, mirroring, outlining or shading by code. The strip is typed runs per row. |
| Clean-up pass by hand | Done. Log: option 1 first draft had L-doubles at the opening's crown steps (5,55)/(28,55): ink 2-run on r7 cut to 1 so the edge steps diagonally; option 2 first draft: leaves 5 wide crowded the slot, now 3 wide (slot 14 to 22 wide), plane redrawn at 22 wide with a pointed nose; hazard stripe phase moved so no stripe ink touches the slot corners (L-doubles 3 to 1). |
| 1x comparison with the quality bar | Against round 3's hangar and the picked igloo style at 1x in the sheet. Both options read as a hangar at 1x (the arch especially); the planes read as a plane at x3, thin at 1x. |
| Required refs read first | environments.md ("Openings (doors, tunnels) face the viewer ... with a dark interior and a lit rim on the light side"), linework.md ("Steps connect diagonally only. Remove L-shaped doubles"), light-and-form.md ("Background objects: shade 3 only for the deepest shadows; walls and solid boundaries may use it structurally"), palettes.md ("Approve the DMG version first"). Not re-read: hardware.md, sprites.md, figures (round 3 notes list the same). |
| Lint | PASS (DMG and Color, all three mountain pieces). Warnings: orphan pixels 16 (round 3) to 18 / 20 (options): the plane's fin, wing tip, legs and the dash line ends, intended. Option 2: one L-double at (6,57), the corner of the black slot against the plane's neighbour; the slot is a filled area, not a line. Palettes 2 of 8 (BASE + SALOON), unchanged. |
| DMG value separation | Rim 1 (lit edge 0) against ink 3 and ground 0; slot navy 2 (option 1) or ink 3 (option 2) against the plane's 0/1; asphalt 2 against ground 0 with ink outline; dashes 0 on 2. Plane vs slot is the strongest contrast on the hangar. |
| Periodic patterns | Ribs every 4 px (x = 3 mod 4), dash period 8, hazard period 4. |
| Squint test 1x, DMG and Color | Option 1: dark arch with a light cross reads first, then the strip. Option 2: boxy roof with a dark slot and a light shape in it. |
| Tiled preview | Not applicable (one-off piece); the strip's period-8 repeat checked in the sheet. |
| Owner's liked pieces untouched | Peaks, mast, lamp, dish, tower: pixel-identical to round 3 (same code path). |

## Deviations from the skill

- "Show art in the real engine (make BUILD=out/b_real ... scratch builds)": not done; the pieces render with the repo's world renderer on the biome ground, as in rounds 2 and 3. `make` still builds (nothing outside docs changed).
- Round 3's mountain skyline fill (`mtn_kit.peak`) is reused unchanged, as flagged in round 3.
- "For a batch, deliver ONE figure first": the brief asked for two options.

## Questions for the layout and the programmer

1. The strip lives on the piece's bottom cell row (y 64 to 70); assumed the layout leaves the cells below the mountain's foot line free (the piece's row 8 is ground today).
2. The strip is capped with ink at both ends (x 1 and x 50); assumed nothing needs to continue past the piece edge.
