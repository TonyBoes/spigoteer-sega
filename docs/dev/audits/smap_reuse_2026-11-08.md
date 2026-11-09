# Story map: what reusing shapes and swapping palettes could gain (2026-11-08)

Analysis only. Script: `tools/artifacts/map_atlas/reuse.py` (rerun `python3 tools/artifacts/map_atlas/reuse.py --sheet`, about 4 minutes; writes `out/reuse.json` and `out/reuse_sheet.png`).
Map analysed: main plus the pending town-move and desert-peaks import (64 x 70 cells), the finished state (11).

Method: every opportunity is simulated. A copy of the world's pixel arrays is edited, the generator's own `Model` is rebuilt, and ids, tiles, 21x19 windows, the padded path windows
(`path_windows`) and Color palettes per window are re-measured. Savings below are measured, not estimated. Color ids are counted the way the build counts them (all states, after the mirror merge).

Baseline: Color 908 ids, DMG 955 tiles. Worst DMG padded path windows 174 (top right, cells 41-63 x 1-20, and 43-63 x 1-21), then 173. Worst 21x19 DMG window 176 (cells 4-24 x 23-41, the saloon / space-lounge / desert peaks block).
397 of 2288 Color 21x19 windows hold 8 palettes. Single-use tiles (finished state): DMG 682 of 948, Color 630 of 901.

## The short answer

The map already reuses almost everything that is "the same shape in another colour": pines, round trees, bushes, spruces, rocks, peaks (snow and desert are the same tiles), cacti pieces
and the three ground textures (flat, sprout, ripple) are already one set of tiles shared across palettes. Reordering palette colours buys 3 Color ids and nothing on DMG.
The single-use tiles are the venue pictures (about 570 of the 948 DMG tiles), the mountain ranges and mesa ("other scenery", 217), the roads (99) and the river edge (39). They are drawn once because they are different pictures.

What is left is (a) redrawing near twins (tiles 1 to 4 pixels apart), which is where the real numbers are and the only thing that moves the tight windows, (b) snapping trees to one pixel offset, and (c) palette merges, which free palette slots but no tiles.

## Ranked table

Columns: DMG = DMG tiles saved, Color = Color ids saved; tight = effect on the worst DMG windows (padded path max 174, 21x19 max 176) and on 8-palette windows (8/8, 397 now).

| # | Opportunity | DMG | Color | Tight windows | Visual cost | Effort |
|---|---|---|---|---|---|---|
| 1 | Redraw near twins, all places, up to 4 px | 147 | 161 | path 174 to 156, 21x19 176 to 157 | 386 DMG cells / 1187 px and 2114 Color cells / 6202 px change (Color count is mostly 1 px on road cells); every cell keeps its look except a few pixels | high: per-tile hand pass; 148 DMG redraws |
| 1a | ...up to 2 px only | 45 | 69 | path 167, 21x19 167 | 107 DMG cells / 157 px; Color 1792 cells / 3459 px | medium |
| 1b | ...up to 1 px only | 23 | 36 | path 172, 21x19 172 | 59 DMG cells, 1 px each | low |
| 2 | Near twins inside the venue pictures (<= 4 px) | 53 | 80 | path 172, 21x19 176 to 168 | 71 DMG cells / 225 px, 114 Color cells: small drawing details inside buildings | medium |
| 3 | River edge twins (<= 4 px) | 13 | 4 | path 174 to 170 (the top-right worst window holds 25 water tiles) | 55 DMG cells / 194 px: the water's edge shape gets a little less varied | low-medium |
| 4 | Mountain range and mesa twins (<= 4 px) ("other scenery") | 14 | 17 | path 170, 21x19 174 | 32 DMG cells / 98 px | medium |
| 5 | Road twins (<= 4 px) | 16 | 14 | path 172 | 39 DMG cells / 142 px; Color 129 cells (road speckle) | low |
| 6 | Fold stray-pixel tiles into the flat ground tile (<= 2 px) | 16 | 10 | 21x19 176 to 172, path unchanged | 32 DMG cells lose a dot: mostly the dots that round the road bends and cut tree tips at the map edge | low |
| 7 | Snap round trees to one pixel offset (4 offsets today, 17 trees) | 20 | 20 | none | 16 trees move up to 4 px | low |
| 8 | Snap pines to one offset (6 offsets, 29 pines) | 8 | 19 | none | 4 to 6 pines move up to 4 px | low |
| 9 | Pines and round trees together (7 + 8, measured together) | 28 | 39 | none | as above | low |
| 10 | Everything realistic at once: 9 + 1a | 72 | 106 | path 167, 21x19 167 | as 1a and 9 | medium |
| 11 | Palette merge cactus into grass | 0 | 0 | 8/8 windows 397 to 240 | cactus cells show the grass greens on sand; colour distance 26 of 765 per colour (very close; see sheet panel 5) | trivial |
| 12 | Merge town4 and town5 into town1 | 0 | 0 | 8/8 397 to 260 | colour distance 48 and 58: the two small town awnings take the town palette's colours | low |
| 13 | Merge bistro@g into bistro | 0 | 0 | 8/8 397 to 281 | distance 44: 11 cells of plaza ground colour | low |
| 14 | Merge town1@z and town1@n into town1 | 0 | 0 | 8/8 397 to 394 | distance 12 and 24: almost identical colours | trivial, but saves almost nothing |
| 15 | All six small palettes merged (11 + 12 + 13 + 14) | 0 | 0 | 8/8 397 to 82 | the sum of the above | low |
| 16 | Merge factory into grass | 0 | 0 | clears all 82 east-wedge windows | the factory yard turns green (sheet panel 6); distance 54 | low, but visible |
| 17 | Reorder cow, tea@g, water palette colours (relabel) | 0 | 3 | none | none (the pixel indices change, the picture does not) | low; town1 cannot be reordered |
| 18 | Redraw the snow spruce as the pine | -6 | 0 | path 174 to 180 (worse) | spruce becomes a bigger pine | do not |
| 19 | Peaks, rocks, bushes, cacti, ground textures | 0 | 0 | none | already one shape per family | nothing to do |

## What each measurement says

**1. Exact reuse by relabelling.** Colour indices are already consistent across palettes (index 0 the ground, 3 the ink, as `tools/smap_world/pal.py` documents), so a permutation per palette
finds almost nothing: the best of 12 random-restart coordinate descents over 24 permutations per palette gives Color 908 to 905 (cow 0,2,1,3; tea@g 0,1,3,2; water 2,3,0,1). `town1` is held fixed
because the window and overlay text is drawn with its slot (`src/smap.c ui_attr`), so its colour order cannot change. Index 0 is the shared ground everywhere except water (2), which is why water reorders.
Ceiling if every block could take its own palette order (not possible, a palette is per cell): Color 1002 distinct blocks fall to 856 shape classes (colour order and flips ignored). On DMG a relabel is a shade change:
948 blocks fall to 929 classes with any shade permutation, 936 keeping shade 0, 943 swapping only two shades. So DMG gains at most 19 tiles and they would look different. Not worth it.

**2. Near reuse.** Number of tiles one redraw pass could drop (greedy stars, no chains), upper bound: DMG, same shades: 23 / 45 / 84 / 146 at 1 / 2 / 3 / 4 px. Color, same colours with flips: 54 / 103 / 146 / 218.
Color with colour order free (needs palette reordering): 83 / 140 / 181 / 254. DMG with shades free: 33 / 67 / 117 / 171. The table rows 1 to 6 are the simulated version (blocks actually replaced, the Models rebuilt), which is lower
because a tile can be a star member only once. Where the savings are (DMG, 4 px): stars centred on a ground tile 44 (the flat tile absorbing stray-pixel fringes, row 6), other scenery 22, venue pictures 53 (Stadium 13, Space 9, Tea 7, Bistro 5, Igloo 5), road 16, water 13.
Tiles inside a venue picture are the most numerous but each saving changes about 1.3 cells, so the visual cost per tile is small but the work is spread over 11 pictures.

**3. Repeated objects** (cell boxes and phase counts are in `out/reuse.json`, key `families`; matched by pixel template, Color and DMG alike):

| Family | Copies | Pixel offsets (x,y mod 8) | Palettes | Same shape? | Tiles now (Color/DMG) | One offset saves |
|---|---|---|---|---|---|---|
| Pine 16x18 | 29 | 6 | grass | one drawing | 39 / 23 | Color 19, DMG 8 |
| Round tree 16x19 | 17 | 4 | grass, tea@g, zoo | one drawing (jungle tree = round tree) | 32 / 32 | Color 20, DMG 20 |
| Bush 16x10 | 21 | 1 | grass, zoo | the round tree's crown | 8 / 8 | 0 |
| Snow spruce 16x13 | 7 | 1 | igloo | a separate drawing from the pine | 4 / 4 | 0 (swap to pine: worse) |
| Snow drift 24x9 | 2 | 1 | igloo | one | 9 / 9 | 0 |
| Rock 10x5 | 9 | 1 | grass, saloon | one drawing | 2 / 2 | 0 |
| Peaks A-D 32x22-26 | 1+2+1+1 | 1 each | saloon, igloo | snow and desert are the same tiles, palette only | 12-15 each | 0 |
| Cactus S, S2, B, Q | 1, 1, 3, 2 | 1 | cactus | four pieces, each repeated at the same offset | 1-2 each | 0 |

Same-shape-in-different-colour is already done. The only repeats that are not unified are pines and round trees standing at different pixel offsets (the tiles differ because the cut lines differ).
Tree sprites in the lodge, zoo and igloo pictures are the same pieces as the land trees, so they are included in these counts.
Fences (cow ranch), road pieces and water edges are not template pieces; they show up as near twins (rows 3 and 5), not as repeats.

**4. Ground textures.** Three texture tiles cover every biome: flat (873 grass cells, 211 desert, 161 jungle, 137 farm, 82 snow, 15 yard), sprout (grass, farm, jungle: 199 + 40 + 36) and ripple (desert and snow: 45 + 14). All are already shared across palettes on both models.
The other ground-like tiles (12 on Color, 13 on DMG) are road-bend and clipped-tip fringes, covered by row 6. A smaller set would save nothing.

**5. Palette merges.** 23 palettes; `town1` is pinned (UI text). 397 of 2288 windows hold 8 palettes. Colour distance is the mean of |dR|+|dG|+|dB| per colour after the best colour matching (0 identical, 765 black to white).
Nearest neighbours: town1@z to town1 12, town1@n to town1 24, cactus to grass 26, bistro@g to bistro 44, town4 to town1 48, town5 to town1 58. None of the merges changes ids or tiles (the pixels are relabelled, the tile shapes stay).
Merged all six: 8/8 windows 397 to 82.
Wedges: the 8/8 windows over (35-37, 44-46) are 63 windows, over (50-52, 44-46) are 82. Small-palette merges do NOT free them: cactus into grass leaves 31 west and 82 east; all six leave 31 west and 82 east. The west wedge windows
always hold grass, town1 and water, and the 8 are drawn from cow, factory, farm, saloon, base, tea@g, zoo, cactus, lodge, town1@g. Single merges that clear every east window: factory into grass (distance 54), grass into factory, farm into town1 (92).
No single merge clears the west windows except water into town1 (116) and grass into town1 (176), which are not realistic. Two merges do: cactus into grass plus factory into grass (distance 80, clears all 114 wedge windows).
So the wedge bends would be freed only by recolouring the factory yard to grass (panel 6) or by moving something else; dropping the tiny palettes alone is not enough.
Windows that reach 8 only because of tiny palettes (cactus 157, town5 120, town4 131, bistro@g 116 windows) would drop below 8, which gives room for later features, not for the wedges.

**6. Tight windows.** The worst padded path window (top right, 174) holds: venue igloo 33 tiles, other scenery 64 (the mountain range), water 25, road 23, peaks 12, snow drifts 9, lodge 7, pines 6, spruces 4, ground 5, rocks 2.
The worst 21x19 window (176) holds: space lounge 63, saloon 34, other scenery 41 (desert peaks, mesa, airbase mountain), peaks 16, town 10, round trees 6, cactus 4. Only near-twin redraws touch these; palette merges and phase snaps change neither.
Best per area for the top-right window: river edge (174 to 170), mountain range (170), road (172), igloo picture (173). Best for the 21x19 worst: venue Space (170), mountain/mesa (174).

## What I am unsure of

- The simulation moves trees by up to 4 px and merges blocks by pixel edit; a real redraw by hand could pick better stars (the greedy star count is conservative) or do worse than "center wins" at the eye level.
- Color near-merges here keep each cell's palette and only change index pixels; a 1-px index change shows as a different colour pixel, which can be more visible than on DMG. The 1-px Color count (36 ids, 1583 cells) is dominated by road cells; look before taking it.
- Category boxes (venue, decor) use the venue picture sizes in `VENUE_PX` and template matching; objects outside the 8 templates (fences, barn, hay, zoo gate) are counted as "other scenery" or venue.
- Window effects after a merge are exact for DMG tile counts and Color palette counts; the real allocator (hints, colouring) may behave differently once the tiles change, so the 174 and 176 numbers are what the generator's limit checks would see, not a build result.
