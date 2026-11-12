# Story map, DMG: tile sharing from TODAY's art (PROPOSAL, nothing imported)

Owner 11-11, after the 11-06 kit sheets: "I don't hate the idea of doing that kind of tile plan, but I want the agent to go back and do a version using the
current art instead." This is that version. Every pixel of every package is a pixel of today's `assets/smap/world_d.png`: a merge makes a tile show
another tile that is already in the picture. No new art, no kit, no sign swapped, no building redrawn. Nothing under `assets/`, `src/` or `tests/golden/`
was touched. DMG only; the Color picture is unchanged.

**Short answer.** Today's art has few near-twins. Screened for visible damage, merging buys about 4 percent of the tiles for a pixel dusting (light),
8 percent for a few hundred pixels spread over ground and roads (medium), and 10 percent if the venues are touched too (strong, not recommended). The worst
view goes 164 to 159 / 157 / 154. That is not the 11-06 kit's size of gain; it is the part that costs nothing visible. Today's pool has room (164 of 176).
Bigger savings need real shared parts, which means redrawing.

## Sheets (all in `png/`, DMG greys, big labels, order in each heading)

| file | shows |
|---|---|
| `venue_<name>_x4.png` (11) | per venue, x4, 2 x 2: TODAY, LIGHT, STRONG, CHANGED (orange = light, purple = strong; MEDIUM equals LIGHT inside venues) |
| `whole_map_x1.png` | whole map at x1, 2 x 2: TODAY, LIGHT, MEDIUM, STRONG |
| `whole_map_changed_x2.png` | changed pixels on the whole map (orange light, red extra in medium, purple extra in strong) |
| `ground_views_x3.png` | the six busiest ground, road, water and mountain views: TODAY, MEDIUM, CHANGED |
| `ranked_merges_1..4.png` | every candidate merge in rank order, cheapest first: the tile in its map context, before, after, diff (a label `t172>372` is block 172 replaced by block 372) |
| `world_d_light.png`, `_medium.png`, `_strong.png` | the three whole-map pictures as indexed DMG PNGs (same 4 palette entries as `world_d.png`), for the pick |

Not shown: Saloon and Rodeo have 0 changed cells in every package (their tiles have no near-twins); their sheets show that. The pixel counts printed on the sheets include the ground in the crop, so they are larger than the per-venue figures in section 4.

## 1. Today's numbers (`count_tiles.py`, output in `count_tiles.txt`)

Method as 11-06 `count_tiles.py`, on the build's own model (`gen_smap_world.Model`, DMG data set, finished map, no fog). The map is now 64 x 70 cells (4480).

| | today |
|---|---|
| unique tiles | **896** (903 over all unlock states; 46 of the ids are animation tiles) |
| used once | **663** |
| worst 21 x 19 view | **164** of 176 (at cells 41,0: the mountains, bistro and igloo corner); 22 x 20 loaded region: 181 |
| new tiles per one-cell scroll step (22 x 20 region, 8584 steps) | mean **4.60**, p95 **11**, max 19 |
| venues | 906 cells, 545 unique tiles (61 percent of all); everything else 3574 cells |

On 11-06 the map had 658 unique tiles, the worst view was 175. The 11-07 re-import grew the map to 70 rows and moved the pressure; the pool is no longer at the edge,
but the scroll step is still 4.6 tiles and 11 at p95, and that is what the sharing is for.

| area | cells | unique | only here | used once |
|---|---|---|---|---|
| Saloon | 63 | 53 | 52 | 45 |
| Teahouse | 84 | 64 | 63 | 56 |
| Town | 108 | 75 | 72 | 65 |
| Lodge | 80 | 54 | 44 | 43 |
| Space | 126 | 61 | 47 | 44 |
| Factory | 70 | 47 | 46 | 35 |
| Stadium | 70 | 45 | 38 | 34 |
| Zoo | 112 | 46 | 42 | 23 |
| Bistro | 63 | 43 | 42 | 38 |
| Rodeo | 70 | 43 | 41 | 38 |
| Igloo | 60 | 34 | 30 | 28 |
| Roads | 913 | 122 | 106 | 41 |
| Ground: Snow | 213 | 84 | 52 | 49 |
| Ground: Desert | 242 | 52 | 22 | 21 |
| Ground: Water | 332 | 39 | 38 | 21 |
| Ground: Grass | 1359 | 22 | 3 | 3 |
| (other grounds) | 1066 | 129 | | |

## 2. What cannot be shared (read this first)

- **Identical tiles: 0.** The model already merges equal blocks. The "invisible" package is therefore empty on DMG.
- **Flips: 134 pairs are mirror twins, saving nothing.** The DMG background has no flip bit (hardware: BG flips are CGB only). Making one of a pair equal to
  the other's mirror is an ordinary merge with a pixel cost, so flip twins are not special here. (Color already merges them: `FLIP_MERGE`.)
- **Near-twins are scarce.** Tiles that have another tile within N pixels: 1 px: 21, 2 px: 40, 3 px: 96, 4 px: 180, 6 px: 291, 8 px: 379, 12 px: 515 of 896.
  About 380 tiles have no neighbour within 12 px: they are the buildings' own art.
- **Animated cells.** Their tiles are pinned (the animation rewrites one tile, every cell of that id would play it). Blocked: factory smoke (2 tiles equal to the
  rest puff, 96 near twins within 6 px), runway lights (3 equal twins), water (24 near twins), lodge smoke (7). Nothing else (falls, fountain, bunting, flag,
  radar, igloo smoke, cow tails, logs) has a twin within 6 px, so they block no merge. Their frames are never touched.

## 3. The method, and how a merge is chosen

A block B is replaced by block A when B differs from A by few pixels. Greedy, cheapest first (pixels changed on the map = differing pixels x cells that show B),
in stages of at most 1, 2, 3 ... 6 differing pixels per tile (so each package contains the smaller stages). Before a pair may merge it is screened on the map,
in the 3 x 3 cell context of every cell that shows B:

1. no new stray pixel (an orphan, the lint's definition);
2. no broken line: no changed pixel that is dark ink (shade 3) with a dark 4-neighbour;
3. no new dark speck or 2 px dash (a new group of 1 or 2 dark pixels);
4. no letter tile: sign letters are protected by hand (`vetoes.py`: COCOA, TAPS, LODGE, ROBOCO, ZOO, MILK, the zoo gate bars, the penguin's chest);
5. no animated tile; no merge costing more than 40 px on the map (the road hatch, 825 px for one tile, the desert edge, 378 px, the pine foot, 84 px, are off the list).

Rules 2 and 3 were added after I looked at the first light package: it added dark ticks under the runway, opened the lodge chimney's top outline and lengthened the
giraffe's ears. The screen is what makes the packages quiet; its price is shown in section 5.

## 4. Packages

Cap = most pixels a tile may differ from the tile it shows. A "venue tile" is a block with a cell inside a venue.

| package | rule | tiles | saved | used once | worst 21x19 | worst 22x20 | step mean | step p95 | px changed | cells changed | px that change a shade by 2 or more |
|---|---|---|---|---|---|---|---|---|---|---|---|
| today | | 896 | 0 | 663 | 164 | 181 | 4.60 | 11 | 0 | 0 | 0 |
| **invisible** | identical or flip only | 896 | **0** | | | | | | 0 | 0 | 0 |
| **light** | at most 3 px per tile, everywhere | 861 | **35** | 631 | **159** | 174 | 4.46 | 11 | **140** | 54 | 51 |
| **medium** | light + ground, roads, water, mountains, decor up to 6 px; venue tiles still 3 | 828 | **68** | 610 | **157** | 174 | 4.33 | 11 | **430** | 118 | 125 |
| strong (not recommended) | everything up to 6 px | 804 | **92** | 580 | **154** | 170 | 4.23 | 10 | **557** | 145 | 183 |

(The lint, run on the three indexed pictures, counts 847 / 814 / 790 unique tiles against 882 today: the same savings of 35 / 68 / 92; the model's 896 counts 14
animation ids that the picture does not.)

Where the changes fall (cells / pixels; areas with no change omitted; `areas.md`):

| area | cells | light | medium | strong |
|---|---|---|---|---|
| Stadium | 70 | 1 / 1 | 1 / 1 | 5 / 18 |
| Bistro | 63 | 2 / 2 | 2 / 2 | 7 / 26 |
| Igloo | 60 | 0 | 0 | 1 / 5 |
| Town | 108 | 2 / 2 | 2 / 2 | 4 / 13 |
| Lodge | 80 | 0 | 0 | 3 / 13 |
| Space | 126 | 9 / 23 | 9 / 23 | 13 / 42 |
| Factory | 70 | 2 / 6 | 2 / 6 | 7 / 30 |
| Zoo | 112 | 3 / 7 | 3 / 7 | 3 / 7 |
| Teahouse | 84 | 2 / 4 | 2 / 4 | 7 / 27 |
| Saloon, Rodeo | 63, 70 | 0 | 0 | 0 |
| Roads | 913 | 14 / 42 | 49 / 198 | 49 / 204 |
| Ground: Snow | 213 | 5 / 13 | 13 / 52 | 13 / 52 |
| Ground: Water | 332 | 3 / 9 | 17 / 75 | 12 / 45 |
| Ground: Pines | 18 | 6 / 18 | 6 / 18 | 9 / 33 |
| Ground: Desert, Grass, Base, Park | | 6 / 13 | 12 / 42 | 12 / 42 |

### The cost curve (`curve.py`)

| cap per tile | all areas: saved | px | worst 21x19 | ground only: saved | px | worst 21x19 |
|---|---|---|---|---|---|---|
| 1 px | 9 | 10 | 164 | 2 | 5 | 164 |
| 2 px | 11 | 14 | 162 | 5 | 13 | 163 |
| **3 px** | 35 | 140 | 159 | 21 | 94 | 161 |
| 4 px | 68 | 372 | 156 | 43 | 278 | 161 |
| 6 px | 92 | 557 | 154 | 54 | 384 | 161 |
| 8 px | 119 | 861 | 150 | 66 | 499 | 160 |
| 10 px | 131 | 1011 | 148 | 73 | 639 | 159 |

There is a step at 3 px (cheap, 4 px per tile saved) and a slow climb after it (about 11 px per tile from 3 to 6). Beyond 6 px the pictures start to differ (the 11-06
kit's merges were of that size and worse).

What the screen costs (same caps, `packages.py --loose`, without rules 2 and 3): light 855 tiles (41 saved), medium 815 (81), strong 772 (124), worst view 158 / 156 / 152.
A stricter variant that counts shade steps instead of pixels (`--weighted`, a dark pixel on a light ground counts 3): 873 / 831 / 803 (23 / 65 / 93 saved).
The numbers in the table are the middle one.

## 5. Ranked merges

`ranked.md` lists all 92 merges of the strong run in rank order (block ids, pixels changed on the map, cells, where, and whether light or medium contains it);
`png/ranked_merges_N.png` shows each in context. Cheapest first:

| rank | px | tiles saved | where |
|---|---|---|---|
| 1 to 9 | 1 to 2 each | 1 each | one brick or roof pixel in Bistro (2), Town (2), Space (2), Teahouse, Stadium and Zoo (shared tile), a Base tile |
| 10 to 12 | 2 to 3 | 1 each | three Snow mountain-flank tiles |
| 13 to 23 | 3 each | 1 each | five Road bend and bridge tiles, one Water edge, one Base tile, one Space rock strip, two Factory wall tiles, one Teahouse eave |
| 24 to 30 | 6 each | 1 each | Snow and Desert mountains, four Road bend pairs (2 cells each), Water edge, Zoo gate bar tile |
| 31 to 32 | 9 | 1 each | Pine feet, grass tuft tile |
| 33 and on | 3 to 18 | 1 each | Road bends and bridge ends (cells 2 to 3 each), Space and Snow mountains, Water, Teahouse and Factory wall details |

Tiles saved per pixel changed: 1 tile per 1 to 3 px for the first 23, per 6 px for rank 24 to 30, per 9 to 18 px after that.

## 6. Do the venues lose richness? (judged against the 11-06 complaint)

The 11-06 complaint was that the saloon, stadium and bistro lost richness and looked alike. Here no building is redrawn and no tile moves between buildings, so they cannot
look alike. Judged per package at x4 and at x1:

**Light and medium (same inside every venue).** No visible loss at x1. Side by side at x4 the changes are: Stadium one pixel in the stands' roof line; Bistro one pixel in two
brick joints; Town two pixels in a dormer and a rooftop trim; Factory one wall-panel pixel at each end of the roof beam; Teahouse the upper eave tips each 1 px longer;
Zoo a giraffe-head pixel and the foot of two gate bars, 1 px each; Space: nine cells of the airstrip mountains lose or move a rock strata dash (23 px, 3 px at most per tile).
Saloon, Igloo, Lodge, Rodeo: nothing. Bistro, Stadium and Saloon are the three the owner named: 2 px, 1 px and 0 px.

**Medium, outside the venues.** 118 cells in all. Roads: 49 cells (198 px) lose a gravel dot or shift a curb pixel on bends and bridge ends. Water: 17 cells (75 px), edge pixels of the
river and pond. Snow: 13 cells (52 px), mountain flank texture. Pines 6 cells (feet of the pine trunks). Visible only when flicking between TODAY and MEDIUM on the ground sheet.
Grid-hiding variants that remain (medium): Grass 19 of 22 tiles, Desert 52 of 52, Snow 76 of 84, Roads 101 of 122.

**Strong (not recommended).**
- Bistro: the menu window gains a dark bar in its left pane and a pane corner shifts: visible loss, the one place it reads.
- Stadium: the lawn's lower-left and lower-right edge steps change and a stand-edge pixel moves: small at x4.
- Teahouse: the paper walls gain two vertical seam lines: visible at x4.
- Factory: the sawtooth ridge tips change and short grey dashes appear on the ground in front of the door: visible at x4.
- Space: strata dashes on the main peak move or vanish in 13 cells; Town: the fountain's top cap and the chapel door's foot (4 cells); Lodge: a roof or antler pixel and the bucket's rim (3 cells).
- Saloon, Rodeo, Igloo (1 cell): nothing worth naming.

Sign letters never change in any package (COCOA, TAPS, LODGE, ROBOCO, ZOO, MILK BAR), by the hand protections.

## 7. Does it help Color?

Not needed and not done: the Color map stays as it is (2 banks, 352 slots, flip merging already on). For information, 13 of the light merges and 30 of the medium merges are also
near twins in the Color picture with the same palette, so a later Color pass could take them. DMG and Color tile ids already come from separate data sets, so nothing couples them.

## 8. Budgets

DMG BG tile pool only (the 176 slots; `SMAPW_POOL`), plus 16 bytes of ROM per tile saved (light 560 B, medium 1088 B, strong 1472 B less in the tile bank). No palette, WRAM, ROM0 or code
change. Tile ids and `path_hints` change with any package, so `gen_smap_world.py` must be re-run on the picked picture; I did not run it on the patched pictures
(the numbers above use the build's own model on the patched blocks, not the generator).

## 9. Self-audit (skill section 9)

| check | result |
|---|---|
| Hand-placed | No pixel is new. A script chooses which existing, hand-drawn tile a cell shows instead of another; each changed pixel is copied from that tile. The owner decides which merges stand (`ranked.md`). Scripts also count, screen, preview and write the PNG. |
| Clean-up log | Three review rounds of the ranked sheets. Round 1 vetoed the letters and gate bars; round 2 (light package) added the broken-line and dark-speck rules; round 3 added the line rule's weighted and loose variants for the notes. Protected ids: 207 208 235 341 342 343 386 387 642 643 734 735 736 737 791 832 833 (reasons in `vetoes.py`). |
| 1x comparison | `whole_map_x1.png`: the four maps are not distinguishable at x1 except by flicking. At x4 see section 6. |
| References read | `environments.md` ("Merge near-duplicate tiles. Report the unique-tile count for every scene"), `linework.md` ("Remove stray pixels and noise ... Accidental squares"), `light-and-form.md` ("Background objects: shade 3 only for the deepest shadows; walls and solid boundaries may use it structurally"). Figures 06, 09, 10, 14, 15, 16, 18 were NOT opened: this task draws nothing. |
| Lint (`gb_art_lint.py --mode dmg --kind bg`) | PASS (hardware and format) on all three pictures; unique tiles 847 / 814 / 790 (today 882). Warnings, today -> light / medium / strong: 2x2 squares 46 -> 43 / 43 / 43; L-doubles 154 -> 157 / 162 / 166 (the merges add a few; none checked individually); orphans 1391 -> 1366 / 1326 / 1326 (fewer). |
| Colours, palettes, tile count | 4 DMG shades, palette entries in the order of `world_d.png`; no palette change; tiles 896 -> 861 / 828 / 804 (model), worst view 164 -> 159 / 157 / 154. |
| Squint test | At x1 nothing reads differently; the orange and purple overlays are the only way to find the changes. |
| Tiled preview | Not applicable (no tile is drawn); the merged tiles are reused where they already sit. |
| Animation | No animated tile is touched; the blockers are listed in section 2. |
| Footprint | Every cell, every venue footprint, every stop and path unchanged. |

## 10. Deviations from the skill

- Skill "Provide previews at 1x and 4x ... with the quality-bar asset beside yours": the quality bar is today's picture, always shown beside the package.
- Project rule "contact sheets with `tools/dev/contact_sheet.py`": I used my own script (`render.py`, `sheets.py`) because that tool's labels are 14 px and the owner cannot read small labels on his phone.
- Skill "Every pixel is hand-placed ... Scripts may only convert, preview, lint and build": the merge choice is made by a script (screened by rules I wrote, reviewed by eye on `ranked_merges_N.png`). See the self-audit row. If the owner reads that rule as covering the choice of tile, the packages are a list of candidates for him to pick from, not art.
- Skill "Deliver ONE figure first and stop for approval": not a figure batch; the brief asked for the whole proposal.
- No engine run (`make BUILD=out/b_real` scratch ROM) of the packages: the brief asked for sheets; the engine would need the generator re-run on the patched pictures.

## 11. Doubts

- Whether 4 / 8 / 10 percent is worth any change at all with the pool at 164 of 176; the scroll step (mean 4.6, p95 11) moves little (to 4.46 / 4.33, 11 / 11 / 10).
- The screen is my judgement of "visible"; the lodge chimney, the giraffe ears and the runway ticks were the cases that showed me a bare pixel count is not enough. There may be more I
  did not see; `ranked_merges_N.png` is where to look.
- Medium's ground changes (Roads, Water, Snow) are only judged on the busiest six views and the 92 context thumbnails.
- p95 of the scroll step is untouched by light and medium. The 11-run of new tiles when a venue slides in is the venue's own unique art; only redrawn shared parts reduce it.

## 12. Reproduce (from the repo root, about 2 minutes in all)

    python3 docs/dev/proposals/smap_dmg_kit2/count_tiles.py > docs/dev/proposals/smap_dmg_kit2/count_tiles.txt   # today's numbers
    python3 docs/dev/proposals/smap_dmg_kit2/packages.py          # merges, results.json, arrays.npz (--loose / --weighted print the variants, write nothing)
    python3 docs/dev/proposals/smap_dmg_kit2/report.py            # packages.md, areas.md, ranked.md, report.json
    python3 docs/dev/proposals/smap_dmg_kit2/curve.py             # curve.md
    python3 docs/dev/proposals/smap_dmg_kit2/sheets.py            # png/ venue sheets, whole map, ground views, world_d_*.png
    python3 docs/dev/proposals/smap_dmg_kit2/review.py 1 999 --png   # png/ranked_merges_N.png

Files: `lib.py` (model, window and step counts), `merge.py` (distance, greedy, screens), `vetoes.py` (protected ids with reasons), `render.py` (greys, big labels).

## 13. Applied 11-11 (owner: "medium except uneven line on stadium")

Patch: `tools/dev/smap_dmg_tile_share.py` (idempotent, 115 cells, 421 px; a second run changes 0), regenerated `assets/smap/world_d.png`. Color untouched.
Re-run on main's world (zoo bush gone, route plan in): medium is 826 tiles in the proposal model (66 saved, 421 px, worst 157 / 174); `vetoes.py` protects blocks 19 and 189.

Dropped, stadium (both made an uneven line): cell (9,1) tile 19 > 313, 1 px, the roofline of the stands above the flag grows 1 px; cell (8,8) tile 189 > 161, 5 px, the lawn's lower-right edge steps.
Dropped with them: tile 12 > 313 in two ground cells, Snow (58,0) and Desert (15,31), 1 px each (they rode in the same merge group), and the Zoo cell (16,53), which shares tile 19 (1 px).
So 9 px fewer than the 430 of the proposal. Nothing else was invalidated by the zoo-bush removal (the bush cells were in no merge). The Stadium view differs by 0 px (`png/applied_stadium_x4.png`); `png/applied_changed_x2.png` is the whole-map overlay of what was applied.
Reproduce: `packages.py`, `export_patch.py`, `python3 tools/dev/smap_dmg_tile_share.py`, `applied_sheets.py`.
