"""python3 render_one.py KEY OUTDIR   (KEY: now | A | B)   Renders one variant of the integrated map from mapctx (the map is built with SMAP_BIG=B, and SMAP_FALLS=A|B for the new options;
`now` is stage 1k's cave) and writes, at x1 (the sheet builder scales them):
    OUTDIR/KEY_wide_c.png, KEY_wide_d.png      cells 24..63 x rows 0..12 (the wide window, Color and DMG light water)
    OUTDIR/KEY_close_c_<t>.png, _d_<t>.png     the close-up (cells 43..49 x rows 1..8) at video frames t in STRIP_T and in every 3rd frame of the 180-frame loop (GIF source)
Frame model (the approved falls: smap_anim/items.py): streak step every 9 frames (k = (t // 9) % 4), the foam lip 6 frames after it, the pool glints on their 30-frame pace; the new cascade
cells step at t = 4 mod 9 (falls_v2.PHASE).  Only reads; nothing under assets/ or tests/ is written."""
import os
import sys
from pathlib import Path

key, out = sys.argv[1], Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)
HERE = Path(__file__).resolve().parent
IMP = HERE.parent / "smap_import"
os.environ["SMAP_BIG"] = "B"
if key in ("A", "B"):
    os.environ["SMAP_FALLS"] = key
sys.path.insert(0, str(IMP))
sys.path.append(str(IMP.parent / "smap_anim"))
sys.path.insert(0, str(HERE))
import mapctx as M  # noqa: E402
import falls_cave as FC  # noqa: E402

I = FC._items
WORLDS = (M.W.WORLD, M.W.WORLD_DMG)
WIDE = (24, 0, 64, 13)
CLOSE = (43, 1, 50, 9)
STRIP_T = [9 * k + 6 for k in range(4)]
if key in ("A", "B"):
    import falls_v2 as F2


def put(cx, cy, tile):
    for w in WORLDS:
        for j, r in enumerate(tile):
            for i, c in enumerate(r):
                v = {".": 0, "-": 1, "+": 2}.get(c, None)
                v = int(c) if v is None else v
                w.px[cy * 8 + j][cx * 8 + i] = FC.to_dmg(v, cx, cy, i) if w is WORLDS[1] else v


def lower(t):
    """the approved cells of rows 6..8 (and row 5 for the new options) at video frame t"""
    k = (t // 9) % 4
    for side, cx in (("L", 46), ("R", 47)):
        if key != "now":
            put(cx, 5, FC.fall_rows(side, k)[:8])
        put(cx, 6, FC.fall_rows(side, k)[8:])
        g = (I.GSEQ_L if side == "L" else I.GSEQ_R)[((t + I.FOOT_PH[0 if side == "L" else 1]) // 30) % 6]
        put(cx, 7, I.foot_tile(side, ((t - I.LIP_PH) // 9) % 4, g))
    w = I.WS["vsubtle"]
    put(46, 8, w["A"][[0, 0, 1, 0, 0, 2][(t // 30) % 6]])
    put(47, 8, w["B"][[0, 0, 2, 0, 0, 1][((t + 15) // 30) % 6]])


def state(t):
    lower(t)
    k = (t // 9) % 4
    if key == "now":
        for w in WORLDS:
            for (x, y), v in FC.cell_pixels(k).items():
                if FC.FLOW_X0 <= x < FC.FLOW_X0 + 8 and FC.FLOW_Y0 <= y < FC.FLOW_Y0 + 4:
                    w.px[y][x] = v
    else:
        kc = ((t - F2.PHASE) // 9) % 4
        for (x, y), v in F2.water_px(key, kc).items():
            for w in WORLDS:
                w.px[y][x] = v


# wide window at frame 6 (x4 is done by the sheet builder; here x1 so every sheet scales the same way)
state(6)
M.render(True, WIDE, 1).convert("RGB").save(out / f"{key}_wide_c.png")
M.render(False, WIDE, 1).convert("RGB").save(out / f"{key}_wide_d.png")
ts = sorted(set(STRIP_T) | set(range(0, 180, 3)))
for t in ts:
    state(t)
    M.render(True, CLOSE, 1).convert("RGB").save(out / f"{key}_close_c_{t:03d}.png")
    M.render(False, CLOSE, 1).convert("RGB").save(out / f"{key}_close_d_{t:03d}.png")
print(key, "frames", len(ts))
