#!/usr/bin/env python3
"""Maintainer tool (owner 11-11): take the round bush away from the foot of the tall zoo bamboo, on the Color and the DMG picture.

    python3 tools/dev/smap_zoo_bush.py            # edits assets/smap/world_c.png and world_d.png in place (idempotent)

The bush sat at cells (3..5, 59) and (3..5, 60).  It hid the foot of the middle stalk (cell 4) and bit into the right edge of the left stalk (cell 3) and the left edge of the right stalk (cell 5).
The stalk is drawn tile by tile (`..#-+#..` x7 and the node flare `.##-+##.`); cell (4, 58) is that tile, so row 59 of the three stalks gets it back (the three stalks then end together on one line, with
their node flare as the foot: a clean end, no cut-off outline) and row 60 is the plain ground (colour 0, the grass around it; there is no other ground to seam with: the cells next to the bush are blank).
Cell palettes are untouched (all `zoo`).  Everything outside those six cells stays byte-identical.
"""
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent.parent
FILES = [ROOT / "assets" / "smap" / "world_c.png", ROOT / "assets" / "smap" / "world_d.png"]
STALK_FOOT = [(3, 59), (4, 59), (5, 59)]
GROUND = [(3, 60), (4, 60), (5, 60)]
STALK_SRC = (4, 58)


def main():
    for f in FILES:
        im = Image.open(f)
        a = np.array(im)
        cell = lambda x, y: a[y * 8:y * 8 + 8, x * 8:x * 8 + 8]
        stalk = cell(*STALK_SRC).copy()
        before = a.copy()
        for c in STALK_FOOT:
            cell(*c)[:] = stalk
        for c in GROUND:
            cell(*c)[:] = 0
        n = int((before != a).sum())
        if n:
            o = Image.fromarray(a, "P")
            o.putpalette(im.getpalette())
            o.save(f)
        print(f.name, "pixels changed:", n)


if __name__ == "__main__":
    main()
