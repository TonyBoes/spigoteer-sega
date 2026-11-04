# Town, round 3 (2026-11-04): cleanup pass

Owner on round 2: clean up the buildings (windows, doors, the lines between buildings; the tavern's thin door goes, the
tower's door serves the tavern), put something in the sky, use Dregs's new design everywhere, legs always showing.

- **Sheet:** `sheet_round2_round3.png`. Each picture is round 2 | round 3, Color over DMG, x3, with 1x strips at the top. Both sets are captures from scratch ROMs (`out/town/st`, picture rows).
- **Concept only:** nothing under `src/`, `assets/` or `tests/` changed.
- **Tools:** `tools/master.py` (the hand-drawn master, edited in place), `keys.py`, `compose.py`, `make_r3_sheet.py`. `_patch_st_r3.py` lets the scratch build give CREDITS its 5th palette (no speaker page), as round 2 did. Like rounds 1-2 they run from `out/town/tools` (next to round 1's `render_v2.py`, `check.py`, `lint_all.py`, `cap_town.py`, `_patch_st.py`).

## Buildings (master, so all three times of day agree)

Rules now:

- Every window is the kit window: a 5x6 frame with 3x4 glass.
- Every door or opening is arched and at least 6 px wide inside, with wall on both sides.
- No sills or ledges.
- Each building's openings sit on one axis, and the floors line up.
- Where buildings touch, they share one 1 px ink line. Where they don't touch, sky shows between them.

| Building | Round 2 | Round 3 |
| --- | --- | --- |
| Left gable (cropped) | Placed at x -8: its outline (x 15) doubled the tower's (x 16). A 3 px door slice showed at the screen edge | Placed at x -7, so it shares the tower's outline. Its door is removed (the piece has no door now). The oculus and one upper window show |
| Clock tower | Clock, two windows, a door | Unchanged. Its door now reads as the tavern's door |
| Tavern | A 5 px door crowded against the right edge, with a doubled ink edge (x 70-71). The shop window started on the tower's outline (2 px ink, x 31-32). The upper windows sat 1 and 2 px from the banner. The awning stopped at x 63. A sill | The door is gone. The awning spans the whole front (x 32-70). The 4-bay shop window is centred, with 3 px of wall each side. The upper windows are over the outer bays (x 37-41, x 61-65), with 5 px of wall to the edges and 5-6 px to the banner. The sill is gone |
| Market hall | Plain | Unchanged |
| Right gable | Its ground floor was one dark rectangle, x 136-156. Dregs's hair and legs, and Sal's lower half, disappeared into it | An arched passage, with its frame under the upper windows' outer frames (x 138, x 157). Inside it is the sky's colour at night and dawn, and the sunlit street (cream) by day |

## Sky

| Time | Added | Keys |
| --- | --- | --- |
| Day (FINALE) | Three soft cream clouds, no ink: 24x6 above the tavern, 16x4 right of the spigot, 10x3 top left. Each sits in one tile row, 8+ px from the spigot and the roofs, below the bunting | `o` cream DMG 0 on sky DMG 1 |
| Dawn (CREDITS) | Two thin gold strips: x 50-80 at y 14-15, and x 124-147 at y 22-23 | `O` rim gold DMG 1 on peach DMG 0 |
| Night | Nothing new. `o` and `O` take the sky's colour, and the stars may sit on them | |

Both read on DMG: the clouds are light grey on mid grey, the strips grey lines on white. Nothing moves or flashes.

## Characters

| Picture | Who | Round 3 |
| --- | --- | --- |
| intro_a | Dregs | The v8 idle (`assets/art/dregs/dregs.txt`) replaces the pre-v8 figure. He faces the stump using the game's run-time flip of the idle. He stands in front of the lit shop window, and his feet are on the cobble at y 92, like Sal's. Keys as the approved intro_a: skin `D`, grey `m`, ink |
| credits_b | Dregs | The v8 fill picture (arm out, unflipped) replaces the pre-v8 mopper and his apron. He stands in front of the tavern with his feet at y 93. The mop is hand-drawn: a 1:1 handle from his fist, and the old mop's 3-row head in front of him |
| finale_a | Dregs | The same v8 idle, now whole: 4 px lower, so his feet are on the cobble at y 93. He stands in the passage, light behind him |
| finale_a | Sal | His sprite's legs and feet (idle rows 19-23) under his approved finale torso, feet at y 93 |
| finale_a | Crowd | 5 px lower (heads from y 95), so no feet touch it |
| intro_before, intro_a | Sal | Unchanged. His legs were already on the cobble. He now stands in the passage (navy behind), so his ink outline reads |

- **Legs:** every Sal and Dregs now has both legs and feet showing, over cobble or light, and none is cut by the frame, the fountain or the crowd.
- **The coffee-stand Sasquatch:** unchanged.

Dregs's colours against his sprite (sprite: skin cream #f0d8a0 DMG 1, grey #b0a0b8 DMG 2):

| Picture | Skin | Grey | Why |
| --- | --- | --- | --- |
| finale_a | `S` #f0b888, DMG 1 | `B` lilac #a090b0, DMG 2 | As imported 10-29. DMG values match his sprite |
| intro_a | `D` #f0d8a0, DMG 0 | `m` #a888a0, DMG 1 | As the approved intro_a. At night DMG 2 is the sky |
| credits_b | `D` peach, DMG 0 | Head: `B` violet, DMG 2. Jacket: `m` stone #b898a8, DMG 1 | The jacket is lifted to DMG 1 because the wall behind it is DMG 2. The head's grey stays DMG 2 because the gold window tiles have no other slot |

No Color-only hue edit on Dregs now. Round 2's two are gone: FINALE m to B, and CREDITS m to gold.

## Clean-up log (per picture, `EDITS`/`FINALE_FIX` in `tools/compose.py`)

- **finale_a (136, 69), Sal's cap, last brim-shade pixel `y` to `B`:** Color only; DMG is unchanged (both 2). That cell holds the passage pier, and the gold and lilac can't share one palette.
- **finale_a (128, 89) and (154, 89), cobble highlight `h` to `p`:** these were orphan pixels left by the new legs.
- **Master, tavern awning:** the stripes are tile-periodic (AAaa from x 32), so the facade costs 2 tiles less.
- **Master, upper windows:** the tavern's upper windows each straddle a tile, which costs 2 tiles. I kept them that way for the line-up with the bays.
- **Master, passage:** its arch top is at y 64, in the tile row Dregs already uses, which saves 2 tiles.
- **Lint warnings checked:**
  - No new 2x2 squares. The new one in CREDITS is Dregs's own fist in his fill picture.
  - The new orphans are the sprites' own eyes and gaps, or the crowd moved.
  - L-doubles went from 81 to 73 (FINALE). The rest are unchanged.

## Counts (check.py = gen_story's packing; the scratch ROMs build)

| Picture | Tiles / limit | Round 2 | Palettes |
| --- | --- | --- | --- |
| intro_before | 115 / 151 | 105 | 4 |
| intro_a | 106 + 30 trail / 151 | 95 + 30 | 3 |
| finale_a | 139 / 146 | 134 | **4** (no 5th needed) |
| credits_b | 138 / 199 | 129 | 5 + HUD (unchanged; needs Option A as before) |

**Lint:** PASS on all 8 pictures and the 3 masters.

## Doubts

1. **The day passage is a large cream (DMG 0) opening.** Dregs needs it: sky blue is DMG 1, like his skin, so his tiles would clash. It is as bright as the fountain's stone. By day it reads as sunlit street; I'm not sure it isn't too loud.
2. **intro_a Dregs is the idle flipped**, as `src/po.c` shows it in game, so that he faces the stump. If any flipped copy counts as mirroring, he faces left instead (one argument).
3. **The CREDITS apron is gone** (his sprite has none), and he holds the mop in his fill pose. It's a smaller gag than the old picture's.
4. **The left gable shows one upper window right of its oculus.** Its twin is off screen, because the house is cropped by the frame.
5. **The tavern's upper windows are 0.5 px off the banner's axis.** The banner is 8 px on a 39 px front, so the gaps are 5 and 6 px.
6. **The finale crowd now shows only heads (y 95-103).**
7. **finale_contest is still derived from the old generator (C3).** The scratch build used a copy of finale_a, as in rounds 1 and 2.
