"""python3 numbers.py before|after: DMG unique tiles (whole map; worst 21x19 window anywhere; worst 21x19 window that shows the stadium (x0 0 to 12, y0 0 to 3)), palettes per 21x19 window (max, windows over 8),
and the Color palettes of the stadium window."""
import sys
from collections import Counter

import numpy as np

mode = sys.argv[1]
if mode == "after":
    import after  # noqa: F401
    import mapctx as M
else:
    import mapctx as M
    M.apply()
from mapctx import W

w = W.WORLD_DMG
ids = {}
g = np.zeros((M.CH, M.CW), int)
for cy in range(M.CH):
    for cx in range(M.CW):
        g[cy, cx] = ids.setdefault(bytes(w.px[cy * 8 + j][cx * 8 + i] for j in range(8) for i in range(8)), len(ids))
worst, wat, sw, swat = 0, None, 0, None
for y0 in range(M.CH - 18):
    for x0 in range(M.CW - 20):
        n = len(np.unique(g[y0:y0 + 19, x0:x0 + 21]))
        if n > worst:
            worst, wat = n, (x0, y0)
        if x0 <= 12 and y0 <= 3 and n > sw:
            sw, swat = n, (x0, y0)
pw = []
for y0 in range(M.CH - 18):
    for x0 in range(M.CW - 20):
        c = Counter(W.WORLD.pal[y][x] for y in range(y0, y0 + 19) for x in range(x0, x0 + 21))
        pw.append((len(c), x0, y0))
sp = max((p for p in pw if p[1] <= 12 and p[2] <= 3))
print(mode, "tiles whole", len(ids), "worst 21x19", worst, wat, "stadium windows worst", sw, swat)
print(mode, "palettes per window max", max(pw)[0], "windows over 8:", sum(1 for p in pw if p[0] > 8), "max in stadium windows", max(p[0] for p in pw if p[1] <= 12 and p[2] <= 3))
