# Story map, direction A: one scrolling 256 x 256 map (concept, 2026-11-04)

Mockups only. Nothing under `src/`, `tests/`, `assets/` or the goldens changed. The pictures come from `tools/` (kit.py = my grids,
layout.py = where things go, render.py/build.py = previews). Scripts only cut, place, convert and preview.

## Files

| File | What |
| --- | --- |
| `sheet.png` | The one contact sheet (phone width): maps, four screens, the walk |
| `map_early_cgb_x2.png`, `map_early_dmg_x2.png` | Whole map, early: town, saloon and stadium revealed, the rest fog, a red dot for the next stop |
| `map_late_cgb_x2.png`, `map_late_dmg_x2.png` | Whole map, everything revealed, all dots green, the "!" over the tent |
| `view_*_x3.png` | 160x144 screens, Color over DMG: town (early), saloon (desert, with name tag), igloo (NE edge), lounge (SW corner, UFO), cow (E) |
| `walk_cgb.gif`, `walk_dmg.gif` | Sal walks town to saloon, about 3.8 s, 30 fps; the tag slides in and out |
| `master/` | The map as indexed PNGs (palette x 4 + colour, as `map_bg_only_indexed.png`), Color and DMG; my pieces; tiled previews |

## What it is

32 x 32 cells = the hardware BG map, scrolled with SCX/SCY only: no streaming. The square is in the middle (round 6's gable
houses, clock tower, market hall, bunting along the top, the v14 fountain and tent). Ten venues sit 10 to 12 cells out in their
own biomes, joined by 8 px roads: one loop through the stops in chapter order and two short spokes from the square.
Every fork is a stop (the saloon corner, the bistro, the Chrome Cow), so a D-pad press never has to choose a branch.

Camera: target = Sal centred, clamped to 0..96 / 0..112. Each frame `cam += gap >> 2`, at least 1 px, at most 4 px. Sal walks 3 px
a frame. Legs are 3 to 12 cells: 0.15 to 0.55 s. Arrows (gold) show only the exits that exist and are revealed.

## Budget

| Item | Number |
| --- | --- |
| BG tiles, whole map revealed (identical index tiles merged, no flips: gen_smap's rule) | **174** (the lint, which counts palette too, says 179) |
| What the map screen can use | 176 (ids 0-35 and 93-232; `FONT_END`, `DIM_BASE` in gen_smap.py). v14 used exactly 176. Left: 2 |
| Peak while fog is up | 171 (156 revealed + 15 fog). It is lower than the late map, so the peak is 174 |
| Fog tiles | 15 (13 not in the late map): plain, puff, edge x4, corner x4, inner corner x4. The edge, corner and inner corner are turns of one drawing each (a copy of my own tile; the DMG has no BG flips) |
| BG palettes | 8, as v14. The tag row uses 0, the panels 5: no new one. Any 20x18 view uses up to 8 |
| OBJ palettes | unchanged: Sal, UFO, open dot, locked dot, arrow, "!" (the same six sheets) |
| Sprites per line | worst 6 of 10, over every camera position and every stop (dots 1, Sal 2, UFO 3, arrows 1, "!" 1; 8x16 mode) |
| Objects in OAM | 20 of 40 (11 dots, Sal 2, UFO 3, "!" 1, up to 3 arrows) |
| Tiles in ROM | 174 x 16 = 2784 B, fog 208 B, tilemap 1024 B, CGB attributes 1024 B (512 B as nibbles), zone map 512 B as nibbles |
| WRAM | **0 new globals.** Camera x/y, leg and step: about 6 B in `story_scratch` (`V(n)` slots after V_PREV) |
| ROM0 | **0 B.** Scroll, walk and fog code goes in the smap bank (`#pragma bank 255`); my guess is 600 to 900 B of it |

How the tile count is kept under 176: the tiles are stored in the order of first use by chapter, so a revealed state is a prefix of the
array (one `set_bkg_data` call, or one per zone). The fog tiles take the top ids. Without that, the 174 plus 15 fog tiles is
189, over the 176. So the map screen must load only the tiles of revealed zones, at screen entry with the LCD off (it already
does that).

To get to 174 I dropped from v14: the stadium's ticket gate, the bistro's umbrella table, the ice chunks, the teahouse pond,
both lamp posts, a second tree, a second cactus, a second bush, the tall-grass tufts and the skull. If the owner wants any
back, something else of the same size has to go.

### Fog

- **Method.** A zone map (each cell belongs to its nearest stop; the square is its cobbled block). A zone that is not revealed has its cells
  drawn as cloud tiles instead of ground. The edge tile is chosen from the 4 neighbours (a table of 16 entries). It is tile data, so it
  works on the DMG as well as on Color: **it fits the DMG, it is not Color-only.**
- **Cost.** 15 tiles (240 B), the zone map (512 B as nibbles, or 44 B as rectangles) and about 150 B of code (a guess). It is done once at screen
  entry, LCD off: no VBlank cost. A dissolve when a venue unlocks would use the existing queue, 3 rows a frame.
- It needs no palette trick. Colour only adds the pale blue.

### Walk data

11 legs, 13 runs of (direction, cells) at 1 B each, 11 leg lengths and an exits table of 11 x 4 B: about 70 B. It lives in the smap
bank beside the stop table (`stop_x/stop_y`, `snap`). The same data walks the leg backwards.

| Leg | Runs |
| --- | --- |
| town-saloon | L10 |
| saloon-stadium | U11 |
| stadium-lodge | R8 U3 |
| lodge-bistro | R10 |
| bistro-igloo | R3 |
| bistro-factory | D4 |
| factory-cow | D10 |
| cow-town | L8 |
| cow-teahouse | D8 L4 |
| teahouse-zoo | L9 |
| zoo-lounge | L4 |

## Venue art: reused or redrawn

| Piece | Status |
| --- | --- |
| Saloon, stadium (without its gate), lodge, bistro, igloo, factory, Chrome Cow and its blue road, zoo, teahouse, mountain | **Reused** from v14, cut out whole and spaced out. The bistro is recoloured by palette (teal to the town's lilac): same pixels |
| Fountain, festival tent | **Reused** from v14 |
| Trees, bush, cactus, rocks, cow, plain snow and grass | **Reused** from v14 |
| The square: gable house, clock tower, market hall, bunting, cobble | **Redrawn** at map scale from round 6 (my grids in kit.py) |
| Roads (11 tiles), fog (6 drawings, 15 tiles), snow drift, fence | **New** |
| Air base: hangar and runway | **New**, desert olive, in palette 1 |
| Stadium's white yard | A flat tile of palette 6, to hold the stadium's white edge |
| Sal, UFO, dots, arrows, "!" | **Reused** sprites; the walk is one frame, flipped, with a 1 px bob |

Palette changes: BG 4 is now the town's (cream F8F0B0, terracotta F0B888, lilac A090B0, ink 201828) in place of the teal;
BG 5's first colour is F8F0B0 so the fountain sits on the cobble without a seam. This also moves the cream of the START and
festival panels slightly.

## Doubts

1. **Tile budget** is 174 of 176. It only works with per-zone tile loading. I read the pool from `gen_smap.py` and did not build it.
2. **Fog edges are straight and rectilinear**, with a 1 px outline and a few puffs. A round cloud edge needs an outside colour per
   biome, and a tile has one palette. A rounder bank needs more tiles.
3. **Red dots against fog.** The owner's rule is green open, red locked, but locked places are now hidden. I show the next stop as a
   red dot on the cloud's edge (early map, town view). Keep it, or no red at all?
4. **Bistro is lilac now** because the town needed a palette and all 8 are used. Alternative: keep teal and give the town the teal.
5. **The square has no awning or tavern**, and only 4 buildings. Lamp posts are cut for tiles.
6. **DMG ghosting.** Roads have 1 px dark edges and the whole map scrolls at up to 3-4 px a frame (skill: "avoid 1-px dark detail ...
   on anything that moves"). The edges are shade 2 and run along the roads; cap the camera at 2 px a frame if the owner sees smear.
7. **Real engine:** none. Nothing here was built in a scratch ROM, because the brief forbids engine code. The previews follow the
   gen_smap conventions (DMG shades F8/A8/58/18, OBP0 = D0, CGB palettes without colour correction).
8. **Sound** is not in the GIF. The brief's blip on arrival is a game change.
9. **Zones** are nearest-stop cells, so unlock borders are staircases. They are mine to tune; the engine needs the zone map.
10. At 1x the air base has no control tower (it cost 2 tiles). The UFO bobs 1 px every 24 frames.

## Questions for the programmer

1. Does anything else use BG ids 242-247 and 252-255 on the map screen? If they are free, there are up to 10 spare tiles (assumed: no).
2. Can the loader fill the tile ids per revealed zone at screen entry (assumed: yes, LCD off)?
3. Can the camera and the window tag run together: the tag is on the window, `WY` 0 to -8 slide (assumed: yes, as the current tag)?
4. Is the tilemap at 0x9800 and the window at 0x9C00 (assumed: yes)?

## Self-audit

References read before drawing: SKILL.md, environments.md, hardware.md, linework.md, light-and-form.md, palettes.md; figures 06,
10, 16 (and the owner's round-6 notes). Rules I used: "Neighbouring terrain types differ in texture and shape, not only colour"
(environments.md: roads have edges and pebbles, grass has none); "Duplicate shared colours on purpose ... idx0 is the SAME blue"
(palettes.md: town cream matched); "Keep scrolling backgrounds light" (hardware.md section 9); "Count objects per row" (stats.py).

| Check | Result | Evidence |
| --- | --- | --- |
| Hand-placed: what wrote the pixels | PASS | My grids typed in `tools/kit.py`, the v14 picture's cells, and `layout.py` placing them. Scripts only cut, place, rotate my own fog tiles by quarter turns, preview. No outline, shading or fill generation (the flat white yard and plain fog tiles are flat fills of one colour) |
| Clean-up pass by hand | PASS | Fog: waves read as ocean wallpaper, redrawn as plain white and a few puffs; haze specks outside the cloud edge removed (noise); hangar from white and red to desert olive (the white clashed with the sand); corner pixels at road bends; the cobble to one variant for tiles; the stadium gate dropped for budget |
| 1x comparison with the quality bar | PASS | v14 map (the owner's approved) beside it at 1x on the sheet; the square matches its weight. The roads are lighter than v14's dotted ring |
| References read | PASS | listed above |
| Lint | PASS (hardware/format) | `master/map_late_indexed.png`: 179 tiles, palettes 8 of 8, 17 squares, 74 L-doubles, 116 orphans (mostly the v14 art); my pieces sheet: 6 L-doubles (the hangar and house roof diagonals), 19 orphans (pebbles, brick hints), not removed one by one |
| Colours per tile, palettes, tiles | PASS | each cell one palette; 174 tiles; 8 palettes |
| Scanline budget | PASS | 6 of 10 |
| Squint test, DMG and Color | PASS | the square and the fog read first, roads second; on the DMG roads are the only mid-grey lines |
| Banding, squares, strays | PARTIAL | see the lint; the road pebbles are 2-px dashes; 2x2 squares remain in v14 pieces |
| Light direction | PASS | top left in the houses (lit left roof edge, left highlight) |
| Tiles: tiled preview | PASS | `master/tiled/tiled_all.png`: road, cobble, fog, fence, runway, bunting repeat cleanly. The puff repeats as wallpaper if tiled, so it is placed by hand |
| Animation | PASS | one sprite frame flipped and bobbed 1 px; no wind-up; GIFs: biggest frame-to-frame brightness change 3.9 of 255, scroll at most 3 px a frame, no flashing |
| Footprint kept | PARTIAL | the map is 256x256, not one screen: that is the brief. The 11 stops and chapter order are kept |
| Files indexed, ordered, aligned | PASS | idx 0 lightest to 3 darkest in every palette |
| Engine questions | PASS | above |

Deviation from the skill: "Show art in the real engine (scratch builds)" is the owner's standing rule; this concept is not run in a ROM.
