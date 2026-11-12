#!/usr/bin/env python3
"""Proposal (owner 11-11, NOT imported): rebuild the tall zoo bamboo from the tiles the map's big bamboo clump already uses.

    python3 docs/dev/proposals/smap_zoo_bamboo/smap_zoo_bamboo_opt.py 1            # writes build_1/world_c.png and world_d.png beside this script
    python3 docs/dev/proposals/smap_zoo_bamboo/smap_zoo_bamboo_opt.py 2
    python3 docs/dev/proposals/smap_zoo_bamboo/smap_zoo_bamboo_opt.py 1 --apply     # the patch: edits assets/smap/world_c.png and world_d.png in place (idempotent)

Option 1: the clump's two columns (3 stalks, 16 px wide) stand on the zoo cells x = 3..4 (the grove's left edge); option 2: on x = 4..5 (the gate side).
Both: top row 54, four middle rows 55..58 (middle, foot, middle, foot tile), foot row 59 (the grove's old foot line); the stalk tops land about where the old ones were (old 429 / 440 / 447 px, new 432 / 438 / 440).
The clump is the cells (13..14, 50..52): top T (13,50) (14,50), middle M (13,51) (14,51), foot F (13,52) (14,52): six tiles, each used once on the map today, so the grove needs no tile of its own,
and the old grove's own tiles (and the bush's) leave the map.  The cells (3..5, 53..60) are cleared first, so this also covers the bush's area (it needs no smap_zoo_bush.py first).
Only those cells of world_c.png and world_d.png change; the cell palettes (all `zoo`) do not.  The tiles are copied from the clump cells of the same picture (copying finished tiles; no pixel is drawn).
"""
import argparse
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[4]
CLUMP_X, CLUMP_Y = 13, 50       # the big clump: cells (13..14, 50..52)
ROWS = {"top": 54, "foot": 59}
MIDS = ("mid", "foot", "mid", "foot")      # the middle rows alternate the clump's middle tile and its foot tile (fewer leaf ticks than four middles: the middle tile carries a leaf stub)
CLEAR = [(x, y) for y in range(53, 61) for x in (3, 4, 5)]
X0 = {1: 3, 2: 4}


def build(a, opt):
    cell = lambda x, y: a[y * 8:y * 8 + 8, x * 8:x * 8 + 8]
    src = {k: [cell(CLUMP_X + i, CLUMP_Y + r).copy() for i in (0, 1)] for k, r in (("top", 0), ("mid", 1), ("foot", 2))}
    for c in CLEAR:
        cell(*c)[:] = 0
    x0 = X0[opt]
    for i in (0, 1):
        cell(x0 + i, ROWS["top"])[:] = src["top"][i]
        for y, k in zip((55, 56, 57, 58), MIDS):
            cell(x0 + i, y)[:] = src[k][i]
        cell(x0 + i, ROWS["foot"])[:] = src["foot"][i]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("opt", type=int, choices=(1, 2))
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--src", default=str(ROOT / "assets" / "smap"))
    args = ap.parse_args()
    src = Path(args.src)
    out = src if args.apply else Path(__file__).resolve().parent / f"build_{args.opt}"
    out.mkdir(parents=True, exist_ok=True)
    for name in ("world_c.png", "world_d.png"):
        im = Image.open(src / name)
        a = np.array(im)
        before = a.copy()
        build(a, args.opt)
        o = Image.fromarray(a, "P")
        o.putpalette(im.getpalette())
        o.save(out / name)
        print(name, "pixels changed:", int((before != a).sum()))


if __name__ == "__main__":
    main()
