---
name: palette-rearrange-means-slot-swap
description: "Rearrange X's palette so it works with everyone" = reorder colour slots (skin slot), the look stays identical
metadata:
  type: feedback
---
When the owner asks to "rearrange" a patron's palette/colouring "so it works with everyone else", he means: reorder the palette's colours and swap the art's indices to match, so the look is pixel-identical and the colour in the skin slot (Bistro: colour 2) is the one that should land on other patrons' skin. Do NOT redraw or recolour the character.

**Why:** 2026-10-31 I redrew MIME without red (Q78); owner: "I did not mean that I wanted the mimes colours to change." Same pattern as ARTISTE and ASH earlier.

**How to apply:** swap `-`/`+` (or whichever) in art/<venue>_<name>*.txt, reorder the palette in plan_data, verify the 1x images are pixel-identical, LOG line. See [[think-before-relaying]].
