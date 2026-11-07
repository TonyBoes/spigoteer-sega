"""Scratch probe: the 21 x 19 windows of layout NAME that need more than 8 BG palettes, with the palettes and their cell counts.  python3 -I probe_pal.py lay_A4"""
import os
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
os.environ["SMAP_LAYOUT"] = sys.argv[1]
os.environ["SMAP_FOG"] = "none"
sys.path.insert(0, str(HERE / "src"))
sys.path.append(str(ROOT / "tools" / "smap_world"))
import world2 as W  # noqa: E402

w = W.WORLD
CW, CH = W.CW, W.CH
bad = []
for y0 in range(CH - 18):
    for x0 in range(CW - 20):
        c = Counter(w.pal[y][x] for y in range(y0, y0 + 19) for x in range(x0, x0 + 21))
        if len(c) > 8:
            bad.append((len(c), x0, y0, dict(c)))
print(len(bad), "windows over 8")
seen = set()
for n, x0, y0, c in sorted(bad, key=lambda b: -b[0])[:12]:
    key = tuple(sorted(c))
    if key in seen:
        continue
    seen.add(key)
    print(n, (x0, y0), sorted(c.items(), key=lambda kv: kv[1]))
