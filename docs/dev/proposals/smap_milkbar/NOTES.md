# Milk bar final round: sign B on `base` silver, tea cell merged, quality pass on the band

Owner (Q106): "Keep airbase silver. ... I prefer the last sign where the arrow is on the side." Built: sign B (diner), building body cells on `base`, the tea house cell (34, 59) on `tea@g` (Color only, DMG unchanged, as in `milkbar_sheet12.png`). `milkbar_sheet13.png` (two columns, large labels): B as picked | B after pass; DMG and Color, close-up x4 and map x3. Code: `sign_b2` in `src/cow_sign.py`, modes `cB` and `dB` of `src/render_one.py` (env `MB_TEAFIX=1 MB_PASTURE=1`), `src/sheet13.py`.

**Pass on the band only** (bottle, pole, head, building, lot, cows, pasture unchanged):
- **Bulbs:** in the picked version the bulbs were 1 px chrome dots touching the chrome tube, so they merged into it. Now the band is an ink outline round a 4 px pink fill (the chrome tube is gone from the band; the head keeps its tube), and the bulbs are 2 x 2 chrome blocks with a pink margin on every side, one every 4 px along the band (7 down the left side, 3 along the arm). They read as separate dots at map x3 on DMG (grey 168 on pink 88) and on Color (white-lilac on pink). Static.
- **Bend:** the bottom left corner is a stepped quarter circle of radius 4 instead of a square corner, and the inside corner is chamfered. At this size it is a stair, closer to the references' curve; a rounder bend does not fit (the lane starts right below the arm).
- The band is now 6 px of ink-pink-ink with 4 px of pink (it was ink, tube, 2 px of pink, tube, ink).

| | whole map | worst 21 x 19 anywhere | worst window at the milk bar | piece only | palettes per window |
| --- | --- | --- | --- | --- | --- |
| B as picked (base, tea merged) | 579 | 133 | 117 | 81 | 8 |
| B after pass | 579 | 133 | 117 | 81 | 8 |

Palettes per window are 8 everywhere on the map. Lint PASS (DMG) for the new picture; every pixel typed.

---

# Milk bar round 4k, A coffee sign on `base` (tea cell merged)

`milkbar_sheet12.png`: column 1 = A on factory (sheet 11), column 2 = A on `base` (98a0b0) with the tea house cell (34, 59) put on `tea@g` (Color only, DMG unchanged); close-up x4 and map x3, DMG and Color; under them the cells x 33..35, rows 58..60 before and after, Color x6. Code: mode `cA` of `src/render_one.py` (env `MB_TEAFIX=1`), `src/sheet12.py`. Nothing in the layout or the tea picture is edited: the merge is a palette assignment of that one cell in the scratch map.

Counts (A on base, tea merged): whole map 578 tiles, worst 21 x 19 view 133, worst milk bar window 113, palettes per window 8 at worst, everywhere on the map and near the milk bar (the 9 of the unmerged case are gone). Same art as A on factory, so the tile counts are the same.

**Correction to the earlier estimate.** The cell has 31 index 0 pixels, not 4: on `tea` all of them are the pale d8ecb0; 27 of them are the margin round the tea house's sign (outside the outline) and show as a pale square on the grass (the "before" crop). On `tea@g` they all become the grass colour b0d080, the square disappears, and the 4 inner highlight pixels (on the round sign) go from pale to grass green too. So the visible change is a removal of an existing pale patch plus a 4 px highlight loss.

---

# Milk bar round 4k, investigation: can `base` (98a0b0) fit the milk bar window?

With the building's body cells on `base`, 8 of the sliding 21 x 19 windows hold 9 palettes: origins x 33..34, y 41..44 (nothing else on the map, nothing with the factory palette). All 8 contain the same nine palettes:

| palette | cells in these windows | where |
| --- | --- | --- |
| grass | about 125..170 | the lawn west of the river and bank, rows 41..61 |
| water | about 118..131 | the river, x 37..48 |
| farm | 36..46 | the pasture and verge, x 48..54 |
| cow | 29..42 | pen fence, sign, cows, the sign block |
| town1 | 26..43 | the lane (road) at the bottom and the ring road at the top |
| tea@g | 3..8 | the tea house's cells next to grass, x 33..35, rows 57..61 |
| factory | 2..12 | the factory's bottom cells, x 52..54, rows 41..44 (top edge only; windows from y 45 down do not see them) |
| tea | **1** | cell (34, 59) |
| base | 1..5 | the milk bar's left two columns, x 53..54, rows 59..61 (right edge only; windows from x 35 do not see tea, windows from x 55 do not see the left two columns) |

The window origins are fixed by the tea house (left edge) and the milk bar (right edge) 20 cells apart, so the overlap is only the strip x 33..35 and x 53..54.

**Options**
1. **Merge the single `tea` cell (34, 59) into `tea@g`.** That cell is on `tea` because the generator found index 0 pixels inside the tea picture's outline (`world2.py` lines 146 to 158: a cell gets `@g` only if all its index 0 pixels are outside the outline). They are 4 pixels, (86, 36), (87, 36), (84, 37), (87, 39) of the picture, the highlight pixels of a rounded object on the tea house. On `tea@g` those 4 pixels would be grass green (b0d080) instead of the pale d8ecb0. Cost: 4 pixels of the tea house change colour on Color, DMG unchanged; the window drops to 8. It is the cheapest fix, but not "no visible change outside the milk bar": the tea house loses a 4 px highlight. Variant: redraw those 4 pixels as index 1 (cream f4ecc8) so that the colour stays near and no palette change is needed (this changes the DMG shade of the 4 pixels from the lightest to a lighter grey).
2. **Keep the milk bar's left two columns (x 53, 54) on COW** (white, not silver): base then only appears from x 55, outside the tea windows. Cost: a 16 px wide white strip at the building's left end (a pilaster look); nothing else changes.
3. Drop `factory`, `farm`, `town1`, `grass` or `water` from the window: not possible without recolouring terrain.
4. Move the milk bar two cells east: not possible, the ring road is at x 62.

I did not render the coffee sign on `base`: option 1 is not strictly clean (4 tea house pixels), option 2 is a visible change on the milk bar itself. Say which one to render.

---

# Milk bar round 4k (current): classic roadside arrow signs, building on a borrowed silver palette

Owner: "not what I wanted with the arrow. Something more like what these classic signs looked like" (refs `docs/dev/proposals/refs/owner_sign_diner.jpg`, `owner_sign_coffee.jpg`), then "can we borrow a silver palette from somewhere else on the map? so the cows and milk sign can stay white?" `milkbar_sheet11.png`: 4j silver (COW idx 1) | building on the FACTORY palette, no arrow | A coffee sign | B diner sign; close-up x4, A5 map x3, DMG and Color. Code: `src/cow_sign.py` (both signs typed row by row), `build(3, 'A', 2, new, borrow)` in `src/cow_a5.py`, `src/cow_roof.py` (`narrow`), `src/sheet11.py`.

**Signs** (both 24 px wide on the lawn between the bank and the building, x 0..23, y 64..119; thick 6 px band: ink outline, chrome tube, pink fill; a big solid head with a flat back and a 2 px tip pointing right at the bar; static):
- **A coffee:** the bottle on top of a tall vertical panel (10 wide) reading MILK top to bottom in chrome on pink, whose foot bends into the arm and head. The bottle moved up 2 rows (cap at y 64, just under the fence) to fit 4 letters and the bend above the lane.
- **B diner:** the bottle on its pole (pole and foot as before, 2 px right of 4j), the band wraps round the bottle's left side and under it into the arm and head, a row of bulbs (chrome dots, every other pixel) along the band's middle.
The head is only 10 px tall (6 px band): there is no room for more between the bottle and the lane (the lane starts at y 120).

**Silver by borrowing a palette.** COW idx 1 is back to `e8e0f0` (cows, bottle, fence, trough, sign post white). The building's body cells (wall cells y 96..119 in the picture: the two wing wall cells and the two cell rows under the sign block) are on an existing table entry:
- `base` [f8e090, 98a0b0, 1c2468, 080818] has the better silver but puts **9 palettes** in the milk bar window (limit 8): rejected.
- `factory` [d0c890, 88a090, 385048, 101818] gives 8. Its silver is a green-grey: it reads as dark olive-grey, not as light silver. It is the only candidate that fits the window; the 4j recolour (COW idx 1 `b0b8c8`) looks better. The trim line (pink in COW) becomes factory's idx 2, a dark green-grey.
- Cells: no cell shows ground (asserted in the build: no index 0 pixel in those cells). To get this the raised sign block is 48 px wide (was 52, edges on cell edges, word gap 4 instead of 5) so the two wings are whole cells; the wings' top row of cells (parapet and blank rows) stays COW, so the wing parapet is white and the wing wall silver. The neon block and the roof cap stay COW. DMG unchanged (index shades are the same).

| | whole map | worst 21 x 19 anywhere | worst window at the milk bar | piece only | palettes per window (milk bar) |
| --- | --- | --- | --- | --- | --- |
| 4j silver, no arrow | 574 | 133 | 112 | 76 | 8 |
| FACTORY silver, no arrow | 574 | 133 | 112 | 76 | 8 |
| A coffee | 578 | 133 | 113 | 80 | 8 |
| B diner | 579 | 133 | 117 | 81 | 8 |
(`base` instead of `factory`: 9 in every row.)

Lint PASS DMG and Color for A and B.

---

# Milk bar round 4j: cow across the lane, sign left, neon arrow, silver building

Owner: "v2. but move the cow to the left of the building under the building to the other side of the road, then move the milk bottle sign to the left a bit. Maybe try adding a neon arrow to the milk bottle sign that curves pointing down at the venue. And try making the color of the building silver instead of white." Base: 4i v2. `milkbar_sheet10.png`: v2 | new (no arrow) | new + arrow, close-up x4 and the A5 map x3, DMG and Color. Code: `build(3, 'A', 2, new)` in `src/cow_a5.py`, `MB_SILVER=1` in `src/a5env.py`, `src/sheet10.py`.

1. **Cow:** now on the south verge below the lane (picture x 6..19, y 144..153; world cells x 50..51, rows 65..66), left of the building's span, on grass, well below Sal's stop (lane row 63) and clear of the river bank. The pen cows are as before.
2. **Sign:** 6 px left (pole centre x 12, was 18); bottle x 4..19; foot still above Sal's box.
3. **Arrow:** a curved neon tube from the bottle's right shoulder over the lawn, 40 px long, descending to an arrowhead pointing down at the MILK BAR block's cap (head x 54..58, tip y 83, cap y 85). Chrome core, pink halo, like the lettering; static. Shown with and without (columns 2 and 3).
4. **Silver:** the chrome COW index 1 is `e8e0f0` (used by the building, the bottle's glass, the cows' bodies, the pen's fence and trough and the sign post). No other palette has a silver with pink at index 2, so I chose to change COW index 1 to `b0b8c8` (RGB555 grid) instead of giving the building another palette (a new slot; the table is full). Nothing else uses `cow` on the map (grep of tools/ and src/: only the generator, `pal.py`, `palsnap.py` and `v_cow.py`; `e8e0f0` also appears in `assets/approved/venues/biker_pal.json`, a different palette, untouched). What else changed colour: the cows, the bottle glass and label, the fence, the trough and the post go from white-lilac to silver; the cows read greyer. DMG unaffected (index 1 is still shade 1). Palette count unchanged.

| | whole map | worst 21 x 19 anywhere | worst window at the milk bar | piece only | palettes per window |
| --- | --- | --- | --- | --- | --- |
| v2 | 571 | 133 | 115 | 74 | 8 |
| new (no arrow) | 574 | 133 | 112 | 76 | 8 |
| new + arrow | 584 | 133 | 122 | 86 | 8 |

The arrow costs 10 tiles (its cells are mostly unique). Lint PASS DMG and Color.

---

# Milk bar round 4i: flat roofs and a neon sign

Owner: "Could I get versions of the milk bar where the roof isnt domed and the sign on the building looks more like a neon sign? Of the examples I like A's doors better." Base: 4h option A (dark glass windows, A's doors). Only the roof and the sign band changed (x 32..95, y 20..39 of the piece); position, lot, bikes, sign post, cow and pasture are as in 4g. `milkbar_sheet9.png`: 4h A | v1 | v2 | v3, close-up x4 and the A5 map x3, DMG and Color. Code: `src/cow_roof.py` (hand-typed roofs; the letters are round 3's 5 x 5 glyphs), `build(3, 'A', v)` in `src/cow_a5.py`, `src/sheet9.py`.

- **v1 flat roof with a parapet:** coping (2 chrome rows between ink lines), a cornice line, a dentil row.
- **v2 raised centre:** the sign block is taller (cap and cornice above it) and sits in a raised centre, 52 px wide; the two wings have a low parapet and a plain chrome wall; a neon underline under the letters. Reads best at 1x.
- **v3 canted roof:** the top edge climbs left to right in 5 steps, parallel ink stripes follow it, flat underside.
- **Neon sign (all three):** dark board, a 1 px pink tube border with the four corners cut, the letters 1 px thick with a chrome core (the hot tube) and a pink halo on the dark board (3 px between letters so the halos do not merge). COW indexes only: core 1, halo and tube 2 (pink), board 3. DMG: core shade 1 (light), halo and tube shade 2, board shade 3: light on dark, as asked. Static. I tried a star at each end of the line in v1 and v3 and took it out: it touched the lettering.

| | whole map | worst 21 x 19 anywhere | worst window at the milk bar | piece only | palettes per window |
| --- | --- | --- | --- | --- | --- |
| 4h A | 565 | 133 | 111 | 68 | 8 |
| v1 | 564 | 133 | 111 | 67 | 8 |
| v2 | 571 | 133 | 115 | 74 | 8 |
| v3 | 569 | 133 | 113 | 72 | 8 |

Lint PASS DMG and Color for all three; warnings: L-doubles and orphans (the halo pixels and letter ends are deliberate), the existing COW palette order.

---

# Milk bar round 4h: doors inside the wall, two non-pink window options

Owner: "Looks better. fix the doors on the bar to fit more in the building. Also--do the windows need to be pink?" Round 4g kept as is (position, sign, cow, pasture). `milkbar_sheet8.png`: 4g | windows A | windows B; building close-up x4 and the A5 map x3, DMG row and Color row each. Code: `src/cow_bldg.py` (hand-typed panes and door rows), `build(3, 'A' or 'B')` in `src/cow_a5.py`, `src/sheet8.py`.

**Doors.** Redrawn: 15 px wide (x 79..93 of the piece), with a chrome wall strip each side (x 76..78 and x 94), an ink frame, a chrome head, two leaves split by a 1 px ink line, 2 px handles, a chrome rail under the glass, the same ink line (y 51) as under the windows, a chrome panel and an ink threshold at the facade's foot (y 55). The door's top (y 42) is level with the window tops, the glass bottoms are level with the windows' (y 48). The pink trim row (y 41) now runs unbroken over the door.
**Windows.** Five panes now x 36..75 (the wall is chrome on both sides). A: dark glass, ink with a 3 px chrome glint, chrome rims; door glass the same. B: light glass, index 0 with ink frame and a chrome glint; door handles ink. Pink stays only on the MILK BAR board stripe, the trim row y 41 and the bottle.
**Palette.** COW: index 0 meadow (c8e888), 1 chrome (e8e0f0), **2 pink (f03898)**, 3 ink (2a1e34). No new colour. DMG: pink was shade 2 (88, mid-dark); A and B use shades 3 and 1 (A) and 0 and 1 (B) on the windows, so the DMG look changes too: A is dark panes with light glints, B is white panes with grey glints. Note for B on Color: index 0 is the meadow green, so the light glass is pale lime (it reads as reflecting the grass); there is no whiter index in COW.

| | whole map | worst 21 x 19 anywhere | worst window at the milk bar | piece only | palettes per window |
| --- | --- | --- | --- | --- | --- |
| 4g | 562 | 133 | 111 | 65 | 8 |
| A | 565 | 133 | 111 | 68 | 8 |
| B | 565 | 133 | 111 | 68 | 8 |

Lint PASS DMG and Color for both; A has more L-doubles (the dark glass meets the ink frame at its corners, deliberate), orphans as before.

---

# Milk bar round 4g: building one cell west, cow and sign swapped

Owner: "move the milk bar to the left a bit so it is not right on the corner. swap th location of the milk sign and the cow to the left of the milk bar." Supervisor reading, built: arrangement 1's pen kept (2 cows and the trough). The building with its lot and bikes moves 8 px (one cell) west, so one cell of grass (x 88..95 of the picture, world cell 61) lies between it and the north-south road. The cow stands where the sign stood in arrangement 1; the bottle sign stands beside the building where the cow was in round 4e. `milkbar_sheet7.png`: arrangement 1 | new, DMG row then Color row, x3, in the A5 map (red tick = Sal's stop). Code: `src/cow_a5.py` (`build(3)`), `src/render_one.py arr3`, `src/sheet7.py`.

Details: the lane (road tiles, TOWN1) runs the full picture width, the lot is the same 64 px wide, now at x 24..87. Sign: pole at x 16..19, bottle x 10..25 (1 px off the building's left edge at x 27), pole shortened by 8 px so the foot (y 110, 111) stays above Sal's 16 px box (y 116..132); Sal's stop (x 418, row 63) is on plain lane road. The lawn cow is at x 1..14, y 98..107, on grass, 1 cell from the river bank cell: the river bank needed no nudge. Only one reading was built: with a 16 px move there is no room left of the building for both.

| | whole map | worst 21 x 19 anywhere | worst window at the milk bar | piece only | palettes per window |
| --- | --- | --- | --- | --- | --- |
| A5 as it is | 547 | 133 | 101 | 44 | 8 |
| arrangement 1 | 557 | 133 | 111 | 61 | 8 |
| new | 562 | 133 | 111 | 65 | 8 |

Lint PASS DMG and Color; warnings as in round 4f (orphans, the road's L-doubles, the copied bottle).

---

# Milk bar round 4f: sign and cow repositioned (two arrangements), the hay field replaced by a cow pasture

Owner (Q106): "That milk bar option looks good, but lets reposition the sign and the cow.  Let's also get rid of the hay field--it's supposed to be a cow pasture." `milkbar_sheet6.png`: 4e as shown | arrangement 1 | arrangement 2, in the A5 map around the milk bar, DMG row then Color row, x3, red tick = Sal's stop (world px 418, 508). Building, lot, bikes: round 4e, pixel-identical (`cow_lot4.build()` is embedded unchanged). Nothing imported, no golden touched.

**What draws the hay field in A5** (generator, `tools/smap_world` and its A5 scratch copy `docs/dev/proposals/smap_layout_a5/src`): the striped field is `FIELDS = FIELDS_A4 = [(51, 48, 60, 53)]` (`scen_A5.py` line 50, copied into `lay_A5.py` line 184), drawn by `world2.py` (about lines 118 to 121, `FIELD_EDGE` and `FIELD` tiles, palette farm). The four bales are `HAYS = [(48, 56), (48, 59), (51, 54), (58, 53)]` (`scen_A5.py`), placed through `decor.HAY` in `lay_A5.SCENERY`. `BARNS = []`. In A5 nothing else reads `FIELDS` or `decor.HAY`; the older layouts (`lay_A3`, `lay_A4`) and the live `tools/smap_world/world2.py` use the same two names, so the real change is one edit to the A5 layout (`FIELDS = []`, bales out of `SCENERY`) once the owner picks. In this proposal `src/a5env.py` does it only in memory (env `MB_PASTURE=1`), the repo's layout files are unchanged.

**The pasture.** The picture grows to 96 x 184 (cells x 50..61, rows 47..69, `src/cow_a5.py`): the grass is the farm biome's own ground (blank cells keep it), a typed fence (post tile, rail tile, side tile, white with ink, COW palette, no new palette slot) round cell rows 47..54 and x 50..61, a trough (typed, 16 x 5), and cows from round 2's cow (copied). The lane west of the lot (x 50..53, rows 62 and 63) is now typed road (the road's F1 and ES tiles, TOWN1) because round 2's cow venue used to cover it. This also fixes 4e's open issue 2: no cow stands on a road cell any more.

**Arrangement 1.** The sign stands at the west end of the lane (pole x 8, foot 8 wide) where the road comes in from the bridge, on the grass above the kerb; the pen holds two cows and the trough. The old cow place is road again.
**Arrangement 2.** The sign is a roadside sign on the south verge across the lane (cell x 55, rows 64..68, a shortened pole), facing the diner; one cow grazes on the lawn west of the building above the lane (feet row 61, off the road), the pen holds the trough and the small cow.

**Sal's stop** (x 418 = cell 52, row 63) is on plain lane road in both: nothing stands on it. Sal's body is about 16 px wide and 16 tall above the stop: arrangement 1's sign foot (x 4..11 of the piece, y 118, 119) is 2 px from the left edge of that box (x 10): may touch a transparent column; arrangement 2 is clear.

**Tile counts** (unique DMG tiles, the generator's own counter: distinct 8 x 8 cells of `WORLD_DMG`, whole map; worst 21 x 19 window over the whole map and among windows touching the piece area x 50..61, rows 47..69). Colour windows: palettes per 21 x 19 window, cap 8.

| | whole map | worst 21 x 19 anywhere | worst window at the milk bar | piece only | palettes per window |
| --- | --- | --- | --- | --- | --- |
| A5 as it is (hay field, round 2 milk bar) | 547 | 133 (at 28,19) | 101 | 44 | 8 |
| 4e (hay field, 4e piece) | 546 | 133 | 98 | 45 | 8 |
| arrangement 1 + pasture | 557 | 133 | 111 | 61 | 8 |
| arrangement 2 + pasture | 560 | 133 | 106 | 62 | 8 |

The map's worst window (limit 176) is far from the milk bar and is unchanged. The pasture costs 15 to 17 tiles over the 4e piece (fence, trough, cows, the lane tiles; the whole-map count rises by 11 to 14 over 4e even though the hay field tiles leave the map: I did not split the two effects). DMG and Color both fit: all new cells use COW and TOWN1, which the windows already hold.

**Still open.** The venue-over-road assert (`world2.build`) still fires for the lot and lane cells (as in 4e); the generator must be given the 96 x 184 piece as a venue with road cells exempt, and the lot cells stay walkable. Nothing here was run in the engine: renders come from the scratch generator and the pasted piece (this is the real A5 map data, not an old screenshot).

**Self-audit.** Lint (`gb_art_lint.py`, DMG and Color, bg): PASS for both arrangements; warnings: orphan pixels (fence ends, trough legs, the cows' ears and the road's own speckle, as in earlier rounds), 3 L-shaped doubles in the road tile at y 126 (the road's own tiles), 2 to 3 in the sign (round 2 C's bottle, copied); palette-order warning is the existing COW palette (idx 0 is the meadow colour, idx 1 the chrome), not changed. Every pixel typed or copied from round 2 and the road tiles; scripts only paste, count, render.

---

# Milk bar round 4e: the same lot and 3/4 bikes, checked in the A5 layout

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
