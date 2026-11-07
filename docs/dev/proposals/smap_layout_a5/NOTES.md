# Story map layout A5 (proposal, nothing imported to assets/)

Sheets (this folder): `sheet_color_x2.png` (whole map Color, A4 | A5), `sheet_dmg_x2.png` (DMG, A4 | A5 dark water | A5 light water), `sheet_factory_town.png` (A4 | A5 close-ups x3), `sheet_water.png` (river source and lake; Color | DMG dark | DMG light, x3), `sheet_new_tiles.png` (typed tiles x8), `sheet_engine.png` (real engine, scratch build, Color over DMG).
Scratch only: `src/` here is a copy of `tools/smap_world` plus typed layout files; `mk_src.py` then `mk_a5.py` regenerate `src/world2.py`, `src/gen_smap_world.py`, `src/pal.py`, `src/lay_today.py` (do not commit those). Env: `SMAP_LAYOUT=lay_A5 SMAP_FOG=none`, `SMAP_GOLD=lilac` (default), `SMAP_WATERDMG=light` (DMG data set only).

## What changed from A4

1. **Factory yard and palette.** The `factory` palette is re-tinted in place (index 0 packed earth d0c890 instead of pale grey; steel green-grey 88a090 / 385048; ink 101818). No picture pixel changed, no slot added. The yard ground is packed earth with a new gravel tile; two grass notches in blank cells of the picture and two earth bits running north past the log piles break the rectangle. The yard is still mostly the picture's own 10 x 7 cells (roads bound it west, south and east).
2. **Town edge on grass.** The air round the town buildings was cream because the town palettes' index 0 is cream. Cells with air and no cream wall take `town1@g` (index 0 = grass, no pixel change). Cells with air and cream walls needed a pixel touch: 172 typed pixels (flag centres, spigot, tower one pixel wider each side, the hall/trough gap, the trough foot). Same edits on DMG and Color (the index is the DMG shade). The six gold-edge cells use `town1@g` too (`SMAP_GOLD=lilac`: the lilac edge shows on the gold; `lodge` and `own` (a 19th palette, impossible) were tried and rejected).
3. **River from the top ranges.** Falls (2 x 2 typed cells) under the gap between ranges B and C, mossy rocks flanking, a pool, a 2-wide stream through the snow with grass banks (the snow starts east of the bank), a short bridge where the bistro-igloo road crosses, then the meandering river to the lake. The snow edge was moved east (x 49 to 50) to keep the `igloo` palette out of the river windows.
4. **Irregular lake** rows 49 to 69, typed shore (bays, a headland, lobes), every shore run two rows or more; the mill pond has rounded corners; the shore tiles have second variants on a typed rhythm.
5. **DMG water.** Dark water (as A4) and a typed light set (land 0, water 1 = 168, glints 0, rock edge 2), shown side by side. DMG and Color tile sets are built separately so the light water costs no Color tile.

## Numbers (A4 to A5)

| | A4 | A5 dark | A5 light |
|---|---|---|---|
| DMG tiles | 539 | 547 | 546 |
| worst 21x19 window (limit 176) | 128 | 133 | 133 |
| 22x20 window | 132 | 138 | 138 |
| flat (limit 239) | 219 | 218 | 218 |
| Color tiles / slots | 610 / 352 | 618 / 352 | - |
| palettes per 21x19 window (cap 8) | 8 | 8 | 8 |
| palette table (cap 18) | 18 | 18 | 18 |
| cells the generator snapped to another palette | - | 0 | 0 |

Scratch engine build: links, ROM0 15566 used (477 free by the linker map, unchanged), WRAM_LO 3936, WRAM_HI_0 3635 (unchanged), ROM_34 14224 (A4 13662). All 11 legs walked in PyBoy, DMG and Color: Sal stays on screen, camera follows (`probe_shots.py`). `make test` and `make check` not run (a changed map changes goldens; for the owner's pick first). `engine_scratch.patch` (CAM_MAXY 416, row limit 69) was applied for the build and reverted; `src/` of the game is unchanged.

## Palette slots

A4's 18-entry table held an unused `base` slot and the unused `stadium` slot (placeholder park). A5 spends `base` for `town1@g`; `stadium` stays for the real park. A `factory@g` and a 19th `town5@g` are not affordable (the table is baked into `story_scratch`, WRAM is full). The `water` palette also serves the river in the snow (grass bank pixels beside snow cells).

## New tiles (DMG)

10 typed water tiles (falls FL_A FL_B FR_A FR_B, splash SPL_A SPL_B, shore variants BN2 BS2 BW2 BE2) + 1 gravel, in the dark set; the same 10 again as the light set (replaces, not adds). Lint (`gb_art_lint.py`, DMG and CGB strips): PASS, 1 orphan pixel warning (a gravel or splash pixel, intentional), RGB-not-indexed warning (previews only).
`check_water.py`: every adjacent water pair joins on its shared edge, dark and light; floating logs only on flat water: OK. `probe_presnap.py`: windows over 8 palettes before snapping: 0. (`probe_pal.py` counts after the generator's snap and can hide a recolour; I was caught by this once: the first A5 river in the snow had 44 snapped cells.)

## Pixel edits in the town (x, y inside the picture; index values)

1. Flag centres (28,12) (44,12) (60,12): 0 to 1. 2. Spigot (44,25) (46,30) (44,44) (45,33..40): 0 to 1. 3. (51..55,39): 0 to 2. 4. Tower left: x=0 to 3 for rows 14..29, 31..58 and (0,59); (1,14) (1,31) to 2; (1,15) (2,15) (1,56..58) (2,56..58) to 1; (1,16..29) (1,32..55) to 0. 5. Tower right: (14,14..29) to 2, (15,14..29) to 3. 6. Hall-trough gap: (41,48..58) to 2; (41,59..63) (40,60..63) (42,63) to 3. 7. Trough foot: (70..71,60..61) (71,62) (70..71,63) to 3. Also in `src/v_town_a5.py`.

## Doubts

- The factory yard is still largely the picture's rectangle; a real organic yard needs a `factory@g` palette or a redrawn picture edge.
- The river in the snow has a grass bank strip beside the snow (a palette limit, not a taste). The flanking rocks are mossy green (grass palette), not grey.
- Town edge: the tower is one pixel wider and the three flag centres and spigot highlights changed shade: these are small redraws of a picture the owner likes; he should look at `sheet_factory_town.png`.
- The desert next to the town was trimmed to x <= 28 (rows 28 to 33) and the snow tongue starts at x 52 and 53 (rows 15, 16) to stay at 8 palettes per window.
- The lake is a 10 to 12 wide river-lake; the cow field and tea garden banks are unchanged.
- Placeholders (park, space lounge, ranges) are boxes, not art.

## Questions for the programmer

1. Can the palette table grow past 18 (it is baked into `story_scratch`)? It would free `factory@g` and `town5@g`.
2. The engine's map height (70 rows) needs `CAM_MAXY` 416 and the row limits 69: derive them from the generator.

## Self-audit (gb-pixel-art)

| Item | Result | Evidence |
|---|---|---|
| Hand-placed pixels only | PASS | typed lists in `a5art.py`, `v_town_a5.py`; scripts only convert, preview, lint, build |
| Adjacent features separated by DMG value | PASS | tower outline 3 beside wall 2/1, water 88 beside land 248, light water 168 beside land 248 |
| Tile and palette budgets | PASS | table above |
| Lint | PASS with warnings | see New tiles |
| 1x in the engine | PASS | `sheet_engine.png` |
| DMG and Color both shown | PASS | `sheet_dmg_x2.png`, `sheet_color_x2.png` |
| Redesign of liked art avoided | PARTIAL | town picture pixels touched (172); flagged above |
| Tiled preview | PARTIAL | tiles repeat by the real map (lake, river at x3); `tiled_preview.py` not run |
| Animation | n/a | static water |

## Floating logs redrawn (owner: "logs in water read as ice blocks")

`sheet_logs_river.png`: now | v1 | v2, river section with the log landing, Color, DMG dark, DMG light, x3. Select with `SMAP_LOG=v1|v2` (default `old`, A4's pieces); the typed art is `src/logs5.py` (symbols typed by hand, converted to indices by a table), wired in `src/a5art.py`.
- v1: one log, dark bark body with two bark lines, a round end showing an end-grain disc (cream with a dark centre dot) at one end, a 2 px ripple at each end. v2: a pair of logs side by side, discs at opposite ends. Pieces are whole cells now (16 x 8 and 8 x 16; they sat 1 px in before).
- Color palette: no new palette and no new slot. The log cells keep the `water` palette; its index 3 ("deep") changes from navy 2c4c78 to lodge wood brown 905830 (the log landing's own wood). Index 3 is used only by the logs and the falls' rock edge, so the falls edge turns brown too (rock/earth; say if that is unwanted). Palettes per window stay 8 (`probe_presnap.py`: 0 windows over, 0 snapped).
- DMG dark: body 24, bark lines and disc 168, on water 88. DMG light: body 24, bark lines 88, disc 248, on water 168.
- Counts, v1 and v2 alike (and unchanged from the old logs): DMG 547 tiles (light water 546), worst 21x19 window 133 of 176, 22x20 138, flat 218; Color 618 tiles in 352 slots. `check_water.py` OK.
- Lint (DMG): PASS. Warnings kept on purpose: L-shaped doubles at the rounded log ends (one corner pixel of a 5 px log), v2's 2 x 2 end discs (the disc is the point), one orphan (the disc's centre dot).
- Doubt: on DMG dark the logs are near black on mid-grey water (reads wood, a little heavy); a mid body is impossible there because the water is already 88. The Color brown is the lodge's mid wood; the landing's planks are mostly its lighter tan.
