---
name: spigoteer-patrons
description: The rules for Spigoteer's bar patrons and their palettes - the patron spec (16x16 busts, pre-shifted tiles, lifted sprites, mirroring, the held mug), tile budgets per look, BG/OBJ palette pairs, the Palette Plan page, Color-only extra looks, palette variants, and the owner's standing art rulings. Use it for any task that touches patron art, patron code (render, lift, mirror, spawn, tips), venue palettes, the Palette Plan, patron names or the credits cast, even if the brief only names one character.
---

# Spigoteer patrons and palettes

Decisions are dated. Current status (what is held, what is next) lives in `docs/dev/notes/QUEUE.md`: check it first.
On 2026-10-24 the owner said "Hold off on patron changes still": do no patron work unless the brief says the hold is
lifted.

## The spec
`docs/dev/notes/PATRON_SPEC.md` is the authority (sections 1-12, with the held-mug shapes and quality examples). Read
the sections your task touches. The essentials:
- A group is 3 variants A, B, C. Each has a **16x16 front view** (3/4, facing right) and a **16x16 back view**. No
  animation frames: walking, pushing and leaving slide the same picture; drinking is the mug sprite plus a 2 px sway.
- 4 indices `.`/`-`/`+`/`#`. **Index 0 is the venue wall**, transparent when lifted: never enclosed inside the figure
  (no holes). Indices 1-3 ordered light to dark. The build checks size, holes, order and lifted columns.
- Read at a glance by silhouette and value, on the DMG against white and on the CGB against the venue's dark wall
  (table in the spec, section 11). Neighbouring features differ in value. No "arrowhead" faces.
- Pictures are mirrored on right-to-left bars: nothing may depend on facing right. On the DMG with mixed directions,
  back views are not mirrored. Saloon A's back view must be symmetric (`tests/test_cowboy_back.py`).
- Saloon A appears on the title (one BG palette, so never enhanced), the credits and the saloon story screens: a new
  A changes more goldens.

## Tiles
- The engine pre-shifts each front view to 8 offsets in a 24x16 footprint: **48 tiles + 4 for the back view = 52 per
  look**; 50 with "option 2" (the unshifted pose's empty third column shares the blank tile). Every pixel column
  trimmed from a 16-px figure saves 2 more.
- VRAM blocks: tiles 0-127 sprite-only, 128-255 shared, 256-383 BG-only. Count the BG budget separately. On CGB,
  bank 1's sprite-only block is a free 128-tile pool for sprite features.
- Patrons walk as BG tiles and are lifted to two 8x16 sprites (from shift 0) only when they overlap: 2 of the 10
  sprites per line.
- Keep tile margin for late decorations, most likely Color-only (owner, 2026-10-22). Don't spend bank-1 margin
  without saying so.

## Palettes
- Every patron look costs **one OBJ palette and one matching BG palette** (same colours 1-3). BG is full in every
  venue, so BG is the binding limit.
- Palettes are per screen and can be reloaded mid-frame (at the playfield's top line).
- Palette swaps on the same tiles give free variety. Put skin in the same colour slot in every figure so looks can
  share palettes; swap a figure's colour slots if needed.
- **Palette labels follow the plan:** "BG1" or "OBJ 2" means that slot as the Palette Plan page shows it now, not
  the shipped game. Look it up in `tools/artifacts/palette_plan/build.py` (PLANS, FIELD_MOVES) before acting.
- The Graphics Atlas page (formerly the Palette Plan; same URL and build.py): edit PLAN / IDEAS / LOG in `build.py`, add a LOG line for each owner decision, run it after
  `make atlas`, republish (see `spigoteer-review-pages`), commit.

## Color and DMG (owner, 2026-10-21 and 10-22)
- The DMG keeps the original 3 looks per venue and the original palettes. Extra looks (up to about 8 per venue) are
  **Color only**, with their tiles in CGB VRAM bank 1. Don't raise DMG tile concerns about the extras.
- Color spawns pick uniformly among the allowed (look, palette) combinations; no extra weighting.
- Patrons keep 1 px movement.
- Enhanced two-palette looks (spec section 3) are being dropped after the next patron revision (QUEUE).

## The owner's art rulings
- Use the `gb-pixel-art` skill and the `gb-artist` agent. Every pixel hand-placed; one figure first, then the rest.
- Proposals first; nothing is imported until the owner picks. After he picks, a quality pass is the default unless
  he says a piece is locked.
- A pass is not a redraw: keep what he likes; fix only flagged problems. Ask how he reads a figure before touching
  details (he once read an "ear" the agent removed).
- Patrons overlap and pass each other; never one shoving another along the bar.
- No credits changes during patron or boss work: the credits remake waits until patrons and bosses are LOCKED.

## Back views (owner, 2026-10-27: "Some of the backs don't seem to understand concepts of what makes a good back sprite. They don't seem to match the characters well.")
- Same person from behind: someone seeing the front and back side by side must match them at once. Build the back
  from the front: keep the head and shoulder outline (hair length, hat or cap shape, ponytail, width) and the colour
  masses (the front's dominant head colour stays dominant).
- Replace the face with what is behind it: hair, or the cap's crown from behind (seam, strap gap), hair down to the
  nape. Skin only as small ear bumps and a narrow neck. No eyes, mouth or brim facing the viewer, and nothing that
  reads as a face, mask, visor or blindfold.
- Clothes carry on from the front: same colours and patterns (stripes, jersey), plus back details (collar, number).
- Judge each back next to its front at 1x and x8 before showing the owner.
- **A back is not the front with the face removed** (owner, 2026-10-27, on robot backs that traced the front's outline
  and blanked the screen: "They are just the sprite with the face removed."). Design what is actually behind the
  figure: rear-only features (for robots: a hatch or access panel, battery pack, wind-up key, cable, exhaust, fins,
  handle; for people: hair, collar, back of the clothes), seen from behind (one-sided details such as an arm stripe
  show on the side they would be on from behind). The silhouette may change where a rear feature sticks out; keep
  the size, head shape and colour masses so the pair still matches. Ask "what would I see walking round him?", not
  "what do I erase?".

## Files
`assets/art/patrons/<group>.txt` and `<group>_back.txt`; `assets/palettes.json` (`<group>_a/_b/_c`);
`tools/gen_art.py` (validates); `src/render.c`, `lift.c`, `mirror.c`, `mugs.c`, `enhance.c`, `patrons.c`;
`make preview` and `make atlas` to see the result.
