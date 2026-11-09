# Test batch 1 report (2026-11-09)

Branch `worktree-agent-a1c83b178316ca175` (fast-forwarded to main first). One commit per item, then this report.
Out of scope and untouched: tests, goldens, perf guards, game code. `make cfall` stays in verify's default.

## Item 1: one testing rule

| File | Before | After |
|---|---|---|
| CLAUDE.md:11-13 | "Done means `make test` and `make check` pass, on both DMG and CGB. A ROM that builds ... Run them" | "Done means committed, and the verify run passes (`tools/dev/verify.sh`, run by `gb-runner`) ... While working, run only the tests for the area you touch (`make test F=<file>` or `make test K=<expr>`), plus `make` and `make check`; the verify run is the one full run." |
| CLAUDE.md:20-23 (rule 3) | "Replacing a golden screenshot is a visible decision. Add new goldens freely. When a test fails because the picture changed on purpose, say so in the commit message with the golden's name and why." | "... a visible decision, and only the supervisor makes it. Add new goldens freely. When a test fails because the picture changed on purpose, leave the failure in, and name the golden, its diff bounding box and why in the commit message and report." |
| CLAUDE.md:51 "Done" | "Done means committed and green on DMG and CGB." | "Done means committed, with your targeted tests and `make check` green on DMG and CGB (verify runs the full suite)." |
| CLAUDE.md:59 | "make test ... (~1.5 min); JOBS=1 for the old serial run" | "full pytest ... (~4 min); JOBS=1 for the serial run. Targeted (preferred while working): make test K=<expr> or make test F=<file>" |
| CLAUDE.md:64 | "Full branch verification (about 20 min; the supervisor or a gb-runner agent)" | "run only by a gb-runner agent ... (default stages about 7 min; FULL=1 adds the slow fade stage, CBUILD=1 adds the C-build pytest)" |
| gb-worker.md:20 | "Test the narrowest thing first (one test file, one `gbtest run`), then the full `make test` and `make check`." | "... (one test file, one `gbtest run`, `make test F=<file>` or `K=<expr>`), then `make check`. Do not run the full `make test`: verify does (CLAUDE.md rule 1)." |
| LESSONS.md:32-33 | "Done means: make -B, make cfall, the full pytest suite on both models, make check, the slow tests (RUN_SLOW=1), and the suite again on the C build" | "Done means: committed, and verify.sh (run by gb-runner) passes. Default stages: ... FULL=1 adds the slow fade tests; CBUILD=1 adds the suite on the C build ... While working, run targeted tests only." |
| gb-toolchain/SKILL.md:43 | `make && make test && make check` | Unchanged. It is the new-project skeleton scaffolding (cp skeleton, then build), not an instruction to run the suite while working. |
| agent_rules/rules_code.txt, batchB_common.txt | line 11 / line 2 told agents to run the full make test / regenerate goldens | Superseded header added at the top, pointing to CLAUDE.md. Grep shows no current instruction file uses them; only old queue briefs, HANDOFF_2026-10-25.md and docs/dev/README.md (an index) mention them, so a header rather than a rewrite. |
| memory_snapshot/one-full-test-run.md, verify-quick-for-map-art.md, c-build-speed-not-required.md | QUICK=1 / "full run" / C tests in verify | Reworded to default / FULL=1 / CBUILD=1, F=/K=, and gb-runner-only reruns. New supervisor-no-full-runs.md copied from the live note. MEMORY.md index lines updated (not asked for, but the old index line contradicted the new wording). |

## Item 2: supervisor never runs full suites
SUPERVISOR.md step 7, before: "... run `make cfall`, `make`, `make test`, `make check` once on main."
After: "brief `gb-runner` to run ... once on main. **The supervisor never runs a full `make test` or `verify.sh` itself ... every full run goes to `gb-runner`, including this rerun.** Targeted tests (one file, `-k`) are fine."
Memory note: supervisor-no-full-runs.md (repo copy).

## Item 3: verify.sh stages
- verify.sh: default = make -B, cfall, asm pytest, make check, double speed/half rate. `FULL=1` adds "slow: fade"; `CBUILD=1` adds "pytest (C build)"; `QUICK=1` ignored. Header, the log's worktree line, and the expected pytest-total count (2, +1 FULL, +1 CBUILD) updated.
- SUPERVISOR.md step 6 (the brief said :66-70), before: "(about 20 min). It runs make -B, ... Map and art branches use `QUICK=1` ... engine, fade or timing changes and releases get the full run." After: default stages, FULL=1, CBUILD=1, QUICK=1 no-op.
- gb-runner.md:19, before: "run `tools/dev/verify.sh <worktree> <name>` in the background," After: adds "(default stages, about 7 min; prefix `FULL=1` when the brief says engine/fade/timing/music or release, `CBUILD=1` only when it says porting release; `QUICK=1` is a no-op),".
- Proof that flags reach their stages: ran verify.sh with stubbed make/python3 on PATH (stubs in out/stub, not committed). Stage lines in the log:

| Flags | Stages run |
|---|---|
| none | make -B, cfall, pytest (asm), make check, slow double speed + half rate; RESULT: PASS |
| FULL=1 | same, plus "slow: fade" after make check |
| CBUILD=1 | same as none, plus "pytest (C build)" |
| QUICK=1 | identical to none |
| FULL=1 CBUILD=1 | fade and C build both; the old full run |

## Item 4: make test K= / F=
Makefile: `python3 tools/dev/ptest.py -j $(JOBS) $(if $(K),-k '$(K)') $(or $(F),tests)`, and the same for JOBS=1 with `pytest -q`. ptest.py needed no change: its parse_known_args passes `-k expr` and paths on to collection and the shards. `make -n` shows the plain `make test` command unchanged. Real runs are in the hook table (rows 9 and 10). CLAUDE.md command list documents both (item 1 commit).

## Item 5: hook (`.claude/hooks/filter_test_output.py`)
A command line is wrapped when any segment (split on `|`, `||`, `&&`, `;`) starts, after VAR=value prefixes, with make, pytest, python3 -m pytest, tools/dev/ptest.py or verify.sh. Before: whole line had to be one plain command (no pipes, no chaining). The wrapper is unchanged, so the exit status is `$?` of the whole line as before. Multi-line commands and lines with a background `&` are still left alone (rc would be meaningless).
Hand test: PreToolUse JSON fed to the hook, rewritten command run with bash, in the worktree. Scratch tests in out/hooktests (not in tests/).

| # | Command | Wrapped | Exit | Output lines | Failure shown |
|---|---|---|---|---|---|
| 1 | `pytest` on a passing file | yes | 0 | 4 | n/a |
| 2 | `pytest <passing> \| tail -3` | yes | 0 | 4 | n/a |
| 3 | `echo hi; pytest <passing> && echo after` | yes | 0 | 6 | n/a |
| 4 | `pytest <failing file>` | yes | 1 | 15 | FAILED line and AssertionError |
| 5 | `pytest <failing> \| tail -3` | yes | 0 (tail's, as unwrapped) | 5 | FAILED line |
| 6 | `make -n && make -n test` (dry, to avoid an 80 s build) | yes | 0 | 23 | n/a |
| 7 | `make test K=test_other F=out/hooktests` | yes | 0 | 6 | n/a (1 passed) |
| 8 | `make test F=out/hooktests/test_scratch_fail.py` | yes | 2 (make's code for pytest failure) | 8 | FAILED line, ptest "1 failed" |
| 9 | `tools/dev/verify.sh /nonexistent hooktest` | yes | 1 | 4 | cd error shown |
| 10 | `ls out \| head -3` | no, left alone | n/a | n/a | n/a |
| 11 | `pytest <file> &` | no, left alone | n/a | n/a | n/a |

verify.sh writes its RESULT line only to /workspace/out/verify/<name>.log and prints nothing to stdout, so wrapping it hides nothing; its stdout is empty on success, and the wrapper adds "[filter] full output: ... (exit rc)".

## Skipped or changed from the brief
- Item 1: gb-toolchain/SKILL.md:43 left alone (skeleton scaffolding). MEMORY.md index edited too. rules_code.txt:13 still has its old "full make test" line below the superseded header (historical).
- Item 3: the supervisor's SUPERVISOR.md lines were 66-70 in the numbering you gave; the edit is in step 6.
- The hook test of `make && make test` used `make -n` for both (a real build is ~80 s); the real wrap path was exercised with `make test K=... F=...` and `make test F=...`.
- The timed verify run is not done here (gb-runner will).
- Remaining "full make test while working" lines after grep: none in CLAUDE.md, .claude/agents, SUPERVISOR.md, LESSONS.md, memory_snapshot. Left deliberately: SKILL.md:43 (skeleton), rules_code.txt:13 (superseded), SUPERVISOR.md:73 and :76 (they say verify/gb-runner runs the full test, which is the policy).
- A pkill I tried to clean up my own dry-run was denied; I stopped my background task through TaskStop instead. No process of mine remains.

Verify time: (pending gb-runner)
