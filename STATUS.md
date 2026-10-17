# Status (branch asm-b1-b2, from main 9d9ed79)

Batch 1 (ASM_F: perf_ly / perf_snap asm in src/main.c, C kept under #else): DONE and verified before batch 2 edits.
make test 4504 passed, GB_ROM=build/game-c.gb pytest 4505 passed, make check and gbcheck game-c OK, data layout identical,
rig cases 0 mismatches (tests/test_asm_equiv.py, RUN_SLOW sweep passed). ROM0 free 126 -> 273 B. No golden changes.
test_perf asm vs C: level8 same, pile 311/313 vs 311/313, realistic peak dmg end 234 vs 216 (single-worst frame, noisy), missed 239 vs 245.
Not finished: profiler comparison (out/run_prof.sh asm|c, then python3 out/cmp.py prof_c prof_asm main:_perf_ly,main:_perf_snap) and the
RUN_SLOW test_build run (out/b1_build.log) were still running; rerun if the logs are empty. out/ is not committed.

Batch 2 (ROM0 relief in C): WIP, UNBUILT AND UNTESTED. New src/rom0_relief.c (#pragma bank 21) holds add_score (BANKED) and
dancers_step (dancer_look + draw_dancers); render.c draw_stage_fx calls dancers_step(); game.h declares both BANKED; bonus.c extern
add_score now BANKED (shared-file edit, one line). hi_pick/split6 skipped as told.

Resume: make (fix compile errors, e.g. duplicate externs in rom0_relief.c), make cfall, then make test / make check, cfall pytest,
gbcheck game-c, RUN_SLOW test_build, tools/data_layout_check.py, report ROM0 free + bank 21 free, commit batch 1 and 2 separately
(this WIP commit mixes them: main.c carries both edits).
