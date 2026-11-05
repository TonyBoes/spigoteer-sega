# Story map: faster, smoother walk (handoff, 2026-11-05)

Goal, from the owner: "Map movement should be faster and less jerky"; then "I'm not noticing much of a change in Sal's walk speed ... still noticing the [stuttering]".
- Color: 2 px/frame on every stretch, with 0 holds and 0 late frames, at double speed.
- DMG: smooth first, at the fastest stutter-free pace. Also report option (b): how many unique DMG tiles would have to go, and where, to hold 2 px everywhere. No art change without the owner's pick.

## Built (WIP commit, not green, not merged)
- **src/render.c `vq_exec` (ROM0):**
  - A queue entry with bank bit 1 set and a destination below 0x98 is one 16-byte Color GDMA block in VBlank, staged 16-byte aligned in story_scratch: A_XSTG, 96 B, up to 5 tiles a frame. A tile's drain cost fell from 19-21 to 9-11.
  - Bank bit 1 with a destination of 0x98 or above is stride mode: a column's ids and attributes go out as one run, 32 bytes apart.
- **src/smap_eng.c:**
  - `flush_line` matches stride mode. A column cell costs like a row cell (Color 2, DMG 1).
  - `smap_region_work` now runs before `smap_camera_step`.
  - `room()` reserves 5 units for the scroll entry; a ring-wrapping line reserves its run overhead twice.
  - Color jobs take up to 22 cells a frame.
  - The ASM_SMAP burst branch in `job_run` was edited to drop the column-cost special cases. The C twin is unchecked since.
- **LY gates:** LY_WORK/LY_FIRST 62 on DMG, LY_WORK_C/LY_FIRST_C 100 on Color. These are guesses, not fitted.
- **tools/smap_gear.json:** all 2 for both models. This is not shippable for DMG.

## Numbers (per game frame, all 22 legs)
- **Color, all 2 px:**
  - 2138 frames, 14 holds, 10 late at LY_WORK_C 120.
  - 18 holds and 4 late at 100.
  - About 372 holds before this round.
- **DMG, old mixed table:** 14 holds / 110 late at LY 80; 22 / 64 at LY 70. Stride mode cut late frames from 54 to 1 at the earlier gear.
- **DMG, all 2 px at LY 62:** 2664 frames, 512 holds, 87 late. DMG cannot hold 2 px everywhere.
- **Raw DMG tile loads per 8 px per leg:** 1.5 to 5.6, from out/mv/tiles.py on the pre-stride build.

## Tools
- `python3 tools/dev/smap_gear.py --rounds 8`: the per-model pace fit. About 5 minutes a round per model. Don't run it alongside a build.
- Scratch tools, in the previous worktree's out/mv/:
  - holds.py: every hold frame with job state;
  - frames.py: per-frame cost, tiles and job progress;
  - late.py: per-frame function timing;
  - tiles.py: tile loads per column.

## Open
1. **ROM0** is 402 B free against the 443 rule (`vq_exec` +41). Win the 41 B back: move something cold out of ROM0, shrink `vq_exec`, or put the GDMA path in a banked helper called from a tiny stub. Never below 443.
2. **C twins:** `make cfall` and the C-twin tests after the burst edit.
3. **Per-model gear fit** to 0 holds and 0 late. The leftover Color holds are in tile-heavy columns.
4. **DMG report and options:** (a) the fastest stutter-free pace, built; (b) the art trim needed for 2 px, with numbers.
5. **PERF dict** (tests/test_story_map_world.py): the last measured worst frames were DMG 155 against 139 and Color 109 against 84. Never raise it; get under it or report.
6. **Report:** average px/frame per leg, old against new, on both models.
7. **Goldens:** story_map_scroll_walking dmg/cgb will change. List them with their bbox.
8. **Tearing check** of stride mode, SameBoy if possible.

## Round 3 (adaptive pace, no gear table) - state at commit "WIP (not green): story map walk tests ..."

What changed: the fitted gear table is gone (`tools/dev/smap_gear.py` and `tools/smap_gear.json` are obsolete, unused). `walk_step` in
`src/smap.c` picks the pace each frame (2, 1, 1/2, 1/4, 1/8 px) from `smap_room()` (px Sal may still walk before the camera shows an
unloaded cell) against the cells the loading line still needs at the rate it has been loading (`V_RATE`, a byte of the map's own
scratch: V_SEL while walking). `ly_ok()` gates every cell on the frame's LY. A UFO bob moves OAM y directly (`ufo_bob`).

Measured (out/mv/measure.py, per game frame): DMG 3471 frames, 1.098 px/frame (old 0.981), 0 holds (old 52), 5 late frames;
Color at double speed 2116 frames, 1.777 px/frame (old 0.994), 5 holds, 1 late frame. Slowest stretches: DMG dense zones (the
engine's per-cell C cost and the 2 tiles/frame staging), Color stops 6 up and 7 up.

Open (the reasons this is not green):
1. PERF guard: DMG worst frame 154 (guard 139), Color 143 (guard 84). The adaptive pace spends the frame up to its late line.
2. vq_exec's GDMA/stride branch: +4 cycles per entry and -43 B ROM0 (400 free, floor 421). Tests that depend on the title timing
   (test_qd winner sprays, test_rush boss win, test_story_difficulty prompt, test_rng stadium picks, test_mg_logroll, lr_fall.cgb)
   move with ANY change there (a 4-nop experiment on main's vq_exec breaks the same five). hi_pick with split6 frees 292 B but
   moves 15 other goldens, so it was reverted.
3. Golden story_map_scroll_walking (dmg, cgb): the picture at Sal x >= 120 is a few px further on.
