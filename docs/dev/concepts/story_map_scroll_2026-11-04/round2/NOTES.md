# Story map, direction A, round 2 (mockups only)

Owner: "Sal's full-size sprite moving around the map" and "redoing the art since we have so much more space to add details for the locations."
Nothing is in `src/`, `tests/`, `assets/` or the goldens. Previews are scripted (`tools/`), not an engine build (declared deviation, as in round 1).

## Files
- `sheet.png` phone sheet: both maps, five screens (Color over DMG, x3).
- `map_{early,late}_{cgb,dmg}_x2.png` full maps. `view_*_x3.png` screens. `walk_cgb.gif`, `walk_dmg.gif` (Stadium to Saloon, 3.5 s, name tag at the end).
- `vignettes_x4.png` the 11 pictures: round 1 | round 2 Color | round 2 DMG. `vignettes/` the strips.
- `tools/` all sources: `v_*.py` hand-typed vignettes, `tiles.py` ground/road/fog tiles, `decor.py`, `salwalk.py` (Sal), `world2.py` (layout), `render2.py`/`build2.py` previews, `stats*.py`, `slots.py`.

## What changed
- World 64 x 48 cells (512 x 384 px), camera 160 x 144. Roads 16 px wide. Each biome its own ground (grass, desert, snow, farm, forest, paved, plaza, yard, moss). South-west spread out.
- Sal is the in-game 16 x 24 sprite, his OBJ colours. Down poses are the game's own three frames. **New art, needs approval:** right-facing side (stand, two steps; left is the hardware x-flip) and back (stand, two steps). Side step 2 is weak (legs together). The back is a dark silhouette with collar and belt.
- Fog is a puffy off-white cloud with a soft shade and a scalloped edge (lens tiles), grey on DMG. Green open dots and red locked dot at the cloud edge kept.
- 11 vignettes redrawn bigger from each venue's in-game look and palette. The town is the approved round-6 town, unchanged except: sky replaced by cream, Sal and Dregs removed, cobbles retyped for the lower rows.

## Counts (late state unless stated)
| | Result |
| --- | --- |
| Unique BG tiles, whole world | 916 (127 with only the town open, 389 with 3 venues, 777 with 8) |
| Per area (tiles / only there) | town 105/94, saloon 90/77, stadium 79/61, lodge 120/110, bistro 65/55, igloo 145/128, factory 65/55, cow 93/72, tea 88/61, zoo 88/77, space 87/75 |
| Per 21 x 19 window, worst | 203 (at cell 3,23); 23% of windows are over 170. Map pool is 176 |
| BG palettes per window | worst 10 late, 13 mid-game (fog edges). Hardware gives 8. **Not solved**, see doubts |
| Sprites | 11 objects on screen at worst, 6 on one line (limits 40 and 10), with arrows, dots and UFO |
| Sal OBJ tiles | 9 frames x 8 = 72 tiles in ROM; one direction (24) or one frame (8) resident, free OBJ ids 40..55 = 16 |

## Tile strategy (three options)
Binding fact: the worst window needs 203 tiles and a fixed tile-to-slot plan needs 221 slots (greedy, `slots.py`). Ground variants plus scenery collapsed still need 188 per window. So no option fits DMG without trimming art.
Streaming facts at 4 px a frame (a new column every 2 frames): worst new tiles 15 per column, 19 per row; mean 6.3. Column step worst 278 B (15 x 16 + 19 ids + 19 attributes), row step 346 B. Per frame: worst 173 B, mean 70 B. The queue drains 86 B a frame (`VQ_DRAIN_BUDGET`).

| | (a) Stream both modes | (b) Bank 1 on Color, simpler DMG | (c) Mix |
| --- | --- | --- | --- |
| Tiles per window | 176 slots, window up to 203: does not fit | Color 352 slots, fits with room to look ahead; DMG 176 | same as (b) |
| VBlank B/frame worst | 173 (mean 70) vs 86: camera must drop to 2 px a frame in dense spots | Color: look-ahead spreads it, mean 70 fits; DMG as (a) | Color mean 70, DMG capped |
| DMG / Color | both identical art | Color only gets full art; DMG redrawn simpler | one data set, DMG loses less |
| ROM (banked) | tiles 14.7 KB + maps 3 to 6 KB + attrs 3 KB + Sal 1.2 KB = about 25 KB, 2 banks | + a second DMG tile set about 8 KB | as (a) plus about 2 KB trim data |
| WRAM | slot table about 176 B of `story_scratch` (shared with the panels) | same | same |
| ROM0 | none (code in bank 255 `smap.c`) | none | none |

What DMG loses in (b) and (c) (to get from 203 to about 170 at the worst windows): ground variants (8 tiles), scenery variety (about 15), fog billow detail, and about 10 to 15 tiles of detail in the heaviest vignettes (igloo, lodge, town, cow).
**Recommend (c):** one streamed data set with a fixed slot plan (no allocator), Color uses bank 1 as look-ahead so it scrolls at full speed, DMG gets the trim above and a 2 px camera cap in the tile-dense windows.

## Doubts (owner or supervisor to decide)
1. Palettes: whole-world 15; worst window 10 late and 13 mid-game, limit 8. Done so far: roads use TOWN1 (cream, skin, lilac), factory orange, zoo gate wood, cherry pink and town orange folded away (the factory sign and bolt are grey now, the zoo gate green, the blossom tree brown). 118 late windows still hold 9 or 10, mostly 1 to 3 stray cells at biome borders. Needs a cell-palette snap and 1-cell biome nudges; fog edges need fewer palettes. A scanline palette swap is not possible (about 4 B per HBlank).
2. New Sal poses are mine. The saloon sign says SALOON, the game says TAPS.
3. Town sky is flat cream. Giraffe and palms skipped. Biome borders are boxy under the roads.
4. Sal covers cows and the fence at the Chrome Cow stop; he never covers a name or a door.
5. Fog is flat in Color (off-white, faint billows); judged acceptable, not great.
6. DMG grounds are all white (texture only).

## Self-audit
| Check | | Evidence |
| --- | --- | --- |
| Hand-placed | PASS | typed grids in `tools/v_*.py`, `tiles.py`, `salwalk.py`; scripts only compose, recolour by palette and render |
| Clean-up pass by hand | PASS | stray rows and palette conflicts fixed by hand during drawing (cell conflicts, overwritten rows); no log kept |
| 1x comparison with the bar | PASS | compared with the igloo and the round-6 town at 1x and x3 |
| References read | PASS | SKILL.md and its figures read before round 1 |
| Lint | FAIL | late CGB: 946 tiles, 15 palettes of 8 (ERROR); DMG PASS. Warnings: 113 2x2 blocks, 6 L-doubles (Color), 1071 orphans in a 512 x 384 map; not each checked |
| Colours per tile, palettes, tile count | FAIL | 916 tiles over a 176 pool; palettes as above |
| Scanline budget | PASS | 11 objects, 6 per line |
| Squint test | PASS | viewed Color and DMG at 1x and x3 |
| Banding, squares, L-doubles | PARTIAL | see lint; eyeballed |
| Light direction, flips | PASS | Sal's left is a flip of the right pose; his lighting is the game's |
| Tiled preview | FAIL | not run |
| Animation | PARTIAL | step cycle step1, stand, step2, stand; side and back poses need the owner |
| Footprint | PASS | 16 x 24 as in game |
| Files | PARTIAL | previews are RGB PNGs, nothing for `assets/` yet |
| Engine questions | PASS | listed above |

Deviation from the skill: "A check you skipped is a FAIL, not a note." Tiled preview was skipped (FAIL above).
