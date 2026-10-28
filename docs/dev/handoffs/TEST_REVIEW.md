# Test suite review (2026-10-28, report only: no test, golden or game file was changed)

## Summary for the owner

- The suite is in better shape than its length suggests. On the current main (after patron revision 2, Stadium/Lodge/Factory v2) a full run is 5,699 cases: 5,591 pass, 91 skip, 17 failed only because my `build/game-c.gb` was stale (rebuilt with `make cfall`, then all 40 asm-twin tests pass). Nothing else is red.
- It is cheap, not slow: about 400 s of work in total (about 1.5 min with 8 shards when warm). Four tests are a third of it: `make dist` (58 s), the credits centring audit (43 s), the Asteroid bot game (20 s), the parrot seed sweep (8 s).
- The length is boilerplate, not weight. 53,348 lines in 126 test files plus 16 helpers. About 40 near-identical functions are copied per mini-game and per boss (release-list unlock, "his row and art", "win the fight by pouring" and so on). Table-driving them saves roughly 600 to 900 lines and almost no time.
- Real staleness is small, because the earlier agents deleted tests with the features (`test_enhanced.py` went with the enhanced looks). I found 3 orphan golden files, 6 pairs of byte-identical goldens, 4 stale comments or docstrings and 2 tests worth rewriting. All are in the STALE and ORPHAN tables.
- The 91 skips are mostly not "dead tests": 26 are RUN_SLOW tests that `verify.sh` runs, 32 are "DMG only / CGB only" guards inside tests that should be separate cases, 26 are two tests that boot a game just to skip (hud timer, idle gap).
- The biggest risk is gaps, not staleness: nothing in `make test` enforces the WRAM / ROM0 budgets; 5 of the 10 asm routines have no direct C-versus-asm test; the perf peaks and the lift/mirror tests only ever put looks 0 to 2 on screen, never the Saloon's five Color-only looks in VRAM bank 1; the Stadium, Lodge and Factory v2 imports have goldens but no palette or tile assertions.

How measured: `tools/dev/ptest.py -j 8` on main after `git merge --ff-only main` (the worktree started 157 commits stale, so my first run was on old code and I redid it). Per-test seconds come from `tests/durations.json` (a quiet serial run, 402 s total) and from this run's junit files. Scripts: `tools/dev/test_inventory.py` (static inventory), `tools/dev/test_runall.py` (one pytest process per file, junit in `out/junit/`), `tools/dev/test_junit_report.py` (slowest, per file, skip groups). All write only under `out/`.

## Inventory

- 126 `test_*.py` files, 16 helper files (`conftest.py`, `perf_helpers.py`, `boss_common.py`, `asm_rig.py` and others), 53,348 lines, 1,750 test functions, 5,699 collected cases, 593 goldens (300 names, 293 on both models, 7 single-model Color/GBA ones).
- Largest: `test_story.py` 1,716 lines, `test_mg_milkrun.py` 1,250, `test_pause.py` 1,152, `test_sound.py` 1,097, `test_mg_tshirt.py` 1,074. Mini-game files total 12,201 lines, boss files 6,610, music/sound files 3,555.
- Ages: the repo is 3 weeks old (first commit 2026-10-09), so no test is old; the oldest untouched are `test_bob.py` (10-09), `test_overlap.py`, `test_stage_anim.py`, `test_art.py` (10-11).
- Symbols: every ROM label the tests pass to `gb.addr/mem/write/read...` exists in `build/game.noi`. The script's "missing" hits were env names (`GB_ROM`, `RUN_SLOW`), dict keys or `_shadow_OAM_base`, all false positives. So no test reads a removed symbol.

## STALE

| Test | file:line | Why | Action |
|---|---|---|---|
| docstring of `restored()` cites `test_enhanced` | `tests/test_mg.py:415` | `test_enhanced.py` was deleted in 1d773d4 (enhanced looks dropped) | rewrite the comment (no behaviour change) |
| `for k in (0, 1, 2, 3, 5, 6, 7)` skips OBJ 4, comment says "no bistro sprite uses 4" | `tests/test_ou.py:601` | written when OBJ 4 was the enhanced palette; OBJ 4 is now the Saloon's 4th patron palette and the Prototype lamp. Comparing all 8 may now be right. UNSURE (the comment also says Colby's jacket uses 4) | rewrite: check 4 too, or say why not |
| `test_realistic_peak_frame_time_target` strict xfail with numbers (DMG end LY ~187, 59 of 1200 missed, per-frame costs "M13c") | `tests/test_perf.py:285` | numbers predate the asm pass, half-rate mode and patron revisions; it still xfails (so the target is still unmet) but the reason text is history | rewrite: re-measure and update the reason, or turn it into a recorded measurement. UNSURE which the owner wants |
| `test_a_lift_on_the_frame_a_drinkers_sway_crosses_a_column_leaves_nothing_for_a_frame` xfail | `tests/test_lift.py:198` | known glitch, QUEUE says "documented as xfail; not fixed" | keep (this is a deliberate open bug marker) |
| comment "batch 2 .. 11 add their @candidate generators here" | `tests/test_asm_equiv.py:58` | only `perf_ly` and `perf_snap` are registered there; the other routines live in `test_catch_asm.py`, `test_mugs_asm.py`, `test_chooser_trace.py` | rewrite the comment |
| `test_the_tag_art_file_has_no_arrow_any_more` and `test_the_drink_arrow_is_gone` (2 x 10 cases) | `tests/test_boss_cap_ui.py:97`, `:105` | guards for a removed feature (owner 2026-10-17). They pass; they cost 20 cases of fights | keep one case per model, remove the other 18; or remove after a release. UNSURE (cheap, owner may like the guard) |
| tests pinned to the saloon cowboy's old back view and the patron art | `tests/test_cowboy_back.py:16`, `tests/test_art.py:49` (`test_patrons_golden_per_group`), `BACK_BASE` use in `tests/test_patrons.py` | not wrong now, but the Saloon backs (5 more looks), the Factory back (Toob v4, Q78) and Stadium/Lodge backs are still being redrawn; these will churn | mark FRAGILE; no action until the art is locked |
| music tests pin digests to `tools/proarr.py` and branch `promusic` (both gone) | `tests/test_music_batch1.py:1-3, 26`, `tests/test_music_batch234.py:1-4, 67`, `tests/test_show_tune.py` (`tools/promusic.py`) | the digests still match the generator, but the reference tool they were taken from no longer exists, so they can only be updated by re-pinning | keep; reword the comments to say "pinned digest" |
| `"src/xx.c"` in a docstring | `tests/test_mg_tuning.py:2` | typo for `src/mg.c` | fix comment |
| credits tests describe the current cast cards | `tests/test_credits.py` (987 lines, 70 s of 400) | the credits are deferred and will be remade after the patrons are locked (QUEUE 2026-10-22) | mark FRAGILE; the audit is the thing to shrink now (see SLOW) |

Overruled decisions I looked for and did not find in the tests: enhanced two-palette looks (removed), drink arrow (guarded as absent, above), left-hand drinks (art only), 120 Hz music (shelved, no test), counter lip (no test), robots_x (gone with the enhanced tests). Index-0 gaps: the only check that forbids them was in the deleted `test_enhanced.py`; no remaining test asserts "no gaps". UNSURE whether the patron art builder in `tools/gen_art.py` (`index0_holes`, line 962, still used by `check_rows`) should now allow drawn gaps; no test depends on it.

## OVERLAP

| Group | Files | Proposed merge / sample | Time saved |
|---|---|---|---|
| "release list unlocks it when reached" and "BONUS > MINI GAMES lists and plays it" copied per game (8 files x 2 tests x 2 models) | `test_bs.py`, `test_mg_logroll.py`, `test_mg_marshmallow.py`, `test_mg_tshirt.py`, `test_mg_taiko.py`, `test_mg_milkrun.py`, `test_mg_asteroid.py`, `test_mg_monkey.py` (see `test_mg_monkey.py:834` and `:856`) | one table-driven test in `test_mg_list.py` over (game id, name, list position, medal) | about 2 s; about 250 lines; 14 fewer functions |
| per-boss copies: `test_the_fight_follows_the_last_call` (10 files), `test_win_the_fight_by_pouring` (9), `test_his_row_and_art` (9) | `test_boss*.py` | a table in `boss_common.py`, one function each | about 3 s; about 400 lines; about 25 fewer functions |
| `make release` run by 12 files through a module-scope `release_built` fixture | `test_bs`, `test_debug`, `test_rush`, `test_mg_list`, `test_mg_bonus` and the 8 mini-game files | one session-scoped fixture with a file lock in `conftest.py` (ptest already runs these in phase 2; a plain `pytest` with several processes races: 4 failures in my first parallel run) | removes a race; little time |
| goldens with byte-identical pictures under two names (6 pairs, 12 files) | `title`/`title_version` (`test_flow.py:222`, `test_release.py:21`); `story_narrator`/`story_pic_intro_before` (`test_story.py:675`, `test_story_pictures.py:215`); `scene`/`stage` (`test_bartender.py:18`, `:200`); `card_stub_page1`/`pause_card_stub_p1` (`test_mg_card.py:275`, `test_pause.py:914`); `card_short_qd`/`qd_intro` (`test_mg_card.py:149`, `test_qd.py:282`); `arcade_start`/`story_goal` (`test_arcade.py:85`, `test_story.py:1016`) | keep one name per pair (the supervisor deletes the other; I changed nothing) | 12 PNG files, 6 comparisons |
| "at most 10 sprites a line" checked in 35 files (19 dedicated tests plus inline loops) | `test_mg_*`, `test_qd`, `test_bs`, `test_tips`, `test_edge`, `test_keg_bartender`, `test_classic_mode`, and others | one always-on check in the frame loop helper (`conftest.py` / `boss_common.frames`) instead of per-file tests. UNSURE: needs care so it does not change frame timing | small; about 19 functions |
| perf guards: `test_perf.py` (68 cases), `test_perf_arcade.py`, `test_half_rate.py`, `test_overlap.py`, `test_edge.py` share `perf_helpers.py` and several scenarios | those | no merge proposed; `test_classic_peak_real_rows_at_other_frame_alignments` (42 cases, 6 s) could be sampled to 14 | about 4 s |
| huge parametrisations | `test_idle_gap` (60), `test_mg_tuning` (60), `test_perf` (42) | all cheap (0.05 s a case on average); sampling gains nothing | none |

## SLOW (seconds from `tests/durations.json`, a quiet serial run; this run's numbers agree)

| # | Test | Seconds | Note |
|---|---|---|---|
| 1 | `test_release.py::test_make_dist` (`tests/test_release.py:40`) | 57.6 | real `make dist` rebuild, pinned to shard 0 |
| 2-3 | `test_credits.py::test_centring_audit_of_every_card[dmg/cgb]` (`tests/test_credits.py:809`) | 21.7 + 21.6 | writes `out/credits_offsets.*.json`, asserts centring |
| 4-5 | `test_mg_asteroid.py::test_a_bot_flies_a_whole_game...[dmg/cgb]` (`tests/test_mg_asteroid.py:702`) | 9.8 + 9.8 | |
| 6-7 | `test_mg_monkey.py::test_every_run_has_parrots_over_many_seeds` (`tests/test_mg_monkey.py:637`) | 4.3 + 4.2 | |
| 8 | `test_pouroff.py::test_a_steady_player_wins_by_three_to_six_on_average` (`:722`) | 3.6 | statistical |
| 9-10 | `test_credits.py::test_the_roll_shows_every_line_centred...[cgb/dmg]` | 2.8 + 2.8 | |
| 11 | `test_pouroff.py::test_a_lazy_player_loses_more_than_he_wins` (`:746`) | 2.5 | statistical |
| 12-15 | `test_asm_equiv.py::test_c_vs_asm[dmg/cgb-perf_ly/perf_snap]` | 1.7 each | needs `build/game-c.gb` |
| 16 | `test_credits.py::test_no_frame_during_a_card_change...[cgb]` | 1.7 | |
| 17 | `test_music_cpu.py::test_no_call_of_any_tune_is_over_18_lines[title-3]` | 1.6 | |
| 18-19 | `test_catch_asm.py::test_random_images[cgb-find_catcher/scan_catcher]` | 1.5 each | |
| 20 | `test_mugs_asm.py::test_random_images[cgb-update_mugs]` | 1.5 | |
| 21-22 | `test_perf_arcade.py::test_the_arcade_peak...[10-cgb]`, `[8-cgb]` | 1.4 each | |
| 23-30 | `test_catch_asm` / `test_mugs_asm` `random_images` (the other model/routine pairs) | 1.4 each | |

Fresh-worktree extras not in that file: `test_practice_art.py` builds its own ROM into `out/b_pa` (61 s the first time, incremental after), and `make release` is built once for 12 files (about 60 s the first time). In a new worktree the first `make test` is about 3 min wall; in the main checkout about 1.5 min.

Time per file (top 12, seconds): `test_credits` 61.9, `test_release` 57.6, `test_mg_asteroid` 23.0, `test_mg_monkey` 13.7, `test_pouroff` 10.8, `test_pause` 10.3, `test_asm_equiv` 9.8, `test_catch_asm` 9.7, `test_mg_tuning` 8.7, `test_mg_milkrun` 8.7, `test_mg_tshirt` 8.4, `test_perf` 8.2. The other 112 files total about 200 s. The full list is in `tests/durations.json` (`files`).

Proposed: move `make dist` to `verify.sh` / RUN_SLOW and keep a cheap structural check (-55 s); run the credits audit on one model in `make test` and both in RUN_SLOW, or step through every third card (-22 to -30 s); Asteroid bot one model in `make test` (-10 s); halve the parrot seeds (-4 s). Total about 100 to 110 s of the 402.

## SKIPPED (91 in the main run: 88 skip + 3 xfail; 112 on a tree with no `build/game-c.gb`)

| Group | Count | Where | Action |
|---|---|---|---|
| RUN_SLOW (the fade tests, double speed, full variant rebuild, perf_ly sweep) | 26 | `test_fade_hw` 22, `test_asm_equiv:113` 2, `test_double_speed` 1, `test_build:37` 1 | keep; `verify.sh` lines 42 and 48 run them. They never run in `make test` |
| "DMG only" / "CGB only" guard inside the test body | 32 | `test_classic:359-496` 16, `test_venues:201` 10, `test_saloon_looks:22-64` 4, `test_dx_badge:310-442` 1 (plus 5 more counted by model), `test_practice_art:220` 1 | rewrite so each test is parametrised only over the models it applies to (no skipped cases) |
| data-dependent skip that is always true for the same parameters | 26 | `test_hud_timer:30` 14 (games 0, 3, 7, 11, 12, 13, 14 show no timer; each boots a game 400 frames to find out), `test_idle_gap:65` 12 (non-serve shifts) | remove: compute the list at collection time |
| Practice/oneline and boss tag | 4 | `test_oneline:180` 2, `test_boss_tag:49` 2 | rewrite the same way (UNSURE which boss has no second beat) |
| xfail (known) | 3 | `test_perf:285` 2, `test_lift:198` 1 | keep, see STALE |
| asm twin tests when `build/game-c.gb` is missing | 21 (only in a tree without `make cfall`) | `test_asm_equiv`, `test_catch_asm`, `test_mugs_asm` | see GAPS: the missing-or-stale C ROM trap |

## ORPHAN GOLDENS

Found by name: every golden name was searched in the test sources, and names built by an f-string were matched by prefix (65 names, all matched a live prefix).

| Golden | Files | Why | Action |
|---|---|---|---|
| `dx_rainbow_phase` | `tests/golden/dx_rainbow_phase.cgb.png` | no test names it; `test_dx_badge.py:446` uses `dx_final_phase` since 7bc9416 (DX badge v4) | supervisor deletes |
| `mg_list_scrolled` | `tests/golden/mg_list_scrolled.dmg.png`, `.cgb.png` | no test names it; `test_mg_list.py:290` only uses `mg_list_locked`; replaced in f38e855 (plain wood wall) | supervisor deletes |
| 6 duplicate-content pairs | 12 PNG | see OVERLAP | keep one name per pair |

I did not delete or change any golden. A run with a missing golden writes it (`conftest.py` `_finish`); my runs created none (`git status` clean for `tests/golden`).

## GAPS

| Feature | What to test | Priority |
|---|---|---|
| WRAM and ROM0 budgets (CLAUDE.md: no new WRAM globals; ROM0 about 745 B free, now 453 B in the main build and 70 B in the C build) | a test that reads `build/game.map`/`.noi` and fails when WRAM_LO, WRAM_HI_0 or ROM0 free cross recorded limits. Today only `test_scratch_map.py` checks the story_scratch layout; budgets are checked by hand | high |
| C twins: only 5 of the 10 `ASM_*` switches have a direct C-versus-asm test (`perf_ly/snap`, `draw_held`, `update_mugs`, `find_catcher`/`scan_catcher`/`catch_full`, the chooser trace). No differential test for `ASM_LIFT_DRAW` (`draw_lifted_asm`; its C twin is new in 1d773d4), `ASM_PATRON_LOOP`, `ASM_PATRON_STEPS`, `ASM_BOSS_HATS`, `ASM_LIFT_FRAME`. They are covered only by the whole suite on the C ROM in `verify.sh` | a random-image test like `test_mugs_asm.py` for each | high |
| stale C ROM trap: `test_asm_equiv/catch_asm/mugs_asm` use whatever `build/game-c.gb` exists, of any age. After my fast-forward 17 of them failed (layout changed) until `make cfall` | skip with a clear message, or fail loudly, when `game-c.gb` is older than `game.gb`; or have `make test` depend on `cfall` | high |
| Saloon Color-only looks 3-7 (VRAM bank 1; `PATRON_BANK1`, `spawn_variant`, 29 combinations, `test_saloon_looks.py` has 4 tests, 3 skipped on DMG) | a patron of look 3-7 is lifted (`draw_lifted`, `and #7`), mirrored on an L bar (`quick_mirror`), walks the sway, is overlapped in a crowd, and appears in the show with OBJ 5; DMG output byte-identical to before. `perf_helpers.py:133,252,363,500` use `p % 3` so the perf peaks and chooser trace never see a bank-1 look. UNSURE: the whole-level goldens on CGB see random looks, so some are exercised by chance | high |
| Stadium A/B/C, Lumber Lodge WILLOW/ASH, Factory v2 (BOXY yellow on Color, VOLTA, BLIP): imported, covered by goldens (`patrons_*`, `venue_*`, 40 goldens replaced in 218d240) | per look: BG/OBJ palette slot, tile count within the group budget, DMG unchanged, back view present; same style as `test_saloon_looks.py` | medium |
| patron tile sharing (batch 3, Q61/Q76: full lookup table; WRAM audit found 395 B of scene buffers unused in bars and fights) | when it is built: a test that every venue's patron tiles resolve to the same pixels through the table, and a WRAM budget test (above) | planned |
| Color-only extras not yet built (Factory 4th look NEKA, Space Lounge astronaut, mint robot) | with the import: the `test_saloon_looks.py` pattern (Color only, bank, DMG keeps its looks) | planned |
| GUS tips | `test_tip2.py` covers it (always tips, no random number, one at a time in classic). Fine | none |
| pause, story map, three modes, save v7 | covered: `test_pause` 196 cases, `test_story_map` 125, `test_arcade`/`test_classic*`/`test_scores`, `test_save_upgrade` 79 | none |
| `tools/gen_art.py` patron builder rules (holes/gaps, order, lifted columns) | the only builder tests were in the deleted `test_enhanced.py`; if drawn gaps are now allowed, a test that a drawn gap is kept transparent in the lift (QUEUE Q73) | medium, UNSURE |
| DMG half-rate, double speed, bright (GBA), DX badge | covered (`test_half_rate`, `test_double_speed`, `test_bright`, `test_dx_badge`); real hardware timing only by `make check` and the RUN_SLOW tests | none |

## If every proposal is taken

- Test files: 126 to about 124 (no file removed outright; two small ones could fold into `test_mg_list`/`boss_common`). Functions about 1,750 to 1,700; cases about 5,699 to 5,600 (no skipped model guards, no always-skipped parameters, 18 drink-arrow cases, 1 dist case). New tests for GAPS add about 40 cases.
- Lines about 53,300 to about 52,000 (boilerplate merge, plus the new gap tests).
- Goldens 593 to 578 (3 orphan files, 12 duplicate files; plus 0 new).
- CPU time 402 s to about 295 s; wall with 8 shards warm about 1:30 to about 1:00, cold (new worktree, two builds) about 3:00 to about 2:00. These are estimates from the per-test table; I did not re-run with the changes.

Doubts: (1) my first run (per-file processes, 10 at once) raced on `make release` and showed 4 failures that passed alone; the numbers above are from the later `ptest.py` run. (2) the 17 failures in that run were the stale C ROM, confirmed green after `make cfall` (40 passed, 2 skipped). (3) "stale" is judged by docstrings, symbols, git history and the rulings I could read; a test can still assert something the owner has since changed without my seeing it; the UNSURE marks are those cases.
