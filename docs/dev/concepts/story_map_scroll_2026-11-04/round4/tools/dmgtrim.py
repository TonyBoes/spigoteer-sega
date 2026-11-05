"""The DMG data set (round 4): a tile-merge table.  A tile is replaced by another tile of the map, one that is already drawn (no pixel is made up).
Merges are taken cheapest first, cost = (sum of shade-index differences between the two tiles) x (cells that use the dropped tile), a tile that
was merged is never a target and a target is never merged, so no tile drifts through a chain.  The number of merges is the smallest that puts
every 21 x 19 window, in every unlock state, within TARGET tiles.  Writes dmg_merge.json (tile signature -> kept tile) for the preview."""
import json
import sys

import numpy as np

import render2 as R
import stats2 as S
import world2 as W

TARGET = 176
CW, CH = W.CW, W.CH


def states():
    out = []
    for p in range(0, 11):
        out.append(W.with_fog(W.WORLD, {"town"} | set(W.ORDER[:p])) if p < 10 else W.WORLD)
    return out


SIGNS = {"zoo": (30, 12, 52, 18), "lodge": (31, 29, 51, 33), "factory": (28, 34, 52, 38), "bistro": (22, 2, 52, 6),
         "saloon": (29, 5, 44, 9), "stadium": (25, 3, 57, 15), "cow": (37, 23, 60, 30)}      # lettering boxes, venue-local pixels


def protected(grid):
    """Tiles that carry sign lettering: never dropped, so TAPS, LODGE, BISTRO, ROBOCO, MILK and ZOO stay readable."""
    out = set()
    for name, (x0, y0, x1, y1) in SIGNS.items():
        vx, vy = W.WORLD.venue_rect[name][:2]
        for cy in range(vy + y0 // 8, vy + y1 // 8 + 1):
            for cx in range(vx + x0 // 8, vx + x1 // 8 + 1):
                out.add(grid[cy][cx])
    return out


def order_merges(allgrids):
    cnt = {}
    for g in allgrids[-1:]:                      # counts in the late world
        for r in g:
            for t in r:
                cnt[t] = cnt.get(t, 0) + 1
    for g in allgrids[:-1]:
        for r in g:
            for t in r:
                cnt.setdefault(t, 0)
    tiles = list(cnt)
    prot = protected(allgrids[-1])
    arr = np.array([[ch for row in t for ch in row] for t in tiles], dtype=np.int16)
    n = len(tiles)
    d = np.abs(arr[:, None, :] - arr[None, :, :]).sum(2)
    pairs = []
    for i in range(n):
        for j in range(n):
            if i != j and tiles[i] not in prot and cnt[tiles[i]] <= cnt[tiles[j]]:
                pairs.append((int(d[i, j]) * max(cnt[tiles[i]], 1), i, j))
    pairs.sort()
    drop, keep, seq = set(), set(), []
    for cost, i, j in pairs:
        if i in drop or i in keep or j in drop:
            continue
        drop.add(i)
        keep.add(j)
        seq.append((tiles[i], tiles[j], cost, int(d[i, j])))
    return seq


def apply(grid, mp):
    return [[mp.get(t, t) for t in r] for r in grid]


def wmax(g, ww=21, wh=19):
    best = 0
    for y0 in range(CH - wh + 1):
        for x0 in range(CW - ww + 1):
            best = max(best, len({g[y][x] for y in range(y0, y0 + wh) for x in range(x0, x0 + ww)}))
    return best


if __name__ == "__main__":
    sts = states()
    grids = [S.sig_grid(v) for v in sts]
    print("DMG window max before:", max(wmax(g) for g in grids))
    seq = order_merges(grids)
    print("candidate merges:", len(seq))
    lo, hi = 0, len(seq)
    while lo < hi:
        mid = (lo + hi) // 2
        mp = {a: b for a, b, _, _ in seq[:mid]}
        if max(wmax(apply(g, mp)) for g in grids) <= TARGET:
            hi = mid
        else:
            lo = mid + 1
    # a fixed tile -> slot plan needs more slots than the window max: go on until the greedy colouring of the late world fits TARGET
    import slots as SL
    lo2, hi2 = lo, len(seq)
    while lo2 < hi2:
        mid = (lo2 + hi2) // 2
        mp = {a: b for a, b, _, _ in seq[:mid]}
        if SL.slots(apply(grids[-1], mp))[1] <= TARGET:
            hi2 = mid
        else:
            lo2 = mid + 1
    print("merges for the window max alone:", lo, " for the slot plan:", lo2)
    lo = lo2
    mp = {a: b for a, b, _, _ in seq[:lo]}
    worst = max(wmax(apply(g, mp)) for g in grids)
    tiles_after = len({t for r in apply(grids[-1], mp) for t in r})
    print("merges:", lo, " window max after:", worst, " world tiles after:", tiles_after,
          " largest single difference:", max(d for _, _, _, d in seq[:lo]) if lo else 0)
    json.dump([[a, b] for a, b in mp.items()], open(sys.argv[1] if len(sys.argv) > 1 else "dmg_merge.json", "w"))
