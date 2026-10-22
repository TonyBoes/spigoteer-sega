# Saloon patron potentials (owner, 2026-10-21)

The owner likes these and wants them saved as candidates. They are **not imported**.

| Figure | Slot | Source |
|---|---|---|
| Prospector 1 | A | round 2 (`prospector_1/`). **PLANNED 2026-10-21:** shares the Outlaw's palette on the Saloon's OBJ 7 / BG 7 (beard #D8C098; Palette Plan). Not imported yet. |
| Prospector 2 | A | round 2 (`prospector_2/`) |
| Singer | B | round 2 (`singer/`) |
| Rancher | B | round 2 (`rancher/`) |
| Outlaw, the ORIGINAL round-1 version | C | round 1 `d2_dusty` variant C (`outlaw_round1/`). **PLANNED 2026-10-21:** Saloon OBJ 7 / BG 7, his own palette; Big Tex's body and hat take the same palette (Palette Plan). Not imported yet. |

- Not chosen: the gunslinger, the cardsharp, and the round-2 outlaw redraw.
- By default, any of these gets another quality pass before import (the art-another-pass-default rule), unless the owner says it's locked.
- The round-1 outlaw's outline was script-made (see SKILL_DEVIATIONS.md). A pass on him should keep his design and look, and hand-fix only what the skill flags. The owner preferred him to the redraw.

## How the owner reads the ORIGINAL outlaw (2026-10-21, Q31). Use this in every brief that touches him.
- The single skin-coloured pixel in the hat-brim shadow, at (5,6) in outlaw.txt, is his EAR. Never remove it as a "stray pixel".
- The skin area with a black dot to its right is a HALF-SHADOWED FACE with ONE visible EYE.
- The light dots lower down, which round 2 called "eyes", are a PATTERN on the scarf/poncho: buttons or patterning on the cloth covering his face.
- The owner chose to keep him exactly as originally drawn (Q21/Q22): no clean-up, no tweaks.

## Owner set 2 (uploaded 2026-10-21, `owner_set_2/`, PATRON_SPEC format)
Saved concepts the owner handed over. **Not imported, and not placed in the Palette Plan yet.**

| Figure | Variant | Palette (light to dark) |
|---|---|---|
| Gunslinger | A | #F8D0A0, #B87040, #202030 |
| Saloon singer | B | #F8D0B0, #B84058, #202030 |
| Old prospector (bald, grey beard) | C | #F8D0A0, #988880, #202030 |

- The files were previewed on a guessed wall colour, #805838. The real Saloon wall is #295262.
- None of these is an enhanced variant.
- The art-another-pass-default rule applies before import, unless the owner locks them.

## Saloon singer v3 (owner, 2026-10-21): CHOSEN as a new Saloon patron
`saloon_singer_v3/saloon_singer_front.png` (16x16, front view only). Her palette is #F8D0B0, #B84058, #202030. The wall
(colour 0) shows through at her pupils, which is deliberate: the owner's "wall as a free 4th colour" experiment.
- Planned on the Saloon's OBJ 4 / BG 4 (Palette Plan).
- A back view still has to be drawn.
- She replaces the set-2 Saloon singer art.

## Brown-haired singer (owner, 2026-10-21): CHOSEN as a new Saloon patron
`brown_singer/brown_singer_front.png` (16x16, front only; the art's wall placeholder is blue #005493). Her palette is
#F8D0B0, #805838, #202030. The wall shows through at her pupils and at a few gaps in her dress. Planned on the Saloon's
OBJ 5 / BG 5 with her own palette (the owner chose that over sharing OBJ 3). A back view still has to be drawn.

## Names (owner, 2026-10-21)
- **MABEL**: the Saloon's patron B, formerly ROSIE. Owner's redraw: grey hair under a black lace shawl, dark dress.
  - Her palette is #FFCEAD, #ADADAD, #303038.
  - Files are `../../rosie_sprite/mabel.txt`, `mabel_front.png` and `mabel_back_proposal.png`.
  - The back view is a proposal and still needs a pass.
- **ROSIE**: now the red-dress singer (the Saloon singer v3, OBJ 4).
- When imported, tools/gen_credits.py PATRONS must follow. The Saloon line is ["DUSTY", "ROSIE", "HANK"]; B becomes MABEL, and ROSIE goes to the singer's slot.
- **ARTIE**: owner set 2 C, the bald old prospector with a grey beard.
  - CHOSEN 2026-10-21. He shares MABEL's palette on the Saloon's OBJ 6 / BG 6, so his skin becomes #FFCEAD and his beard #ADADAD.
  - Art: `owner_set_2/saloon.txt` and `saloon_back.txt`, variant C.
- **MABEL's back** (`mabel_back_proposal.png`, a diamond lace net) is a placeholder. The owner wants a MAJOR quality check on it before anything is submitted.
- **DUSTY and HANK, new fronts** (owner's redraws, 2026-10-21) are in `../../dusty_hank_sprite/dusty_hank_v2.txt`.
  - DUSTY has a creased hat with curled brim tips. HANK has a wide flat tan hat and a full beard.
  - Both stay on the plan's OBJ 3 palette, the owner's pick over HANK's own colours.
  - Both back views still need redrawing to match the new hats.
- **Outlaw (2026-10-22): owner's recolour.** Red poncho and bandana, navy hat and outline, tan details. File: `../../outlaw_sprite/outlaw_owner_v3.png`, with the outline closed on the bottom rows.
  - It replaces the "keep the original exactly" Outlaw.
  - He now shares ROSIE's palette (OBJ 4 / BG 4): his red becomes #B84058, his navy #202030, his tan #F8D0B0.
  - OBJ 7 keeps the former Outlaw palette for the Prospector and Big Tex.
- **Names (2026-10-22):** the Outlaw is **REDD**.
- **Names (2026-10-22):** the brown-haired singer is **EMMA**.
- **Names (2026-10-22):** Prospector 1 is **GUS, the prospector**; ARTIE is **a priest**, not a prospector.
