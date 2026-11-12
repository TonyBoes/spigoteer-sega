#!/usr/bin/env python3
"""Before | after sheets (DMG greys, big labels): one per venue at x4, the whole map at x1, the changed-pixel overlays, the busiest ground and road views.
    python3 docs/dev/proposals/smap_dmg_kit2/sheets.py     (writes png/ next to this file; run packages.py and report.py first)
Packages: LIGHT (3 px per tile at most), MEDIUM (ground up to 6 px, venues still 3), STRONG (everything up to 6 px).  Inside a venue MEDIUM = LIGHT."""
import json

import numpy as np
from PIL import Image

import lib
import merge
import render

PNG = lib.OUT / "png"
ORANGE, RED, PURPLE = (255, 140, 0), (225, 30, 30), (150, 40, 220)
VEN = ["Saloon", "Stadium", "Bistro", "Igloo", "Lodge", "Factory", "Rodeo", "Teahouse", "Zoo", "Space", "Town"]


def bbox(pg, name, margin=1):
    ys, xs = zip(*[(y, x) for y in range(lib.CH) for x in range(lib.CW) if pg[y][x] == name])
    return max(min(xs) - margin, 0), max(min(ys) - margin, 0), min(max(xs) + margin, lib.CW - 1), min(max(ys) + margin, lib.CH - 1)


def three_tone(old, light, medium, strong):
    """today dimmed; pixels light changes in orange, the extra ones medium changes in red, the extra ones strong changes in purple"""
    rgb = render.overlay(old, old)
    rgb[strong != old] = PURPLE
    rgb[medium != old] = RED
    rgb[light != old] = ORANGE
    return rgb


def crop(img, b):
    x0, y0, x1, y1 = b
    return img[y0 * 8:(y1 + 1) * 8, x0 * 8:(x1 + 1) * 8]


def counts_in(old, new, b):
    x0, y0, x1, y1 = b
    ch = (old != new)[y0 * 8:(y1 + 1) * 8, x0 * 8:(x1 + 1) * 8]
    return int(ch.reshape(y1 - y0 + 1, 8, x1 - x0 + 1, 8).any(axis=(1, 3)).sum()), int(ch.sum())


def grey3(a):
    return np.stack([render.grey(a)] * 3, -1)


def main():
    PNG.mkdir(exist_ok=True)
    rep = json.load(open(lib.OUT / "report.json"))["rows"]
    dm, sg, use, pin = merge.prepare()
    arrs = np.load(lib.OUT / "arrays.npz")
    base = render.new_world(dm, np.arange(len(sg)))
    img = {k: render.new_world(dm, arrs[k]) for k in ("light", "medium", "strong")}
    pg = lib.piece_grid()
    K = 4
    pal = Image.open(lib.ROOT / "assets" / "smap" / "world_d.png").getpalette()
    for k, v in img.items():                      # the three worlds as indexed DMG pictures (same 4 palette entries as assets/smap/world_d.png), for the owner's pick
        im = Image.fromarray(v, "P")
        im.putpalette(pal)
        im.save(PNG / f"world_d_{k}.png")
    for name in VEN:
        b = bbox(pg, name)
        o, l, s = crop(base, b), crop(img["light"], b), crop(img["strong"], b)
        m = crop(img["medium"], b)
        lc, sc = counts_in(base, img["light"], b), counts_in(base, img["strong"], b)
        pans = [render.panel(grey3(o), "TODAY", K, 40, sub=" "),
                render.panel(grey3(l), "LIGHT", K, 40, sub=f"{lc[1]} px in {lc[0]} cells"),
                render.panel(grey3(s), "STRONG", K, 40, sub=f"{sc[1]} px in {sc[0]} cells"),
                render.panel(three_tone(o, l, m, s), "CHANGED", K, 40, sub="orange light, purple strong")]
        im = render.stack([render.row(pans[:2], gap=12), render.row(pans[2:], gap=12)],
                          title=[name.upper(), "order: TODAY, LIGHT, STRONG, CHANGED", "MEDIUM = LIGHT inside venues"], size=44)
        p = PNG / f"venue_{name.lower()}_x4.png"
        im.save(p)
        print(p.name, im.size)
    # ---- whole map at x1: 2 x 2
    pans = [render.panel(grey3(base), "TODAY", 1, 40, sub=f"{rep['today']['tiles']} tiles"),
            render.panel(grey3(img["light"]), "LIGHT", 1, 40, sub=f"{rep['light']['tiles']} tiles, {rep['light']['px']} px"),
            render.panel(grey3(img["medium"]), "MEDIUM", 1, 40, sub=f"{rep['medium']['tiles']} tiles, {rep['medium']['px']} px"),
            render.panel(grey3(img["strong"]), "STRONG", 1, 40, sub=f"{rep['strong']['tiles']} tiles, {rep['strong']['px']} px")]
    im = render.stack([render.row(pans[:2], gap=14), render.row(pans[2:], gap=14)], title=["WHOLE MAP x1", "order: TODAY, LIGHT, MEDIUM, STRONG"], size=44)
    im.save(PNG / "whole_map_x1.png")
    print("whole_map_x1.png", im.size)
    ov = Image.fromarray(render.scale(three_tone(base, img["light"], img["medium"], img["strong"]), 2))
    im = render.stack([ov], title=["CHANGED PIXELS x2", "orange light, red extra in medium, purple extra in strong"], size=40)
    im.save(PNG / "whole_map_changed_x2.png")
    # ---- the busiest non-venue views (medium): 12 x 10 cell windows
    ch = (img["medium"] != base).reshape(lib.CH, 8, lib.CW, 8).sum(axis=(1, 3))
    venue = np.array([[pg[y][x] in VEN for x in range(lib.CW)] for y in range(lib.CH)])
    work = np.where(venue, 0, ch)
    picks = []
    for _ in range(6):
        best = None
        for y0 in range(lib.CH - 9):
            for x0 in range(lib.CW - 11):
                sc_ = int(work[y0:y0 + 10, x0:x0 + 12].sum())
                if best is None or sc_ > best[0]:
                    best = (sc_, x0, y0)
        picks.append(best)
        _, x0, y0 = best
        work[max(y0 - 4, 0):y0 + 14, max(x0 - 4, 0):x0 + 16] = 0
    rows = []
    for _, x0, y0 in picks:
        b = (x0, y0, x0 + 11, y0 + 9)
        o, l, m, s = (crop(base, b), crop(img["light"], b), crop(img["medium"], b), crop(img["strong"], b))
        rows.append(render.row([render.panel(grey3(o), f"TODAY  cells {x0},{y0}", 3, 30), render.panel(grey3(m), "MEDIUM", 3, 30),
                                render.panel(three_tone(o, l, m, s), "CHANGED", 3, 30)], gap=10))
    im = render.stack(rows, title=["GROUND, ROADS, WATER, MOUNTAINS", "the six busiest views. order: TODAY, MEDIUM, CHANGED"], size=40)
    im.save(PNG / "ground_views_x3.png")
    print("ground_views_x3.png", im.size)


if __name__ == "__main__":
    main()
