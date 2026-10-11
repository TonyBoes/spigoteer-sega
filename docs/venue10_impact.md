# Spigoteer: the 10th venue, engine checklist (The Chrome Cow)

Status: PROPOSAL (2026-10-10), awaiting owner approval. A checklist for the engine agent; nothing in src/, tools/,
tests/ or assets/ is changed by this document. Line numbers are as of commit 310b931. The design is in
docs/story.md (chapter 7, PRE_BIKER / POST_BIKER, the proposal tables) and docs/minigames_bosses.md (Duke 3.12,
Milk Run 4.10, the mosh pit section 9).

## 0. The one decision that shapes the rest: insert at index 6

Today one index means the same venue everywhere: patron group = theme (venue art) = arcade level row - 1 = story
chapter = tune (`TUNE_VENUE0 + g`) = pour art (`pour_load(story_chapter)`) = gen_story's CHAPTERS `venue` column. The
owner wants the biker bar before the teahouse in story **and** arcade order, so insert it at **index 6 in every list**:
ninjas / teahouse move 6 -> 7, aliens / space 7 -> 8, zoo 8 -> 9. Appending it at index 9 with a remap table was
considered and rejected: every identity above would need the map.

Names used below: patron group `punks` (variant A mohawk punk, B bandana-and-shades biker, C spiky leather rocker;
CGB mohawks pink, green, blue), theme `biker` (The Chrome Cow), story scene suffix `BIKER`, speaker `GRANNY`, Last
call arrival pattern `chord`, twist `TWIST_MOSH`.

Order of work: the lists (section 1) and story data (section 2) must land in one commit with the docs/story.md
fold-in, because gen_story checks the script, the tables and src/level.c against each other. The save migration
(section 3) lands in the same release.

## 1. Venue, group and tune lists

| # | where | assumes | change |
|---|---|---|---|
| 1 | tools/gen_art.py:30 | `PATRON_GROUPS`, 9 groups | insert `"punks"` at index 6 |
| 2 | tools/gen_art.py:32-33 | `THEMES`, 9 themes, theme index = group index | insert `"biker"` at index 6 |
| 3 | tools/gen_art.py:747 | `VARIANT_PALS` (only zoo names its palettes) | nothing if the punks use `punks_a/b/c`; add an entry only for other names |
| 4 | Makefile:16 | comment "9 x 2.5 KB" of patron tiles | 10 |
| 5 | Makefile:25 | `PATRON_GROUPS := ... ninjas aliens zoo` | insert `punks` after `robots` |
| 6 | Makefile:28 | `VENUES := ... teahouse space zoo` | insert `biker` after `factory` |
| 7 | tools/palettes2c.py:31 | `groups` list (= gen_art.PATRON_GROUPS) | insert `"punks"` at 6 |
| 8 | tools/extract_art.py:36-38 | per-group seed palettes | add a `"punks"` entry if the extractor is run for the new group |
| 9 | src/level.c:27 | `LEVEL_ROWS 9` | 10 |
| 10 | src/level.c:60-70 | the level table, 9 rows, column 1 = group | insert row 7 `{ 6, 0xF, 1, 12, 244, 60, 4, 125, 97 }` (midway between robots and ninjas, so every existing venue keeps its own difficulty) and renumber the group column of ninjas / aliens / zoo to 7 / 8 / 9; gen_story.py:149-151 (`level_rows`) reads this table and requires one row per chapter |
| 11 | src/level.c:28-58, :69, :84 | comments: "level 10 is row 1 again", "after level 9 the venues come round" | 11 / 10 |
| 12 | src/music.h:10-12 | `TUNE_COUNT = TUNE_VENUE0 + 9`; the comment's group list | `+ 10` (better: a generated `VENUES` constant); add punks to the list |
| 13 | tools/songs.py:282 | `VENUES` (9 tunes in group order) | insert the new tune at index 6; owner picks a public-domain piece (minigames_bosses.md question 12) and its melody spec goes in docs/music_specs.md |
| 14 | tools/songs.py:1-3, :90 | docstrings "nine venue tunes" | ten |
| 15 | tools/gen_music.py:234 | `ORDER = [...] + [f"venue{i}" for i in range(9)]` | `range(len(songs.VENUES))`; :12 comment "nine venue tunes" |
| 16 | tools/gen_music.py:329-358 | `mus_buf_a` is sized by the largest A-buffer tune | automatic, but a bigger new tune grows WRAM: check the map |
| 17 | src/music.c:96, :178-185; tools/gen_music.py:375-378 | tempo is fixed per tune (hUGEDriver song tempo + the groove's `tempo`) | "the band plays faster" in Last call: either build the tune twice (a `venue6_fast` entry, `TUNE_BIKER_FAST`) or add a tempo override to music.c; the callers below must pick it |
| 18 | src/main_cold.c:183, :215; src/show.c:16; src/story.c:349 | `music_play(TUNE_VENUE0 + cur_group)` / `+ story_hdr.venue` | the index is right after the insert; the biker's Last call needs the fast tune at level start, after a life and after a show |
| 19 | tools/gen_pour.py:5, :45-48 | one `assets/art/pour/<theme>.txt` per THEMES entry | add `assets/art/pour/biker.txt` (the milk glass's sparkle and overflow, proposal first) |
| 20 | src/pour.c:41-44 | `pour_venue_tiles[t]`, t = chapter | automatic with the insert |
| 21 | src/venue.c:25-28; build/venue_load.c (gen_art.py:429-473) | `venue_fetch(t)` switch | generated; one more bank file `build/venue_biker.c` |
| 22 | src/enhance.c:19 | `x_ids[PATRON_GROUPS]` from art.h | generated; add `punks_x` to palettes.json only if a variant is enhanced |
| 23 | src/lift.c:82, src/level.c:72-82 | `lift_level_init(g)`, `load_patron_group(g)` | generated tables; automatic |

## 2. Story chapters and chapter-number rules

| # | where | assumes | change |
|---|---|---|---|
| 24 | tools/gen_story.py:42-43 | `SPEAKERS` | add `"GRANNY"` (before NARRATOR); speaker ids are generated |
| 25 | tools/gen_story.py:67-79 | `CHAPTERS`, 9 rows, venue column 0-8 | insert `("BIKER", 6, G_SERVE, 22, 0, 0, "SERVE 22 PUNKS", "NO CRYING OVER MILK", "serve 22")` after ROBOT; TEAHOUSE / SPACE / ZOO venue 7 / 8 / 9 |
| 26 | tools/gen_story.py:108-119 | `PATTERNS`, one per Last call, all different | add `"chord": [(0, "s"), (1, "s"), (2, "b"), (3, "s"), (2, "s"), (1, "d")]` (three bars at once, a long breather, three more, a shorter one: 1.03 intervals a patron, inside the 0.9-1.15 check) |
| 27 | tools/gen_story.py:125-145 | `SHIFTS`, 9 rows | insert `((G_SERVE, 10, 0, 0, 0, "SERVE 10 PUNKS", "ICE COLD MILK", "serve 10"), (G_SERVE, 24, 0, 0, 0, "SERVE 24 PUNKS", "THE BAND SPEEDS UP", "serve 24", "chord", 115, 85))` after the robots' row |
| 28 | tools/gen_story.py:719-720 | the per-shift twist byte is always 0 | carry a twist per shift (CHAPTERS / SHIFTS gain a twist field): `TWIST_MOSH` on chapter 7's Happy hour and (if approved) Last call |
| 29 | src/story.c:409, :437-438 | `story_twist` copied, twist hook empty | set `mosh_on` / `mosh_limit` (88 Happy hour, 72 Last call) at the shift start; clear it in every other shift, arcade and the boss (minigames_bosses.md 9.5) |
| 30 | src/patrons.c:287 (`caught`), :375 (`walking_step`), :436 (`push_px`); src/game.h | patrons overlap, never shove | the mosh pit hooks, ~90 B ROM0, 48 B WRAM (minigames_bosses.md 9.5); the only venue-specific rule in the hot path |
| 31 | tools/gen_story.py:196 | banner line `CHAPTER {c + 1} {shift}` <= 20 | "CHAPTER 10 HAPPY HOUR" is 21: the build fails. Pick a form (e.g. "CH 10 HAPPY HOUR" for two-digit chapters, or drop "CHAPTER" everywhere); OPENING (18) and LAST CALL (20) fit |
| 32 | src/story.c:414 | `s[i++] = '1' + story_chapter;` one digit | chapter 10 prints ':' (the character after '9'): write two digits |
| 33 | src/story.c:406 | `char s[21]` | the 21-character "CHAPTER 10 HAPPY HOUR" + NUL overflows it unless item 31 shortens the line |
| 34 | tools/gen_story.py:294, :305 | table regexes `^\| (\d) \|`: one digit | `(\d+)`, or chapter 10's rows are never read (the row count check fails) |
| 35 | tools/gen_story.py:290 | scene order INTRO, PRE/POST per CHAPTERS, FINALE, CREDITS | automatic once docs/story.md's `### PROPOSAL PRE_BIKER` / `POST_BIKER` headings drop `PROPOSAL` (item 61) |
| 36 | tools/gen_story.py:875 | `STORY_CHAPTERS` = len(CHAPTERS); SC_PRE = 1 + 2c, SC_POST = 2 + 2c | automatic (10); every `SC_* + 2 * story_chapter` in story.c:477, :491, :508 follows |
| 37 | src/story.c:3-5, :66 | comments "c (0..8)", "after chapter 9's POST", "0..8" | 0..9, chapter 10 |
| 38 | src/story.c:10-11, :544-545 | comments: strict rules "chapter 2 / 7", "chapter 7's strict rule" | 2 / 8. The rules themselves are data (`F_NO_TAP` / `F_NO_BREAK` in CHAPTERS / SHIFTS), so they move with the teahouse's row: no code change |
| 39 | tools/gen_story.py:85-88 | CONDITIONS comment "the strict rule's event in chapter 7" | chapter 8. `GLASS_BROKEN` itself is set in any chapter (story.c:544) and only POST_TEAHOUSE has the variant, so Hana's text variant needs no code change |
| 40 | tools/gen_story.py:22 | docstring "nine different ones" (Last call patterns) | ten |
| 41 | assets/story/portraits.json; assets/story/portraits/granny.txt | 13 portraits, a speaker without art fails the build | add GRANNY (56x56, approved style S3, proposal to the owner first). The SPIGOTEER COZY variant range (from PRE_IGLOO:3 to the end) covers the new scenes by itself |

## 3. Save (SRAM, src/save.c)

| # | where | assumes | change |
|---|---|---|---|
| 42 | src/save.c:3-19 (layout comment), :33 | byte 34 = chapters cleared 0..9 (9 = the story complete) | 0..10. The design's "Pour-Off won" value (docs/minigames_bosses.md 2.2, not built) becomes 11 |
| 43 | src/save.c:42, :85-88 | `STORY_MAX = STORY_CHAPTERS`; v4 valid if byte 34 <= 9 and byte 35 == 0 at 9 | automatic with STORY_CHAPTERS 10, which is why the version must change: an old save's 7 means "teahouse cleared", a new 7 means "biker bar cleared" |
| 44 | src/save.c:4, :57, :84, :122-123, :143 | magic "TPR4" | version 5, "TPR5" |
| 45 | src/save.c:122-131 | migrations v3 -> v4, v2, v1 | add v4 -> v5 (`save_migrated = 4`) and send v3 through the same mapping: byte 34 p <= 5 kept, byte 35 kept; **p >= 6 becomes 6 with byte 35 = 0** (the first chapter not cleared is now The Chrome Cow; an old byte 35 counted steps of the teahouse and means nothing for it). Recommended so the story never skips the drip tray; the owner decides (minigames_bosses.md question 13). The alternative, p >= 7 -> p + 1, keeps the player's place but skips chapter 7 |
| 46 | src/music.h:58 | comment "story chapters cleared (0..9)" | 0..10 |
| 47 | src/title.c:189 | CONTINUE while progress < STORY_CHAPTERS | automatic; a migrated complete save (9 -> 6) shows CONTINUE again, which is intended |

## 4. Arcade rotation

| # | where | assumes | change |
|---|---|---|---|
| 48 | src/level.c:97-99 | `cur_group = idx % LEVEL_ROWS`, `arcade_loop = idx / LEVEL_ROWS + 1` | automatic with LEVEL_ROWS 10: loop 2 starts at level 11, loop 3 at 21 |
| 49 | src/main.c:394 | the bonus round after every even level | still works, but with 10 venues a loop it always follows the same venues (sports, bistro, factory, teahouse, zoo); with 9 it alternated by loop. Owner's call; no code change for the plain rule |
| 50 | src/main_cold.c:184 | "LOOP n" banner when `cur_group == 0 && level > 1` | automatic |
| 51 | src/debug.c:10 | `DEBUG_LEVELS 18` (two loops) | 20 |
| 52 | Title screen and credits | src/title.c draws no venue list; the story CREDITS scene names no count | no change. CREDITS.md does (item 63) |

## 5. Art, palettes, banks

| # | where | change |
|---|---|---|
| 53 | assets/art/patrons/punks.txt, punks_back.txt (+ the approved copies assets/approved/punks.txt, punks_back.txt, as the other groups have) | the 3 looks, fronts and backs (proposals first; art is in-house) |
| 54 | assets/approved/venues/biker_{stage,anim,attr,bar,bar_attr,drink,drink_pal,floor,pal,show,show_pal} | the 11 venue files every theme has (stage with the neon cow, the bar, a milk-glass drink and its crash, the house band as the show performers); the bar set must leave one of the 36 venue-pool ids for the mosh pit's counter splash tile |
| 55 | assets/palettes.json (+ assets/approved/palette_overrides.json) | `punks_a` / `punks_b` / `punks_c` (pink, green, blue mohawks; colour 0 is the wall at load); `punks_x` only if a variant is enhanced |
| 56 | ROM banks | one more venue bank file, one more patron bank file (~2.5 KB), the tune's patterns (bank 3 has 15 B free today: the blob may need another bank), ~1 KB more story text, ~90 B ROM0 for the mosh pit (1605 B real free at 310b931): check `romusage`. Banks 1-7 are full, bank 8 has ~13 KB free; autobank places the new files, `-Wm-yoA` sizes the ROM |

## 6. Tests

| # | where | assumes | change |
|---|---|---|---|
| 57 | tests/test_story.py:78 | `text_bytes < 7000` (5943 today) | the new scenes and the PRE_TEAHOUSE page add ~1 KB: about 6950; raise the cap with the bank check |
| 58 | tests/test_story.py:124, :669, :700, :824, :938, :1166 | `range(9)`, `list(range(9))` | 10 |
| 59 | tests/test_story.py:690, :693, :810-813, :1201-1205 | the last chapter is 8 (`c == 8`, `to_shift(model, 8, 2)`, `post(8)`, `story_progress == 9`, banner "CHAPTER 9 LAST CALL") | 9, progress 10, the new two-digit banner text |
| 60 | tests/test_story.py:703, :755 | 27 portrait pairs; 9 different Last call patterns | recount with GRANNY; 10 |
| 61 | tests/test_story.py:1049-1115 | the teahouse is chapter index 6 (`to_chapter(model, 6)` x3, `to_shift(model, 6, 1)`, `teahouse_post` docstring "Chapter 7") | 7 / chapter 8 |
| 62 | tests/test_story.py:864, :1228, :1309-1337; tests/test_scores.py:51-63 (`v4_image`, `parse_save`); tests/test_sound.py:541-565 | "TPR4", v4 bad-save cases `(10, 0), (2, 5), (9, 1)`, `(7, 3)` | TPR5; keep a v4 builder for the migration tests (progress 4 with its step kept; 7 -> 6 with step 0; 9 -> 6); bad v5 cases (11, 0) and (10, 1) |
| 63 | tests/test_art.py:9, :20 | `GROUPS` list (9), "(level - 1) % 9" | insert punks; % 10 |
| 64 | tests/test_venues.py:30-31, :94, :133, :176, :212, :144 | `GROUP_THEME` (9), `range(9)`; `[0, 1, 4, 7]` with id "space" | add `"punks": "biker"`; range(10); space is index 8 now |
| 65 | tests/test_sound.py:20-21, :428, :437, :656, :693 | `TUNE_COUNT = TUNE_VENUE0 + 9`, `range(9)`, the venue frames slice | 10; the "even level" helper still holds |
| 66 | tests/test_stage_anim.py:75 | the set of 9 animated themes | add biker (if its stage animates) |
| 67 | tests/test_edge.py:273 | `range(1, 10)` (one loop of levels) | `range(1, 11)` |
| 68 | tests/test_debug.py:76-78, :106 | wraps at 18; `(lvl - 1) % 9` | 20; % 10 |
| 69 | tests/test_flow.py:17-23, :475-476, :486, :495 | the level TABLE (9 rows), `% 9`, `// 9`, "LOOP 2 banner before level 10" | the new row; 10; level 11 |
| 70 | tests/test_scores.py:1-2, :205-215, :248-262 | "after level 9", `to_level(gb, 10)`, HUD "L10", loop levels (1, 9, 10, 18, 19, 27, 28, 36, 37, 45, 46, 54), `% 9`, `// 9` | level 11, "L11"; (1, 10, 11, 20, 21, 30, 31, 40, 41, 50, 51, 60); 10 |
| 71 | tests/test_enhanced.py:237-244 | "level 18 (zoo) -> bonus -> level 19 (cowboys, loop 3)" | level 20 -> 21 |
| 72 | tests/perf_helpers.py:166-196, :321, :443; tests/test_perf.py:60 | level 9 is the fastest row (zoo), reached from level 8 through its bonus round | level 10, reached from level 9 (odd: no bonus round between); `target=9` -> 10 |
| 73 | tests/test_pour.py:213 | chapters `[0, 5]` | unchanged (saloon, factory) |
| 74 | new: tests/test_twists.py; tests/test_boss.py `test_duke_*`; the Milk Run tests | | as listed in docs/minigames_bosses.md 9.6, 3.12 and 4.10 |

## 7. Goldens (CLAUDE.md rule 3: name every replaced golden and why in its commit)

| golden | expectation |
|---|---|
| venue_biker, patrons_punks, stage_anim_biker (if animated), a GRANNY tour golden (optional) | new: add freely |
| loop_banner | **replaced on purpose**: LOOP 2 now comes at level 11, so the HUD's level reads L11 |
| story_last_call | **replaced on purpose**: the test reaches chapter 10's Last call; the banner reads the new two-digit form |
| story_hana_not_one, story_hana_so_few | unchanged once the tests point at chapter index 7 (same POST_TEAHOUSE pages) |
| venue_* / patrons_* / stage_anim_* of teahouse, space, zoo and ninjas, aliens, zoo | unchanged (named by theme / group; only their index moves) |
| story_goal, story_two_lives, story_bonus_life, story_narrator, story_portrait, story_dregs, story_spigoteer, story_aurora, story_spigoteer_cozy, story_zizz, story_dregs_sorry, story_managerbot | unchanged (chapters 1-6, INTRO page 1, and pages whose text does not change) |
| title, title_anim, title_continue | unchanged |

## 8. Docs outside this change

| # | where | change |
|---|---|---|
| 75 | docs/story.md | fold the PROPOSAL in with the gen_story change: drop `PROPOSAL` from the two scene headings, put the `text` blocks' pages into their scenes (INTRO 6-8, POST_SALOON 5, PRE_TEAHOUSE's new page 4, POST_TEAHOUSE's last page, POST_ZOO 3, FINALE 1 and 7), replace the chapters and shifts tables by the 10-row versions (with `(\d+)` in gen_story, item 34) and drop the top note |
| 76 | docs/minigames_bosses.md section 6 | "Art volume: 9 bosses ... 9 mini-game sets" and the ~60 KB total: 10 (left for the agent editing section 6) |
| 77 | CREDITS.md:29, :38 | "the other nine tunes" -> ten; "level 1, 10, ..." -> "level 1, 11, ..."; a row for the new tune |
| 78 | docs/music_specs.md | the new tune's melody spec |
| 79 | PLAN.md | see the list below (not edited here: another agent is editing PLAN.md) |

PLAN.md lines that state 9 venues / chapters or a chapter number that moves:
- :176 "nine venue tunes"; :262 (M10b) "endless loop of the nine venues"; :265 (M11c) "nine venue owners".
- :756 "After chapter 9's POST: FINALE"; :770 "goal_t.twist (0 for all nine now)"; :772 "chapters cleared 0..9".
- :808 "the nine Last call patterns all different"; :844-845 SRAM v4 "34 chapters cleared (0-9)", "must be 0 when 9
  chapters are cleared"; :848 "CONTINUE ... when chapters 1-8 are cleared".
- :858 and :868 "chapter 9's Last call" / "chapter 9 Happy hour" (the bot runs); :871 "nine patterns"; :873 "golden
  story_last_call, chapter 9".
- "Story lives as built": :949 "chapter 7: a broken glass, F_NO_BREAK"; :958 "BROKEN CUP COSTS TWO (chapter 7)";
  :987 "chapters 2 and 7"; :994 "chapter 9's Last call".
- "Story page text variants as built": :1009 "chapter 7's two lives"; :1014 "chapter 7".
- Not changing: :780 chapter 6 (the factory stays 6); :946 chapters 4, 5; :1075 chapters 1, 6.

## Count

79 items: 23 list entries, 18 story / chapter-number rules, 6 save, 5 arcade, 4 art and banks, 18 test entries, 5
docs; plus the goldens table (2 to replace on purpose, 3-4 new).
