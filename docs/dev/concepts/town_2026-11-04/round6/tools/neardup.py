#!/usr/bin/env python3
"""Read-only: tile pairs of a picture whose DMG index patterns differ in at most N pixels (candidates for merging a
tile by a hand edit), with their cells, the differing pixels (x, y, key here / key there).
    neardup.py PIC.txt [N]"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from render_v2 import parse   # noqa: E402

key, pix = parse(sys.argv[1])
n = int(sys.argv[2]) if len(sys.argv) > 2 else 2
tiles = {}
for cy in range(13):
    for cx in range(20):
        pat = tuple(key[pix[cy * 8 + y][cx * 8 + x]][0] for y in range(8) for x in range(8))
        tiles.setdefault(pat, []).append((cx, cy))
pats = list(tiles)
out = []
for i, a in enumerate(pats):
    for b in pats[i + 1:]:
        d = [k for k in range(64) if a[k] != b[k]]
        if len(d) <= n:
            ca, cb = tiles[a][0], tiles[b][0]
            px = [(ca[0] * 8 + k % 8, ca[1] * 8 + k // 8, pix[ca[1] * 8 + k // 8][ca[0] * 8 + k % 8],
                   pix[cb[1] * 8 + k // 8][cb[0] * 8 + k % 8]) for k in d]
            out.append((len(d), tiles[a], tiles[b], px))
for d, ca, cb, px in sorted(out):
    print(d, ca, cb, px)
