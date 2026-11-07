"""Dumps the APPROVED pieces (each at the commit the import brief names) as cell lists for mapctx.py to paste over the A5 world.
Adapted from smap_anim/r4dump.py (same cell-list format, same pieces) with two pieces changed to their final approved state:
  stadium  smap_stadium/src/park_map.py    BLEND (8950c018): the final-2 stadium + wavy flag (frames 0..2) with the symmetric foul-line edit  at (1, 1)
  igloo    smap_venue_redesign/src/igloo_1.py  option 1 (COCOA sign, chimney, penguin)                                                       at (50, 5)
  mountain smap_hangar/src/sheet_h9.py build('n')   round 4i, jet nudged 4 px right (same composition as r4dump)                              at (9, 36)
  cow      smap_milkbar/src/cow_a5.py build_final()  milk bar final: sign B on base, raised 4 px and 4 px left; 104 x 184, at (49, 47)
Run (plain python, each piece's modules import their own common.py):  python3 -I dump_scenes.py KIND scenes/KIND.json
Only reads the typed pieces; nothing is drawn here."""
import json
import sys
from pathlib import Path

kind = sys.argv[1]
P = Path(__file__).resolve().parents[1]
ROOT = P.parents[2]
SRC = {"stadium": "smap_stadium", "igloo": "smap_venue_redesign", "mountain": "smap_hangar", "cow": "smap_milkbar",
       "range_a": "smap_venue_redesign3", "range_b": "smap_venue_redesign3", "range_c": "smap_venue_redesign3"}[kind]
sys.path.insert(0, str(ROOT / "tools/smap_world"))
if kind == "cow":                                            # smap_milkbar/src/a5env.py hard-codes another worktree: stand in for it (it only sets the A5 import paths)
    import types
    a = types.ModuleType("a5env")
    for p in (ROOT / "docs/dev/proposals/smap_layout_a5/src", ROOT / "tools/smap_world", P / SRC / "src"):
        sys.path.insert(0, str(p))
    sys.modules["a5env"] = a
sys.path.insert(0, str(P / SRC / "src"))
import common as C  # noqa: E402


def cells(c):
    return {f"{i},{j}": [list(t), C.W.MERGE.get(p, p)] for (i, j), (t, p) in C.cells(c).items()}


res = {"kind": kind}
if kind == "stadium":
    import park_map as M
    cs = [M.build(True, k) for k in range(3)]
    res.update(at=[1, 1], mode="nonblank", w=cs[0].w // 8, h=cs[0].h // 8, frames=[cells(c) for c in cs])
elif kind == "igloo":
    import igloo_1 as M
    c = M.build()
    res.update(at=[50, 5], mode="nonblank", w=c.w // 8, h=c.h // 8, frames=[cells(c)])
elif kind == "mountain":
    import sheet_h9 as M
    c = M.build("n")
    res.update(at=[9, 36], mode="all", w=c.w // 8, h=c.h // 8, frames=[cells(c)])
elif kind.startswith("range_"):
    import mtn_vert as M
    # round 3 range peak (owner 11-06) composed for the A5 layout's three range areas (cells x, y; px w, h).  Peak places in px inside the area, pasted back (higher) to front (lower):
    # two tiers where the area is 5 rows high (the front tier stands in front of the gaps of the back tier), one staggered row (8 px up / down) where it is 4 rows.
    AREAS = {"range_a": ((17, 0), 120, 32, False, [(0, 8), (24, 0), (48, 8), (72, 0), (88, 8)]),
             "range_b": ((34, 0), 112, 40, True, [(16, 0), (48, 0), (80, 0), (0, 16), (32, 16), (64, 16)]),
             "range_c": ((48, 0), 128, 40, True, [(0, 0), (32, 0), (64, 0), (96, 0), (16, 16), (48, 16), (80, 16)])}
    at, w, h, snow, places = AREAS[kind]
    c = M.stack(sorted(places, key=lambda p: (p[1], p[0])), w, h, snow)
    res.update(at=list(at), mode="nonblank", w=c.w // 8, h=c.h // 8, frames=[cells(c)])
else:
    import cow_a5 as M
    c = M.build_final()
    res.update(at=[49, 47], mode="nonblank", w=c.w // 8, h=c.h // 8, frames=[cells(c)])
names = sorted({v[1] for f in res["frames"] for v in f.values()})
res["colors"] = {n: [list(map(int, col)) for col in C.P.get(n)] for n in names}
Path(sys.argv[2]).write_text(json.dumps(res))
print(kind, res["w"], res["h"], names)
