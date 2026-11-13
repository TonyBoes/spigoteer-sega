"""Unique-tile counts for the layout 'A': the whole boss (topper row + body's two rows) on 3 tile rows, columns shifted as the list does now."""
from pathlib import Path
import rp_common as c

build = Path(c.ROOT / "build")
tot = 0
every = set()
for n in c.BOSSES:
    rows, pal = c.full_boss(build, n)
    x0, x1, y0, y1 = c.bbox(rows)
    dx = 24 - (x0 + x1 + 1) // 2
    grid = [[0] * 48 for _ in range(24)]
    for y, r in enumerate(rows):
        for x, v in enumerate(r):
            if v:
                grid[y][x + dx] = v
    uq = set()
    nb = 0
    for ty in range(3):
        for tx in range(6):
            t = c.tile_of(grid, tx, ty)
            if any(any(r) for r in t):
                uq.add(t)
                nb += 1
    tot += len(uq)
    every |= uq
    print(f"{n:11s} dx {dx:2d} non-blank {nb:2d} unique {len(uq):2d}")
print("sum", tot, "unique over all", len(every))
