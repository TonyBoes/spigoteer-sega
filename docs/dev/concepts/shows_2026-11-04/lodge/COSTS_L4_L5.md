# Lodge shows L4 "Log roll" and L5 "Do-si-do", 2026-11-04: costs

Color only. The DMG keeps today's lodge show. Proposals: nothing under `src/` or `assets/` changed. Both were built and run in a scratch copy
(`out/rc` of this worktree) that has the igloo I1b glide block applied unchanged (`../COSTS.md`, the two diffs). Today's Sasquatch is kept: the heads
are pixel-exact copies, and L4 frames 11-12 and L5 frames 0, 2, 6 are today's frames, untouched.

| | L4 Log roll | L5 Do-si-do |
|---|---|---|
| Frames | 16 (11, 12 = today's 1, 3) | 7 (0, 2, 6 = today's 0, 2, 1) |
| Frame width | 24 (every figure in columns 0-15) | 16 |
| 8x16 quarters (bank-1 pool 64) | 49 | 22 |
| OBJ palettes | 1, today's | 1, today's |
| Cells per frame (max 4) | 4 | 4 |
| OBJ entries per line, worst (limit 10) | 6, measured in the engine on lines 8-39 for a whole show | 6, the same |
| Loop | 16 beats = 64 rows (a row every 3 frames) | 16 beats = 64 rows |
| Glide records | 25 | 21 |
| New WRAM | 0 | 0 |
| Built and run in the engine | yes (Color, double speed) | yes |

Nothing else uses lines 8-39; the patrons start at line 40. Each performer is at most 2 cells wide on a line, so 3 x 2 = 6.

## What happens

- **L4.** The log is two halves: each birler's frame carries the half under his feet (the left birler is the X-flip of the right one), so the log stays whole
  while one of them falls. Beats 0-3: they birl; the log turns (a bark stripe steps down its face every row, and a mark goes round the end grain). The third
  cheers at stage right. Beats 4-5: the log stops, both wobble. Beat 6: the right one drops behind the log. Beats 7-9: he hangs on the log, dazed; the third
  runs over (x 120 to 72, eased) and holds out a hand. Beat 10: he climbs back with the hand. Beats 11-15: birling again; the third runs home and cheers.
- **L5.** Beats 0-3: three in a line, hands linked, gallop 32 px left and back. Beats 4-5: two hook arms and swing a half turn; the third gallops to the right
  end. Beats 6-9: the pair swings its way across to the right while the third gallops to the left end: they cross mid-stage. Beats 10-11: whoops at both
  ends. Beats 12-15: they cross back and link hands in the middle. The swing is a circle of radius 8 px, a 45-degree step every 2 rows (front and back view,
  side views facing, one passing in front, side views). The front dancer is always performer 0 (OAM priority); at each half turn the two figures change
  performers, which cannot be seen (same poses in the same places), so the turn goes on the same way round.

## Measured (scratch copy, Color at double speed as shipped)

- ROM0: 447 B free before and after (linker map). No ROM0 code.
- Banked data (whole ROM used, vs the same scratch copy with today's lodge): L4 +2773 B (the DMG per-performer block 219 B, the Color glide block 979 B,
  the pool 1571 B = 49 quarters, bank-1 ids 0-97, one segment). L5 +1832 B (219 B, 915 B, pool 707 B = 22 quarters, ids 0-43).
  The glide code itself (show_ext.c +78 B) is the igloo's and is shared.
- WRAM: WRAM_LO 160 B free and WRAM_HI_0 461 B free, unchanged.
- Perf, the guards' metric (logic end line), the lodge with 4 patrons walking, one whole show (581 sampled frames): today's lodge dance mean 20.7, p90 48,
  worst 78; L4 mean 26.5, p90 56, worst 87; L5 the same. No late frames. As at the igloo, the glide redraws a performer every frame.
- `make test` on each scratch build: 6217 passed, 7 failed, the same 7 for L4 and L5; all perf guards passed. None is the art:
  - `tests/test_mg_logroll_fish.py`, 6 cases (cgb and dmg): the mini-game's Sasquatch is drawn from the lodge's legacy show rows, and the test reads the
    frame from the tile id (`(tile - OBJ_DANCER) // 8`). A Color show needs `"performers"` in `lodge_show_pal.json`, whose DMG block packs today's 4 frames
    into shared 8x16 quarters, so the ids move (the pictures are the same frames). Checked: `"performers"` alone, with no Color file, fails the same way.
  - `tests/test_venues.py::test_a_bonus_round_between_levels_restores_the_performer_tiles[cgb]`: it counts 12 performer sprites with bank-0 ids
    `OBJ_DANCER..+31`; on Color the show now uses bank-1 ids. Passes with `"performers"` alone.

## Engine and generator changes beyond the glide block

None. Both shows use the igloo I1b glide block as it is (`src/show_ext.c`, `tools/gen_art.py`).

## To import one (for the supervisor, after the owner picks)

1. The glide block diffs (`../COSTS.md`), if the igloo's I1b has not brought them in already.
2. `assets/approved/venues/lodge_show_cgb.txt` = `lodge_show_L4_cgb.txt` or `lodge_show_L5_cgb.txt`; in `lodge_show_pal.json` add `"performers"` (three
   `{"loop": [0, 1, 2, 3], "flip": 0}`, today's dance) and `"performers_cgb"` (the JSON line in the file's header).
3. Test changes: `test_mg_logroll_fish.py` sq_frame should map the tile through the venue's legacy show table (build/venues.json `show_table`) instead
   of `// 8`; the bonus-round test should count the show's bank-1 sprites on Color.
