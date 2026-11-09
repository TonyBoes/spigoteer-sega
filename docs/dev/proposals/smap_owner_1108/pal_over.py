"""python3 -I pal_over.py TAG   : the 21 x 19 Color windows of the variant snapshot out/owner1108/snap_TAG that hold more than 8 palettes, with each palette's cell count and cells (read-only)."""
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
snap = ROOT / "out" / "owner1108" / f"snap_{sys.argv[1]}" if len(sys.argv) > 1 else ROOT / "assets" / "smap"
lim = int(sys.argv[2]) if len(sys.argv) > 2 else 8
J = json.loads((snap / "world.json").read_text())
N = J["pal_names"]
CP = [[N[ord(c) - 48] for c in r] for r in J["cell_pal"]]
CW, CH = J["cw"], J["ch"]
rep = {(r["x"], r["y"]): N[r["pal"]] for r in J["repair"]}
for state in ("working", "broken"):
    g = [row[:] for row in CP]
    if state == "broken":
        for (x, y), p in rep.items():
            g[y][x] = p
    bad = []
    for y0 in range(CH - 18):
        for x0 in range(CW - 20):
            c = Counter(g[y][x] for y in range(y0, y0 + 19) for x in range(x0, x0 + 21))
            if len(c) > lim:
                bad.append(((x0, y0), c))
    print(state, "windows over", lim, ":", len(bad))
    if bad:
        for (w, c) in bad[:3]:
            print("  window", w, dict(c.most_common()))
        allp = Counter()
        for (w, c) in bad:
            for p in c:
                allp[p] += 1
        print("  palette presence in the bad windows:", dict(allp.most_common()))
        xs = [w[0] for w, _ in bad]
        ys = [w[1] for w, _ in bad]
        print("  windows x0", min(xs), max(xs), "y0", min(ys), max(ys))
