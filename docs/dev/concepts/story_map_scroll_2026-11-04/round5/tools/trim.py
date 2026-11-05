"""DMG trim estimate (round 3): after ground variants and scenery are plain, by what share must the venue-only tiles shrink so that no window
holds more than a target?  A tile is 'only' an area's if no other area uses it; the rest are shared (roads, kerbs, plain ground, fog)."""
import render2 as R
import stats2 as S
import world2 as W

w = R.LATE
sg = S.sig_grid(w)
PLAIN = tuple(tuple([0] * 8) for _ in range(8))
g = [[PLAIN if w.kind[y][x] in ("ground", "decor") else sg[y][x] for x in range(W.CW)] for y in range(W.CH)]
owner = {}
for y in range(W.CH):
    for x in range(W.CW):
        owner.setdefault(g[y][x], set()).add(W.ZONE[y][x])
only = {t: next(iter(z)) for t, z in owner.items() if len(z) == 1}
print("tiles after plain ground and scenery:", len(owner), "area-only:", len(only), "shared:", len(owner) - len(only))
per = {}
for t, z in only.items():
    per[z] = per.get(z, 0) + 1
print("area-only tiles:", dict(sorted(per.items())))
rows = []
for y0 in range(W.CH - 18):
    for x0 in range(W.CW - 20):
        ts = {g[y][x] for y in range(y0, y0 + 19) for x in range(x0, x0 + 21)}
        n_only = sum(1 for t in ts if t in only)
        rows.append((len(ts), n_only, x0, y0))
for target in (176, 170, 146):
    worst = 0
    for n, o, x0, y0 in rows:
        sh = n - o
        if sh >= target:
            worst = 1.0
            continue
        worst = max(worst, 1 - (target - sh) / o if o and n > target else 0)
    print(f"target {target}: area-only tiles must shrink by {worst:.0%} in the worst window")
