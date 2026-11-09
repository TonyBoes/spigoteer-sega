# Test Changes — Batch 3: Fast Builds (C3)

Goal: make `make` fast, so agents stop paying ~73 s per build while working, and every build in verify gets cheaper. Start from main (f7538fd9 or later).

## Ground rules

- Work on a branch. One commit per item, with a message naming the item.
- **The current one-shot `lcc` build stays the default** until I approve a switch. The new build lives behind an opt-in flag (for example `OBJ=1`).
- No edits to assertions, goldens, perf guards or game code. Never raise a perf guard. ROM0's free space must not shrink.
- Three builds already run at once in verify (C2). Cap per-build jobs (start with 8) so verify can't saturate the shared machine, and report the load with every timing.
- Each build keeps its own object directory. No object file may be shared between builds (see a0e50dc0, the shared hUGEDriver.o bug).
- Bulk reading, timing and verify runs go to subagents. Get summaries back.
- Merge-before-review applies only to a fix for a problem already on main (item S1). Nothing in this batch qualifies.

## Small items first

### S1. Merge-before-review rule
Add to SUPERVISOR.md: a fix for a problem already on main may merge before the owner's review if the report says so in its first line, with the reason. Everything else waits for review.

### S2. Skipped-test warning
- Store the expected skip count (currently 56) in a file the supervisor owns.
- When the asm pytest stage skips more than that, verify still finishes, but the RESULT line says so (for example `RESULT: PASS (skips 58 > 56)`) and lists the newly skipped test IDs.
- Only the supervisor changes the baseline, with a reason in the commit message.
- **Proof:** stub or scratch runs showing a normal run, a run with extra skips, and a run with fewer skips.

## Part A — Per-object build (opt-in)

### A1. Build it
- Compile each source to its own object with `lcc -c`, using make's dependency tracking so a header change rebuilds only the objects that include it. Then link.
- It must cover the main ROM, the C twin (`cfall`), `make release`, and the variant builds that tests use (`BUILD=…`, for example `test_show_ext`, `test_practice_art` and the double speed build).

### A2. Make it deterministic
The link order must come from a fixed, sorted list, never from the order jobs happen to finish.

**Proof:** build the same tree 3 times with different job counts (1, 4 and 8) and in two different build directories. All ROM hashes must match.

### A3. Try for byte-identical output
Find out how the one-shot `lcc` call orders objects for linking and autobanking, and reproduce that order.

- If the per-object ROMs (`game.gb`, `game-c.gb`, `release.gb`) match the one-shot ROMs byte for byte, there is no layout decision to make. Say so.
- If they can't match, stop here and do Part B.

### A4. Incremental correctness
Use the same method as B3 in batch 2: an incremental per-object build must match a clean per-object build after each of these edits:

- a `.c` file
- a header included by several files
- an asset
- a generator in tools/
- a Makefile flag

Revert the scratch edits afterwards.

### A5. Timing
Report each of these for both builds, with the load:

- clean build
- incremental build after a one-line `.c` edit
- incremental build after a widely included header edit
- one default verify run with `OBJ=1`, compared with 3 min 15 s

## Part B — Only if A3 can't match (report, don't switch)

- Show where the layout differs: which routines or data moved banks, and ROM0 free bytes before and after.
- Note any bank-switch changes in timing-sensitive code.
- Run `FULL=1` verify, `make check` and every perf guard on the `OBJ=1` ROM as evidence.
- Recommend whether the new layout is safe to adopt. I decide.

## Report

Write `.claude/audit/batch3-report.md`, kept compact:

- **S1, S2:** what changed and the proof results.
- **Part A:** each proof, its result and the hashes.
- **Timing:** a table like batch 2's.
- **Part B:** findings, if it applies.
- **Recommendation:** switch the default or not, and what would change in the instructions if we do.

Don't merge. Reply with the report path and a 3-line summary.
