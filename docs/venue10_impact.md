# Spigoteer: the 10th venue and the new order, engine checklist (The Chrome Cow, space last)

Status: PROPOSAL (2026-10-10), awaiting owner approval. A checklist for the engine agent; nothing in src/, tools/,
tests/ or assets/ is changed by this document. Line numbers are as of commit 310b931. The design is in
docs/story.md (chapter 7, PRE_BIKER / POST_BIKER, the proposal tables, the space / zoo text) and
docs/minigames_bosses.md (Duke 3.12, Milk Run 4.10, the mosh pit section 9).

Three owner decisions (2026-10-10) are covered here:
1. A 10th venue, The Chrome Cow (biker bar, milk), before the teahouse.
2. The space lounge moves to the end. The order, in story **and** arcade: 1 saloon, 2 stadium, 3 lumber lodge,
   4 bistro, 5 igloo, 6 robot factory, 7 The Chrome Cow, 8 teahouse, 9 jungle zoo, 10 space lounge.
3. The shift-start goal banner drops the chapter number: its first line is the shift name alone (OPENING SHIFT /
   HAPPY HOUR / LAST CALL), then the goal lines.

## 0. The decision that shapes the rest: one order for every list

Today one index means the same venue everywhere: patron group = theme (venue art) = arcade level row - 1 = story
chapter = tune (`TUNE_VENUE0 + g`) = pour art (`pour_load(story_chapter)`) = gen_story's CHAPTERS `venue` column. Keep
that identity and reorder every list to the new order (a remap table instead was considered and rejected: every one
of those identities would need the map):

| index | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
|---|---|---|---|---|---|---|---|---|---|---|
| group | cowboys | sports | lumberjacks | chefs | divers | robots | **punks** | ninjas | zoo | **aliens** |
| theme | saloon | sports | lodge | bistro | igloo | factory | **biker** | teahouse | zoo | **space** |
| tune (songs.VENUES) | susanna | ballgame | mountain | funicula | skaters | hall | **new** | sakura | weasel | **danube** |
| was | 0 | 1 | 2 | 3 | 4 | 5 | new | 6 | 8 | 7 |

Moves: ninjas / teahouse 6 -> 7, aliens / space 7 -> 9, the zoo keeps index 8. The level-table rows and the story
goals stay with the **position** (difficulty ramp), not with the venue: the zoo takes row 9's numbers (the space
lounge's), space takes the last row's (the zoo's), section 1 item 10.

Names used below: patron group `punks` (variant A mohawk punk, B bandana-and-shades biker, C spiky leather rocker;
CGB mohawks pink, green, blue), theme `biker` (The Chrome Cow), story scene suffix `BIKER`, speaker `GRANNY`, Last
call arrival pattern `chord`, twist `TWIST_MOSH`.

Order of work: the lists (section 1) and story data (section 2) land in one commit with the docs/story.md fold-in,
because gen_story checks the script, the tables and src/level.c against each other. The save migration (section 3)
lands in the same release.

## 1. Venue, group and tune lists

| # | where | assumes | change |
|---|---|---|---|
| 1 | tools/gen_art.py:30 | `PATRON_GROUPS`, 9 groups, aliens at 7, zoo at 8 | the new order: `..., "robots", "punks", "ninjas", "zoo", "aliens"` |
| 2 | tools/gen_art.py:32-33 | `THEMES`, theme index = group index | `..., "factory", "biker", "teahouse", "zoo", "space"` |
| 3 | tools/gen_art.py:747 | `VARIANT_PALS` (only zoo names its palettes) | nothing if the punks use `punks_a/b/c` |
| 4 | Makefile:16 | comment "9 x 2.5 KB" of patron tiles | 10 |
| 5 | Makefile:25 | `PATRON_GROUPS := ... robots ninjas aliens zoo` | `... robots punks ninjas zoo aliens` (the build only needs the set, but keep the order with gen_art) |
| 6 | Makefile:28 | `VENUES := ... factory teahouse space zoo` | `... factory biker teahouse zoo space` |
| 7 | tools/palettes2c.py:31 | `groups` list (= gen_art.PATRON_GROUPS) | the new order |
| 8 | tools/extract_art.py:36-38 | per-group seed palettes | add a `"punks"` entry if the extractor is run for the new group |
| 9 | src/level.c:27 | `LEVEL_ROWS 9` | 10 |
| 10 | src/level.c:60-70 | the level table, 9 rows, column 1 = group | rows by position: 1-6 unchanged; row 7 `{ 6, 0xF, 1, 12, 244, 60, 4, 125, 97 }` (new, midway between rows 6 and 7); row 8 `{ 7, 0xF, 1, 13, 237, 58, 4, 125, 93 }` (the old row 7, ninjas); row 9 `{ 8, 0xF, 1, 15, 223, 56, 3, 150, 87 }` (the zoo with the old row 8's numbers); row 10 `{ 9, 0xF, 1, 16, 210, 52, 3, 150, 80 }` (aliens with the old last row's numbers: the hardest). gen_story.py:149-151 (`level_rows`) reads this table and requires one row per chapter |
| 11 | src/level.c:28-58, :67-69, :84 | comments: per-row group names "7 ninjas, 8 aliens, 9 zoo", "level 10 is row 1 again", "after level 9" | the new names; 11 / 10 |
| 12 | src/music.h:10-12 | `TUNE_COUNT = TUNE_VENUE0 + 9`; the comment's group list (..., ninjas, aliens, zoo) | `+ 10` (better: a generated `VENUES` constant); the new order in the comment |
| 13 | tools/songs.py:282 | `VENUES` in group order (..., "hall", "sakura", "danube", "weasel") | `..., "hall", <new>, "sakura", "weasel", "danube"`; the owner picks the new public-domain piece (minigames_bosses.md question 12), its melody spec goes in docs/music_specs.md |
| 14 | tools/songs.py:1-3, :90 | docstrings "nine venue tunes" | ten |
| 15 | tools/gen_music.py:234 | `ORDER = [...] + [f"venue{i}" for i in range(9)]` | `range(len(songs.VENUES))`; :12 comment "nine venue tunes" |
| 16 | tools/gen_music.py:329-358 | `mus_buf_a` is sized by the largest A-buffer tune | automatic, but a bigger new tune grows WRAM: check the map |
| 17 | src/music.c:96, :178-185; tools/gen_music.py:375-378 | tempo is fixed per tune (hUGEDriver song tempo + the groove's `tempo`) | "the band plays faster" in the biker's Last call: build the tune twice (a `venue6_fast` entry, `TUNE_BIKER_FAST`) or add a tempo override to music.c; the callers below must pick it |
| 18 | src/main_cold.c:183, :215; src/show.c:16; src/story.c:349 | `music_play(TUNE_VENUE0 + cur_group)` / `+ story_hdr.venue` | right once the lists are reordered; the biker's Last call needs the fast tune at level start, after a life and after a show |
| 19 | tools/check_music.py:29, :57-71 | `TUNE_VENUE0 + songs.VENUES.index(source)` | automatic with the reordered VENUES |
| 20 | tools/gen_pour.py:5, :45-48 | one `assets/art/pour/<theme>.txt` per THEMES entry, in THEMES order | add `assets/art/pour/biker.txt`; the table follows the new THEMES order |
| 21 | src/pour.c:41-44 | `pour_venue_tiles[t]`, t = chapter | automatic |
| 22 | src/venue.c:25-28; build/venue_load.c (gen_art.py:429-473) | `venue_fetch(t)` switch | generated; one more bank file `build/venue_biker.c` |
| 23 | src/enhance.c:19 | `x_ids[PATRON_GROUPS]` from art.h | generated; add `punks_x` to palettes.json only if a variant is enhanced |
| 24 | src/lift.c:82, src/level.c:72-82 | `lift_level_init(g)`, `load_patron_group(g)` | generated tables; automatic |

## 2. Story chapters, chapter-number rules and the banner

| # | where | assumes | change |
|---|---|---|---|
| 25 | tools/gen_story.py:42-43 | `SPEAKERS` | add `"GRANNY"` (before NARRATOR) |
| 26 | tools/gen_story.py:67-79 | `CHAPTERS`, 9 rows in the old order | `..., ROBOT (5), ("BIKER", 6, G_SERVE, 22, 0, 0, "SERVE 22 PUNKS", "NO CRYING OVER MILK", "serve 22"), TEAHOUSE (7, unchanged), ("ZOO", 8, G_SERVE, 25, 0, 0, "SERVE 25 ANIMALS", "", "serve 25"), ("SPACE", 9, G_SERVE, 30, 0, 0, "SERVE 30 GLOWING", "BEAKERS", "serve 30")` |
| 27 | tools/gen_story.py:108-119 | `PATTERNS`, one per Last call, all different | add `"chord": [(0, "s"), (1, "s"), (2, "b"), (3, "s"), (2, "s"), (1, "d")]` (three bars at once, a long breather, three more, a shorter one: 1.03 intervals a patron, inside the 0.9-1.15 check) |
| 28 | tools/gen_story.py:125-145 | `SHIFTS`, 9 rows in the old order | after robots: biker `((G_SERVE, 10, 0, 0, 0, "SERVE 10 PUNKS", "ICE COLD MILK", "serve 10"), (G_SERVE, 24, 0, 0, 0, "SERVE 24 PUNKS", "THE BAND SPEEDS UP", "serve 24", "chord", 115, 85))`; teahouse unchanged; zoo `((G_SERVE, 12, 0, 0, 0, "SERVE 12 ANIMALS", "", "serve 12"), (G_SERVE, 28, 0, 0, 0, "STAMPEDE", "SERVE 28 ANIMALS", "serve 28", "stampede", 120, 80))`; space last `((G_SERVE, 15, 0, 0, 0, "SERVE 15 GLOWING", "BEAKERS", "serve 15"), (G_SERVE, 32, 0, 0, 0, "SERVE 32 GLOWING", "BEAKERS", "serve 32", "inside out", 125, 75))` (inside the WALK / SPAWN_RANGE limits) |
| 29 | tools/gen_story.py:719-720 | the per-shift twist byte is always 0 | carry a twist per shift: `TWIST_MOSH` on chapter 7's Happy hour and Last call (owner 2026-10-11) |
| 30 | src/story.c:409, :437-438 | `story_twist` copied, twist hook empty | set `mosh_on` / `mosh_limit` (88 Happy hour, 72 Last call) at the shift start; clear it in every other shift, arcade and the boss (minigames_bosses.md 9.5) |
| 31 | src/patrons.c:287 (`caught`), :375 (`walking_step`), :436 (`push_px`); src/game.h | patrons overlap, never shove | the mosh pit hooks, ~90 B ROM0, 48 B WRAM (minigames_bosses.md 9.5) |
| 32 | src/story.c:401, :406, :411-416 | banner line 1 = `chapter_word` "CHAPTER " + `'1' + story_chapter` + the shift (one digit: chapter 10 would print ':'; `char s[21]`) | **owner: drop the chapter number.** Line 1 is the shift name alone: delete `chapter_word` and the digit, centre `shift_name[story_shift]` directly (no `s[]` buffer needed). This also removes the two-digit problem |
| 33 | tools/gen_story.py:96, :884 | `SHIFT_NAMES = ["OPENING", "HAPPY HOUR", "LAST CALL"]` (SHIFT was left out to fit "CHAPTER n ") | `["OPENING SHIFT", "HAPPY HOUR", "LAST CALL"]` |
| 34 | tools/gen_story.py:196-197 | checks `CHAPTER {c + 1} {name}` <= 20 | check the shift name alone (13 / 10 / 9) |
| 35 | tools/gen_story.py:294, :305 | table regexes `^\| (\d) \|`: one digit | `(\d+)`, or chapter 10's rows are never read |
| 36 | tools/gen_story.py:290 | scene order INTRO, PRE/POST per CHAPTERS, FINALE, CREDITS | follows CHAPTERS; docs/story.md's scenes must be in the new order (item 77) |
| 37 | tools/gen_story.py:875 | `STORY_CHAPTERS` = len(CHAPTERS); SC_PRE = 1 + 2c, SC_POST = 2 + 2c | automatic (10); story.c:477, :491, :508 follow |
| 38 | src/story.c:3-5, :66 | comments "c (0..8)", "after chapter 9's POST", "0..8" | 0..9, chapter 10 |
| 39 | src/story.c:10-11, :544-545 | comments: strict rules "chapter 2 / 7", "chapter 7's strict rule" | 2 / 8. The rules are data (`F_NO_TAP` / `F_NO_BREAK`), so they move with the teahouse's row: no code change |
| 40 | tools/gen_story.py:85-88 | CONDITIONS comment "the strict rule's event in chapter 7" | chapter 8. `GLASS_BROKEN` is set in any chapter (story.c:544) and only POST_TEAHOUSE has the variant: no code change |
| 41 | tools/gen_story.py:22 | docstring "nine different ones" (Last call patterns) | ten |
| 42 | assets/story/portraits.json; assets/story/portraits/granny.txt | 13 portraits; a speaker without art fails the build | add GRANNY (56x56, style S3, proposal first). The SPIGOTEER COZY range (PRE_IGLOO:3 to the end) and DREGS SORRY (FINALE:4) need no change |

## 3. Save (SRAM, src/save.c)

| # | where | assumes | change |
|---|---|---|---|
| 43 | src/save.c:3-19 (layout comment), :33 | byte 34 = chapters cleared 0..9 (9 = the story complete) | 0..10. The design's "Pour-Off won" value (minigames_bosses.md 2.2, not built) becomes 11 |
| 44 | src/save.c:42, :85-88 | `STORY_MAX = STORY_CHAPTERS`; v4 valid if byte 34 <= 9 and byte 35 == 0 at 9 | automatic with 10, which is why the version must change: an old 7 meant "teahouse cleared", a new 7 means "biker bar cleared"; old 8 meant "teahouse and space cleared", which the new order cannot even express |
| 45 | src/save.c:4, :57, :84, :122-123, :143 | magic "TPR4" | version 5, "TPR5" |
| 46 | src/save.c:122-131 | migrations v3 -> v4, v2, v1 | add v4 -> v5 (`save_migrated = 4`) and send v3 through the same mapping: byte 34 p <= 5 kept, byte 35 kept; **p >= 6 becomes 6 with byte 35 = 0** (the first chapter not cleared is now The Chrome Cow; an old byte 35 at p = 6 counted the teahouse's steps). Recommended (minigames_bosses.md question 13): the old chapters 7-9 are 8, 10, 9 in the new order, so no count above 6 maps onto it; going back to chapter 7 keeps the story whole |
| 47 | src/music.h:58 | comment "story chapters cleared (0..9)" | 0..10 |
| 48 | src/title.c:189 | CONTINUE while progress < STORY_CHAPTERS | automatic; a migrated complete save (9 -> 6) shows CONTINUE again, which is intended |

## 4. Arcade rotation

| # | where | assumes | change |
|---|---|---|---|
| 49 | src/level.c:97-99 | `cur_group = idx % LEVEL_ROWS`, `arcade_loop = idx / LEVEL_ROWS + 1` | automatic with LEVEL_ROWS 10 and the reordered rows: the rotation is the new order; loop 2 starts at level 11, loop 3 at 21 |
| 50 | src/main.c:394 | the bonus round after every even level | still works, but with 10 venues a loop it always follows the same venues (sports, bistro, factory, teahouse, space); with 9 it alternated by loop. Owner's call; no code change for the plain rule |
| 51 | src/main_cold.c:184 | "LOOP n" banner when `cur_group == 0 && level > 1` | automatic |
| 52 | src/debug.c:10 | `DEBUG_LEVELS 18` (two loops) | 20 |
| 53 | Title screen and credits | src/title.c draws no venue list; the story CREDITS scene names no count or order | no change. CREDITS.md does (item 80) |

## 5. Art, palettes, banks

| # | where | change |
|---|---|---|
| 54 | assets/art/patrons/punks.txt, punks_back.txt (+ the approved copies assets/approved/punks.txt, punks_back.txt) | the 3 looks, fronts and backs (proposals first; art is in-house) |
| 55 | assets/approved/venues/biker_{stage,anim,attr,bar,bar_attr,drink,drink_pal,floor,pal,show,show_pal} | the 11 venue files every theme has; the bar set must leave one of the 36 venue-pool ids for the mosh pit's counter splash tile |
| 56 | assets/palettes.json (+ assets/approved/palette_overrides.json) | `punks_a` / `punks_b` / `punks_c` (pink, green, blue mohawks; colour 0 is the wall at load) |
| 57 | ROM banks | one more venue bank file, one more patron bank file (~2.5 KB), the tune's patterns (bank 3 has 15 B free today: the blob may need another bank), ~1.5 KB more story text, ~90 B ROM0 for the mosh pit (1605 B real free at 310b931): check `romusage`. Banks 1-7 are full, bank 8 has ~13 KB free; autobank places the new files |

## 6. Tests

| # | where | assumes | change |
|---|---|---|---|
| 58 | tests/test_story.py:78 | `text_bytes < 7000` (5943 today) | the new scenes, the PRE_TEAHOUSE page and the longer POST_SPACE add ~1.5 KB: raise the cap with the bank check |
| 59 | tests/test_story.py:124, :669, :700, :824, :938, :1166 | `range(9)`, `list(range(9))` | 10 |
| 60 | tests/test_story.py:690, :693, :810-816, :1201-1205 | the last chapter is 8 (`c == 8`, `to_shift(model, 8, 2)`, `post(8)`, `story_progress == 9`) | 9 (the space lounge), progress 10 |
| 61 | tests/test_story.py:794, :813, :1240 | banners "CHAPTER 1 OPENING", "CHAPTER 9 LAST CALL" | "OPENING SHIFT", "LAST CALL" (item 32) |
| 62 | tests/test_story.py:703, :755 | 27 portrait pairs; 9 different Last call patterns | recount with GRANNY; 10 |
| 63 | tests/test_story.py:1049-1115 | the teahouse is chapter index 6 (`to_chapter(model, 6)` x3, `to_shift(model, 6, 1)`, "Chapter 7") | 7 / chapter 8 |
| 64 | tests/test_story.py:864, :1228, :1309-1337; tests/test_scores.py:51-63 (`v4_image`, `parse_save`); tests/test_sound.py:541-565 | "TPR4", v4 bad-save cases `(10, 0), (2, 5), (9, 1)`, `(7, 3)` | TPR5; keep a v4 builder for the migration tests (4 with its step kept; 7 -> 6 with step 0; 9 -> 6); bad v5 cases (11, 0), (10, 1) |
| 65 | tests/test_art.py:9, :20 | `GROUPS` list in the old order, "(level - 1) % 9" | the new order; % 10 |
| 66 | tests/test_venues.py:30-31, :94, :133, :176, :212, :144 | `GROUP_THEME`, `range(9)`; `[0, 1, 4, 7]` with id "space" | add `"punks": "biker"`; range(10); space is index 9 now |
| 67 | tests/test_sound.py:20-21, :428, :437, :656, :693 | `TUNE_COUNT = TUNE_VENUE0 + 9`, `range(9)`, per-group tunes in the old order | 10; the tune of group g follows the new VENUES order |
| 68 | tests/test_stage_anim.py:75 | the set of 9 animated themes | add biker (if its stage animates) |
| 69 | tests/test_edge.py:273 | `range(1, 10)` (one loop of levels) | `range(1, 11)` |
| 70 | tests/test_debug.py:76-78, :106 | wraps at 18; `(lvl - 1) % 9` | 20; % 10 |
| 71 | tests/test_flow.py:17-23, :475-476, :486, :495 | the level TABLE (9 rows, old order), `% 9`, `// 9`, "LOOP 2 banner before level 10" | the 10 rows of item 10; 10; level 11 |
| 72 | tests/test_scores.py:1-2, :205-215, :248-262 | "after level 9", `to_level(gb, 10)`, HUD "L10", loop levels (1, 9, 10, 18, 19, 27, 28, 36, 37, 45, 46, 54), `% 9`, `// 9` | level 11, "L11"; (1, 10, 11, 20, 21, 30, 31, 40, 41, 50, 51, 60); 10 |
| 73 | tests/test_enhanced.py:237-244 | "level 18 (zoo) -> bonus -> level 19 (cowboys, loop 3)" | level 20 (space) -> 21 |
| 74 | tests/perf_helpers.py:166-196, :321, :443; tests/test_perf.py:60 | level 9 is the fastest row (the zoo), reached from level 8 through its bonus round | level 10 (space, the aliens), reached from level 9 (odd: no bonus round between); `target=9` -> 10. The perf numbers in PLAN.md were measured with the zoo's art on the fastest row; re-measure with the aliens |
| 75 | tests/test_pour.py:213 | chapters `[0, 5]` | unchanged (saloon, factory) |
| 76 | new: tests/test_twists.py; tests/test_boss.py `test_duke_*`; the Milk Run tests | | as listed in minigames_bosses.md 9.6, 3.12 and 4.10 |

## 7. Goldens (CLAUDE.md rule 3: name every replaced golden and why in its commit)

| golden | expectation |
|---|---|
| venue_biker, patrons_punks, stage_anim_biker (if animated), a GRANNY tour golden (optional) | new: add freely |
| story_goal | **replaced on purpose**: the banner's first line reads OPENING SHIFT instead of CHAPTER 1 OPENING |
| story_last_call | **replaced on purpose**: the banner reads LAST CALL, and the last chapter is now the space lounge (its venue, patrons and goal SERVE 32 GLOWING BEAKERS), not the zoo |
| loop_banner | **replaced on purpose**: LOOP 2 comes at level 11, so the HUD's level reads L11 |
| story_hana_not_one, story_hana_so_few | unchanged once the tests point at chapter index 7 (same POST_TEAHOUSE pages) |
| venue_space, venue_zoo, venue_teahouse, patrons_aliens, patrons_zoo, patrons_ninjas, stage_anim_space, stage_anim_zoo, stage_anim_teahouse | unchanged pictures (named by theme / group); the tests that reach them by index must use the new index |
| level2, crash_saloon, crash_factory | unchanged (levels and venues 1-6 keep their place) |
| story_zizz (PRE_SPACE page 3), story_dregs_sorry (FINALE page 4) | unchanged: those pages keep their text and place (the new PRE_SPACE page comes after page 5) |
| story_two_lives, story_bonus_life, story_narrator, story_portrait, story_dregs, story_spigoteer, story_aurora, story_spigoteer_cozy, story_managerbot | unchanged |
| title, title_anim, title_continue | unchanged |

## 8. Docs outside this change

| # | where | change |
|---|---|---|
| 77 | docs/story.md | fold the PROPOSAL in with the gen_story change: the scenes in the new order (PRE/POST_BIKER after POST_ROBOT; PRE/POST_SPACE moved after POST_ZOO), `PROPOSAL` dropped from the two new headings, the `text` blocks' pages put into their scenes (INTRO 6-8, POST_SALOON 5, PRE_TEAHOUSE's new page 4, POST_TEAHOUSE's last page, PRE_ZOO 4-5, the whole POST_ZOO, PRE_SPACE's new page 6 and goal page, the whole POST_SPACE, FINALE 1 and 7), the chapters and shifts tables replaced by the 10-row versions in the new order, the top note dropped |
| 78 | docs/minigames_bosses.md section 6 | "Art volume: 9 bosses ... 9 mini-game sets" and the ~60 KB total: 10 (left for the agent editing section 6) |
| 79 | docs/music_specs.md | the new tune's melody spec |
| 80 | CREDITS.md:29, :38-46 | "the other nine tunes" -> ten; "level 1, 10, ..." -> "level 1, 11, ..."; a row for the new tune; the table in the new venue order (space last) |
| 81 | PLAN.md | see the list below (not edited here: another agent is editing PLAN.md) |

PLAN.md lines that state 9 venues / chapters, a chapter number that moves, or the old banner:
- :176 "nine venue tunes"; :262 (M10b) "endless loop of the nine venues"; :265 (M11c) "nine venue owners".
- :756 "After chapter 9's POST: FINALE"; :770 "goal_t.twist (0 for all nine now)"; :772 "chapters cleared 0..9".
- :808 "the nine Last call patterns all different"; :837-839 the banner "CHAPTER n " + the shift, "CHAPTER 1 OPENING
  SHIFT would be 23 characters, so the word SHIFT is left out" (now: the shift name alone, OPENING SHIFT).
- :844-845 SRAM v4 "34 chapters cleared (0-9)", "must be 0 when 9 chapters are cleared"; :848 "CONTINUE ... when
  chapters 1-8 are cleared".
- :858 and :868 "chapter 9's Last call" / "chapter 9 Happy hour" (bot runs on the zoo, which keeps index 9 but with
  smaller goals now; the hardest chapter is the space lounge); :871 "nine patterns"; :873 "golden story_last_call,
  chapter 9"; :880 "the banner now says CHAPTER 1 OPENING".
- "Story lives as built": :949 "chapter 7: a broken glass, F_NO_BREAK"; :958 "BROKEN CUP COSTS TWO (chapter 7)";
  :987 "chapters 2 and 7"; :994 "chapter 9's Last call".
- "Story page text variants as built": :1009 "chapter 7's two lives"; :1014 "chapter 7".
- Not changing: :780 chapter 6 (the factory stays 6); :946 chapters 4, 5; :1075 chapters 1, 6.

## Count

81 items: 24 list entries, 18 story / chapter-number / banner rules, 6 save, 5 arcade, 4 art and banks, 19 test
entries, 5 docs; plus the goldens table (3 to replace on purpose: story_goal, story_last_call, loop_banner; 3-4 new).
