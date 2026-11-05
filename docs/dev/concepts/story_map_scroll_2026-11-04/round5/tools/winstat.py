"""Round 5: the DMG window counts with the art as it stands (no merge): per unlock state the worst 21 x 19 window, how many windows are over the
pool (176), the largest excess, and what the tiles of the worst window are made of (by the kind of the cells that use them).
python3 winstat.py [dmg]"""
import sys
from collections import Counter

import numpy as np

import stats2 as S
import world2 as W

CW, CH = W.CW, W.CH
TARGET = 176
DMG = len(sys.argv) > 1 and sys.argv[1] == "dmg"
WW, WH = 21, 19


def states(world=None):
    world = world or W.WORLD
    out = []
    for p in range(0, 11):
        out.append(W.with_fog(world, {"town"} | set(W.ORDER[:p])) if p < 10 else world)
    return out


def counts(sg):
    res = np.zeros((CH - WH + 1, CW - WW + 1), dtype=int)
    for y0 in range(CH - WH + 1):
        for x0 in range(CW - WW + 1):
            res[y0, x0] = len({sg[y][x] for y in range(y0, y0 + WH) for x in range(x0, x0 + WW)})
    return res


def breakdown(w, sg, x0, y0):
    use = {}
    for y in range(y0, y0 + WH):
        for x in range(x0, x0 + WW):
            use.setdefault(sg[y][x], Counter())[w.kind[y][x]] += 1
    tot = Counter()
    for t, c in use.items():
        tot[c.most_common(1)[0][0]] += 1
    return tot


if __name__ == "__main__":
    for n, v in enumerate(states(W.WORLD_DMG if DMG else W.WORLD)):
        sg = S.sig_grid(v)
        c = counts(sg)
        over = int((c > TARGET).sum())
        y0, x0 = np.unravel_index(int(c.argmax()), c.shape)
        print(f"state {n:2d}: worst {c.max()} at cell ({x0},{y0}); windows over {TARGET}: {over} of {c.size}; most to lose {max(0, c.max() - TARGET)}")
        if n == 10:
            print("  worst window by kind:", dict(breakdown(v, sg, x0, y0)))
            hist = Counter()
            for e in (c[c > TARGET] - TARGET):
                hist[int(e // 5 * 5)] += 1
            print("  excess histogram (5-tile bins):", sorted(hist.items()))
            np.save("win_late_dmg.npy" if DMG else "win_late.npy", c)
