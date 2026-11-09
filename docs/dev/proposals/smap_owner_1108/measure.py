"""python3 -I measure.py TAG [x0 y0 x1 y1]     (env OWNER=... as ctx.py reads it; no OWNER = the map as frozen in assets/smap)

The budgets of a variant map, measured by the build's own generator (tools/gen_smap_world.py's scratch copy smap_layout_a5/src/gen_smap_world.py, the one the commit numbers come from) on a
variant snapshot (variant_snapshot.py writes it: the same freezing as tools/dev/smap_snapshot.py, DMG trims and falls A cells included):
  DMG tiles (whole map), worst 21 x 19 view and worst padded 22 x 20 view (limit 176), Color tile ids after the flip merge (cap about 1019), BG palettes per 21 x 19 view (max 8) and per
  22 x 20 region, palette table entries.
With a cell box (the cells a proposal changes) it also reports the worst DMG view and the worst palette count among the windows that contain a changed cell.
Writes out/owner1108/numbers_TAG.json; prints one JSON line."""
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
OUT = ROOT / "out" / "owner1108"
tag = sys.argv[1]
box = tuple(int(v) for v in sys.argv[2:6]) if len(sys.argv) >= 6 else None
snap = OUT / f"snap_{tag}"
subprocess.run([sys.executable, "-I", str(HERE / "variant_snapshot.py"), tag], check=True, stdout=subprocess.DEVNULL)
shim = OUT / f"shim_{tag}"
shim.mkdir(exist_ok=True)
src = (ROOT / "tools" / "smap_world" / "world_snap.py").read_text()
key = 'ASSETS = Path(__file__).resolve().parent.parent.parent / "assets" / "smap"'
assert key in src
(shim / "world_snap.py").write_text(src.replace(key, f'ASSETS = Path({str(snap)!r})'))
sys.path.insert(0, str(shim))
sys.path.insert(0, str(ROOT / "docs" / "dev" / "proposals" / "smap_layout_a5" / "src"))
import numpy as np  # noqa: E402
import gen_smap_world as G  # noqa: E402

W = G.W
assert str(snap) in str(W.ASSETS), W.ASSETS
cw, ch = W.CW, W.CH
G.TILE_MAX = 1024
cg, dm = G.Model(True), G.Model(False)
n21, at21 = dm.window_max(21, 19)
n22, at22 = dm.window_max(22, 20)
STATES = (10, 11)                  # 10: the fountain broken (states 1..10 are one picture), 11: repaired
hist, over, best, at_p, best22 = {}, 0, 0, None, 0
used = set()
for st in STATES:
    pal_grid = cg.pals[st]
    used |= {W.PAL_NAMES[i] for i in np.unique(pal_grid)}
    for y0 in range(ch - 18):
        for x0 in range(cw - 20):
            n = len(np.unique(pal_grid[y0:y0 + 19, x0:x0 + 21]))
            if st == 11:
                hist[n] = hist.get(n, 0) + 1
                over += n > 8
            if n > best:
                best, at_p = n, (x0, y0)
    best22 = max(best22, max(len(np.unique(pal_grid[y0:y0 + 20, x0:x0 + 22])) for y0 in range(ch - 19) for x0 in range(cw - 21)))
used = sorted(used)
stops_, legs_, _, _ = G.geometry()
PW = G.path_windows(stops_, legs_)            # every camera window Sal can cause (feet at the centre, one cell of padding): 22 or 23 x 20 or 21 cells
pw_worst, pw_at, pw_pal = 0, None, 0
for st in STATES:
    for (c0, c1, r0, r1) in PW:
        n = len(np.unique(dm.grids[st][r0:r1 + 1, c0:c1 + 1]))
        if n > pw_worst:
            pw_worst, pw_at = n, (c0, c1, r0, r1)
        pw_pal = max(pw_pal, len(np.unique(cg.pals[st][r0:r1 + 1, c0:c1 + 1])))
res = {"tag": tag, "dmg_path_windows_worst": pw_worst, "path_at": pw_at, "color_path_palettes_worst_padded": pw_pal, "n_path_windows": len(PW), "dmg_tiles": dm.nt, "dmg_worst_21x19": n21, "at21": at21, "dmg_worst_22x20": n22, "at22": at22, "color_ids": cg.nt,
       "pal_worst_21x19": best, "pal_at": at_p, "pal_windows_over_8": over, "pal_worst_22x20": best22, "pal_hist": dict(sorted(hist.items())),
       "table_entries": len(W.PAL_NAMES), "table_used_in_state_10": len(used), "table": list(W.PAL_NAMES)}
if box:
    bx0, by0, bx1, by1 = box
    worst, wat, pworst, pat, worst22, wat22 = 0, None, 0, None, 0, None
    for st in STATES:
        for y0 in range(max(0, by0 - 18), min(ch - 19, by1) + 1):
            for x0 in range(max(0, bx0 - 20), min(cw - 21, bx1) + 1):
                n = len(np.unique(dm.grids[st][y0:y0 + 19, x0:x0 + 21]))
                if n > worst:
                    worst, wat = n, (x0, y0)
                p = len(np.unique(cg.pals[st][y0:y0 + 19, x0:x0 + 21]))
                if p > pworst:
                    pworst, pat = p, (x0, y0)
        for y0 in range(max(0, by0 - 19), min(ch - 20, by1) + 1):
            for x0 in range(max(0, bx0 - 21), min(cw - 22, bx1) + 1):
                n = len(np.unique(dm.grids[st][y0:y0 + 20, x0:x0 + 22]))
                if n > worst22:
                    worst22, wat22 = n, (x0, y0)
    pwb = 0
    pwb_at = None
    for st in STATES:
        for (c0, c1, r0, r1) in PW:
            if c1 >= bx0 and c0 <= bx1 and r1 >= by0 and r0 <= by1:
                n = len(np.unique(dm.grids[st][r0:r1 + 1, c0:c1 + 1]))
                if n > pwb:
                    pwb, pwb_at = n, (c0, c1, r0, r1)
    res.update({"box_dmg_path_window_worst": pwb, "box_path_at": pwb_at})
    res.update({"box": box, "box_dmg_worst_21x19": worst, "box_at": wat, "box_dmg_worst_22x20": worst22, "box_at22": wat22, "box_pal_worst": pworst, "box_pal_at": pat})
try:                                                  # the full generator: slot plans, budgets, reachability of every stop along the legs (it exits 1 on a failure)
    import contextlib
    import io
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        G.main(str(OUT / f"gen_{tag}" / "build"), str(OUT / f"gen_{tag}" / "preview"))
    res["generator_ok"] = True
    res["generator_last_line"] = buf.getvalue().strip().splitlines()[-1][:300] if buf.getvalue().strip() else ""
except (SystemExit, AssertionError) as e:
    res["generator_ok"] = False
    res["generator_error"] = repr(e) + " " + buf.getvalue()[-300:]
json.dump(res, open(OUT / f"numbers_{tag}.json", "w"), indent=1, default=str)
print(json.dumps({k: v for k, v in res.items() if k not in ("table", "pal_hist")}, default=str))
