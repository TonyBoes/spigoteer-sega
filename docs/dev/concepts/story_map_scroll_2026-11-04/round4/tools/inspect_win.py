"""python3 inspect_win.py STATE X0 Y0: the palettes of one window and the kinds of cell that hold them."""
import sys
from collections import Counter

import world2 as W

p, x0, y0 = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3])
v = W.with_fog(W.WORLD, {"town"} | set(W.ORDER[:p])) if p < 10 else W.WORLD
c = {}
for y in range(y0, y0 + 19):
    for x in range(x0, x0 + 21):
        c.setdefault(v.pal[y][x], Counter())[v.kind[y][x]] += 1
for k, n in sorted(c.items(), key=lambda t: sum(t[1].values())):
    print(k, sum(n.values()), dict(n))
