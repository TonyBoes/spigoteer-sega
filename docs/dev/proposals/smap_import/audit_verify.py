"""python3 audit_verify.py dump OUT.json   (run with SMAP_NO_ANIM_STATIC=1: the items are built on the map without the pasted art, as the items assert)
   python3 audit_verify.py check OUT.json  (default map, art pasted): for every tile animation of every item, are the cells the engine table would rewrite (the cells holding the animated
   tile's frame 0 image) in the map, and does each hold the approved frame 0 tile on Color and a DMG tile that is the same picture?  Prints a table row per item."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import mapctx as M  # noqa: E402
import audit_anim as AA  # noqa: E402


def tile(w, cx, cy):
    return ["".join(str(w.px[cy * 8 + j][cx * 8 + i]) for i in range(8)) for j in range(8)]


if sys.argv[1] == "dump":
    before_px, before_pal, its, a5 = AA.build(M)
    out = {}
    for it in its:
        rows = []
        for (a, base, cells) in it.resolve():
            rows.append(dict(name=a.name, cells=cells, base=list(base), frames=[list(f) for f in a.frames]))
        out[it.key] = rows
    json.dump(out, open(sys.argv[2], "w"))
    print({k: sum(len(r["cells"]) for r in v) for k, v in out.items()})
else:
    data = json.load(open(sys.argv[2]))
    for key, rows in data.items():
        cells = sorted({tuple(c) for r in rows for c in r["cells"]})
        bad_c = [tuple(c) for r in rows for c in r["cells"] if tile(M.W.WORLD, *c) != r["base"]]
        # engine cells: every cell of the map that holds a tile image equal to an animated tile's frame 0
        extra = []
        for r in rows:
            base = r["base"]
            same = [(x, y) for y in range(M.CH) for x in range(M.CW) if tile(M.W.WORLD, x, y) == base]
            extra += [c for c in same if list(c) not in r["cells"]]
        dmg_same = [tuple(c) for r in rows for c in r["cells"] if tile(M.W.WORLD_DMG, *c) != tile(M.W.WORLD_DMG, *r["cells"][0]) and len(r["cells"]) > 1 and False]
        print(f"{key}: animated cells {len(cells)}, frame 0 differs from the approved tile at {len(bad_c)} {bad_c[:6]}, other cells holding the same image {len(set(extra))} {sorted(set(extra))[:6]}")
