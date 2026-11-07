"""Dumps the APPROVED pieces as cell lists (tile rows of digits + palette name per 8 x 8 cell) for mapctx.py to paste over the A5 world:
  stadium  smap_stadium/src/park_s2.py  (option 2, final 2, wavy flag; frames 0..2)           pasted at cell (1, 1), every cell
  igloo    smap_venue_redesign/src/igloo_1.py  (option 1, COCOA, chimney, penguin)            pasted at (50, 5), non-blank cells
  mountain smap_hangar/src/sheet_h9.py build('n')  (round 4i: hangar, runway strip, jet)      pasted at (9, 36), every cell
  cow      smap_milkbar/src/cow_a5.py build(3, 'A')  (round 4h/4i milk bar, pasture, lawn cow) pasted at (50, 47), non-blank cells
Run (plain python, each branch's modules import each other and their own common.py):  python3 r4dump.py KIND scenes/KIND.json
Only reads the typed pieces; nothing is drawn here."""
import json
import sys
from pathlib import Path

kind = sys.argv[1]
P = Path(__file__).resolve().parents[1]
SRC = {"stadium": "smap_stadium", "igloo": "smap_venue_redesign", "mountain": "smap_hangar", "cow": "smap_milkbar"}[kind]
sys.path.insert(0, str(P / SRC / "src"))
import common as C  # noqa: E402


def cells(c):
    out = {}
    for (i, j), (t, p) in C.cells(c).items():
        out[f"{i},{j}"] = ["".join(t[k] for k in range(8)) if False else list(t), C.W.MERGE.get(p, p)]
    return out


res = {"kind": kind}
if kind == "stadium":
    import park_s2 as M
    cs = [M.build(True, k) for k in range(3)]
    res.update(at=[1, 1], mode="all", w=cs[0].w // 8, h=cs[0].h // 8, frames=[cells(c) for c in cs])
elif kind == "igloo":
    import igloo_1 as M
    c = M.build()
    res.update(at=[50, 5], mode="nonblank", w=c.w // 8, h=c.h // 8, frames=[cells(c)])
elif kind == "mountain":
    import jet2_h
    import mtn_h as M
    import strip6_h
    c = M.build(which="h2e", runway=False, raised=True)
    strip6_h.strip6(c)
    C.paste(c, 8, 57, jet2_h.pose("L"))
    res.update(at=[9, 36], mode="all", w=c.w // 8, h=c.h // 8, frames=[cells(c)])
else:
    import cow_a5 as M
    c = M.build(3, "A")
    res.update(at=[50, 47], mode="nonblank", w=c.w // 8, h=c.h // 8, frames=[cells(c)])
names = sorted({v[1] for f in res["frames"] for v in f.values()})
res["colors"] = {n: [list(map(int, col)) for col in C.P.get(n)] for n in names}
Path(sys.argv[2]).write_text(json.dumps(res))
print(kind, res["w"], res["h"], names)
