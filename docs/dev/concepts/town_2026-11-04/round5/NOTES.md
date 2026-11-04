# Town, round 5 (2026-11-04): consistency pass

This round changes only what the owner named; everything else is round 4. It is a concept only: no changes to `src/`,
`tests/` or the goldens. The pictures were checked in the scratch ROM (`out/town/st`) on Color and DMG.

`sheet_round4_round5.png` compares round 4 and round 5 in the engine: Color over DMG, at 1x and x3.

## Changes

| # | Owner's note | Round 5 |
| --- | --- | --- |
| 1 | "you altered the roof of the tavern ... the roof was not the problem" | Round 3's tavern roof is back, pixel for pixel (rows y 32-71 of the tavern match round 3's exactly). The clock-tower note is now fixed on the tower itself. Its body is 11 rows taller, so the cornice (y 28) and the clock (y 32-40) stand above the tavern's ridge (y 32). The spire is redrawn shorter and steeper (8 rows, tip y 20) so it clears the night moon. The clock face, windows and door are unchanged. |
| 2 | The light building on the right matches nothing | The right house is now the plain `GABLE` piece, with the same wall (`B`) and windows (`L`) as its neighbours at every time of day: lilac by day, ink at night, violet at dawn. The front is plain and the windows centred. Readability is fixed on the characters' edges, not on the wall (see below). |
| 3 | The coffee booth is only in the last picture | **Removed from credits_b.** The reasons are below. |
| 4 | Bricks by day but not at sunset | The same `X` brick hints sit on the same 7 cells at every time, now visible in all three: sandstone by day, faint navy on the ink walls at night, and stone mauve (#b898a8) on the violet walls at dawn. There are no other textures. |
| 5 | "move the windows down from the awning a little" | The tavern's shop window now starts 3 rows lower. Under the awning's ink edge (y 71) there are 2 rows of clear wall (y 72-73), then the window frame (y 74), the glass (y 75-82) and the bottom frame (y 83). The patrons moved down with the glass. I read "windows" as the shop window only, because the upper windows are above the awning, so I did not make a second version. |

**Why the coffee booth was removed rather than added to every picture.**
- It stands at x 136-159, y 47-87. That is exactly where Sal stands at night and Dregs by day, so the booth would sit
  behind both of them.
- It is drawn in the fixed HUD palette, so it cannot take the night and day lighting.
- Sal's and Dregs's tiles cannot share a tile with it, because each tile has one palette.
- finale_a has no tile to spare.

The gag it served is the narrator line "THE SASQUATCH SELLS COFFEE NOW." The text still works without the picture.
docs/story.md:1159, the CREDITS picture description, still says "the Sasquatch's coffee stand opens at the right". It
needs that clause dropped when the pictures are imported.

**Knock-on fixes, all forced by the five changes above. Logged in `tools/compose.py` and `tools/keys.py`.**
- **Sal at night:** his ink hair met the now-ink wall. I added a moonlit rim (new key `v`, the sky's navy, DMG 2),
  hand-placed on the wall pixels around his hair: the row above it (corners left open) plus one column on each side.
  It is 12 pixels per night picture.
- **Spire at dawn:** the spire is now the wall's violet (it was rust). In the taller tower the spire and the wall share
  a tile row, and rust and violet are both DMG 2. By day the spire was already the wall's lilac, so dawn now matches day.
- **Spire top:** the top 3 rows have no lit edge. The moon's edge (DMG 1) shares their cell at night.
- **FINALE (136, 69):** the tip of Sal's hat brim is now ink. Gold and lilac are both DMG 2 in that cell.
- **CREDITS, Dregs's jacket:** now `B` (dawn violet), as FINALE's jacket is the day wall's lilac. The lower shop window
  is behind his chest, and the old mauve and the gold glass are both DMG 1. His ink outline keeps the jacket off the
  wall.
- **CREDITS, left jet:** its ink outline at y 50-52 was restored, so the fountain is the same in every picture.

## Consistency audit

Each cell gives the number of pixels that differ from the master in that picture, followed by the keys of whatever
covers them. 0 means identical keys, so only the lighting changes. Source: `tools/audit.py` and `tools/audit_fountain.py`.

| Building, prop or texture | intro_before | intro_a | finale_a | credits_b |
| --- | --- | --- | --- | --- |
| Left gable house | same | same | same | same |
| Clock tower | same | same | same | same |
| Tavern (roof, windows, banner, awning, shop window) | same, except 8 px of crowd heads | same, except Dregs | same | same, except Dregs |
| Tavern patrons (2) | same | same | same | same |
| Right house | same, except Sal and his rim | same, except Sal and his rim | same, except Sal and Dregs | same |
| Market hall | same, except the fountain | same, except the fountain | same, except the fountain and Sal | same, except the fountain |
| Fountain basin and jets | reference | spigot gone, jets off (story) | same, except Sal and his glass | same, except the spigot drips (story) |
| Brick hints (7 cells) | same | same | same | same |
| Bunting | same | same | same | same |
| Cobble plaza | same, except the crowd | same, except the crowd | same, except the crowd | same, except the suds and mop |
| Coffee booth | none | none | none | none |

**Exceptions** (all deliberate):
- **Lighting:** all key colours.
- **Story props:** Sal, Dregs, the crowd, the spigot's state, the drips, the suds and mop, and Sal's rim (a lighting
  edge on Sal).
- **The sky changes with the time of day:**
  - Night has the moon and stars.
  - Day has the cream clouds.
  - Dawn has the sun and the gold streaks.
  - The cloud pixels are in the master at every time, but they take the sky's colour at night, and the day clouds do
    so at dawn.

  The owner liked the clouds, so I left them alone. Say if the sky must be identical too.

## Counts (check.py = gen_story's packing; the scratch ROM builds; ROM0 443 B free, unchanged)

| Picture | Round 5 tiles / limit | Round 4 | Palettes |
| --- | --- | --- | --- |
| intro_before | 118 / 151 | 119 | 4 |
| intro_a | 107 / 117 (+30 trail) | 109 | 3 |
| finale_a | **146 / 146** (0 spare) | 145 | 4 |
| credits_b | 128 / 199 | 138 | 5 (Option A, as before) |

There are no tile clashes. The water phases 1-3 give the same counts, because the jets did not move. They are
regenerated in `water_phases/`, and no new GIFs were made.

**Lint:** RESULT PASS on all 11 files: the 8 pictures and the 3 masters. Each water phase also passes on all 11.

L-doubles went up:

| Picture | Round 4 | Round 5 |
| --- | --- | --- |
| intro_before | 44 | 70 |
| intro_a | 40 | 69 |
| finale_a | 73 | 77 |
| credits_b | 3 | 27 |

All the new ones are on the right gable and the new spire. At night those are ink on ink, and their courses meet the
outline, so the stair steps count as L-doubles. The approved left gable already produced the same count. Orphan pixels
went down (35 to 33 and 39 to 30).

## Self-audit (gb-pixel-art section 9)

| Check | PASS/FAIL | Evidence |
| --- | --- | --- |
| Hand-placed | PASS | My grids. Restoring round 3's tavern is a copy of approved hand work. The new spire rows, the window rows, Sal's rim and the 4 jet-outline pixels are listed by hand. compose.py only stamps them. |
| Clean-up pass done by hand | PASS | The knock-on fixes above: 6 edits, each with a reason. |
| 1x comparison with the quality bar | PASS | The 1x strips against round 4. After that comparison I added Sal's rim and restored the jet outline. |
| Required references read | PASS | Round 3, still in force. "Separate adjacent features by DMG value" led to Sal's rim and the hat-tip and jacket fixes. |
| Lint | PASS | 11/11 PASS. The L-doubles are explained above. |
| Colours per tile, palettes, tile count | PASS | 0 clashes. 118/151, 107/117, 146/146, 128/199. |
| Scanline budget | PASS | The stills use no sprites. |
| Squint test, DMG and Color | PASS | Night: the spire, the moon, the fountain and Sal (rim) read. Day: the spigot, the Spigoteer and Dregs (by his outline). |
| No banding, squares, strays, L-doubles | PASS | No new strays. The L-doubles are the silhouette stairs, as on the left gable. |
| Light direction | PASS | Lit edges are on the left (moon and sun on the left), except the spire's top 3 rows. |
| Tiles: tiled preview | PASS | Texture cells checked in the 1x captures. |
| Animation | PASS | The water phases change only the 6 jet tiles. |
| Footprint kept | PASS | Picture sizes, rows and the portrait frame are unchanged. The tower piece is now 16 x 68 at (16, 20). |
| Files named | PASS | `pictures/`, `water_phases/`, `tools/`. |
| Engine questions | PASS | None new. The motion plan is on hold. |

## Doubts

1. finale_a is at 146/146 with no spare tile. Any later FINALE change must give a tile back.
2. The sky still differs by time of day (stars and moon, clouds, streaks).
3. Sal's navy rim is a small halo. Check that it reads as moonlight and not as a glow.
4. The dawn spire is now violet instead of rust. That changes the dawn look slightly; it was forced by the tile clash.
5. Dregs's jacket in CREDITS is the wall's violet. It separates only by his ink outline, as in FINALE by day.
6. story.md's CREDITS description still mentions the coffee stand.
