"""Review sheets of the ranked merges: each merge shows the tile that is replaced in its map context (3x3 cells, x5), before | after | changed pixels.
    python3 review.py [first last [only_venues]]   writes out/review_<n>.png under the worktree's out/ (scratch)"""
import json
import sys
from collections import Counter

import numpy as np
from PIL import Image, ImageDraw

import lib
import merge
import render

K = 4
OUTPNG = False       # True: write the sheets into png/ as ranked_merges_N.png (python3 review.py 1 999 --png)


def context(px_img, cx, cy):
    """3x3 cells around (cx, cy), clamped"""
    x0 = min(max(cx - 1, 0), lib.CW - 3)
    y0 = min(max(cy - 1, 0), lib.CH - 3)
    return px_img[y0 * 8:y0 * 8 + 24, x0 * 8:x0 * 8 + 24], (cx - x0, cy - y0)


def entries(res, dm, use, arr_final, pg):
    g = dm.grids[lib.G.NSTATE]
    out = []
    for e in res["ranked"]:
        b = e["moved"]
        ys, xs = np.nonzero(g == b)
        areas = Counter(pg[y][x] for y, x in zip(ys, xs))
        out.append(dict(e, uses=int(use[b]), areas=areas, cells=list(zip(xs.tolist(), ys.tolist())), sig_a=dm.sigs[e["rep"]]))
    return out


def sheet(ents, base, new, title, per_row=3):
    panels = []
    for e in ents:
        pick = None
        for c in e["cells"]:                                  # prefer a venue cell
            pick = c
            break
        cx, cy = pick
        one = base.copy()
        sa = np.array(list(e["sig_a"]), dtype=np.uint8).reshape(8, 8)
        for (xx, yy) in e["cells"]:
            one[yy * 8:yy * 8 + 8, xx * 8:xx * 8 + 8] = sa
        b, _ = context(base, cx, cy)
        a, _ = context(one, cx, cy)
        ov = render.overlay(b, a, dim=True)
        ar = ", ".join(f"{k[:9]} {v}" for k, v in e["areas"].most_common(1))
        lab = f"#{e['step']} S{e['stage']} {e['px']}px x{e['uses']} t{e['moved']}>{e['rep']} {ar}"
        parts = [render.panel(np.stack([render.grey(b)] * 3, -1), "before", K, 18),
                 render.panel(np.stack([render.grey(a)] * 3, -1), "after", K, 18),
                 render.panel(ov, "diff", K, 18)]
        r = render.row(parts, gap=6, bg=(255, 255, 255))
        im = Image.new("RGB", (r.width, r.height + 30), (255, 255, 255))
        d = ImageDraw.Draw(im)
        d.text((4, 2), lab, fill=(0, 0, 120), font=render.font(15))
        im.paste(r, (0, 30))
        panels.append(im)
    rows = []
    for i in range(0, len(panels), per_row):
        rows.append(render.row(panels[i:i + per_row], gap=8))
    return render.stack(rows, title=title, size=26)


def main():
    first = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    last = int(sys.argv[2]) if len(sys.argv) > 2 else 60
    venues_only = "--venues" in sys.argv
    global OUTPNG
    OUTPNG = "--png" in sys.argv
    res = json.load(open(lib.OUT / "results.json"))
    arrs = np.load(lib.OUT / "arrays.npz")
    dm, sg, use, pin = merge.prepare()
    base = render.new_world(dm, np.arange(len(sg)))
    new = render.new_world(dm, arrs["strong"])
    pg = lib.piece_grid()
    ents = entries(res, dm, use, arrs["strong"], pg)
    ents = [e for e in ents if first <= e["step"] <= last]
    if venues_only:
        ents = [e for e in ents if any(not k.startswith(("Land", "Roads")) for k in e["areas"])]
    n = 0
    for i in range(0, len(ents), 24):
        im = sheet(ents[i:i + 24], base, new, f"merges {ents[i]['step']} to {ents[min(i + 23, len(ents) - 1)]['step']}")
        p = (lib.OUT / "png") if OUTPNG else (lib.ROOT / "out")
        p = p / f"ranked_merges_{n + 1}.png" if OUTPNG else p / f"review_{first}_{n}.png"
        im.save(p)
        print(p, im.size)
        n += 1


if __name__ == "__main__":
    main()
