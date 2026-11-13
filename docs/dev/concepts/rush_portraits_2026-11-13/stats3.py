"""Per boss: tile count for each vertical shift dy (0..8) of the whole boss in the 4 inside tile rows (32 px)."""
from pathlib import Path
import rp_common as c

build = Path(c.ROOT / "build")
for n in c.BOSSES:
    rows, pal = c.full_boss(build, n)
    x0, x1, y0, y1 = c.bbox(rows)
    dx = 24 - (x0 + x1 + 1) // 2
    out = []
    for dy in range(0, 9):
        grid = [[0] * 48 for _ in range(32)]
        for y, r in enumerate(rows):
            for x, v in enumerate(r):
                if v:
                    grid[y + dy][x + dx] = v
        uq = set()
        for ty in range(4):
            for tx in range(6):
                t = c.tile_of(grid, tx, ty)
                if any(any(r) for r in t):
                    uq.add(t)
        top, bot = y0 + dy, 32 - (y1 + dy + 1)
        out.append(f"dy{dy}:{len(uq)}({top}/{bot})")
    print(f"{n:11s}", " ".join(out))
