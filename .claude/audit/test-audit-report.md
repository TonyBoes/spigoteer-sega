# Spigoteer test suite audit (2026-11-09, read-only)

Sources: one timed full run (`.claude/audit/test-run.log`, a copy of `out/verify/audit-main.log`; per-shard logs in `out/ptest/20261109-073002-*` (asm) and `out/ptest/20261109-074123-*` (C)), test collection, git history, a scan of 148 subagent and 2 supervisor transcripts, and a grep of every instruction file. "Unknown" means not measured.

## 1. Inventory

**Tools**
| Kind | What |
|---|---|
| Runner | pytest 9.1.1 + pytest-timeout. No xdist, cov, mutmut or hypothesis installed (PyPI blocked). No pytest.ini; markers `slow`, `only_model` in tests/conftest.py:831-836 |
| Emulators | PyBoy 2.7.0 drives and asserts; SameBoy (via `gbcheck`) is the timing check (`make check`) and is also used by a few tests |
| Goldens | 630 PNGs (322 names × .dmg/.cgb), 2.5 MB in tests/golden/. Read-only diff tool tools/dev/golden_bbox.py; `gb-golden-check` agent gives a verdict table; only the supervisor replaces goldens |
| Build/budget guards | test_budget.py (link map), test_perf*.py (3 files, 73 tests), test_release.py; romusage |
| Map/page checks | tools/dev/smap_frames_check.py, smap_pixel_check.py, page self-checks in tools/artifacts/*/ |
| Inventory/timing tools (exist, rarely used) | tools/dev/test_inventory.py, test_runall.py, test_junit_report.py |

**Commands**
| Command | Defined | Runs |
|---|---|---|
| `make test` | Makefile:335-339 | `tools/dev/ptest.py -j 8 tests` (shards by tests/durations.json, 180 s per-test timeout); `JOBS=1` = `pytest -q tests`. No narrowing option |
| `make check` | Makefile:342 | `gbcheck build/game.gb --length 10`, DMG + CGB |
| `make cfall` | Makefile:307 | builds build/game-c.gb (C twin of every asm routine) |
| `pytest tests/test_x.py[::name] [-k expr]` | (pytest) | single file / test / keyword: the targeted form agents use |
| `tools/dev/verify.sh <wt> <name>` | 79 lines | make -B → cfall → pytest (asm) → make check → RUN_SLOW fade → pytest on C build → RUN_SLOW double speed/half rate; RESULT/END lines. `QUICK=1` skips slow fade + C build |
| Env switches | tests/, tools/dev | RUN_SLOW, GB_ROM, GB_UPDATE_GOLDEN, GB_GOLDEN_REPORT, GB_DOUBLE_SPEED, PERF_*, QUICK, JOBS (19 in all) |

**Counts:** 163 test files (+ helpers); **6629 tests collected** (6694 minus 65 model-deselected); only 1969 `def test_` — 6345 ids are parametrised, ~5727 run once per model (DMG and CGB).

Largest areas (tests): story_map* 345, pause* 214, boss_in* 200, story 195, mg_tuning 191, extra_looks* 187, show* 181, classic* 163, debug* 145, venues 134. Full table: inventory agent's notes (127 prefix groups).

## 2. Timing (one run, main a5cd3368, 24 cores, load 0.7 at start; other agents active but not saturating)

| Stage | Wall | Result |
|---|---|---|
| make -B | 81 s | OK |
| make cfall | 76 s | OK |
| pytest, asm build | 233 s | 6579 passed, 50 skipped, 0 failed |
| make check | < 1 s stamp resolution (unknown) | DMG OK, CGB OK |
| RUN_SLOW fade | 448 s | 21 passed, 1 failed (the known f1-cgb) |
| pytest, C build | 363 s | 183 failed, 4748 passed, 1668 not reported (C tests on hold since 11-01) |
| RUN_SLOW double speed / half rate | 79 s | 63 passed |
| **Total** | **21 min 24 s** | RESULT: FAIL (all failures pre-existing) |

QUICK=1 (map/art branches) would be about 81+76+233+79 s ≈ 8 min.

**Slowest tests (asm stage, per-shard top lists)**
| s | Test |
|---|---|
| 83.2 | test_show_ext::test_the_color_show_is_in_bank_1… (setup) |
| 82.8 | test_practice_art::test_the_first_picture_is_there_on_entering[dmg] (setup) |
| 81.6 | test_release::test_make_dist |
| 10.8 | test_mg_asteroid bot game [cgb] / [dmg] (10.6) |
| 10.8 | test_asm_equiv::test_c_vs_asm[dmg-perf_ly] |
| 9.9 | test_double_speed pump-after-gap |
| 7.6 | test_rng stadium picks uniform [cgb] |
| 6.7 | test_pouroff steady player wins |
| 5.7 / 4.4 | test_mg_monkey parrots over many seeds [cgb]/[dmg] |
| 5.1 / 4.9 | test_story_map_world walk cost bounds [dmg]/[cgb] |

The three ~80 s items are one-off builds (variant ROMs, the dist zip), not per-test costs; they sit in separate shards and set the shard's floor. Repeated per-test setup is small (test_debug: 89 setups, 0.9 s). Every test boots its own PyBoy (cost per boot not measured separately).

## 3. When and how tests run

| Who | What triggers it |
|---|---|
| gb-worker / gb-artist agents | their own judgement during a task; agent def says narrow first, then full `make test` + `make check` (gb-worker.md:20) |
| Supervisor | after merges into main; before Q12 also after every fast-forward |
| gb-runner | verify.sh on request of the supervisor, once per branch |
| gb-golden-check | reruns only the failing golden tests |
| Hooks | none trigger tests; one hook filters output (section 4) |

Measured from transcripts (Bash calls):
| Window | FULL runs sup / sub | Targeted sup / sub | per sub transcript FULL / targeted | sub transcripts with >1 FULL (max) |
|---|---|---|---|---|
| 7 days | 98 / 186 | 28 / 824 | 1.19 / 5.28 | 36 of 54 (max 20) |
| since Q12 rule (2 days) | 16 / 34 | 10 / 114 | 0.92 / 3.08 | 7 of 13 (max 6) |

There is a documented targeted form (SUPERVISOR.md:71-73, memory one-full-test-run) and agents do use it (pytest with a file or `-k`: 824 calls in 7 days). But full runs persist after the rule: 34 full runs by agents and 16 by the supervisor in two days.

## 4. What comes back into context

- **Hook** (.claude/settings.json → .claude/hooks/filter_test_output.py): rewrites single-line `make …` / `pytest …` commands to log to `/tmp/claude-testlog.*`, then prints the whole log if ≤ 30 lines, else matching lines (FAILED/ERROR/Traceback/passed/golden/WRAM/ROM0/[dmg]/[cgb]…, max 120) plus the last 15 and the log path. Same for pass and fail. It does **not** match piped, chained (`&&`, `|`, `;`), multi-line commands, `ptest.py` or `verify.sh`; those return whatever the agent pipes (often `| tail -N`). Logs are never deleted.
- **Sizes returned** (chars; tokens ≈ chars/4), 7 days: FULL pass median 396 (max 12,228); FULL fail median 1,146 (max 10,070); targeted pass 260 (max 11,540); targeted fail 943 (max 6,580); make check 143. The output size per call is small.
- **Verbosity:** `-q` in 876 of 1136 calls, `-x` 224, `-k` 339, `--tb=short` 3, `--durations` 8. verify.sh uses `-q -p no:cacheprovider`. Quieter options exist (`--tb=line`, `-rN`, `--no-header`) but are unused.
- **gb-runner returns**: a summary the brief asks for; in the transcripts its last message is ~116 chars median (175 max) — but today's audit runner returned ~3,500 chars because the brief asked for tables. The verify log itself is 202 lines/18 KB; with the C stage on, 185 lines are flagged failures that are already known.

## 5. Growth history

| Week of | Test files | `def test_` | Goldens |
|---|---|---|---|
| 10-08 | 0 | 0 | 0 |
| 10-12 | 33 | 586 | 216 |
| 10-19 | 110 | 1563 | 564 |
| 10-26 | 124 | 1742 | 593 |
| 11-02 | 147 | 1837 | 578 |
| 11-09 | 163 | 1969 | 630 |

747 commits touch tests/: Opus-coauthored 586, Sonnet 104, none 57 (mostly by the main Opus sessions and gb-workers). Most-changed: test_story 56, test_sound 51, test_flow 47, test_story_pictures 39, test_debug 34.

Rules on adding tests: "Add new goldens freely" (CLAUDE.md:20); the mini-game skill lists required tests (spigoteer-minigames/SKILL.md:39-42); junk-poke tests for hand-placed RAM (pyboy-zeroed-ram.md:14); rewrite tests that encode old rules rather than loosen them (agent_rules/batchB_common.txt:3). **No rule says when NOT to add a test**, and none limits doubling across DMG/CGB.

## 6. Possible redundancy (flags only)

- **Model doubling:** ~5727 of 6629 tests run on both DMG and CGB, including files that are 100% doubled (boss_in*, pause*, tips, flow, menu, mg_tuning 190/191). Where the code path doesn't depend on the model, half are duplicates; not checked per test.
- **Overlapping names:** test_bonus.py (17), test_bonus2.py (24), test_mg_bonus.py (9) — suspect overlap, not verified.
- **Golden families** repeating one code path per venue: credits_cast_patrons_* (11), wash_*_0..3, dregs_gag_*, venue_*.
- **77 of 322 golden names** never appear literally in tests/*.py (may be built by f-strings; tools/dev/test_inventory.py could settle it, not run).
- **C-build stage:** 4,931 test results per full verify, 183 known failures, on hold since 11-01; nobody acts on them.
- **Stale tests:** 25 skip/xfail sites, all environment or opt-in gates except 2 xfails (test_perf:285 owner target, test_lift:198 known rare bug) and 1 content skip (test_harmony:120). Tests reading missing symbols: unknown (not run).
- **Coverage:** no ROM coverage tool; pytest-cov would only cover the Python harness and isn't installed. PyBoy `hook_register` (already used, conftest.py:179, 484) could count executed ROM addresses per test — would have to be built. No mutation testing available.

## 7. Current instructions (verbatim, by file)

**CLAUDE.md**
- :11-13 "1. **Done means `make test` and `make check` pass**, on both DMG and CGB. A ROM that builds is not a ROM that works. Run them; do not reason about whether they would pass."
- :20-23 "3. **Replacing a golden screenshot is a visible decision.** Add new goldens freely. When a test fails because the picture changed on purpose, say so in the commit message with the golden's name and why. Never regenerate all goldens to make a red run green."
- :36-38 "- **Goldens:** add new ones freely. Only the supervisor replaces an existing golden. Agents list each changed golden with its diff bounding box (from a read-only script that writes nothing under `tests/golden/`) and the reason, and commit with those failures left in, saying so."
- :40-41 "Report `WRAM_LO` / `WRAM_HI_0` and `romusage` before and after. ROM0 has about 745 B free: keep it. Never raise a perf guard; if one fails, stop and report."
- :42-43 "Every asm routine keeps its C version built (`make cfall`) and tested. Never delete the C path."
- :46-47 "…kill any pytest or profiler you start."
- :51-52 "- **Done** means committed and green on DMG and CGB."
- :59 "make test       # pytest on DMG and CGB, 8 shards via tools/dev/ptest.py (~1.5 min); JOBS=1 for the old serial run"
- :64 "Full branch verification (about 20 min; the supervisor or a `gb-runner` agent): `tools/dev/verify.sh <worktree> <name>`."
- :66-68 "Test and build commands (`make`, `make test`, `make check`, `pytest`) pass through a hook: if the output is long you see the failures, errors and the last lines, plus the path of the full log. Open the full log only when that is not enough."
- :72-73 "PyBoy is for driving and asserting; SameBoy is the timing truth. PyBoy zeroes RAM that real hardware leaves as junk: clear hand-placed bytes in `main()` and test with a junk poke."

**.claude/agents/gb-worker.md**
- :20 "- Test the narrowest thing first (one test file, one `gbtest run`), then the full `make test` and `make check`."
- :21 "- Test output is filtered to failures and a summary, with the full log's path. Open that log only if you need it."
- :24 "- Stop when the work is committed and green, or when you hit a denial, a perf guard or a budget limit."

**.claude/agents/gb-runner.md**
- :19-20 "- **Verify:** run `tools/dev/verify.sh <worktree> <name>` in the background, wait for the `END` line in `/workspace/out/verify/<name>.log`, then report the RESULT line and every flagged line, verbatim."

**.claude/agents/gb-golden-check.md**
- :16-17 "1. Rerun only the failing tests in the worktree to collect `out/diff/*.actual.png`…"

**Skills**
- gb-toolchain/SKILL.md:43 "make && make test && make check"; :158-159 "`make test` runs every test on both DMG and CGB. A test that only makes sense on one model can check `gb.model_name`."
- spigoteer-minigames/SKILL.md:39-42 "Start, controls, scoring, win and lose, medals, Practice, HARD if the spec has it, and sprites per line. Add goldens for the key screens on DMG and CGB after looking at them."
- spigoteer-music/SKILL.md:47 "Run `make` after any merge before single tests or recordings, or they use a stale `build/`."

**docs/dev/SUPERVISOR.md**
- :66-70 step 6 (verify; "Map and art branches use `QUICK=1` … engine, fade or timing changes and releases get the full run.")
- :71-73 "**One full run per change (owner Q12, 2026-11-08):** the verify run is the only full test run. Briefs tell agents to run only the tests for the area they touch while working (`pytest -k`, the relevant files), plus `make` and `make check`, and to leave the full `make test` to verify."
- :74-76 "7. **Fast-forward main.** No full test run on main after a fast-forward of the verified tip. If another branch was merged in between …, run `make cfall`, `make`, `make test`, `make check` once on main."

**docs/dev/LESSONS.md**
- :32-33 "- **Done means:** `make -B`, `make cfall` (the C reference build), the full pytest suite on both models, `make check` (SameBoy, DMG + CGB), the slow tests (`RUN_SLOW=1`), and the suite again on the C build (`GB_ROM=build/game-c.gb`)."
- :41-42 "- **Fragile tests:** assert on driver or game state (variables by name) rather than on audio FFTs or exact frame timing, and feed input by game step rather than by frame."

**Memory notes**
- one-full-test-run.md:11 "One full test run per change. Agents run only the tests for the area they touch while working (plus `make` and `make check`); the verify run (QUICK for map/art…) is the single full run; after a fast-forward merge of the verified tip, no rerun on main. Rerun on main once only when other merges landed in between."
- verify-quick-for-map-art.md "brief gb-runner with `QUICK=1 tools/dev/verify.sh <worktree> <name>` for map/art/asset-only branches; the full run when src/ engine, fades, timing or music change, and before any release."
- c-build-speed-not-required.md:14 "in verify.sh's C-build run, speed/timing guard failures … are expected and do not block a merge."; :17 "during the patron import, no C-build test runs and no C-build fixes (make cfall must still link so the C twin exists)."
- owner-testing-judgement-only.md:11 "Mechanics … are ours to verify with tests and emulator runs before handing over."
- orphan-processes.md:18 "Never run make or tests in a worktree while a background verification is running there."
- Old brief templates: docs/dev/agent_rules/rules_code.txt:11 "Done means `make test` and `make check` pass on DMG and CGB."; batchB_common.txt:2 "Regenerate ONLY goldens whose test fails because of your change…" (superseded).

**Hooks:** only the PreToolUse Bash hook above. No settings.local.json; user settings have no hooks.

**Where practice and instructions differ**
1. CLAUDE.md:11, gb-worker.md:20, rules_code.txt:11 still say run the full `make test`; the Q12 rule (SUPERVISOR.md:71-73, memory) says targeted only. Agents follow the agent file: 34 full runs in 2 days after the rule.
2. LESSONS.md:32-33 "Done means" includes the C-build suite and slow tests; memory says C-build tests are on hold, yet verify.sh still runs them (6 min, 183 known fails) on every full verify.
3. CLAUDE.md:59 says `make test` takes ~1.5 min; measured 3.9 min (asm stage).
4. CLAUDE.md:20-23 reads as if the committer replaces goldens; every later rule says supervisor only. batchB_common.txt:2 still says agents regenerate.
5. CLAUDE.md:66-68 says test commands pass through the filter; piped or chained commands, ptest.py and verify.sh don't.
6. The brief asked for raw output in `.claude/audit/test-run.log`, but verify.sh writes its own log; the file was 1 line until I copied the verify log in.

## 8. My view

- **Time:** the 21-min full verify is 3 stages that rarely find anything new: slow fade 7.5 min (1 known failure), C-build pytest 6 min (183 known failures), and the clean rebuild + cfall 2.6 min. The asm suite itself is 3.9 min, with a floor set by three ~80 s one-off builds.
- **Tokens:** not the size of test output (median 0.4-1.1 k chars) but the **number of turns** spent on tests: each test call is a turn that re-reads the agent's whole context. 1,136 test calls in 7 days by agents and supervisor; per-turn context size per agent not measured, so the total is unknown. Second: the supervisor's own 98 full runs in 7 days, each re-reading a very large supervisor context. Third: triaging the same known failures (C build, fade f1-cgb) in every verify report and every agent report.
- **Confusion/repeat work:** the conflicting "done means" lines above; known failures re-explained each time; checks that test the wrong thing (today: the map pause was reported fixed from a picture check and a model, not a motion check of the real ROM); a test broken on main by another merge (Milk Run HUD) that showed up later as someone else's failure.

## Top 3 time costs
1. **C-build pytest stage in full verify: 363 s per run**, 183 failed / 1668 not reported, on hold since 11-01 (log: C stage line in test-run.log).
2. **Slow fade stage: 448 s per full verify**, 21 passed + 1 known failure.
3. **Repeated full suites by agents:** 186 agent full runs in 7 days (36 transcripts ran it more than once, max 20), each ≈ 4 min of asm suite plus build → order of 12+ machine-hours a week; still 34 in the 2 days since the Q12 rule.

## Top 3 token costs
1. **Turns spent on test calls**: 1,136 test-related Bash calls in 7 days (824 targeted + 186 full by agents alone), each re-reading the caller's context. Per-call output is small; the turn is the cost. (Total tokens: unknown, context sizes not measured.)
2. **Supervisor full runs**: 98 in 7 days (16 in the last 2), each a turn on the largest context in the project.
3. **Known-failure triage**: every full verify flags 185 lines that are already known (C build + fade f1-cgb); runner and supervisor read and dismiss them each time, and agents report them again.

## Recommendations (not yet approved)
1. Update CLAUDE.md:11, gb-worker.md:20 and the old rules_code.txt to the Q12 rule (targeted tests while working; verify is the one full run), and fix the `make test` time to ~4 min.
2. Drop the C-build pytest stage from verify.sh while C tests are on hold (keep `make cfall` so the C twin links); run it only before a porting release.
3. Move the slow fade stage to engine/fade changes only (QUICK already skips it; make QUICK the default and full the exception).
4. Add a known-failures list so verify reports only new failures.
5. Add a narrowing option to `make test` (e.g. `make test K=story_map`) and make the hook match piped/chained test commands, so targeted runs are easy and always filtered.
6. Review DMG+CGB doubling for model-independent logic tests (half of ~5,700 runs), starting with the 100%-doubled files.
7. Before relying on a check, state what it measures (picture, model, real-ROM motion), so a fix is checked by the right test.
