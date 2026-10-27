# Handoff: patron revision batch 2, steps 4-6 (branch of agent-abe02cc24d30eb47b, on top of patron-rev-2 0791845)

Done: step 3 (option 2, the shared blank pair) and the C-twin split_isr fix. Steps 4, 5, 6 are NOT started.
Read HANDOFF_batch2_split.md too (traps: `make cfall` before `make test`; never rebuild while `make test` runs).

## Step 3 as built (the layout every later step builds on)
Per group (152 tiles): shifted poses v*42+(s-1)*6 (0..125), the ONE blank pair at PATRON_BLANK_OFS 126 (ids >= 128 and even, plain
colour 0), the three shift-0 poses of 4 tiles at PATRON_SHIFT0_OFS 128 + v*4 (column-major; OBJ tiles t, t+2), then the 12 back tiles
(PATRON_TILES_PER_GROUP is now 140; BACK_BASE = BASE + 140). PATRON_BLANK = BASE + 126.
- A shift-0 draw's 3rd column is PATRON_BLANK(+1): render.c stamp() (`d & 7` test), stamp3(c, t3), mirror.c quick_mirror (t3), queue path
  (seq_ofs(): id_seq is 126 shifted entries + 3 x 6 shift-0 entries at 126 + 6 v; the tile layout is 4 apart), dmg_mixed copies 4 tiles
  at shift 0, mixed_b flips 4.
- Boss: BOSS_BG_A region 162..203 ends at the blank pair; BOSS_BG_B = OBJ_BASE + 8 = 214: 8 pairs (variant C's shift 0 + back); BOSS_PAIRS_MAX 29
  (gen_boss.py; every boss fits). The 2 ids freed past the back views (230-231) were NOT given to the boss (the snapshot tests compare the
  group's own range).
- Consumers changed: gen_art.py (load_patron_pose0 gives t >= 4 the blank pair), dgag.c pats, po.c load_crowd, lift.c lift_tile (+4 per look),
  title.c unchanged (variant 0, first 2 columns). Tests: test_patrons (BLANK, drawn_tiles, pose_first), test_overlap, test_lift, test_classic,
  test_boss (pairs 29, 214), test_boss_in_place. Tools: palette_plan/build.py PAT_S0/PAT_BACK, gfx_atlas/events.py.
- ROM0 free 565 -> 515 B (render.c stamp +30, seq_ofs +20). Putting the shift-0 handling inline in quick_entries cost 250 B (SDCC spills): keep it in seq_ofs().

## Design settled for step 4 (not built)
- DMG rule from the brief: the DMG pictures must NOT change, so the DMG keeps today's three looks (A DUSTY, B MABEL, C HANK). The owner's
  2026-10-22 plan says the DMG three are DUSTY, EMMA, GUS: that is a later table change (ask the supervisor). Color: A DUSTY, B EMMA, C GUS in the
  bank-0 slots (GUS sits out Big Tex: patrons.c try_spawn `v == 2 && boss_on`, now only on Color for look 2 = GUS, DMG look 2 = HANK stays as today),
  and bank 1: HANK, ROSIE, REDD, MABEL, ARTIE (looks 3..7).
- ROM storage by look, not by group: a look's data is 42 shifted + 4 shift-0 + 4 back = 50 tiles. HANK and MABEL (and DUSTY) are already in
  patron_tiles_cowboys (variants 2, 1, 0): copy their ranges. New blobs needed: EMMA, GUS, ROSIE, REDD, ARTIE (5 x 800 B) from
  tools/artifacts/palette_plan/art/cowboys_{emma,gus,rosie,redd,artie}.txt (fronts, 16x16) and docs/dev/concepts/*sprite*/ (back drafts). EMMA, ARTIE
  and GUS have no back: stand-ins (name them in the commit and report). ROM_25 has ~5.8 KB free.
- Bank-1 layout (BG ids; all of bank 1 is free for tiles): look k (0..4 = looks 3..7) shifted poses k*42 + (s-1)*6 (ids 0..209), blank pair 210,
  shift-0 poses 212 + 4k (even, >= 128, OBJ-able), back views 232 + 4k. BG attribute bit 3 = bank 1, OAM attribute bit 3 = bank 1. Looks >= 3 use
  the bank-1 blank pair (210) as their 3rd column so a footprint has one attribute.
- No st_tab growth (WRAM): looks >= 3 compute their first tile by formula (Color only; DMG never has them). R bars on Color use the attribute flip.
- Quick redraw (render.c queue_quick) for looks >= 3: write the 6 ids into the shadow rows as quick_mirror does (src = shadow, k = 32), or
  send them through mark_dirty (slower). Check the perf guards.
- patron_variant: bits 0-2 look, bits 3-5 palette instance (step 5). The `& 3` uses: render.c (3), mirror.c quick_mirror, lift.c draw_lifted C + asm
  (`and a, #3` at the _patron_variant read), patrons.c spawn (v from next_rand; keep the DMG stream unchanged: Color-only extra next_rand()).
  boss_mothership.c MINI_VARIANT compares the whole byte.
- OBJ palettes: OBJ 3,4,6,7 free for patrons, OBJ 5 is the show's (pal5_check reloads it when a show starts: a lifted patron wearing OBJ 5 would
  be recoloured during a show) and Sal's OBJ 0 already carries the coin. The plan wants the dancers in OBJ 1; nothing of that is built. Decide with the supervisor.
  BG: 2,3,4 and 7 (bar_b is free in the Saloon), and BG 5 through SPLIT_PAL (the stage palette above line 39).
- Step 6: GUS always tips (maybe_tip skips the roll and draws no random number; ARCADE and STORY only, CLASSIC unchanged); at most 2 tips at
  once (second coin slot in an existing union; draw_coin uses OAM_COIN 27 only). SPLIT_PAL must be lifted with SCREEN BRIGHT (src/bright.c)
  and a test added (HRAM 0xFFD6 equals the lifted palette).

## Status at commit 9039771 (step 3 committed)
- C twin: split_isr hides the window first from ONE LCDC read; the split line is `split_line()` (reads the 8 SPLIT_PAL bytes before the
  HBlank wait). pause_menu_boss now matches on the C ROM (GB_ROM=build/game-c.gb). tests/test_split.py still fails on the C ROM (line 40
  reads (24,16,48), PyBoy timing of C's palette writes; very probably failed before too: not checked on the baseline).
- make test: 44 failed = 37 distinct step-1 CGB goldens (patron-area boxes only) + test_perf classic_peak_real_rows[dmg-12]
  (music restart sampled at m=1 twice 66 frames apart: assert_music_every_frame sees d=190; a helper blind spot, guard NOT touched; needs a
  supervisor call) + 5 CGB `palettes(gb) == pals` fails at OBJ palette 4 (test_bs x2, test_pause quits_with_boss_gone, mini_game pause 3):
  most likely step-1 fallout (OBJ 4 no longer loaded in the Saloon), unchecked on the baseline. make check green. ROM0 free 515 B, WRAM unchanged.
- Steps 4, 5, 6 not started; design above stands.

## Status after step 6 (branch worktree-agent-a5774f77ba8c5fc67: 1b6c1e5 step 4, e619fa4 step 5, step 6 commit after it)
- Steps 4-6 done. patron_variant byte: bits 0-2 look, 3-5 (palette instance ^ look), bit 6 PATRON_BANK1. Instances: pi0 BG2/OBJ3 (A), pi1 BG3/OBJ6 (C), pi2 BG4/OBJ7 (E),
  pi3 BG7/OBJ4 (B), pi4 BG5 via SPLIT_PAL / OBJ5 (D). Slot moves vs the plan: plan OBJ5 (C) built as OBJ6, plan OBJ6 (D) built as OBJ5.
- Step 5: mirror.c sal_combo[29], uniform pick from the one spawn byte (boss fights drop GUS and pi 2, 4). Step 6: src/tip.c (maybe_tip banked; GUS always tips in
  ARCADE/STORY via tip_pocket != 0), second coin in story_scratch at SCR_TIP2_AT (tip2.h), OAM 26. One-coin code stays in ROM0 (banked per-frame calls broke test_boss_in_place's guards).
- ROM0 free 481 B, _DATA 7547 B unchanged. Goldens failing: all Saloon/title/menu pictures (art changed on purpose) plus inherited step-1 CGB factory/robots ones; none replaced.
- C ROM (make cfall): extra failures vs f242c5d's C ROM are timing-only (boss_in_place cgb x2, classic mixed_levels cgb x2, debug cgb-1, perf_arcade [10-dmg]); asm ROM green.
- Open: EMMA, ARTIE, GUS backs are stand-ins; during a show a lifted pi4 patron shows the dancers' colours (OBJ 5).
