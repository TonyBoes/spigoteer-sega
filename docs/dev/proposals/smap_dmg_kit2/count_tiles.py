#!/usr/bin/env python3
"""Today's DMG story-map tile numbers, from assets/smap/world_d.png through the build's own model (tools/gen_smap_world.py Model, the Map Atlas Static).
Read-only: prints only.   python3 docs/dev/proposals/smap_dmg_kit2/count_tiles.py
Counts are on the finished map (unlock state 11, no fog); the worst windows are taken over every unlock state (state 1 carries the fog)."""
from collections import Counter, defaultdict

import numpy as np

import lib
import merge

dm, sg, use, pin = merge.prepare()
G = lib.G
g = dm.grids[G.NSTATE]
pg = lib.piece_grid()
print(f"map {lib.CW}x{lib.CH} cells = {lib.CW * lib.CH} cells; DMG tile pool {G.POOL}; window 21x19 view, 22x20 loaded region")
m = lib.metrics({p: dm.grids[p] for p in dm.ustates})
print(f"unique tiles (state 11): {m['unique']}   used once: {m['once']}   (all states: {dm.nsig}, of which animation group tiles {len(pin)})")
print(f"worst 21x19 window: {m['w21'][0]} of {G.POOL}  at (state, x, y) {m['w21'][1]};   worst 22x20: {m['w22'][0]} at {m['w22'][1]}")
g11 = {G.NSTATE: g}
m11 = lib.metrics(g11, steps=False)
print(f"   state 11 only (no fog): 21x19 {m11['w21'][0]} at {m11['w21'][1][1:]},  22x20 {m11['w22'][0]} at {m11['w22'][1][1:]}")
print(f"scroll step, new tile ids per one-cell step of the 22x20 loaded region ({m['step_n']} steps, both axes and directions): "
      f"mean {m['step_mean']:.2f}  p95 {m['step_p95']:.0f}  max {m['step_max']}")

# ---- per area ------------------------------------------------------------------------------------------------------------------------------------
areas = defaultdict(list)
for y in range(lib.CH):
    for x in range(lib.CW):
        n = pg[y][x]
        a = "Roads" if n == "Roads" else ("Ground: " + n[6:] if n.startswith("Land:") else n)
        areas[a].append(int(g[y, x]))
cnt = np.bincount(g.ravel())
print(f"\n{'area':22}{'cells':>6}{'unique':>8}{'only here':>10}{'once':>6}")
ven = ("Stadium", "Bistro", "Igloo", "Saloon", "Town", "Lodge", "Space", "Factory", "Zoo", "Teahouse", "Rodeo")
for a in list(ven) + sorted(k for k in areas if k not in ven):
    ids = set(areas[a])
    others = set().union(*[set(v) for k, v in areas.items() if k != a])
    print(f"{a:22}{len(areas[a]):>6}{len(ids):>8}{len(ids - others):>10}{sum(1 for i in ids if cnt[i] == 1):>6}")
vc = [i for a in ven for i in areas[a]]
print(f"venues: {len(vc)} cells, {len(set(vc))} unique tiles; everything else: {sum(len(v) for k, v in areas.items() if k not in ven)} cells")

# ---- flips: DMG background tiles cannot be flipped, so a flip twin saves nothing ----------------------------------------------------------------
live = [i for i in range(len(sg)) if use[i] > 0 and i not in pin]
seen = {bytes(sg[i].tolist()): i for i in live}


def flips(s):
    a = s.reshape(8, 8)
    return {"x": a[:, ::-1], "y": a[::-1], "xy": a[::-1, ::-1]}


twins = 0
sym = 0
for i in live:
    for k, f in flips(sg[i]).items():
        j = seen.get(bytes(f.reshape(-1).tolist()))
        if j is not None and j != i:
            twins += 1
        elif j == i:
            sym += 1
print(f"\nidentical tiles: 0 (the model already merges equal blocks).  Flip twins (a tile equal to another after an X, Y or XY flip): {twins // 2} pairs,"
      f" self-symmetric tiles {sym}.  The DMG background cannot flip tiles, so these save nothing without redrawing one of the pair.")

# ---- animated tiles: what they block ----------------------------------------------------------------------------------------------------------
d = merge.dist_matrix(sg)
print("\nanimation groups whose tile id is pinned (the animation rewrites the one tile): near-twins they block")
byitem = defaultdict(lambda: [0, 0, 0])
for gi, an in enumerate(G.ANIMS):
    ids = {i for k, i in dm.ids.items() if isinstance(k, tuple) and k[1] == gi}
    for i in ids:
        if use[i] == 0:
            continue
        r = byitem[an.item]
        r[0] += 1
        r[1] += int(((d[i][live] == 0)).sum())
        r[2] += int(((d[i][live] <= 6)).sum())
print(f"{'item':22}{'pinned tiles':>13}{'equal twins':>12}{'twins <= 6 px':>14}")
for k, v in byitem.items():
    print(f"{k:22}{v[0]:>13}{v[1]:>12}{v[2]:>14}")
