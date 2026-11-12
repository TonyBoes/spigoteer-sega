#!/usr/bin/env python3
"""Writes tools/dev/smap_dmg_tile_share.py: the MEDIUM package (owner pick 11-11, stadium lines kept) as a table of cells -> 8 x 8 blocks.
    python3 docs/dev/proposals/smap_dmg_kit2/export_patch.py       (run packages.py first; reads arrays.npz, the current assets/smap/world_d.png)
Every block in the table is the block of another cell of the same picture (the tile the cell now shares); the table only records which."""
import numpy as np

import lib
import merge
import render

HEAD = '''#!/usr/bin/env python3
"""Maintainer tool (owner 11-11, "medium except uneven line on stadium"): DMG tile sharing from today's art, the MEDIUM package of docs/dev/proposals/smap_dmg_kit2.

    python3 tools/dev/smap_dmg_tile_share.py            # edits assets/smap/world_d.png in place (idempotent); the Color picture is not touched

{n} cells of the DMG picture show the pixels of a near-identical cell instead of their own (ground, roads, water, mountains, decor up to 6 px per tile; every venue tile at most 3 px;
no sign letter, no animated tile; the stadium's roofline and lawn edge are left as drawn).  The table is CELLS: (x, y) -> eight rows of eight shade digits; every block in it is a
block that already exists elsewhere in the picture.  Re-running changes nothing.  Reproduce the table: docs/dev/proposals/smap_dmg_kit2/export_patch.py.
"""
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent.parent
FILE = ROOT / "assets" / "smap" / "world_d.png"
CELLS = {{
'''
TAIL = '''}


def main():
    im = Image.open(FILE)
    a = np.array(im)
    before = a.copy()
    for (x, y), rows in CELLS.items():
        a[y * 8:y * 8 + 8, x * 8:x * 8 + 8] = np.array([[int(c) for c in r] for r in rows], dtype=a.dtype)
    n = int((before != a).sum())
    if n:
        o = Image.fromarray(a, "P")
        o.putpalette(im.getpalette())
        o.save(FILE)
    print(FILE.name, "pixels changed:", n)


if __name__ == "__main__":
    main()
'''


def main():
    dm, sg, use, pin = merge.prepare()
    arrs = np.load(lib.OUT / "arrays.npz")
    arr = arrs["medium"]
    g = dm.grids[lib.G.NSTATE]
    px = np.array(dm.world.px, dtype=np.uint8)
    lines = []
    for y in range(lib.CH):
        for x in range(lib.CW):
            t = int(g[y, x])
            if arr[t] != t:
                blk = sg[int(arr[t])].reshape(8, 8)
                if not (px[y * 8:y * 8 + 8, x * 8:x * 8 + 8] == blk).all():
                    lines.append(f"    ({x}, {y}): {tuple(''.join(str(int(v)) for v in r) for r in blk)!r},")
    out = HEAD.format(n=len(lines)) + "\n".join(lines) + "\n" + TAIL
    p = lib.ROOT / "tools" / "dev" / "smap_dmg_tile_share.py"
    p.write_text(out)
    print(p, len(lines), "cells")


if __name__ == "__main__":
    main()
