#!/usr/bin/env python3
"""List each distinct cell colour map of a picture with its cells (read-only).   cellmaps.py PIC.txt"""
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from render_v2 import parse   # noqa: E402

key, pix = parse(sys.argv[1])
d = defaultdict(list)
for ty in range(13):
    for tx in range(20):
        m, ks = {}, set()
        for y in range(ty * 8, ty * 8 + 8):
            for x in range(tx * 8, tx * 8 + 8):
                s, hx = key[pix[y][x]]
                m.setdefault(s, set()).add(hx)
                ks.add(pix[y][x])
        d[tuple(sorted((s, tuple(sorted(v))) for s, v in m.items()))].append((tx, ty, "".join(sorted(ks))))
for m, cells in sorted(d.items(), key=lambda kv: -len(kv[1])):
    print(len(cells), m)
    print("     ", " ".join(f"{x},{y}:{k}" for x, y, k in cells[:14]))
