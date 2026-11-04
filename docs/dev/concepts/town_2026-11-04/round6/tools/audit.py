#!/usr/bin/env python3
"""Read-only consistency audit: for each master piece (building, prop, texture cell), how many of its pixels in each
picture differ from the master (same keys = the same building; the key tables only change the lighting), and which
picture keys cover the differing pixels (so a difference can be traced to a story prop standing in front).
    audit.py PICDIR"""
import sys
from collections import Counter
from pathlib import Path

T = Path(__file__).resolve().parent
sys.path.insert(0, str(T))
from render_v2 import parse   # noqa: E402
import master as M            # noqa: E402

NAMES = ["intro_before", "intro_a", "finale_a", "credits_b"]
m = M.master()
pics = {n: parse(Path(sys.argv[1]) / f"{n}.txt")[1] for n in NAMES}
rows = []
for name, x0, y0 in M.PLACE:
    piece = M.PIECES[name].split("\n")
    cells = [(x0 + dx, y0 + dy) for dy, r in enumerate(piece) for dx, c in enumerate(r)
             if c != "." and 0 <= x0 + dx < 160 and 0 <= y0 + dy < 104]
    rows.append((f"{name} at ({x0},{y0})", cells))
for (tx, ty), v in M.TEX_CELLS.items():
    rows.append((f"texture {v} cell ({tx},{ty})", [(tx * 8 + dx, ty * 8 + dy) for dy in range(8) for dx in range(8)
                                                    if M.TEX[v][dy][dx] == "X"]))
rows.append(("plaza cobble y 88-103", [(x, y) for y in range(88, 104) for x in range(160)]))
for label, cells in rows:
    out = []
    for n in NAMES:
        p = pics[n]
        diff = [(x, y) for (x, y) in cells if p[y][x] != m[y][x]]
        cov = Counter(p[y][x] for (x, y) in diff)
        out.append(f"{len(diff)}" + (" " + "".join(sorted(cov)) if diff else ""))
    print(f"{label:34s} | " + " | ".join(out))
