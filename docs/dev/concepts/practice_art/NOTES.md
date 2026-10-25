# Practice screen art, 3 style-setting proposals (Quick Draw, Milk Run, Taiko Pour)

Proposals only. Nothing under src/ or assets/ was touched, nothing committed. Sources and the build scripts are in `src/`.

## What each picture is
| Picture | Read at a glance | Palette (CGB, idx0 lightest .. idx3 darkest) | Tiles, art only 64x48 | Tiles with own frame 80x64 (exact / flips merged) |
|---|---|---|---|---|
| Quick Draw | Sunset street duel: the Kid (hat, serape) and Sal each draw a soda bottle, Sal's spray reaches the Kid; saloon sign (a bottle on a board) on a post, mesas, low sun | f8e8b8 / e8a050 / b04830 / 281830 | 41 | 49 / 49 |
| Milk Run | Sal on the bike, speed lines, a crate in the air with its shadow, a milk bottle ahead, cottages and a kerb | f8f0d8 / 90b0c8 / d03848 / 201828 | 40 | 48 / 48 |
| Taiko Pour | Sal on a tatami stage pouring a stream from the teapot into the cup, a taiko drum, a lantern, petals, bamboo blind | f8f0d8 / f0a898 / 409078 / 282838 | 42 (40 merged) | 50 / 48 |

RGB555 words are in each `<name>.pal.txt`. All channels are multiples of 8. DMG: the indices are the shades (BGP 0xE4).

## Style choices (meant to carry to all 13)
- One scene, one hero action, one prop that names the game, a hint of place. No text.
- Value plan: idx0 and idx1 hold sky, walls and floors; idx2 holds mass (roofs, doors, stage, mesas); idx3 is outline and the darkest shadows only. Characters and interactables get full idx3 outlines. Scenery is outlined in idx2 (Milk Run houses), so the rider is the darkest thing on the screen.
- A walkable floor gets a bright top edge (Quick Draw lip, Taiko stage lip).
- Shared outline colour: idx3 is a deep blue-purple in all three (281830, 201828, 282838). Suggest keeping that for all 13 so the Practice screen reads as one set.
- Light from the top left. Ramps go warm and light to cool and dark.
- The owner's own art is reused as the cast, not redrawn: Sal (bartender fill pose and spig draw pose), the Kid (kid.txt draw pose), the bike, crate, bottle, teapot and cup. Only the index mapping per picture changed (for example skin to idx0 or idx1). The sets, props and spray are new and hand-typed.
- Border: I propose the art carries its own 1-tile frame ring (8 hand-typed tiles, lit top and left, shaded bottom and right, same four indices as the picture, so it costs no extra palette). It makes the picture read as an object on the dark wall. The game's own frame is cheaper (art 64x48, 8 fewer tiles) but its colours come from the wall palette, so the picture sits in a flat dark box. See `frame_compare_own_vs_game_*_x4.png` and `frame_compare_art_x8_*.png`. The "game frame" in those is a MOCK I made (dark wall band, one cream rule), not the real tile.

## Files
- Per picture: `<name>.txt` (80x64 house ASCII with frame), `<name>_inner.txt` (64x48), `.png` and `_inner.png` (indexed), `_x8_cgb.png`, `_x8_dmg.png` (and `_inner_` versions), `.pal.txt`.
- `in_screen/<name>_in_practice_{cgb,dmg}_x4.png`: pasted into a real gbtest-style screenshot (PyBoy via tests/ helpers) of the Practice list with that game selected, columns 1-10, rows 6-13.
- `frame_compare_*`, `compare_1x.png` / `compare_2x.png` (the three beside the owner's Sal and the Emma concept).
- `screens/`: the raw list screenshots used.

## Skill self-check
| Check | Result | Evidence |
|---|---|---|
| Hand-placed: what wrote the pixels | PASS with a caveat | Scene grids were typed by me as rows and runs (sun, mesas, houses, drum, stage, sign), then Python only pasted the owner's finished sprites (flips by hardware rule) and my typed blocks, and transcribed the grid into PNGs. No fills by shape formula, no outliner, no filters. The 8 frame tiles are typed text. The caveat: the sun and drum runs were written by me from circle estimates, and the composer script (`*_compose.py`) places typed runs by loops. I judge that allowed; the owner may judge otherwise. |
| Clean-up pass by hand | PASS | Log: QD bottle neck and spray redrawn (a ragged flipped neck and 6 scattered pixels became a 3-row neck plus three 1 px rays), QD pebble L-triple to a pair, QD scattered drops removed, TK stream replaced by a straight 2 px stream from the spout, TK drum eye-like dark pupil to pink core with a cream highlight, TK blind slat added at the right edge to remove a 2x2 gap, MR houses re-outlined in idx2 (they fought the rider), MR crate moved off the houses, QD saloon building and MR/TK first attempts dropped (read as a vending machine / a pot). |
| 1x comparison with the quality bar | PASS, mine is not above it | `compare_2x.png` with Sal and Emma. The reused sprites match by construction; my backgrounds are plainer than the owner's igloo-grade detail and Taiko's teapot has no spout of its own. |
| Required references read before drawing | PASS | SKILL.md; environments.md, linework.md, light-and-form.md (tiles/backgrounds row); palettes.md; hardware.md. Quotes below. Figures 06, 09, 16, 18 looked at; 10, 14, 15 not opened. |
| Lint | PASS on all, warnings noted | See lint lines below. |
| Colours per tile, palettes, tile count | PASS | 1 palette each; tiles 49 / 48 / 50 with frame (limit 80, aim 56), 41 / 40 / 42 without. |
| Scanline budget | n/a | Background art, no sprites. |
| Squint test, DMG and CGB | PASS | Hero and prop separate in all three. QD: figures against sun/sky. MR: the black rider is the darkest mass. TK: Sal, pot, drum. Weakest is MR on DMG (road and houses are close grays). |
| Banding, squares, strays | PARTIAL | My isolated 2x2 check: remaining 2x2s are the owner's bike hubs and the Kid's serape hem. The frame is flat strips by design (hard moulding), the sunset bands are deliberate stylised stripes. L-double warnings are in the owner's sprites and at deliberate rectangle corners. Orphans: QD spray rays and drops (deliberate), eyes and bolts. |
| Light direction | PASS | Top left. Sal and the Kid are the owner's flip-safe sprites. |
| Tiled preview | not run | Backgrounds are scenes, not repeating tiles (the wall and floor are single-use). |
| Engine questions | below | |

Quotes from the required files (one per file):
- SKILL.md: "Decide every pixel yourself. Every pixel in a delivered asset must come from your own decision, recorded in a grid or pixel list you wrote."
- environments.md: "Play-field backgrounds stay in shades 0-1; walkable and solid things get 2-3 with a bright top edge; characters and interactables get full outlines."
- linework.md: "Every pixel in a delivered asset is a decision you made, recorded in a grid or pixel list you wrote." (section 7)
- light-and-form.md: "Background objects: shade 3 only for the deepest shadows; walls and solid boundaries may use it structurally."
- palettes.md: "In every CGB palette keep index 0 lightest through index 3 darkest" (and "Approve the DMG version first").
- hardware.md: "Report the unique-tile count of every scene and stay inside the budget the programmer gives you (engine)."

Lint lines (CGB, bg): quick_draw 80x64, 4 colours, 49 tiles, PASS (1 isolated 2x2, 15 L-doubles, 9 orphans); milk_run 48 tiles, PASS (2 squares, 15 L-doubles, 4 orphans); taiko_pour 50 tiles (48 merged), PASS (14 L-doubles, 10 orphans).

## Questions for the programmer
1. Practice list, the picture frame: does the picture's 10x8 tile block get its own CGB palette (one BG palette per picture, 8 palettes total allowed)? Art assumes palette slot per picture, idx0 to idx3.
2. The list text currently runs to column 12 (MARSHMALLOWS, BATTERY SORT). My composites paste the picture over columns 1-10 rows 6-13 as briefed, so the right end of some names pokes out beside it. Art assumes the list layout changes (text moves or the picture sits elsewhere).
3. Is there a real 1-tile frame tile for the game-frame option? The mock I used is not it.
4. Does a 10x8 block of unique tiles have to be loaded on selection (swap per game) or all 13 resident? Art assumes swapped on selection, at most 80 tiles.

## Uncertain / not checked
- `assets/art/practice/README.md` does not exist in this worktree, so I used only the brief and src/mg_list.c. The "patron redraws in docs/dev/concepts/" are not in the worktree; I used /workspace/docs/dev/concepts/emma_front_v2.txt as the bar.
- No colour-corrected (SameBoy) preview was made; the CGB previews are the raw RGB555 expansion, like the goldens. Real CGB glass is paler, and the cream/amber pairs of Quick Draw are the ones to check on that.
- Not run: make test, make check (no game code changed).
- The Kid's face and Sal's face sit on one palette entry (cream) in Quick Draw; at 1x they read as faces but are plain.
- Milk Run's rider is the owner's small overlay (cap and face), so at this size the rider is a black blob with a cream face. A bigger bike would need new art.
- Taiko Pour: the teapot sprite has no real spout; the stream leaves from its side next to the nub.
- I did not star-test the other 10 games' palettes; the three here were chosen to differ in hue while sharing cream and a deep blue-purple idx3.
