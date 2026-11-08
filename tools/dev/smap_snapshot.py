#!/usr/bin/env python3
"""Maintainer tool (owner decision Q113 / Q115 A' / Q117 B, 2026-11-07): freeze the INTEGRATED story map into assets/smap/, the data tools/gen_smap_world.py builds the ROM from.

    python3 tools/dev/smap_snapshot.py            # rebuilds assets/smap/world_c.png, world_d.png, world.json

The integrated map is built by the stage 1 proposal pipeline (docs/dev/proposals/smap_import/mapctx.py on the scratch src/ of smap_layout_a5): the A5 layout with the owner's pick A'
(four long bends at r32, the others r24 with trims), mountain B with the cave and the approved falls, the animation art's static tiles, light DMG water, the milk bar, the stadium BLEND,
the fountain, the airbase, the igloo and the teahouse pass.  Run docs/dev/proposals/smap_layout_a5/mk_src.py + mk_a5.py and smap_import/dump_scenes.py first (they write the untracked
scratch src/ and scenes/ that mapctx reads).  The build itself never needs any of that: it reads the snapshot.

Output (read by tools/smap_world/world_snap.py):
  assets/smap/world_c.png    the Color data set's pixels, indexed 0..3, 512 x 560
  assets/smap/world_d.png    the DMG data set's pixels (the hand-trimmed set: light water)
  assets/smap/world.json     the cell palettes (indices into pal_names), the 22 palettes' colours, the stops and legs, the venues' cells, and the REPAIR cells: the fountain's broken
                             state (shown until the story repairs it: the cells differ from the working fountain in both data sets)

THE TEAHOUSE SWAP POINT is the one line TEA_ART below: the module that draws the teahouse (docs/dev/proposals/smap_tea_pass/v_tea_pass.py at 2d212801 today; the curtain version drops in
there when the owner approves it) and TEA_LEVEL, its texture level.  Change it, run this tool, run `make`.
"""
import json
import os
import pickle
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
OUT = ROOT / "assets" / "smap"
PROP = ROOT / "docs" / "dev" / "proposals"
TEA_ART = "v_tea_pass"          # <- the teahouse swap point: the module (docs/dev/proposals/smap_tea_pass/<name>.py, same build(dmg) as tools/smap_world/v_tea.py)
TEA_LEVEL = "C1S"               # rib roof, textured walls, the wide curtain (no slit), both lanterns at y36, no garden (final, d73ad77f)
FALLS = "A"                     # <- the falls / mountain interface swap point: A (owner pick 11-07, "for now"), B, or "cave" (the stage 1 cave); a later redesign drops in at big_mountain.py
FALLS_ANIM_CELLS = [(47, 3), (46, 4), (47, 4)]      # falls A's animated cells (4 images each): pinned from the flip-merge; stage 3's engine table
# DMG only, one pixel each: (cell x, cell y, pixel x, pixel y, old shade, new shade).  They make six DMG tiles of the top right (falls A, the igloo and the east road) equal to a neighbour's, so that
# no padded path window (23 x 21 cells) needs more than the DMG's 176 tiles (it was 179 at cells 41..63 x 1..20; the camera would have stalled).  Each is a speck at a cell edge.
DMG_TRIM = [(52, 1, 7, 3, 1, 2), (50, 2, 7, 7, 0, 1), (50, 4, 0, 7, 3, 0), (53, 6, 5, 7, 3, 0), (51, 8, 7, 7, 3, 0), (58, 8, 0, 7, 3, 0)]
MAP_ENV = {"SMAP_TEA_PASS": "1", "SMAP_TEA_TEX": TEA_LEVEL}
if FALLS != "cave":
    MAP_ENV["SMAP_FALLS"] = FALLS


def dump(path, broken):
    """subprocess body: build the integrated world (working or broken fountain) and pickle what the snapshot keeps"""
    os.environ.update(MAP_ENV)
    if broken:
        os.environ["SMAP_BROKEN"] = "1"
    sys.path.insert(0, str(PROP / "smap_tea_pass"))
    import swap  # noqa: F401  (puts the teahouse art in place of tools/smap_world/v_tea.py)
    sys.path.insert(0, str(PROP / "smap_import"))
    if TEA_ART != "v_tea_pass":
        sys.path.insert(0, str(PROP / "smap_tea_pass"))
        sys.modules["v_tea"] = __import__(TEA_ART)
    import mapctx as M
    W = M.W
    cw, ch = M.CW, M.CH
    merge = getattr(W, "MERGE", {})

    def grid(w):
        return [list(r) for r in w.px], [[merge.get(w.pal[y][x], w.pal[y][x]) for x in range(cw)] for y in range(ch)]
    pc, palc = grid(W.WORLD)
    pd, pald = grid(W.WORLD_DMG)
    names = sorted({n for r in palc for n in r})
    rgb = {n: [list(c) for c in M.PAL.get(n)] for n in names}
    data = {
        "cw": cw, "ch": ch, "order": list(W.ORDER), "stops": {k: list(v) for k, v in W.STOPS.items()},
        "legs": [[a, b, [list(q) for q in pts]] for (a, b), pts in W.LEGS.items()],
        "venues": {k: list(v[1]) for k, v in W.VENUES.items()},
        "px_c": pc, "px_d": pd, "pal_c": palc, "rgb": rgb, "dmg_shade": list(M.PAL.DMG_SHADE),
        "anim_cells": sorted(set(getattr(W, "ANIM_CELLS", ())) | (set(FALLS_ANIM_CELLS) if FALLS != "cave" else set())),
    }
    with open(path, "wb") as f:
        pickle.dump(data, f)


def build():
    tmp = ROOT / "out" / "smap_snapshot"
    tmp.mkdir(parents=True, exist_ok=True)
    for tag, broken in (("working", False), ("broken", True)):
        subprocess.run([sys.executable, __file__, "--dump", str(tmp / f"{tag}.pkl"), "1" if broken else "0"], check=True)
    a = pickle.load(open(tmp / "working.pkl", "rb"))
    b = pickle.load(open(tmp / "broken.pkl", "rb"))
    cw, ch = a["cw"], a["ch"]
    names = sorted(a["rgb"])
    assert set(b["rgb"]) <= set(names), (set(b["rgb"]) - set(names))
    idx = {n: i for i, n in enumerate(names)}
    for (cx, cy, px, py, old, new) in DMG_TRIM:                # the DMG tile trims (DMG data set only; the Color pixels are untouched)
        for d in (a, b):
            assert d["px_d"][cy * 8 + py][cx * 8 + px] == old, (cx, cy, px, py, old)
            d["px_d"][cy * 8 + py][cx * 8 + px] = new
    repair = []
    for y in range(ch):
        for x in range(cw):
            sc = [a["px_c"][y * 8 + j][x * 8 + i] for j in range(8) for i in range(8)]
            sb = [b["px_c"][y * 8 + j][x * 8 + i] for j in range(8) for i in range(8)]
            dc = [a["px_d"][y * 8 + j][x * 8 + i] for j in range(8) for i in range(8)]
            db = [b["px_d"][y * 8 + j][x * 8 + i] for j in range(8) for i in range(8)]
            if sc != sb or dc != db or a["pal_c"][y][x] != b["pal_c"][y][x]:
                repair.append({"x": x, "y": y, "c": "".join(map(str, sb)), "d": "".join(map(str, db)), "pal": idx[b["pal_c"][y][x]]})
    for k in ("cw", "ch", "order", "stops", "legs", "venues"):
        assert a[k] == b[k], k
    from PIL import Image
    OUT.mkdir(parents=True, exist_ok=True)
    for key, name in (("px_c", "world_c.png"), ("px_d", "world_d.png")):
        im = Image.new("P", (cw * 8, ch * 8))
        im.putpalette([v for s in a["dmg_shade"][:4] for v in (s, s, s)] + [0] * (768 - 12))
        im.putdata([v for row in a[key] for v in row])
        im.save(OUT / name, optimize=True)
    js = {
        "note": "frozen by tools/dev/smap_snapshot.py; the builder reads this, never the proposal pipeline",
        "cw": cw, "ch": ch, "order": a["order"], "stops": a["stops"], "legs": a["legs"], "venues": a["venues"],
        "pal_names": names, "pal_rgb": a["rgb"], "dmg_shade": a["dmg_shade"], "anim_cells": [list(c) for c in a["anim_cells"]],
        "teahouse": {"art": TEA_ART, "level": TEA_LEVEL},
        "cell_pal": ["".join(chr(48 + idx[a["pal_c"][y][x]]) for x in range(cw)) for y in range(ch)],     # one char per cell: chr(48 + palette index)
        "repair": repair,
    }
    (OUT / "world.json").write_text(json.dumps(js, indent=0, separators=(",", ":")) + "\n")
    print(f"snapshot: {cw} x {ch} cells, {len(names)} palettes, {len(repair)} repair cells, wrote {OUT}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--dump":
        dump(sys.argv[2], sys.argv[3] == "1")
    else:
        build()
