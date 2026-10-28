# Handoff: patron revision batch 2, steps 3-6 (branch patron-rev-2)

Done: step 1 (1d773d4, enhanced looks dropped; 43 CGB goldens left failing, supervisor replaces them), merge of main (0dd3316),
step 2 is a no-op (no story text names ROSIE; gen_credits PATRONS deferred), the Color palette split (see its commit).

## Traps
- `make cfall` BEFORE `make test`: a stale build/game-c.gb makes tests/test_asm_equiv.py hang forever (test_c_vs_asm[dmg-perf_ly]).
- Never rebuild while `make test` runs. Only `make test` (not pytest -k) exercises everything: ~9 min.
- `sleep` is blocked: wait with Monitor. Compound python heredocs with variables are refused as "too complex": use Write/Edit.
- ROM0 free: 651 at start, 704 after step 1, 592 after the split. Banks 1-24 are full (0-262 B); ROM_25 has ~5.8 KB, ROM_19/20/21 785/1347/503.
- WRAM_LO 3936, WRAM_HI_0 3635 (after step 1; the split adds none; it uses HRAM 0xFFD4-0xFFE5).

## The split (game.h SPLIT_*)
BG slots 2,3,4,7 are free for patrons in the Saloon, BG 5 is the stage: the split rewrites BG 5 at line 39 from HRAM SPLIT_PAL (8 bytes
at 0xFFD6), the VBlank restores it from SPLIT_STG. So the 5th patron palette goes in BG 5 (via SPLIT_PAL), the others in 2,3,4,7.
TODO (supervisor): the patron palette written into SPLIT_PAL must get the SCREEN BRIGHT lift like every other palette (src/bright.c,
main.c pal_put lifts; SPLIT_STG is read back from palette RAM so it is already lifted). Add a test for it. Stage_b (BG 6, the cat) is untouched.

## Option 2 (shared blank column) consumers of PATRON_SHIFT0_OFS + v*6
Layout today per group: shifted poses 126 tiles, shift-0 poses at 126+v*6 (3x2 column-major, ids >=128 and even), 3 back views x4 at 144.
Option 2: shift-0 pose has 4 own tiles + 1 shared blank pair, so 50 tiles per look. Consumers to change: src/dgag.c:409-410, src/po.c:154,
src/title.c:493-494, credits cast (`load_patron_pose0` in generated patron_load.c, tools/gen_*), src/mirror.c (pose(), mixed_b flips
6 pose + 4 back tiles of variant 2, all-R DMG case reverses 156 tiles), src/render.c (st_tab, stamp3 third column at shift 0, id_seq
shift-0 entries -> BLANK; do not grow id_seq), src/lift.c, boss tile borrowing (src/boss.h BOSS_BG_A/B, tools/gen_boss.py BOSS_PAIRS_MAX,
the #if checks), tests restored() in tests/test_boss.py and tests/test_mg.py (reads 78*16.. / 0x8800), tests/test_patrons.py BASE/SHIFT0_OFS.

## Steps 4-6 notes
- 8 looks (Saloon): A DUSTY, B EMMA, C GUS (DMG looks; GUS sits out the Big Tex fight: patrons.c try_spawn `v==2 && boss_on`), bank 1: HANK,
  ROSIE (singer), REDD, MABEL, ARTIE. 5 x 50 = 250 tiles in bank 1. patron_variant `&3` -> `&7` in render.c, mirror.c, lift.c and the
  asm `and #3` in draw_lifted_asm (C twin exists; ASM_LIFT_DRAW). lift_prop/lift_tile/lift_pal become 8-entry (lift_prop is [4] now).
- Palettes per look (build.py PLANS["cowboys"]): HANK [3,5,6]; ROSIE [3,4,5,7]; REDD [3,4,5,6,7]; DUSTY [3,5]; EMMA [4,5,7];
  MABEL [3-7]; ARTIE [3-7]; GUS [5,7] = 29 combinations, uniform on Color. Plan slot -> BG: OBJ 3 -> BG 2.., 5 patron BG palettes needed.
- Backs: art in tools/artifacts/palette_plan/art/cowboys_*.txt (fronts), docs/dev/concepts/*sprite*/ (back drafts). EMMA, ARTIE, GUS have no
  back: use clearly named stand-ins and list them.
- Dancers move to OBJ 1, coin to OBJ 0 in the plan (OBJPAL_DANCER / OBJPAL_COIN are still 5): only if the brief says so.
- Step 6: grep main for GUS-always-tips / two tips first (patrons.c maybe_tip, `tip_chance`).
- Both DMG mixed-direction options (mirror.c MIXED_B) must keep working; DMG keeps 3 looks.
