# Test batch 3 report: fast builds (2026-11-09)

Branch `worktree-agent-a951f5888047b62b4` (ff-merged to main 0e0c293b first). Brief: docs/dev/notes/test_batch3_brief_2026-11-09.md.
Not touched: assertions, goldens, perf guards, game code. ROM0 free space is unchanged (477 B real, same ROMs byte for byte).
The one-shot lcc build is still the default; the new build is `make OBJ=1`. 24 cores; load (1-minute `uptime`) is given with each timing.

## S1, S2 (commits 4eb08ed1, 4ff55cde)
**S1.** SUPERVISOR.md step 7 has the merge-before-review rule; the memory note is copied to docs/dev/memory_snapshot/ and indexed.
**S2.** `tools/dev/skip_baseline.txt` (supervisor-owned: header, `count 56`, the 56 skipped IDs from a full green run; in tools/dev because only verify reads it and test authors do not edit it) and `tools/dev/skipcheck.py`. verify.sh compares the asm pytest run's results.txt: more skips, or a skipped ID not in the list, gives `RESULT: PASS (skips 58 > 56)` plus a "skipped tests" section naming the IDs; never a failure.
Proof (stub make/python3, real results files): normal 56 gives `RESULT: PASS`; two extra skips gives `RESULT: PASS (skips 58 > 56)` with both IDs listed; one fewer gives `RESULT: PASS` and the section lists the test that ran; same count but a different ID gives `RESULT: PASS (skips 56 vs 56: OK, new IDs)`.

## Part A: per-object build (OBJ=1)
**How the one-shot lcc call works** (`lcc -v`): it runs `sdcc -c` on each .c in command-line order (src sorted, then GEN in the Makefile's order), then ONE `bankpack -yt0x1B -lkout=x.lk <121 objects in that order, hUGEDriver.o last>`, then `sdldgb ... crt0.o -f x.lk`, `ihxcheck`, `makebin`. bankpack rewrites its input objects in place. So the object order is the command-line order, and objects must be copied before a link.
**A1 (714f518c, e47f97a8).** `make OBJ=1` (also read from the environment, so the tests' own `make BUILD=...` calls follow): `tools/dev/objs.mk` compiles each C file with `lcc -c -Wf-MMD` (header dependencies, `OBJJOBS` jobs, default 8 per build) into `<BUILD>/obj/<variant>/o/`; the ROM recipe then copies the objects to `.../link/` and runs one lcc link in the fixed order. Own object dir per variant and per BUILD dir; nothing shared. Covers game, release, unlocked, cfall and every `BUILD=` variant. objs.mk knows nothing of the generators, so `make -B` cannot re-run them in parallel. verify.sh: header says `(OBJ=1)`; with `make -B` it also clears `build/obj/*/o`.
Variants, one-shot vs OBJ=1, sha1 equal in all three (tools/dev/obj_variants.sh):
| Build | sha1 (12) | one-shot | OBJ=1 |
|---|---|---|---|
| test_show_ext cgb_rom | 651ab23367c7 | 76 s | 15 s |
| test_practice_art | fd7c05139255 | 77 s | 14 s |
| double speed dsmr (-DAUTO_MR) | 2252fc5d26e3 | 76 s | 15 s |
Also green with OBJ=1: `tests/test_show_ext.py -k color` (2), `tests/test_practice_art.py` (25), `RUN_SLOW=1 tests/test_build.py` (variants do not disturb each other).
**A2 + A3 (01202538): deterministic and BYTE-IDENTICAL to the one-shot ROMs.** tools/dev/obj_hashes.sh in a fresh dir each time; same tree:
| Run | game.gb | release.gb | game-c.gb |
|---|---|---|---|
| one-shot (out/bo) | cabc63dc320c475d33bb6d65b6dd2410f392c3c3 | 9e2226ec4ee1625dd3d5dc6771400fc85a8a8f9d | 844d47af0b7dd97d27f582d69e9760a553f70091 |
| OBJ=1 jobs 1, dir A | same | same | same |
| OBJ=1 jobs 4, dir B | same | same | same |
| OBJ=1 jobs 8, dir A | same | same | same |
| OBJ=1 jobs 8, dir B | same | same | same |
So there is no layout decision and Part B does not apply. (The .map/.noi differ only in object path text.) My guess at why batch 2's naive relink differed: it linked objects that bankpack had already rewritten, or in another order; here the copies are pristine and the order is the one-shot's.
**A4 (f1a93af8): incremental = clean, per edit** (tools/dev/obj_incremental.sh, game / game-c, first 12 hex, build/ vs out/b_clean, OBJ=1):
| Edit | Result | Hashes |
|---|---|---|
| base | MATCH | cabc63dc320c / 844d47af0b7d |
| .c: src/tip.c new function | MATCH | fe75e56cee83 / 9479d44247a0 |
| header: src/layout.h BT_DY 2 to 3 | MATCH | 8673a3a0733e / 1cc056d4ed74 |
| asset: assets/art/coin.txt one pixel | MATCH | 56c34fe4f82b / 0f5745c3ccc4 |
| generator: tools/harmony.py comment | MATCH (= base) | cabc63dc320c / 844d47af0b7d |
| Makefile: VERSION 0.9 to 0.8 | MATCH | 8c6b07a99b02 / 074933196617 |
| all reverted | MATCH (= base) | cabc63dc320c / 844d47af0b7d |
The header and Makefile hashes equal batch 2's one-shot hashes for the same edits. Scratch edits reverted with new edits; `git status` clean.

## A5: timing (game.gb alone unless noted; one build, own BUILD dir)
| Case | One-shot | OBJ=1 | Load (before) |
|---|---|---|---|
| clean build | 76.6 s | 14.5 s | 4.8 / 2.8 |
| incremental, one-line .c edit (src/tip.c) | 73.2 s | 0.3 s (1 compile + link) | 3.6 / 2.6 |
| incremental, widely included header (src/layout.h, 105 of 120 objects) | 74.4 s | 12.4 s | 2.5 / 2.2 |
| three clean builds at once (make, release, cfall), OBJ=1 | about 76 s each (about 80 s measured in batch 2) | 20.6 s | 2.8 |
| test variant builds (show_ext, practice_art, dsmr) | 76 to 77 s each | 14 to 15 s each | 2 to 4 |
| one default verify run | 3 min 15 s (owner's number) | **PLACEHOLDER: gb-runner, `OBJ=1 tools/dev/verify.sh <worktree> b3-obj`** | |
The single lcc call is 120 compiles in series (0.6 s each); OBJ=1 runs them 8 at a time (CPU time is the same, about 77 s). Disk: build/obj/<variant>/o is 28 MB per variant (lcc's .asm/.lst/.sym are deleted).

## Part B
Not needed (byte-identical).

## Recommendation
Switch the default to OBJ=1 once gb-runner's `OBJ=1` verify run (default stages) passes and its time is in the table above; the evidence is hash identity for all three ROMs and three variants, five incremental proofs, and 5x to 250x faster builds. To switch: in the Makefile make `OBJ ?= 1` (and keep `OBJ=0` for the one-shot as the reference); in CLAUDE.md "The loop" note that `make` is per-object (8 jobs, own object dirs under build/obj/) and `make OBJ=0` is the old one-shot; update the verify timing in CLAUDE.md, SUPERVISOR.md, LESSONS.md, gb-runner.md and the memory snapshot once measured; add to gb-toolchain a line that tests' `make BUILD=...` builds follow `OBJ`. Risks: under verify three builds at 8 jobs each is up to 24 jobs on a 24-core shared machine (lower `OBJJOBS` if other agents suffer); a header deleted after a .d file named it is handled by an empty `%.h` rule; `make clean` removes the objects with build/.
Doubts: the .c-edit time (0.3 s) is a single run; the verify-time gain is not measured yet (placeholder); I did not run the full pytest with OBJ=1 (gb-runner's verify does).
