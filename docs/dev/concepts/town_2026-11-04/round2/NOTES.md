# Town, round 2 (2026-11-04): calmer, fountain first

Owner: "The town square looks better, but it might be a tad busy, and the fountain has a hard time standing out in the
daytime."

- **Sheet:** `sheet_round1_round2.png`. Each picture shows round 1 against round 2, Color over DMG, at x3. Captures are from the scratch ROM (picture rows), with 1x strips at the top.
- **Unchanged:** the buildings, bunting, cobbles, characters and composition. The removals below are hand edits to the master's pieces (`tools/_r2_master.py`, written row by row).

## What was removed or quieted (master, all three times of day)

| Piece | Removed or quieted |
| --- | --- |
| Market hall (behind the fountain) | Lozenge frieze, string course and all four windows removed: it is one plain mass. It ends at x 127, which leaves a sliver of sky between it and the right house |
| Tavern | Staggered roof joints (now three plain courses), the two outer upper windows, the sills and ledge, and the mugs in the shop window (plain lit panes) |
| Gable houses | Ledge, sills and ground-floor window removed. The two upper windows and the oculus stay |
| Clock tower | Two of four spire courses, the mid ledge and the window sills removed |
| Right house | The arch is now one square dark opening across the ground floor, so no wall shows behind Sal's cap or Dregs |
| Day doors | Now dark openings (DMG 3) instead of light wood: one value change fewer per door |
| Day roof | Light terracotta with lilac courses; it uses the characters' palette |

## The fountain

| Time | Stone | Wall behind | Change |
| --- | --- | --- | --- |
| Day (FINALE) | DMG 0, pale stone `#fff0b0` | Plain lilac hall, DMG 2 | The basin and column are the lightest mass on the screen. Dregs's jacket keeps its lilac (a per-picture edit) |
| Dawn (CREDITS) | DMG 1, mauve, unchanged | Hall goes dark (backlit), DMG 3, new key `H` | The fountain reads against a dark band |
| Night | DMG 1, unchanged | Silhouette, DMG 3, as before | Already reads |

## Counts (gen_story, scratch build)

| Picture | Tiles / limit | Round 1 | Palettes | Engine change |
| --- | --- | --- | --- | --- |
| intro_before | 105 / 151 | 112 | 4 | none |
| intro_a | 95 + 30 trail / 151 | 101 + 30 | 3 | none |
| finale_a | 134 / 146 | 142 | **4** (was 5) | **none** (round 1 needed Option A) |
| credits_b | 129 / 199 | 139 | 5 + HUD | Option A (BG 2 anywhere, no speakers) |
| Pool | 396 / 512 | 432 | | |

- **CREDITS without Option A:** it drops to 4 if the jets' water takes the stone's mauve instead of blue.
- **Lint:** PASS on all 8 pictures and the 3 masters.
- **Tiled previews:** clean (roof, bunting, cobble, awning and shop window).

## Clean-up log, round 2 (per picture, `EDITS` in `tools/compose.py`)

- **finale_a, removed:** round 1's cap recolour (Sal's cap shading back to gold). The cap now sits on sky and the shop front, so it fits the spigot's palette.
- **finale_a, added:** the basin colour in the 4 gaps between Sal's arm and body (x 128-135, y 78-79), which showed the new alley's sky (skin and sky are both DMG 1).
- **finale_a, added:** Dregs's `m` pixels set to lilac `B` (x 141-159). His jacket keeps its round 1 and old FINALE value, DMG 2.
- **Kept from round 1:** the water-to-spray edit above Sal's hand, and in credits the Dregs gold and the cup-sign backboard.

## Doubts

1. **The day fountain may be too bright.** It is now a large pale-cream block. The column's highlight stripe and the rim's light line merge into the stone, because both are DMG 0, so only the ink lines model it.
2. **The day roof** is peach-and-lilac rather than round 1's terracotta, which saves FINALE's fifth palette.
3. **Dawn still has gold lit windows and trim** on the left houses. I kept them, because they are the dawn rim light.
