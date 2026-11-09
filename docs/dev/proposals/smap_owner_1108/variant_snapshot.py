"""python3 -I variant_snapshot.py TAG     (env OWNER=... as ctx.py)

Freezes the variant map the way tools/dev/smap_snapshot.py freezes the real one (the same assembly: working and broken fountain, the DMG trims, the repair cells, world.json, world_c.png, world_d.png),
but into out/owner1108/snap_TAG/ and from the proposal pipeline AS ctx.py configures it.  Nothing under assets/ is touched; the generator (measure.py) and the sheets read this copy.
Writes out/owner1108/snap_TAG/{world_c.png, world_d.png, world.json}."""
import json
import os
import pickle
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "tools" / "dev"))


def dump(path, broken):
    if broken:
        os.environ["SMAP_BROKEN"] = "1"
    import ctx
    S, M = ctx.S, ctx.M
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
        "anim_cells": sorted(set(getattr(W, "ANIM_CELLS", ())) | set(S.FALLS_ANIM_CELLS)),
    }
    with open(path, "wb") as f:
        pickle.dump(data, f)


def build(tag):
    import smap_snapshot as S
    out = ROOT / "out" / "owner1108" / f"snap_{tag}"
    out.mkdir(parents=True, exist_ok=True)
    for t, broken in (("working", False), ("broken", True)):
        subprocess.run([sys.executable, "-I", __file__, "--dump", str(out / f"{t}.pkl"), "1" if broken else "0"], check=True, env=dict(os.environ))
    a = pickle.load(open(out / "working.pkl", "rb"))
    b = pickle.load(open(out / "broken.pkl", "rb"))
    cw, ch = a["cw"], a["ch"]
    names = sorted(a["rgb"])
    assert set(b["rgb"]) <= set(names), (set(b["rgb"]) - set(names))
    idx = {n: i for i, n in enumerate(names)}
    for (cx, cy, px, py, old, new) in S.DMG_TRIM:
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
    for key, name in (("px_c", "world_c.png"), ("px_d", "world_d.png")):
        im = Image.new("P", (cw * 8, ch * 8))
        im.putpalette([v for s in a["dmg_shade"][:4] for v in (s, s, s)] + [0] * (768 - 12))
        im.putdata([v for row in a[key] for v in row])
        im.save(out / name, optimize=True)
    js = {
        "note": "variant snapshot (owner proposals 11-08), not the real one", "cw": cw, "ch": ch, "order": a["order"], "stops": a["stops"], "legs": a["legs"], "venues": a["venues"],
        "pal_names": names, "pal_rgb": a["rgb"], "dmg_shade": a["dmg_shade"], "anim_cells": [list(c) for c in a["anim_cells"]],
        "teahouse": {"art": S.TEA_ART, "level": S.TEA_LEVEL},
        "cell_pal": ["".join(chr(48 + idx[a["pal_c"][y][x]]) for x in range(cw)) for y in range(ch)],
        "repair": repair,
    }
    (out / "world.json").write_text(json.dumps(js, indent=0, separators=(",", ":")) + "\n")
    for t in ("working", "broken"):
        (out / f"{t}.pkl").unlink()
    return out


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--dump":
        dump(sys.argv[2], sys.argv[3] == "1")
    else:
        o = build(sys.argv[1])
        print("variant snapshot:", o)
