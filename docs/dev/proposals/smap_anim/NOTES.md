# Story-map animations, mockups (Q110). Proposal only: nothing in `assets/`, no engine change, no goldens.

Base: map layout A5 merged (`smap_layout_a5`) and venue round 3 merged (no conflict). A5's map still has plain boxes where the stadium and the space mountain go, so items 4b, 5 and 8 are shown on the round-3 pieces over their own biome ground (`mountain`, `stadium` scenes), everything else on the real A5 map render.

Files (this folder): `gifs/NN_name.gif` one per item, DMG left and Color right, x3, a 160 x 144 view cut from the map, loops exactly, 50 ms per step (3 video frames); `contact_sheet_frames.png` (every distinct state of every item, DMG over Color, x4, labels first); `gifs/strip_*.png` the single strips; `gifs/report.json`, `groups.json`, `combined.json` the numbers below. Sources: `items.py` (every animated tile typed by hand), `anim_lib.py` and `build.py` (compose, preview, measure), `mapctx.py`, `r3dump.py`. Rebuild: `mk_src.py` + `mk_a5.py` of `smap_layout_a5` (scratch `src/`, not committed), `python3 r3dump.py out/an/r3.json`, `python3 -I build.py OUTDIR`.

## The table

Frames = distinct images of one tile. "Tiles / step" = tile images rewritten in VRAM at one step. "ROM" = new tile images stored (not already on the map). B/step = tiles x 16. Cadence in video frames (60 fps).

| # | Item | Frames | Tiles / step | ROM tiles | Cadence | Shared or unique | VRAM per step |
|---|---|---|---|---|---|---|---|
| 1 | Water glints: tiles WA and WB (19 and 22 cells on the map; WF stays flat) | 3 each | 1 (WA and WB offset 6 frames) | +4 | 15 per tile, a step every 6 or 9 frames | shared, cheap: every open-water cell | 16 B |
| 2 | Waterfall FL/FR (2 x 2 cells) + splash pair | 3 (falls), 3 (splash) | 4 falls; 2 splash (6 frames later) | +9 (8 falls, 1 splash ring) | 12 | unique, but only 6 cells exist | 64 B / 32 B |
| 3 | Town fountain jet and basin (PLACEHOLDER, see below) | 3 | 2 or 3 | +5 | 12 | unique | 32-48 B |
| 4a | Town bunting, 7 flags | 3 | 1 or 2 | +6 (P 2, Q 2, end flag 2) | 15, P and Q 6 apart | P, Q shared (3 cells each); end flag unique (it shares a tile with the hall roof) | 16-32 B |
| 4b | Stadium pennants, 2 poles (NEW art) | 3 | 1 | +3 (+1 static pole tile) | 15 | shared by both poles | 16 B |
| 5 | Radar dish, one tile | 4 | 1 | +3 | 15 | unique | 16 B |
| 6a | Lodge chimney smoke | 4 | up to 4 | +10 | 15 | unique; 2 cells over blank grass need their own tile id | 64 B max |
| 6b | Factory, two stacks | 4 | up to 3 (stacks offset 6) | +15 | 15 | unique; 2 new tile ids | 48 B max |
| 6c | Igloo | none | | | | the dome has no chimney (an ice dome with a doorway); nothing added | |
| 7 | Cow tail, two cows (NEW tail art: the cows have none) | 3 | 1 | +6 (2 are the tail at rest) | 12, rests 36 of every 72 | unique; 2 new tile ids | 16 B |
| 8a | Mast lamp, space mountain | 2 | 1 | +1 | lit 60, dim 30 | unique | 16 B |
| 8b | Stadium light-tower lamps | 3 | 1 (both towers, same tile) | +2 | 48 | shared | 16 B |
| | Total | | | **64 images (+1 pole tile)** | | | |

Cheap and shared: 1, 4b, 8b (and 4a's P and Q). Everything else is unique art.

## DMG streaming cost

Only the tiles of what is on screen need animating, so the honest number is per view (peak tiles written in one video frame, with the phases in `items.py`; average bytes per frame over a minute):

| view | peak tiles in one frame | peak bytes | average bytes per frame | tiles per second |
|---|---|---|---|---|
| river top: falls + water | 5 | 80 | 10 | 38 |
| town: bunting + fountain + river water | 6 | 96 | 9 | 33 |
| lodge: smoke + mill-pond water | 5 | 80 | 6 | 22 |
| factory: both stacks | 3 | 48 | 6 | 21 |
| milk bar: two tails + lake water | 2 | 32 | 4 | 15 |
| mountain: dish + lamp | 2 | 32 | 1.4 | 5 |
| stadium: pennants + lamps | 2 | 32 | 1.4 | 5 |
| everything at once (cannot happen) | 20 | 320 | 31 | 115 |

Rule of thumb for the programmer to confirm: about 10 tiles (160 B) fit one VBlank with an unrolled copy, so the busiest real view (the town) uses about 60% of a VBlank on its worst frame and under 10 B on an average one. Steps are never aligned on purpose (phases 0, 6, 12 frames), so the average is what a walking frame sees most of the time. If Sal's scroll streaming already fills VBlank on a frame, the scheduler can skip or delay any animation step by a frame or two without a visible cost (the steps are 6 to 48 frames apart). Color writes the same tile bytes to bank 0 only; attributes do not change (one exception: the two cells over the lodge puff change their palette entry to `lodge`, an attribute-only change).

## Flicker check (owner rule)

Measured on every consecutive pair of GIF frames, wrap included, at 1x, DMG and Color; and every distinct state looked at in the strips.
- Largest area changing in one step: 0.34% of the view (water), others 0.2% or less. No large-area change, no white flash.
- Lights: mast lamp 1 pixel, centre index 0 to 1 and back, 1.33 changes a second; stadium lamps 4 pixels of the head, index 0 to 1, 1.25 changes a second per head (0.62 per pixel). One shade step (80 of 255 on the DMG grey; the Color step is a colour step, see doubts).
- Water, smoke: one-shade-step pixels, up to 5 pixel changes a second for the falls streaks (they are moving water, not a light: see doubts).
- Shape moves (flags, dish, tail) change a few pixels by up to 224 in grey (ink against sky) but they are 1 to 3 px moves of at most 0.09% of the screen, at most 4 changes a second per pixel.

## Per item notes

1. WA and WB are the two glint tiles of the dark DMG water; each 2-pixel stair of glints slides 1 px left, back, 1 px right, back inside its tile (never across the edge). The light DMG water set (`WA_L`, `WB_L`) takes the same shifts at the same cost; not rendered.
2. Falls: streaks fall 5 rows a step over the 15 flowing rows (the 16th row is the pool edge and stays), exactly 3 steps to close the loop. All columns share one speed (that is what closes the loop in 3 frames). Splash: a small centred ring (new tile C) and the two existing arcs A and B in turn.
3. Fountain: PLACEHOLDER on today's fountain (another artist is redrawing it). Four existing sparkle pixels of the jet blink in two groups, and the basin glint slides one pixel. Nothing is added to the art; the whole animation is 5 tiles and can be dropped or replaced by the new artist's own. A cheaper version: two frames, jet only (about 3 tiles).
4a. The bunting string stays; the lower two rows of each flag swing a pixel; neighbouring flags swing opposite ways.
4b. The round-3 stadium has no pennants. Two flagpoles stand on the back stand's roof line with one red (index 1) pennant each; at rest the art is new (1 flag tile, 1 pole tile). If the owner does not want added art, drop 4b.
5. Dish: face-on, turning, edge-on, back (darker inside, pin on the other side). Pin and post stay on their column; one 8 x 8 tile.
6a/6b. Today's static puffs (lodge, both factory stacks) are frame 0, so the resting art is unchanged. Puffs rise and thin, a new one swells at the cap. The factory's left stack has log piles right above it, so its smoke drifts left of them. Over blank grass the cells need their own tile id (counted in the table).
7. The cows have no tail today; a 4-pixel tail with a pink tuft is added hanging, then it swings out right and back, resting between flicks. The second cow is 18 frames behind the first.
8. Lamps: the lamp centre is index 0 on a ring of ink. Stadium head lamps are index 0 in an ink grid.

## Self-audit (gb-pixel-art)

| Check | PASS/FAIL | Evidence |
|---|---|---|
| Hand-placed | PASS | every animated tile and pixel run is a typed grid or run list in `items.py`; the scripts compose, preview, lint, measure and write GIFs |
| Clean-up pass by hand | PASS | log: falls streaks adjusted so no two columns touch (rows 3 and 6 of FL F1 checked); bunting end flag kept inside its tile; smoke puffs kept in single-pixel-wide clusters of 2 or more; lodge puff cells recoloured by palette instead of pixel; first dish draft (3 frames) lacked a back view, added frame 3 |
| 1x comparison with the quality bar | PASS | each GIF view is 1x map context beside the existing town, igloo and milk bar art; flags and puffs match the weight of the existing static puffs |
| References read first | PASS | animation.md ("keep unchanged 8x8 tiles identical across frames so they share VRAM"), environments.md section 11, hardware.md section 8, linework.md, light-and-form.md, fx-and-ui.md, palettes.md |
| Lint | PASS | `gb_art_lint.py` on `new_tiles_dmg.png` (64 new tile images in one strip, scratch): PASS; 7 L-double warnings at tile joins of the strip (dish rim and pole pixels meeting across the strip's tile edges, not in the map) and 29 orphan pixels (glints, smoke wisps, sparkles: intended) |
| Colours per tile, palettes, tile count | PASS | no new palette; 64 new images, +1 pole tile, 7 new tile ids on the map; only the 2 lodge-smoke cells change palette attribute; window palette cap of 8 not changed by the other cells |
| Squint test | PASS with doubts | pennants and mast lamps are small by design; see doubts |
| No banding, squares, stray pixels | PASS | orphans are the intended glints |
| Animation: clusters intact, unchanged tiles shared, no wind-up on player actions | PASS | clusters move whole; unchanged rows identical; nothing is player-triggered |
| Light direction | n/a | |
| Footprint kept | PASS | static art unchanged except where marked new (4b flags and poles, 7 cow tails, 3 fountain frame 0 unchanged) |
| Engine questions | listed below | |

Deviations from the skill, in its words: environments.md 11 says "bake both into one short looping tile animation (4-8 frames)", "highlight blobs that grow and shrink like circles" and, for waterfalls, "streaks ... at varied lengths and speeds, edges that jitter by 1 px". The water here is 3 frames of sliding glints (the shared glint tiles only), and the falls streaks share one speed and do not jitter, to keep the cost at 3 frames and close the loop. It is a cost choice, not a taste one.

## Questions for the programmer

1. Can the map engine rewrite 1 to 6 background tile images per VBlank from a table (tile id, frame list, period, phase) while Sal scrolls, and how many bytes does the DMG streaming leave on its worst frame? Assumed: yes, about 6 tiles (96 B).
2. Animated tiles that start from the shared blank grass tile (lodge smoke, factory smoke, cow tails) need their own tile ids in the map. Is there margin in the DMG tile window (A5: worst window 133 of 176) for 7? Assumed: yes.
3. Can animation be switched off for tiles that are off screen? Assumed: only on-screen ids are scheduled.

## Doubts

- The falls streaks change 5 times a second per pixel. It is a motion, not a light, and the area is tiny, but if the owner reads the no-flash rule strictly the period can go from 12 to 18 frames at no cost.
- Stadium lamps: on Color the one-step dim is white to red (index 1 of the stadium palette), small but a colour jump. The mast lamp is yellow to grey-blue.
- Radar: after the back view the dish jumps to face-on (4 frames only); 6 frames would smooth it for +2 tiles.
- Factory smoke is the dearest item (+15 images for two stacks). One stack (right) costs 7.
- The pennants and cow tails are new art on pieces the owner picked; the tail is the smallest possible, the pennants add 2 poles to the stands.
- I stepped through the numbers frame pair by frame pair and looked at every distinct state, not at the GIFs in a browser.
