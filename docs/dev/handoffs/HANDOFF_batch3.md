# Handoff: patron revision batch 3 (patron tile lookup table, Q61 B)

STATUS: measured, NOT built. Stopped before the engine change on purpose (WRAM, perf and benefit: see below). Needs a supervisor decision.

## Measurement (tools/dev/patron_dups.py, from the art itself; tile_dups.py needs the atlas and counts whole VRAM)
Tiles a group's 150 stored patron tiles (126 shifted + 12 shift-0 + 12 back) could share, the blank pair at PATRON_BLANK already existing:

| venue | blanks | copies | tiles shareable | only whole 8x16 columns |
|---|---|---|---|---|
| cowboys (Saloon) | 6 | 0 | 6 | 0 |
| sports | 10 | 1 | 11 | 4 |
| lumberjacks | 18 | 0 | 18 | 6 |
| chefs | 11 | 7 | 18 | 8 |
| divers | 3 | 33 | 36 | 26 |
| robots | 12 | 4 | 16 | 4 |
| punks | 9 | 4 | 13 | 2 |
| ninjas | 5 | 1 | 6 | 2 |
| zoo | 2 | 0 | 2 | 0 |
| aliens | 7 | 0 | 7 | 0 |
| Saloon bank 1 (5 looks, 250 tiles) | 9 | 8 | 17 | 6 |

Layout-only sharing (poses overlapping at arbitrary st_tab offsets, no runtime cost): 0-4 tiles per venue. Useless.

## Why it was not built
- A real lookup needs a 6-id pose table per look and shift (21 shifted poses + 3 shift-0 = 138-144 B per group) that is group-specific, so it
  cannot live in ROM0 (ROM0: 453 B free asm, 70 B C) and needs WRAM at level load. No new WRAM globals allowed; story_scratch during a fight has only
  0..69, 218..229 and 234..299 free (scratch.h), in pieces, 136 B in total: not enough for 138-144 B in one run, and the DMG mixed levels
  keep two tile sets (st_tab dir bit), which doubles it. Net of the freed st_tab (64 B) and ROM0 id_seq (144 B, would move to the table), it is
  close but fragmentary.
- Consumers of the fixed layout to change: render.c stamp/stamp3/put_col, seq_ofs/id_seq/quick_entries, mirror.c quick_mirror, lift.c lift_tile,
  dgag.c, po.c load_crowd, boss.h BOSS_BG_A/B (contiguous regions), credits, gen_art.py, the C twins, tests that read tile ids. Large, with the perf
  guards on the C ROM already at their limit (see HANDOFF_batch2_steps.md).
- Benefit: 2-36 tiles per venue in bank 0, scattered until compacted; the next step (Color-only 4th looks, about 50 tiles each) uses bank 1, which is
  empty in every venue but the Saloon (252 of 256 used there by the 5 extra looks; 17 would come back). The 4th looks do not need the table.

## Options for the supervisor
(a) Drop Q61 B: the next step goes into bank 1 as is (50 tiles per extra look, bank 1 free in 9 venues).
(b) Blank-only: a per-pose 6-bit blank mask (24 B per group, in ROM0 for the current group copied at level load, or in story_scratch 0..69) and
    packed poses; saves 2-18 tiles per venue (divers 3), costs a stamp loop and a slower quick path (blank poses go through quick_mirror).
(c) Full table in WRAM: needs the supervisor to name 144 contiguous WRAM bytes (or free st_tab plus a story_scratch run).

## Numbers (nothing changed in the game)
ROM0 free 453 B (asm), _DATA 7547 B (WRAM), ROM 512 KB, banks 1-8 have 17-83 B free. No source changes: tools/dev/patron_dups.py and this file only.
