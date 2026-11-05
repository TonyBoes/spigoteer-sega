"""Round 5 working view: a venue's DMG picture at x6 with each 8 x 8 cell boxed by how often its tile occurs in the whole late world
(red: once, orange: twice, none: three or more).  Shows where the one-off tiles are, so the hand trim goes to the right places.
python3 tileheat.py OUTDIR [--dmg] [venue ...]"""
import sys
from collections import Counter
from pathlib import Path

from PIL import Image, ImageDraw

import pal
import stats2 as S
import world2 as W

args = [a for a in sys.argv[1:] if a != "--dmg"]
WD = W.WORLD_DMG if "--dmg" in sys.argv else W.WORLD
OUT = Path(args[0])
OUT.mkdir(parents=True, exist_ok=True)
names = args[1:] or list(W.WORLD.venue_rect)
sg = S.sig_grid(WD)
cnt = Counter(t for r in sg for t in r)
K = 6
for name in names:
    x0, y0, x1, y1 = W.WORLD.venue_rect[name]
    im = Image.new("RGB", ((x1 - x0 + 1) * 8 * K, (y1 - y0 + 1) * 8 * K))
    d = ImageDraw.Draw(im)
    uniq = set()
    for cy in range(y0, y1 + 1):
        for cx in range(x0, x1 + 1):
            t = sg[cy][cx]
            uniq.add(t)
            for j in range(8):
                for i in range(8):
                    v = pal.DMG_SHADE[t[j][i]]
                    d.rectangle([((cx - x0) * 8 + i) * K, ((cy - y0) * 8 + j) * K, ((cx - x0) * 8 + i + 1) * K - 1, ((cy - y0) * 8 + j + 1) * K - 1], fill=(v, v, v))
            c = cnt[t]
            if c <= 2:
                col = (230, 40, 40) if c == 1 else (240, 150, 30)
                d.rectangle([(cx - x0) * 8 * K, (cy - y0) * 8 * K, ((cx - x0) * 8 + 8) * K - 1, ((cy - y0) * 8 + 8) * K - 1], outline=col)
    one = sum(1 for t in uniq if cnt[t] == 1)
    two = sum(1 for t in uniq if cnt[t] == 2)
    print(f"{name:8s} cells {(x1 - x0 + 1) * (y1 - y0 + 1):3d}  distinct tiles {len(uniq):3d}  once {one:3d}  twice {two:3d}")
    im.save(OUT / f"heat_{name}.png")
