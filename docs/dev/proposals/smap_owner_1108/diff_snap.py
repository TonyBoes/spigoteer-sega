"""python3 -I diff_snap.py TAG_A TAG_B  : cells that differ between two variant snapshots (out/owner1108/snap_*), per data set, as a list of cell boxes (read-only)."""
import sys
from pathlib import Path

from PIL import Image

OUT = Path(__file__).resolve().parents[4] / "out" / "owner1108"
a, b = sys.argv[1], sys.argv[2]
for f in ("world_c.png", "world_d.png"):
    ia = Image.open(OUT / f"snap_{a}" / f).convert("L")
    ib = Image.open(OUT / f"snap_{b}" / f).convert("L")
    da, db = ia.load(), ib.load()
    cells = set()
    for y in range(ia.height):
        for x in range(ia.width):
            if da[x, y] != db[x, y]:
                cells.add((x // 8, y // 8))
    xs = sorted({c[0] for c in cells})
    ys = sorted({c[1] for c in cells})
    print(f, len(cells), "cells differ; x", xs[:1], xs[-1:], "y", ys[:1], ys[-1:])
    # clusters by column band
    cols = {}
    for (x, y) in sorted(cells):
        cols.setdefault(x // 8, []).append((x, y))
    for k, v in cols.items():
        print("  x band", k * 8, "..", k * 8 + 7, ":", len(v), "cells, y", min(c[1] for c in v), "..", max(c[1] for c in v))
