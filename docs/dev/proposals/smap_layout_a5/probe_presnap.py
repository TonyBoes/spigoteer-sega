import os
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
os.environ["SMAP_LAYOUT"] = sys.argv[1]
os.environ["SMAP_FOG"] = "none"
d = "smap_layout_a5" if sys.argv[1] == "lay_A5" else "smap_layout_a4"
sys.path.insert(0, str(HERE / "src"))
sys.path.append(str(ROOT / "tools/smap_world"))
import world2 as W

w = W.WORLD
print("snapped", len(W.SNAPPED))
pal = [r[:] for r in w.pal]
for (x, y, old, new) in W.SNAPPED:
    pal[y][x] = old
bad = []
for y0 in range(W.CH - 18):
    for x0 in range(W.CW - 20):
        c = Counter(pal[y][x] for y in range(y0, y0 + 19) for x in range(x0, x0 + 21))
        if len(c) > 8:
            bad.append((len(c), x0, y0, dict(c)))
print(len(bad), "windows over 8 before snapping")
for n, x0, y0, c in sorted(bad, key=lambda b: -b[0])[:4]:
    print(n, (x0, y0), sorted(c.items(), key=lambda kv: kv[1]))
