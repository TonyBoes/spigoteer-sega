"""Constraint numbers: how tall each boss is, what the list's portrait loses, unique-tile counts for the layouts. Run from the worktree root."""
from pathlib import Path
import rp_common as c

build = Path(c.ROOT / "build")
tot = {}
print("boss        w  drawn rows(full)  bbox(full)       topper rows above body  lost-top  lost-bottom  body row15 px")
allw = {}
for n in c.BOSSES:
    rows, pal = c.full_boss(build, n)
    x0, x1, y0, y1 = c.bbox(rows)
    h = y1 - y0 + 1
    # the list shows body rows 8..23 only (what gen_rush_portraits.py packs)
    lost_top = max(0, 8 - y0)
    # bottom: the body's last row is the counter's edge; rows of the full boss under the window = 0, report body row 15 drawn pixels
    r15 = sum(1 for v in rows[23] if v)
    print(f"{n:12s}{len(rows[0]):3d}  {h:3d} ({y0}..{y1})   x {x0}-{x1}    {lost_top}   {r15}")
    # layouts: A: the whole boss, whole pixels, centred vertically in the 32 px window by its drawn rows, horizontally by the drawn box
    dx = 24 - (x0 + x1 + 1) // 2
    dy = 16 - (y0 + y1 + 1) // 2                     # centre on 32 rows (the 4 inside tile rows)
    grid = [[0] * 48 for _ in range(32)]
    for y, r in enumerate(rows):
        for x, v in enumerate(r):
            if v:
                grid[y + dy][x + dx] = v
    uniq, nb = set(), 0
    for ty in range(4):
        for tx in range(6):
            t = c.tile_of(grid, tx, ty)
            if any(any(r) for r in t):
                uniq.add(t)
                nb += 1
    print(f"             centred 32 rows: dy {dy} dx {dx}; non-blank tiles {nb}, unique {len(uniq)}")
    allw[n] = uniq
every = set().union(*allw.values())
print("unique tiles over all ten (A, centred in 4 rows):", len(every), "+ blank")
