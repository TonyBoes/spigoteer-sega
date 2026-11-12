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

# Round 6 (owner Q17, 2026-11-11): the DMG's route plan, built
The design note above, as built (DMG first; Color below when done).
- The slot of every CELL is planned at build time (tools/smap_world/route.py, called by tools/gen_smap_world.py): the windows the region can hold while Sal walks (every pixel of every leg
  both ways, the stops, the glides between a resting view and Sal; each padded by one line) give a conflict graph over live ranges (a tile's cells that share a window share a node, an animated tile is
  one node), DSATUR with a tabu search in 176 colours. `check_plan` is the build's proof: every window holds one tile a slot, and a replay of every walk (lines leave, lines enter and load their tiles
  into their slots) finds every cell of every window resident. The build fails if either fails. 175 colours, the fullest window 173 of 176.
- A line is a list of {tile, slot} from `smap_d_fetch` (the finished story's world; `smap_d_fix` patches the 12 fountain cells of states 1..10). The engine loads the tile when the slot holds
  another one. Gone: the hint, home2, smap_freeslot, V_RR, V_NDISP, V_CS, the far-tile scan, tbl_find, the use counts (A_CNT), smap_dadd, the drop job (a DMG line that leaves costs nothing: region_work just
  moves the extents; an add job that spans a line that left starts over). The slot table is 176 u16 (A_TBL, 352 bytes).
- Asm: `smap_burst` (cells whose slot already holds their tile; C twin add_cell_d), `smap_d_fetch`. job_run is two functions (job_run_c the Color's, job_run_d the DMG's) so a change to one does not move a cycle of the other.
- Not built (said): the spare-slot preload of the next lines (the dense stretches have 3 spare slots, not 20-30: the fullest padded window is 173 of 176), and plans for the camera jumps (they need none: the
  map entry, the resting views and the glides are windows of the plan).
- Tools: tools/dev/smap_walk_numbers.py (px/frame, holds, late, p90, worst over every leg both ways, GB_ROM / GB_NOI for main's ROM), tools/dev/smap_cmp_main.py (every frame against main's ROM).

# Round 7 (owner 11-11): the DMG walk stutter, lookahead and an even pace
Cause, verified: the region led the view by ONE line, so on every stretch the next line (19-22 cells, each a fetch and a map write) was never loaded in time at 2 px a frame; walk_step then paced 1 px and paused 1 frame in 2/3/4 (cycle 2,2,2,1,1,0 a cell line, quiet or busy). On the dense stretches a second limit: the DMG stages 2 tiles a frame, and a line of new tiles needs about 18.
- Lookahead: tools/smap_world/route.py choose_leads gives each stretch (both ways) up to 6 lines ahead, as many as its windows' tiles leave slots for (budget falls 175 -> 157 until the colouring holds); windows, plan and proof use them (walk_sequences leads=); smapw_leg_lead[leg][stretch] (low nibble forward, high backwards). Dense stretches (saloon, space lounge roads) keep 1-2.
- Engine (DMG only): V_LEADX/V_LEADY (the old V_RR / V_NDISP slots) = lines beyond the first; stretch_init sets them, walk_dirs shrinks the stretch's own to the lines its last px can show and takes the next stretch's in the corner zone, walk_ready and the walk's end clear them. region_work_d is the DMG's own region_work (the Color's region_work, tile_load and ly_ok are untouched: the Color's frames are cycle for cycle main's; ANY cycle added to them flipped Color goldens: the tag timing sits on a frame edge); smap_region_work dispatches.
- Pace: walk_step DMG branch: the sustainable pace is w / (rem + sl): 2 px, or 2 in 3, 2 or 1 of 4 frames, else 1; never a 0 (the old pauses are gone). Dense stretches run 1,1,2,2 cadences.
- Loader: NSTG_MAX_D 3 (the third staging tile after the slot table: 352..367, WRAM free on the DMG), ADD_CAP 8, CROSS_CAP 6 on a cross frame, LY_WORK 44, LY_URGENT 28 while the room is under 8 px (V_CS), ly_ok_d. F_CROSS fixed for DMG walks to the left / up (it only flagged right / down: the heavy "sprites all redrawn" frame came unannounced). A dropped frame (logic past the VBlank) shows as a 0 px SAMPLE though the hook log has no record of it: measure with tools/dev/smap_pace_table.py (samples every emulated frame).
- Numbers (all legs both ways, DMG): frames 3475 -> 3030, px/frame 1.445 -> 1.657, 0 px frames mid-stretch 369 -> 0, late 0 -> 0, logic p90 106 -> 107, worst 133 -> 129. Color identical.
