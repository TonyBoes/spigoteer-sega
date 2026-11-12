#!/usr/bin/env python3
"""Lays the story map's world-pinned clouds out (assets/story_map/cloud_layout.txt, src/smap_cloud.c).

A record is (row, pos, shape, flip): its world y is 16 * row (rows are the 16-px lines of the 35-row world), its x is pos + clock / 8 mod 512 (a cloud that goes past
488 comes in again from the left edge: the twin at pos - 512). Shapes: A (16 wide, 2 sprites) and B (24, 3), the approved ones; and the BIG cloud (48x32), which is four
records that move together: T (the top half's left 24 px) and U (the bottom half's) in rows r and r + 1 at pos, and the same two flipped at pos + 24.
The layout is searched, not drawn by hand: simulated annealing over (row, pos), the shapes fixed, to keep the sprite entries that a screen (plus a 20 px margin each way)
holds <= the pool (16, 15 aimed at) at every camera spot and clock, to have no more than 4 entries on any line (a big cloud's rows: 6, alone), to keep clouds in one row
apart and clouds in neighbouring rows from stacking. Deterministic (seeded). Usage: cloud_layout.py [--write]   (prints the statistics; --write replaces the layout file)."""
import os
import random
import sys
from pathlib import Path

import numpy as np

OUT = Path(__file__).resolve().parents[2] / "assets" / "story_map" / "cloud_layout.txt"
W = {"A": 16, "B": 24, "T": 24, "U": 24, "V": 24}
NSMALL = {"A": int(os.environ.get("CLA", 0)), "B": int(os.environ.get("CLB", 14))}      # (A is not a shape any more: OBJ tiles; CLA is kept for a scratch build)
NBIG = int(os.environ.get("CLBIG", 2))
BIGTOPS = "TV"                                 # the first big cloud has the top T, the second the long one V (its bottom half is the first one's: U)
MX, MY = 20, 20                                # the margin of a look (px each way)
WS = np.arange(0, 512, 4)                      # the screen's left edge in cloud space (4 px steps)
CY = np.arange(0, 417, 4)                      # the camera's y
NROWS = 35                                     # the world is 512 x 560 px: 35 rows of 16 px, the camera goes down to y 416
POOL = 16
# Sal's rows: the roads are at world y 100, 236, 372, 508 and a stop has its arrows 33 px above his feet, the dot at his feet and the down arrow below: [y - 48, y + 36] at each. A big cloud (32 px, 6 + Sal 2 +
# arrows 2 + the dot 1 would be 11 sprites on a line) keeps out of them: its first row r is one of these.
BIGROWS = [9, 17, 26]                          # (the first NBIG of them, one each)


def xind(pos, wd):
    u = (pos - WS) % 512
    return ((u < 160 + MX) | (u > 512 - MX - wd)).astype(np.int16)


def xind_screen(pos, wd):
    u = (pos - WS) % 512
    return ((u < 160) | (u > 512 - wd)).astype(np.int16)


def yind(row, margin):
    y = 16 * row
    return ((y + 16 > CY - margin) & (y < CY + 144 + margin)).astype(np.int16)


def records(items):
    """items: ('s', row, pos, shape) or ('b', row, pos) -> [(row, pos, shape, flip, group)]"""
    out = []
    for g, it in enumerate(items):
        if it[0] == "s":
            out.append((it[1], it[2], it[3], None, g))
        else:
            r, p = it[1], it[2]
            t = it[3] if len(it) > 3 else "T"
            out += [(r, p, t, 0, g), (r, (p + 24) % 512, t, 1, g), (r + 1, p, "U", 0, g), (r + 1, (p + 24) % 512, "U", 1, g)]
    return out


def energy(items, detail=False):
    recs = records(items)
    T = np.zeros((len(WS), len(CY)), np.int32)
    S = np.zeros(T.shape)
    rowline, bigrow = {}, set()
    pen = 0
    for r, p, s, f, g in recs:
        wd = W[s]
        T += np.outer(xind(p, wd), yind(r, MY)) * (wd // 8)
        S += np.outer(xind_screen(p, wd), yind(r, 0)) * (0.25 if s in 'TUV' else 1.0)
        rowline.setdefault(r, np.zeros(len(WS), np.int32))
        rowline[r] += xind(p, wd) * (wd // 8)
        if s in "TUV":
            bigrow.add(r)
    peak = int(T.max())
    for r, v in rowline.items():
        pen += 200 * max(0, int(v.max()) - (6 if r in bigrow else 4))
    for i in range(len(recs)):
        for j in range(i):
            (r1, p1, s1, _, g1), (r2, p2, s2, _, g2) = recs[i], recs[j]
            if g1 == g2 and items[g1][0] == "b":
                continue
            d = (p1 - p2) % 512
            d = min(d, 512 - d)
            if r1 == r2 and d < (W[s1] + W[s2]) // 2 + 40:
                pen += 300
            elif abs(r1 - r2) == 1 and d < (W[s1] + W[s2]) // 2 + 24:
                pen += 20
            elif abs(r1 - r2) == 2 and d < 12:
                pen += 5
    ncl = sum(1 for it in items)
    e = 400 * max(0, peak - (POOL - 1)) + float(T.std()) * 6 + peak * 8 + pen
    if detail:
        return e, peak, round(float(T.mean()), 2), round(float(S.mean() / 1.0), 2), int(S.max()), max(int(v.max()) for v in rowline.values())
    return e


def build(seed, iters):
    rnd = random.Random(seed)
    items = [("s", rnd.randrange(NROWS), rnd.randrange(0, 512, 4), s) for s, n in NSMALL.items() for _ in range(n)]
    items += [("b", BIGROWS[k], rnd.randrange(0, 512, 4), BIGTOPS[k % 2]) for k in range(NBIG)]
    e = energy(items)
    temp = 40.0
    for it in range(iters):
        i = rnd.randrange(len(items))
        old = items[i]
        r, p = old[1], old[2]
        if rnd.random() < 0.5:
            r, p = (old[1] if old[0] == "b" else rnd.randrange(NROWS)), rnd.randrange(0, 512, 4)
        else:
            p = (p + rnd.choice((-8, -4, 4, 8, 16, -16))) % 512
        items[i] = (old[0], r, p) + old[3:]
        e2 = energy(items)
        if e2 <= e or rnd.random() < np.exp((e - e2) / temp):
            e = e2
        else:
            items[i] = old
        temp = max(0.5, temp * 0.9992)
    return items, e


def main():
    items, e = build(21, int(os.environ.get("CLIT", 20000)))
    d = energy(items, True)
    print("%d clouds (%d big); energy %.0f peak %d mean-window %.2f on-screen mean %.2f max %d max-line %d" % ((len(items), sum(1 for i in items if i[0] == "b")) + d))
    recs = records(items)
    rnd = random.Random(121)
    lines = []
    for r, p, s, f, g in sorted(recs, key=lambda t: (t[0], t[1])):
        lines.append(f"{r} {p} {s} {rnd.randrange(2) if f is None else f}")
    if "--write" in sys.argv:
        OUT.write_text("# the story map's clouds (tools/dev/cloud_layout.py, deterministic): row (world y = 16 * row), pos (px, mod 512), shape (A, B; T and U: the big cloud's top and bottom halves), flip\n" + "\n".join(lines) + "\n")
        print("wrote", OUT, len(lines), "records")


if __name__ == "__main__":
    main()
