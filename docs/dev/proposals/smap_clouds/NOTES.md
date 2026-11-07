# Story-map sprite clouds: proposal (nothing in src/, assets/ or tests/golden/)

Owner: "I think it would be cool is sprite clouds drifted across the map, independent of the background. Assuming we got sprite only tile slots freed up."

Files here: `clouds.txt` (the art, typed by hand), `clouds.py` (transcribes, composites over the integrated map, lints; rebuild: `python3 -I docs/dev/proposals/smap_clouds/clouds.py docs/dev/proposals/smap_clouds`, from the repo root, after `smap_import/build.py`'s first two steps wrote the A5 scratch src), `clouds_dmg.png` / `clouds_cgb.png` (indexed 64x16 sheets: 8 sprite columns), `sheet_designs.png`, `sheet_context.png`, `smap_clouds_dmg_color.gif` (DMG left, Color right, 450 game frames at 60 fps: Sal stands at the town, walks west to the saloon and north to the stadium, the camera scrolls x 216 to 0 and y 164 to 28 and the clouds scroll with the map; no flashing), `report.txt`.

**Revision 2 (owner, Q114: "clouds need to stay where they are in relation to map not sal").** The clouds now live in world coordinates: they scroll with the map when Sal walks and the camera moves, and still drift on their own. Revision 1 (screen-space lanes) is replaced; the designs, tiles and palettes did not change.

**Answer: yes.** 13 OAM entries (23-35) and 16 sprite-only tiles buy five clouds on four world lanes; no new WRAM global (one free byte of `story_scratch` holds the clock's high half), no existing sprite touched, no new Color palette slot that the map uses. The beam-up hides them.

## Part 1: budget (the map as it stands in src/ today)

The map is in 8x16 sprite mode (`src/main.c:12`). An entry is 16 lines tall whatever its art; that is what the scanline counts below use.

| Resource | Used now | Free for clouds | Where |
|---|---|---|---|
| OAM entries (40) | 0-2 arrows, 3-6 Sal, 7 bang, 8-18 the 11 stop dots, 19-21 UFO, 22 panel cursor = 23 | 23-39 = 17 free; the clouds take **23-35 (13)**. The beam-up uses 0-2 (the UFO over Sal) and 23-31 (the beam, 9 entries), so the clouds must be hidden while it plays (they are: see Integration). 36-39 stay spare | `src/smap.c:136-141`; beam `src/cameo.c:116-143` (`figat(23, rows*3 ...)`, `for (i = 23; i < 32 ...)`) |
| Sprite-only tiles (ids 0-127; BG ids 128+ share 0x8800 with sprites 128-255) | 0-39 Sal (5 pictures x 8); 56-73 the map's 18 (UFO 6, dots 4, bang 2, arrows 6: `tools/gen_smap.py:94`, `src/smap_priv.h:13`); 98-115 the beam and UFO art when the space lounge is open (`cam_map_load`, `CAM_SPACE_BASE 98`, 18 tiles, from `tools/gen_cameo.py`) | 40-55 (16: the DX badge / zoo cameo's, not loaded on the map), **74-97 (24)**, 116-127 (12) = 52 with the space lounge open, 70 before. Clouds take 74-89 (even ids: 8x16 pairs) | `src/game.h:157-167`; the map streams only BG ids 0-35 and 93-232 (`pool_id`, `src/smap_priv.h:84`), never 0x8000-0x87FF |
| Color bank-1 sprite tiles | none loaded by the map (`tile_load` bank 1 writes the BG pool ids only, `src/smap_eng.c:515-525`) | all 128 of bank 1 ids 0-127. Not needed: the clouds are the same tiles on both machines | |
| DMG sprite palettes | OBP0 = 0xD0 (every map sprite: Sal, arrows, dots, UFO, bang; `src/smap.c:795`). OBP1 only by the beam (0xE4, `cam_map_load`, `src/cameo.c:124`; the beam's entries use `S_PALETTE`) | **OBP1** (set 0x90: white, light grey, mid grey) | |
| Color OBJ palettes | 0 Sal, 2 UFO and beam, 3 open dot, 4 locked dot, 6 arrow, 7 bang (`src/smap.c:131-135, 789-791`) | **1 and 5** (the cards' and the coin's; the map never loads either). Clouds: 1 | |
| WRAM | `story_scratch` variable block is full: `S_V + V_N = 396 + 68 = 464 = S_T` (`src/smap_priv.h:32,45,46`). `V_TICK` is only 8 bits | **1 byte**: the high byte of a 16-bit frame clock (`V_TICK` low), at `story_scratch` 238 or 239, which the region table leaves free (A_PUSE ends at 238, A_ATTR_UI starts at 240, `src/smap_priv.h:21-22`; the stage 1 import notes keep those 2 B free after its re-lay). Not a global. Everything else is derived: world x = (base + clock >> shift) & 1023, fixed world y, screen = world - camera |

### Sprites per scanline

Worst line today, standing at a stop (all entries counted by their 16 lines):
- Sal 2 (his two rows of two entries never overlap each other) + the left and right arrows 2 = 4 on his lines sy+8..sy+15 (sy = his top, `src/smap.c:316-340`).
- Lines sy+25..sy+31: Sal 2 + the down arrow 1 + his own dot 1 + up to 2 more dots on the same lane (stops share a feet y: `smapw_stop`; at most 2 other stops fit in 160 px) = 6.
- With the bang or the UFO near a stop: 7. During the beam: UFO 3 + beam band 3 on the 5 lines they share = 6; Sal 2 + one band 3 = 5.
- **Worst non-cloud line: 7.** The limit is 10.

Clouds, world version: four lanes at world y 56, 184, 312 and 440 (128 apart, 16 tall), one cloud per lane except lane 184 (two, 210 px apart and the same speed, so never on one 160 px screen). Any 144-line view holds a whole lane. Lanes are at least 16 px apart in y, so **a line holds at most one cloud: 3 entries.** Worst line = 7 + 3 = **10, within the limit.** The mock-up counts it: over the whole walk the most cloud entries on any line is 3.
- **A cloud over Sal** (now possible, the world moves under both): the worst line is exactly that 7 + 3 = 10; no cloud can add a second group to the same lines. Hardware keeps the first 10 entries in OAM order and the clouds are the last (23-35), so a cloud is what gets cut, never Sal. Color: Sal is in front (lower OAM index). **DMG: the entry with the smaller x wins, so a cloud to the left of Sal's x covers part of him for the seconds it takes to pass.** The mock-up's walk (town to saloon to stadium) never meets one (0 frames); the town stop sits right under lane 184, so a cloud can cross him there. Owner's call: accept it (a cloud passing over a hero reads as a cloud), or hide a cloud while it is within Sal's box (one compare per cloud, about 40 cycles).
- A cloud off the screen gets OAM y 0, so it costs no line at all (revision 1's off-screen-in-x entries did). Unused entries 23-35 are y 0.
- **The beam**: `V_BEAM` set hides entries 23-35 (y 0) once, in `press_a`, and `cloud_update` returns while `V_BEAM` is non-zero. The beam then writes 23-31 itself (it already sets them to y 0 first) and never touches 32+. So during the beam the line counts are the beam's own (6 at most).

**How many 8x16 clouds fit:** the 13 entries hold 5 clouds (A 2 + C 3 + B 3 + B 3 + A 2); up to 17 entries (23-39) are free, so a 6th would fit. Lanes are the limit, not entries. Tiles: 16 of the 52-70 free.

### CPU (estimated by instruction count, not measured: nothing is built)

Every frame `cloud_update(cx, cy)` runs at the end of `smap_update` (after the walk and the drawing, so it takes nothing from the `LY_WORK` window `smap_region_work` watches, `src/smap_priv.h:88-97`):
- the clock: `V(V_TICK)++` already runs; when it wraps to 0, `SC(238)++` (about 12 cycles once per 256 frames);
- per lane: its screen y = world y - camera y (16-bit, about 30 cycles) and a range test, about 35 cycles in all; 4 lanes = about 140;
- per cloud on a lane that is in view: `wx = (base + (clk >> shift)) & 1023` (16-bit shifts and add, about 70), `sx = wx - cx` (about 30), the range test (about 40), 2-3 stores of the entries' x and y (about 70) = about 210; at most 2 lanes are in view, usually 2 clouds = about 420;
- entries of a cloud that just left the screen get y 0 (about 10 per entry).
- **Total about 600 cycles a frame = 0.85% of a 70,224-cycle DMG frame, about 1.3 scanlines (456 cycles each); worst about 750.** The same every frame, walking or standing.
- Window hiding folds in: with a window up (V_WH) an entry overlapping its rows gets y 0, 3 more compares.
- Revision 1 (screen space, a step every 4-8 frames) cost about 115 cycles a frame; the world version costs about 5 times that, because the camera moves them and the positions are rederived every frame. If that is too much for the walk: a cheaper form shifts the visible clouds' x by the camera's step like `oam_shift` (about 120 cycles for 13 entries) and recomputes only when a cloud enters or leaves; not drawn here.
- No asm needed. If wanted: `make cfall` keeps the C twin as the rules say.

ROM: 256 B of tiles, about 400-500 B of code and 3 palette words, all in smap.c's own bank (it is a bank on its own), none in ROM0 (the 745 B of free ROM0 stay). Not measured: romusage before and after in stage 2.


## Part 2: the clouds

Three designs (`sheet_designs.png`): A PUFF 16x16 (2 entries), B LONG 24x16 (3), C TOWER 24x16 (3). Each is 8x16 columns, white body (index 1), soft shade under the belly and the lobes' lower corners (index 2), outline (index 3). Flips: the engine mirrors a whole group with the OAM X flip (entries in reverse order, each flipped), which doubles the looks for free; it is drawn flip-safe (lit from the top, symmetric lobes).

- DMG: OBP1 = 0x90 gives white / light grey / mid grey. On the white ground the outline carries the cloud; over water (shade 2) the white body carries it and the outline vanishes into the water. The shade is the light grey, so the belly is soft. No black anywhere, so clouds never compete with Sal (black outline).
- Color: OBJ palette 1: `F8F8F8` `B0C8F0` `7090C8` (RGB555 0x7FFF, 0x7B36, 0x664E), same tiles; a cool blue shade and a deeper blue edge (figure 13: shadows cool, darkest a deep hue; figure 7: mids below about 16 of 31 so the steps survive the washed-out LCD, first draft D0E0F8 was too close to white). The map and design sheets are the project's raw palette render; one row of `sheet_designs.png` shows an approximate LCD correction (a common emulator matrix, illustrative, not SameBoy's).
- Tiles: 16 slots, 12 unique (3 are blank halves), 9 with flips merged. Not merged in the plan: flip-merging would save 4 tiles but adds an entry flag per tile; unneeded.
- Drift: lane-mates, A and C: 1 px / 8 frames (7.5 px/s, shift 3), B 1 px / 4 (15 px/s, shift 2). World x = (base + clock >> shift) & 1023; the world is 512 wide, so each cloud is on the map half of the time and slides off the right edge and returns from the left (hidden both times). 16384 and 8192 are multiples of 1024, so the 16-bit clock wrapping (every 18 minutes) is seamless. A group is X-flipped by a fixed flag per cloud.
- Stays with the map (owner Q114): a cloud's position is fixed in the world and moves only by its own drift; Sal walking sends the camera across it exactly like the trees (the GIF: the camera goes from x 216 to 0 and y 164 to 28 over 250 frames and the clouds scroll with the ground). Screen position = world - camera, so no `oam_shift` is involved; the map's camera is the only input.
- No flashing: the motion is 1 px steps, slow, light shades; DMG ghosting is not a worry at this speed on white.

Mock-up honesty: the integrated map is a stage 1 proposal, not in the engine, so the GIF and context sheet composite the sprites over the python render of that map (the same world renders the other import sheets use; merged again for stage 1c), with Sal's real art and no arrows or dots drawn, the camera following Sal 1:1 (clamped to the world), and the clock = the game frame. It is not a ROM capture. The context sheet shows clouds at the world positions of a clock value set in `clouds.py` (the igloo view is at clock 3040, about 50 s in).

## Integration sketch (stage 2, if the owner picks one)

- `tools/gen_smap.py`: three more 8x16 groups after the UFO; `SOB_CLOUD_A/B/C` at OBJ 74-89 (`OB + 18 .. OB + 33`; `OB` is 56; keep a build assert `< 98`, the beam art starts there); one more row in `smap_obj_pal` for OBJ palette 1. The 5 clouds' (design, world y, base x, shift, flip) table is `const` in smap.c (about 25 B).
- `smap_enter`: `set_sprite_data` already loads the block; after `cam_map_load()` set `OBP1_REG = 0x90` (DMG) / `set_sprite_palette(1, 1, ...)` (Color); write tile and prop of entries 23-35 once (Color palette 1 | flip, DMG `S_PALETTE` for OBP1; flipped groups list their entries in reverse); `story_scratch` is cleared there, so the clock starts at 0 (clouds start from their base each visit).
- `smap_update`: `if (!++V(V_TICK)) SC(238)++` instead of `V(V_TICK)++`; one `cloud_update()` call at the end (the lanes above, `if (V(V_BEAM)) return;` first), with the window hide folded in.
- Beam (`press_a`, `smap.c:634`): `V_BEAM = 1` also sets `OBP1_REG = OBP1_PLAY` (0xE4) for the beam's edges and sets y 0 on entries 23-35 (OBP1 0xE4 would turn the clouds dark, and 23-31 are the beam's).
- `leave()`: put OBP1 back to `OBP1_PLAY` (screens after the map expect their own value; `cameo.c:57` sets it for the PRE scene, other screens do not obviously).
- Tests: a junk-poke test of the cloud entries (PyBoy zeroes OAM; real hardware does not), an OAM assertion (entries 23-35 only; y 0 during the beam), and the existing map goldens will change where a cloud is in view: freeze the clock or hide the entries in the tests (the clock byte is a free scratch byte, so a test can poke it).


## DMG or Color

- **Fits DMG**: yes, entirely. It needs OBP1 (free on the map except the beam, handled above), 8 OAM entries and 16 tiles. Nothing is Color-only.
- **Color**: needs one OBJ palette (1 or 5, the map uses neither). Gating: none; the same code runs on both, only the prop byte differs (`is_cgb`).
- Color-only extras possible, not in this proposal: a second palette tinting the clouds with the time of day (a palette write, no tiles), bank-1 variants (128 bank-1 sprite tiles are free).

## Risks and doubts

1. **OBP1 collision with the beam** (`cam_map_load` sets 0xE4 whenever the space lounge is open). The fix is two writes, but it touches the beam's code path and the leave path; stage 2 must test the beam and the screens after the map on DMG.
2. **OBJ palette 1 on Color**: the map must load it itself; I did not find who restores it afterwards (mini-games and levels load their own mug palettes; I did not verify every path). Palette 5 is the alternative; `render.c:816` rewrites it when a coin appears.
3. **DMG sprite priority**: a cloud with a smaller x than Sal covers part of him while it passes (the world version can put a cloud over him: the town stop is under lane 184). Color is fine. Optional hide-near-Sal compare, see above.
4. **Free scratch byte**: `story_scratch` 238 (or 239) is free today and in the stage 1 import's re-lay (it needs +6 B for 20 palettes and keeps 2 B at 238..239 and 9 B at 291..299 free), but `tests/test_scratch_map.py` and any later re-lay must keep it. If the owner wants strictly no storage: `V_TICK` alone is 8 bits, so a drift of 1 px per 4-8 frames cannot be derived from it without a jump every 256 frames; `music_frames` is 16-bit but counts only with the sound on and restarts with each tune, so I did not use it.
5. **CPU**: about 600 cycles a frame (estimate), 5 times the screen-space version, because the camera moves them. There is a cheaper form (above).
6. **Coverage**: a cloud is on the map half the time and a lane is 16 px of 560, so a screen shows about 1 or 2 clouds, sometimes none (the GIF has gaps). More lanes cost lines, not entries; more clouds per lane risk two on one screen and 13 on a line.
7. **Shade 0 against shade 1 on a real DMG** is a small step: the clouds depend on the mid-grey outline (OBP1 0x90). With OBP0 only (0xD0: no mid grey) they would need a black outline; not recommended.
8. **OAM 23-35 reserved**: any later map sprite there collides, and the beam owns 23-31 while it plays.
9. **Window layer**: under a panel or the name tag an entry is set to y 0; the world position is derived each frame, so nothing is lost while it is hidden.
10. The mock-up's walk uses `WALK_STEP_FRAMES` 10 (`src/game.h:44`) but not the walk's easing.


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
| Scanline budget | PASS | clouds 3 per line max (4 lanes 128 px apart, one cloud per lane on a screen); worst non-cloud line 7; total 10 worst, clouds last in OAM so they alone are cut; off-screen clouds are y 0. The mock-up counted 3 cloud entries on a line at most over 450 frames. |
| Squint test at 1x, DMG and Color | PASS | `sheet_context.png` x3 and the GIF: clouds read as white shapes with a grey rim on white ground, white bodies on water; Sal (black outline) reads first. Not tested on a real DMG. |
| No banding, squares, stray pixels, L-doubles, V-point chins | PASS | lint clean; by eye, the 1-px steps of the belly are 1,1,1 on both ends. |
| Light direction; flipped sprites still correct | PASS | lit from the top, symmetric; flipped panels in `sheet_designs.png`. |
| Tiles: tiled preview | N/A | sprites. |
| Animation: clusters intact, unchanged tiles shared | PASS | whole groups move as units (1 px drift plus the camera's scroll); no frames, one tile set; no wind-up (nothing player-triggered). |
| Placeholder footprint | N/A | new asset; the free slots it takes are listed in the budget table. |
| Files indexed, ordered, grid-aligned, named | PASS | index 0 magenta transparent, 1 lightest to 3 darkest, 64x16. |
| Engine questions with working assumptions | PASS | see below. |

## Questions for the programmer (with the art's working assumption)

1. Is OBP1 free on the story map when the beam is not playing? Assumed yes (only `cam_map_load` writes it, 0xE4); the art needs 0x90 and a switch back at the beam.
2. Does anything between the map and the next screen assume OBJ palette 1 or OBP1 as the map left them? Assumed no; stage 2 to restore `OBP1_PLAY` in `leave()`.
3. Can OAM 23-35 be reserved for the map's clouds, and `story_scratch` 238 for their clock? Assumed yes (nothing uses them today; 23-31 are the beam's while it plays).
4. Should the map's goldens hide or freeze the clouds? Assumed a frozen start position or hidden entries in the test runs.

## Deviations from the skill and the brief

- Skill: "Deliver one labelled contact sheet per proposal set (`tools/dev/contact_sheet.py`)." I did not use that tool. The brief asked for big bold labels, at most 2 columns and at least 1000 px; contact_sheet.py's labels are 14 px, so the two sheets are composed in `clouds.py` with 34 to 46 px bold labels (the same helper `smap_import/renders.py` uses).
- Skill, section 4 rule 5: "Outlines on gameplay objects only", and figure rule "Light-shaded outline: Background objects ... Not DMG gameplay sprites". Clouds are scenery, so a light top edge was the first plan; it read hollow on the white ground, so the outline is the full mid-grey (index 3) on all sides, and the shade (index 2) is inside. Owner-visible choice.
- Skill: "**before placing the first pixel**, read the required files ... Figures to study before drawing". I read the reference text before drawing but opened the figure images (03, 04, 07, 11, 13, 15, 18) only after the first designs, and not 02, 05, 06, 08, 12, 17. What they changed: figure 7 (the shade colour was too close to white for the LCD), figure 18 (the belly shade is a flat band under the lobes, 2 rows, ends stepped differently from the outline: not the 'hugging' form).
- Brief: "from the integrated map ... in the real engine" (skill: "Show art in the real engine"). The integrated map exists only as the stage 1 proposal, not in src/, so there is no engine build of it to put sprites in; the mock-up composites over its render. Stated above.
