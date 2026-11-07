import after  # noqa: F401
from mapctx import W

w = W.WORLD
for name in ("igloo", "saloon", "town1@g", "stadium", "park", "town1", "bistro@g"):
    cells = [(x, y) for y in range(3, 22) for x in range(11, 32) if w.pal[y][x] == name]
    xs = [c[0] for c in cells]
    ys = [c[1] for c in cells]
    print(name, len(cells), (min(xs), min(ys), max(xs), max(ys)) if cells else None, cells[:16])
