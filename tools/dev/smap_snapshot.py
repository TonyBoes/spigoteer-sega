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
  assets/smap/world.json     the cell palettes (indices into pal_names), the 23 palettes' colours, the stops and legs, the venues' cells, and the REPAIR cells: the fountain's broken
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
OUT = Path(os.environ["SMAP_SNAP_OUT"]) if os.environ.get("SMAP_SNAP_OUT") else ROOT / "assets" / "smap"      # (SMAP_SNAP_OUT: write somewhere else, for before / after pictures)
PROP = ROOT / "docs" / "dev" / "proposals"
TEA_ART = "v_tea_pass"          # <- the teahouse swap point: the module (docs/dev/proposals/smap_tea_pass/<name>.py, same build(dmg) as tools/smap_world/v_tea.py)
TEA_LEVEL = "C1S"               # rib roof, textured walls, the wide curtain (no slit), both lanterns at y36, no garden (final, d73ad77f)
FALLS = "A"                     # <- the falls / mountain interface swap point: A (owner pick 11-07, "for now"), B, or "cave" (the stage 1 cave); a later redesign drops in at big_mountain.py
FALLS_ANIM_CELLS = [(47, 3), (46, 4), (47, 4)]      # falls A's animated cells (4 images each): pinned from the flip-merge; stage 3's engine table
# DMG only, one pixel each: (cell x, cell y, pixel x, pixel y, old shade, new shade).  There were six of them (the top right's falls A, igloo and east road: a padded path window needed 179 DMG tiles,
# the limit is 176).  The Q10 tree removal and near-twin merge (owner 11-08) bring the worst padded path window to 173 without them, so none is needed; the old six are in commit e574897b.
DMG_TRIM = []
# The owner's map changes of 11-08 (Q6 "a2", Q7 "yes", docs/dev/proposals/smap_owner_1108): A2 desert peaks (prop_a.py), B1 awning, B2 paving, B3 the town 8 cells west, B4 the band's rounded ends (owner_pre.py).
# ctx.py applies them to the proposal pipeline; they are part of the integrated map now, so dump() always sets this.
OWNER_FLAGS = "A2,B1,B2,B3,B4,Q10"
MAP_ENV = {"SMAP_TEA_PASS": "1", "SMAP_TEA_TEX": TEA_LEVEL}
if FALLS != "cave":
    MAP_ENV["SMAP_FALLS"] = FALLS


def dump(path, broken):
    """subprocess body: build the integrated world (working or broken fountain) and pickle what the snapshot keeps"""
    os.environ.update(MAP_ENV)
    if broken:
        os.environ["SMAP_BROKEN"] = "1"
    os.environ["OWNER"] = OWNER_FLAGS
    sys.path.insert(0, str(PROP / "smap_owner_1108"))
    import ctx  # noqa: F401  (the tea pass swap, the proposal pipeline's paths and the owner changes of 11-08 on top of it)
    sys.path.insert(0, str(PROP / "smap_import"))
    if TEA_ART != "v_tea_pass":
        sys.path.insert(0, str(PROP / "smap_tea_pass"))
        sys.modules["v_tea"] = __import__(TEA_ART)
    import mapctx as M
    W = M.W
    cw, ch = M.CW, M.CH
    # Sal's path on the east road, space -> town: its two waypoints stand at x 295, not 296 (the road is 288..303 wide, the road pixels are unchanged: they were laid from the legs before this line).
    # The walk's lookahead then loads the lead column 25 at the corner (the camera's first column is 26 all the way up) instead of column 26, the town hall's side with six tile uploads: the Color walk
    # frame that cost 147 lines is gone (the guard is 145).
    W.LEGS[("space", "town")] = [(295 if x == 296 else x, y) for (x, y) in W.LEGS[("space", "town")]]
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
    import numpy as np
    import q10_twins                                          # the near-twin merge's areas (owner Q10, 11-08): read from the layout here, applied in build()
    ok, prot = q10_twins.area_masks(M.lay, palc, cw, ch)
    data["q10_ok"], data["q10_prot"] = ok.tolist(), prot.tolist()
    with open(path, "wb") as f:
        pickle.dump(data, f)


TWIN_PX = int(os.environ.get("SMAP_TWIN_PX", "2"))                    # owner Q10 (11-08): near twins 1 to 2 px apart fold into the most-used tile, in the approved areas only (docs/dev/proposals/smap_owner_1108/q10_twins.py)


def q10_twins_apply(a, b):
    """merge the working state's tiles, then give the broken state the same edits wherever its cell still holds the pixels the working one had (so only the fountain's cells differ)"""
    import numpy as np
    sys.path.insert(0, str(PROP / "smap_owner_1108"))
    import q10_twins
    ok, prot = np.array(a["q10_ok"]), np.array(a["q10_prot"])
    cw, ch = a["cw"], a["ch"]
    for key, flips in (("px_c", True), ("px_d", False)):
        old = np.array(a[key], dtype=np.uint8)
        new, st, _ = q10_twins.merge(old, ok, prot, flips, TWIN_PX)
        print(f"near twins {key}: {st}")
        bb = np.array(b[key], dtype=np.uint8)
        for cy in range(ch):
            for cx in range(cw):
                sl = (slice(cy * 8, cy * 8 + 8), slice(cx * 8, cx * 8 + 8))
                if (old[sl] != new[sl]).any() and (bb[sl] == old[sl]).all():
                    bb[sl] = new[sl]
        a[key], b[key] = new.tolist(), bb.tolist()


MAX_FLAT = 239                  # the engine's byte use count per DMG tile in a 22 x 20 window (tools/gen_smap_world.py MAX_CELLS_IN_WIN)


def q10_ground(a, b):
    """With the trees and bushes gone, the plain ground of a few windows (cells 21..45 x 30..54, the lawn between the desert and the river) holds the flat ground tile in more than MAX_FLAT of the
    440 cells of a 22 x 20 window.  The ground's own tuft (tiles.SPROUT, the same tile as everywhere on the grass) goes on the fewest extra flat grass or sand cells that bring every window back to the
    limit: the cell covered by most windows over the limit first, never beside another tuft.  Both data sets and both fountain states get the same cells."""
    import numpy as np
    sys.path.insert(0, str(ROOT / "tools" / "smap_world"))
    import tiles
    cw, ch = a["cw"], a["ch"]
    TUFT = {n: np.array([[int(c) for c in r] for r in rows], dtype=np.uint8) for n, rows in (("grass", tiles.SPROUT), ("saloon", tiles.RIPPLE))}   # the grass's sprout, the sand's ripple
    pd = np.array(a["px_d"], dtype=np.uint8)
    pc = np.array(a["px_c"], dtype=np.uint8)

    def blocks(p):
        return p.reshape(ch, 8, cw, 8).transpose(0, 2, 1, 3).reshape(ch, cw, 64)
    bd, bc = blocks(pd), blocks(pc)
    flat = ~(bd.any(axis=2))
    cand = flat & ~(bc.any(axis=2)) & np.array([[n in TUFT for n in r] for r in a["pal_c"]])
    tuft = np.zeros((ch, cw), dtype=bool)
    for t in TUFT.values():
        tuft |= (bd == t.reshape(64)).all(axis=2)
    wins = [(x0, y0) for y0 in range(ch - 19) for x0 in range(cw - 21)]
    added = []
    while True:
        over = [(x0, y0) for (x0, y0) in wins if flat[y0:y0 + 20, x0:x0 + 22].sum() > MAX_FLAT]
        if not over:
            break
        score = np.zeros((ch, cw), dtype=int)
        for (x0, y0) in over:
            score[y0:y0 + 20, x0:x0 + 22] += 1
        score = np.where(cand, score, -1)
        for (x, y) in zip(*np.nonzero(cand)[::-1]):                     # keep the tufts apart (no tuft on a cell beside another)
            if any(0 <= x + dx < cw and 0 <= y + dy < ch and tuft[y + dy, x + dx] for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, 1), (1, -1), (-1, -1))):
                score[y, x] = -1
        best = score.max()
        assert best > 0, "no flat ground cell left to take a tuft"
        ys, xs = np.nonzero(score == best)
        k = (xs * 7 + ys * 13) % len(xs)                                # deterministic pick among equals
        x, y = int(xs[int(np.argmin(k))]), int(ys[int(np.argmin(k))])
        added.append((x, y))
        flat[y, x] = False
        tuft[y, x] = True
        cand[y, x] = False
    for key in ("px_c", "px_d"):
        for d in (a, b):
            for (x, y) in added:
                t = TUFT[a["pal_c"][y][x]]
                for j in range(8):
                    for i in range(8):
                        assert d[key][y * 8 + j][x * 8 + i] == 0
                        d[key][y * 8 + j][x * 8 + i] = int(t[j][i])
    print(f"ground tufts added: {len(added)} {added}")


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
    q10_twins_apply(a, b)
    q10_ground(a, b)
    for (cx, cy, px, py, old, new) in DMG_TRIM:              # the DMG tile trims (DMG data set only; the Color pixels are untouched)
        for d in (a, b):
            assert d["px_d"][cy * 8 + py][cx * 8 + px] == old, (cx, cy, px, py, old)
            d["px_d"][cy * 8 + py][cx * 8 + px] = new
    # palsnap (tools/smap_world, run by world2 on each build) moves cells to a neighbouring ground so that no window needs more than 8 palettes; the broken fountain's town has another
    # palette set, so it snapped a few ground cells differently (the working state's snap is the one that is shown): a cell with the same pixels in both states takes the working palette
    for y in range(ch):
        for x in range(cw):
            if a["pal_c"][y][x] != b["pal_c"][y][x] and all(a[k][y * 8 + j][x * 8 + i] == b[k][y * 8 + j][x * 8 + i] for k in ("px_c", "px_d") for j in range(8) for i in range(8)):
                b["pal_c"][y][x] = a["pal_c"][y][x]
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
