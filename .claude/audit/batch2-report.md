# Test batch 2 report: faster verify (2026-11-09)

Branch `worktree-agent-a846146b69801c0bd` (ff-merged to main first). Brief: docs/dev/notes/test_batch2_brief_2026-11-09.md.
Not touched: assertions, goldens, perf guards, game code. Load (`uptime`) is given with each timing; 24 cores, load 1.1 to 2.9 during this work.

## Part A: findings

**A1. Why `make -B` takes 80 s** (timed per recipe line, load 1.8, 79.6 s wall; no `-j` anywhere in the Makefile).
| Step | Time |
|---|---|
| the single `lcc` call (compiles all 68 src + 52 build C files, then links, one process) | 72.8 s |
| gen_smap_world.py | 1.3 s |
| gen_art.py (runs twice under -B: multi-target rule without `&:`) | 1.7 s |
| gen_story.py (5 runs), gen_boss.py (11 runs), gen_mg.py (5 runs) | 1.5 s, 1.0 s, 0.24 s |
| all other 40 generator runs together | about 0.9 s |
Total of the 49 generator runs 6.5 s (18 are duplicate runs of the same recipe under -B, about 2.5 s). Asset conversion is not worth caching: 6.5 s, and plain `make` already skips it. The cost is lcc compiling about 120 files one after the other (about 0.6 s each). An experiment (out/obj/exp.sh, not committed) compiled every file to its own object with `lcc -c`, 12 at a time: 9 s for all 121 objects. The naive relink did not reproduce build/game.gb byte for byte (bank assignment depends on object order and the -autobank step), so this is a proposal, not a change (C3).

**A2. Why `-B`.** It is in the first verify.sh (commit e8c0b87f, dev setup); no message gives a reason. Closest history: a0e50dc0 (Oct 17) fixed the real stale-ROM causes (shared hUGEDriver.o rewritten by every link, flags not a ROM dependency). So `-B` was a safe default. Dependency audit (a Python audit hook logging every file each generator opens during `make -B`, plus import analysis, compared with `make -pn`): the lcc side is complete (every build/ header that src/ includes is a ROM prerequisite), but 7 generators read files their rules did not list: gen_art (assets/tiles/story.txt, src/layout.h, plan_slots.json), gen_boss (venues/*_tilt.txt), gen_credits (venue *_pal.json, patrons *_x.txt, palette_plan/*.py, plan_slots.json), gen_looks (src/game.h, plan_slots.json), gen_smap_world (src/order.h), gen_story (assets/tiles/bar.txt, src/level.c), gen_music (tools/harmony.py). Fixed in B3a. Also: nothing depends on the Makefile itself (flag changes are caught by the .flags stamps; a recipe or list edit is not); and `TIP`/`GLOW`/`CREDITS` env variables change gen_art's output without a stamp (they use their own BUILD dirs, so harmless).

**A3. The three ~80 s tests.** Each is one more full lcc build, because lcc is one process and any change recompiles everything.
- `test_show_ext` cgb_rom: `make BUILD=out/b_showcgb OUT=out/o_showcgb out/b_showcgb/game.gb` with env `SPIGOTEER_TEST_SHOW_CGB` (a generated 24x24 show and json): its own generated files differ (venue_factory), full lcc. Measured 84 s.
- `test_practice_art` art_rom: `make BUILD=out/b_pa PRACTICE_ART_DIRS=tests/data/practice_art out/b_pa/game.gb`; only practice_art_*.c differ from the main build, but lcc recompiles all. 84 s (63 s in the old durations file). Incremental (an existing out/b_pa and no change) is already free.
- `test_release::test_make_dist`: ptest's prebuild already ran `make release` (75 s, serial, before any shard starts); then `make dist` deletes build/release.gb and rebuilds it (80 s) when dist/ is missing, which it is in a fresh worktree.
Caching by source hash would only hit when the same tree was built before (a re-run, or main after a merge of an already verified branch), and the test fixtures cannot be edited (markers only). The real fix is per-object compilation (C3), which makes all of them and the main builds cheap. A reuse of the main build is not possible: their generated sources differ and lcc recompiles everything anyway.
Also in the same stage: `RUN_SLOW` double speed test f builds its own ROM in out/dsmr (`-DAUTO_MR`), another 80 s build: that is the whole 80 s of the "double speed / half rate" stage. So one default verify does 7 full lcc builds (game, cfall, release prebuild, dist, show_ext, practice_art, dsmr), about 525 CPU seconds, all independent.

**A4. Side by side stages.**
| Stage | Reads | Writes |
|---|---|---|
| `make cfall` | src/, build/*.c/.h (all up to date after the build) | build/game-c.*, build/obj/game-c/, build/game-c.flags, build/game-c_link.log |
| double speed / half rate (RUN_SLOW) | build/game.gb/.noi, build/*.json, tests/golden | out/dsmr/ (own build and SameBoy runs), out/dsoff/ (patched ROM copies, written by rename, same bytes for the same key) |
| asm pytest (ptest) | build/game.gb, build/*.json | build/release.* (prebuild + make dist), out/ptest/, out/b_pa, out/b_showcgb, out/dsoff, out/diff (only on failure) |
No shared file, folder or port (PyBoy is headless; only test_double_speed and test_fade_hw call sameboy_tester, with their own directories). The one precondition is that the generated sources are up to date when the overlap starts: true after the build stage. `make check` writes out/check and takes 1 s; it runs before the three start. Done in B1.

**A5. ptest -j 8.** Measured shards of the batch 1 run (batch1 junit): 178, 146, 62, 135, 63, 69, 41, 64 s. The stage is 256 s = 75 s prebuild (`make release`) + 178 s longest shard. Cause: tests/durations.json is from Nov 1: 554 of 6392 tests are missing from it (planned as at least 1 s each, which also inflates the estimate) and the three 80 s tests are weighted 0.05 s (make_dist), "none" (show_ext) and 63 s, so shard 0 got make_dist plus 97 s of other tests, shard 1 and 3 got 60 s plus a build. Simulation with ptest.plan() and the measured per-test times of that run: -j 8 gives 94 s per shard (all equal), -j 12 gives max 84 s (the build tests alone), -j 16 and -j 20 also 84 s. So the floor is the 80 s builds; refreshing durations.json gets about 80 s of the 85 s available, more shards add about 10 s at most (C1).

## Part B

| Item | Commit | Result |
|---|---|---|
| B1 overlap stages | 67cbba8c | done |
| B2 release-only | aad4dca4 | done |
| B3 incremental | 9b541248 (B3a), 831a8ee0 (B3) | done, with a prerequisite fix |
| B4 cache builds | none | skipped |
| docs | see Instruction lines | done, times filled in (about 5 min) |

**B1.** `tools/dev/verify.sh`: after the build and `make check` (1 s), pytest runs in the foreground while `make cfall` and the RUN_SLOW double speed / half rate stage run in the background; FULL (fade) and CBUILD stages follow. Each stage keeps its own section (written in a fixed order after all finished), now with `RESULT <stage>: PASS|FAIL`; the overall `RESULT:` waits for all and lists the failed stages. `VERIFY_LOGDIR` overrides the log directory (proof). Proof with stub make/python3 (out/stub): all-pass gives RESULT: PASS; one injected failure each in pytest, cfall, check, slow, fade, cbuild gives `RESULT: FAIL (failed stages: <name>)`; build failure gives `RESULT: FAIL (build)`. With stub cfall 3 s and slow 4 s and pytest 1 s the run took 4 s: the verdict waits for the slowest stage.
**B2.** `release_only` marker (tests/conftest.py, in the existing collection hook) on `test_make_dist`; items with it are deselected unless `FULL` is set, so no skips. `--collect-only tests`: 6628/6694 collected without FULL, 6629/6694 with `FULL=1`; the test is listed only with FULL=1.
**B3a (needed by B3).** The 7 generator gaps of A2 added as prerequisite-only rules to the Makefile (no recipe changed). Proof: touching each of 11 listed files now re-runs its generator (`make -n` table, out/b3/gaps.sh: 11 of 11 OK). Without them B3 would have kept stale generated files.
**B3.** Default verify uses plain `make`; `FULL=1` uses `make -B`. Proof (out/b3, incremental `make` + `make cfall` in build/ versus a from-scratch build of the same tree in out/b_clean, sha1 of game.gb / game-c.gb):
| Scenario | Incremental = clean? | Note |
|---|---|---|
| base tree | MATCH cabc63dc320c / 844d47af0b7d | also shows the ROM does not depend on the BUILD dir |
| source: src/tip.c (new function) | MATCH 3247545c8dde / 0260073b2248 | |
| header: src/layout.h (BT_DY 2 to 3) | MATCH 8673a3a0733e / 1cc056d4ed74 | gen_art re-ran (the B3a gap) |
| asset: assets/art/coin.txt (one pixel) | MATCH 198351fe78de / 84fc8c77e29b | |
| Makefile: VERSION 0.9 to 0.8 | MATCH 8c6b07a99b02 / 074933196617 | flags stamp |
| tool: tools/harmony.py (comment) | MATCH (= base) | gen_music re-ran (the B3a gap) |
| all reverted | MATCH, back to the base sha | git status clean (only my commits) |
Two first attempts at header/asset edits (MUG_DY 4 to 3, a bar.txt pixel) made the generators reject the input; both builds failed the same way (incremental and clean), so I chose valid edits. Timings: incremental make + cfall about 150 s (two lcc runs), clean 80 s each in parallel; load 2.0 to 2.9.
Important limit: B3 saves the 80 s build only in a worktree whose build/ is current (an agent that ran `make` on its final commit). A fresh worktree, or one with edited sources, still pays the full lcc run, because lcc recompiles everything on any change.
**B4 skipped.** The three builds need test fixture changes to use a cache (only markers are allowed), a Makefile-level content-hash cache would only hit on re-runs of an identical tree, and the incremental make rule already gives that reuse in the same worktree. The saving is real only with per-object compilation (C3). Not done.

## Timing

Measured by gb-runner on the same commit e0013fb3, one run after another (logs /workspace/out/verify/b2-*.log):

| Stage | Before (batch 1 script), load 1.9 -> 5.4 | After, source touched (realistic branch), load 3.0 -> 5.4 | After, nothing changed, load ~4.7 |
|---|---|---|---|
| build | make -B 80 s | make 73 s (full lcc rebuild) | make ~0 s |
| make check | ~1 s | ~1 s | ~1 s |
| pytest asm | 216 s | 214 s | 93 s |
| cfall | 75 s (serial) | 80 s (beside pytest) | ~0 s (beside pytest) |
| double speed / half rate | 80 s (serial) | 89 s (beside pytest) | 4.5 s (its own build reused) |
| **total** | **7 min 32 s** | **4 min 48 s** | **1 min 34 s** |

All three: RESULT PASS, 6574 passed / 56 skipped, slow 63 passed, no FAILED or timeout lines. The realistic figure for a branch with code changes is about 5 min (target 3-4 min not reached by B1-B3 alone; C1 + C2 below are the next step). A rerun of an unchanged tree (e.g. main after a docs-only merge) is about 1.5 min. The 4.5 s slow stage is sound: test_double_speed builds with plain `make` into out/dsmr, so it reuses that build only when nothing changed.

## Instruction lines changed (before, after)
1. CLAUDE.md:66-67. Before: "(default stages about 8 min; `FULL=1` adds the slow fade stage, `CBUILD=1` adds the C-build pytest)". After: "(default stages about 5 min: plain `make`, then pytest, `make cfall` and the double speed / half rate tests side by side, `make check`; `FULL=1` uses `make -B`, adds the slow fade stage and the release-only tests, `CBUILD=1` adds the C-build pytest)".
2. docs/dev/SUPERVISOR.md:66-70. Before: "(about 8 min). The default stages are `make -B`, `make cfall`, the full pytest, `make check`, and the `RUN_SLOW` double-speed and half-rate tests, ending with a RESULT line. `FULL=1` adds the `RUN_SLOW=1` fade tests". After: "(about 5 min). The default stages are plain `make` (incremental), then the full pytest, `make cfall` and the `RUN_SLOW` double-speed and half-rate tests side by side, and `make check`, each with a `RESULT <stage>` line, ending with the overall RESULT line. `FULL=1` uses `make -B`, adds the release-only tests (`test_make_dist`) and the `RUN_SLOW=1` fade tests".
3. .claude/agents/gb-runner.md:19. Before: "(default stages, about 8 min; prefix `FULL=1` when the brief says engine/fade/timing/music or release,". After: "(default stages, about 5 min; prefix `FULL=1` when the brief says engine/fade/timing/music or release (it also runs `make -B` and the release-only tests),".
4. docs/dev/LESSONS.md:32-34. Before: "Default stages: `make -B`, `make cfall` (the C reference build), the full pytest suite on both models, `make check` (SameBoy, DMG + CGB), and the `RUN_SLOW=1` double-speed and half-rate tests. `FULL=1` adds the slow fade tests;". After: "Default stages: plain `make`, then side by side the full pytest suite on both models, `make cfall` ... and the `RUN_SLOW=1` double-speed and half-rate tests, and `make check`. `FULL=1` uses `make -B` and adds the release-only tests and the slow fade tests;".
5. docs/dev/memory_snapshot/MEMORY.md:56. Before: "verify.sh default ~8 min; FULL=1 adds slow fade". After: "verify.sh default ~5 min (plain make, parallel stages); FULL=1 adds make -B, release-only tests, slow fade".
6. docs/dev/memory_snapshot/verify-quick-for-map-art.md:3. Before: "verify.sh default is the ~8 min stage set; FULL=1 adds slow fade,". After: "verify.sh default is the ~5 min stage set (plain make; pytest, cfall and slow ds/hr side by side); FULL=1 uses make -B, adds release-only tests and slow fade,".
7. tools/dev/verify.sh header: rewritten (stage list, FULL=1, log format, why the stages do not clash). The live memory under /home/node/.claude/projects (not in the repo) still says about 8 min; the supervisor syncs it.
All "N min" placeholders are now "about 5 min" (items 1 to 6 and the verify.sh header), from the source-touched run.

## Owner fixes after batch 2 (one commit each)

**Fix 1: `make -B` when the Makefile or a generator changed** (verify.sh `build_mode`). The default build is plain `make` unless `FULL=1`, or the branch (`git diff --name-only main...HEAD`), its uncommitted changes (`git diff --name-only HEAD`) or untracked files touch the Makefile or a generator file; then it is `make -B`. The log gets a line `build mode: <cmd> (<reason>)` before the build section. If `main` is missing or the list cannot be read, it chooses `make -B`.
*Generator list, derived from make itself:* every `tools/` path in the rules whose target is under `build/` (`make -pn all`, wildcards expanded, so it follows the Makefile): the scripts the recipes run (48 files in all: tools/gen_*.py, palettes2c.py, rom0free.py, ...) and their `tools/` prerequisites (gen_art.py, harmony.py, taiko_chart.py, cannon_table.py, tools/dev/extra_combos.py, tools/smap_world/world_snap.py, palette_plan/*.py and plan_slots.json, the B3a additions). Rules for `make test`, atlas, map-atlas and dist are left out, so editing ptest.py does not force -B. Not covered: a `tools/` module a generator imports that no rule names; the import closure of every generator (A2) found none. `VERIFY_MODE_ONLY=1` prints the decision and exits; `VERIFY_BASE` (default `main`) is the ref to compare with.
*Dry run proof* (real git, scratch edits appended and removed again by reverse edits; `VERIFY_BASE=HEAD VERIFY_MODE_ONLY=1`, out/b3/mode.sh):
| Case | Decision |
|---|---|
| no edit | make |
| Makefile (scratch comment) | make -B, changed vs main: Makefile |
| tools/gen_trans.py (generator) | make -B, changed vs main: tools/gen_trans.py |
| tools/harmony.py (B3a prerequisite) | make -B, changed vs main: tools/harmony.py |
| src/tip.c | make |
| tools/dev/ptest.py (not a generator) | make |
| no edit again | make |
| FULL=1 | make -B (FULL=1) |
| base main, this branch (it changes the Makefile) | make -B |
The stub flow still passes (stub run: `build mode: make -B (could not read the generator list from make)`, RESULT: PASS). git status was clean after the dry run except verify.sh itself.
*Instruction lines touched.* CLAUDE.md:67 before "plain `make`, then pytest," after "plain `make` (`make -B` when the branch changes the Makefile or a generator), then pytest,". SUPERVISOR.md:67 before "are plain `make` (incremental), then" after "are plain `make` (incremental; `make -B` when the branch changes the Makefile or a generator), then". LESSONS.md:32 before "Default stages: plain `make`, then" after "Default stages: plain `make` (`make -B` when the branch changes the Makefile or a generator), then". verify.sh header line 8: now says make -B with FULL=1 or when the Makefile/a generator changed, and that the log has a "build mode:" line.

**Fix 2: one `pytest_collection_modifyitems`** (tests/conftest.py). The two definitions are merged (release_only, only_model, then the PERF_ONLY filter as a helper). `--collect-only tests`, before / after: default 6630 / 6630; `FULL=1` 6631 / 6631; `PERF_ONLY=1` 6630 / 253 (the filter was dead before: pytest kept only the second definition; it now keeps the Color speed guards); `FULL=1 PERF_ONLY=1` 6631 / 253. Part C item 6 below is therefore fixed.

## Part C: proposals (not done)
1. **Refresh tests/durations.json** (`tools/dev/ptest.py -j 1 --record`, serial, quiet machine, about 10 min; it is a balancing file, never changes results) and give test_show_ext, test_practice_art their real 80 s. Saves about 80 s of the pytest stage (shards 178 s to about 95 s by the simulation). Risk: none for results; re-record every few weeks. Do NOT raise `-j` after: -j 12 saves at most 10 s more (floor is the 84 s builds) and loads the shared machine. Do not add `-j` to the Makefile: only 6.5 s of generators, multi-target rules would first need `&:` (they race under -j; they already run twice under -B), saving at most 5 s.
2. **Start `make release` with the build**: after the generators are up to date, run `make`, `make release` (and cfall) as three separate processes at once, so ptest's 75 s serial prebuild disappears behind the 80 s build. Saves about 75 s. Risk low (separate makes, own obj dirs, no shared output; same method as B1's no-clash table); the generators must run first and once (`make assets`).
3. **Per-object compilation** (`lcc -c` per file, `make -j`, then link): compile 73 s to about 9 s measured at 12 jobs (out/obj/exp.sh), and incremental builds recompile only what changed; every one of the 7 builds per verify and the three 80 s tests get cheap (saves about 60 s on the critical path, more in tests and in agents' own loops). Risk: medium. My first attempt linked a ROM that differs from the lcc one-shot ROM (other bank packing, order dependent, two attempts gave two different hashes), so it needs its own proof (ROM identity or an accepted, tested re-layout) and an asm/ROM0 budget check. Biggest single lever.
4. **Merge train** (verifying several finished branches together): the supervisor merges the finished, individually targeted-tested branches into one scratch branch `train-<date>` in order, one verify run on the result, then ff-merges main to it. If the combined run fails: (a) read the failed stage and tests; (b) if they touch one branch's files, take that branch out (a new train branch without it, never a revert) and re-run; (c) if it is an interaction, bisect by two-branch trains (run only the failing tests on each half); (d) the branch that caused it goes back to its worker. Goldens: each branch lists its changed goldens as today; the supervisor replaces them on the train branch. Saves one verify (about 5 min) per extra branch. Risk: a bad branch delays the others; limit trains to branches that touch different areas (art plus engine, not two engine branches).
5. **test_make_dist rebuilds release twice** (prebuild plus `make dist`), only with FULL now: skip the prebuild's release when FULL is not set is not possible (other tests read it); instead make `dist` reuse an up-to-date build/release.gb (the test already has dist_is_current but dist/ is empty in a fresh worktree). Saves 80 s on FULL runs only. Risk: low; changes a test helper, so it needs the owner's OK.
6. Doubt, not a saving: tests/conftest.py defines `pytest_collection_modifyitems` twice (lines 88 and about 836); the second replaces the first, so the PERF_ONLY=1 filter is probably dead. Worth a look by a test owner.

## What I checked versus assumed
Checked: B2 counts; B1 with stubs (not with real make/pytest, no timed verify run); B3 checksums in 7 scenarios; gap fixes by dry run; Part A timings, with load given. Assumed: that the stages do not clash beyond A4's read of the code (no real parallel run yet: gb-runner's timed run is the first); the after-times above are estimates. Test run results (pytest) were not run by me beyond `--collect-only`; no goldens changed.

## C1 + C2 (follow-up, 2026-11-09)

**C1: tests/durations.json refreshed.** `FULL=1 tools/dev/ptest.py -j 1 --record tests` (FULL so the release-only test_make_dist is timed). Machine: no other pytest or lcc, load 1.93 at start and about 2.1 at the end (my own stub runs and waiting loops added to it; the owner's limit was 2, so this is on the edge, not below it). 6533 passed, 96 skipped, 737 s. Before: 554 of 6628 tests missing, file total 612.7 s; after: none missing, total 900.9 s; test_practice_art 78 s, test_show_ext 77 s, test_make_dist 147 s (FULL only: its own release build plus `make dist`). Shard plan at -j 8 for the default verify collection (ptest.plan, phase 1; phase 2 is 1 s): before 314 314 314 314 314 314 314 314 (flat: the estimate was inflated by the 554 unknown tests at 1 s or more; measured batch 1 shards were 178 146 62 135 63 69 41 64 s), after 70 78 77 70 70 70 70 70, longest 78 s (the two 77-78 s build tests each sit on a shard; that is the floor).

**C2: `make release` beside `make`.** Clash findings: both ROMs depend on `$(ROM_DEPS)`, which includes every generated source, so two plain makes started together would both run the generators into the same build/ files (race). Everything else is separate per variant (build/<variant>.flags, build/obj/<variant>/ with its own hUGEDriver.o copy and lcc tempdir, build/<variant>_link.log, .gb/.map/.noi/.sym). Fix: new Makefile target `prep` (= ROM_DEPS plus the game and release flags stamps, no lcc). verify.sh now runs `make prep` first and once (`make -B prep` in -B mode, then build/game.gb and build/release.gb are removed so lcc really reruns), then `make release` in the background beside `make`. make check, cfall and the slow stage start when `make` finishes; the pytest stage waits for the release build. ptest's own prebuild is then `make release` on a current ROM: measured 0.045 s. Sections and RESULT lines unchanged, plus a new "== make release" section with "RESULT release: PASS/FAIL".
Proofs. (1) Real build in this worktree: after `make prep`, `rm -f build/game.gb build/release.gb`, `make &` and `make release &` together: both rc 0, both done at 74 s (against about 80 s + 75 s serial); build/game.gb sha256 6303312820bc... identical to the serial build from before; build/release.gb 929abe0177a1... identical to a serial rebuild. (2) Stub flow (PATH stubs for make and python3 in a scratch git tree, out of the repo): all pass gives RESULT: PASS with the stub's call log showing `make -B prep`, then `make release` and `make` started within 1 ms, then check, cfall, slow, then ptest; STUB_FAIL=release gives `RESULT release: FAIL` and `RESULT: FAIL (failed stages: release)` with END; STUB_FAIL=build gives `RESULT: FAIL (build)` and the background release make is killed (no stub process left); STUB_FAIL=prep gives `RESULT: FAIL (build)`.
Not done on purpose: no timed verify (gb-runner), and no "about N min" or stage-list text changed anywhere (still "about 5 min"); the verify.sh header's stage list is untouched too. Expected saving: about 75 s of the pytest stage's prebuild (the first run in a fresh worktree; later runs find release current anyway).

**C2b: cfall moved out from beside pytest (found in the timed run c1c2: 6533 passed / 95 skipped against 6574 / 56).** B1's A4 "no shared files" was wrong: pytest reads build/game-c.gb (test_mugs_asm 12, test_catch_asm 10, test_asm_equiv 9, test_asm_twins 6, test_story_map_world 4 skip without it; in incremental mode they read the old or a half-written one) while `make cfall` ran beside it. Now `make cfall` starts in the build phase beside `make` and `make release` (after `make prep`; -B mode also removes build/game-c.gb), and the pytest stage starts only when all three are done. Guard: before pytest, verify.sh requires cfall's output to say CFALL_OK and build/game-c.gb to exist and be non-empty (make cfall exits 0 only when the C ROM is current, and in -B mode the old one was removed); otherwise the log gets the failed stage's section, `RESULT: FAIL (failed stages: cfall)` and END, and ptest never starts. A comment in verify.sh that said the three stages do not clash was rewritten.
Proofs: (1) real: after `make prep`, `make`, `make release` and `make cfall` ran at once, all rc 0, done at 76, 76 and 78 s; game.gb 6303312820bc..., release.gb 929abe0177a1..., game-c.gb ff5b7a0c4d19... all byte-identical to the serial builds (cfall writes only build/game-c.*, build/obj/game-c/, game-c.flags, game-c_link.log). With the fresh C ROM, test_asm_twins + test_mugs_asm + test_catch_asm: 28 passed, none skipped. (2) stub: all pass, with cfall 5 s slow, shows ptest starting only after cfall finished; STUB_FAIL=cfall gives `RESULT cfall: FAIL`, `RESULT: FAIL (failed stages: cfall)`, END, and the call log has no ptest line.
What else pytest reads that a parallel stage writes (checked): the only stage left beside pytest is the double speed / half rate one, which writes out/dsmr/ (own ROM build) and out/dsoff/ (patched ROM copies written by rename, same bytes for the same key; ptest's own tests use the same files); pytest reads build/game.gb, build/release.gb, build/game-c.gb, build/*.json, all finished before it starts. make check writes out/check before and alone. Not checked by running: the full ptest, so the skip count is expected back to about 56 but not measured (gb-runner's run shows it).

## C2b timed (gb-runner, commit 092e624b, load 3.3 -> 5.9, build mode make -B because the Makefile changed)

| Stage | Wall | Result |
|---|---|---|
| build (make -B) | 82 s | PASS |
| release (beside) | 75 s | PASS |
| cfall (beside) | 78 s | PASS |
| make check | 1 s | PASS |
| pytest (after all three builds) | 110 s | PASS, 6574 passed, 56 skipped |
| double speed / half rate (beside pytest) | 14 s | PASS, 63 passed |
| **total** | **3 min 15 s** | **RESULT: PASS** |

Skips are back to the batch-1 set (56): no skips in test_mugs_asm, test_catch_asm, test_asm_twins, test_story_map_world; test_asm_equiv only the 2 RUN_SLOW exhaustive sweeps. The earlier c1c2 run (3 min, 6533 passed / 95 skipped) had read no game-c.gb: the race B1 introduced, fixed by C2b. Instruction lines now say "about 3 min" and list the new stage order (CLAUDE.md:67, SUPERVISOR.md:67-68, LESSONS.md:32-33, gb-runner.md:19, verify.sh:7, memory snapshot).
