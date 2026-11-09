#!/usr/bin/env python3
"""Maintainer tool (owner 11-08 Q4 / 11-09): take the cream wedges out of the two Color road bends at the bottom of the map.

    python3 tools/dev/smap_wedge_fix.py            # edits assets/smap/world.json and world_c.png in place (idempotent)

The bends at cells (35..37, 44..46) and (50..52, 44..46) are drawn with `town1`, whose colour 0 is the paving's cream: the ground outside / inside the curve showed cream instead of grass.
The ground pixels are the 4-connected runs of colour 0 that hold a 2 x 2 block (the road's cream edge line is 1 px thick); they stay colour 0 and the cells change to a palette whose colour 0 is grass.
  Cells that hold only ground (and the kerb tip's one dark pixel): (37,46) and (50,46): the `grass` palette, which every view already holds, draws them exactly as before except the tip pixel's dark
  ((16,32,24) for (32,24,40)).  No palette is added.
  The other wedge cells also hold the road's cream edge line and dots (the old colour 0 inside the road).  A grass-0 palette cannot draw them cream, so they take `town1@g` (grass, fill, kerb,
  dark: no new palette) with the edge line and dots drawn as road fill (colour LINE) and ground pixels left as colour 0 (grass).  HALF=1 skips these cells (the half fix).
Only world_c.png and the cell palettes change: the DMG picture is untouched (world_d.png; the DMG palettes are not read from the cell palettes).
"""
import json
import os
from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent.parent
JS, PNG = ROOT / "assets" / "smap" / "world.json", ROOT / "assets" / "smap" / "world_c.png"
BENDS = [(35, 37, 44, 46), (50, 52, 44, 46)]          # (cell x0, x1, y0, y1)
HALF = os.environ.get("HALF") == "1"      # only the two all-ground cells (no edge line to draw): the half fix
LINE = int(os.environ.get("LINE", "1"))


def main():
    js = json.loads(JS.read_text())
    if js["cell_pal"][46][37] == chr(48 + js["pal_names"].index("grass")):
        print("already applied")
        return
    im = Image.open(PNG)
    px = np.array(im)
    names = js["pal_names"]
    t1 = names.index("town1")
    cp = [list(r) for r in js["cell_pal"]]
    cells = [(x, y) for (x0, x1, y0, y1) in BENDS for y in range(y0, y1 + 1) for x in range(x0, x1 + 1) if ord(cp[y][x]) - 48 == t1]
    m = np.zeros(px.shape, bool)
    for (x, y) in cells:
        m[y * 8:y * 8 + 8, x * 8:x * 8 + 8] = px[y * 8:y * 8 + 8, x * 8:x * 8 + 8] == 0
    ground = np.zeros(px.shape, bool)
    seen = np.zeros(px.shape, bool)
    H, W = px.shape
    for sy in range(H):
        for sx in range(W):
            if m[sy, sx] and not seen[sy, sx]:
                q, pts = deque([(sx, sy)]), []
                seen[sy, sx] = 1
                while q:
                    x, y = q.popleft()
                    pts.append((x, y))
                    for a, b in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                        if 0 <= a < W and 0 <= b < H and m[b, a] and not seen[b, a]:
                            seen[b, a] = 1
                            q.append((a, b))
                ps = set(pts)
                if any((x + 1, y) in ps and (x, y + 1) in ps and (x + 1, y + 1) in ps for (x, y) in pts):
                    for (x, y) in pts:
                        ground[y, x] = True
    changed = []
    out = px.copy()
    gpal = names.index("town1@g")
    for (x, y) in cells:
        sl = (slice(y * 8, y * 8 + 8), slice(x * 8, x * 8 + 8))
        if not ground[sl].any():
            continue
        c = px[sl].copy()
        o = c.copy()
        if not ((c == 0) & ~ground[sl]).any():           # only ground (and the dark tip): the `grass` palette (every view has it) draws it as before, the tip's dark is a hair different
            cp[y][x] = chr(48 + names.index("grass"))
            changed.append((x, y))
            continue
        if HALF:
            continue                      # west bend mixed cells: no palette to give them, see the commit message
        o[(c == 0) & ~ground[sl]] = LINE          # the road's own cream pixels (its edge line and dots) cannot be cream in a grass-0 palette: they take the fill colour
        cp[y][x] = chr(48 + gpal)
        out[sl] = o
        changed.append((x, y))
    js["cell_pal"] = ["".join(r) for r in cp]
    JS.write_text(json.dumps(js, indent=0, separators=(",", ":")) + "\n")
    if (out != px).any():
        o = Image.fromarray(out, "P")
        o.putpalette(im.getpalette())
        o.save(PNG)
    print("retyped", sorted(changed, key=lambda k: (k[1], k[0])))


if __name__ == "__main__":
    main()
