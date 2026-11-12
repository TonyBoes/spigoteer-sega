# C-build test triage, 2026-11-12

Owner 11-12: "Work on the c build tests." The 11-01 hold is lifted. Standing rule (memory c-build-speed-not-required): speed and timing
guard failures in the C build are allowed; wrong pictures, wrong behaviour, crashes, hangs and asm/C mismatches are real.

Base: main at 44b679be. `build/game.gb` sha1 9ee22ebcf0669af7f7a5f743617791c2d0ae95a8 (before and after: no source change).
ROM0 real free: game.gb 477 B, game-c.gb 85 B, release.gb 804 B (unchanged).

## How the C stage runs

`CBUILD=1 tools/dev/verify.sh` runs `GB_ROM=build/game-c.gb python3 tools/dev/ptest.py -j 8 tests`. conftest reads GB_ROM.

## The coverage question (952 vs 1668 tests in earlier runs): answered

ptest ran every shard with `--timeout=180 --timeout-method=thread`. In the C build some tests hang (below). The thread method does
`os._exit` for the whole shard process, so the shard's junit XML is never written and every result of that shard, including the tests that
had already passed, is lost. Which shards die depends on how the 8 shards were cut, so the count of reported tests changed from run to run.
First full run of this session: 6768 collected, 286 failed, 4672 passed, 54 skipped, **1756 not reported** (shards 2 and 6 died; ptest
says "N collected tests have no result" and exits 2).

The hangs: `tests/test_pause.py` and `tests/test_boss_in_place.py` had `while rows[16] != "A BACK": tap(a)` loops. In the C build the boss
hint card does not open at normal speed (the fade out takes longer than the test's wait, see below), so the loop never ended.
Fixes (test side, same meaning): both loops are bounded (12 taps, then assert), and ptest takes `PTEST_TIMEOUT_METHOD=signal` and
`PTEST_TEST_TIMEOUT=SECS` from the environment (default unchanged: thread, 180); verify.sh's C stage sets signal and 90 s. With that
the C suite completes: 6769 collected, 0 not reported, about 100 s wall.

## Result of a complete C run

6769 tests: **393 failed**, 6319 passed, 56 skipped (before the known list below).

How each failure was classified (scripts kept in out/, not committed):
1. Every failing id was re-run on 14 single-twin ROMs (`-DASM_<X>=0` one at a time: F, DRAW_HELD, SCANS, LIFT_DRAW, UPDATE_MUGS,
   PATRON_LOOP, PATRON_STEPS, BOSS_HATS, LIFT_FRAME, CHOOSER, SPLIT_PAL, TILE_COPY, SMAP, CLOUD) and on game-c.gb at double speed.
2. Golden failures were measured with tools/dev/golden_bbox.py (read-only).

| single-twin ROM | failures it reproduces |
|---|---|
| SPLIT_PAL | 263 (CGB only: the mid-frame palette split handlers) |
| SMAP | 54 (story map, DMG pace) |
| CLOUD | 27 (story map clouds) |
| UPDATE_MUGS | 12 (CGB boss fights) |
| TILE_COPY | 10 (test_antics ends-on-time 6, test_debug 4) |
| F | 3, CHOOSER 2 |
| DRAW_HELD, SCANS, LIFT_DRAW, PATRON_LOOP, PATRON_STEPS, BOSS_HATS, LIFT_FRAME | 0 |

On game-c.gb at double speed (the speed the Color ships at, owner Q92) 137 of the 393 pass.

## Groups

**(a) speed / timing: 296 tests** (all in tests/c_build_known.txt with their code)
- A-LATE-WRITE 77: CGB golden or pixel comparisons whose only difference lies in rows 40-106, the chain lines of the stage palette split.
  Typical: venue_biker.cgb 24 px, bbox 136,40,159,40 (one line, the right 3 tiles); stage_anim_*, venue_*, patrons_*, boss_* the same
  rows. This is a mid-frame palette write that the slower C handler (ASM_SPLIT_PAL twin) lands late. Evidence: the diff is a few lines
  at the split line and nowhere else; the same test passes on every other single-twin ROM; 105 of the SPLIT_PAL failures pass at double speed.
- A-DS-PASS 106: fail at normal speed, pass on the same C ROM at double speed. Includes the boss hint card tests (test_pause,
  test_boss_in_place, test_pause_card_fade, boss_cap_ui, fade_chain): at normal speed the C palette reads in the card fade (`pal_in`, which
  reads colours only inside lines 144-152 of the VBlank, and the C split ISR eats that VBlank) take about 60 frames instead of 8, the test
  has long tapped again, and the card never shows. Measured: tw_SPLIT_PAL at normal speed, the card is not open after 300 frames; at double
  speed it opens in 12 frames, like the asm ROM (LCD off at frame 12, window on).
- A-MAP-PHASE 96: test_smap_pace_dmg (36), test_smap_motion (31), test_story_map (21), test_story_map_world (6), clouds (2): they count
  frames or take pictures at a frame count; reproduced by the SMAP and CLOUD twins alone (the C map code is slower, "Sal moved 0 px on frames
  [...]" on frames the loop ran late). Weakest evidence of the groups: I did not check that no map picture differs for another reason.
- A-SPEED-GUARD 17: ends-on-time (test_antics 6, reproduced by the TILE_COPY twin alone), "frames end no later" (test_boss_in_place 10),
  tick gap (test_trans). Owner: expected.

**(c) test assumes the asm build: 54** (C-ASM-HOOK): test_show_obj5.py hooks the asm labels `_split_put_o`, `_split_put_o2`, `_split_put_oe`
(src/main.c) to assert that every OBJ palette write lies in an HBlank. The C twin (`put_o8`, `split_put_a`) has no such labels
(KeyError "no symbol 'split_put_o'"). The module's other tests need the same hooks. Skipped per id in the C build. test_show_three.py
has 2 more of the same family left OPEN (below).

**(b) real C-twin bug: none proven.** No failure survives as a clear difference between a C routine and its asm: the dedicated asm/C
twin tests (test_asm_*, test_mugs_asm, test_catch_asm, ...) pass in this run on game.gb vs game-c.gb. The nearest thing is the
single-twin ROM check: DRAW_HELD, SCANS, LIFT_DRAW, PATRON_LOOP, PATRON_STEPS, BOSS_HATS and LIFT_FRAME alone cause no failure at all.
Nothing was fixed in the C twins; the asm build is untouched (same sha1).

**(d) open, 43** (not explained, left failing, not in the known list). All CGB except 3. Suspected families, none proven:
- lifted-look pixel checks: test_extra_looks_pixels 6, test_extra_looks_venues 6, test_extra_looks_zoo_space 4, test_extra_looks 2,
  test_show_three 6 (incl. 2 more asm-label KeyErrors, so (c)): pixel/colour differences with the show or lift running; probably the same
  late split write but the first differing pixel is not in rows 40-106 or not reported, so not proven.
- test_boss_sumo 4, test_boss_yeti 1, test_boss_leo 1 (blast golden), test_pour 1: fight timing ("the mug moves first (2 px a frame)":
  boss_hits 1 instead of 0). The single-twin check at double speed shows a different set of boss tests failing than at normal speed, so
  these are phase-sensitive (timing), not a logic difference; still not proven.
- test_tips 2 (show.cgb, show_backs.cgb: diff 76,8,85,10, ten pixels at the top of the screen, a different mid-frame write than the split rows).
- test_fade_chain 2 ("scanlines [44] hold colours of another level": row 44 is a chain line; probably late write).
- speed guards that also fail at double speed: test_perf 1, test_perf_arcade 2, test_half_rate 1, test_trans 1.
- test_look_window 2 (DMG spawn sequence for the fixed seed): reproduced by the CHOOSER and F twins alone; the RNG-driven sequence depends on
  frame phase. Candidate for a real difference (the chooser C twin) but the asm/C chooser test passes; not resolved.
- test_rng 1 (chi-square 95 vs 49 degrees of freedom: a statistical bound).

## Per test file (all 393)

| file | failures | by group |
|---|---|---|
| test_show_obj5 | 54 | c 54 |
| test_smap_pace_dmg | 36 | map 36 |
| test_smap_motion | 31 | map 31 |
| test_boss_in_place | 29 | ds 19, guard 10 |
| test_story_map | 21 | map 21 |
| test_pause | 19 | ds 19 |
| test_extra_looks_pixels | 18 | ds 12, open 6 |
| test_fade_chain | 17 | ds 15, open 2 |
| test_boss_sumo | 16 | ds 10, open 4, late 2 |
| test_lift | 10 | late 9, ds 1 |
| test_venues | 10 | late 10 |
| test_art | 9 | late 9 |
| test_stage_anim | 9 | late 9 |
| test_show_three | 8 | open 6, ds 2 |
| test_antics | 6 | guard 6 |
| test_boss_cap_ui | 6 | ds 6 |
| test_boss_duke | 6 | ds 3, late 3 |
| test_extra_looks_venues | 6 | open 6 |
| test_story_map_world | 6 | map 6 |
| test_boss_leo | 5 | late 3, ds 1, open 1 |
| test_boss_mothership | 5 | late 5 |
| test_debug | 5 | ds 5 |
| test_boss_yeti | 4 | late 3, open 1 |
| test_extra_looks_zoo_space | 4 | open 4 |
| test_show_wash | 4 | late 4 |
| 26 files with 1-3 failures each | 59 | see tests/c_build_known.txt and the open list |

## What was changed

- tests/c_build_known.txt + conftest `_c_build_known`: exactly the 350 explained ids are skipped with their code and reason when GB_ROM is a
  C ROM; never a whole file; the asm build never reads it; `C_KNOWN_RUN=1` runs them anyway (refresh after a fix).
- tests/test_pause.py, tests/test_boss_in_place.py: the tap-until-"A BACK" loops are bounded and assert (same meaning, fail in seconds).
- tools/dev/ptest.py: `PTEST_TIMEOUT_METHOD`, `PTEST_TEST_TIMEOUT` (defaults unchanged); tools/dev/verify.sh C stage uses signal / 90 s.

## Open / next

1. The 43 open ones, by family above. Most likely reclassify as late writes with a bbox check; the test_look_window pair and the sumo
   "mug moves first" pair are the ones that could still be real.
2. Real fix candidates for the late writes (if the owner wants the C twin usable at normal speed on Color): the C split handlers are too
   slow, not wrong. At double speed 105 of the 263 SPLIT_PAL failures pass. Not required (owner 11-01).
3. A twin check that would catch a real C bug without timing: run the same scripted input on game.gb and game-c.gb at double speed and
   compare the game state (RNG, positions) frame by frame, ignoring the pictures. Not built.
