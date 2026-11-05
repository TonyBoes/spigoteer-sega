"""Round 5: how many slots a static home-slot plan needs for the DMG set, and how a few dynamic overflow slots take the rest.
Conflict graph: two tiles conflict when some 21 x 19 window of any unlock state holds both.  Greedy colouring by degree with a cap of C colours (the
home slots); tiles that find no colour are the overflow tiles.  For each C we count the most overflow tiles any window holds (K needed).
python3 hybrid.py [dmg|color]"""
import sys

import numpy as np

import stats2 as S
import winstat as WS
import world2 as W

MODE = sys.argv[1] if len(sys.argv) > 1 else "dmg"
CW, CH = W.CW, W.CH
world = W.WORLD_DMG if MODE == "dmg" else W.WORLD
states = [S.sig_grid(v) for v in WS.states(world)]
ids = {}
G = []
for sg in states:
    G.append(np.array([[ids.setdefault(sg[y][x], len(ids)) for x in range(CW)] for y in range(CH)]))
n = len(ids)
print(MODE, "tiles over all 11 states:", n)
conf = np.zeros((n, n), dtype=bool)
WWd, WHt = 21, 19
for g in G:
    for y0 in range(CH - WHt + 1):
        for x0 in range(CW - WWd + 1):
            u = np.unique(g[y0:y0 + WHt, x0:x0 + WWd])
            conf[np.ix_(u, u)] = True
np.fill_diagonal(conf, False)
deg = conf.sum(1)
order = np.argsort(-deg, kind="stable")
print("max conflicts", int(deg.max()))


def colour(cap):
    col = -np.ones(n, dtype=int)
    for i in order:
        used = {col[j] for j in np.nonzero(conf[i])[0] if col[j] >= 0}
        c = 0
        while c in used and c < cap:
            c += 1
        if c < cap:
            col[i] = c
    return col


full = colour(10 ** 6)
print("static colouring needs", int(full.max()) + 1, "slots")
wins = []
for g in G:
    for y0 in range(CH - WHt + 1):
        for x0 in range(CW - WWd + 1):
            wins.append(np.unique(g[y0:y0 + WHt, x0:x0 + WWd]))
for K in range(0, 41, 2):
    cap = 176 - K
    col = colour(cap)
    over = col < 0
    worst = max(int(over[u].sum()) for u in wins)
    print(f"home slots {cap:3d}  overflow tiles {int(over.sum()):3d}  most overflow tiles in a window {worst:3d}  {'OK' if worst <= K else ''}")
