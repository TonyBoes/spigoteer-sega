"""How many VRAM slots a fixed tile -> slot plan needs: two tiles may share a slot only if no 21 x 19 window holds both (greedy colouring)."""
import numpy as np

import render2 as R
import stats2 as S
import world2 as W

CW, CH = W.CW, W.CH


def slots(sg):
    ids = {}
    cell = np.zeros((CH, CW), dtype=int)
    for y in range(CH):
        for x in range(CW):
            cell[y, x] = ids.setdefault(sg[y][x], len(ids))
    n = len(ids)
    occ = np.zeros((n, CH, CW), dtype=np.float32)
    for y in range(CH):
        for x in range(CW):
            occ[cell[y, x], y, x] = 1
    dil = np.zeros_like(occ)
    for k in range(n):
        pad = np.pad(occ[k], ((18, 18), (20, 20)))
        acc = np.zeros((CH, CW), dtype=np.float32)
        for dy in range(37):
            for dx in range(41):
                acc += pad[dy:dy + CH, dx:dx + CW]
        dil[k] = acc > 0
    conf = (dil.reshape(n, -1) @ occ.reshape(n, -1).T) > 0
    np.fill_diagonal(conf, False)
    order = np.argsort(-conf.sum(1))
    col = -np.ones(n, dtype=int)
    for i in order:
        used = {col[j] for j in np.nonzero(conf[i])[0] if col[j] >= 0}
        c = 0
        while c in used:
            c += 1
        col[i] = c
    return n, col.max() + 1, int(conf.sum(1).max())


if __name__ == "__main__":
    w = R.LATE
    sg = S.sig_grid(w)
    print("late world: tiles, slots needed (greedy), max conflicts:", slots(sg))
    PLAIN = tuple(tuple([0] * 8) for _ in range(8))
    g = [[PLAIN if w.kind[y][x] in ("ground", "decor") else sg[y][x] for x in range(CW)] for y in range(CH)]
    print("ground and scenery plain:", slots(g))
