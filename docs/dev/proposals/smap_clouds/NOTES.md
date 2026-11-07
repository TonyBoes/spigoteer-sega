# Story-map sprite clouds: proposal (nothing in src/, assets/ or tests/golden/)

Owner: "I think it would be cool is sprite clouds drifted across the map, independent of the background. Assuming we got sprite only tile slots freed up."

Files here: `clouds.txt` (the art, typed by hand), `clouds.py` (transcribes, composites over the integrated map, lints; rebuild: `python3 -I docs/dev/proposals/smap_clouds/clouds.py docs/dev/proposals/smap_clouds`, from the repo root, after `smap_import/build.py`'s first two steps wrote the A5 scratch src), `clouds_dmg.png` / `clouds_cgb.png` (indexed 64x16 sheets: 8 sprite columns), `sheet_designs.png`, `sheet_context.png`, `smap_clouds_dmg_color.gif` (DMG left, Color right, 454 game frames at 60 fps, no flashing), `report.txt`.

**Answer: yes.** 8 OAM entries and 16 sprite-only tiles buy three clouds; 0 bytes of WRAM, no existing sprite touched, no new Color palette slot that the map uses.

## Part 1: budget (the map as it stands in src/ today)

The map is in 8x16 sprite mode (`src/main.c:12`). An entry is 16 lines tall whatever its art; that is what the scanline counts below use.

| Resource | Used now | Free for clouds | Where |
|---|---|---|---|
| OAM entries (40) | 0-2 arrows, 3-6 Sal, 7 bang, 8-18 the 11 stop dots, 19-21 UFO, 22 panel cursor = 23 | 23-39 = 17; **32-39 = 8 permanently**. The beam-up uses 0-2 (the UFO over Sal) and 23-31 (the beam, 9 entries) | `src/smap.c:136-141`; beam `src/cameo.c:116-143` (`figat(23, rows*3 ...)`, `for (i = 23; i < 32 ...)`) |
| Sprite-only tiles (ids 0-127; BG ids 128+ share 0x8800 with sprites 128-255) | 0-39 Sal (5 pictures x 8); 56-73 the map's 18 (UFO 6, dots 4, bang 2, arrows 6: `tools/gen_smap.py:94`, `src/smap_priv.h:13`); 98-115 the beam and UFO art when the space lounge is open (`cam_map_load`, `CAM_SPACE_BASE 98`, 18 tiles, from `tools/gen_cameo.py`) | 40-55 (16: the DX badge / zoo cameo's, not loaded on the map), **74-97 (24)**, 116-127 (12) = 52 with the space lounge open, 70 before. Clouds take 74-89 (even ids: 8x16 pairs) | `src/game.h:157-167`; the map streams only BG ids 0-35 and 93-232 (`pool_id`, `src/smap_priv.h:84`), never 0x8000-0x87FF |
| Color bank-1 sprite tiles | none loaded by the map (`tile_load` bank 1 writes the BG pool ids only, `src/smap_eng.c:515-525`) | all 128 of bank 1 ids 0-127. Not needed: the clouds are the same tiles on both machines | |
| DMG sprite palettes | OBP0 = 0xD0 (every map sprite: Sal, arrows, dots, UFO, bang; `src/smap.c:795`). OBP1 only by the beam (0xE4, `cam_map_load`, `src/cameo.c:124`; the beam's entries use `S_PALETTE`) | **OBP1** (set 0x90: white, light grey, mid grey) | |
| Color OBJ palettes | 0 Sal, 2 UFO and beam, 3 open dot, 4 locked dot, 6 arrow, 7 bang (`src/smap.c:131-135, 789-791`) | **1 and 5** (the cards' and the coin's; the map never loads either). Clouds: 1 | |
| WRAM | `story_scratch` variable block is full: `S_V + V_N = 396 + 68 = 464 = S_T` (`src/smap_priv.h:32,45,46`) | none needed: the cloud state lives in the shadow OAM entries themselves (see Integration) | |

### Sprites per scanline

Worst line today, standing at a stop (all entries counted by their 16 lines, hidden-by-x entries included):
- Sal 2 (his two rows of two entries never overlap each other) + the left and right arrows 2 = 4 on his lines sy+8..sy+15 (sy = his top, `src/smap.c:316-340`).
- Lines sy+25..sy+31: Sal 2 + the down arrow 1 + his own dot 1 + up to 2 more dots on the same lane (stops share a feet y: `smapw_stop`, at most 2 other stops fit in 160 px; `draw_still`) = 6.
- With the bang or the UFO near a stop: 7. During the beam: UFO 3 + beam band 3 on the 5 lines they share = 6; Sal 2 + one band 3 = 5.
- **Worst non-cloud line: 7.** The limit is 10.

Clouds: three groups of 3, 2 and 3 entries on three lanes at least 16 px apart (screen y 12, 100, 118), so a line never holds two clouds: **at most 3 more, 10 in the worst case, normally 3 to 7.** Two things make that safe:
1. Hardware keeps the first 10 entries *in OAM order* on a line and drops the later ones. The clouds are OAM 32-39, the last, so if a line is ever full it is a cloud that is cut, never Sal, an arrow, a dot or the UFO.
2. The lanes sit away from Sal. The camera centres him (his top is screen y 48 when the camera is not clamped), so his band with the arrows is lines 39..88 and the lanes are 12-27, 100-115, 118-133. `clouds.py` walks the igloo to lodge route and counts 0 frames where a lane meets his band. At the world's edges he moves toward a lane and a cloud can pass over him (Color: he is in front, lower OAM index; DMG: the hardware gives the entry with the smaller x priority, so a cloud left of his x covers his head for a moment; harmless).
An entry off the screen in x still counts toward the line, so the three lanes cost their entries all the time, not only when a cloud is in view. That is already in the numbers above.

**How many 8x16 clouds fit:** 8 entries = 3 clouds (3 + 2 + 3), or 4 two-entry puffs. Up to 17 entries (23-39) if the beam-up hid the clouds first (the beam writes 23-31 itself); not proposed, the 8 are enough for a few clouds on a 160 px view and keep the beam untouched. Tiles: 16 of the 52-70 free.

### CPU (estimated by instruction count, not measured: nothing is built)

State is `x` of each group's first entry (the other entries are +8 and +16). A step is `x++` on each of the group's 2-3 entries (about 30 cycles each in SDCC C), one compare for the wrap, and a tick test per cloud:
- Steps happen when `(V_TICK & mask) == phase`: B every 4 frames (phase 0), A and C every 8 (phases 5 and 3). The phases never coincide, so **at most one cloud steps in a frame**: about 190 cycles on a step frame, about 40 on the others, **about 115 on average = 0.16% of a 70,224-cycle DMG frame; worst 0.4 of a 456-cycle scanline.**
- It is called once at the end of `smap_update`, after the walk and the drawing, so it takes nothing from the `LY_WORK` window that `smap_region_work` watches (`src/smap_priv.h:88-97`).
- Walking frames (`draw_walk`) are untouched. No `oam_shift` is needed: the clouds are in screen space.
- Hiding under a window (the name tag, a panel) is done in `draw()` (which already runs on every frame with a window or a still hero): 3 compares and up to 8 stores, about 100 cycles, only on those frames. A cloud entry overlapping the window rows is set to y 0, restored from its lane constant.
- No asm needed. If the owner wants one anyway: `make cfall` keeps the C twin as the rules say.

ROM: 256 B of tiles, about 250-350 B of code and 3 palette words, all in smap.c's own bank (it is a bank on its own), none in ROM0 (the 745 B of free ROM0 stay). Nobody measured the bank's free space: romusage before and after in stage 2.

## Part 2: the clouds

Three designs (`sheet_designs.png`): A PUFF 16x16 (2 entries), B LONG 24x16 (3), C TOWER 24x16 (3). Each is 8x16 columns, white body (index 1), soft shade under the belly and the lobes' lower corners (index 2), outline (index 3). Flips: the engine mirrors a whole group with the OAM X flip (entries in reverse order, each flipped), which doubles the looks for free; it is drawn flip-safe (lit from the top, symmetric lobes).

- DMG: OBP1 = 0x90 gives white / light grey / mid grey. On the white ground the outline carries the cloud; over water (shade 2) the white body carries it and the outline vanishes into the water. The shade is the light grey, so the belly is soft. No black anywhere, so clouds never compete with Sal (black outline).
- Color: OBJ palette 1: `F8F8F8` `B0C8F0` `7090C8` (RGB555 0x7FFF, 0x7B36, 0x664E), same tiles; a cool blue shade and a deeper blue edge (figure 13: shadows cool, darkest a deep hue; figure 7: mids below about 16 of 31 so the steps survive the washed-out LCD, first draft D0E0F8 was too close to white). The map and design sheets are the project's raw palette render; one row of `sheet_designs.png` shows an approximate LCD correction (a common emulator matrix, illustrative, not SameBoy's).
- Tiles: 16 slots, 12 unique (3 are blank halves), 9 with flips merged. Not merged in the plan: flip-merging would save 4 tiles but adds an entry flag per tile; unneeded.
- Drift: C 1 px / 8 frames (7.5 px/s), B 1 px / 4 (15 px/s), A 1 px / 8. A group wraps when its first entry's x byte reaches 168 (all entries are then off the right edge) and jumps to 232 (-24 px, all off the left); at each wrap the engine can flip the group. The GIF does that; a cloud takes 12 to 25 s to cross.
- Independent of the background: screen space; Sal walking at 2 px/frame sends the ground past them. Option (not drawn): a quarter of the camera's step added to x gives a parallax; costs a few more cycles per camera move.
- No flashing: the motion is 1 px steps, slow, light shades; DMG ghosting is not a worry at this speed on white.

Mock-up honesty: the integrated map is a stage 1 proposal, not in the engine, so the GIF and context sheet composite the sprites over the python render of that map (the same world renders the other import sheets use), with Sal's real art and no arrows or dots drawn. It is not a ROM capture.

## Integration sketch (stage 2, if the owner picks one)

- `tools/gen_smap.py`: three more 8x16 groups after the UFO; `SOB_CLOUD_A/B/C` at OBJ 74-89 (`OB + 18`; `OB` is 56, so these are `OB + 18 .. OB + 33`; keep the `< 98` check because the beam art starts at 98); one more row in `smap_obj_pal` for OBJ palette 1.
- `smap_enter`: `set_sprite_data` already loads the block; after `cam_map_load()` set `OBP1_REG = 0x90` (DMG) / `set_sprite_palette(1, 1, ...)` (Color); write the 8 entries (lane y + 16, staggered x, tile, prop: Color palette 1 | flip, DMG `S_PALETTE` for OBP1).
- `smap_update`: one `cloud_drift()` call at the end (the tick test and the steps above); `draw()`: the window hide for entries 32-39.
- Beam (`press_a`, `smap.c:634`): `V_BEAM = 1` also sets `OBP1_REG = OBP1_PLAY` (0xE4) for the beam's edges and hides the 8 clouds (OBP1 0xE4 would turn them dark); or let them keep going and accept dark ones for 3 s: not recommended.
- `leave()`: put OBP1 back to `OBP1_PLAY` (screens after the map expect their own value; `cameo.c:57` sets it for the PRE scene, other screens do not obviously).
- Tests: a junk-poke test of the cloud entries (PyBoy zeroes OAM; real hardware does not; `hide_all_sprites` at `smap.c:773` runs first), an OAM-count assertion (entries 32-39 only), and existing map goldens will change where a cloud sits: the map's goldens need the clouds frozen or the entries hidden for the tests.

## DMG or Color

- **Fits DMG**: yes, entirely. It needs OBP1 (free on the map except the beam, handled above), 8 OAM entries and 16 tiles. Nothing is Color-only.
- **Color**: needs one OBJ palette (1 or 5, the map uses neither). Gating: none; the same code runs on both, only the prop byte differs (`is_cgb`).
- Color-only extras possible, not in this proposal: a second palette tinting the clouds with the time of day (a palette write, no tiles), bank-1 variants (128 bank-1 sprite tiles are free).

## Risks and doubts

1. **OBP1 collision with the beam** (`cam_map_load` sets 0xE4 whenever the space lounge is open). The fix is two writes, but it touches the beam's code path and the leave path; stage 2 must test the beam and the screens after the map on DMG.
2. **OBJ palette 1 on Color**: the map must load it itself; I did not find who restores it afterwards (mini-games and levels load their own mug palettes; I did not verify every path). Palette 5 is the alternative; `render.c:816` rewrites it when a coin appears.
3. **DMG sprite priority**: a cloud can cover Sal where its x is smaller than his. Lanes avoid his band unless the camera is clamped.
4. **Shade 0 against shade 1 on a real DMG** is a small step: the clouds depend on the mid-grey outline (OBP1 0x90). With OBP0 only (0xD0: no mid grey) the clouds would need a black outline or only a light-grey one; not recommended.
5. **The 10 per line limit holds only with the OAM order**: any later feature that puts a sprite at an index above 31 would sit behind the clouds in priority; keep 32-39 reserved.
6. **Window layer**: clouds under a panel are hidden by y 0; the cloud then reappears with the panel gone (its x kept in the entry, stepping stops while it is hidden: it should keep stepping; the step code must not read y).
7. CPU numbers are an estimate. The mock-up's Sal walk uses `WALK_STEP_FRAMES` 10 (`src/game.h:44`) but not the walk's easing.

## Hand-placed art: clean-up log

- B, first draft: a flat stratus with tapering ends read as a flying saucer; redrawn as two humps with a valley (rows 4-9), rounded ends, same flat belly.
- All three: top-edge pixels changed from index 2 (light) to 3 (mid) after the DMG white-ground render showed a hollow, faint cloud; index 2 stays only on the underside and lobe corners.
- Five lone index-2 "crease" pixels (A rows 6 twice, B row 8, C row 6 twice) removed: the lint flagged them as orphans and at x8 they read as stray notches. Lint then clean.
- Corners: bottom row 1-1-1 steps in, flat 10 / 18 px belly kept; side runs checked against figure 11 (1,1,1 then vertical).
- Quality bar at 1x: the approved ice igloo and Sal (`sheet_designs.png` bottom row, native size): the clouds are lighter and smaller than both and never darker than Sal's outline, so they sit behind the story visually.

## Self-audit (gb-pixel-art section 9)

| Check | Result | Evidence |
|---|---|---|
| Hand-placed: what wrote pixels to the delivered file? | PASS | `clouds.txt`, typed by me; `clouds.py` transcribes it into indexed PNGs, composites and scales (nearest). No outline, fill, mirror or shade step. The only flip is the hardware X flip shown in the sheet. |
| Clean-up pass done by hand | PASS | log above (5 items). |
| 1x comparison with the quality bar | PASS | igloo and Sal, bottom row of `sheet_designs.png`. |
| Required references read before drawing | PASS | sprites.md ("Keep characters 16 px wide or less where possible" / "Outline the silhouette"), linework.md ("Remove L-shaped doubles"; "a stray pixel unlike all 8 neighbours is noise"), light-and-form.md ("Sprites that will be mirrored ... are lit from the top"), fx-and-ui.md ("Count particles against 10 objects per scanline and 40 total"), hardware.md ("at most 10 on any scanline"; "Off-screen objects still count"), animation.md ("Move clusters as units"), palettes.md ("Author 8-bit channel values in steps of 8"), briefs.md. Figures opened after the first designs: 03, 04, 07, 11, 13, 15, 18 (not 02, 05, 06, 08, 12, 17), see deviations. |
| Lint | PASS | DMG: 64x16, 3 colours, 12 unique tiles (9 flip-merged), RESULT PASS, no warnings after the clean-up (first run: 5 orphan pixels, fixed). CGB: RESULT PASS; first run warned #D0E4F8 off the RGB555 grid; the colours are now on the grid (B0C8F0, 7090C8); 1 of 8 palettes. |
| Colours per tile, palettes, tile count | PASS | 3 colours + transparent per tile; 1 OBJ palette; 16 tile slots in 74-89. |
| Scanline budget | PASS | clouds 3 per line max (3 lanes 16 px apart); worst non-cloud line 7; total 10 worst, clouds last in OAM so they alone are cut. |
| Squint test at 1x, DMG and Color | PASS | `sheet_context.png` x3 and the GIF: clouds read as white shapes with a grey rim on white ground, white bodies on water; Sal (black outline) reads first. Not tested on a real DMG. |
| No banding, squares, stray pixels, L-doubles, V-point chins | PASS | lint clean; by eye, the 1-px steps of the belly are 1,1,1 on both ends. |
| Light direction; flipped sprites still correct | PASS | lit from the top, symmetric; flipped panels in `sheet_designs.png`. |
| Tiles: tiled preview | N/A | sprites. |
| Animation: clusters intact, unchanged tiles shared | PASS | whole groups move by 1 px as units; no frames, one tile set; no wind-up (nothing player-triggered). |
| Placeholder footprint | N/A | new asset; the free slots it takes are listed in the budget table. |
| Files indexed, ordered, grid-aligned, named | PASS | index 0 magenta transparent, 1 lightest to 3 darkest, 64x16. |
| Engine questions with working assumptions | PASS | see below. |

## Questions for the programmer (with the art's working assumption)

1. Is OBP1 free on the story map when the beam is not playing? Assumed yes (only `cam_map_load` writes it, 0xE4); the art needs 0x90 and a switch back at the beam.
2. Does anything between the map and the next screen assume OBJ palette 1 or OBP1 as the map left them? Assumed no; stage 2 to restore `OBP1_PLAY` in `leave()`.
3. Can OAM 32-39 be reserved for the map from now on? Assumed yes (nothing on the map uses them today).
4. Should the map's goldens hide or freeze the clouds? Assumed a frozen start position or hidden entries in the test runs.

## Deviations from the skill and the brief

- Skill: "Deliver one labelled contact sheet per proposal set (`tools/dev/contact_sheet.py`)." I did not use that tool. The brief asked for big bold labels, at most 2 columns and at least 1000 px; contact_sheet.py's labels are 14 px, so the two sheets are composed in `clouds.py` with 34 to 46 px bold labels (the same helper `smap_import/renders.py` uses).
- Skill, section 4 rule 5: "Outlines on gameplay objects only", and figure rule "Light-shaded outline: Background objects ... Not DMG gameplay sprites". Clouds are scenery, so a light top edge was the first plan; it read hollow on the white ground, so the outline is the full mid-grey (index 3) on all sides, and the shade (index 2) is inside. Owner-visible choice.
- Skill: "**before placing the first pixel**, read the required files ... Figures to study before drawing". I read the reference text before drawing but opened the figure images (03, 04, 07, 11, 13, 15, 18) only after the first designs, and not 02, 05, 06, 08, 12, 17. What they changed: figure 7 (the shade colour was too close to white for the LCD), figure 18 (the belly shade is a flat band under the lobes, 2 rows, ends stepped differently from the outline: not the 'hugging' form).
- Brief: "from the integrated map ... in the real engine" (skill: "Show art in the real engine"). The integrated map exists only as the stage 1 proposal, not in src/, so there is no engine build of it to put sprites in; the mock-up composites over its render. Stated above.
