# Spigoteer test review (read-only, nothing changed)

## Summary

1. 6104 tests, 553 s serial (measured today, quiet machine). make test measured 112 s wall here, not 230 s (230 s was likely load from other agents plus the same imbalance).
2. The wall time is mostly one bad estimate: tests/durations.json is from 10-27 and knows 495 tests. Today's slow tests (rng 38 s, credits 61 s, soak 27 s, extra looks 14 s) count as 0.02 s each, so one shard gets 109 s against its 46 s plan, another 82 s. A refresh brings the wall back to about 65-70 s (10-29 was 65 s).
3. Only 8 tests cost 260 s of the 553 s: practice_art first entry (63, a ROM build), make dist (61, a ROM build), rng (34), credits audit (2 x 21), asteroid bot (2 x 10). The other 6,000 tests together cost about 290 s.
4. Nothing in the soak or the fade chain makes an older test safe to drop. The one overlap is inside test_credits (the audit repeats the roll-line check). Every other candidate guards an owner bug or a perf guard. All 578 goldens are read by a test; none are byte-identical pairs.
5. Taking every proposal below: about 51 s serial saved (9%), and the wall comes down by the durations refresh and the rng split, not by deleting tests. Nothing gets deleted without your OK.

## Why 65 s became 230 s

- Shard plan estimated 46 s per shard. Measured shards: 65, 53, 57, 109, 54, 51, 82, 38 s (run today, 8 shards).
- The 109 s shard holds test_rng (38), credits (27), extra_looks_pixels (14): none are in durations.json, so the planner stacked them blind.
- The 82 s shard holds the soak (29) plus perf and mg tests.
- The earlier 130 s p1s4 is the same effect: where the unknown slow files land changes with the collection order.
- Floor: make dist is 61 s and pinned to shard 0. Perfect balance cannot beat about 65 s until that is faster.
- First run in a fresh worktree also pays a 60 s ROM build in test_practice_art (cached afterwards).
- Collection itself is fast (0.8 s).

## Table (files over 1.5 s; the rest are grouped below)

| file | tests | serial s | class | reason | saving s |
|---|---|---|---|---|---|
| test_practice_art.py | 25 | 64.4 | SLOW | One test pays 63 s: it builds a second ROM (placeholder art) with make. Cached after the first run in a worktree, so it only bites fresh worktrees. Not a test problem. | 0 |
| test_credits.py | 60 | 61.4 | MERGE | test_centring_audit_of_every_card costs 21 s per model. Its roll-line loop repeats test_the_roll_shows_every_line_centred (same lines, same 1 px limit, 2.7 s). Keep its card-centre part (about 2 s), drop the loop. The credits are due a remake anyway. | 38 |
| test_release.py | 5 | 61.2 | KEEP | make dist, 61 s, always rebuilds the release ROM. Pinned to shard 0, so it sets the wall-time floor (about 65 s). Speed idea: reuse build/release.gb if it is newer than src. | 0 |
| test_rng.py | 6 | 38.4 | SLOW | Guards the owner bug "it does not feel random". 5 runs of 90,000 frames in one test (34 s). Split into 5 parametrized tests so the shards share it. Same checks, no loss. | 0 |
| test_glitch_soak.py | 94 | 27.5 | KEEP | New, 27 s for 74 runs (20 more under RUN_SLOW). Unique: checks every frame against game state. Cheap for what it covers. | 0 |
| test_mg_asteroid.py | 56 | 22.9 | KEEP | Two bot games at 10 s each (a Python search plans the route). Guards the 10-sprites-a-line limit. | 0 |
| test_extra_looks_pixels.py | 40 | 13.5 | SLOW | 40 tests at 0.34 s: each boots its own ROM. Boot once per venue and loop the looks. Unique: pixels against the source art, which the soak does not check. | 7 |
| test_mg_monkey.py | 93 | 13.3 | KEEP | Parrot test (8 s) guards the owner bug "a run where no parrots appeared". Keep 40 seeds. | 0 |
| test_pouroff.py | 92 | 11.5 | KEEP | Two tuning tests of 12 and 8 seeds (6 s) pin the spec "win by 3-6". Fewer seeds would make them flaky. | 0 |
| test_pause.py | 196 | 10.6 | KEEP | 196 small checks, 0.05 s each. | 0 |
| test_perf.py | 68 | 10.1 | KEEP | Perf guards. Never dropped. | 0 |
| test_mg_tuning.py | 191 | 9.0 | KEEP | Unique coverage. | 0 |
| test_asm_equiv.py | 15 | 8.5 | SLOW | perf_ly on DMG takes 7.5 s, the same test on Color 0.9 s: the first Rig build is paid by whichever runs first. Build the Rig once per module. | 6 |
| test_mg_milkrun.py | 108 | 8.4 | KEEP | Unique coverage. | 0 |
| test_mg_tshirt.py | 97 | 8.2 | KEEP | Unique coverage. | 0 |
| test_story.py | 195 | 7.9 | KEEP | Unique coverage. | 0 |
| test_boss_in_place.py | 200 | 7.0 | KEEP | Unique coverage. | 0 |
| test_perf_arcade.py | 4 | 6.4 | KEEP | Perf guards. Never dropped. | 0 |
| test_save_upgrade.py | 79 | 5.9 | KEEP | Unique coverage. | 0 |
| test_twists.py | 51 | 5.1 | KEEP | Unique coverage. | 0 |
| test_mg_taiko.py | 61 | 4.8 | KEEP | Unique coverage. | 0 |
| test_difficulty.py | 50 | 4.4 | KEEP | Unique coverage. | 0 |
| test_sound.py | 120 | 4.0 | KEEP | Unique coverage. | 0 |
| test_mg_logroll.py | 68 | 3.8 | KEEP | Unique coverage. | 0 |
| test_story_map.py | 125 | 3.4 | KEEP | Unique coverage. | 0 |
| test_classic_mode.py | 71 | 3.2 | KEEP | Unique coverage. | 0 |
| test_idle_gap.py | 50 | 3.2 | KEEP | Unique coverage. | 0 |
| test_extra_looks_venues.py | 70 | 3.1 | MERGE | See test_extra_looks.py. | 0 |
| test_mg_marshmallow.py | 65 | 2.9 | KEEP | Unique coverage. | 0 |
| test_edge.py | 62 | 2.8 | KEEP | Unique coverage. | 0 |
| test_qd.py | 58 | 2.8 | KEEP | Unique coverage. | 0 |
| test_ou.py | 38 | 2.7 | KEEP | Unique coverage. | 0 |
| test_lift.py | 44 | 2.7 | KEEP | Two games side by side, pixel equal. Has one strict-known xfail (rare 4th lift). Not covered by the soak. | 0 |
| test_mg_logroll_fish.py | 44 | 2.6 | KEEP | Unique coverage. | 0 |
| test_keg_bartender.py | 122 | 2.5 | KEEP | Unique coverage. | 0 |
| test_trans.py | 30 | 2.4 | KEEP | Unique coverage. | 0 |
| test_dregs_gag.py | 78 | 2.3 | KEEP | Unique coverage. | 0 |
| test_boss_mothership.py | 49 | 2.3 | KEEP | Unique coverage. | 0 |
| test_boss_sumo.py | 53 | 2.1 | KEEP | Unique coverage. | 0 |
| test_story_pictures.py | 58 | 2.1 | KEEP | Unique coverage. | 0 |
| test_fade_chain.py | 25 | 2.1 | KEEP | New, 2 s. Per-frame fade colours: unique. | 0 |
| test_music_cpu.py | 17 | 2.1 | KEEP | Unique coverage. | 0 |
| test_classic.py | 92 | 2.1 | KEEP | Unique coverage. | 0 |
| test_boss_cap_ui.py | 84 | 2.0 | KEEP | Unique coverage. | 0 |
| test_patron_clear.py | 4 | 2.0 | KEEP | Unique coverage. | 0 |
| test_boss_duke.py | 47 | 2.0 | KEEP | Unique coverage. | 0 |
| test_extra_looks_zoo_space.py | 52 | 1.9 | MERGE | See test_extra_looks.py. | 0 |
| test_rush.py | 39 | 1.9 | KEEP | Unique coverage. | 0 |
| test_music_batch234.py | 35 | 1.8 | MERGE | See test_music_batch1.py. | 0 |
| test_venues.py | 134 | 1.8 | KEEP | Unique coverage. | 0 |
| test_bs.py | 42 | 1.8 | KEEP | Unique coverage. | 0 |
| test_antics.py | 66 | 1.8 | KEEP | Unique coverage. | 0 |
| test_menu_scroll.py | 28 | 1.8 | KEEP | Unique coverage. | 0 |
| test_jukebox.py | 66 | 1.8 | KEEP | Unique coverage. | 0 |
| test_double_speed.py | 36 | 1.7 | KEEP | Unique coverage. | 0 |
| test_debug.py | 114 | 1.7 | KEEP | Unique coverage. | 0 |
| test_story_difficulty.py | 70 | 1.7 | KEEP | Unique coverage. | 0 |
| test_boss.py | 36 | 1.7 | KEEP | Unique coverage. | 0 |
| test_barchange.py | 68 | 1.7 | KEEP | Unique coverage. | 0 |
| test_bonus2.py | 62 | 1.7 | KEEP | Unique coverage. | 0 |
| test_scores.py | 48 | 1.6 | KEEP | Unique coverage. | 0 |
| test_patrons.py | 86 | 1.6 | KEEP | Unique coverage. | 0 |
| test_trans_fade.py | 26 | 1.5 | KEEP | Settled picture, TRANS clear, volume: fade_chain does not check these. | 0 |
| test_mg_card.py | 24 | 1.5 | KEEP | Unique coverage. | 0 |
| test_extra_looks.py | 25 | 1.3 | MERGE | Same 11 checks as test_extra_looks_venues and test_extra_looks_zoo_space, one set per venue. One parametrized module would be easier to keep. Time: none. | 0 |
| test_music_batch1.py | 10 | 0.9 | MERGE | Two tests also in test_music_batch234.py (generated notes, harmony clash). Merge by parametrizing over tunes. Time: none. | 0 |
| test_show_resume_attrs.py | 10 | 0.6 | COVERED | The soak (shows and their ends, attribute check of every cell) would catch the same bug class, but this guards the owner bug of 11-01 (HANK flicker) and costs 0.6 s. Kept by rule. | 0 |
| test_chooser_trace.py | 3 | 0.5 | KEEP | Asm vs C chooser equivalence. Soak does not replace it. | 0 |
| test_saloon_looks_lift_mirror.py | 12 | 0.2 | KEEP | Pixel mirror check of the Color looks. The soak checks cells, not mirroring. | 0 |
| test_perf_saloon.py | 1 | 0.1 | KEEP | Perf guard. Never dropped. | 0 |
| 77 other files | 1751 | 44.5 | KEEP | Each under 1.5 s. Per-boss, per-venue and per-minigame files repeat the same shape on purpose (one set per boss or game); I found no duplicate checks worth merging for time. | 0 |

Total proposed saving: 51 s serial.

## Other findings

- xfail: test_perf realistic-peak target (owner target unmet, strict=False) and test_lift 4th-lift sway. Both documented, keep.
- 85 skipped: 20 soak runs (RUN_SLOW), 22 fade_hw (SameBoy only), ~37 asm/C tests that need build/game-c.gb (make cfall), a few others. Not dead tests.
- STALE: found none by reading headers and names. Not verified against every test body.
- Per-boss / per-minigame repeats (his_row_and_art, follows_the_last_call, win_the_fight_by_pouring across 9 boss files; screen_and_art and goldens across 7 minigame files): MERGE for upkeep only, 0 s.
- Goldens: all 578 read by at least one test (checked with an Image.open hook over a full run; 18 apparent misses were hook gaps, re-run and found). No byte-identical pairs. Near twins (under 1 % of pixels differ, both models): filling / spout_fill (0.06 %), mg_list / practice_art_quickdraw (0.10 %), mg_list_locked / ol_practice_locked_bonus (0.30 %), ts_aim / ts_meter (0.17 %), scene / story_bonus_life (0.39 %). They are different screens of different tests; dropping one saves almost nothing. Not proposed.

## Speed fixes

1. Refresh tests/durations.json: `python3 tools/dev/ptest.py -j 1 --record` on a quiet machine (about 9 min). Biggest win: wall 112 s to about 70 s. Redo after big new test files.
2. Make ptest treat a test missing from durations.json as unknown-slow (for example the file mean, or put new files first), not 0.02 s. Stops new slow tests from wrecking a plan.
3. Split test_rng into 5 parametrized runs (same checks) so shards share its 34 s.
4. Credits audit: drop the roll-line loop (38 s serial).
5. Shared boots: extra_looks_pixels (boot once per venue, about 7 s), asm_equiv Rig built once (about 6 s).
6. make dist test: skip the rebuild when build/release.gb is current. Lowers the 65 s floor.
7. practice_art ROM build: nothing to fix in the test; warm out/b_pa in new worktrees.
