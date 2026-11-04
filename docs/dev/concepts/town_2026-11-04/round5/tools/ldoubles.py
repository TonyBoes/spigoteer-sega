#!/usr/bin/env python3
"""Read-only: the lint's L-double positions (same rule as gb_art_lint.py), all of them, grouped by 8x8 cell.
    ldoubles.py IMAGE.png"""
import sys
from collections import Counter
import numpy as np
from PIL import Image

rgb = np.array(Image.open(sys.argv[1]).convert("RGB"))
h, w = rgb.shape[:2]
cols = {tuple(c) for c in rgb.reshape(-1, 3)}
dark = min(cols, key=lambda c: 0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2])
dm = np.all(rgb == np.array(dark, np.uint8), axis=2)
ls = set()
for y in range(h):
    for x in range(w):
        if not dm[y, x]:
            continue
        for dy in (-1, 1):
            for dx in (-1, 1):
                yy, xx = y + dy, x + dx
                if 0 <= yy < h and 0 <= xx < w and dm[y, xx] and dm[yy, x] and not dm[yy, xx]:
                    bh = 0 <= x + 2 * dx < w and dm[y, x + 2 * dx]
                    bv = 0 <= y + 2 * dy < h and dm[y + 2 * dy, x]
                    if not bh and not bv:
                        ls.add((x, y))
print(len(ls), sorted(Counter((x // 8, y // 8) for x, y in ls).items()))
