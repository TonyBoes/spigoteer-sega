# Town, round 4 (2026-11-04): building quality pass, plus a motion plan

These are concepts only. Nothing changed in `src/`, `tests/` or the goldens. The pictures were checked in a scratch ROM
(`out/town/st`, built from round 3's scratch tree with these four pictures installed) and captured with PyBoy.

- `sheet_round3_round4.png` compares round 3 with round 4 from the engine captures, Color over DMG, at 1x and x3.
- `sal_night.png` shows Sal at night before and after, INTRO pages 1 and 11, x5.
- `gifs/` holds the motion mockups (x3, 4.3 s loop): `day_color`, `day_dmg`, `night_color`, `night_dmg`, `dawn_color`.
- `pictures/` holds the four round 4 sources. `water_phases/phaseN/` holds the water tiles the engine would swap in.
- `tools/` has the master, the per-time keys, compose and the checks. `motion.py` builds the GIFs.

## Part A: the stills (made on the master, so all three times of day agree)

| # | Owner's note | Round 3 | Round 4 |
| --- | --- | --- | --- |
| 1 | Big open door behind the rival and Sal (right building) | A dark passage arch behind each figure | A plain house front with its own key `J`. By day it is pale cream plaster (DMG0), so Dregs (ink hair, lilac jacket, skin) reads, legs included. At night it is the sky's navy inside its ink outline, with lit windows, so Sal's ink hair reads against it. At dawn the coffee stand covers it. |
| 2 | Two small gable windows at the far edges look like eyes | One window at each outer edge | One centred double window (3-px panes, 2-px mullion) under the oculus. The left gable is cropped so its window sits at x 0-9. |
| 3 | The clock tower is at a weird height next to the tavern | The tavern ridge was about level with the tower | The tavern roof is lowered so its ridge (y 39) and eave (y 40) line up with the tower's cornice. The spire now rises well above every roof as the landmark. |
| 4 | Light texture on the buildings, at least by day | Plain walls | Two sparse brick-hint tiles (`TEX` A/B: one 3-px dash and one 2-px dash per tile) on 7 wall cells, in sandstone (DMG1) by day. At night and dawn they take the wall's own colour, so they vanish. They use whole cells only, add 0 colours and fit the budget. |
| 5 | Patron silhouettes in the tavern window | Empty lit bays | Two hand-drawn busts in bays 1 (with a mug) and 4: ink at night, the wall's lilac by day. Dregs stands in bays 2-3 (intro_a, credits). |
| 6 | A stray hat in front of the fountain by day | The night crowd's hat tip and a robot antenna showed on the basin | Removed (`FINALE_FIX`, below). Every silhouette was checked in all four pictures. |
| 7 | Sal's legs look odd at night | Walk/shrug legs | His own idle sprite's standing legs (`sal_stand` in compose.py), on INTRO p1 and p11. See `sal_night.png`. |

### Clean-up log (by hand; `tools/compose.py` and `tools/master.py`)

- FINALE (83-90, 82-87): the old crowd's hat tip removed. `g#` became `m` and `g` became `#` on the basin edge.
- FINALE (120-123, 86-87): the robot antenna removed. `#` became `m` and `g` became `#`.
- The round 3 cap fix was dropped because the stray-hat fix replaces it.
- INTRO p1 and p11 (144, 89): an orphan cobble highlight beside Sal's new feet, changed from `h` to `p`.
- CREDITS: the backboard is now taken from the right house key `BJ`.
- The right house's texture cell uses its own key `x`, so the hints stay invisible on the navy wall at night.

## Counts (check.py = gen_story's packing; the scratch ROM builds; ROM0 443 B free, unchanged)

| Picture | Round 4 tiles / limit | Round 3 | Palettes |
| --- | --- | --- | --- |
| intro_before | 119 / 151 | 115 | 4 |
| intro_a | 109 / 117 (the limit is 147 minus the 30 trail tiles) | 106 | 3 |
| finale_a | **145 / 146** (1 spare) | 139 | 4 |
| credits_b | 138 / 199 | 138 | 5 + HUD (Option A, as before) |

Every water phase gives the same counts, with no clashes and no new palette. Each phase changes only the 6 jet tiles.

**Lint (gb_art_lint, bg): RESULT PASS on all 11 files**, which are the 8 pictures and the 3 masters. Each water phase
(1-3) also passes on all 11.

The lint warnings are the same kinds as in round 3, and fewer of them:
- L-doubles: 65 to 44 (intro_before) and 59 to 40 (finale_a).
- Orphans: 41 to 40.
- The off-grid colours are the game's existing palette values.

## Part B: motion plan (mockups only, no engine code)

### 9. Fountain water: BG tile frames, DMG and Color. Recommended.

**What moves.** The two jets (cells x 10 and x 15, rows 6-8) have 4 phases.
- Each phase moves every highlight pixel (W) one row down its jet.
- Phase 0 is the art as drawn.
- The highlight pixels of each phase are hand-listed in `motion.py` (`L`, `R`, `R_GLASS`).
- In FINALE, the right jet stops at the Spigoteer's glass (y 59).
- The droplets and the foam stay still, so the effect stays calm.

**Pictures.** Water flows in intro_before (night), finale_a (day) and credits_b (dawn). intro_a has no jets, because
the spigot has just blown off, so it stays still.

**Cost.**

| Item | Cost |
| --- | --- |
| VRAM | 0 new tiles. The phases overwrite the 6 jet tiles in place. They are already unique; the generator should assert it. |
| BG tiles | 0 |
| Palettes | 0 |
| ROM | 3 phases × 6 tiles × 16 B = 288 B per picture, 864 B for 3 pictures, plus about 120 B of code. All banked, generated into `build/story_pictures.c` beside the burst. |
| ROM0 | 0 |
| WRAM | 0 new globals. It needs one tick/phase byte in `story_scratch` (for example 169, a burst byte, which is free outside the INTRO). Staging reuses `PS_TILES` (`story_scratch + 40`, 48 B = one jet), used only while `story_swap == SW_IDLE`. |
| CPU | On a step frame: copy 48 B from ROM, then 3 `vq_add` calls with `.dst` set to the tile's VRAM address (as SW_TILES does at story.c:322-326), about 1.2k cycles. VBlank: 3 × (16 + 3) = 57 of `VQ_DRAIN_BUDGET` 86. |
| Rate | One step every 8 frames (7.5 steps/s; one loop is 0.53 s). The left jet goes on the step frame and the right jet on the next frame. |

**Hook.** Call it from `story_update`, in the `if (!btn && PIC_SCENE)` block at story.c:1084, next to
`story_burst_crackle`. The call is something like `story_water_step(story_t)`, BANKED.

It skips a frame, and the phase waits, when any of these holds: `vq_held`, `story_swap != SW_IDLE`, or
`qv_cost + 57 > VQ_DRAIN_BUDGET`. That is the same yielding pattern as `story_burst_step`. A delayed step shows a phase
for one frame longer, which cannot be seen.

When `swpage` loads the next picture, the water table switches with it.

**Rejected: Color-only palette cycling.** By day the water's colour shares its slot with the sky (#b8dcf4, DMG1), so
cycling it would ripple the sky. A slot of its own does not exist (finale_a uses 4 of 4). Palette cycling also changes
colours in hard steps, and DMG cannot do it at all, because BGP covers the whole screen.

### 8. Clouds drifting: OBJ sprites, Color only. Recommended. DMG keeps the still clouds of round 3.

**What moves.**
- FINALE: the three hand-drawn clouds of master.py (`CLOUD_A/B/C`) drift right as 8x16 sprites (the game runs in
  8x16 mode, main_cold.c:191), one pixel every 8 frames (7.5 px/s; about 25 s across the screen).
- OAM x is `base + c`, where `c` is one `story_scratch` byte. It wraps at 256 by itself, so each cloud spends 88 steps
  (about 12 s) off-screen and comes back in from the left. Nothing ever jumps.
- They pass **behind** the Golden Spigot through 3 mask sprites. The masks hold copies of the spigot's own pixels and
  have lower OAM indexes, and on CGB the lower OAM index always wins.
- The masks show only while a cloud is within x 87-119. They are pixel-identical to the BG, so switching them on and
  off cannot be seen.
- At load, on CGB only (`is_cgb`), the 7 BG cloud cells are pointed at the plain sky tile. DMG keeps them.

**Cost.**

| Item | Cost |
| --- | --- |
| OAM | 20-29: 7 clouds + 3 masks. This is the burst's range, free outside the INTRO. |
| OBJ tiles | 56-75: 10 sprites of 2 ids. This is the burst's tile range, free outside the INTRO. 0 BG tiles. |
| OBJ palette | 4 (BURST_PAL, "unused on a cut-scene"): transparent, cream #fff0b0, gold #e8a828, ink #201828. The clouds use cream; the masks use all three. |
| Sprites per line | Worst case 10 on lines 20-21 (3 + 2 + 2 clouds + 3 masks), which is exactly the hardware limit. Otherwise 7. The portrait overlay starts at y 32 (`BURST_FRAME`), so it never shares these lines. |
| ROM | About 320 B of tiles, 8 B of palette, about 30 B of tables and about 100 B of code. All banked. |
| ROM0 | 0 |
| WRAM | 0 new globals; 1 `story_scratch` byte. |
| CPU | About 300 cycles every 8 frames (10 OAM entries). Map writes: 7 cells, once, at load. |

**Hook.** The same `PIC_SCENE` block at story.c:1084: `story_sky_step()`, BANKED. The CGB cell swap goes after the
picture's map is put (`pic_put`, story.c about 942-998). The tiles and palette go in with `set_sprite_data` /
`set_sprite_palette`, as `story_burst` loads its own (gen_story.py 1025-1028).

**Dawn streaks (credits_b).** They are cheap with the same code and only new data.
- STRIP_A (4 sprites) and STRIP_B (3 sprites) drift the same way and pass behind the spigot (3 masks, rows 14-29).
- They pass in front of the sun, which reads as streaks in front of the sun.
- At most 7 sprites per line. About 9 cells go to sky on CGB.
- `gifs/dawn_color.gif` shows it.

**Why DMG keeps still clouds.**
- On DMG, OBJ-to-OBJ priority goes by X (the smaller X wins), so a mask cannot keep a cloud behind the spigot from both
  sides.
- An OBJ set behind the BG shows only over BG colour 0. The sky is colour 1 (BGP 0xE4), so the sky itself would hide
  the cloud.
- The DMG options left are worse:
  - clouds in front of the spigot;
  - a STAT/LYC split that swaps BGP over lines 0-23, with the sky re-indexed to colour 0. That needs a new interrupt
    handler, a re-indexed band, and the CGB palettes reordered.

**Rejected for clouds.**

| Option | Why not |
| --- | --- |
| BG tile frames | A 1-px drift needs a unique tile for every sky cell on the path, about 18 more tiles. finale_a has 1 spare. |
| Scroll (SCX split) | It would scroll the spigot and the bunting in those rows too, and it needs a STAT handler. |

### The GIFs (x3, 32 steps × 133 ms = 4.3 s, 15-26 KB each)

| GIF | What it shows |
| --- | --- |
| `day_color` | FINALE: water and clouds. The clouds start 24 steps in, so cloud A passes behind the spigot. |
| `day_dmg` | FINALE: water only; the clouds stay still. |
| `night_color`, `night_dmg` | INTRO p1: water only (no clouds at night). |
| `dawn_color` | CREDITS: water and the dawn streaks. |

**Flicker check, frame by frame (`motion_check.py` strips, plus counts from `motion.py`).**
- Only the jet pixels and the cloud edges change: 14-38 pixels per step.
- A jet pixel is lit for one step in four and moves down. Nothing toggles on and off in place, and no palette changes.
- The water loops seamlessly (8 cycles).
- **The clouds jump back 32 px when the GIF loops.** That jump exists only in the GIF. The game never jumps.

## Self-audit (gb-pixel-art section 9)

| Check | PASS/FAIL | Evidence |
| --- | --- | --- |
| Hand-placed: what wrote pixels to the delivered file? | PASS | My key grids: the master pieces, `TEX` and `EDITS`/`FINALE_FIX` in compose.py, and the water highlight lists in motion.py. compose.py and motion.py only stamp those lists and copy approved props and sprites. |
| Clean-up pass done by hand | PASS | Clean-up log above: 4 picture fixes, 1 new key. |
| 1x comparison with the quality bar | PASS | The 1x strips in `sheet_round3_round4.png`, against round 3 and the approved props. The navy night house came out of this comparison. |
| Required references read before drawing | PASS | Read in round 3 and still in force: SKILL.md, briefs.md and the figures. "Separate adjacent features by DMG value": Sal's hair is ink on a navy wall. |
| Lint (and portrait check) | PASS | RESULT PASS 11/11, and 11/11 for each water phase. The warnings are listed above, and fewer than in round 3. |
| Colours per tile, palettes, tile count | PASS | 0 clashes. 119/151, 109/117, 145/146, 138/199. Palettes 4/3/4/5, unchanged. |
| Scanline budget (sprites) | PASS | Color clouds: worst 10 on lines 20-21 (at the limit), otherwise 7. Dawn: 7. The stills use no sprites. |
| Squint test at 1x, DMG and CGB-corrected | PASS | Night: spire, Sal and the fountain read first. Day: the spigot, the Spigoteer and Dregs. I fixed Sal's hair merging into the ink house at night. |
| No banding, squares, stray pixels, L-doubles, V-point chins | PASS | The stray hat and antenna are gone. The remaining L-doubles are the 45° gable steps and roof corners, as in round 3. |
| Light direction consistent; flipped sprites still correct | PASS | Dregs flipped in intro_a as before; the highlights stay on the outer side of each jet. |
| Tiles: tiled preview clean | PASS | Texture cells checked in the 1x captures; no seams. |
| Animation: clusters intact, unchanged tiles shared, no wind-up on player actions | PASS | The water changes only its 6 jet tiles. The cloud OBJs are copies of the drawn clouds. |
| Placeholder footprint kept, or changes explained | PASS | All picture sizes, rows 0-12 and the portrait frame are unchanged. |
| Files indexed, ordered, grid-aligned, named | PASS | `pictures/`, `water_phases/phaseN/`, `gifs/`. |
| Engine questions listed with working assumptions | PASS | Hooks, scratch bytes and OAM/OBJ ranges are above; the doubts are below. |

## Deviations

- Clouds drift only on Color. The brief asked for "DMG fit or Color-only". The reasons are above. The project direction
  ("gate Color-only features behind `is_cgb` and leave the DMG path unchanged") covers it.
- At night the right house is navy inside its ink outline. The other houses are ink silhouettes. I did this because the
  skill says "Separate adjacent features by DMG value": with an ink house, Sal's ink hair merged into the wall.

## Doubts

1. Is the cream right house too bright and plain by day? It has one texture cell.
2. The navy night house breaks the all-ink skyline a little. It is the same value the round 3 passage had behind Sal.
3. finale_a has 1 tile spare. Any later FINALE change has to give a tile back.
4. The Color clouds reach exactly 10 sprites on lines 20-21 while one crosses the spigot. Nothing else may use those
   lines in FINALE.
5. intro_a's water stays still because the spigot is gone. Say if a dribble is wanted.
6. The scratch byte (169) and the OAM/OBJ/palette 4 ranges are the burst's. That holds only while the burst stays
   INTRO-only.
