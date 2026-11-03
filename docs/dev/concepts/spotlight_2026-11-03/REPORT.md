# Show stage lighting (Color only) — investigation 2026-11-03

From the investigation agent's report (branch inv/show-spotlight); written into this file by the supervisor.

Stage = text rows 1-4 (y 8-39), BG 5/6 only. HUD y 0-7 (BG 1) and bar rows (y 40+) untouched. Performers OBJ y 8-31.
One palette (8 B) fits one HBlank at double speed. EV_MAX 8 LYC events. Dim colours must be derived from the
already-lifted (BRIGHT) colours, as split_vbl's SPLIT_STG is. DMG path unchanged in every option (is_cgb + show timer).

| Look | BG slots | New HBlank writes | ROM0 (est.) | WRAM | Tiles |
|---|---|---|---|---|---|
| A Dim (+16-frame fade) | 0 | 0 | ~10-20 B | 0-1 B in a union | 0 |
| B Wash (dim + tint per beat) | 0 | 0 | ~10 B more | 0 | 0 |
| C Pools (lit tile columns) | 2 borrowed (BG 3/4) | +2 restores (lines 37/38) | ~30-60 B | 16 B buffers + ~4 B (no hole found) | 0 |
| D Sweep (pools move with beat) | as C | as C | C + ~10 B | as C | 0 |
| E Cones (beams) | 3 borrowed | +3; EV_MAX > 8 | ~60-90 B (over the ROM0 margin) | ~28 B | 3-4 BG |

Dim = colours x (0.40, 0.45, 0.62). Performers left as they are.
Recommendation: A then B; C/D later if real spotlights are wanted; skip E.
Unsure: ROM0 numbers are estimates (margin 6 B); HBlank room at 37/38 from source comments, not SameBoy; no story_scratch hole for C's buffers.
Mockups: <venue>_<look>.gif/png, sheet_all.png, sheet_stage_x4.png (scripts capture.py, mock.py, run.py).
