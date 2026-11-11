#!/usr/bin/env python3
"""Cost curve: tiles saved and pixels changed as the per-tile cap grows from 1 to 10 px (screened merges, vetoes.py applied), for
  all areas       (every tile may change)
  ground only     (venue tiles untouched: moved tiles are those with no cell in a venue)
    python3 docs/dev/proposals/smap_dmg_kit2/curve.py     (about 2 min; prints a markdown table, writes curve.md)"""
import numpy as np

import lib
import merge
import render
from vetoes import PROTECT, CAP

CAPS = (1, 2, 3, 4, 5, 6, 8, 10)


def stages(dm, sg, use, pin, d, veto, limit):
    state = None
    out = {}
    base = render.new_world(dm, np.arange(len(sg)))
    for dmax in range(1, max(CAPS) + 1):
        rep, log, groups = merge.greedy(sg, use, pin, dmax, d, veto=veto, state=state, protect=PROTECT, cap=CAP, limit=limit)
        state = (rep, groups)
        if dmax in CAPS:
            gr, arr = merge.apply_map(dm, rep)
            m = lib.metrics(gr, steps=False)
            px = int((render.new_world(dm, arr) != base).sum())
            out[dmax] = (m["unique"], m["w21"][0], px)
    return out


def main():
    dm, sg, use, pin = merge.prepare()
    d = merge.dist_matrix(sg)
    base = np.array(dm.world.px, dtype=np.uint8)
    veto = merge.auto_veto(dm, sg, use, pin, d, base, max(CAPS))
    vten = merge.venue_ids(dm, len(sg))
    a = stages(dm, sg, use, pin, d, veto, np.full(len(sg), 99))
    g = stages(dm, sg, use, pin, d, veto, np.where(vten, 0, 99))
    L = ["| cap per tile | all areas: tiles saved | px | worst 21x19 | ground only: tiles saved | px | worst 21x19 |", "|---|---|---|---|---|---|---|"]
    for c in CAPS:
        L.append(f"| {c} px | {896 - a[c][0]} | {a[c][2]} | {a[c][1]} | {896 - g[c][0]} | {g[c][2]} | {g[c][1]} |")
    (lib.OUT / "curve.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
