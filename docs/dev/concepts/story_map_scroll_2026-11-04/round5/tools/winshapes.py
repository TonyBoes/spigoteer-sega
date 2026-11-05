"""Round 5: the worst DMG window for the three window shapes the camera can show: 21 x 19 (both axes off the 8 px grid), 21 x 18 (y on the grid:
the camera walks a road sideways) and 20 x 19 (x on the grid: it walks a spine).   python3 winshapes.py [dmg|color]"""
import sys

import numpy as np

import stats2 as S
import winstat as WS
import world2 as W

CW, CH = W.CW, W.CH


def worst(sg, ww, wh):
    best, at, over = 0, None, 0
    for y0 in range(CH - wh + 1):
        for x0 in range(CW - ww + 1):
            n = len({sg[y][x] for y in range(y0, y0 + wh) for x in range(x0, x0 + ww)})
            if n > 176:
                over += 1
            if n > best:
                best, at = n, (x0, y0)
    return best, at, over


if __name__ == "__main__":
    world = W.WORLD if len(sys.argv) > 1 and sys.argv[1] == "color" else W.WORLD_DMG
    res = {}
    for n, v in enumerate(WS.states(world)):
        sg = S.sig_grid(v)
        for shape in ((21, 19), (21, 18), (20, 19)):
            b, at, over = worst(sg, *shape)
            res.setdefault(shape, []).append((b, at, over))
    for shape, rows in res.items():
        print(shape, "per state worst:", [r[0] for r in rows], " late: worst", rows[-1][0], "at", rows[-1][1], " windows over 176 in the late world:", rows[-1][2])
