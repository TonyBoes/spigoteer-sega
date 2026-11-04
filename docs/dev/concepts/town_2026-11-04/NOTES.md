# Town master and the square pictures (proposal, 2026-11-04)

Nothing under `src/` or `assets/` changed. The pictures were built and captured in a scratch tree (`out/town/st`, its own
`make`) whose `tools/gen_story.py` carries the Option A experiment (`tools/_patch_st.py`).

## Sheets

| File | Shows |
| --- | --- |
| `sheet_master.png` | The master: one set of pixels with three palette sets (night, day, dawn), Color and DMG at x3, plus 1x |
| `sheet_pictures.png` | Each picture: scratch ROM capture at 1x (Color, DMG), then x4 Color and x4 DMG |
| `sheet_before_after.png` | 1x strips (before, after; Color and DMG), then before and after per picture at x3, Color over DMG (ROM captures, picture rows) |
| `sheet_venue_check.png` | The Pour-Off venue (golden `po_perfect`, unchanged) next to the top of the day square |

## What the master is

- One hand-drawn 160x104 grid in material keys (`tools/master.py`), built from five pieces placed by hand:
  - The **gable house**, the Pour-Off venue's house brought nearer: 45° gable, trim on the lit slope, an oculus, the venue's
    5x6 window with 3x4 glass, sills, a ledge and an arched door. It is used at both ends of the square.
  - The **clock tower**, the INTRO's clock face kept: a spire with courses, ledges, windows and an arched door.
  - The **tavern**: a tiled roof with an eave, the venue's cream banner, an awning, a shop window with mugs, and a door.
  - The **market hall** behind the fountain: flat top, a lozenge frieze, a string course and windows.
  - The **right house's shop front**: an open dark arch, so whoever stands there (Sal at night, Dregs by day) reads on DMG.
- The venue's **bunting** (`festival_stage.txt` rows 0-6) runs along the top of every picture. The INTRO's **cobble** lies under every plaza.
- The kit repeats (tiled previews are clean):

  | Part | Repeat |
  | --- | --- |
  | Roof | 8 px |
  | Frieze | 8 px |
  | Bunting | 16 px |
  | Cobble | 8x16 |
  | Awning | 4 px |
  | Shop window | 16 px |

- The master alone is 38 tiles (night), 58 (day) and 57 (dawn).
- The props are copied unchanged from the approved pictures: fountain, Golden Spigot, Sal, Dregs, the INTRO crowd, moon, stars, sun, coffee stand and suds (`tools/compose.py`, a rectangle each).
- The FINALE crowd is the mockup's ten hand-drawn silhouettes (ink pixels only).
- The old string lights are gone. The bunting replaces them in every picture.

## Tiles per picture (gen_story's own count, scratch build)

| Picture | Tiles | Limit | Before |
| --- | --- | --- | --- |
| intro_before | 112 | 151 | 117 |
| intro_a | 101 + 30 trail = 131 | 151 (with the burst) | 112 + 34 |
| finale_a | 142 | 146 | 134 |
| credits_b | 139 | 199 | 132 |
| Story picture pool | 432 | 512 | 451 |

The pool total assumes finale_contest is re-derived from the new finale_a. In the scratch build, finale_contest was a plain copy of
finale_a. Re-deriving it with the old generator is not possible: `tools/gen_contest_pic.py` paints sky where Sal and Dregs stood, and
in the new square the hall and the shop front are behind them. The generator must paint the master there instead (C3). An unshared
contest would take the pool to about 560, over the 512 an id can address.

## Palettes per scene

All three times of day use the same pixels and only swap keys (`tools/keys.py`). DMG keeps its four shades; the time of day only moves materials between shades.

- **INTRO, night: 4 palettes (intro_a needs 3). This fits the engine today, with no code change.**
  - Spigot, bunting and moon (palette 0, the burst's: light gold, gold, sky, ink).
  - Town and trail dots (the trail's cream and mauve).
  - Jets.
  - Sal.
  - To fit, the night's whites became one lamplight cream: Sal's shirt and the spray (`#f8f8f0` to `#f0d8a0`) and the stars (to `#f8f0a0`).
- **FINALE, day: 5 palettes.** The four outside the portrait frame:
  - Bunting: venue cream, sky, the venue's orange `#f08828`.
  - Spigot: cream, sky, gold.
  - Houses: cream, sky, the venue's lilac.
  - Sal, Dregs and the plaza: cream, skin, lilac.

  The fifth, the tavern roof (cream, terracotta `#e88860`, terracotta shade `#b05840`), is used only by cells under the speaker
  portrait frame (cols 1-9, rows 4-12). It goes in BG 2, which is free on narrator pages. This is Option A below.
- **CREDITS, dawn: 5 palettes plus the HUD** (the coffee stand, as before).
  - Bunting, roofs and mugs (one rust `#b05040`).
  - Spigot.
  - Houses.
  - Jets.
  - Stone, plaza and Dregs.

  CREDITS has no speaker page, so the fifth can use BG 2 anywhere.
- **Without any engine change**, the day and dawn pictures can be cut to 4 palettes. Each picture has to give something up:
  - FINALE: the tavern roof drops its terracotta for the skin/lilac palette.
  - CREDITS: the jets turn stone-grey instead of blue.

## The src/story.c change (Option A), not made

A picture may have up to three more palettes in BG 2-4. They may be used only by the cells a speaker's portrait frame covers, or anywhere in a scene with no speakers.

| Where | Change |
| --- | --- |
| `tools/gen_story.py` | `PIC_SLOTS` (0, 5, 6, 7, 2[, 3, 4]); the palettes needed outside the frame are ordered first (as in `_patch_st.py`); checks for that |
| `src/story.c` fade | `PS_PALS`/`PS_OUT` grow by 4 words per extra palette. `story_scratch` must be re-laid around `PB_T` (168) and the burst's bytes, and `pic_put` writes 6 palettes instead of 5. Not measured whether 6 fit VBlank: the code says 8 do not |
| `src/story.c` portrait | When a portrait goes away, `write_palettes` must put the picture's BG 2 back |

- Estimated size: about 60-100 B of banked code (story.c is bank 255). It needs 0 B of ROM0 and no new WRAM, only `story_scratch` offsets.
- The scratch ROM shows exactly the missing pieces:
  - The roof palette is not faded: it pops in at full colour during the fade-in.
  - On FINALE p8, a narrator page after three speaker pages, the tavern roof shows the last portrait's colours, because BG 2 is not restored.
- Option B, the existing raster split (`SPLIT_ON`), would allow a top band with its own palettes. It is more work and was not tried.

## DMG

- **Every picture is DMG-safe.** The shades follow the old pictures' structure:
  - Night: the town is a dark silhouette.
  - Day: walls are DMG 2 on a DMG 1 sky.
  - Dawn: walls are DMG 2 on a DMG 0 sky.
- **The DMG look changes only where the new buildings stand.** In the FINALE, the plaza is light (cobble 1, mortar 2) under a black crowd.
- **The festival venue does not need to change.** The day square uses its own colours and shades:
  - Sky `#b8dcf4` at DMG 1.
  - Lilac `#a090b0` at DMG 2.
  - Cream `#fff0b0` at DMG 0.
  - Ink `#201828` at DMG 3.
  - The same bunting, gable and window shapes.

## Clean-up log (hand edits after composing; `EDITS` in `tools/compose.py`)

| Picture | Rect | Change | Why |
| --- | --- | --- | --- |
| finale_a | 120-127, 64-71 | water `b` to spray `W` | The jet's last water above Sal's hand: water and skin are both DMG 1 by day |
| finale_a | 128-143, 64-71 | Sal's cap shading `y` to `B` | On Color the cap's gold shading becomes the wall's lilac (DMG unchanged). The hall and the gable are behind it |
| credits_b | 31-60, 66-87 | Dregs's and the mop's `m` to `e` | On Color his stone-grey pixels become the trim gold (DMG unchanged). He stands in front of the gold-lit awning and window |
| credits_b | 136-143 and 152-159, 48-55 | wall `B` to ink | A backboard behind the cup sign: its pale gold and the wall are both DMG 2 |

Master changes made during composing:

- The shop-window mugs got their own key `M`.
- The hall lost its roof (flat top and frieze), because the jets and column cross it.
- The right house got the shop front.
- Credits copies leave out the old string's end (x 72-79 above the basin) and the old bulbs (sun copied left of x 48 only).

## Doubts

1. **Two characters change hue on Color only.** Sal's cap shading turns lilac in FINALE; Dregs's grey bits turn gold in CREDITS. DMG is identical in both. Dregs's credits pose is pre-v8 (C2), so his will change anyway; Sal's needs the owner's look.
2. **Night whites are warmed to lamplight cream.** This covers Sal's shirt, the jets' spray and the stars.
3. **FINALE (and CREDITS without a code change) need Option A.**
4. **The hall is a plain lilac block behind the fountain by day.** The fountain stone is the wall's lilac, as in the old FINALE, so the basin reads as part of the hall on Color.
5. **The finale contest picture needs its generator reworked (C3)** before the pool numbers hold.
6. **Test changes if adopted:**
   - `tests/test_story_pictures.py` pins the exact tile counts and `len(pals) <= 4`.
   - The INTRO, FINALE and CREDITS goldens would all change. Only the supervisor replaces them.

## Running the tools

They run from `out/town/tools` in the worktree, with relative paths to the repo:

- `compose.py OUTDIR`
- `check.py`
- `lint_all.py`
- `cap_town.py cgb|dmg`
- `make_sheets.py DEST`
