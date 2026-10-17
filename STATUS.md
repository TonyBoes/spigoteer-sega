# Status (branch asm-b1-b2, from main 9d9ed79)

Batches 1 and 2 are done and verified; the two are in the WIP commit 87dc160 plus this one (main.c carries both edits).

Batch 1 (ASM_F: perf_ly / perf_snap asm in src/main.c, C kept under #else): ROM0 free 126 -> 273 B.
Batch 2 (ROM0 relief in C): add_score (BANKED) and dancers_step (dancer_look + draw_dancers) in src/rom0_relief.c, bank 21.
  ROM0 free 273 -> 1093 B (asm build), 946 B (cfall). Bank 21 free 10325 B. hi_pick/split6 skipped.

Verified on the final tree: make test 4504 passed; GB_ROM=build/game-c.gb pytest 4505 passed; make check and gbcheck game-c OK;
RUN_SLOW test_build passed; data_layout_check identical; rig 0 mismatches (perf_ly: 20,000 random plus RUN_SLOW exhaustive sweep).
No golden changed.

NOT done: profiler re-run against the baseline. The old scripts (out/asm_scripts, not committed) fail on boss/story scenarios against
current main (the CONTINUE menu assertion) and the arcade_peak jobs did not finish in 17 min, so no profile numbers were recorded.
test_perf stands in: level-8 106/118 missed 0; pile 311/313 (unchanged); realistic peak dmg end 236 missed 239 / cgb end 230 missed 288
(C build of the same tree: dmg 216/245, cgb 228/306; single-worst frames swing +-30 with layout).
