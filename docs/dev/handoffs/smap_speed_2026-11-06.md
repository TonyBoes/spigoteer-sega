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
