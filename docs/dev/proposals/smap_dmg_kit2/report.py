#!/usr/bin/env python3
"""Numbers for NOTES.md: packages (after packages.py), changed pixels per area, the ranked list as a table, the Color check.
    python3 docs/dev/proposals/smap_dmg_kit2/report.py   (writes report.json, ranked.md, areas.md, packages.md next to it)"""
import json
from collections import Counter, defaultdict

import numpy as np

import lib
import merge
import render

PKG = {"light": "light", "medium": "medium", "strong": "strong"}


def main():
    res = json.load(open(lib.OUT / "results.json"))
    arrs = np.load(lib.OUT / "arrays.npz")
    dm, sg, use, pin = merge.prepare()
    G = lib.G
    base = render.new_world(dm, np.arange(len(sg)))
    pg = lib.piece_grid()
    m0 = lib.metrics({p: dm.grids[p] for p in dm.ustates})
    rows = {"today": dict(tiles=m0["unique"], once=m0["once"], w21=m0["w21"][0], w22=m0["w22"][0], mean=m0["step_mean"], p95=m0["step_p95"],
                          px=0, cells=0, hard=0)}
    per_area = {}
    for name, key in PKG.items():
        arr = arrs[key]
        gr = {p: arr[dm.grids[p]] for p in dm.ustates}
        m = lib.metrics(gr)
        new = render.new_world(dm, arr)
        ch = new != base
        hard = int((np.abs(new.astype(int) - base.astype(int)) >= 2)[ch].sum())
        cells = ch.reshape(lib.CH, 8, lib.CW, 8).any(axis=(1, 3))
        rows[name] = dict(tiles=m["unique"], once=m["once"], w21=m["w21"][0], w22=m["w22"][0], mean=m["step_mean"], p95=m["step_p95"],
                          px=int(ch.sum()), cells=int(cells.sum()), hard=hard)
        pa = defaultdict(lambda: [0, 0])
        for y in range(lib.CH):
            for x in range(lib.CW):
                if cells[y, x]:
                    n = pg[y][x]
                    a = "Roads" if n == "Roads" else ("Ground: " + n[6:] if n.startswith("Land:") else n)
                    pa[a][0] += 1
                    pa[a][1] += int(ch[y * 8:y * 8 + 8, x * 8:x * 8 + 8].sum())
        per_area[name] = dict(pa)
    # ---- packages table
    L = ["| package | tiles | saved | used once | worst 21x19 | worst 22x20 | step mean | step p95 | px changed | cells changed | px that change a shade by 2+ |",
         "|---|---|---|---|---|---|---|---|---|---|---|"]
    for name in ("today", "light", "medium", "strong"):
        r = rows[name]
        L.append(f"| {name} | {r['tiles']} | {rows['today']['tiles'] - r['tiles']} | {r['once']} | {r['w21']} | {r['w22']} | {r['mean']:.2f} | {r['p95']:.0f} | "
                 f"{r['px']} | {r['cells']} | {r['hard']} |")
    (lib.OUT / "packages.md").write_text("\n".join(L) + "\n")
    # ---- areas table
    ven = ("Stadium", "Bistro", "Igloo", "Saloon", "Town", "Lodge", "Space", "Factory", "Zoo", "Teahouse", "Rodeo")
    cells_of = Counter()
    for y in range(lib.CH):
        for x in range(lib.CW):
            n = pg[y][x]
            cells_of["Roads" if n == "Roads" else ("Ground: " + n[6:] if n.startswith("Land:") else n)] += 1
    names = list(ven) + ["Roads"] + sorted(k for k in cells_of if k.startswith("Ground"))
    A = ["| area | cells | light: cells / px | medium: cells / px | strong: cells / px |", "|---|---|---|---|---|"]
    for a in names:
        l = per_area["light"].get(a, [0, 0])
        mm = per_area["medium"].get(a, [0, 0])
        st = per_area["strong"].get(a, [0, 0])
        if l[0] or mm[0] or st[0]:
            A.append(f"| {a} | {cells_of[a]} | {l[0]} / {l[1]} | {mm[0]} / {mm[1]} | {st[0]} / {st[1]} |")
    (lib.OUT / "areas.md").write_text("\n".join(A) + "\n")
    # ---- ranked list
    g = dm.grids[G.NSTATE]
    R = ["| # | stage | in light / medium | px | cells | where | block (replaced > kept) |", "|---|---|---|---|---|---|---|"]
    for e in res["ranked"]:
        b = e["moved"]
        ys, xs = np.nonzero(g == b)
        areas = Counter(pg[y][x].replace("Land: ", "Ground ") for y, x in zip(ys, xs))
        where = ", ".join(f"{k} {v}" for k, v in areas.most_common(2))
        pk = "S%d" % e["stage"]
        inl = "light" if arrs["light"][b] == arrs["light"][e["rep"]] else ""
        inm = "medium" if arrs["medium"][b] == arrs["medium"][e["rep"]] else ""
        R.append(f"| {e['step']} | {pk} | {inl} {inm} | {e['px']} | {int(use[b])} | {where} | {b} > {e['rep']} |")
    (lib.OUT / "ranked.md").write_text("\n".join(R) + "\n")
    # ---- Color check: is a merged DMG pair also a near twin in the Color picture (same palette)?
    cg = lib.static().cg
    cpx = np.array(cg.world.px, dtype=np.int8)
    cpal = cg.world.pal

    def cblock(x, y):
        return cpx[y * 8:y * 8 + 8, x * 8:x * 8 + 8].reshape(-1)

    help_c = {"light": 0, "medium": 0}
    for e in res["ranked"]:
        b, a = e["moved"], e["rep"]
        cb = [(cpal[y][x], cblock(x, y)) for y, x in zip(*np.nonzero(g == b))]
        ca = [(cpal[y][x], cblock(x, y)) for y, x in zip(*np.nonzero(g == a))]
        ok = all(any(pb == pa_ and int((vb != va).sum()) <= e["stage"] for pa_, va in ca) for pb, vb in cb)
        if ok:
            help_c["light" if e["stage"] <= 3 else "medium"] += 1
    rows["color_help"] = help_c
    json.dump({"rows": rows, "per_area": per_area}, open(lib.OUT / "report.json", "w"), indent=1, default=int)
    print("\n".join(L))
    print()
    print("\n".join(A))
    print("Color: merged pairs that are also near twins (same palette, same px budget) in the Color picture:", help_c)


if __name__ == "__main__":
    main()
