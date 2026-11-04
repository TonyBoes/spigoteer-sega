"""Read-only: orphan pixels (unlike all 8 neighbours) in B that are not orphans in A.   orphans.py A.png B.png"""
import sys
import numpy as np
from PIL import Image


def orph(f):
    rgb = np.array(Image.open(f).convert("RGB")).astype(int)
    h, w = rgb.shape[:2]
    out = set()
    for y in range(1, h - 1):
        for x in range(1, w - 1):
            c = rgb[y, x]
            nb = [rgb[y + dy, x + dx] for dy in (-1, 0, 1) for dx in (-1, 0, 1) if dy or dx]
            if not any((n == c).all() for n in nb):
                out.add((x, y))
    return out


a, b = orph(sys.argv[1]), orph(sys.argv[2])
print("new:", sorted(b - a, key=lambda p: (p[1], p[0])))
print("gone:", sorted(a - b, key=lambda p: (p[1], p[0])))
