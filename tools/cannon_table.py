#!/usr/bin/env python3
"""T-Shirt Cannon's landing table (docs/minigames_bosses.md 4.2; src/ts.c): simulates every power level of the meter with the game's own
integer physics and checks the fairness rule. tools/gen_ts.py imports this and fails the build when the rule breaks; the same numbers go
to build/ts.json for tests/test_mg_tshirt.py.

The cannon's barrel is fixed at the 60 degree lob (the stand is a staircase: a flatter shot enters at its first column whatever the
power, so the angle was no second decision). The golf-style power meter p = 0 .. PMAX sets the launch speed, v = V0 + DV p (8.8 px/f):
vx = v >> 1, vy = -(v - (v >> 3) - (v >> 7)) (v sin 60, 222/256), gravity 1/16 px/f^2 (16 in 8.8). The muzzle is the barrel tip of the
60 degree look of the cannon sprite. One step a frame: x += vx; y += vy; vy += 16; then the shirt's centre is looked up:
 - in a stand column 9-19 (its top row is 11 - (c - 9) / 2) at or below the column's top and above the ad boards (y 104): the CROWD is hit
   (column c - 9);
 - in the stand at the ad boards (y >= 104) or anywhere down at y 124 (the grass): SHORT;
 - at x >= 168 (past the last column, over the stand): OVER.

Fairness rule: (a) the meter starts with at least SHORT_MIN steps of short and ends with at least OVER_MIN steps of over (the oops
zones the owner asked for, drawn red on the meter), (b) every stand column 0-10 is reached by some power, (c) a raised fan reaches the
column on each side, so the powers that catch it (3 columns) span at least REACH_MIN steps for every fan, (d) no flight is longer
than 120 frames.
"""
import json
import sys

V0, DV, PMAX = 224, 13, 63
MUZZLE = (43, 105)           # barrel tip (px) of the 60 degree look (assets/art/tshirt/cannon.txt)
CANNON_XY = (32, 104)        # the sprite's top-left
FAN_FIRST, FAN_N = 9, 11
BOARD_Y, LAND_Y, OUT_X = 104, 124, 168
SHORT_MIN, OVER_MIN, REACH_MIN = 8, 8, 5
SHORT, CROWD, OVER = 0, 1, 2


def top_row(c):
    return 11 - (c - FAN_FIRST) // 2


def velocity(p):
    v = V0 + DV * p
    return v >> 1, -(v - (v >> 3) - (v >> 7))


def fly(p):
    """-> (SHORT | CROWD | OVER, column 0-10 (CROWD) else 0, frames of flight) for power p."""
    x, y = MUZZLE[0] << 8, MUZZLE[1] << 8
    vx, vy = velocity(p)
    for t in range(1, 400):
        x += vx
        y += vy
        vy += 16
        px, py = x >> 8, y >> 8
        c = px >> 3
        if FAN_FIRST <= c < FAN_FIRST + FAN_N:
            top = top_row(c) * 8
            if top <= py < BOARD_Y:
                return CROWD, c - FAN_FIRST, t
            if py >= BOARD_Y:
                return SHORT, 0, t
        if px >= OUT_X:
            return OVER, 0, t
        if py >= LAND_Y:
            return SHORT, 0, t
    return OVER, 0, 400


def table():
    return [fly(p) for p in range(PMAX + 1)]


def zones(t):
    """-> (the last short power, the first over power)."""
    short_max = max(p for p, r in enumerate(t) if r[0] == SHORT and all(q[0] == SHORT for q in t[:p + 1]))
    over_min = min(p for p, r in enumerate(t) if r[0] == OVER and all(q[0] == OVER for q in t[p:]))
    return short_max, over_min


def windows(t):
    """-> {column: number of powers that hit it}."""
    w = {c: 0 for c in range(FAN_N)}
    for k, c, _ in t:
        if k == CROWD:
            w[c] += 1
    return w


def reach(t, c):
    """Powers that a raised fan in column c catches (its own column and one each side)."""
    return sum(1 for k, cc, _ in t if k == CROWD and abs(cc - c) <= 1)


def problems(t):
    out = []
    sm, om = zones(t)
    if sm + 1 < SHORT_MIN:
        out.append(f"only {sm + 1} steps of short (need {SHORT_MIN})")
    if PMAX + 1 - om < OVER_MIN:
        out.append(f"only {PMAX + 1 - om} steps of over (need {OVER_MIN})")
    for c, n in windows(t).items():
        if n == 0:
            out.append(f"column {c} cannot be hit")
        if reach(t, c) < REACH_MIN:
            out.append(f"a raised fan in column {c} is caught by only {reach(t, c)} powers (need {REACH_MIN})")
    for p, (k, c, n) in enumerate(t):
        if n > 120:
            out.append(f"flight at power {p} takes {n} frames")
    return out


def report(t):
    sm, om = zones(t)
    w = windows(t)
    lines = [f"short: power 0-{sm}; over: {om}-{PMAX}; columns' windows (steps): " + " ".join(f"c{c}:{n}" for c, n in w.items()),
             "with the reach of a raised fan (steps): " + " ".join(f"c{c}:{reach(t, c)}" for c in range(FAN_N))]
    return "\n".join(lines)


def to_json(t):
    sm, om = zones(t)
    return {"v0": V0, "dv": DV, "pmax": PMAX, "muzzle": list(MUZZLE), "cannon": list(CANNON_XY), "grav": 16, "board_y": BOARD_Y,
            "land_y": LAND_Y, "out_x": OUT_X, "short_max": sm, "over_min": om, "table": [list(r) for r in t],
            "vel": [list(velocity(p)) for p in range(PMAX + 1)]}


if __name__ == "__main__":
    tb = table()
    print(report(tb))
    bad = problems(tb)
    for b in bad:
        print("FAIL", b)
    sys.exit(1 if bad else 0)
