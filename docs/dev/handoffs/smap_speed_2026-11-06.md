# Map walk, round 4 (owner Q87 yes, 2026-11-06)

State: green on DMG and Color except the two story_map_scroll_walking goldens (Sal's first frame at x >= 120 is one step further on).

- vq_exec / vq_vbl are main's again. The map's special runs (stride columns, Color GDMA tiles) are `qsp` entries (smap_priv.h): the drain sees a
  1-byte copy to 0xFF7F, the real destination and length ride in pad[]. `smap_vbl` (render.c, an 8-byte ROM0 stub) runs `smap_isr` (smap_eng.c, banked,
  asm behind ASM_SMAP, C twin `sp_run`) after vq_vbl; smap_enter registers it, smap_isr takes it out when the map is left. No other screen pays a cycle.
- ROM0 real free 477 B (main 443): update_glass moved into main_cold.c (its only caller).
- PERF of the map walk only: DMG worst 160 (measured 158), Color 145 (143). Late frames remain: DMG 8 of 3896, Color 3 of 2143 (frame logic + music tick ends after line 154).
  The DMG's heavy frames are one C cell with a tile load (add_cell up to 50 lines: smap_d_tile 30, the free-slot search 13) behind LY_WORK 50, and smap_d_fetch (about 20 lines a chunk).
  Next steps: smap_d_tile and the free-slot search are the DMG's pace; an asm slot search and a cheaper tile decode would lift the DMG pace and remove the late frames.
- Trial: an unrolled stride copy (8 cycles a cell) gained nothing (committed and reverted). A pop-based copy has no home: the drain is main's, the stride runs are not contiguous.

# Round 5 (owner Q89 yes, 2026-11-06): DMG asm for the per-cell work

Measured with a hook profile (LY at global symbols; statics made global in a scratch build), the round 4 numbers were stale: smap_d_tile is 1.1 lines and smap_d_fetch
4.65 lines a call (about 8 cells); the real cost of a cell that loads a tile was the C around them (tbl_find, the cost checks, the slot choice, tbl_get/set, tile_load, qraw:
about 33 lines), and, when V_NDISP > 0, a full 176-slot scan (smap_scan, about 30 lines) for every tile that is not resident.
- `smap_freeslot` (asm, twin: the loop in add_cell): first free slot after V_RR, 4 slots a step. Rarely reached (the hint and its second home usually take the tile).
- `smap_dadd` (asm, twin: add_cell's DMG branch, which also takes every case dadd answers 3 to): the whole load cell: hint / home2 check, the V_NDISP scan, cost checks, slot,
  far count, table, tile staged by `smap_d_tcopy` and the old tile's hint read by `smap_d_hintx` (generated, banked, called through ___sdcc_bcall_ehl, no stack arguments), queue entry, count.
  `add_cell_d` wraps it for the DMG so that the Color's add_cell is untouched (an extra local in add_cell cost the Color 3 lines of worst frame).
- ADD_CAP 6 -> 8 (DMG cells a frame). 9 gives 22 late frames, 10 gives 40.
- Tried and dropped: LY_SLOWC (a lower limit for slow cells) 4 / 12: pace 0.94 / 0.86, holds 13 / 45.
Result, all legs both ways (test_story_map_world.walk_frames): DMG 0.975 -> 1.083 px/frame (frames 3918 -> 3518), holds 3 -> 2, late 8 -> 3;
Color 1.740 -> 1.742, holds 5, late 3 -> 2. Map perf guard (DMG 160, Color 145) passes unchanged. ROM0 free 477 B, no new WRAM. Golden story_map_scroll_walking.dmg changes (pace): bbox 0,0,159,143.
Left in the frame (average lines a frame, DMG): walk_step 10 (16-bit C, banked smap_room), fetch to burst 3.7 of C glue in job_run (room() twice ...), flush_line 7 a call,
tile_load tail. Trimming walk_step and flush_line would let ADD_CAP go to 9-10.

## Design note: a route plan (owner 11-06, not built)
The map is not free roam: every walk follows a leg with fixed stretches (waypoint to waypoint) in a fixed direction, so the region work along it is known at build time.
- Replaces: the runtime slot choice (hint, home2, smap_freeslot, V_RR), the V_NDISP bookkeeping and the far-tile scan (the 30-line scan for each tile that is not resident), tbl_find,
  and most of smap_dadd's logic. The runtime would only follow a list.
- Data (ROM, banked with the world data, per stretch and direction; the stretch table smapw_leg_pt already exists): for each new line the camera will want, the tiles to load as
  (tile id, slot) pairs in the order they come in, and the slots whose tiles leave (so the count update needs no lookup). About 2-3 bytes a load; roughly 2 loads a line over the
  route, a few KB in all. The generator can pick slots that stay free for the whole stretch, which the hint colouring (windows only, no order) cannot.
- Spare slots and time: the pool is 176 slots; the 22 x 20 window needs up to about 150 on the dense stretches (saloon, space lounge, zoo, town: where the late frames and the full
  scans are), so 20-30 slots are spare there. The plan keeps the next lines' tiles in those and loads them in frames that end early (a load is 0.5 a frame on average, NSTG_MAX 2 at most),
  so the camera step finds everything resident.
- Expected DMG gain: a load cell becomes about 5 lines (copy + queue), no scans; the worst frames (now up to 168) lose the 30-line scan and dadd's 8-13 lines, loads move to spare frames,
  so ADD_CAP 9-10 and 2 px steps could hold on the dense stretches. I expect 1.3 px/frame or more on the DMG (with walk_step and flush_line trimmed) and no late frames.
