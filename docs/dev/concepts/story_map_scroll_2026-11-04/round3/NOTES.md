# Story map, round 3 (concept art, ready for the engine build)

Owner: "The walk looks decent, but let's just always have him face the camera. No side view." Q78 (the scrolling map at its cost): yes.
Nothing is in `src/`, `tests/`, `assets/` or the goldens. Previews are scripted (`tools/`), not an engine build (declared deviation).

## Files
- `sheet.png` phone sheet. `vignettes_x4.png` the three vignettes that changed (round 2 | round 3 Color | round 3 DMG).
- `walk_cgb.gif`, `walk_dmg.gif` Stadium to Saloon, 3.3 s, front-facing; `walk_strip.png` six frames of it.
- `map_{early,late}_{cgb,dmg}_x2.png`, `view_*_x3.png`, `tiled_preview.png` (skill's tiled_preview.py on every ground patch).
- `tools/` sources. Checks: `palcheck.py` (every window, every unlock state), `palmap.py`, `palareas.py`, `stats2.py`, `stats3.py`, `trim.py`, `slots.py`, `speedcaps.py`, `stats4.py`.

## What changed since round 2
1. **Sal** always faces the camera: the game's own idle / walk1 / walk2 (assets/art/bartender.txt), no flip, no new art. The side and back poses are deleted.
2. **The Chrome Cow** is the biker bar: purple-black studded wall, chrome parapet, pink neon sign of a cow in sunglasses with horns, MILK neon window, studded door, checker lip, two motorcycles parked out front, the cow field and fence kept on the left. Palette is the game's stage palette COW (wall 2a1e34, chrome e8e0f0, neon pink f03898, meadow c8e888). No pink milk shop.
3. **Saloon sign** reads TAPS (the sign the game shows over the Saloon's bar: src/po.c "the TAPS sign"). The name tag still says THE SALOON, as in the story table.
4. **Palettes:** every 21 x 19 window needs 8 BG palettes or fewer in every unlock state (below).
5. Town: the fountain spray (palette TOWN4, water and lilac) now uses TOWN1, so it reads peach, not pale blue. This is the one visible change to the approved town and it is what the 8-palette limit cost. Doubt 1.

## Palette check (`palcheck.py`)
Over every one of the 41 x 30 window positions, for the town alone and for 1 to 10 venues open in story order (11 states): **worst window 8 palettes**, at cell (31,5); windows over 8: 0 in every state. Per state: 4, 6, 7, 7, 8, 8, 8, 8, 8, 8, 8.
How: roads use TOWN1; factory orange, zoo gate wood, cherry pink, town orange and town water folded into their venue or town palette; 11 stray ground cells moved to the palette of their neighbour (`palsnap.py`: (49,23..29) farm to cow, (49,8),(49,9),(50,6),(51,11) snow to plaza, (49,23) cow to grass; one cell is a shade off); each biome's ground opens with its own venue (the desert south of row 31 with the space lounge); the cloud edge shows its ground in one of 3 colours (`fog:grass`, `fog:saloon`, `fog:fogbase`), and interior cloud tiles (no ground pixel) take the commonest of those.
Slots: a fixed slot per palette works for states 0 to 6 only (colouring finds 8 slots), not for 7 to 10 (`palmap.py`). So the engine allocates slots as columns stream in: **slot refcounts** (8 x u16 = 16 B), a palette takes a free slot when its first cell enters (8 B write in VBlank) and frees it at zero cells. A window never needs more than 8, so one is always free.

## Palette map per area (late world; cells per area; colours then RGB555 words)
| Area | Palettes (cells) |
| --- | --- |
| town | town1 363, town5 32 |
| saloon | saloon 260, town1 45 |
| stadium | stadium 204, town1 39 |
| lodge | grass 207, lodge 56, town1 36 |
| bistro | bistro 164, town1 30 |
| igloo | igloo 271, town1 40, grass 4 |
| factory | factory 78, town1 28, grass 1 |
| cow | farm 325, cow 75, town1 53, grass 11 |
| tea | tea 260, town1 55, grass 12 |
| zoo | zoo 173, town1 32, saloon 28, grass 1 |
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
| town5 | f8f0b0 f0b888 e8a828 201828 | 5bdf 46fe 16bd 1464 |
| zoo | d8f0a0 58b048 186830 082818 | 53db 26cb 19a3 0ca1 |
| fog:grass | b0d080 f8f8f8 d8e0f0 b0b8d8 | 4356 7fff 7b9b 6ef6 |
| fog:saloon | f8e090 f8f8f8 d8e0f0 b0b8d8 | 4b9f 7fff 7b9b 6ef6 |
| fog:fogbase | f8f8f8 f8f8f8 d8e0f0 b0b8d8 | 7fff 7fff 7b9b 6ef6 |

(The values are the preview's, channels as typed; the programmer should take the game's own RGB555 words for palettes it already has: cow = `assets/approved/venues/biker_pal.json` stage_a/stage_b.) DMG: one BGP, shades 0 to 3 by index; fog is shade 1 (cloud) over grey.

## Tile plan (c): final
- **Tile set:** 913 unique 8x8 tiles (Color), stored in first-use order by unlock state, so a state is a prefix. Whole world 64 x 48 cells.
- **Pool:** map screen BG pool is 176 (ids 0-35 and 93-232 in bank 0). Color adds the same 176 ids in VRAM bank 1 (attribute bit 3): **352 slots**.
- **Slot plan (static, computed offline):** a tile gets one slot; two tiles share a slot only if no 21 x 19 window holds both (greedy colouring over the conflict graph, `slots.py`). Full detail needs **225 slots**: fits Color (352), not DMG (176). Mean 4.1 and max **7** tiles per slot.
- **Resident table (WRAM, `story_scratch`):** one nibble per slot (the index 0 to 6 of the tile now in it, 15 = empty): Color 225 nibbles = **113 B**. No new globals, no ROM0 code (code goes in smap.c, bank 255).
- **Per-area tiles** (tiles, of them only in that area): town 105/94, saloon 104/90, stadium 60/48, lodge 126/120, bistro 54/50, igloo 129/118, factory 65/55, cow 100/86, tea 76/59, zoo 92/83, space 87/75. Worst 21 x 19 window 203 (cell 3,23); 23% of windows are over 170. With the town only: 127 tiles, window 115. Peak per state: 172 (3 open), 174 (5), 197 (8), 203 (10).
- **Color:** all of it, nothing trimmed; the look-ahead (below) runs 4 columns / rows ahead using the slots a window does not need.
- **DMG:** 176 slots, so the art must shrink. Trim list, in order, with the effect on the worst window (203): (1) ground variants to the flat tile, -8 (195); (2) scenery (trees, rocks, hay, mounds, bushes) to nothing or to 1 shared piece per biome, -11 (184); (3) cloud billow tiles FA-FD to one, -3 in the early states; (4) venue-only tiles shrink **8%** for a 170 target or **22%** for 146 (area-only counts after 1 and 2: town 93, lodge 69, space 69, tea 59, saloon 58, factory 55, igloo 52, zoo 50, cow 49, bistro 49, stadium 48; 8% is 4 to 7 tiles each, 22% is 11 to 20). **Open: whether the name-tag font (about 30 tiles) comes out of the 176**; if it does the target is 146 and step 4 is 22%. The trimmed DMG art is not drawn yet (it needs the owner's pick of what DMG loses).

## Stream data format (proposal)
All in banked ROM (2 banks, about 26 KB: tiles 14.6 KB, cell tile ids u16 6 KB, cell slot-and-attribute 3 KB + 3 KB, Sal 0, headers):
- `tile_data[913][16]` 2bpp tiles in first-use order; `state_end[11]` u16: tiles needed per unlock state.
- `cell_tile[48][64]` u16 tile index; `cell_attr[48][64]` u8: palette name index (0 to 16, see the table), bank bit, no flips (DMG cannot flip).
- `slot_of[913]` u8 slot (0-175 bank 0, 176-224 bank 1) and `var_of[913]` u8 0 to 6.
- `pal_rgb[17][4]` u16.
- Fog: tiles come from the same set (12 fog tiles); a cell's fogged tile is computed by the map builder per state (`cell_tile` is per state: 11 states x 6 KB is too big, so store the late map plus a **zone id u8 per cell** (3 KB) and a fog tile table of 8 u8 per cell class; fog cells are rebuilt on entry from the zone ids, as `world2.fog_tiles` does; edge sequence is a fixed 12-entry table `B0 B1 S B0 B1 S S B0 B1 B0 B1 S`).
- Column step (camera crosses a cell boundary): for each of the 19 cells of the new column (21 for a row): `if resident[slot] != var -> queue 16 bytes to slot`, write slot id to the map (32 x 32 hardware map, wrapped), attribute to bank 1 of the map (Color), palette via slot refcounts. Tiles first, ids after, so a cell never shows a wrong tile.
- Entry to the map screen and each unlock: LCD off, load the visible window plus 4 columns / rows ahead, all 8 palettes.

## Camera caps (`speedcaps.py`, late world)
Drain is 86 B/frame (`VQ_DRAIN_BUDGET`). Cost of a line = 16 x new tiles + ids (+ attributes on Color). A line is crossed in 8/s frames at s px a frame. Rule: **s = the largest of 4, 3, 2, 1 with 86 x 8 / s >= pending bytes.**
| | worst line | speed 4 | speed 3 | speed 2 | speed 1 |
| --- | --- | --- | --- | --- | --- |
| Color column | 278 B | 72% | 22% | 6% | 0 |
| Color row | 346 B | 55% | 21% | 23% | under 1% |
| DMG column (untrimmed ids only) | 259 B | 82% | 17% | 1% | 0 |
| DMG row | 325 B | 62% | 26% | 12% | 0 |
Look-ahead on Color lifts most of these to 4. Sal walks 3 px a frame; if the camera is held below that it trails him (the window has 80 px of room), and past 32 px behind Sal waits. The round-2 follow rule stays (`gap >> 2`, minimum 1, maximum as above).

## Sprites (OBJ), exact ids
- **Sal: no OBJ tiles of his own on the map.** He uses the boot-time bartender tiles: picture p (0 idle, 1 walk1, 2 walk2) has tiles 8p to 8p+7, entries A = 8p, B = 8p+2, C = 8p+4, D = 8p+6 (the 8x16 pairs, as `draw_bartender`): idle 0 2 4 6, walk1 8 10 12 14, walk2 16 18 20 22. A at (left, top), B at (left+8, top), C at (left, top+16), D at (left+8, top+16); left = feet x - 8, top = feet y - 24; OBJ palette 0 (OBJPAL_BARTENDER: f8f8f0, f0b888, 202030); no flip. Walk cycle: step1, stand, step2, stand, one picture per 2 game frames while walking (as the GIF), stand when still. He faces the camera for every direction.
- **Map sprites from OB = 56** (smap.c `OB`), pairs in this order: ufo 56 58 60 (24 x 16, three columns), dot_open 62, dot_locked 64, bang 66, arrow_right 68, arrow_up 70, arrow_down 72 (arrow_left = arrow_right with x-flip). 18 tiles (round 1 had 22: the map's own 16 x 16 Sal, ids 56 to 59 with OBJ palette 1, is dropped; palette 1 is free). OBJ palettes: ufo 2, open dot 3, locked dot 4, arrow 6, bang 7, as now.
- **Budget:** at most 11 objects on screen and 6 on one scanline (Sal 4, arrows up to 3, dots up to 4, UFO 3) against 40 and 10 (`stats4.py`).

## Self-audit
| Check | | Evidence |
| --- | --- | --- |
| Hand-placed | PASS | typed grids (`v_*.py`, `tiles.py`, `salsrc` reads the game's file); the cow head is typed as spans per row; scripts only compose, snap cell palettes, render and count |
| Clean-up pass by hand | PASS | cow bar: bikes first sat on the dark wall and vanished, wall shortened and the bikes put on the light forecourt; bike fork and headlamp retyped; MILK window and door rows recounted |
| 1x comparison with the bar | PASS | cow, TAPS and town set beside round 2 at x4 (`vignettes_x4.png`) and at 1x on the sheet |
| References read | PASS | SKILL.md, environments.md ("neighbouring terrain types differ in texture and shape"), linework.md, light-and-form.md, palettes.md, hardware.md |
| Lint | FAIL (cannot be cleared) | DMG PASS. Color: "palettes needed (greedy estimate): 14 of 8": the linter takes the 512 x 384 world as one screen; no screen holds more than 8 (`palcheck.py`: worst 8 over 11 states x 1230 windows) and the engine swaps palette slots as it scrolls. Other warnings: 113 2x2 blocks, 6 L-doubles, 1078 orphans (tufts, studs, stars are deliberate; not each checked), RGB PNG (previews, not assets) |
| Colours per tile, palettes, tile count | PARTIAL | 913 tiles; window 203 vs pool 176 (Color has 352; DMG needs the trim above); palettes 8 per window |
| Scanline budget | PASS | 11 objects, 6 per line |
| Squint test | PASS | maps and screens at 1x and x3, Color and DMG; DMG MILK neon (shade 2 on shade 3) is faint, the cow head and the chrome rim carry the sign |
| Banding, squares, L-doubles | PARTIAL | lint warnings above, eyeballed on the maps |
| Light direction, flips | PASS | no flips now |
| Tiled preview | PASS with a note | run on 10 ground patches, road and cloud (`tiled_preview.png`): grass, desert, snow, farm, jungle, moss, plaza, yard read quiet with no seams; the dense forest floor repeats in vertical bands when the 4 x 4 patch is tiled (in the world the variants follow a 13-cell hash and do not band) |
| Animation | PASS | the game's three front frames, unchanged tiles shared (head objects A and B are identical in all three) |
| Footprint | PASS | Sal 16 x 24 as in game |
| Files | PARTIAL | previews are RGB PNGs; nothing for `assets/` yet |
| Engine questions | PASS | below |

## Doubts and questions for the programmer
1. Fountain spray is peach (was pale blue). Keeping the blue costs a 9th and 10th palette in 65 to 100 windows. Owner call: accept peach, or give the fountain a recolour inside TOWN1 or TOWN5.
2. Does the name-tag font come out of the 176 BG tiles? It decides the DMG target (170 or 146). Working assumption: yes, 146.
3. The DMG art is not drawn. Step 4 of the trim list needs a pick of what the DMG loses.
4. Palette slots must be allocated while scrolling (refcounts); a fixed table fails from 7 venues open. Working assumption: 16 B of `story_scratch`.
5. The 113 B resident table and the 16 B of refcounts share `story_scratch` with the panels and the tag: not checked against `src/scratch.h`.
6. The early-state cloud is flat in Color (off-white, faint billows); judged acceptable.
7. The cow bar's DMG neon is faint, see the squint row. Palette cell snap moved 11 ground cells; one (49,23) is a shade off its neighbours.
8. Sal covers the cows and the fence at the cow stop; he never covers a name or door.
9. Skill deviation, quoting it: "A check you skipped is a FAIL, not a note." The lint row stays FAIL for the reason above; nothing else was skipped.
