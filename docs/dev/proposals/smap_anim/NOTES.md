# Story-map animations, mockups (Q110, second pass on the APPROVED art). Proposal only: nothing in `assets/`, no engine change, no goldens.

## What changed since the first delivery (owner's words)

"all animations look good, but bring back old flag and stadium that I approved. and the new igloo I approved. And maybe use a different, not tan palette for the lodge smoke. Don't like the stadium lamp effect." and "the fountain water doesn't match the revised fountain. Several things like that in the art pass."

So every animation now sits on the approved pieces, on the real A5 map render (no piece needed its own ground). Merged `--no-ff` into this branch, no conflicts in any: fountain round 3 (`worktree-agent-a9bde35169ec4c32e`), approved stadium (`...ad92c4ce81f826634`), approved igloo option 1 (`...a326fa4ec4c6f3e7f`), airbase round 4i (`...a958d884767ee8afe`), milk bar round 4i (`...a742552fa3a9454c1`), and A5 with `SMAP_LOG=v1` (brown logs), and then the falls seam fix (`worktree-agent-a9eca06ceee777aa2`, 3rd commit: the four falls tiles retyped, 8 px wide like the stream, side edges are the bank's own rim, no index 3). Dropped: the stadium lamps (8b) and the pole pennants (4b of the first delivery). Added: wavy stadium flag (4b), igloo chimney smoke (6c).

Files: `gifs/NN_name.gif` one per item, DMG left and Color right, x3, a 160 x 144 view cut from the map, loops exactly, 50 ms per step (3 video frames); `contact_sheet_frames.png` (every distinct state of every item, DMG over Color, labels first); `gifs/strip_*.png` the single strips; `gifs/report.json`, `groups.json`, `combined.json` the numbers. Sources: `items.py` (every animated tile typed by hand), `anim_lib.py` and `build.py` (compose, preview, measure), `mapctx.py` (loads A5 with the approved pieces), `r4dump.py` + `scenes/*.json` (the approved pieces as cell lists; stadium has its 3 flag frames), `anim_stub.py`. `r3dump.py` is obsolete. Rebuild: `mk_src.py` + `mk_a5.py` of `smap_layout_a5` (scratch `src/`, not committed), `python3 -I build.py OUTDIR`.

Wiring notes: the space mountain / airbase is pasted at cell (6,36), 3 cells west of its dump position, so its two palettes stay out of the windows holding the tea garden and cow field. The milk bar roof variant was not chosen in the brief; I used the round-4h A base.

## The table

Frames = distinct images of one tile. "Tiles / step" = tile images rewritten in VRAM at one step. "ROM" = new tile images stored. B/step = tiles x 16. Cadence in video frames (60 fps).

| # | Item | Frames | Tiles / step | ROM tiles | Cadence | Shared or unique | VRAM per step |
|---|---|---|---|---|---|---|---|
| 1 | Water glints: tiles WA and WB (19 and 22 cells; WF stays flat) | 3 each | 1 (WA, WB offset 6 frames) | +4 | 15 per tile | shared, cheap | 16 B |
| 2 | Waterfall 2 x 2 cells + splash pair (seam-fix tiles: bank rim at the sides, no brown) | 3 | 4 falls; 2 splash | +9 | 12 | unique, 6 cells | 64 B / 32 B |
| 3 | Town fountain: two side streams (2 cells) + basin glints (2 cells), round 3 art | 3 streams, 2 basin | up to 2 | +6 | 12 | unique | 32 B |
| 4a | Town bunting, 7 flags | 3 | 1 or 2 | +6 | 15, P and Q 6 apart | P, Q shared (3 cells each); end flag unique | 16-32 B |
| 4b | Approved stadium: wavy flag, 2 cells | 3 | 1 or 2 | +4 | 9 | unique | 16-32 B |
| 5 | Radar dish (airbase 4i), one tile | 4 | 1 | +3 | 15 | unique | 16 B |
| 6a | Lodge chimney smoke, WHITE (see palette) | 4 | up to 2 | +10 (8 puff images, 2 cap cells with the tan puff erased) | 15 | unique; 2 cells over blank grass need own tile id | 32 B max |
| 6b | Factory, two stacks | 4 | up to 3 | +15 | 15 | unique; 2 new tile ids | 48 B max |
| 6c | Igloo (option 1) chimney smoke, 1 cell | 4 | 1 | +3 | 15 | unique | 16 B |
| 7 | Cow tails, pasture cow and one more (milk bar 4i) | 3 | 1 | +6 (2 are the tail at rest) | 12, rests 36 of 72 | unique; 2 new tile ids | 16 B |
| 8a | Mast lamp (airbase) | 2 | 1 | +1 | lit 60, dim 30 | unique | 16 B |
| | Total | | | **67 images** | | 6 new tile ids (lodge 2, factory 2, cows 2) | |

Dropped from the first table: 8b stadium lamps, pole pennants. Cheap and shared: 1, 4a (P, Q).

Lodge smoke palette: the existing `water` palette (idx 0 = the grass colour b0d080, idx 1 = e8f0d8 foam white), already in every window round the lodge, so no window gains a palette. It is used only on the two cells ABOVE the chimney, (58,19) and (59,19) (y 152-159; attribute-only change). The chimney cap row (y 167) shares its two cells with the old tan puff (y 163-165), and no palette already in those windows has grass as index 0, a near-white index 1 and the lodge's ink as index 3, so the smoke leaves those cells: the cap cells keep the `lodge` palette and the cap is exactly as approved (same pixels, same colour). The old tan puff is erased from the cap cells (those two tile images change, counted in ROM) and the rest puff now floats at y 157-159, 7 px above the cap. If the owner prefers the puff to touch the chimney, the only palette-neutral way is to keep the tan puff on the cap cells; that is a one-line switch in `items.py`.
Igloo smoke uses the igloo's own ice-blue shades (the piece's palette), as its art does.

Not animated: the lawn cow (its sign pole sits 1 px from the tail space); the stadium pennant string (see below).

Pennant string estimate (not done, not cheap): the arch is 14 cells, each its own image at rest, so a flutter of 3 frames means about 14 x 2 = 28 extra tile images and up to 14 tiles per step. Skipped as the brief said.

## DMG streaming cost

Peak tiles written in one video frame, average bytes per frame, per view (phases in `items.py`):

| view | peak tiles in one frame | peak bytes | average bytes per frame |
|---|---|---|---|
| river top: falls + water | 5 | 80 | 10.1 |
| town: bunting + fountain + water | 5 | 80 | 9.8 |
| lodge: smoke + water | 3 | 48 | 4.3 |
| factory: both stacks | 3 | 48 | 5.6 |
| milk bar: tails + water | 2 | 32 | 3.9 |
| airbase: dish + lamp | 2 | 32 | 1.4 |
| stadium: flag | 2 | 32 | 3.6 |
| igloo: smoke + water | 6 | 96 | 11.2 |
| everything at once (cannot happen) | 20 | 320 | 33.3 |

Assumed for the programmer to confirm: about 10 tiles (160 B) fit one VBlank. The worst real view (igloo, 6 tiles, 96 B) is about 60% of that; averages are about a tenth. Steps are never aligned on purpose, and any step can slip a frame or two if scroll streaming needs the VBlank. Color writes the same tile bytes to bank 0; attributes do not change except the 2 lodge puff cells.

## Flicker check (owner rule)

Every consecutive GIF frame pair (wrap included), DMG and Color, plus a look at every distinct state.
- Largest area changing in one step: 0.34% of the view (water); all others 0.2% or less. No large change, no white flash.
- The only light left is the mast lamp: 1 pixel, one shade step, 1.33 changes a second (about 1 blink per 1.5 s). Stadium lamps are gone.
- Water and falls streaks are moving water, not lights (falls: 5 changes a second per pixel, see doubts). Smoke and fountain: one-shade pixels, 2 to 3.3 changes a second per tile.
- Stadium flag: the approved 8 fps wave, 6.67 changes a second on about 20 pixels, 0.11% of the view. A motion of a cloth, not a light, but the fastest item; period 9 can go to 12 (5 a second) if wanted.
- Shape moves (bunting, dish, tails): 1 to 3 px moves, at most 0.09% of the screen.

## Palette check

Window cap is 8 palettes per 21 x 19 cells. Worst window on this map is 9, at window (11,3), caused by the approved stadium's PARK + STADIUM palettes joining the town's (it exists with no animation; the 18-entry palette table needs a 19th entry or a merge). Flagged for the palette plan; none of the animation changes add a palette.

## Self-audit (gb-pixel-art)

| Check | PASS/FAIL | Evidence |
|---|---|---|
| Hand-placed | PASS | every animated tile is a typed grid or run list in `items.py`; scripts only compose, preview, measure, write GIFs |
| Clean-up pass by hand | PASS | falls streaks no two columns touching; lodge puff recoloured by palette; stadium flag frames adjusted to the approved flag shape; dish back view added |
| 1x comparison with the quality bar | PASS | views are 1x map context on the approved art |
| References read first | PASS | animation.md, environments.md 11, hardware.md 8, linework.md, light-and-form.md, fx-and-ui.md, palettes.md |
| Lint | PASS with notes | `gb_art_lint.py` run on the first-delivery strip of new tiles; orphan pixels are intended glints and wisps; not re-run on the 67-tile strip, only compared by eye |
| Colours per tile, palettes, tile count | PASS with a flag | no new palette; 67 new images, 6 new tile ids; window worst 9 (pre-existing, approved stadium) |
| Squint test | PASS with doubts | mast lamp and fountain glints are small by design |
| No banding, squares, stray pixels | PASS | |
| Animation: clusters intact, unchanged tiles shared | PASS | |
| Footprint kept | PASS | static art of every approved piece unchanged; only cow tails are new art |
| Engine questions | listed below | |

Deviation from the skill, in its words: environments.md 11 says "bake both into one short looping tile animation (4-8 frames)", "highlight blobs that grow and shrink like circles" and, for waterfalls, "streaks ... at varied lengths and speeds, edges that jitter by 1 px". Water here is 3 frames of sliding glints and the falls share one speed with no jitter, to keep cost at 3 frames and close the loop. A cost choice, not taste. I also did not re-run the lint on the final tile strip (see audit).

## Questions for the programmer

1. Can the map engine rewrite 1 to 6 background tile images per VBlank from a table (tile id, frame list, period, phase) while Sal scrolls, and how many bytes does DMG streaming leave on the worst frame? Assumed 6 tiles (96 B).
2. Tiles that start from the shared blank grass tile (lodge, factory, cows) need their own ids: 6 new. Margin in the DMG tile window? Assumed yes.
3. Can animation be skipped for off-screen ids? Assumed only on-screen ids are scheduled.

## Doubts

- Igloo smoke cannot rise above the piece (nothing above it in the art), so it swells in place; the owner may want a bigger chimney rise.
- Falls streaks change 5 times a second per pixel; period 12 can go to 18 at no cost.
- Fountain animates only streams and basin glints; the jet art is the owner's round 3 and was not changed.
- Radar jumps from back view to face-on in 4 frames; 6 frames would smooth it for +2 tiles.
- Factory smoke is the dearest item (+15 images); one stack costs 7.
- Lodge smoke floats 7 px above the cap (the cap keeps its colour); the puff no longer touches the chimney at rest.
- I checked frame pairs numerically and looked at distinct states and zoomed frames, not the GIFs in a browser.
