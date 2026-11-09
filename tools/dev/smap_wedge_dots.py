#!/usr/bin/env python3
"""Maintainer tool (owner 11-09): give the Color road bends' wedge cells their cream dots and edge line back, with the ground still grass.

    python3 tools/dev/smap_wedge_dots.py            # edits assets/smap/world.json and world_c.png in place (idempotent); run after smap_wedge_fix.py

`town1@g` = [grass, peach, lilac, near-black] drew those cells' cream road pixels as road fill (smap_wedge_fix.py).  Near-black (colour 3) is used by only 36 of the 104 `town1@g` cells (the 30 town-front
cells and six lone one-pixel kerb tips); the others never use it.  A new palette `town1@w` = [grass, peach, lilac, cream] draws the bend cells exactly as the straight road is drawn: the cream pixels are
colour 3 (an invisible re-index) and the ground stays colour 0.
A view must never hold both `town1@g` and `town1@w` besides the other palettes (8 hardware slots; the generator checks every real view and the hand-overs), so `town1@w` replaces `town1@g`
everywhere except where a real view needs both: the town front (rows 19..23, the 30 near-black cells), the cells around it (x 23..46, y <= 35: 12 no-near-black cells, they stay `town1@g`) and the bend cell
(37,44), whose view (the top road at the town front down to the bend) would need a 9th palette plus a second palette on the lead line: it keeps `town1@g` (its dots stay the fill colour).
The six lone near-black kerb tip pixels (colour 3 in a corner of (50,28), (0,29), (63,29), (63,45), (0,63), (63,63)) are redrawn as lilac (colour 2, the kerb's own colour) in `town1@w`.
Only world_c.png and the cell palettes change: the DMG picture is untouched.
"""
import json
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent.parent
JS, PNG = ROOT / "assets" / "smap" / "world.json", ROOT / "assets" / "smap" / "world_c.png"
ORIG = "ed4b66c0:assets/smap/world_c.png"          # the picture before smap_wedge_fix.py drew the road's cream pixels as fill
BEND_CELLS = [(37, 44), (37, 45), (36, 46), (35, 46), (50, 44), (50, 45), (51, 46), (52, 46)]
STAY = {(37, 44), (0, 27), (0, 28), (0, 29), (1, 29), (2, 29)}      # (37,44) see above; the five at the west edge keep town1@g so it is resident when a walk leaves the town front westward (no palette write there)


def erase_dots():
    """Owner 11-09: the one near-black pixel in the corner of (37,46) and (50,46) (plain grass cells, a leftover of the old square corner) is erased, in the Color and the DMG picture."""
    # DMG: only (50,46).  Erasing (37,46)'s makes the blank tile fill 240 cells of the 22 x 20 window at (22..43, 32..51) (the cap is 239: the engine keeps 0xF0.. of a use count free).
    for f, cells in ((PNG, ((37, 46), (50, 46))), (PNG.with_name("world_d.png"), ((50, 46),))):
        im = Image.open(f)
        a = np.array(im)
        n = 0
        for (x, y) in cells:
            c = a[y * 8:y * 8 + 8, x * 8:x * 8 + 8]
            n += int((c == 3).sum())
            c[c == 3] = 0
        if n:
            o = Image.fromarray(a, "P")
            o.putpalette(im.getpalette())
            o.save(f)
        print(f.name, "dot pixels erased:", n)


def main():
    erase_dots()
    js = json.loads(JS.read_text())
    names = js["pal_names"]
    if "town1@w" in names:
        print("already applied")
        return
    tg = names.index("town1@g")
    px = np.array(Image.open(PNG))
    im = Image.open(PNG)
    orig = np.array(Image.open(__import__("io").BytesIO(subprocess.check_output(["git", "show", ORIG], cwd=ROOT))))
    cp = [list(r) for r in js["cell_pal"]]
    cells = [(x, y) for y in range(js["ch"]) for x in range(js["cw"]) if ord(cp[y][x]) - 48 == tg]
    sl = lambda x, y: (slice(y * 8, y * 8 + 8), slice(x * 8, x * 8 + 8))
    use3 = [c for c in cells if (px[sl(*c)] == 3).any()]
    front = [c for c in use3 if 19 <= c[1] <= 23 and 23 <= c[0] <= 34]
    keep = lambda c: 23 <= c[0] <= 46 and c[1] <= 35
    move = [c for c in cells if c not in front and not keep(c) and c not in STAY]
    names.append("town1@w")
    w = names.index("town1@w")
    t1, g = js["pal_rgb"]["town1"], js["pal_rgb"]["town1@g"]
    js["pal_rgb"]["town1@w"] = [g[0], g[1], g[2], t1[0]]
    out = px.copy()
    tips, dots = [], []
    for (x, y) in move:
        cp[y][x] = chr(48 + w)
        s = sl(x, y)
        if (x, y) in BEND_CELLS:
            m = (orig[s] == 0) & (px[s] == 1)       # the road's cream pixels that were drawn as fill
            out[s][m] = 3
            dots.append((x, y, int(m.sum())))
        else:
            m = px[s] == 3
            out[s][m] = 2                           # a lone kerb tip's near-black pixel: lilac
            if m.any():
                tips.append((x, y))
    js["cell_pal"] = ["".join(r) for r in cp]
    JS.write_text(json.dumps(js, indent=0, separators=(",", ":")) + "\n")
    o = Image.fromarray(out, "P")
    o.putpalette(im.getpalette())
    o.save(PNG)
    print("town1@w cells", len(move), "bend cells with dots", dots, "tips redrawn", tips)


if __name__ == "__main__":
    main()
