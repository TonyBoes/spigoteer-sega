"""Round 5: which 21 x 19 windows the camera can really show.  The camera is centred on Sal (target = feet - (80, 84), clamped) and trails him
by at most LAG px (the round-2 follow rule: past 32 px behind Sal waits).  Sal walks only the legs of world2.LEGS.
reachable() -> set of (x0, y0) window origins (cells) for LAG px of slack both ways."""
import render2 as R
import world2 as W

LAG = 32


def reachable(lag=LAG):
    out = set()
    pts = set()
    for (a, b) in W.LEGS:
        for p in W.leg_points(a, b):
            pts.add(p)
        for p in W.leg_points(b, a):
            pts.add(p)
    for n in W.STOPS:
        pts.add(W.STOPS[n])
    for (fx, fy) in pts:
        tx, ty = R.clampcam(fx - 80, fy - 12 - 72)
        for dx in range(-lag, lag + 1, 4):
            for dy in range(-lag, lag + 1, 4):
                cx, cy = R.clampcam(tx + dx, ty + dy)
                out.add((cx // 8, cy // 8))
                out.add(((cx + 7) // 8, (cy + 7) // 8))
    return {(x, y) for (x, y) in out if 0 <= x <= W.CW - 21 and 0 <= y <= W.CH - 19}


if __name__ == "__main__":
    r = reachable()
    print(len(r), "reachable window origins of", (W.CW - 20) * (W.CH - 18))
