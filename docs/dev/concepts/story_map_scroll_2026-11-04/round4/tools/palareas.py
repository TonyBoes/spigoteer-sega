"""Which BG palettes each area uses (late world), and every palette's colours with their RGB555 words."""
from collections import Counter

import pal
import world2 as W

w = W.WORLD
per = {}
for y in range(W.CH):
    for x in range(W.CW):
        per.setdefault(W.ZONE[y][x], Counter())[w.pal[y][x]] += 1
for z in sorted(per):
    print(f"{z:8s} " + ", ".join(f"{n} {c}" for n, c in per[z].most_common()))
print()
used = sorted({n for c in per.values() for n in c} | {"fog:fogbase", "fog:grass", "fog:saloon"})
for n in used:
    cols = pal.get(n)
    words = []
    for c in cols:
        r, g, b = (int(v) >> 3 for v in c)
        words.append("%04x" % (r | g << 5 | b << 10))
    print(f"{n:12s} " + " ".join("%02x%02x%02x" % tuple(int(v) for v in c) for c in cols) + "   " + " ".join(words))
