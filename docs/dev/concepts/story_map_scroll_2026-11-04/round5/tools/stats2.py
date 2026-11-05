"""Numbers for NOTES.md (round 2): unique tiles per world / zone / window, palettes per window, streaming bytes, sprites per line."""
import json
from collections import Counter

import render2 as R
import world2 as W

CW, CH = W.CW, W.CH


def sig_grid(w):
    px = w.px
    return [[tuple(tuple(px[cy * 8 + j][cx * 8:cx * 8 + 8]) for j in range(8)) for cx in range(CW)] for cy in range(CH)]


def window_stats(sg, pg, ww=21, wh=19):
    best_t, best_p, at = 0, 0, None
    for y0 in range(CH - wh + 1):
        for x0 in range(CW - ww + 1):
            t = {sg[y][x] for y in range(y0, y0 + wh) for x in range(x0, x0 + ww)}
            p = {pg[y][x] for y in range(y0, y0 + wh) for x in range(x0, x0 + ww)}
            if len(t) > best_t:
                best_t, at = len(t), (x0, y0)
            best_p = max(best_p, len(p))
    return best_t, best_p, at


def stream(sg, ww=21, wh=19):
    """tiles that must be uploaded when the window moves one cell: those of the new column / row that the old window did not hold"""
    worst_c = worst_r = 0
    tot_c = n_c = 0
    for y0 in range(CH - wh + 1):
        for x0 in range(CW - ww):
            old = {sg[y][x] for y in range(y0, y0 + wh) for x in range(x0, x0 + ww)}
            for nx, d in ((x0 + ww, 1), (x0 - 1, -1)):
                if not 0 <= nx < CW:
                    continue
                old2 = {sg[y][x] for y in range(y0, y0 + wh) for x in range(x0, x0 + ww)}
                new = {sg[y][nx] for y in range(y0, y0 + wh)} - old2
                worst_c = max(worst_c, len(new))
                tot_c += len(new)
                n_c += 1
    for x0 in range(CW - ww + 1):
        for y0 in range(CH - wh):
            old = {sg[y][x] for y in range(y0, y0 + wh) for x in range(x0, x0 + ww)}
            for ny in (y0 + wh, y0 - 1):
                if not 0 <= ny < CH:
                    continue
                new = {sg[ny][x] for x in range(x0, x0 + ww)} - old
                worst_r = max(worst_r, len(new))
    return worst_c, worst_r, tot_c / n_c


if __name__ == "__main__":
    late = R.LATE
    sg = sig_grid(late)
    pg = late.pal
    allt = {sg[y][x] for y in range(CH) for x in range(CW)}
    print("unique tiles, whole late world:", len(allt))
    zones = {}
    for y in range(CH):
        for x in range(CW):
            zones.setdefault(W.ZONE[y][x], set()).add(sg[y][x])
    for z, s in sorted(zones.items()):
        print(f"  zone {z:8s} {len(s):3d} tiles   (only here: {len(s - set().union(*[v for k, v in zones.items() if k != z]))})")
    print("palettes, whole late world:", len({pg[y][x] for y in range(CH) for x in range(CW)}))
    print("window 21x19 late: tiles, palettes, where =", window_stats(sg, pg))
    print("streaming (late world, cell step): worst new tiles per column, per row, mean per column =", stream(sg))
    for p in (0, 3, 5, 8, 10):
        rev = {"town"} | set(W.ORDER[:p])
        w = W.with_fog(W.WORLD, rev) if p < 10 else W.WORLD
        s2 = sig_grid(w)
        tt = len({s2[y][x] for y in range(CH) for x in range(CW)})
        print(f"state {p:2d} venues open: world tiles {tt}, window max (tiles, pals, at) = {window_stats(s2, w.pal)}, stream = {stream(s2)}")
