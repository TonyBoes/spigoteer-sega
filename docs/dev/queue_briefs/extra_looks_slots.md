# Palette slots per venue, as the Graphics Atlas plan shows them (read 2026-11-01)

Source: the published Atlas (tools/artifacts/palette_plan/index.html, built from plan_data.py / build.py field_model).
This is the spec for the patron import. Owner 2026-11-01: "Where the keg goes is different for every stage. You need
to look through every venue in the Atlas to see where the object pallets and the background pallets are assigned."
Implement it as written; flag (do not resolve) anything that looks inconsistent.

Playfield BG slots (above the playfield: BG 1 HUD, BG 5 and BG 6 stage; they are reloaded where the playfield starts).

| Venue | BG 0 | BG 1 | BG 2 | BG 3 | BG 4 | BG 5 | BG 6 | BG 7 |
|---|---|---|---|---|---|---|---|---|
| Saloon | bar, wall, keg | free | GUS, HANK | DUSTY, EMMA | (4 swaps) | free | free | ROSIE, REDD |
| Stadium | bar, wall, keg (keg colour 3 #311018 -> #20294A) | PETE, FRANK (as OBJ 1) | LOUIS (as OBJ 2) | NORM | PIPER (as OBJ 4) | TOM (as OBJ 5) | MIKE (as OBJ 6) | SERENA |
| Lumber Lodge | bar, wall | keg | CEDAR, WILLOW, BOONE | INES (as OBJ 6) | SMITH (as OBJ 4) | ROD (as OBJ 5) | INES (as OBJ 6) [flag: INES twice] | ASH |
| Bistro | bar, wall | keg | PIERRE, BRIE, NONNA | MIME (as OBJ 3) | OLIVE (as OBJ 4) | Sage (as OBJ 5) | Deep skin (as OBJ 6) | BASIL, PINOT, HERB |
| Igloo | bar, wall | keg | FROSTI (as OBJ 2) | IGGY | MUFFY (as OBJ 4) | MUSH, CUB, DENALI (as OBJ 5) | POLLY | MOOSE |
| Robot Factory | bar, wall | keg | CLANK (as OBJ 1) | BOXY | BLIP, NEKA (as OBJ 4) | TOOB (as OBJ 5) | VOLTA | TELLY |
| Chrome Cow | bar, wall | keg | DJ (as OBJ 2) | PUNK | RAVEN, FRINGE (as OBJ 4) | ROADY, ANVIL (as OBJ 5) | HARLEY (as OBJ 6) | BABY |
| Teahouse | bar, wall | keg | MONK (as OBJ 5) | KAGE | HANA (as OBJ 4) | SENSEI (as OBJ 0) | SAKURA, RONIN, KON (as OBJ 6) | POET |
| Jungle Zoo | bar, wall | keg | COCO | TUCO, RAJA (as OBJ 3) | PINKY (as OBJ 4) | free | BAMBOO, ELLIE, ZIGGY | MUDDY |
| Space Lounge | bar, wall | keg | ZORP | XENO, VENUS | LUNA, GLOP (as OBJ 4) | MOTHMA (as OBJ 3) | DASH (as OBJ 6) | GLORP |

OBJ slots (sprites).

| Venue | OBJ 0 | OBJ 1 | OBJ 2 | OBJ 3 | OBJ 4 | OBJ 5 | OBJ 6 | OBJ 7 |
|---|---|---|---|---|---|---|---|---|
| Saloon | Sal, tip coin | full mug, effects, show dancers | empty mug, capacity mugs | GUS, HANK | ROSIE, REDD | MABEL, ARTIE | DUSTY, EMMA | (4 swaps); boss hat |
| Stadium | NORM, Sal, coin | PETE, FRANK, full mug, cheerleaders | LOUIS, empty mug | free | PIPER | TOM | MIKE | SERENA; boss forelock |
| Lumber Lodge | Sal, coin | BOONE, PIP, full mug, Sasquatch | empty mug | CEDAR, WILLOW | SMITH | ROD | INES | ASH; boss crest |
| Bistro | PIERRE, BRIE, NONNA, Sal, coin, waiter | full mug | empty mug | MIME | OLIVE | Sage | Deep skin | BASIL, PINOT, HERB; boss beret |
| Igloo | Sal, coin, penguin | full mug | FROSTI, empty mug | IGGY | MUFFY | MUSH, CUB, DENALI | POLLY | MOOSE; boss horns |
| Robot Factory | Sal, coin, show dancers | CLANK, PEPPER, full mug | empty mug | BOXY | BLIP, NEKA | TOOB | VOLTA | TELLY; boss lamp |
| Chrome Cow | Sal, coin | full mug, empty mug, capacity mugs | DJ | PUNK | RAVEN, FRINGE | ROADY, ANVIL | HARLEY, the band | BABY; boss helmet |
| Teahouse | SENSEI, Sal, coin | full mug | empty mug | KAGE | HANA | MONK | SAKURA, RONIN, KON, taiko drummer | POET; boss topknot |
| Jungle Zoo | Sal, coin | COCO, full mug | empty mug | TUCO, RAJA | PINKY | show dancers | BAMBOO, ELLIE, ZIGGY | MUDDY; boss crown |
| Space Lounge | Sal, coin | ZORP, full mug | XENO, empty mug | MOTHMA | LUNA, GLOP | VENUS, show dancers | DASH | GLORP; boss antenna |

Notes for the build
- "(as OBJ n)": the BG palette holds the same colours 1-3 as OBJ n (the page shows "colours as OBJ n").
- BG numbers do not equal OBJ numbers (e.g. Teahouse MONK = OBJ 5 / BG 2). Take each look's (OBJ, BG) pair from this table.
- In the playfield, BG 1 holds the keg (or, in the Stadium, PETE/FRANK). The windows drawn over the playfield (banner,
  pause, card, note) use the HUD palette today: keeping them in HUD colours is an engineering task, not an owner question.
- Swaps: each look may also spawn in the venue's other patron palettes except VARIANT_CUTS (plan_data.py).
