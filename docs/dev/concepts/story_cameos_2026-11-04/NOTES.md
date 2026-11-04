# Story cameos mockup (2026-11-04)

Owner (2026-11-04, plan Q61): "Those are all fine to mock up." Owner (same day, on the bus): "I don't even know that we need a bus
to space honestly the map shows the UFO hovering around a mountain so it would be a bus to the UFO or the UFO beaming him up or
something like that." So PRE_SPACE p1-2 show the UFO beam-up. No bus was built.

Built as sprites in a scratch ROM (a copy of the tree in `out/cam`, main 53a1cb64 + `src/cameo.c` + 3 hook lines in `src/story.c`).
Nothing under `src/` or `assets/` was changed. "Before" is the same tree unchanged (`out/base`), captured at the same frames.

## Sheets

| File | What |
|---|---|
| `sheet_sasquatch.png` | PRE_LUMBER p3, p4; POST_LUMBER p2 (frame 60: hands over the valve; frame 150: ducks off), p3, p4. Before / after, Color over DMG, x3 |
| `sheet_leo.png` | PRE_ZOO p4; POST_ZOO p1, p2 (the crown on Sal), p3 (still crowned) |
| `sheet_ufo.png` | PRE_SPACE p1 (frames 36, 60, 130: beam on, Sal rising, UFO leaving), p2 (frame 60: set down at the tap) |
| `sheet_1x.png` | every after shot at 1x, Color and DMG |
| `beam_preview.png` | the new beam under the map UFO, x4 and 1x, DMG and Color |

## What each page shows

| Page | Text | Cameo |
|---|---|---|
| PRE_LUMBER p3, p4 (extra, the plan names p3) | "who's the big hairy fella behind you?" / "Sasquatch? Ha! No such thing" | Sasquatch HAPPY (waving) with his cone, on the back bar right of the portrait |
| POST_LUMBER p2 | "handed it over, then tiptoed off" | HAPPY beside Sal, the valve up in his raised hand; at frame 90 the valve is on Sal's counter and he sneaks off left in his DUCK pose (crest, brow, eyes over the counter), 1 px tiptoe bob |
| POST_LUMBER p3 | "no such thing as a Sasquatch" | DUCK peeking over the back bar; the valve stays by Sal |
| POST_LUMBER p4 | Dregs: "who's the big hairy fella?" | HAPPY waving on the back bar |
| PRE_ZOO p4 | "the crown is on Leo the lion" | Leo WALK with his crown, back bar |
| POST_ZOO p1 | "the lion approaches... and purrs" | Leo HAPPY (eyes shut, paw up) with the crown, beside Sal |
| POST_ZOO p2, p3 | "Leo placed the crown on the Spigoteer's head" | Leo HAPPY without the crown; the crown on Sal (its band on his hair's top row, as on Leo's mane); p3 Sal keeps it |
| PRE_SPACE p1 | "took the bus to outer space" | the map UFO flies in over Sal (frames 0-29), the beam drops band by band (30-41), Sal rises 15 px (44-73) and vanishes into it, the beam goes (80-91), the UFO leaves left (96+) |
| PRE_SPACE p2 | "it was a very long bus ride" | the same backwards: the UFO arrives from the left and sets Sal down at his tap |

Poses: every boss pixel is his game art, transcribed (`gen_cameo.py` reads `assets/art/boss/sasquatch.txt` HAPPY, DUCK,
HAT_STILL and `leo.txt` WALK, HAPPY, HAT_STILL). The valve is the intro's valve piece (`intro_pieces.txt`), the crown is Leo's
topper, the UFO is `assets/story_map/obj_ufo.png`. **New pixels: the beam only** (`beam.txt`, 24x40). No new boss pose was drawn.

## Costs (measured on the scratch ROM)

| Figure set | OBJ tiles | CGB OBJ palettes | OAM | Worst line (sprites, incl. Sal) |
|---|---|---|---|---|
| Sasquatch (HAPPY 8, DUCK 4, cone 2, valve 4) | 18 | 7 his colours, 6 the valve's gold | 7 (HAPPY 4 + cone 1 + valve 2) | 7 (POST_LUMBER p2, Sal's row) |
| Leo (WALK 8 + HAPPY 6, col 0 shared; crown 2) | 16 | 7 his colours | 5 | 7 (POST_ZOO p1, p2) |
| UFO + beam (UFO 6, beam 12 with mirrored tiles merged) | 18 | 7 (one palette for both: the beam uses the UFO's white and blue) | 12 (UFO 3 + beam 9) | 6 |

Per page, sprites per line (max over rows 0-103) / OAM used, after vs before: PRE_LUMBER p3-4 5/9 (2/4); POST_LUMBER p2 7/11,
p3 4/8, p4 5/11 (2/4); PRE_ZOO p4 5/10 (3/5); POST_ZOO p1 7/10, p2 7/9, p3 3/5 (2-3/4-5); PRE_SPACE p1-2 6/16 (2/4).
With the plan's crowd (two patrons a bar, 4 sprites a row) the cameo rows go to 9 (POST_LUMBER p2, POST_ZOO p1-2: Sal 2 + boss 4
+ cone/crown 1 + crowd 4 = 11 on Sal's row: **over 10**). Rule for E3: the boss stands on a bar with no crowd, or Sal's bar has no
crowd on a cameo page.

Tile ranges in the mockup: Leo at OBJ 40-55 (exactly the free block). The Sasquatch and the UFO took OBJ 98-115 because they
need 18: in a real build they fit 40-55 only if the valve goes (14) or the DUCK goes (14); otherwise use 98-127, which is free
in PRE scenes and in POST_LUMBER (its gag uses 56-89 only). DMG: bosses on OBP1 0xE4 (as in their fights; a PRE scene leaves
the title's 0xC4 in OBP1, so the cameo sets 0xE4 at scene start, LCD off, like `dg_load`); the UFO on OBP0 0xD0 exactly as on
the map; the beam on OBP1 (dark-grey edges, light-grey rings: on OBP0 its white rings vanish on the white DMG lounge wall).

**ROM**: `cameo.c` is one banked area of 2,991 B (tiles 832 B, figure tables ~130 B, palettes and cues ~70 B, code ~1.95 KB:
unoptimised mockup code, int16 maths, closed-form cues). Hooks in `story.c`: 3 calls, about 30 B (`story_c.diff`). ROM0
unchanged (447 B free before and after). WRAM: no new globals (state in `win_rows[4]`, unused in a scene; the cameo object has a
0-byte `_DATA`). Autobank moved modules: banks 13, 27, 29 changed by -91..+217 B, bank 30 lost 2,865 B (15,254 -> 12,389 free).
A real E3 written tight (cue table from `gen_story.py`, 8-bit maths) should be about 0.8-1.2 KB code+data plus the 52 tiles
(832 B); the plan's 150-200 B for E3 was too low.

**story.c changes**: yes, small: `cam_load(s)` after `dg_load` in `scene_enter`, `cam_page(scene, page)` before `dg_page` in
`page_begin`, `cam_frame()` after `dg_frame` in `scene_frame`. The cameo itself lives in its own banked file.

## Answers to the plan's programmer questions

1. **CGB VRAM bank 1 during scenes**: free. Probed on CGB in PRE/POST_LUMBER, PRE/POST_ZOO, PRE_SPACE (page 1): 0 BG cells and
   0 OBJ entries use bank-1 tiles. A scene writes only the bank-1 attribute map. Bank-1 tiles are loaded by the level load
   (Color-only looks) and the show pool, so a scene may overwrite them only if the next level reloads them (it does: `level.c`
   loads them at every level start). Not used by this mockup.
2. **A boss as a sprite with one OBJ palette**: yes. His three colours plus the wall as transparent are an exact fit (Sasquatch
   #E8B878 #5C2C14 #140804, Leo #F8D060 #C86018 #301808); the cone/crown share the palette, as in the fights (OBJ 7). DMG: OBP1
   0xE4 matches the fights' greys.
3. **OAM and sprites per line**: table above. Worst 7 on a line without the crowd; 11 with the crowd on Sal's row (fix: no
   crowd on the cameo's bar). The UFO pages use 16 OAM entries (Sal 4 + UFO 3 + beam 9) and 6 on a line.
4. **ROM and story.c**: above. 3 hook calls in `story.c`; the cameo in its own banked file; ~3 KB as mocked, ~1.6-2 KB done
   properly; bank 30 has room.

## DMG vs Color

All of it fits DMG: same tiles, OBP0/OBP1. Color uses OBJ palettes 6 and 7 (6 only in the lumber scenes, for the gold valve).
Palette writes are at scene start (LCD off); slots 6/7 are free in these scenes (Kiki's accent uses 3; Dregs's gags 1, 2, 5).

## Self-audit (gb-pixel-art section 9)

| Check | PASS/FAIL | Evidence |
|---|---|---|
| Hand-placed | PASS | The beam is my 24x40 grid in `beam.txt`, typed row by row (round 3 rows edited by hand in a list, not computed). Every other pixel is existing approved art transcribed by `gen_cameo.py` (no outlining, mirroring or shading: it only packs 2bpp tiles and merges identical / X-mirrored tiles for storage, which the hardware flip shows back unchanged). |
| Clean-up pass by hand | PASS | Beam log: round 1 -> 2: five rings touching the edges read as a radio mast at 1x; rings cut to three, 1 px off the edges; neck rows 0-3 filled (was 0-2). Round 2 -> 3: ring 1 at rows 12-13 (1-2-1) read as a smiling mouth; moved to rows 15-16 as 2-2-2, ring 2 to 25-26 (3-4-3), ring 3 to 35-36 (4-6-4). Edges kept as clean 1:5 runs, no L-doubles. Placement log: the DUCK on POST_LUMBER p3 moved from the bottom bar (his eyes sat on the text box's edge, only the crest read) to the back bar. |
| 1x comparison | PASS | `sheet_1x.png` and `beam_preview.png`: the beam against the map UFO it hangs from (the quality bar here: the UFO is approved art). The bosses are pixel-identical to their fight art. |
| References read before drawing | PASS | SKILL.md; sprites.md ("Give each character one strong, recognisable silhouette element"); linework.md ("Steps connect diagonally only. Remove L-shaped doubles"); light-and-form.md ("Sprites that never flip ... may follow the scene light"); animation.md ("Move clusters as units between frames"); hardware.md ("at most 10 on any scanline"); palettes.md ("keep index 0 lightest through index 3 darkest"); environments.md ("Scrolling backgrounds stay light"); briefs.md. Figures 03, 04, 11, 12, 15, 17, 18, 20. |
| Lint | PASS | `gb_art_lint.py beam.png --mode dmg --kind sprite --sprite-h 16`: 24x48, 2 colours, 14 tiles exact, 10 with flips merged, RESULT PASS, no warnings. |
| Colours, palettes, tiles | PASS | Costs table: 18 / 16 / 18 OBJ tiles; CGB OBJ palettes 7 (+6 for the valve). |
| Scanline budget | PASS | Worst 7 per line (measured from OAM on every shot); 11 with the plan's crowd on the same row: flagged above. |
| Squint test, DMG and Color | PASS with a doubt | Color: the bosses and the UFO read first on every page. DMG: the beam's edges are dark grey on the white wall and read; its light-grey rings are faint (as a beam should be); the valve on DMG is a dark-grey blob (its gold is idx 1-2). |
| Banding, squares, strays | PASS | Beam: no 2x2 squares (the neck is a 2x4 column of light), no orphans (ring ends join their arcs diagonally). |
| Light direction, flips | PASS | Bosses never flip (as in fights). The beam is symmetric; its right column is the left one flipped in hardware. |
| Tiled preview | n/a | No background tiles. |
| Animation | PASS | Bosses move as whole figures (translation only); the DUCK bob moves the whole figure 1 px. The UFO bobs 1 px every 16 frames, as a hover. No wind-ups (no player action). |
| Footprint | PASS | Boss poses on their bar's two wall rows with the cone/crown 8 rows above, as in the fights. |
| Files | PASS | `beam.txt` grid; `gen_cameo.py` emits the scratch header only. Nothing in `assets/`. |
| Engine questions | listed | Above (answers) and below (new). |

## Deviations from the skill

- None in the new art. Note on mirroring: `gen_cameo.py` stores an X-mirrored duplicate tile once and draws it with the hardware
  flip. The skill allows "hardware flips at runtime"; the pixels in `beam.txt` were all typed, both halves.

## Doubts (judge these)

1. **"Tiptoed off" uses the DUCK pose** (his vanish tell: crest, brow and eyes over the counter) sliding left with a 1-px bob. At 1x
   it reads as a small brown cone with eyes, i.e. "sneaking behind the bar", not clearly "tiptoeing". A true tiptoe needs a new
   side or 3/4 pose (hands up, hunched): the owner's Opus-design area, so not drawn without a go.
2. **The valve** is the intro's 11x14 valve piece. Alone, out of the spigot, it reads as a golden bulb or vase; on DMG as a grey
   blob. It is the only valve art in the game.
3. **The beam-up happens in the space lounge** (the scene's backdrop is the destination), so p1 shows him beamed *up from* the
   lounge and p2 *down into* it. Cleaner: p1 over the story map (the UFO by the mountain), but that is a picture scene, a much
   larger change. The text still says "took the bus" / "very long bus ride": the script needs new lines (owner's words).
4. **Leo on POST_ZOO p1 overlaps nothing but stands 8 px from Sal**; with the crowd plan he must take a bar of his own (above).
5. The Sasquatch on PRE_LUMBER p3-4 was not in the brief (the plan names p3); drop it if unwanted.

## New questions for the programmer (working assumptions in brackets)

1. Story scenes, cue pages: may a cameo use OAM 20-39 (Dregs's gag range) on pages that are never gag pages? (Assumed yes.)
2. POST_ZOO: should the crown stay on Sal's sprite until the scene ends (through the monkeys gag, which needs OAM 20-39)? (Mockup:
   p2-p3 only; a persistent crown would need its own OAM entry outside 20-39, e.g. 19.)
3. PRE_SPACE: may the cue move Sal's own OAM 0-3 (rise, hide) and put them back on the page turn? (Assumed yes: a scene draws Sal
   once at scene start.)
