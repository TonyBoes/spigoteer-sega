# Town, round 6 (2026-11-04): joining the right house and the hall

This round changes only what the owner named. It is a concept only: no changes to `src/`, `tests/` or the goldens.
Every change is on the master, so night, day and dawn agree. Both variants were checked in the scratch ROM on Color and
DMG.

`sheet_round5_round6.png` compares round 5, round 6 with the roof and round 6 without the roof (x3, Color over DMG).

## Changes

| Owner's words | Round 6 |
| --- | --- |
| "Connect the far right building to the building ... behind the fountain" | The hall now runs on to the right house (x 72-135). It closes the sky gap at x 128-135. The house's left outline (x 136) is the only line between the two buildings. That is the same join as the left gable and the clock tower, which share one outline. The hall's old right outline (x 127) is gone. |
| "Give it a door or window or something" | I read "it" as the hall, in its new bay beside the fountain. The window is the clock tower's 5 x 6 kit window, centred in the bay (x 129-133, y 58-63), one wall row under the hall's top line. It reads clear of the fountain in all four pictures. It is lit at night and at dawn, and shows as cream glass by day. I added no door: one at x 128-135 would be dark on the dark hall at night and at dawn, and Sal covers it in FINALE. |
| "Maybe a roof that goes across the top of the buildings" | **Two variants.** "Roof" adds a slate roof on y 48-55 across the hall, from the tavern to the right house's wall. It uses the clock spire's material (`U` with `u` courses) and has the hall's top line as its eave. It sits behind the fountain bowl and the jets, so it shows beside them. "No roof" keeps the hall's flat top. |

A roof higher up, on y 40-47, would run behind the Golden Spigot's base. The spigot's gold clashes with any roof
colour there: the trim and courses at night, the courses by day and the slate at dawn. Fixing that means recolouring
the spigot or adding a 5th palette in FINALE, so I don't offer it.

**Tiles freed (FINALE was at 146/146).** The hall's top line ran 1 px past the fountain column's outline on each side,
at (96, 56) and (111, 56). Both pixels are now wall, so the line stops at the column's own outline. Cells (12,7) and
(13,7) now repeat the column tiles below them. That saves 2 tiles in FINALE; the change is 2 px, the same in every
picture. Closing the sky gap saved nothing, because the old sky there was the shared sky tile.

**Forced fixes in FINALE** (`tools/compose.py`):
- The top of Sal's hat crown is now sunlit gold-cream, 5 px. Its dark gold and the hall's lilac, now behind it, are both
  DMG 2.
- 3 single wall pixels between the basin, Sal's arm and the house edge are ink, as they were in round 5.
- The round 5 "gaps show the basin" fix no longer applies: the gaps between Sal's arm and body now show the hall wall,
  which is the right thing behind him.

## Consistency audit

Source: `tools/audit.py`, `tools/audit_fountain.py`, and a check of the joined bay. The round 5 table still holds row
for row, plus:

| Building, prop or texture | intro_before | intro_a | finale_a | credits_b |
| --- | --- | --- | --- | --- |
| Hall, joined bay and window (x 128-135) | same | same | same, except Sal's head | same |
| Hall roof (roof variant) | same | same | same, except the fountain and Sal | same, except the fountain |
| Hall top line at the column (2 px) | same | same | same | same |

All other rows are unchanged from round 5: every building, the patrons, the 7 brick cells, the bunting and the plaza are
the same in all four pictures. The exceptions are still the same: lighting, the story props (Sal and his rim, Dregs,
the crowd, the spigot's state, the drips, the suds and mop) and the sky.

## Counts (check.py; the scratch ROM builds both variants; ROM0 443 B free, unchanged; no new palette)

| Picture | No roof | Roof | Round 5 | Palettes |
| --- | --- | --- | --- | --- |
| intro_before | 119 / 151 | 120 / 151 | 118 | 4 |
| intro_a | 108 / 117 | 109 / 117 | 107 | 3 |
| finale_a | **145 / 146** | **146 / 146** | 146 | 4 |
| credits_b | 129 / 199 | 130 / 199 | 128 | 5 |

There are no tile clashes in either variant. The water phases (`water_phases_*`) give the same counts as their
variant.

**Lint:** RESULT PASS on all 11 files (8 pictures and 3 masters) for each variant, and for each of their water
phases.

The FINALE warnings are as in round 5: 77 L-doubles and 29 orphans. The other pictures change as follows:

| Warning | No roof | Roof |
| --- | --- | --- |
| L-doubles | ±1 | +2 (the roof's courses meeting the jets' outlines) |
| Orphans | ±1 | ±1 |

## Doubts

1. With the roof, FINALE is back at 146/146 with no spare tile. Without it there is 1 spare.
2. The roof's ridge line meets the fountain bowl's rim line (both y 48), so the rim reads less separate by day on DMG.
3. "Roof across the top of the buildings" could also mean one roof spanning the hall and the right house. The right
   house keeps its approved gable, and the hall's roof meets the house's wall.
4. The window is the only new opening. Say if a door is wanted as well; it would show only by day.
