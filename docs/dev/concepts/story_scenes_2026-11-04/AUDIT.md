# Story cut-scenes: audit (2026-11-04)

Source: every page of the 24 scenes (161 pages) captured from main at 52eff2b1 (`/workspace/out/story_scenes/`, sheets in
`sheets_cgb/`, `sheets_dmg/`), plus mid-animation frames of four Dregs gags. Page ids are `SCENE pN`, 1-based.

Worst offenders, annotated: `audit_worst.png` (the red numbers are the problem ids below).

## How a scene is built today

| Kind | Scenes | Rows 0-12 | Characters on screen |
|---|---|---|---|
| Venue scene | the 20 PRE/POST scenes | the venue's in-game stage + bar rows (`load_venue`, `draw_venue`, `write_all_bars`), its stage animation running, **no patrons** | Sal's game sprite at bar 1's tap; the speaker's 56x56 portrait in a frame on the left; in POST scenes Dregs's exit gag (OBJ, 2-3 s) on the narrator page after his line |
| Picture scene | INTRO, FINALE_A, FINALE_B, CREDITS | a 160x104 picture (`assets/story/pictures/*.txt`) | drawn into the picture; INTRO's ten flying pieces and crackle are OBJ |

The venue scenes are already consistent with each other: every scene at a venue shows the same game backdrop. The quality gap
is elsewhere: the picture scenes disagree with each other and with the current sprites, and the venue scenes are empty rooms.

## The problems (ids used in PLAN.md and on `audit_worst.png`)

| Id | Problem | Pages | DMG / Color |
|---|---|---|---|
| 1 | **The small host faces.** Ten 16x16 chibi heads in a row along the bottom: they match neither the owners' portraits nor any sprite, sit on bare sky (no ground), and read as an icon bar, not people in a square. | FINALE_A p1-8, FINALE_B p1-6 (both pictures: `finale_a`, `finale_contest`) | both |
| 2 | **Hollow town by day.** `finale_a` is the night master re-keyed: the lit windows (`g`) became sky colour, so the town is a flat lilac block with holes in it. The moon and star keys are still there, set to the sky colour. | FINALE_A, FINALE_B | both |
| 3 | **No plaza under the fountain by day.** The cobbles of the INTRO and the CREDITS are missing; the fountain base and the two characters stand on sky. | FINALE_A, FINALE_B | both |
| 4 | **Sal without his wooly cap in the contest picture.** The script says he wears it from PRE_IGLOO p3 to the end; `finale_a` has it (owner Q42 B), `finale_contest` (FINALE_A p4-8) does not. | FINALE_A p4-8 | both |
| 5 | **Old Dregs in two pictures.** `credits_b` and `intro_a` were last drawn 2026-10-17 from the pre-v8 Dregs; the v8 sprite was approved 2026-10-29 and is used by `finale_a`, `finale_contest`, the Pour-Off and the gags. | CREDITS p1-4, INTRO p7-12 | both |
| 6 | **Four Festival Squares.** INTRO (night: detailed town, lit windows, cobbles, crowd silhouettes), FINALE (day: hollow town, no plaza, faces), CREDITS (dawn: own colours, sun disc, cobbles, coffee stand), and the Pour-Off's festival venue that the player plays *at Festival Square* between FINALE_A and FINALE_B (gabled houses, balloons, pennants, no fountain). The fountain and spigot are the only shared parts. | INTRO, FINALE_A/B, CREDITS, the Pour-Off | both |
| 7 | **Empty rooms.** The venue scenes show the bars with nobody on them, so the narrator pages that describe the crowd or a character show an empty bar: "the toughest bar ... all mohawks and studs", "a punk with a green mohawk said please", "the Sasquatch handed it over", "Leo placed the crown on the Spigoteer's head", "who's the big hairy fella behind you?". The game draws these venues full of patrons; the scenes look poorer than the levels they introduce. | PRE_BIKER p1, p6; POST_LUMBER p2; PRE_LUMBER p3; POST_ZOO p2; PRE_ZOO p4; PRE_STADIUM p5-6; every PRE/POST narrator page | both |
| 8 | **Sal's cap is portrait-only.** From PRE_IGLOO p3 the portrait wears the cream wooly cap, but Sal's sprite at the tap (and in the gags) does not. | PRE_IGLOO p3 to POST_SPACE p11 (every venue scene after it) | both |
| 9 | **Travel pages with nothing to see.** "The Spigoteer took the bus to outer space" / "It was a very long bus ride" play over the empty space lounge. | PRE_SPACE p1-2 | both |
| 10 | **Gag poses not approved, old head.** The gags' `lying` and `ball` Dregs (`assets/art/dgag/*.txt`) still carry "PROPOSAL (unapproved)" headers and the 10-17 head; the upright and reaching frames come from the approved v8 sprite. | the POST gags that lay him down or roll him (`lying`, `ball`) | both |
| 11 | **Bosses never appear.** The story names the Sasquatch and Leo (and the Zizz cousin's saucer, which the gag does show), and each has approved game art, but the scenes never show them. | PRE_LUMBER p3, POST_LUMBER p2-3, PRE_ZOO p4, POST_ZOO p2 | both |
| 12 | **Credits coffee stand.** The Sasquatch at the stand is a tiny one-off drawing, not his game art. Low priority. | CREDITS p2 | both |
| 13 | **Static stage.** The venue's stage animation runs, but its show (the dancers and bands imported 2026-11-03) and the stage cat's walk are not in the scenes. | every venue scene | both |

Not problems (keep): the portraits (owner's own art, consistent frame, plate and crop); the venue backdrops (they are the game's);
the INTRO picture (the best scene, the model for the rest); the gags (lively, and they already use the live cowboy and fan
patron tiles); the text box and narrator spigot icon.

## Scene by scene

| Scene | Pages | Shows | Problems |
|---|---|---|---|
| INTRO | 12 | `intro_before` p1-6 (night square, crowd silhouettes, Sal walks in); `intro_a` p7-12 behind a white flash (pieces fly, burst star, crackle); SAL, DREGS portraits | 5 (Dregs in `intro_a`), 6 (master) |
| PRE_SALOON | 5 | Saloon stage (TAPS sign, cat), bars; SADIE, SAL | 7, 13 |
| POST_SALOON | 5 | same; DREGS; p4 gag: two cowboys slide him (current cowboy patrons) | 7, 10 |
| PRE_STADIUM | 7 | Stadium (scoreboard, bunting); COACH, SAL; p5-6 rules pages over empty stands | 7, 13 |
| POST_STADIUM | 6 | p2 soda-bath gag, p5 crowd-surf gag (current sports patrons) | 7, 10 |
| PRE_LUMBER | 5 | Lodge (fireplace, antlers); JUNE, SAL; p3 "who's the big hairy fella behind you?" with nobody behind her | 7, 11 |
| POST_LUMBER | 6 | p2 "the Sasquatch handed it over" over an empty bar; p5 boots gag | 7, 11 |
| PRE_BISTRO | 5 | Bistro (brick, ovens); COLBY, SAL | 7, 13 |
| POST_BISTRO | 7 | p5 plates gag | 7, 10 |
| PRE_IGLOO | 5 | Igloo (ice bricks, lights); AURORA; p3 the cap | 7, 8 |
| POST_IGLOO | 6 | p4 slide gag | 7, 8, 10 |
| PRE_ROBOT | 5 | Factory (ROBOCO sign, gears); MGR-BOT | 7, 8 |
| POST_ROBOT | 7 | p5 conveyor gag | 7, 8, 10 |
| PRE_BIKER | 9 | Chrome Cow (ROCK / MILK signs); GRANNY; p1, p6 describe punks over an empty bar | 7, 8 |
| POST_BIKER | 9 | p6-7 chord arcs, blast | 7, 8 |
| PRE_TEAHOUSE | 8 | Teahouse (shoji, blossom); HANA | 7, 8, 13 |
| POST_TEAHOUSE | 6 | p4 drum gag | 7, 8, 10 |
| PRE_ZOO | 6 | Zoo (hedge, torches); KIKI; p4 "the crown is on Leo the lion" | 7, 8, 11 |
| POST_ZOO | 5 | p2 "Leo placed the crown on the Spigoteer's head" (no Leo, no crown); p4 monkeys gag | 7, 8, 11 |
| PRE_SPACE | 8 | Space lounge (portholes); ZIZZ; p1-2 the bus ride | 7, 8, 9 |
| POST_SPACE | 11 | p7 saucer beam gag, p10 "came down" | 7, 8 |
| FINALE_A | 8 | `finale_a` p1-3 (day square, Sal in cap with his glass, Dregs v8, ten faces); `finale_contest` p4-8 | 1, 2, 3, 4, 6; p2 "the crowd gasped" with no crowd |
| FINALE_B | 6 | `finale_a` again | 1, 2, 3, 6 |
| CREDITS | 4 | `credits_b` (dawn square, Dregs mopping, Sasquatch's coffee stand) | 5, 6, 12 |

## Mockup self-audit (gb-pixel-art section 9)

Mockup 1 (`mockup1_finale_crowd.png`): real engine, a scratch copy of the tree (`out/st`), built and captured on DMG and CGB.
Mockup 2 (`mockup2_lumber_cast.png`): a composite of existing game art (no new pixels).

| Check | Result | Evidence |
|---|---|---|
| Hand-placed | PASS | The ten silhouettes are my 16x14 grids in `mock_finale.py` (FIG), transcribed. The cobbles are the INTRO's approved 8-px cobble tile repeated (allowed: repeating an approved tile), keys changed. The windows are the existing hand-placed window pixels moved to a new key. Mockup 2 pastes only game art (patrons copied from the game's own screenshot, the Sasquatch's HAPPY pose transcribed from `assets/art/boss/sasquatch.txt`). |
| Clean-up by hand | PASS | Log (`mock_finale.py` CLEAN): mortar stubs on head tops (7,89) (39,89) (55,89) (151,89) -> stone; trapped stone (14,93) -> mortar, highlight (32,95) -> stone; Granny's knot (108,94) and Kiki's hair flick (139,98) joined to the head; necks widened by 1 at (58,98) (90,98) (91,98) (122,99) (35,99) (132,98); cobble slivers in the shoulder band filled (0,100) (63,100) (80,100) (16,101) (30,101) (110,101) (112,101); the old Colby face's toque tip (58,86) (58,87) (60,87) -> sky. June redrawn after the first 1x look (she read as a pine tree: pom-pom, flat beanie, wide curls now). |
| 1x comparison | PASS | Against the INTRO's crowd (the quality bar the owner named): same plaza tile, same ink masses below the plaza edge. Changed after comparing: the stone went to shade 1 and the mortar to shade 2 so the crowd is the only shade-3 mass on the plaza (the INTRO uses ink mortar, which on the darker day plaza swallowed the figures). |
| References read first | PASS | SKILL.md; portraits.md, environments.md, sprites.md, animation.md, palettes.md, linework.md, light-and-form.md, hardware.md, briefs.md (see PLAN.md, "Rules this plan follows"). |
| Lint | PASS (warnings) | `gb_art_lint.py --mode dmg --kind bg` on the band (rows 88-103): 0 orphans (was 20 before clean-up), 0 squares; 50 L-doubles = the stepped corners of filled silhouettes, not lines (kept). Whole picture: 38 orphans (all in the unchanged sky: stars, pennants), was 58 with 3 squares in the original. |
| Colours, palettes, tiles | PASS | 4 CGB BG palettes (the picture maximum); 133 unique tiles (picture slot 146; the original 134). The new keys reuse the only free shade-1 colour (#f0b888) of the stone palette. |
| Scanline budget | n/a | Mockup 1 adds no sprites. Mockup 2's plan: PLAN.md "Motion and cast" counts lines. |
| Squint test | PASS | DMG: plaza light grey, mortar dark grey, crowd black, fountain and figures above it unchanged; the crowd reads first, then the spigot. Color: same order. |
| Banding, squares, strays | PASS | lint above; checked the shoulder band at x6. |
| Light direction | n/a | Silhouettes. |
| Tiles: tiled preview | n/a | The cobble tile is the INTRO's, already approved in place. |
| Animation | n/a | None in the mockups. |
| Footprint | PASS | 160x104 picture, same rows; Sal, Dregs, fountain, town and sky untouched. |
| Files | PASS | `finale_a_mockup.txt` is a drop-in portrait-v2 source; nothing under `assets/` changed. |
| Engine questions | listed | PLAN.md "Questions for the programmer". |
