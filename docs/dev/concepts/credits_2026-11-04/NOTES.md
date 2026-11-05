# Credits remake: patron cards (mockups only, nothing imported)

Render: `render_mockups.py OUTDIR` (needs no ROM). Every patron pixel is copied from `assets/art/patrons/<group>.txt` / `<group>_x.txt`
(shift-0 front pose); colours are the Palette Plan's (`plan_slots.json`, the Atlas export) at 5 bits a channel; lettering is the game's own
glyphs (`tools/gen_credits.py`). Sheets: `sheet_layouts.png` (A, B, C on Saloon / Igloo / Space Lounge, x3, DMG row last: it is the same for every
layout), `sheet_all_venues.png` (A, all 10 venues, Color over DMG, x2).

## Why not 2 rows of 4
Names are 4-6 letters, 8 px a letter (ink = 8n-3: 29 to 45 px). A row of four names leaves a gap of 1 px or less in the worse row of every venue
(Bistro, Factory -2; Chrome Cow, Teahouse -4; the rest 1). The card's own rule is 8 px. Ruled out without a mockup.

## Layouts
| | A: one card, 3-3-2 grid, name under sprite | B: one card, roster 2x4, name beside sprite | C: two cards of 4 (2x2, name under) |
|---|---|---|---|
| Read | like today's card, repeated; top row = the DMG's three | list, clear on a phone, small sprites beside long names | biggest, airy, but 4 cards a venue |
| Sprites per line (max, with the 2 px bob) | 6 | 4 | 4 |
| Objects (of 40) | 16 | 16 | 8 per card |
| Text tiles (BG, unique, worst venue; budget 78 at ids 178-255) | 38 | 37 | 23 |
| Names fit | gaps >= 6 px (tightest row asserted) | yes | yes |
| Timeline | unchanged (3 cards a venue) | unchanged | 4 cards a venue: 40 cards, the tune-share table needs a new split |

Same for all three:
- **OBJ palettes:** the patron card shows no Dregs, topper or bartender, so all 8 OBJ palettes are free there; each card already
  rewrites them (CR_PAL, VBlank). A venue needs at most 7 distinct looks' palettes (Stadium, Space Lounge; Saloon 4, Bistro 4) because
  looks share (PIERRE/BRIE/NONNA = Sal's, BASIL/PINOT/HERB, the Saloon's five instances). So **no BG-tile patrons and no mid-frame swap**.
  `OBJPAL_ROBOT + k` (5..7) becomes OBJ 0..6 by a generated per-look table.
- **Tiles:** 4 per look (two 8x16 objects; the third column of the 6-tile pose is empty). The 3 base looks stay at OBJ ids 100-117, bank 0
  (as now); the 5 Color-only looks go to VRAM **bank 1** (sprite attribute bit 3), 20 tiles, ids 100-123. Needs a new banked accessor
  per venue for the shift-0 pose of the `_x` art (`load_<v>_x(part)` loads all 8 shifts; shift 0 is a subset, so no new ROM data).
- **Code:** `cr_card_sprites` loops 8 looks (positions from a generated table; Color only), `cr_load` loads 8 looks + palettes, `gen_credits.py`
  gets the 8 names, rows and positions from the plan. DMG path unchanged (3 patrons, one row). Owner card, boss card and the roll: no change.
- **Build time:** about 14 more tile units than the 19 now (32 tiles + 7 palettes); check the card still builds inside the fade on the 88 s tune.

## Recommendation: A
The top row is the DMG's three, the rest reads as "and more", the timeline and card count do not change, 6 sprites a line leaves 4 spare.
B is the fallback if the owner prefers a list; C costs a re-split of the tune and 10 more fades.

## Names (plan order; 3 base, then Color-only)
Saloon DUSTY EMMA GUS | HANK ROSIE REDD MABEL ARTIE.  Stadium PETE NORM SERENA | FRANK PIPER LOUIS TOM MIKE.
Lodge CEDAR ASH WILLOW (owner's order) | BOONE SMITH ROD INES PIP.  Bistro PIERRE BRIE BASIL | PINOT NONNA MIME OLIVE HERB.
Igloo IGGY POLLY MOOSE | MUFFY CUB MUSH FROSTI DENALI.  Factory BOXY VOLTA BLIP | NEKA TELLY CLANK TOOB PEPPER.
Chrome Cow PUNK HARLEY BABY | DJ RAVEN ROADY ANVIL FRINGE.  Teahouse KAGE SAKURA RONIN | SENSEI KON MONK POET HANA.
Zoo COCO BAMBOO MUDDY | TUCO ELLIE ZIGGY PINKY RAJA.  Space ZORP XENO GLORP | DASH MOTHMA GLOP LUNA VENUS.

## Doubts
1. **The credits' current labels are stale** (`gen_credits.py PATRONS`): Saloon shows DUSTY ROSIE HANK over the art DUSTY, EMMA, GUS
   (golden `credits_cast_patrons_saloon`); Stadium labels B SERENA / C NORM but B is the ref (NORM); Chrome Cow still SPIKE/BANDIT/SLICK.
   The mockups use the plan names, so the DMG cards change too (goldens: `credits_cast_patrons_saloon.{dmg,cgb}`, Stadium and Chrome Cow
   if they exist, all `credits_cast_patrons_*.cgb`). The Lodge order CEDAR, ASH, WILLOW is kept (owner 2026-10-17).
2. GUS and ASH: the game swaps colour planes 1/2 of those tiles at level load; the plan's colours are for the swapped tiles, so the mockup swaps the art's
   indices, and a build writes the palette swapped (as `lumberjacks_ash_credits` does).
3. Saloon palettes are the plan's primary instance per look (`SALOON_PRIMARY`: DUSTY/EMMA one, GUS/HANK another, ROSIE/REDD red, MABEL/ARTIE grey);
   several looks share a palette, as the plan has it.
4. Existing DMG card: the outline (idx 3) is black on the black card, so it vanishes. Shown as it is now; not mine to change here.
5. B's roster reads down the columns, so the base three are not one row; A's third row (2 names) is centred, not on the grid.
6. Plan colours are the Atlas's; the Saloon's slot colours also differ slightly from `palettes.json` (lifted channels): the mockups use the 5-bit values.
