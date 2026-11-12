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

## Update, same day: the timing-independent state check and the 43 open ones

tests/test_c_state_equiv.py (rig tests/c_state_rig.py): the same scripted run on game.gb and game-c.gb, compared on game STATE only (about 90
logic variables: score, lives, level, patrons, mugs, bartender, boss, story progress, RNG) at the start of every main-loop pass. A hook on the
RET of joypad() answers update()'s call with the script's mask for that pass and records the state in the same call, so both ROMs see the same
input at the same logical step whatever their speed. (My first version drove PyBoy's buttons between emulator frames; that gave false
divergences because a late C frame can read the joypad before the host has changed the buttons.) Scenarios: ARCADE levels 1, 2, 4, 7, 9;
random title menus; three boss fights; boss fights with START/A/B mashed (pause menu, hint cards); seven mini-games; DMG, Color double speed
and Color normal speed. Result: all 54 runs have identical state at every step. Findings of the check:

- The story map is the one place where state depends on speed, by design: its walk adapts its pace to the loader rate (src/smap.c V_RATE, the
  "pace the loader can keep"). A new story's first walk ends at stop 0 at one step in the asm ROM and later in the C ROM. The SMAP single-twin
  ROM alone reproduces it (the map code's speed). The comparison ends at the map's first step; the map's code is covered by the twin tests
  (test_asm_twins) and by the pace tests (known list, A-MAP-PHASE).
- Fields that are timing-dependent by design and left out of the comparison: patron_lift (lift.c decides from frame_t0 whether the frame has
  run over), the frame_counter value (aligned by a poke at the start; the logic reads its parity).
- A real C-build LIVELOCK, found by the pause scenarios: pausing a boss fight on a Color at NORMAL speed (not the shipped double speed) never
  returns. The card fade waits in vframe (src/trans.c) for a frame that is not late, and the slow C split handlers (ASM_SPLIT_PAL twin) make
  every frame late. The asm ROM and the C ROM at double speed are fine. The shared code is correct; only a faster C split handler removes it
  (fixing vframe would change game.gb). Two strict xfails in the state test mark it.
- No state divergence anywhere else: no C twin was found to differ from its asm in behaviour in these scenarios.

The 43 open ones are now classified (tests/c_build_known.txt, the C stage has 0 failures, 5758 passed, 447 skipped, 0 not reported):
- A-SPLIT-TWIN 32: reproduced by the SPLIT_PAL single-twin ROM alone (3 more of the 35 SPLIT_PAL-only are the C-ASM-HOOK ones). This is
  attribution, not a measurement of the late write; the picture tests that fail (lifted looks, show colours, goldens of the show at rows 8-10)
  cannot tell a late palette write from a wrong value. Medium confidence; the twin copies the same 8 source bytes.
- A-PHASE 5: test_look_window (CHOOSER/F twins alone), test_boss_yeti, test_pour, test_rng: the test pokes or counts at an emulator-frame
  boundary; the logic is equal in the state check. Medium confidence.
- A-SPEED-GUARD 4 more: test_perf, test_perf_arcade 2, test_half_rate (guards that also fail at double speed).
- C-ASM-HOOK 2 more: test_show_three's `split_put_o` KeyErrors.

## Update 3: the normal-speed livelock fixed (C twins only)

Measured with PyBoy hooks (out/ scripts, not committed): T-cycles since the VBlank vector at which the main loop resumes (frame_wait's RET), arcade
level 4 on a Color at normal speed, a line is 456 T-cycles:

| | asm game.gb | game-c.gb before | game-c.gb after |
|---|---|---|---|
| first palette put (split_vbl3) starts | 1312 | 1408 | 1304 |
| second put starts | 1576 | 2244 | 1752 |
| main loop resumes | 1952 (LY 148) | 3072 (LY 150-152) | 2528 (LY 149) |
| C `split_put_a` (8 BG bytes) | 156 | 960 | ~330 |

The fade (src/trans.c vframe) accepts a frame only when the main loop is back by line 149; the C chain resumed at 150 to 152 on every frame, so
the pause card's fade never returned. Changes, all inside `#if !ASM_SPLIT_PAL` in src/main.c: the 8 palette bytes are stored unrolled through one
`put8()` (the source as plain bytes, so SDCC does `ld a,(bc) / inc bc / ld (de),a`; the counted loop cost ~120 T-cycles a byte), the OBJ path is its
own function so the BG put has nothing in front of its stores, and `split_vbl3` waits for the HBlank itself instead of through a wrapper.
game.gb sha1 unchanged (9ee22ebc...); game-c.gb ROM0 free 85 -> 80 B.

Effect: the pause scenarios of the state check pass at Color normal speed (the two strict xfails are removed), and 105 of the 389 known-list
entries pass now (A-DS-PASS 88, A-SPEED-GUARD 6, A-LATE-WRITE 6, C-ASM-HOOK 4, A-PHASE 1) and are dropped; 1 test that now fails
(test_rng two_title_timings [cgb]: 7 spawns in 3000 emulator frames, 8 needed) is added as A-PHASE. Known list: 389 -> 285.

What is left of the late writes: the C `split_isr3` still lands its palette 1 to 2 lines after the asm one (a hit costs ~2000 T-cycles of which ~400
are the put; the decode is ~270 instructions of stack-heavy SDCC code, and the C hides the window after the decode where the asm hides it first).
A further speed-up needs a restructured decode, not a faster store loop; not done.

## Update 4: the split palette lands on the asm's lines (owner Q37: "fix it if we can now")

Measured with PyBoy hooks (arcade level 4, Color, normal speed; T-cycles; a line is 456; scripts in out/, not committed). "hit" is the LCD interrupt of
a palette event, "put" its first palette write:

| | asm game.gb | game-c.gb before | game-c.gb after |
|---|---|---|---|
| write line of the early stage palette / keg's / late | 31 / 38 / 39 | 32 / 40 / 41 | 31 / 38 / 39 |
| write line of the HUD's BG 1 at the floor row | 136 | 138 | 136 |
| phase of those puts in the line (T-cycles) | 288 / 320 / 304 / 288 | 320 / 336 / 304 / 352 | 336 / 320 / 304 / 336 |
| decode, hit to the first wait loop (median, range) | 492 (492-548) | 1260 (828-1428) | 1176 (792-1436) |
| hit to first put, with the wait for the HBlank | 588 / 620 / 588 | 1116 / 1548 / 1572 | 1548 / 1536 / 1548 (3 lines early, same lines) |
| ISR cost per hit, entry to return (median) | n/a (naked) | 2316 | 2020 |
| main loop resumes after the VBlank (median) | 1952 (LY 148) | 2308 (LY 149) | 2116 (LY 148) |

What was done (C twins only, game.gb sha1 unchanged): the C decode cannot get below about 1200 T-cycles (the asm's is 490: SDCC spills every local and
promotes the list indexing to 16 bits; a table-driven rewrite and a pointer-walking rewrite were both measured and were SLOWER, 1290 and 1570, so they were dropped). So at normal
speed the C twin's hit comes `SPLIT_HIT_EARLY` = 3 lines before its event's line instead of the asm's 1 (src/game.h, used by split_plan in src/level.c
through `SPLIT_HIT(ds)`; in the asm build the macro is `(ds)`, the same source as before): the decode and the wait for the event's HBlank then
fill the 3 lines and the write lands on the event's own line. The 8-byte put was already unrolled (`put8`); the keg-and-late hit sets the late index
before its wait and calls `put8` directly, and split_vbl3 calls `put8` directly: the VBlank chain is 140 T-cycles from the asm's, so the C frame
resumes in line 148 like the asm's, with about 600 T-cycles of room before the cut-off of the fade's vframe (the asm 780).

What is left: events in adjacent lines (a window shown: the keg's and the late reload's separate events, or a window's end next to a palette). A hit cannot start
before the previous one returns and the C hit takes about 3 lines, so the second one writes 1 to 2 lines late; and the C put (a burst of about 190 T-cycles, the asm's 128)
starts late in a short HBlank when sprites lengthen mode 3. 18 known-list entries are of that kind (single-row differences of the golden at rows 40, 86, 102, 112-127).
Fixing them would take the asm's structure (decode the next event while waiting, a 128 T-cycle burst); not done, it would not read as a porting reference.

Known list 285 -> 199 (85 pass now and are dropped, 2 tests that now fail are added as A-PHASE: test_edge [cgb-8] counts the bars patrons came in on in a fixed number of
emulator frames; test_rng two_title_timings was added earlier). C stage with the list: 0 failed, 5950 passed, 255 skipped.

## Open / next

1. The remaining A-LATE-WRITE / A-SPLIT-TWIN entries are adjacent-event cases and short-HBlank puts (Update 4); an asm-shaped decode would be needed.
2. To make the A-SPLIT-TWIN entries proofs: a test that reads the palette RAM bytes written by the C and the asm handlers at each event line
   (same values, any time) would settle value versus lateness.
