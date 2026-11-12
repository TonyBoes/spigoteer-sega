#!/usr/bin/env python3
"""Lays the story map's world-pinned clouds out (assets/story_map/cloud_layout.txt), for the denser test builds CLOUDS=C|D (src/smap_cloud.c).

A cloud is (row, pos, shape, flip): its world y is 16 * row (rows are the 16-px lines of the 35-row world), its x is pos + clock / 8 mod 512 (a cloud
that goes past 488 comes in again from the left edge: the twin at pos - 512), the shape is one of A B C (approved, 2 3 3 sprites wide) or Q (the one new, 2 wide).
The layout is searched, not drawn by hand: simulated annealing over (row, pos), the shapes fixed, to keep the sprite entries a screen (plus an 8 px margin
each way) holds <= the pool at every camera spot and clock, to have no more than 4 entries on any line, to keep clouds in one row apart and to keep clouds in
neighbouring rows from stacking. Deterministic (seeded). Usage: cloud_layout.py [--write]   (prints the statistics; --write replaces the layout file)."""
import random
import sys
from pathlib import Path

import numpy as np

OUT = Path(__file__).resolve().parents[2] / "assets" / "story_map" / "cloud_layout.txt"
W = {"A": 16, "B": 24, "C": 24, "Q": 16}
MIX = {"C": {"A": 10, "B": 2, "C": 2, "Q": 19}, "D": {"A": 14, "B": 2, "C": 2, "Q": 23}}
import os
MX, MY = int(os.environ.get("CLMX", 16)), int(os.environ.get("CLMY", 16))                                 # the margin of a look (px each way)
WS = np.arange(0, 512, 4)                      # the screen's left edge in cloud space (4 px steps)
CY = np.arange(0, 417, 4)                      # the camera's y
NROWS = 35                                    # the world is 512 x 560 px: 35 rows of 16 px, the camera goes down to y 416
POOL = 16


def xind(pos, wd):
    u = (pos - WS) % 512
    return ((u < 160 + MX) | (u > 512 - MX - wd)).astype(np.int16)


def xind_screen(pos, wd):
    u = (pos - WS) % 512
    return ((u < 160) | (u > 512 - wd)).astype(np.int16)


def yind(row, margin):
    y = 16 * row
    return ((y + 16 > CY - margin) & (y < CY + 144 + margin)).astype(np.int16)


def energy(cl, detail=False):
    T = np.zeros((len(WS), len(CY)), np.int32)
    S = np.zeros_like(T)
    rowline = {}
    pen = 0
    for i, (r, p, s) in enumerate(cl):
        wd = W[s]
        T += np.outer(xind(p, wd), yind(r, MY)) * (wd // 8)
        S += np.outer(xind_screen(p, wd), yind(r, 0))
        rowline.setdefault(r, np.zeros(len(WS), np.int32))
        rowline[r] += xind(p, wd) * (wd // 8)
    peak = int(T.max())
    for r, v in rowline.items():
        pen += 200 * max(0, int(v.max()) - 4)
    for i in range(len(cl)):
        for j in range(i):
            (r1, p1, s1), (r2, p2, s2) = cl[i], cl[j]
            d = (p1 - p2) % 512
            d = min(d, 512 - d)
            if r1 == r2 and d < (W[s1] + W[s2]) // 2 + 40:
                pen += 300
            elif abs(r1 - r2) == 1 and d < (W[s1] + W[s2]) // 2 + 24:
                pen += 20
            elif abs(r1 - r2) == 2 and d < 12:
                pen += 5
    e = 400 * max(0, peak - (POOL - 1)) + float(T.std()) * 6 + peak * 8 + pen
    if detail:
        return e, peak, round(float(T.mean()), 2), round(float(S.mean()), 2), int(S.max()), max(int(v.max()) for v in rowline.values())
    return e


def build(name, seed, iters):
    rnd = random.Random(seed)
    shapes = [s for s, n in MIX[name].items() for _ in range(n)]
    cl = [[rnd.randrange(NROWS), rnd.randrange(0, 512, 4), s] for s in shapes]
    e = energy(cl)
    temp = 40.0
    for it in range(iters):
        i = rnd.randrange(len(cl))
        old = cl[i][:]
        if rnd.random() < 0.5:
            cl[i][0] = rnd.randrange(NROWS); cl[i][1] = rnd.randrange(0, 512, 4)
        else:
            cl[i][1] = (cl[i][1] + rnd.choice((-8, -4, 4, 8, 16, -16))) % 512
        e2 = energy(cl)
        if e2 <= e or rnd.random() < np.exp((e - e2) / temp):
            e = e2
        else:
            cl[i] = old
        temp = max(0.5, temp * 0.9992)
    return sorted(cl, key=lambda c: (c[0], c[1])), e


def main():
    out = []
    for name, seed, iters in (("C", 11, 9000), ("D", 12, 16000)):
        cl, e = build(name, seed, iters)
        d = energy(cl, True)
        print(name, len(cl), "clouds; energy %.0f peak %d mean-window %.2f on-screen mean %.2f max %d max-line %d" % d)
        out.append("@" + name)
        rnd = random.Random(seed + 100)
        for r, p, s in cl:
            out.append(f"{r} {p} {s} {rnd.randrange(2)}")
    if "--write" in sys.argv:
        OUT.write_text("# the denser test builds' clouds (tools/dev/cloud_layout.py, deterministic): row (world y = 16 * row), pos (px, mod 512), shape, flip\n" + "\n".join(out) + "\n")
        print("wrote", OUT)


if __name__ == "__main__":
    main()
