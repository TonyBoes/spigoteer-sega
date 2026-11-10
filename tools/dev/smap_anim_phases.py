#!/usr/bin/env python3
"""Maintainer tool: choose the start shifts (ticks) of the story map's animation bundles (tools/smap_world/anims.py SHIFT).

    python3 tools/dev/smap_anim_phases.py            # prints the SHIFT dict to paste into anims.py, and the views that still have more than two events at a tick

The DMG writes two tiles a frame (src/smap_eng.c NSTG_MAX), so no view the camera can show should have more than two animation events at one tick of the 256-tick loop (a third is skipped:
the tile keeps its picture until its next change).  The views are the camera's windows on every pixel of every leg and every stop, a cell more on each side (the generator's path_windows).
Each bundle (a picture whose cells keep their relative timing) takes the shift that adds the fewest overflowing ticks, most-seen bundles first, a few passes.  Start from SHIFT = {} to see the
design timing; the result depends only on the schedules in anims.py.
"""
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tools" / "smap_world"))
import anims as A  # noqa: E402
import gen_smap_world as g  # noqa: E402

CAP = 2


def main():
    A.SHIFT.clear()
    groups = A.build(g.W.WORLD, g.W.WORLD_DMG)
    stops, legs, _, _ = g.geometry()
    wins = sorted(set(g.path_windows(stops, legs, 1)))
    bundles = defaultdict(list)
    for gi, grp in enumerate(groups):
        bundles[A.bundle(grp)].append(gi)
    ev = [set(t for t, _ in grp.events()) for grp in groups]
    wgroups = [[gi for gi, grp in enumerate(groups) if any(c0 <= x <= c1 and r0 <= y <= r1 for (x, y) in grp.cells)] for (c0, c1, r0, r1) in wins]
    shift = {b: 0 for b in bundles}
    of = [A.bundle(grp) for grp in groups]

    def counts(w):
        c = [0] * A.LOOP
        for gi in wgroups[w]:
            s = shift[of[gi]]
            for t in ev[gi]:
                c[(t + s) % A.LOOP] += 1
        return c

    def cost(ws):
        return sum((v - CAP) ** 2 for w in ws for v in counts(w) if v > CAP)
    bw = {b: [w for w in range(len(wins)) if any(gi in wgroups[w] for gi in gis)] for b, gis in bundles.items()}
    order = sorted(bundles, key=lambda b: -len(bw[b]))
    print(f"{len(wins)} views, {len(bundles)} bundles; overflow cost at the design timing {cost(range(len(wins)))}")
    for p in range(3):
        for b in order:
            shift[b] = min(range(A.LOOP), key=lambda s: (cost_with(shift, b, s, bw[b], cost), s))
        print(f"pass {p}: overflow cost {cost(range(len(wins)))}")
    print("SHIFT = " + repr({b: s for b, s in sorted(shift.items()) if s}))
    over = [(max(counts(w)), wins[w]) for w in range(len(wins)) if max(counts(w)) > CAP]
    print(f"{len(over)} views still hold more than {CAP} events at some tick; worst {max(over) if over else None}")


def cost_with(shift, b, s, ws, cost):
    shift[b] = s
    return cost(ws)


if __name__ == "__main__":
    main()
