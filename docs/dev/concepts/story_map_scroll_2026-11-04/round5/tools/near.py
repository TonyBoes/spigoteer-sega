"""Round 5 working list: in one 21 x 19 window of the DMG world, pairs of different tiles that differ in at most N pixels, with where they are
(venue, venue-local pixel of the cell's top left) and the differing pixels (x, y inside the cell: shade in the first | shade in the second).
This only lists candidates; every edit is typed by hand in the venue's source.   python3 near.py X0 Y0 [N]"""
import sys
from collections import defaultdict

import stats2 as S
import world2 as W

x0, y0 = int(sys.argv[1]), int(sys.argv[2])
N = int(sys.argv[3]) if len(sys.argv) > 3 else 3
w = W.WORLD_DMG
sg = S.sig_grid(w)
where = defaultdict(list)
for cy in range(y0, y0 + 19):
    for cx in range(x0, x0 + 21):
        where[sg[cy][cx]].append((cx, cy))
tiles = list(where)
print(len(tiles), "distinct tiles in the window")
out = []
for i, a in enumerate(tiles):
    for b in tiles[i + 1:]:
        d = [(x, y, a[y][x], b[y][x]) for y in range(8) for x in range(8) if a[y][x] != b[y][x]]
        if len(d) <= N:
            out.append((len(d), a, b, d))
out.sort(key=lambda t: t[0])


def loc(t):
    cx, cy = where[t][0]
    k = w.kind[cy][cx]
    if k in w.venue_rect:
        vx, vy = w.venue_rect[k][:2]
        return f"{k} px({(cx - vx) * 8},{(cy - vy) * 8}) x{len(where[t])}"
    return f"{k} cell({cx},{cy}) x{len(where[t])}"


for n, a, b, d in out:
    print(n, "|", loc(a), "<>", loc(b), "|", " ".join(f"({x},{y}):{p}{q}" for x, y, p, q in d))
