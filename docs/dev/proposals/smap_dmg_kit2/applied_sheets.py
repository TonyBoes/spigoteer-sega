#!/usr/bin/env python3
"""Sheets of what was APPLIED to assets/smap/world_d.png (medium, stadium lines kept): the stadium before | after at x4 and the whole-map changed-pixels overlay.
    python3 docs/dev/proposals/smap_dmg_kit2/applied_sheets.py       (before = the committed world_d.png of HEAD, after = the working copy)"""
import subprocess
from io import BytesIO

import numpy as np
from PIL import Image

import lib
import render

PNG = lib.OUT / "png"
RED = (225, 30, 30)


def main():
    old = np.array(Image.open(BytesIO(subprocess.run(["git", "show", "HEAD:assets/smap/world_d.png"], cwd=lib.ROOT, capture_output=True, check=True).stdout)))
    new = np.array(Image.open(lib.ROOT / "assets" / "smap" / "world_d.png"))
    ch = old != new
    cells = ch.reshape(lib.CH, 8, lib.CW, 8).any(axis=(1, 3))
    print("applied:", int(ch.sum()), "px in", int(cells.sum()), "cells")
    g3 = lambda a: np.stack([render.grey(a)] * 3, -1)
    # stadium: cells 0..11 x 0..8 (the venue and a cell around it)
    b = (0, 0, 11, 8)
    crop = lambda a: a[b[1] * 8:(b[3] + 1) * 8, b[0] * 8:(b[2] + 1) * 8]
    o, n = crop(old), crop(new)
    st = int((o != n).sum())
    rgb = render.overlay(o, n)
    pans = [render.panel(g3(o), "BEFORE", 4, 40, sub=" "), render.panel(g3(n), "AFTER", 4, 40, sub=f"{st} px changed")]
    im = render.stack([render.row(pans, gap=12)], title=["STADIUM x4", "order: BEFORE, AFTER"], size=44)
    im.save(PNG / "applied_stadium_x4.png")
    # whole map overlay
    ov = render.overlay(old, new)
    ov[ch] = RED
    im = render.stack([Image.fromarray(render.scale(ov, 2))], title=["APPLIED CHANGES x2", f"{int(ch.sum())} px in {int(cells.sum())} cells, red"], size=40)
    im.save(PNG / "applied_changed_x2.png")
    print("stadium view px:", st)


if __name__ == "__main__":
    main()
