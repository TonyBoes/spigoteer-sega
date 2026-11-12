"""Builds the ranked merge list and the packages, writes results.json and arrays.npz next to this file.
    python3 docs/dev/proposals/smap_dmg_kit2/packages.py            (about 20 s)
Greedy merge in stages (a tile may differ from its representative by at most 1, then 2 ... pixels, cheapest first, so each package nests its smaller stages).
A tile's distance to the one it shows is counted in SHADE STEPS: the sum over its pixels of |shade difference| (a 1 px change between neighbouring shades = 1,
a dark pixel on a light ground = 3, a 2 px dark dash on a light ground = 6).  Packages = (cap outside venues, cap inside venues) in shade steps:
    light  (3, 3)   every tile at most 3 shade steps from the one it shows
    medium (8, 3)   ground, roads, water, mountains, decor up to 8 steps; every venue tile still at most 3
    strong (8, 8)   everything up to 8 steps (shows what the venues lose; not recommended)
A "venue tile" is a block with at least one cell inside a venue.  The ranked list is the strong run (every candidate merge, cheapest first)."""
import json
import sys

import numpy as np

import lib
import merge
from vetoes import VETO, PROTECT, CAP

WEIGHTED = "--weighted" in sys.argv          # distance in shade steps instead of pixels (a stricter variant, numbers in NOTES)
PACKAGES = {"light": (3, 3), "medium": (8, 3), "strong": (8, 8)} if WEIGHTED else {"light": (3, 3), "medium": (6, 3), "strong": (6, 6)}


def run_package(dm, sg, use, pin, d, veto, vten, caps):
    cap_out, cap_ven = caps
    limit = np.where(vten, cap_ven, cap_out)
    state = None
    ranked, snaps = [], {}
    for dmax in range(1, max(caps) + 1):
        rep, log, groups = merge.greedy(sg, use, pin, dmax, d, veto=veto, state=state, protect=PROTECT, cap=CAP, limit=limit)
        state = (rep, groups)
        for e in log:
            e["stage"] = dmax
            e["step"] = len(ranked) + 1
            e["venue"] = bool(vten[e["moved"]])
            ranked.append(e)
    return rep, ranked, groups


def main():
    dm, sg, use, pin = merge.prepare()
    d = merge.dist_matrix(sg, weighted=WEIGHTED)
    dpx = merge.dist_matrix(sg, weighted=False)                    # pixels
    base = np.array(dm.world.px, dtype=np.uint8)
    loose = "--loose" in sys.argv                   # without the broken-line rule: the numbers of the first pass, kept for the notes
    veto = merge.auto_veto(dm, sg, use, pin, d, base, max(max(c) for c in PACKAGES.values()), lines=not loose) | set(VETO)
    vten = merge.venue_ids(dm, len(sg))
    print("vetoed ordered pairs (new stray pixel):", len(veto), "  venue blocks:", int(vten.sum()))
    out = {"packages": {}, "ranked": []}
    arrs = {}
    for name, caps in PACKAGES.items():
        rep, ranked, groups = run_package(dm, sg, use, pin, d, veto, vten, caps)
        for e in ranked:
            e["px"] = int(sum(int(dpx[m, e["rep"]]) * int(use[m]) for m in e["moved_members"]))
        gr, arr = merge.apply_map(dm, rep)
        arrs[name] = arr
        m = lib.metrics(gr)
        print(name, caps, "tiles", m["unique"], "once", m["once"], "worst", m["w21"][0], m["w22"][0], "step", round(m["step_mean"], 2), m["step_p95"], flush=True)
        out["packages"][name] = {k: (list(v) if isinstance(v, tuple) else v) for k, v in m.items()}
        if name == "strong":
            for e in ranked:
                out["ranked"].append({k: e[k] for k in ("step", "stage", "px", "cost", "rep", "moved", "venue")} | {"members": [int(x) for x in e["members"]]})
    if loose or WEIGHTED:
        return
    json.dump(out, open(lib.OUT / "results.json", "w"), indent=1, default=int)
    np.savez(lib.OUT / "arrays.npz", **arrs)


if __name__ == "__main__":
    main()
