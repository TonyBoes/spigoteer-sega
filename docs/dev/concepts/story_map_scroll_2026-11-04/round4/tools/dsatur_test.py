"""Slots needed by greedy and by DSATUR colouring after the first N merges of a merge table.
python3 dsatur_test.py MERGE.json N"""
import json
import sys

import numpy as np

import render2 as R
import stats2 as S
import world2 as W

CW, CH = W.CW, W.CH


def conflict(tg):
    ids = {}
    cell = np.zeros((CH, CW), dtype=int)
    for y in range(CH):
        for x in range(CW):
            cell[y, x] = ids.setdefault(tg[y][x], len(ids))
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
    return n, conf


def dsatur(conf):
    n = len(conf)
    col = -np.ones(n, dtype=int)
    sat = [set() for _ in range(n)]
    deg = conf.sum(1)
    for _ in range(n):
        i = max((k for k in range(n) if col[k] < 0), key=lambda k: (len(sat[k]), deg[k]))
        c = 0
        while c in sat[i]:
            c += 1
        col[i] = c
        for j in np.nonzero(conf[i])[0]:
            sat[j].add(c)
    return int(col.max()) + 1


if __name__ == "__main__":
    pairs = json.load(open(sys.argv[1]))[:int(sys.argv[2])]
    mp = {tuple(tuple(r) for r in a): tuple(tuple(r) for r in b) for a, b in pairs}
    sg = S.sig_grid(R.LATE)
    tg = [[mp.get(t, t) for t in r] for r in sg]
    n, conf = conflict(tg)
    print("merges", len(pairs), "tiles", n, "dsatur slots", dsatur(conf))
