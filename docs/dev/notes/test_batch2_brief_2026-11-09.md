# Test Changes — Batch 2: Faster Verify

Goal: bring the default verify run from 8 min 20 s to about 3–4 min, without making it less trustworthy. Start from main, with batch 1 merged.

## Ground rules

- Work on a branch. One commit per item, with a message naming the item.
- Allowed test edit: adding or changing **markers only**. No assertion changes, no deletions, no golden changes.
- Releases keep the full, clean path: a release verify must still do everything it does today.
- Bulk reading, timing runs and verify go to subagents. Get summaries back, not raw logs.
- Other agents share this machine. Check the load before timing anything, and include it in every timing you report.
- If a proof below fails or is unclear, don't make that change. Report it instead.

## Part A — Find out first (read-only)

1. **Why does `make -B` take 80 s?** Time each build step and list the top 10. Does the Makefile run in parallel (`-j`)? Which steps are asset conversion that could be cached?
2. **Why does verify use `-B`?** Check git log or blame on verify.sh, and report the problem it was added to prevent. Does the Makefile track its dependencies fully: includes, headers, and assets?
3. **The three ~80 s tests** (`test_show_ext` setup, `test_practice_art` setup, `test_release::test_make_dist`): what does each one build, and where? Could the builds be cached by source hash, or reuse the main build?
4. **Can stages run side by side?** For `make cfall`, the double speed/half rate stage and the asm pytest stage, list what each reads and writes. Name any shared file, folder or port that would clash.
5. **Why `ptest -j 8`?** On 24 cores, would more shards help, or does the 80 s floor from item 3 dominate? Is durations.json still well balanced?

## Part B — Approved changes

Make each one only if its proof passes.

### B1. Overlap stages
- Run `make cfall` and the double speed/half rate stage alongside the asm pytest stage, if A4 shows no clashes.
- Each stage still gets its own section and RESULT line in the log. The overall RESULT waits for every stage and fails if any stage fails.
- **Proof:** use your stub method from batch 1 to show a failure in each parallel stage still produces RESULT: FAIL.

### B2. Release-only tests
- Mark `test_make_dist` as release-only, so it runs only with `FULL=1`.
- **Proof:** show `--collect-only` counts with and without `FULL=1`.

### B3. Incremental build in the default verify
- The default verify uses plain `make`. `FULL=1` keeps `make -B`.
- **Proof:** build clean and record the ROM checksums (`game.gb`, `game-c.gb`). Then run at least 4 edit scenarios (a source file, a header or include, an asset, a Makefile change). After each, the incremental build's ROMs must match a clean build of the same tree. Revert the scratch edits afterwards.

### B4. Cache the slow one-off test builds
- Cache the builds found in A3, keyed by a hash of their inputs.
- **Proof:** same checksum method as B3. A changed input must rebuild, and an unchanged one must reuse the cache.

## Part C — Propose only (don't do)

- Any change to `ptest -j`, or adding `-j` to the Makefile, with your evidence from A1 and A5.
- **Merge train:** a rule for verifying several finished branches together in one run. Include what the supervisor does when a combined run fails.
- Anything else from Part A that would save more than 30 s.

## Report

Write `.claude/audit/batch2-report.md`, kept compact:

- **Part A:** findings, with numbers.
- **Part B:** per item, what changed, the proof results, or why it was skipped.
- **Timing:** one default verify before and after on the same commit, with the load for each, as a stage table like batch 1's.
- **Part C:** proposals, each with the expected saving and risk.
- Update every instruction line that states a verify time or lists verify's stages, and quote each one before and after.

Don't merge yet. Reply with the report path and a 3-line summary.
