# DMG/Color test doubling review (2026-11-12)

REPORT ONLY. No test file was edited. Branch worktree-agent-a30ae29d72da75bc3, tool scripts in the worktree's `out/` (not committed).

## Method and its limits

- Collected the suite (`pytest --collect-only`, 6768 selected tests, 69 release-only deselected). A test is **doubled** when its id carries `[dmg]` or `[cgb]` (the `boot` fixture, `tests/conftest.py:367`): **5804 tests in 149 files** (the audit said ~5,727).
- Per doubled test, parsed its source and the same-file helpers it calls (AST, one hop closure) for model signals: `is_cgb`, `model_name`, literal `"cgb"`/`"dmg"`, palette / BCPS / OCPS / BGP / OBP, VRAM bank, golden / screenshot / .png, perf guards (PERF, perf_, missed, drain, budget, double_speed). Any hit = **model-dependent**; no hit = **candidate** for one model.
- Result: **3259 of the 5804 doubled tests are candidates** (about 1630 removable runs after keeping one model).
- This is STATIC evidence. It does not see signals inside the shared helper modules (`tests/*_helpers.py`, `conftest.py` fixtures) or in the ROM code a test exercises. I did not run both models and diff RAM/VRAM per test (about 3,000 tests; too much for this round). Treat the candidate list as a shortlist: at edit time, spot-check each file by running it on both models and comparing a state hash, or by mutating an `is_cgb` branch in a scratch ROM.
- Time: `tests/durations.json` has seconds per FILE (serial, `ptest.py -j 1 --record`), not per test. A file's saving = file seconds x removed/tests x 2 x 0.57, where 0.57 is the CGB instance's share of a pair's time (one measured file, test_idle_gap: DMG 25 tests 1.5 s, CGB 25 tests 2.1 s; one sample only). The figures are estimates, and test_release.py's 147 s is from the OBJ=0 era (it is now about 1 s, item 1) so it is excluded from savings (its doubled tests are 2 header checks).

## Tiers

- **A**: no model signal anywhere in the file's doubled tests. Safest to halve.
- **B**: most doubled tests are candidates, but the file also has model-dependent siblings (golden, palette, perf). The candidates are logic checks in an area that also has a visual or timing side. Judgement call; see risk notes.
- **C**: fewer candidates than model-dependent tests. Halve only the clear logic tests, keep the rest doubled.

## Totals

- Doubled tests: 5804. Candidates: 3259. Removable runs (keep one model): 1627.
- Estimated serial time saved: **144 s of the 901 s suite** (16%). Tier A 37 s (38 files), tier B 84 s (52 files), tier C 23 s (59 files).
- Full `make test` (8 shards, about 113 s of test time, 4 min overall in CLAUDE.md including startup): about **18 s wall** all tiers, 5 s with tier A only (shards are balanced by these same file seconds, so wall scales about linearly).
- `verify.sh` default stages run pytest once on the asm ROM: the same saving. With `CBUILD=1` the C-build pytest repeats it, so double. FULL=1 adds nothing doubled beyond that.
- The saving is modest because per-test time is dominated by a few non-doubled or model-dependent heavy files (practice art, show_ext, glitch_soak, story_map_world, credits).

## Which model to keep for single-model tests: DMG

1. **Strictest timing.** Perf and lateness guards are strict on DMG; owner Q92 relaxes the [cgb] speed checks to double speed as shipped, so a logic regression that costs frames shows first on DMG.
2. **Faster to run.** Measured DMG about 30% quicker than CGB on the same tests (1.5 s vs 2.1 s for 25 tests), so keeping DMG saves more than keeping CGB.
3. **The shared code path is the DMG one.** Colour is a gated addition (`is_cgb`); behaviour common to both is what runs when the gate is off. Logic that is truly model-independent is therefore fully covered by DMG. The reverse is not guaranteed: a CGB-only branch can mask a DMG bug but not the other way round.
4. Against: DMG has the tighter tile and palette budgets, but those tests are model-dependent and stay doubled by definition. Real risk is a candidate that is secretly CGB-gated (see below), where DMG would pass vacuously; for those, keep CGB or both.
5. Mechanism already exists: `@pytest.mark.only_model('dmg')` (conftest.py:861, collection hook line 874) deselects the other instance, so edits are one decorator per test or `pytestmark` per module, and reversible.

## Risk notes (judgement calls)

- **Candidates touching source modules with many `is_cgb` branches** (credits.c 43, smap_eng.c 29, smap.c 22, title.c 21, story.c 20, po.c 16, mg_list.c 11, mirror.c 11, ad.c/bonus2.c/dgag.c 10 each): test_story*, test_story_map*, test_smap*, test_credits*, test_pouroff, test_mg_list, test_title-ish menu tests, test_patrons/mirror, test_bonus2, test_dregs_gag. A test with no model signal in its own text may still read state the gated code writes. Prefer tier A files first; for these keep CGB doubled until a state-hash diff shows equality.
- **Save/RNG/difficulty logic** (test_save_upgrade, test_rng, test_difficulty, test_story_difficulty): model-independent by design, but test_rng and parts of difficulty reference double speed (`double_speed` hits); keep those instances doubled.
- **Music/sound** (test_sound, test_music_*): the driver is shared, but CPU budget per frame differs under double speed; the lateness assertions are model-dependent even where the test text shows no signal. Single-model only for pure register/pattern checks.
- **Boss tests** (test_boss_in_place bgp/palette halves, other boss files golden-heavy): halve only the non-golden logic tests; palette and golden ones stay doubled.
- **`only_model` on a module changes node ids**: if the supervisor or ptest.py keys shards on ids, check `tools/dev/ptest.py` and `tests/durations.json` (file level only: unaffected).
- **Static scan false negatives**: signals in `*_helpers.py`, conftest fixtures (`story`, `show` etc. if they branch on model) and ROM-side gating are invisible here. Edits should wait for the C-build marker work to merge anyway, then run a both-models differential on each file before removing its CGB half.

## Per file (doubled files only, sorted by estimated seconds saved)

Columns: tests = selected tests in the file; doubled = instances with a `[dmg]`/`[cgb]` id; single-model = doubled instances that are candidates (half of these would be removed); est. s = serial seconds saved.

| File | Tests | Doubled | Candidates (single-model) | Tier | Est. s saved | Reason |
|---|---|---|---|---|---|---|
| test_look_window.py | 8 | 8 | 8 | A | 7.0 | no model signal in any test (no is_cgb, model_name, palette, golden, perf) |
| test_mg_asteroid.py | 56 | 40 | 26 | B | 6.7 | candidate tests have no model signal; sibling tests use: palette, cgb, cgb |
| test_mg_monkey.py | 93 | 92 | 66 | B | 6.2 | candidate tests have no model signal; sibling tests use: perf, palette, dmg |
| test_mg_tuning.py | 191 | 190 | 172 | B | 5.8 | candidate tests have no model signal; sibling tests use: perf |
| test_boss_in_place.py | 200 | 200 | 120 | B | 5.3 | candidate tests have no model signal; sibling tests use: bgp, dmg, palette |
| test_save_upgrade.py | 79 | 72 | 72 | A | 5.1 | no model signal in any test (no is_cgb, model_name, palette, golden, perf) |
| test_story_map.py | 249 | 246 | 144 | B | 4.9 | candidate tests have no model signal; sibling tests use: grey, golden, perf |
| test_idle_gap.py | 50 | 50 | 50 | A | 3.6 | no model signal in any test (no is_cgb, model_name, palette, golden, perf) |
| test_twists.py | 51 | 50 | 46 | B | 3.4 | candidate tests have no model signal; sibling tests use: perf, missed, drain |
| test_sound.py | 120 | 110 | 92 | B | 3.4 | candidate tests have no model signal; sibling tests use: perf, model_name, cgb |
| test_difficulty.py | 50 | 50 | 48 | B | 3.2 | candidate tests have no model signal; sibling tests use: golden |
| test_mg_milkrun.py | 108 | 98 | 44 | C | 2.7 | candidate tests have no model signal; sibling tests use: perf, palette, dmg |
| test_mg_tshirt.py | 97 | 92 | 42 | C | 2.5 | candidate tests have no model signal; sibling tests use: perf, palette, cgb |
| test_pouroff.py | 92 | 80 | 30 | C | 2.5 | candidate tests have no model signal; sibling tests use: model_name, cgb, palette |
| test_mg_logroll.py | 68 | 68 | 48 | B | 2.4 | candidate tests have no model signal; sibling tests use: model_name, screenshot, .png |
| test_rng.py | 6 | 6 | 2 | C | 2.2 | candidate tests have no model signal; sibling tests use: double_speed, palette, dmg |
| test_classic_mode.py | 71 | 70 | 60 | B | 2.1 | candidate tests have no model signal; sibling tests use: golden, perf |
| test_mg_marshmallow.py | 65 | 62 | 50 | B | 2.1 | candidate tests have no model signal; sibling tests use: palette, perf, dmg |
| test_menu_scroll.py | 28 | 28 | 28 | A | 2.0 | no model signal in any test (no is_cgb, model_name, palette, golden, perf) |
| test_keg_bartender.py | 122 | 110 | 90 | B | 2.0 | candidate tests have no model signal; sibling tests use: perf |
| test_story_difficulty.py | 70 | 70 | 58 | B | 1.9 | candidate tests have no model signal; sibling tests use: cgb, palette, dmg |
| test_antics.py | 66 | 66 | 58 | B | 1.9 | candidate tests have no model signal; sibling tests use: golden, model_name |
| test_resume.py | 40 | 40 | 40 | A | 1.8 | no model signal in any test (no is_cgb, model_name, palette, golden, perf) |
| test_trans_fade.py | 26 | 26 | 26 | A | 1.8 | no model signal in any test (no is_cgb, model_name, palette, golden, perf) |
| test_boss_sumo.py | 53 | 51 | 39 | B | 1.8 | candidate tests have no model signal; sibling tests use: golden, palette, perf |
| test_edge.py | 62 | 60 | 40 | B | 1.7 | candidate tests have no model signal; sibling tests use: screenshot, model_name, .png |
| test_mg_logroll_fish.py | 44 | 44 | 32 | B | 1.6 | candidate tests have no model signal; sibling tests use: dmg, golden, palette |
| test_boss_mothership.py | 49 | 48 | 32 | B | 1.6 | candidate tests have no model signal; sibling tests use: golden, palette, cgb |
| test_boss_duke.py | 47 | 45 | 35 | B | 1.6 | candidate tests have no model signal; sibling tests use: golden, palette, budget |
| test_asm_equiv.py | 15 | 14 | 4 | C | 1.6 | candidate tests have no model signal; sibling tests use: perf, model_name |
| test_jukebox.py | 66 | 62 | 56 | B | 1.5 | candidate tests have no model signal; sibling tests use: model_name, palette, cgb |
| test_scores.py | 48 | 45 | 40 | B | 1.5 | candidate tests have no model signal; sibling tests use: golden, model_name |
| test_story_map_enter.py | 36 | 36 | 36 | A | 1.5 | no model signal in any test (no is_cgb, model_name, palette, golden, perf) |
| test_patrons.py | 88 | 88 | 78 | B | 1.5 | candidate tests have no model signal; sibling tests use: golden, missed, drain |
| test_debug.py | 114 | 112 | 88 | B | 1.4 | candidate tests have no model signal; sibling tests use: model_name, palette, cgb |
| test_story_map_world.py | 62 | 54 | 6 | C | 1.3 | candidate tests have no model signal; sibling tests use: perf, double_speed, cgb |
| test_tips.py | 78 | 78 | 68 | B | 1.3 | candidate tests have no model signal; sibling tests use: model_name, palette, cgb |
| test_barchange.py | 68 | 66 | 50 | B | 1.2 | candidate tests have no model signal; sibling tests use: model_name, palette, perf |
| test_trans_menu.py | 22 | 22 | 22 | A | 1.2 | no model signal in any test (no is_cgb, model_name, palette, golden, perf) |
| test_music_transitions.py | 28 | 28 | 28 | A | 1.2 | no model signal in any test (no is_cgb, model_name, palette, golden, perf) |
| test_credits.py | 63 | 60 | 6 | C | 1.2 | candidate tests have no model signal; sibling tests use: model_name, golden, dmg |
| test_boss.py | 36 | 33 | 23 | B | 1.1 | candidate tests have no model signal; sibling tests use: model_name, screenshot, palette |
| test_dregs_gag.py | 78 | 68 | 26 | C | 1.1 | candidate tests have no model signal; sibling tests use: golden, cgb |
| test_qd.py | 58 | 58 | 22 | C | 1.1 | candidate tests have no model signal; sibling tests use: golden, model_name, screenshot |
| test_bonus.py | 36 | 36 | 28 | B | 1.1 | candidate tests have no model signal; sibling tests use: golden, perf |
| test_oneline.py | 52 | 52 | 46 | B | 1.0 | candidate tests have no model signal; sibling tests use: model_name, palette, cgb |
| test_trans_puff.py | 12 | 12 | 12 | A | 1.0 | no model signal in any test (no is_cgb, model_name, palette, golden, perf) |
| test_rush.py | 39 | 38 | 22 | B | 1.0 | candidate tests have no model signal; sibling tests use: golden, palette, cgb |
| test_hud_timer.py | 30 | 30 | 30 | A | 1.0 | no model signal in any test (no is_cgb, model_name, palette, golden, perf) |
| test_flow.py | 76 | 76 | 48 | B | 1.0 | candidate tests have no model signal; sibling tests use: model_name, golden, cgb |
| test_story_resume.py | 22 | 22 | 22 | A | 0.9 | no model signal in any test (no is_cgb, model_name, palette, golden, perf) |
| test_boss_sasquatch.py | 25 | 24 | 18 | B | 0.9 | candidate tests have no model signal; sibling tests use: golden, palette |
| test_bonus2.py | 62 | 62 | 28 | C | 0.9 | candidate tests have no model signal; sibling tests use: perf, model_name, golden |
| test_mugs.py | 74 | 74 | 68 | B | 0.8 | candidate tests have no model signal; sibling tests use: golden |
| test_boss_entrances.py | 29 | 26 | 14 | B | 0.8 | candidate tests have no model signal; sibling tests use: palette, golden |
| test_taper.py | 69 | 68 | 54 | B | 0.8 | candidate tests have no model signal; sibling tests use: dmg, model_name, cgb |
| test_scratch_map.py | 47 | 24 | 24 | A | 0.8 | no model signal in any test (no is_cgb, model_name, palette, golden, perf) |
| test_boss_leo.py | 27 | 26 | 18 | B | 0.8 | candidate tests have no model signal; sibling tests use: golden, palette, drain |
| test_mg_shakeup.py | 16 | 16 | 14 | B | 0.8 | candidate tests have no model signal; sibling tests use: screenshot, golden |
| test_music_batch234.py | 35 | 20 | 20 | A | 0.8 | no model signal in any test (no is_cgb, model_name, palette, golden, perf) |
| test_trans_menu_reveal.py | 12 | 12 | 12 | A | 0.8 | no model signal in any test (no is_cgb, model_name, palette, golden, perf) |
| test_boss_yeti.py | 21 | 20 | 14 | B | 0.8 | candidate tests have no model signal; sibling tests use: golden, palette, cgb |
| test_mg_release.py | 32 | 32 | 32 | A | 0.7 | no model signal in any test (no is_cgb, model_name, palette, golden, perf) |
| test_pause.py | 202 | 200 | 12 | C | 0.7 | candidate tests have no model signal; sibling tests use: cgb, palette, double_speed |
| test_boss_mascot.py | 18 | 18 | 14 | B | 0.7 | candidate tests have no model signal; sibling tests use: golden, palette |
| test_bs.py | 42 | 38 | 16 | C | 0.6 | candidate tests have no model signal; sibling tests use: model_name, golden, screenshot |
| test_mg_list.py | 27 | 26 | 20 | B | 0.6 | candidate tests have no model signal; sibling tests use: golden, cgb, model_name |
| test_mg_card.py | 24 | 22 | 14 | B | 0.6 | candidate tests have no model signal; sibling tests use: golden, perf |
| test_mg_taiko.py | 61 | 56 | 10 | C | 0.6 | candidate tests have no model signal; sibling tests use: perf, palette, cgb |
| test_almost_out.py | 16 | 16 | 16 | A | 0.6 | no model signal in any test (no is_cgb, model_name, palette, golden, perf) |
| test_mg.py | 47 | 44 | 18 | C | 0.6 | candidate tests have no model signal; sibling tests use: model_name, screenshot, .png |
| test_boss_tag.py | 31 | 20 | 20 | A | 0.6 | no model signal in any test (no is_cgb, model_name, palette, golden, perf) |
| test_venues.py | 134 | 118 | 32 | C | 0.5 | candidate tests have no model signal; sibling tests use: palette, bcps, bcp |
| test_tune_save_timing.py | 6 | 6 | 6 | A | 0.5 | no model signal in any test (no is_cgb, model_name, palette, golden, perf) |
| test_cameos.py | 14 | 14 | 14 | A | 0.5 | no model signal in any test (no is_cgb, model_name, palette, golden, perf) |
| test_pocket.py | 24 | 24 | 24 | A | 0.5 | no model signal in any test (no is_cgb, model_name, palette, golden, perf) |
| test_story.py | 195 | 166 | 10 | C | 0.5 | candidate tests have no model signal; sibling tests use: golden, dmg, drain |
| test_sfx_taiko_duke.py | 13 | 12 | 12 | A | 0.5 | no model signal in any test (no is_cgb, model_name, palette, golden, perf) |
| test_pause_card_fade.py | 10 | 10 | 10 | A | 0.4 | no model signal in any test (no is_cgb, model_name, palette, golden, perf) |
| test_boss_prototype.py | 21 | 21 | 12 | B | 0.4 | candidate tests have no model signal; sibling tests use: palette, cgb, golden |
| test_trans.py | 30 | 30 | 6 | C | 0.4 | candidate tests have no model signal; sibling tests use: drain, model_name, golden |
| test_bartender.py | 38 | 38 | 32 | B | 0.4 | candidate tests have no model signal; sibling tests use: golden |
| test_debug_tuning.py | 17 | 16 | 14 | B | 0.4 | candidate tests have no model signal; sibling tests use: golden |
| test_arcade.py | 16 | 16 | 12 | B | 0.4 | candidate tests have no model signal; sibling tests use: golden |
| test_hud.py | 15 | 14 | 12 | B | 0.4 | candidate tests have no model signal; sibling tests use: model_name |
| test_boss_flow.py | 11 | 11 | 11 | A | 0.4 | no model signal in any test (no is_cgb, model_name, palette, golden, perf) |
| test_windup.py | 24 | 24 | 24 | A | 0.3 | no model signal in any test (no is_cgb, model_name, palette, golden, perf) |
| test_tip2.py | 15 | 14 | 14 | A | 0.3 | no model signal in any test (no is_cgb, model_name, palette, golden, perf) |
| test_debug_stress.py | 14 | 14 | 8 | B | 0.3 | candidate tests have no model signal; sibling tests use: perf, model_name |
| test_lift.py | 44 | 42 | 6 | C | 0.3 | candidate tests have no model signal; sibling tests use: dmg, model_name, palette |
| test_stage_anim.py | 52 | 50 | 10 | C | 0.3 | candidate tests have no model signal; sibling tests use: model_name, cgb, golden |
| test_mg_bonus.py | 25 | 24 | 8 | C | 0.3 | candidate tests have no model signal; sibling tests use: perf, golden |
| test_pour.py | 41 | 40 | 6 | C | 0.3 | candidate tests have no model signal; sibling tests use: perf, cgb, golden |
| test_smooth.py | 26 | 26 | 16 | B | 0.3 | candidate tests have no model signal; sibling tests use: dmg, golden, budget |
| test_overlap.py | 22 | 22 | 8 | C | 0.3 | candidate tests have no model signal; sibling tests use: budget, model_name, screenshot |
| test_trans_flash.py | 7 | 6 | 6 | A | 0.3 | no model signal in any test (no is_cgb, model_name, palette, golden, perf) |
| test_story_pictures.py | 71 | 54 | 6 | C | 0.3 | candidate tests have no model signal; sibling tests use: drain, model_name, cgb |
| test_ou.py | 38 | 38 | 4 | C | 0.3 | candidate tests have no model signal; sibling tests use: pal_dish, perf, model_name |
| test_spigot.py | 34 | 24 | 24 | A | 0.2 | no model signal in any test (no is_cgb, model_name, palette, golden, perf) |
| test_music_batch1.py | 10 | 4 | 4 | A | 0.2 | no model signal in any test (no is_cgb, model_name, palette, golden, perf) |
| test_chooser_trace.py | 3 | 2 | 2 | A | 0.2 | no model signal in any test (no is_cgb, model_name, palette, golden, perf) |
| test_saloon_looks.py | 6 | 6 | 3 | B | 0.2 | candidate tests have no model signal; sibling tests use: cgb, vram_bank, dmg |
| test_boss_critic.py | 23 | 22 | 4 | C | 0.2 | candidate tests have no model signal; sibling tests use: perf, golden, palette |
| test_music_batch0.py | 13 | 4 | 4 | A | 0.1 | no model signal in any test (no is_cgb, model_name, palette, golden, perf) |
| test_patron_imports.py | 20 | 15 | 12 | B | 0.1 | candidate tests have no model signal; sibling tests use: split_pal, palette, bcps |
| test_story_beats.py | 24 | 10 | 10 | A | 0.1 | no model signal in any test (no is_cgb, model_name, palette, golden, perf) |
| test_harmony.py | 50 | 12 | 12 | A | 0.1 | no model signal in any test (no is_cgb, model_name, palette, golden, perf) |
| test_classic.py | 92 | 92 | 4 | C | 0.1 | candidate tests have no model signal; sibling tests use: dmg, model_name, dmg |
| test_show_tune.py | 5 | 2 | 2 | A | 0.1 | no model signal in any test (no is_cgb, model_name, palette, golden, perf) |
| test_menu_music.py | 22 | 22 | 2 | C | 0.1 | candidate tests have no model signal; sibling tests use: palette |
| test_pause_regs.py | 2 | 2 | 2 | A | 0.1 | no model signal in any test (no is_cgb, model_name, palette, golden, perf) |
| test_bob.py | 4 | 4 | 4 | A | 0.1 | no model signal in any test (no is_cgb, model_name, palette, golden, perf) |
| test_music_loops.py | 19 | 4 | 4 | A | 0.0 | no model signal in any test (no is_cgb, model_name, palette, golden, perf) |
| test_saloon_cat.py | 10 | 2 | 2 | A | 0.0 | no model signal in any test (no is_cgb, model_name, palette, golden, perf) |
| test_ash_palette.py | 3 | 3 | 2 | B | 0.0 | candidate tests have no model signal; sibling tests use: palette |
| test_art.py | 20 | 20 | 0 | C | 0.0 | candidate tests have no model signal; sibling tests use: model_name, golden, palette |
| test_asm_twins.py | 6 | 5 | 0 | C | 0.0 | candidate tests have no model signal; sibling tests use: palette, vram_bank |
| test_boss_cap_ui.py | 84 | 72 | 0 | C | 0.0 | candidate tests have no model signal; sibling tests use: perf, cgb, _drink_pal |
| test_catch_asm.py | 10 | 10 | 6 | B | 0.0 | candidate tests have no model signal; sibling tests use: model_name |
| test_chrome_cow_obj2.py | 3 | 3 | 0 | C | 0.0 | candidate tests have no model signal; sibling tests use: palette, bank1, cgb |
| test_credits_scroll.py | 6 | 6 | 0 | C | 0.0 | candidate tests have no model signal; sibling tests use: double_speed, cgb |
| test_dx_badge.py | 25 | 5 | 0 | C | 0.0 | candidate tests have no model signal; sibling tests use: model_name, cgb, dmg |
| test_erase.py | 24 | 24 | 0 | C | 0.0 | candidate tests have no model signal; sibling tests use: model_name, budget, golden |
| test_extra_looks.py | 25 | 19 | 0 | C | 0.0 | candidate tests have no model signal; sibling tests use: cgb, model_name, palette |
| test_extra_looks_venues.py | 70 | 46 | 0 | C | 0.0 | candidate tests have no model signal; sibling tests use: cgb, model_name, palette |
| test_extra_looks_zoo_space.py | 52 | 43 | 0 | C | 0.0 | candidate tests have no model signal; sibling tests use: cgb, model_name, palette |
| test_fade_hw.py | 22 | 22 | 14 | B | 0.0 | candidate tests have no model signal; sibling tests use: palette, dmg |
| test_glitch_soak.py | 94 | 94 | 0 | C | 0.0 | candidate tests have no model signal; sibling tests use: cgb, dmg, double_speed |
| test_half_rate.py | 27 | 2 | 0 | C | 0.0 | candidate tests have no model signal; sibling tests use: model_name, dmg, cgb |
| test_menu_cursor.py | 22 | 22 | 0 | C | 0.0 | candidate tests have no model signal; sibling tests use: model_name, cgb, cgb |
| test_mugs_asm.py | 12 | 12 | 4 | C | 0.0 | candidate tests have no model signal; sibling tests use: model_name |
| test_patron_clear.py | 4 | 4 | 0 | C | 0.0 | candidate tests have no model signal; sibling tests use: perf, model_name |
| test_perf.py | 68 | 68 | 0 | C | 0.0 | candidate tests have no model signal; sibling tests use: budget, cgb, drain |
| test_perf_arcade.py | 4 | 4 | 0 | C | 0.0 | candidate tests have no model signal; sibling tests use: perf, cgb |
| test_perf_saloon.py | 1 | 1 | 0 | C | 0.0 | candidate tests have no model signal; sibling tests use: drain |
| test_plan_items.py | 9 | 3 | 0 | C | 0.0 | candidate tests have no model signal; sibling tests use: palette, cgb |
| test_plan_slots.py | 24 | 13 | 0 | C | 0.0 | candidate tests have no model signal; sibling tests use: palette |
| test_practice_art.py | 25 | 19 | 0 | C | 0.0 | candidate tests have no model signal; sibling tests use: model_name, dmg, palette |
| test_practice_golden.py | 4 | 4 | 0 | C | 0.0 | candidate tests have no model signal; sibling tests use: golden |
| test_release.py | 4 | 2 | 0 | C | 0.0 | candidate tests have no model signal; sibling tests use: golden |
| test_saloon_looks_lift_mirror.py | 12 | 12 | 0 | C | 0.0 | candidate tests have no model signal; sibling tests use: cgb, palette, lift_pal |
| test_screen_prompt.py | 17 | 3 | 0 | C | 0.0 | candidate tests have no model signal; sibling tests use: cgb |
| test_show_ext.py | 24 | 10 | 0 | C | 0.0 | candidate tests have no model signal; sibling tests use: perf, cgb, palette |
| test_show_restore.py | 4 | 4 | 0 | C | 0.0 | candidate tests have no model signal; sibling tests use: palette |
| test_show_resume_attrs.py | 10 | 10 | 0 | C | 0.0 | candidate tests have no model signal; sibling tests use: vram_bank, bank1, palette |
| test_smap_clouds.py | 9 | 4 | 0 | C | 0.0 | candidate tests have no model signal; sibling tests use: double_speed, cgb |
| test_space_xeno.py | 2 | 2 | 0 | C | 0.0 | candidate tests have no model signal; sibling tests use: palette |
| test_story_map_anim.py | 25 | 22 | 0 | C | 0.0 | candidate tests have no model signal; sibling tests use: cell_pal, cgb, grey |
| test_vq_budget.py | 28 | 28 | 0 | C | 0.0 | candidate tests have no model signal; sibling tests use: drain, model_name, cgb |
