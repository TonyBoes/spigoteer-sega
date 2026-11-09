# Test Changes — Batch 1 (approved)

Based on `.claude/audit/test-audit-report.md` (2026-11-09). This batch covers your recommendations 1, 2, 3 and 5, plus one addition of mine. All of these change instructions and scripts only, not tests.

## Ground rules

- Work on a branch. One commit per item below, with a message naming the item.
- **Out of scope:** no edits to tests, goldens, perf guards or game code. Do not delete the C path: `make cfall` must still build and link.
- **Not in this batch:** the known-failures list (rec 4), DMG/CGB doubling (rec 6), and check-what-it-measures (rec 7). Don't start them.
- Delegate bulk reading and the verify run to subagents. Get summaries back, not raw output.
- If an item turns out bigger or riskier than described, stop and tell me rather than working around it.

## Items

### 1. One testing rule, stated once
The Q12 rule (SUPERVISOR.md:71-73) is the policy. Make every other instruction agree with it.

- **CLAUDE.md** holds the short version, since every agent loads it: while working, run only the tests for the area you touch (`pytest` file or `-k`), plus `make` and `make check`. The verify run is the one full run. "Done" means committed, and that verify passes.
- Update CLAUDE.md:11-13, :51-52 and :59 to match. In :59, fix the `make test` time to about 4 min.
- Rewrite **gb-worker.md:20** to the targeted-only rule. Don't restate the policy in agent files; point to CLAUDE.md instead.
- **LESSONS.md:32-33** ("Done means"): align with the new verify stages from items 2 and 3.
- **gb-toolchain/SKILL.md:43**: check what that line is for, and align it if it tells agents to run the full suite.
- **Goldens:** make CLAUDE.md:20-23 agree with :36-38. Agents add new goldens, and only the supervisor replaces existing ones.
- **Old templates** (`rules_code.txt:11`, `batchB_common.txt:2`): update them, or mark them superseded at the top. Use whichever matches how they're still used.
- Update your own memory notes (one-full-test-run, verify-quick-for-map-art, c-build-speed-not-required) so they don't contradict the new wording.

### 2. Supervisor never runs full suites itself
Full `make test` and `verify.sh` runs always go to gb-runner. That includes the rerun on main when other merges landed in between. Write this into SUPERVISOR.md and your own rules.

### 3. verify.sh stages
- **Default** (new): `make -B`, `make cfall`, pytest on the asm build, `make check`, and the double speed / half rate slow tests. This is today's QUICK=1.
- **`FULL=1`** adds the slow fade stage. Use it for engine, fade, timing or music changes, and before any release.
- **`CBUILD=1`** adds the C-build pytest stage. Use it only before a porting release while C tests are on hold.
- Keep `QUICK=1` accepted as a no-op alias so old briefs don't break.
- Update SUPERVISOR.md:66-70 and the gb-runner brief template to match.

### 4. Narrow `make test`
- Add `make test K=<expr>` (passes `-k`) and `make test F=<file>` (one file). Without K or F, it behaves exactly as now.
- Document both in CLAUDE.md's command list as the preferred way to run targeted tests.

### 5. Hook coverage
Extend `.claude/hooks/filter_test_output.py` to also catch piped and chained commands (`|`, `&&`, `;`), `ptest.py`, and `verify.sh`.

- The command's exit status must be unchanged.
- A failing test must still show its failure lines.
- Test the hook by hand on: single `pytest`, `pytest … | tail`, `make && make test`, a passing run, a failing run, and `make test K=…`. List the results in the report.

## Checks before reporting
- One verify run with the new default stages, through gb-runner, timed. Compare it with the 21 min 24 s from the audit.
- Show in the diff that `FULL=1` and `CBUILD=1` still reach their stages. You don't need to run them to completion.
- Grep all instruction files once more for any line that still says to run the full `make test` while working.

## Report
Write `.claude/audit/batch1-report.md`, kept compact:
- Per item: files changed, with each changed instruction line quoted before and after.
- The hook test results and the new verify time.
- Anything skipped or changed from this brief, and why.

Don't merge yet. Reply with the report path and a 3-line summary, and I'll approve the merge after review.
