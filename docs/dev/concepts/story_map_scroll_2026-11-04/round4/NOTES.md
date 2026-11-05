# Story map, round 4: the engine spec (concept art, last art round)

Owner approved the map in Q78. Coordinator calls for this round: the fountain water stays pale blue; draw the DMG trim; check the scratch budget; make this file the complete spec.
Nothing is in `src/`, `tests/`, `assets/` or the goldens. Previews are scripted (`tools/`), not an engine build (declared deviation, see the audit).

## Files
- `sheet.png` phone sheet. `dmg_trim_x4.png` DMG full | DMG trimmed for all 11 vignettes at x4. `dmg_merge.json` the DMG merge table (394 pairs of 8x8 tiles).
- `walk_cgb.gif`, `walk_dmg.gif` Stadium to Saloon, 3.3 s, front-facing. `map_{early,late}_{cgb,dmg}_x2.png`, `view_*_x3.png`, `vignettes_x4.png`, `walk_strip.png`, `tiled_preview.png` (the last three are round-3 pictures; the tiles they show did not change except the town water).
- `tools/` sources. Checks: `palcheck.py` (every window, all 11 unlock states), `palsnap.py` (cell palette snap), `palareas.py`, `stats2.py`, `slots.py`, `slots_dmg.py`, `dsatur_test.py`, `speedcaps.py`, `stats4.py`, `dmgtrim.py` (merge table), `dmgview.py` (DMG full vs trimmed pictures).

## What changed since round 3
1. **Fountain water is pale blue again** (palette TOWN4: f8f0b0 b8d8f0 a090b0 201828, RGB555 5bdf 7b77 5a54 1464). No accent changed colour. The slot came from the ground instead: 2 hay bales removed (312,262) (350,264), one hay moved (420,296 to 432,296), one mound moved (420,158 to 432,158), and 72 ground cells snapped to a neighbour's palette (`palsnap.py`, colour distance limit 600, cells never moved twice). TOWN1 and TOWN5 are untouched; the town now uses three palettes (town1 357 cells, town5 32, town4 6).
2. **Palette check** over all 41 x 30 window positions and the 11 unlock states: **worst window 8 palettes** (cell (19,5), states 6 to 10; per state 5, 7, 6, 8, 8, 8, 8, 8, 8, 8, 8), **0 windows over 8**.
3. **DMG trim drawn as a tile-merge table** (below), shown full vs trimmed in `dmg_trim_x4.png`.
4. Sign lettering is protected from the merge (TAPS, LODGE, ROBOCO, BISTRO, ZOO, MILK, the 2417 scoreboard).

## Palettes per area (late world; cells; RGB555 words)
| Area | Palettes (cells) |
| --- | --- |
| town | town1 357, town5 32, town4 6 |
| saloon | saloon 260, town1 45 |
| stadium | stadium 204, town1 39 |
| lodge | grass 207, lodge 56, town1 36 |
| bistro | bistro 169, town1 30, grass 1 |
| igloo | igloo 265, town1 40, grass 4 |
| factory | factory 78, town1 28 |
| cow | farm 272, cow 129, town1 53, grass 11 |
| tea | tea 258, town1 55, grass 12 |
| zoo | zoo 175, town1 32, saloon 28, grass 1 |
| space | saloon 92, base 77, town1 20 |

| Palette | Colours 0 1 2 3 | RGB555 words |
| --- | --- | --- |
| base | f8e090 98a0b0 182068 080818 | 4b9f 5a93 3483 0c21 |
| bistro | f0e8d8 78c0b0 286868 082830 | 6fbe 5b0f 35a5 18a1 |
| cow | c8e888 e8e0f0 f03898 281830 | 47b9 7b9d 4cfe 1865 |
| factory | e8e8e0 8898a8 384858 101818 | 73bd 5671 2d27 0c62 |
| farm | c8e888 e8c860 986838 281808 | 47b9 333d 1db3 0465 |
| grass | b0d080 68a048 286038 102018 | 4356 268d 1d85 0c82 |
| igloo | e8f8f8 68a8d8 285090 081838 | 7ffd 6ead 4945 1c61 |
| lodge | b0d080 e0b060 905830 281008 | 4356 32dc 1972 0445 |
| saloon | f8e090 e8b060 a05828 301008 | 4b9f 32dd 1574 0446 |
| stadium | d0d8e0 e04030 283878 101028 | 737a 191c 3ce5 1442 |
| tea | d8e8b0 f0e8c8 a05030 281810 | 5bbb 67be 1954 0865 |
| town1 | f8f0b0 f0b888 a090b0 201828 | 5bdf 46fe 5a54 1464 |
| town4 | f8f0b0 b8d8f0 a090b0 201828 | 5bdf 7b77 5a54 1464 |
| town5 | f8f0b0 f0b888 e8a828 201828 | 5bdf 46fe 16bd 1464 |
| zoo | d8f0a0 58b048 186830 082818 | 53db 26cb 19a3 0ca1 |
| fog:grass | b0d080 f8f8f8 d8e0f0 b0b8d8 | 4356 7fff 7b9b 6ef6 |
| fog:saloon | f8e090 f8f8f8 d8e0f0 b0b8d8 | 4b9f 7fff 7b9b 6ef6 |
| fog:fogbase | f8f8f8 f8f8f8 d8e0f0 b0b8d8 | 7fff 7fff 7b9b 6ef6 |

That is **18 palette entries** (`pal_rgb[18][4]`), 8 live at once. The preview's channel order is as typed; take the game's own words where it has them (cow = `assets/approved/venues/biker_pal.json` stage_a/stage_b). DMG: one BGP, shades 0 to 3 by index, fog is shade 1 over grey.
Folds used to stay at 8: forest into grass, desert into saloon, factory_b into factory, zoogate into zoo, tea_b into tea, town3 into town5 (`world2.MERGE`). Ground follows its venue (`GROUND_OWNER`), the desert south of row 31 belongs to the space lounge. Fog: cloud edge tiles carry a ground pixel and use `fog:<class>` (grass, saloon, fogbase); interior cloud tiles take the commonest class of the state.

## Palette slots (Color)
A window never needs more than 8 palettes, but a fixed palette-to-slot table fails from 7 venues open, so slots are allocated while scrolling: **refcount per slot (8 x u16 = 16 B)**. A cell entering the window increments its palette's count (a palette with count 0 takes a free slot and queues an 8 B palette write for VBlank); a cell leaving decrements, a slot frees at 0. `palslot[18]` maps palette to slot (0xFF = none). Cell attributes written to bank 1 of the map use the slot number, so a cell's attribute is computed at stream time, not stored per slot.

## Tile slots
- **Pool:** map-screen BG tiles: ids 0-35 and 93-232 in bank 0 = **176 slots**. Bank 1 (Color) gives the same 176 again: **352 slots**. The generic tiles (36-76) and the story font (77-92) stay resident outside the pool, the 9 dim letters sit from 233. **The name-tag font does not share the pool** (`gen_smap.py` FONT_END = 93, DIM_BASE = 233; `src/smap.c` tag tiles are in the fixed ranges), so the DMG target is **176**, not 146 (round 3 doubt 2 answered).
- **Plan (static, offline):** a tile gets one slot; two tiles share a slot only if no 21 x 19 window holds both (greedy colouring of the conflict graph, `slots.py`; DSATUR gave the same 187 on the DMG set, `dsatur_test.py`).
- **Color (full detail):** 904 unique tiles, **216 slots**, at most 8 tiles per slot (mean 4.2); worst window **203 tiles** (cell 3,23) against 352. Fits with 136 slots to spare for the 4-column look-ahead.
- **DMG (trimmed):** 530 tiles in the late world (904 before), **176 slots** (greedy colouring), worst window **159 tiles** in every state, at most 6 tiles per slot. The window-only target (176) needed 279 merges but its colouring still wanted 187 slots; 394 merges make the colouring fit, so the plan, not the window, sets the trim.
- **Resident table** (WRAM, `story_scratch`): one nibble per slot, the tile variant 0 to 6 now in it (15 = empty), 216 nibbles Color = **108 B** (113 B reserved for 226 slots), DMG 176 nibbles = **88 B**.

## DMG data set versus Color data set
| | Color | DMG |
| --- | --- | --- |
| tile set | 904 tiles, first-use order by unlock state | 530 tiles: the same list after `dmg_merge.json` (394 tile pairs, dropped tile to kept tile, both already drawn) |
| slots | 216 of 352 | 176 of 176 |
| attributes | palette slot + bank bit per cell | none |
| palettes | 18 words x 4, 8 slots | one BGP |
| ROM | `cell_tile` u16 + attr | `cell_tile` u16 only (tile ids remapped), no attribute table |
Merge rule (`dmgtrim.py`): candidate pairs ranked by (sum of shade differences) x (cells using the dropped tile); a dropped tile is never a target, a target is never dropped (no chains); sign-lettering tiles are never dropped; pairs are taken in rank order, the count is the smallest that makes the late world colour into 176 slots (394). Largest single tile difference 23 shade steps (the pixels are always from an existing hand-drawn tile). **Trim effect per vignette** (pixels that differ, `dmgview.py`): saloon 4.5%, stadium 1.6%, lodge 4.2%, bistro 3.6%, igloo 5.7%, factory 6.9%, cow 1.6%, tea 4.9%, zoo 3.0%, space 2.7%, town 1.2%. Every place stays recognisable on DMG (picture: `dmg_trim_x4.png`); the lodge door, the bistro door and the factory battery cabinet lose the most detail. If the owner wants a hand-drawn DMG version of those details, it replaces the merge for those tiles and the count is re-run.

## Tile set per area (Color; tiles / of them only there)
town 105/94, saloon 104/90, stadium 60/48, lodge 126/120, bistro 54/50, igloo 123/112, factory 65/55, cow 97/83, tea 76/59, zoo 92/83, space 87/75. Late world 904 tiles; town alone 127 (window 115). Window max by state: 115 (0 open), 172 (3), 174 (5), 197 (8), 203 (10).

## Stream data format
All in banked ROM (2 banks, about 26 KB Color, about 22 KB DMG):
- `tile_data[N][16]` 2bpp tiles in first-use order; `state_end[11]` u16 tiles per unlock state (a state is a prefix).
- `cell_tile[48][64]` u16 tile index (late map); `zone[48][64]` u8 (3 KB) and a fog table: fogged cells are rebuilt on entry from the zone ids as `world2.fog_tiles` does (edge sequence `B0 B1 S B0 B1 S S B0 B1 B0 B1 S`, 12 fog tiles shared).
- `cell_attr[48][64]` u8 (Color only): palette index 0 to 17, bank bit; no flips.
- `slot_of[N]` u8 (0-175 bank 0, 176-215 bank 1, Color; 0-175 DMG), `var_of[N]` u8 0 to 6.
- `pal_rgb[18][4]` u16 (Color only).
- Column or row step (camera crosses a cell boundary): for each of the 19 (21) new cells: `if resident[slot] != var` queue 16 B to the slot; write the slot id to the 32 x 32 hardware map (wrapped), attribute to bank 1 of the map, palette refcount update. Tiles first, ids after, so no cell shows a wrong tile.
- Map-screen entry and every unlock: LCD off, load the window plus 4 columns / rows ahead and the 8 live palettes.

## Camera caps (`speedcaps.py`, late world)
Drain is 86 B per frame (`VQ_DRAIN_BUDGET`). A line is crossed in 8 / s frames at s px a frame. **s = the largest of 4, 3, 2, 1 with 86 x 8 / s >= pending bytes.**
| | worst line | speed 4 | 3 | 2 | 1 |
| --- | --- | --- | --- | --- | --- |
| Color column | 278 B | 73% | 22% | 5% | 0 |
| Color row | 346 B | 57% | 21% | 22% | 0 |
| DMG column (full ids, before trim) | 259 B | 83% | 16% | 1% | 0 |
| DMG row | 325 B | 63% | 26% | 11% | 0 |
The trimmed DMG set streams fewer new tiles per line; the table is the pessimistic full-detail figure. Look-ahead on Color lifts most lines to 4. Sal walks 3 px a frame; if the camera is held below that it trails him (80 px of room), and past 32 px behind Sal waits. Follow rule: `gap >> 2`, minimum 1, maximum as above.

## Sprites (OBJ), exact ids
- **Sal: no OBJ tiles of his own on the map.** Boot-time bartender tiles (`OBJ_BARTENDER` 0): picture p (0 idle, 1 walk1, 2 walk2) is tiles 8p to 8p+7; entries A = 8p, B = 8p+2, C = 8p+4, D = 8p+6 (8x16 pairs, as `draw_bartender`). A at (left, top), B at (left+8, top), C at (left, top+16), D at (left+8, top+16); left = feet x - 8, top = feet y - 24; OBJ palette 0; no flip; front frames only. Walk: step1, stand, step2, stand, one picture per 2 game frames.
- **Map sprites from OB = 56** (`smap.c`), in pairs: ufo 56 58 60 (24 x 16), dot_open 62, dot_locked 64, bang 66, arrow_right 68, arrow_up 70, arrow_down 72 (arrow_left = arrow_right x-flipped). 18 tiles. OBJ palettes: ufo 2, open dot 3, locked dot 4, arrow 6, bang 7. Palette 1 is free.
- At most 11 objects on screen and 6 on one scanline (`stats4.py`) against 40 and 10.

## Scratch budget: `story_scratch` = 520 B (`src/scratch.h`), the map screen is its only user
The existing map layout (`src/smap.c`: ROWBUF, ATTR_PANEL, ATTR_TAG, TAGROW, V) uses offsets 0 to 199 (panel rows, attributes, tag row) and 400 to 411 (V). The new tables go in the gaps; nothing else is added.
| Bytes | Use |
| --- | --- |
| 0 to 199 | existing: panel rows, ATTR_PANEL, ATTR_TAG, TAGROW (unchanged) |
| 200 to 312 | resident nibble table, 113 B (DMG uses 88 B) |
| 313 to 328 | palette refcounts, 8 x u16 (Color only) |
| 329 to 385 | pending uploads, 19 x 3 B (slot, variant) |
| 386 to 399 | spare 14 |
| 400 to 411 | V (existing) |
| 412 to 475 | tile staging, 64 B (4 tiles) |
| 476 to 493 | `palslot[18]` (palette to slot, 0xFF = none) |
| 494 to 510 | camera and stream variables, 17 B |
| 511 to 519 | spare 9 |
Used 505 of 520 B counting the gaps as spare (23 B spare in two gaps). Fits. **Needs:** register the new ranges in `tests/test_scratch_map.py` USERS. No new WRAM global, no ROM0 code (new code in `smap.c`, bank 255). The offsets are a proposal; check them against `smap.c`'s macros when building.

## Build pipeline expected
Inputs the programmer gets from this folder: `tools/v_*.py` (typed vignette grids), `tools/decor.py` and `tiles.py` (typed scenery and ground tiles), `tools/world2.py` (the 64 x 48 composition: venue positions, roads, scenery positions, `MERGE`, `GROUND_OWNER`), `tools/palsnap.py` (cell palettes), `dmg_merge.json`, the palette table above. Proposed generator: **new `tools/gen_smap_world.py`** (leave `gen_smap.py` for the panels and tag), steps:
1. Import the concept modules (or an `assets/map/world.txt` and `assets/map/palettes.json` exported from them once the owner locks the art; `assets/` gets nothing until then).
2. Build the late world, dedupe tiles, number them in first-use order by unlock state, write `state_end`.
3. Colour the conflict graph (greedy, as `slots.py`) and write `slot_of`, `var_of` (Color: 216 slots; DMG: remap through `dmg_merge.json` then colour, expect 176).
4. Emit `build/smap_world_cgb.c` and `build/smap_world_dmg.c` (const arrays in banked ROM) and check at build time: window max tiles <= pool, window palettes <= 8 over all states, slots <= 352 / 176, scratch map sums <= 520. A failed check stops the build.
Then `make`, `make test`, `make check` as for any asset.

## Self-audit
| Check | | Evidence |
| --- | --- | --- |
| Hand-placed | PASS | typed grids (`v_*.py`, `tiles.py`); the merge table only chooses between tiles already drawn |
| Clean-up pass by hand | PASS | two hay bales removed and two scenery pieces moved for the water slot; sign lettering protected after the first merge broke it (TAPS, LODGE, BISTRO, ROBOCO, MILK, 2417) |
| 1x comparison with the bar | PASS | `sheet.png` at 1x, `dmg_trim_x4.png` full beside trimmed |
| References read | PASS | SKILL.md and its references (round 3), `src/smap.c`, `src/scratch.h`, `tools/gen_smap.py` this round |
| Lint | FAIL (cannot be cleared) | Color: "palettes needed (greedy estimate): 14 of 8" because the linter reads the 512 x 384 world as one screen; no screen holds more than 8 (`palcheck.py`). Not re-run on the DMG trim |
| Colours per tile, palettes, tile count | PASS | Color 203 of 352, DMG 159 window / 176 slots of 176, palettes 8 per window |
| Scanline budget | PASS | 11 objects, 6 per line |
| Squint test | PARTIAL | DMG trimmed pictures at x4 only, the world map DMG preview was not re-viewed at 1x after the final merge; the MILK neon is faint |
| Tiled preview | PARTIAL | round 3's `tiled_preview.png` was kept; the 72 ground cells that changed palette were not re-tiled |
| Animation | PASS | the game's three front frames |
| Files | PARTIAL | previews are RGB PNGs; nothing for `assets/` yet |

## Doubts
1. The DMG trim is a script choosing which hand-drawn tile replaces which. Skill wording to weigh: "Code may not *decide* pixels: no auto-outliners, ... filters, smoothing, resampling...". It invents no pixel, but it does decide. If the owner says no, the 394 merges become a hand list per vignette (lodge, bistro and factory doors first).
2. 394 merges (not 279) because the static slot colouring needs 187 slots at the window limit; dynamic slot reuse in the engine would allow 279 but costs a relocation step. Programmer's choice.
3. The scratch map is a layout proposal; the offsets must be checked against `smap.c` and `test_scratch_map.py` when built.
4. Previews are scripted, not an engine build.
5. Cloud in the early states is flat in Color; the cow neon is faint on DMG.
6. Sal covers the cows at the cow stop; he never covers a name or door.
