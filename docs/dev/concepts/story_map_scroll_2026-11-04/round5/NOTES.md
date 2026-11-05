# Story map, round 5: the engine spec (concept art; DMG hand trim; dynamic tile slots)

Round 4 was accepted for the blue water and the scratch map. Its DMG trim (a script choosing tile merges) was rejected: code may not decide pixels. This round replaces it.
Nothing is in `src/`, `tests/`, `assets/` or the goldens. Previews are scripted (`tools/`), not an engine build (declared deviation, see the audit).

## Files
- `sheet.png` phone sheet. `dmg_trim_x4.png` DMG full | DMG trimmed per changed vignette at x4. `walk_cgb.gif`, `walk_dmg.gif` Stadium to Saloon, 3.3 s (gifcheck: brightest step 7 and 9 of 255, no strobing). `map_{early,late}_{cgb,dmg}_x2.png`, `view_*_x3.png`.
- `tools/` sources. New this round: `winstat.py` (window max per unlock state, windows over 176), `winshapes.py` (21x19, 21x18, 20x19), `alloc_sim.py` (the allocator, frame by frame along all 22 walks), `hybrid.py` (static plus overflow test), `cmp.py` (full vs trimmed pictures), `worldpng.py` (DMG world as one PNG for the lint), `tileheat.py`, `near.py`, `rowsim.py`, `reach.py`, `idmap.py`, `winview.py`. `world2.py` has `WORLD` (Color and DMG full art) and `WORLD_DMG` (the hand-typed DMG variants).
- The static merge table (`dmg_merge.json`, `dmgtrim.py`) is gone. The static slot plan is dropped for DMG.

## What changed since round 4
1. **DMG hand trim.** Only where a window is over 176. Every change is a typed grid or a typed position in `v_*.py` / `world2.py` under `dmg=True`; no tile is substituted by code. Signs, doors, windows and outlines are untouched.
2. **DMG tile slots are dynamic** (spec below). DMG has to fit the worst window, not a colouring of the whole world.
3. Color: the world, palettes and tile set are unchanged (re-run: palcheck worst window 8, 0 over; stats2 904 tiles, window max 203).

## Worst window, DMG (21 x 19 cells, both axes off the 8 px grid), per unlock state (0 to 10 venues)
| | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| full art | 115 | 144 | 139 | 172 | 174 | 174 | 198 | 197 | 197 | 197 | 203 |
| windows over 176 | 0 | 0 | 0 | 0 | 0 | 0 | 67 | 101 | 100 | 107 | 157 |
| trimmed | 115 | 120 | 121 | 148 | 151 | 151 | 171 | 172 | 172 | 172 | 175 |
Worst window full art **203**, 157 windows over 176, most to lose **27 tiles** (state 10). After the trim: **worst 175 of 176, 0 windows over**, in every state. One axis on the grid: 21 x 18 worst 170, 20 x 19 worst 168. Margin is one slot at the worst window.

## The DMG hand trim (what was typed, per vignette; distinct tiles before to after)
Method: one tile saved needs the picture to repeat on the 8 px grid, so repeated objects and periodic patterns were retyped on the same phase, and details away from signs and doors were simplified.
| Vignette | Tiles | Hand changes (DMG only) |
| --- | --- | --- |
| factory | 58 to 47 | repeated parts retyped on the 8 px grid (see the `dmg` branches in `tools/v_factory.py`) |
| lodge | 70 to 54 | repeated parts retyped on the grid (`tools/v_lodge.py`); door and antlers unchanged |
| zoo | 54 to 43 | fence rails at y 32 and 40 (Color 32 and 44), bars unchanged |
| stadium | 52 to 46 | repeated parts retyped on the grid (`tools/v_stadium.py`); flag and scoreboard unchanged |
| igloo | 52 to 45 | repeated parts retyped on the grid (`tools/v_igloo.py`) |
| cow | 52 to 45 | bikes at x 28 and 52 (Color 28 and 49) so both share tiles; fence kept clear of them |
| bistro | 51 to 47 | the two brick patterns made 8 px wide |
| saloon | 58 to 53 | boardwalk `0:2 (2:7 3:1)*8 2:4 0:2` (Color `2:8 3:1 *7 2:5`), roof tooth pattern `13 11 10 8 7 5 4 2 0 0` |
| space | 74 to 73 | strata lines on rows 12, 20, 28, 36 |
| tea, town | unchanged | approved town art is not touched |
Ground: DMG picks the first of the ground variants except on cells 3, 8, 11 of the period, forest picks variants on a 4-cell period; road uses one floor tile (F1) instead of the chess pair. Scenery: DMG list typed on the 8 px grid (`SCENERY_DMG`); props removed on DMG only (fence, hitching post, tumbleweeds, bistro table and shrub, stones, one pine); others move up to 8 px against the Color picture. See doubts.
Tried and reverted: 45 degree butte slopes (3 tiles saved, shape distorted); removing the saloon barrel or hitching post (cost a tile).

## Palettes per area (late world; unchanged from round 4)
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
18 palette entries (`pal_rgb[18][4]`), 8 live at once (worst window 8, 0 over, all 11 states). Folds: forest into grass, desert into saloon, factory_b into factory, zoogate into zoo, tea_b into tea, town3 into town5 (`world2.MERGE`). DMG: one BGP, fog is shade 1 over grey.

## Palette slots (Color)
Refcount per palette slot (8 x u16 = 16 B). A cell entering the window increments its palette (count 0 takes a free slot and queues an 8 B palette write for VBlank); a cell leaving decrements; a slot frees at 0. `palslot[18]` maps palette to slot (0xFF none). Attributes are computed at stream time.

## Tile slots: pool
Map-screen BG tiles ids 0-35 and 93-232 in bank 0 = **176 slots**; Color adds bank 1 = 352. The generic tiles (36-76), story font (77-92) and name-tag font stay outside the pool.

## DMG allocator (dynamic slots; simulated in `alloc_sim.py dmg 2 rr`)
- **Slot table:** 176 entries, each the 10-bit id of the resident tile (0x3FF = free), packed: 176 x 10 bit = **220 B**.
- **Lookup (tile id to slot):** one ROM byte per tile, `hint[tile]`, the slot it was last given at build time; check `table[hint] == tile`, else scan the 176 entries. A tile is also marked resident by the need bitmap below.
- **Refcounts / need bitmap:** a slot is in use if its tile is in the view now or in the view after the next camera step. `need[176 bits]` = **22 B**, rebuilt at each cell step from the 21 x 19 visible cells (399 lookups, at most once per cell step, 8 px apart); a slot with its bit clear is free for eviction. (This replaces a per-slot count: the window moves one row or column at a time, so the bitmap is rebuilt from the visible cells, or incrementally by decrementing leaving and incrementing entering cells if the asm pass wants it.)
- **Eviction:** round-robin: the first free slot after a rotating pointer (1 B). No ages. A slot is never taken from a tile in the need bitmap.
- **Look-ahead:** after the needed tiles are queued, the lines beyond the view in the direction of travel (2 lines, 3 if there is slack) are loaded into free slots only, nearest line first, within the frame's byte budget. The first direction of a leg is known while Sal stands at a stop.
- **Hold rule:** the camera moves a step only when every tile of the next view is resident (loaded in an earlier VBlank). Otherwise it holds that frame. Sal keeps walking; the camera trails him (80 px of room horizontally, 72 vertically before he reaches the edge).
- **VBlank drain:** 86 B per frame (`VQ_DRAIN_BUDGET`): 16 B a tile plus 1 B per new map cell (DMG, no attributes).
- **Camera speed:** s = largest of 4, 3, 2, 1 with 86 x 8 / s >= pending bytes (pending = unloaded tiles x 16 + new cells).
- **Results (all 22 directed walks of the late world, trimmed DMG, look-ahead 2, round-robin):** moving frames held 1.5%, longest hold 2 frames, **max 85 B in a frame**, minimum free slots 18 along the walks (the worst window itself leaves 1).
- **Worst-case stream per camera step:** column step **227 B**, row step **309 B** (late world, trimmed DMG: the tiles the line needs that are not resident, 16 B each, plus map cells). At 86 B per frame: a column needs 3 frames, a row 4 frames, so with 8 px per cell step the speed caps above hold without a hold at 3 px a frame only when the look-ahead has run.
- **Scratch needed (DMG):** table 220 B + need bitmap 22 B + pointer 1 B + pending upload queue 19 x 3 B = 57 B + camera and stream variables 6 B = **306 B**.

## Scratch budget: `story_scratch` = 520 B (`src/scratch.h`)
Existing map layout (`smap.c`): 0 to 199 (panel rows, ATTR_PANEL, ATTR_TAG, TAGROW) and 400 to 411 (V). Free: region A 200 to 399 (200 B) and region B 412 to 519 (108 B) = **308 B**.
| Bytes | DMG use |
| --- | --- |
| A 200 to 399 | table bytes 0 to 199 (200 B) |
| B 412 to 431 | table bytes 200 to 219 (20 B) |
| B 432 to 453 | need bitmap, 22 B |
| B 454 | rotating pointer, 1 B |
| B 455 to 511 | pending upload queue, 19 x 3 B (slot, tile lo, tile hi) = 57 B |
| B 512 to 517 | camera and stream variables, 6 B |
| B 518 to 519 | spare 2 |
Used 306 of 308 B: tight, 2 B spare. The 10-bit packing is why it fits; unpacked u16 would not.

Color (static plan, unchanged from round 4): 904 tiles, greedy colouring over all states needs 216 to 228 slots (up to 8 tiles per slot), nibble table (the tile variant per slot) **114 B**, palette refcounts 16 B, `palslot[18]` 18 B, pending 57 B, tile staging 64 B, variables 17 B: fits the 308 B. A dynamic table for 352 slots (440 B at 10 bit) does not fit scratch, so Color keeps the static plan (worst window 203 of 352). Hybrid static plus overflow for DMG was tried (`hybrid.py`) and rejected: the static colouring of the trimmed set still needs 200 slots, and 176 home slots leaves 24 overflow tiles.

## Camera caps (`speedcaps.py dmg`, trimmed DMG; Color as round 4)
Worst column **227 B**, worst row **309 B** for DMG; Color column 278 B, row 346 B (Color has the extra attribute bytes). Percentages of lines per speed as in round 4 for Color; DMG lines are lighter than its round-4 full-art figures (259 / 325). Look-ahead lifts most lines to speed 4. Sal walks 3 px a frame; a camera held below that trails him.

## Stream data format
Banked ROM (2 banks, about 26 KB Color, about 22 KB DMG):
- `tile_data[N][16]` 2bpp tiles in first-use order; `state_end[11]` u16 (a state is a prefix). DMG N is the DMG world's distinct tiles over all states; Color N = 904.
- `cell_tile[48][64]` u16; `zone[48][64]` u8 and the fog table (fog tiles are rebuilt on entry as `world2.fog_tiles`).
- `cell_attr[48][64]` u8 (Color only). `pal_rgb[18][4]` (Color only).
- DMG: `hint[N]` u8 (the lookup hint). Color: `slot_of[N]` u8 and `var_of[N]` (static).
- Step: for each new cell: look the tile up, queue 16 B if missing, write the slot id to the 32 x 32 hardware map (wrapped), attribute to bank 1 (Color), palette refcounts. Tiles first, ids after.
- Map entry and every unlock: LCD off, load the window plus 4 columns / rows ahead and the 8 live palettes.

## Sprites (OBJ), exact ids (unchanged)
- Sal has no OBJ tiles of his own on the map: boot-time bartender tiles (`OBJ_BARTENDER` 0): picture p (0 idle, 1 walk1, 2 walk2) is tiles 8p to 8p+7; A = 8p, B = 8p+2, C = 8p+4, D = 8p+6 (8x16 pairs). A at (left, top), B (left+8, top), C (left, top+16), D (left+8, top+16); left = feet x - 8, top = feet y - 24; palette 0; no flip; front frames. Walk: step1, stand, step2, stand, a picture per 2 frames.
- Map sprites from OB = 56: ufo 56 58 60, dot_open 62, dot_locked 64, bang 66, arrow_right 68, arrow_up 70, arrow_down 72 (left = right flipped). 18 tiles. OBJ palettes: ufo 2, open dot 3, locked dot 4, arrow 6, bang 7. 11 objects on screen, 6 per line.

## Build pipeline expected
Inputs: `tools/v_*.py`, `decor.py`, `tiles.py`, `world2.py` (`WORLD`, `WORLD_DMG`, `MERGE`, `GROUND_OWNER`), `palsnap.py`, the palette table. Proposed generator: **new `tools/gen_smap_world.py`** (leave `gen_smap.py` for panels and tag):
1. Import the concept modules (or export `assets/map/world_{cgb,dmg}.txt` and `palettes.json` once the owner locks the art).
2. Build both worlds, dedupe tiles, number them in first-use order by unlock state, write `state_end`.
3. DMG: write `hint[]`. Color: colour the conflict graph (`slots.py`), write `slot_of`, `var_of`.
4. Emit `build/smap_world_{cgb,dmg}.c`; check at build time: window max tiles <= 176 (DMG, every state, all three window shapes) / 352, window palettes <= 8, scratch map <= 308 B free. A failed check stops the build.

## Self-audit
| Check | | Evidence |
| --- | --- | --- |
| Hand-placed | PASS | every DMG change is a typed grid or a typed position in `v_*.py` / `world2.py`; no merge table, no substitution by code |
| Clean-up pass by hand | PASS | reverted edits that broke shapes (butte slopes) or cost a tile (barrel, post); lettering, doors, windows untouched |
| 1x comparison with the bar | PASS | `sheet.png` at 1x; `dmg_trim_x4.png` full beside trimmed, viewed |
| References read | PASS | SKILL.md and its references, earlier rounds |
| Lint | PASS on DMG, FAIL on Color (cannot be cleared) | DMG world (`worldpng.py`, `--mode dmg --kind bg`): RESULT PASS, warnings: 111 isolated 2x2 squares, 133 L-shaped doubles, 1002 orphan pixels (a 512 x 384 world; judged by eye at x4, not individually). Color: "palettes needed (greedy estimate)" over 8 because the linter reads the world as one screen; no screen holds more than 8 (`palcheck.py`) |
| Colours per tile, palettes, tile count | PASS | DMG worst window 175 of 176; Color 203 of 352; palettes 8 per window |
| Scanline budget | PASS | 11 objects, 6 per line |
| Squint test | PASS | DMG maps and views at 1x on `sheet.png` |
| Tiled preview | PARTIAL | scripted renders, not engine tiling; 21 x 19 windows counted from the world grid |
| Animation | PASS | game's three front frames; gifcheck no strobing |
| Show art in the real engine | DEVIATION | previews are scripted |
| Files | PARTIAL | RGB / indexed PNGs; nothing for `assets/` yet |

## Doubts
1. DMG props and scenery shift by up to 8 px against the Color picture, and a few DMG props are removed (fence, hitching post, tumbleweeds, bistro table and shrub, stones, one pine). Owner to confirm they are acceptable.
2. The worst window leaves 1 free slot: look-ahead only happens in windows with slack, and the camera holds 2 to 3 frames where it does not (1.5% of moving frames). Levers if that feels bad: cap the camera lag, move one axis at a time, or trim 5 to 10 more tiles.
3. DMG scratch is 306 of 308 B (2 B spare); the CPU cost of the lookups (hint check, scan fallback, bitmap rebuild) is not simulated: an asm pass question.
4. Color keeps a static plan (216 to 228 slots), not a dynamic allocator, because the table for 352 slots does not fit scratch.
5. Previews are scripted, not an engine build.
6. Lint warnings on the DMG world (orphan pixels, 2x2 squares) were not individually reviewed.
