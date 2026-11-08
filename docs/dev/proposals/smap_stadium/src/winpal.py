"""palettes per 21 x 19 window and unique DMG tiles (whole map, worst 21x19 window, stadium window) of the A5 map with a stadium variant pasted."""
from collections import Counter

import numpy as np

import mapctx as M
from mapctx import W


def palettes(world=None):
    w = world or W.WORLD
    worst = []
    for y0 in range(M.CH - 18):
        for x0 in range(M.CW - 20):
            c = Counter(w.pal[y][x] for y in range(y0, y0 + 19) for x in range(x0, x0 + 21))
            worst.append((len(c), x0, y0, c))
    worst.sort(key=lambda r: -r[0])
    return worst


def tiles(world=None):
    w = world or W.WORLD_DMG
    ids = {}
    g = np.zeros((M.CH, M.CW), int)
    for cy in range(M.CH):
        for cx in range(M.CW):
            t = bytes(w.px[cy * 8 + j][cx * 8 + i] for j in range(8) for i in range(8))
            g[cy, cx] = ids.setdefault(t, len(ids))
    best = (0, None)
    for y0 in range(M.CH - 18):
        for x0 in range(M.CW - 20):
            n = len(np.unique(g[y0:y0 + 19, x0:x0 + 21]))
            if n > best[0]:
                best = (n, (x0, y0))
    sx = len(np.unique(g[0:12, 0:21]))             # the stadium window: cells 0..20 x 0..11 (top left corner of the map, the stadium and the road below it)
    return len(ids), best, sx


if __name__ == "__main__":
    import sys
    import after  # noqa: F401  (the stadium after my edits)
    pw = palettes()
    print("max palettes per 21x19 window:", pw[0][0], "windows over 8:", sum(1 for r in pw if r[0] > 8))
    for n, x0, y0, c in pw[:3]:
        print(n, (x0, y0), dict(c))
    print("tiles (whole map, worst 21x19 at, stadium window 21x12):", tiles())
