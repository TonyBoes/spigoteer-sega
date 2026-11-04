#!/usr/bin/env python3
"""Read-only: list the 8x8 cells of each picture that hold water keys (b, W), their unique tiles, and whether a water
tile's pattern is shared with a non-water cell (then it could not be animated without its own copy). Prints the key
grid of the water bounding box so the frames can be hand-drawn over it."""
import sys
sys.path.insert(0, __file__.rsplit('/', 1)[0])
from render_v2 import parse

WATER = set(sys.argv[2] if len(sys.argv) > 2 else "bW")
key, pix = parse(sys.argv[1])


def cell(cx, cy):
    rows = [pix[cy * 8 + y][cx * 8:cx * 8 + 8] for y in range(8)]
    return tuple(tuple(key[c][0] for c in r) for r in rows), rows


wcells, other = {}, {}
for cy in range(13):
    for cx in range(20):
        pat, rows = cell(cx, cy)
        if any(c in WATER for r in rows for c in r):
            wcells.setdefault(pat, []).append((cx, cy))
        else:
            other.setdefault(pat, []).append((cx, cy))
print(sys.argv[1], "water cells", sum(len(v) for v in wcells.values()), "unique", len(wcells))
for pat, cs in wcells.items():
    print("  ", cs, "shared with non-water" if pat in other else "")
xs = [x for y, r in enumerate(pix) for x, c in enumerate(r) if c in WATER]
ys = [y for y, r in enumerate(pix) for x, c in enumerate(r) if c in WATER]
if xs:
    x0, x1, y0, y1 = min(xs) // 8 * 8, max(xs) // 8 * 8 + 8, min(ys) // 8 * 8, max(ys) // 8 * 8 + 8
    print("bbox cells x", x0, x1, "y", y0, y1)
    for y in range(y0, y1):
        print("%3d " % y + "".join(pix[y][x0:x1]))
