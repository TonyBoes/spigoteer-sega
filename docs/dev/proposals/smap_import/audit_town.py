"""python3 audit_town.py   (SMAP_BROKEN=1 for the broken state): is the approved town picture (smap_fountain/src/v_town_fx.py: the fountain working or broken, the dry tap, the tavern awning's ink end
of 8608d684) in the integrated map, pixel for pixel, on Color and DMG?  The picture is rebuilt from the module and compared with the map at the town's origin; prints the origin and the
differing pixels (the cells the roads and trees of the integrated map cover on purpose are listed, not hidden)."""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import mapctx as M  # noqa: E402
import v_town_fx as F  # noqa: E402

VAL = {"0": 0, "1": 1, "2": 2, "3": 3, "w": 1}
state = "broken" if F.BROKEN else "working"
for dmg in (False, True):
    pic = F.build(dmg)
    rows = pic.rows
    h, w = len(rows), len(rows[0])
    world = M.W.WORLD_DMG if dmg else M.W.WORLD
    best = None
    for oy in range(0, M.CH * 8 - h, 8):
        for ox in range(0, M.CW * 8 - w, 8):
            n = sum(1 for y in range(0, h, 4) for x in range(0, w, 4) if world.px[oy + y][ox + x] == VAL[rows[y][x]])
            if best is None or n > best[0]:
                best = (n, ox, oy)
    n, ox, oy = best
    diff = [(x, y) for y in range(h) for x in range(w) if world.px[oy + y][ox + x] != VAL[rows[y][x]]]
    cells = sorted({(x // 8, y // 8) for x, y in diff})
    print(state, "DMG" if dmg else "Color", "origin px", (ox, oy), "picture", (w, h), "differing pixels", len(diff), "cells", cells[:20])
    awning = [(x, y) for y in range(41, 47) for x in (95,) if world.px[oy + y][ox + x] != 3]
    print("   awning ink end x95 y41..46 missing:", awning)
