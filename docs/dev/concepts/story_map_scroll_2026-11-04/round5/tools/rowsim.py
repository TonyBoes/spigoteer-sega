"""Round 5 working list: for a venue of the DMG world, the cell rows where several different tiles look alike (they differ in at most N pixels),
which is what a pattern with a period other than 8 looks like.   python3 rowsim.py venue [N]"""
import sys

import stats2 as S
import world2 as W

name = sys.argv[1]
N = int(sys.argv[2]) if len(sys.argv) > 2 else 10
w = W.WORLD_DMG
sg = S.sig_grid(w)
x0, y0, x1, y1 = w.venue_rect[name]
for cy in range(y0, y1 + 1):
    row = [sg[cy][cx] for cx in range(x0, x1 + 1)]
    ids = {}
    for t in row:
        ids.setdefault(t, len(ids))
    distinct = list(ids)
    sim = []
    for i, a in enumerate(distinct):
        for b in distinct[i + 1:]:
            d = sum(1 for y in range(8) for x in range(8) if a[y][x] != b[y][x])
            if d <= N:
                sim.append((d, ids[a], ids[b]))
    print(f"row {cy - y0}: {len(row)} cells, {len(distinct)} distinct; look-alike pairs (d, i, j):", sorted(sim)[:8])
