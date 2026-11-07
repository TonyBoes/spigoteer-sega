"""Unique tiles of the town block and of the whole map (DMG: pixels; Color: pixels + palette, flips not merged), read only.
python3 -I run.py OPT OUT metrics.py   (run.py puts the A5 scratch on the path and swaps the fountain)"""
import json
import sys
from pathlib import Path

import world2 as W

wd, wc = W.WORLD_DMG, W.WORLD
CW, CH = W.CW, W.CH
TX, TY = 31, 19


def cell(w, x, y):
    return bytes(ord(str(w.px[y * 8 + j][x * 8 + i])[0]) for j in range(8) for i in range(8))


dmg = {(x, y): cell(wd, x, y) for y in range(CH) for x in range(CW)}
col = {(x, y): (cell(wc, x, y), wc.pal[y][x]) for y in range(CH) for x in range(CW)}
town = [(x, y) for y in range(TY, TY + 9) for x in range(TX, TX + 12)]
rest = [(x, y) for y in range(CH) for x in range(CW) if (x, y) not in set(town)]
res = {
    "dmg_map": len(set(dmg.values())), "color_map": len(set(col.values())),
    "dmg_town_cells_unique": len({dmg[c] for c in town}), "color_town_cells_unique": len({col[c] for c in town}),
    "dmg_town_new_vs_rest": len({dmg[c] for c in town} - {dmg[c] for c in rest}),
    "color_town_new_vs_rest": len({col[c] for c in town} - {col[c] for c in rest}),
}
print("METRICS", json.dumps(res))
if len(sys.argv) > 2:
    import hashlib
    sig = {f"{x},{y}": [hashlib.md5(dmg[(x, y)]).hexdigest()[:8], hashlib.md5(col[(x, y)][0]).hexdigest()[:8], col[(x, y)][1]] for (x, y) in town}
    Path(sys.argv[2]).joinpath("cells.json").write_text(json.dumps(sig))
    Path(sys.argv[2]).joinpath("metrics.json").write_text(json.dumps(res, indent=1))
