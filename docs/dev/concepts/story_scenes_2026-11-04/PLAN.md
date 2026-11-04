# Story cut-scenes: quality-pass plan (2026-11-04)

Owner (2026-11-04): "the quality of the scenes does not match the rest of the game ... make sure that all the scenes are
consistent so that the locations look the same ... move away from ... the little faces on the bottom of the ending scenes ...
something like the crowd outlines in the opening scene ... potentially redesigning the buildings ... adding sprites or
animations ... consistently using the updated sprites for the characters."

Problem ids (1-13) are in AUDIT.md. Mockups: `mockup1_finale_crowd.png`, `mockup2_lumber_cast.png`. Nothing under `src/` or
`assets/` was changed.

## The visual system (five rules)

1. **A venue scene shows the venue as the player knows it**: the game's backdrop (as today) *plus its crowd* (the current
   patron looks) and, where the page names him, its boss. No more empty rooms. (Fixes 7, 11, 13.)
2. **One Festival Square.** `intro_before` is the master. Every square picture (INTRO, FINALE, contest, CREDITS) keeps its
   town, fountain and plaza and changes only the time of day (palette) and the props (people, lights, stand). The plaza is
   always there. (Fixes 2, 3, 6.)
3. **Group shots are silhouettes**, the INTRO's model: dark figures on the plaza, each owner told apart by headgear and shape,
   never small faces. (Fixes 1.)
4. **Only current character art**: Sal = his game sprite (plus the wooly cap from PRE_IGLOO p3 on), Dregs = the v8 sprite,
   patrons = the live patron tiles, bosses = their game art, owners = their portraits (and their silhouettes in group shots).
   A picture that draws a character copies the sprite's pixels. (Fixes 4, 5, 8, 10, 12.)
5. **Motion is cheap and reused**: things the engine already does (stage animation, gags, patron OBJ tiles, the bartender's
   bob) before new systems.

## Venue backdrops

Already canonical: every venue scene calls `load_venue` + `draw_venue` + `write_all_bars`, so each venue looks the same in its
PRE and POST scenes and in its levels. Keep that. The per-venue "Still pictures" table in docs/story.md (saloon front with
swinging doors, igloo under northern lights...) was never built; recommend retiring it (owner question 8) rather than adding
20 one-off illustrations that would each be a new "look" of the venue.

What the backdrop gains (rule 1):

| Item | How | Fits | Cost |
|---|---|---|---|
| Crowd on the bars | Patrons as OBJ (the gag path: `dgag.c` already loads a venue's shift-0 patron tiles to OBJ 98-127 with CGB OBJ palettes 5-7). Two patrons per bar, placed between the portrait frame (ends x 72) and Sal's tap (x 120), so a portrait never covers them; a constant table per venue in ROM. | DMG and Color | OBJ tiles: 3 looks x 6 = 18 (OBJ 98-127, free in a scene); OAM: 6 patrons x 2 = 12 entries; lines: Sal's bar row 2 (Sal) + 4 + 1 (portrait accent) = 7 of 10, other rows 4-5; CPU: set once per scene; WRAM 0 (state in `win_rows` like the gags) |
| Crowd during a gag | The gag page hides the scene crowd (the gag brings its own patrons on bar 0) | both | none |
| Boss cameo on the page that names him | The boss's game pose as OBJ, not BG (his BG palette in fights is a patron slot, 2-4, which the portraits use): a 32x16 boss is 4 OBJ 8x16 wide, 8 OBJ tiles a pose, one CGB OBJ palette (his three colours: an exact fit). Sasquatch HAPPY (PRE_LUMBER p3 behind June, POST_LUMBER p2), Leo with the crown (PRE_ZOO p4, POST_ZOO p2). | both | 8-16 OBJ tiles (OBJ 40-55 are free), 4-8 OAM, +4 sprites on his rows: with 2 patrons and Sal, 10 on Sal's row: put him on a bar without Sal |
| Stage show | The venue's show performers (imported 2026-11-03) dance on the stage during the scene | both | conflicts: the show's OBJ tiles are the portrait accents' range (OBJ_DANCER..127) and its CGB palettes. Phase 5, after the crowd works |

## Group shots (FINALE, FINALE_B, contest)

Mockup 1, built in the real engine: the ten faces go; the plaza comes back (the INTRO's cobble tile, stone at shade 1 and
mortar at shade 2 so the crowd is the only black mass); the ten owners stand on it as a row of ink silhouettes, each by one
signature shape: Sadie's hat brim, Coach's cap bill, June's pom-pom and curls, Colby's toque, Aurora's hood, Manager-Bot's box
and antenna, Granny's bandana knot, Hana's bun, Kiki's helmet, Zizz's drop (floating). 133 tiles, slot 146. DMG and Color.

Then: `finale_contest` is re-derived from the new `finale_a` (as `tools/gen_contest_pic.py` did) with Sal in his cap (4).
FINALE_B shares `finale_a`.

## Buildings and exteriors

The INTRO town is good at night because it is a silhouette with lit windows. By day the same shapes are flat (2). Two steps:

1. **Now (in Phase 1)**: glaze the day windows (mockup 1: the existing window pixels get a sunlit shade-1 glass) and restore the
   plaza. Cheap, tile-neutral.
2. **Redesign (Phase 4)**: one new hand-drawn town master for all four square pictures: three-quarter facades with roof
   planes and eaves, a door or two, an awning, the clock tower kept; built from a small repeated kit (window, wall, roof
   edge) so it costs no more tiles than today (FINALE has 12 spare: 134 of 146; INTRO's burst picture is the tightest).
   Borrow the gabled-house shapes of the Pour-Off's festival venue so the square the player plays in reads as the same place
   (6). Three palettes (night, day, dawn) from one set of pixels.

## Characters: the rule and every mismatch

Rule: story art never redraws a character. A picture copies the sprite's pixels (as `finale_a` and `finale_contest` already
do for Dregs v8); a scene uses the game's own tiles at run time.

| # | Where | Mismatch | Fix |
|---|---|---|---|
| C1 | `intro_a` (INTRO p7-12) | Dregs is the pre-v8 figure (10-17) | copy the v8 idle (and a v8 pose for the burst) |
| C2 | `credits_b` (CREDITS) | Dregs mopping is pre-v8 (10-17) | v8 head and jacket over the apron and mop |
| C3 | `finale_contest` (FINALE_A p4-8) | Sal has no wooly cap | the cap from `finale_a` (owner Q42 B) |
| C4 | every venue scene from PRE_IGLOO p3 | Sal's sprite has no cap; his portrait has | a cap OBJ over his head in scenes (2 OBJ tiles, 1-2 OAM), drawn from the finale cap |
| C5 | `assets/art/dgag/lying.txt`, `ball.txt` | 10-17 head, still marked PROPOSAL | redraw the head from v8; ask the owner to approve |
| C6 | FINALE faces | one-off chibi heads | silhouettes (mockup 1) |
| C7 | CREDITS coffee stand | one-off tiny Sasquatch | his game face at the stand's window, or his cone silhouette |
| C8 | PRE/POST_LUMBER, PRE/POST_ZOO | Sasquatch, Leo never shown | boss cameos (above) |

## Motion

| Item | Where | How | Cost (OAM / tiles / CPU) | Fits |
|---|---|---|---|---|
| M1 Crowd on the bars | every venue scene | static patrons (above), with a 1-px bob in turns on the music beat | 12 OAM, 18 OBJ tiles; a few OAM Y writes every 16 frames | both |
| M2 Sal's idle bob at the tap | every venue scene | the game's `bt_bob` | 0 tiles, negligible CPU | both |
| M3 Portrait blink | every portrait, every few seconds | one closed-eye tile (or two) per portrait swapped in the map in VBlank; eyes only, on the owner's portraits | +1-2 BG tiles each (venue scenes have 24 spare; INTRO's caps are tight: skip there); ~100 B code | both |
| M4 Boss wave | Sasquatch, Leo cameos | his game frames alternated (HAPPY / WALK) | as the cameo | both |
| M5 Fountain jets | INTRO p1-6, FINALE, CREDITS | 2-frame animated BG tiles for the jets | ~6 tiles, a table per picture, ~120 B code shared with M6 | both |
| M6 String lights twinkle | INTRO night | CGB: palette cycle of the bulb colour (0 tiles). DMG: tile swap | Color: 0 tiles; DMG: ~4 tiles | Color first, DMG optional |
| M7 Crowd cheer | FINALE p2 "the crowd gasped" | 3-4 silhouettes raise a hat / arm: tile swap of their cells (BG) | ~6 tiles | both |
| M8 Bus | PRE_SPACE p1-2 | a bus sprite drives in and parks at the airlock | new art: 32x16 OBJ, 8 tiles, 4 OAM | both |
| M9 Stage show | every venue scene | the venue's show | see backdrops | both, Phase 5 |

## DMG vs Color

Everything above works on DMG unless marked: the crowd, the cameos, the cap and the bus use OBP0/OBP1 there (one patron
palette for all looks, as in the gags); M6's palette twinkle is Color-only. Colour-only extras could later live in CGB VRAM
bank 1 if it is free during a scene (question 3 below).

## Budgets

Measured on main 52eff2b1 (this worktree's build):

- **BG ids in a venue scene**: 0-35 venue, 36-76 HUD, 77-92 font, 93-255 portraits (163); busiest scene POST_SALOON 139, so 24
  spare for blinks. Picture scenes: INTRO 141 slot (117 / 112 + 34 burst), FINALE_A 146 (134; mockup 133), CREDITS 132.
- **OBJ ids in a scene**: 0-39 Sal, 40-55 free, 56-127 the gags (POST) or free (PRE).
- **ROM**: banks 1-29 at 7-545 B free; bank 30 has 15,254 B free (the ROM is 512 KB). A new 160x104 picture is about 2.6 KB.
  Code goes in banked story/dgag code (`#pragma bank 255`), never ROM0.
- **ROM0**: 447 B free (linker map). No item needs ROM0.
- **WRAM**: WRAM_LO 160 B, WRAM_HI_0 461 B free; **no new globals**. Scene state goes in `win_rows` (as the gags) or
  `story_scratch`; the scene's static portrait buffers are already `scene_ram`.

Engine changes (all in `src/story.c` / `src/dgag.c` / `tools/gen_story.py`, banked):

| Change | Size (rough) | Phase |
|---|---|---|
| E1 scene crowd: per-venue OBJ placement table, load/hide around gags, beat bob | 200-250 B code, ~40 B data | 2 |
| E2 Sal's cap OBJ after PRE_IGLOO p3 (a page flag from gen_story, like the cozy variant) | ~60 B | 2 |
| E3 boss cameo OBJ per page (`Cast:` line in docs/story.md -> gen_story table) | 150-200 B | 3 |
| E4 portrait blink (closed-eye tile list per portrait in portraits.json) | ~100 B + 1-2 tiles each | 5 |
| E5 picture animated tiles (jets, lights, cheer) | ~150 B + tables | 5 |
| none for Phase 1 or 4 (art only) | 0 | 1, 4 |

## Order of work (one agent per phase)

| Phase | Agent | What | Impact |
|---|---|---|---|
| 1 | gb-artist | Square pictures: mockup 1 finished (crowd, plaza, windows), contest re-derived with the cap (C3), Dregs v8 in `intro_a` and `credits_b` (C1, C2), the credits plaza matched to the master. Art only; goldens for the four pictures change | highest: the ending is the last thing the player sees |
| 2 | gb-worker | E1 + E2: the crowd on the bars in all 20 venue scenes, Sal's cap from PRE_IGLOO p3; tests for line counts and the gag hand-off | high: every venue scene |
| 3 | gb-worker (+ gb-artist for the bus) | E3 boss cameos (Sasquatch, Leo), the bus (M8), C7 coffee stand | medium |
| 4 | gb-artist | Town redesign (one master, three palettes), aligned with the festival venue | medium, larger art job |
| 5 | gb-worker | Motion: blinks (art: closed eyes, owner's portraits, eyes only), jets, lights, cheer, the stage show | polish |
| 6 | gb-artist | C5: the gags' lying and ball Dregs from v8, for approval | low |

## Questions for the owner (with my recommendation)

1. **Finale crowd**: ten ink silhouettes on the plaza (mockup 1) instead of the faces? *Recommend yes.* Variant: five and five
   with a gap under the fountain, if the full row feels heavy.
2. **Day plaza colour**: sandstone (mockup 1; it is the only free colour in that palette) or lilac stone like the night?
   *Recommend sandstone now; the Phase 4 palette plan can revisit it.*
3. **Crowd in the venue scenes** (mockup 2): two patrons per bar, between the portrait and Sal, in every venue scene?
   *Recommend yes, DMG and Color.*
4. **Boss cameos** on the pages that name them (Sasquatch, Leo)? *Recommend yes.*
5. **Sal's cap on his sprite** in the scenes after the igloo (and the contest picture)? Gameplay sprite unchanged?
   *Recommend scenes + contest only.*
6. **Town redesign** borrowing the Pour-Off festival venue's gabled houses, so both read as Festival Square? The festival
   venue itself stays as approved. *Recommend yes, Phase 4.*
7. **Portrait blinks** (one closed-eye tile per portrait, drawn on your portraits, eyes only)? *Recommend yes, Phase 5.*
8. **Retire the per-venue "Still pictures" list** in docs/story.md in favour of "venue + crowd + cameo"? *Recommend yes.*

## Questions for the programmer (working assumptions in brackets)

1. Can the scene crowd reuse the gag's patron OBJ tiles 98-127 and palettes 5-7 in PRE scenes, and be hidden on gag pages?
   (Assumed yes: same loader, `dg_load` runs only for POST scenes.)
2. Is OBJ 40-55 free in every scene (DX badge, pour cue and dust are not used there)? (Assumed yes, per game.h.)
3. Is CGB VRAM bank 1 unused during a scene (no patrons)? (Assumed yes; nothing planned depends on it.)
4. Can a boss pose be drawn as OBJ from his BG tile data with one OBJ palette? (Assumed yes: 3 colours + the wall as
   transparent.)

## Rules this plan follows (gb-pixel-art, read before drawing)

- SKILL.md rule 1: "Decide every pixel yourself." The silhouettes are hand grids; mockup 2 adds no new pixels.
- environments.md: "Give each shade a meaning and keep it game-wide" (shade 3 on the plaza = people only).
- portraits.md: "Make a variant by copying the approved portrait and changing only what the expression needs" (M3 blinks).
- sprites.md: "Give each character one strong, recognisable silhouette element" (one shape per owner in the crowd).
- animation.md: "keep the unchanged 8x8 tiles identical so frames share VRAM" (M3, M5, M7).
- palettes.md: "Each 8x8 background tile uses exactly one palette" (why the new plaza and window keys reuse #f0b888).
- linework.md: "A stray ('orphan') pixel ... is noise" (the clean-up log in AUDIT.md).
- hardware.md: "at most 10 on any scanline" (the crowd and cameo counts above).
