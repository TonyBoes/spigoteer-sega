"""Camera speed caps (round 3): for every one-cell step of the 21 x 19 window in the late world, the bytes to send (new tiles x 16 plus the ids,
and on Color the attributes) and the fastest camera speed (4, 3, 2 or 1 px a frame) at which the 86 B/frame drain (VQ_DRAIN_BUDGET) keeps up."""
import sys
from collections import Counter

import render2 as R
import stats2 as S
import world2 as W

CW, CH = W.CW, W.CH
BUDGET = 86
DMG = len(sys.argv) > 1 and sys.argv[1] == "dmg"            # round 5: "dmg" measures the hand-trimmed DMG world
sg = S.sig_grid(W.WORLD_DMG if DMG else R.LATE)


def speed_for(cost):
    for s in (4, 3, 2, 1):
        if BUDGET * 8 / s >= cost:
            return s
    return 0


def run(extra):
    cnt = Counter()
    worst = {"col": 0, "row": 0}
    for y0 in range(CH - 18):
        for x0 in range(CW - 21):
            old = {sg[y][x] for y in range(y0, y0 + 19) for x in range(x0, x0 + 21)}
            for nx in (x0 + 21, x0 - 1):
                if not 0 <= nx < CW:
                    continue
                k = len({sg[y][nx] for y in range(y0, y0 + 19)} - old)
                cost = 16 * k + 19 * (1 + extra)
                worst["col"] = max(worst["col"], cost)
                cnt[("col", speed_for(cost))] += 1
    for x0 in range(CW - 20):
        for y0 in range(CH - 19):
            old = {sg[y][x] for y in range(y0, y0 + 19) for x in range(x0, x0 + 21)}
            for ny in (y0 + 19, y0 - 1):
                if not 0 <= ny < CH:
                    continue
                k = len({sg[ny][x] for x in range(x0, x0 + 21)} - old)
                cost = 16 * k + 21 * (1 + extra)
                worst["row"] = max(worst["row"], cost)
                cnt[("row", speed_for(cost))] += 1
    return cnt, worst


for label, extra in ((("DMG trimmed (ids only)", 0),) if DMG else (("DMG (ids only)", 0), ("Color (ids + attributes)", 1))):
    cnt, worst = run(extra)
    print(label, "worst column", worst["col"], "B, worst row", worst["row"], "B")
    for kind in ("col", "row"):
        tot = sum(v for (k, s), v in cnt.items() if k == kind)
        print("  ", kind, {s: f"{100 * v / tot:.1f}%" for (k, s), v in sorted(cnt.items(), key=lambda t: -t[0][1]) if k == kind})
