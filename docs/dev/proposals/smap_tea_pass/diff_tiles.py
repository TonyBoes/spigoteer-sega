"""python3 -I diff_tiles.py : which cells of the teahouse box make tiles that the default map has nowhere (new) and which default tiles the pass stops using (lost). DMG data set and Color."""
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import swap  # noqa: E402,F401
sys.path.insert(0, str(HERE.parent / "smap_import"))
import mapctx as M  # noqa: E402

import importlib.util
import os

grids = {}
for tag, pas in (("before", False), ("after", True)):
    for d in (True, False):
        # build a world with / without the pass by re-reading the venue module directly: cell tiles of the picture only
        pass


def tiles_of(modname_path, dmg):
    spec = importlib.util.spec_from_file_location("vt", modname_path)
    mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(HERE.parents[3] / "tools" / "smap_world"))
    spec.loader.exec_module(mod)
    rows = mod.build(dmg=dmg).out()
    return {(i, j): tuple(tuple(int(ch) for ch in rows[j * 8 + y][i * 8:i * 8 + 8]) for y in range(8)) for j in range(7) for i in range(12)}


old = HERE.parents[3] / "tools" / "smap_world" / "v_tea.py"
new = HERE / "v_tea_pass.py"
for dmg in (True, False):
    # whole-map tile multiset without the teahouse box: ground truth of "tiles that exist elsewhere"
    g, _ = M.grid(dmg)
    outside = Counter()
    for cy in range(M.CH):
        for cx in range(M.CW):
            if 24 <= cx < 36 and 55 <= cy < 62:
                continue
            outside[tuple(tuple(g[cy * 8 + j][cx * 8:cx * 8 + 8]) for j in range(8))] += 1
    a, b = tiles_of(old, dmg), tiles_of(new, dmg)
    # the map cell uses ground (index 0) the same as the picture here; blank cells equal the all-0 tile
    print("DMG" if dmg else "Color", "box-only tiles before:", len({t for t in a.values() if t not in outside}), " after:", len({t for t in b.values() if t not in outside}))
    for j in range(7):
        row = []
        for i in range(12):
            ta, tb = a[(i, j)], b[(i, j)]
            row.append(("=" if ta == tb else ("n" if tb not in outside else "s")))
        print("   ", "".join(row), "   (= same, n new tile, s changed to a tile that exists elsewhere)")
