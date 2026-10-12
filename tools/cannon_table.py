#!/usr/bin/env python3
"""T-Shirt Cannon's landing table (docs/minigames_bosses.md 4.2; src/ts.c): simulates every (angle, wind) shot with the game's own
integer physics and checks the fairness rule. tools/gen_ts.py imports this and fails the build when the rule breaks; the same
numbers go to build/ts.json for tests/test_mg_tshirt.py.

Physics (8.8 fixed point, one step a frame): x += vx; y += vy; vy += 16 (1/16 px/f^2); vx += k (wind, k/256 px/f^2); then the
shirt's centre is looked up: inside a fan's 8x16 box (columns 9-19, the top row of column c is 11 - (c - 9) / 2) it is caught; past
x 168 or down at y 124 (the grass) it is lost. Speed 3.0 px/f (768 in 8.8) at 10..60 degrees in 5 degree steps; the muzzle is the
barrel tip of the cannon sprite's look (15 / 30 / 45 / 60 degree art), see MUZZLE.

The spec's fixed muzzle (40, 100) came before the art: the approved look stands the cannon on the grass, its barrel tips are 5-12 px
lower, so the table is the one for those four tips.

Fairness rule (the spec's "every column reachable within 4 px" cannot hold: a shot that enters a column's box from the left is caught
by it, so the flat angles all land on column 9 and each 5 degree step skips some columns, with the spec's own numbers too; see
PLAN.md "T-Shirt Cannon as built"): for every wind that the schedule can show, a wave centred on any of its 9 positions can be hit:
(a) some angle catches a fan in each position's three standing columns (300) in at least WAVE_MIN_300 of the 9, and
(b) every position has a catch in its three columns or in the column each side of them (300 or 100).
"""
import json
import math
import sys

ANGLES = list(range(10, 65, 5))
SPEED = 768                  # 3.0 px/f in 8.8
GRAV = 16                    # 1/16 px/f^2
CANNON_XY = (32, 104)        # the sprite's top-left
MUZZLE = ((46, 112), (46, 109), (44, 107), (43, 105))   # barrel tip (px) of the 15 / 30 / 45 / 60 degree looks (assets/art/tshirt/cannon.txt)
FAN_FIRST, FAN_N = 9, 11
LAND_Y, OUT_X = 124, 168
WINDS = (-2, -1, 0, 1, 2)
SCHEDULE = ((1, 3, (0,)), (4, 8, (-1, 0, 1)), (9, 12, (-2, -1, 0, 1, 2)))   # shots (first, last) and the winds they may show
WAVE_MIN_300 = 7


def look(a):
    return 0 if a <= 20 else 1 if a <= 35 else 2 if a <= 50 else 3


def top_row(c):
    return 11 - (c - FAN_FIRST) // 2


def velocity(a):
    r = math.radians(a)
    return round(SPEED * math.cos(r)), -round(SPEED * math.sin(r))


def fly(a, k, muzzle=MUZZLE):
    """-> (column caught or None, frames of flight) for angle a (degrees) and wind k."""
    mx, my = muzzle[look(a)]
    x, y = mx << 8, my << 8
    vx, vy = velocity(a)
    for t in range(1, 400):
        x += vx
        y += vy
        vy += GRAV
        vx += k
        c = (x >> 8) >> 3
        if FAN_FIRST <= c < FAN_FIRST + FAN_N:
            top = top_row(c) * 8
            if top <= (y >> 8) < top + 16:
                return c, t
        if (x >> 8) >= OUT_X or (y >> 8) >= LAND_Y:
            return None, t
    return None, 400


def table(muzzle=MUZZLE):
    return {(k, a): fly(a, k, muzzle) for k in WINDS for a in ANGLES}


def windows(cols):
    """-> (positions with a 300, positions with a 300 or 100) over the wave's centres 1..9 (standing columns centre - 1 .. centre + 1)."""
    n300 = [p for p in range(1, 10) if {FAN_FIRST + p - 1, FAN_FIRST + p, FAN_FIRST + p + 1} & cols]
    n100 = [p for p in range(1, 10) if {FAN_FIRST + p - 2, FAN_FIRST + p - 1, FAN_FIRST + p, FAN_FIRST + p + 1, FAN_FIRST + p + 2} & cols]
    return n300, n100


def problems(t):
    out = []
    used = sorted({k for _, _, ks in SCHEDULE for k in ks})
    for k in used:
        cols = {c for (kk, a), (c, _) in t.items() if kk == k and c is not None}
        n300, n100 = windows(cols)
        if len(n300) < WAVE_MIN_300:
            out.append(f"wind {k:+d}: only {len(n300)} of 9 wave positions can be hit for 300 (need {WAVE_MIN_300})")
        if len(n100) < 9:
            out.append(f"wind {k:+d}: wave positions {[p for p in range(1, 10) if p not in n100]} cannot be hit at all")
    for (k, a), (c, n) in t.items():
        if c is not None and n > 120:
            out.append(f"flight {a} deg wind {k:+d} takes {n} frames")
    return out


def report(t):
    lines = ["landing column / frames of flight; rows: wind, columns: angle"]
    lines.append("wind  " + " ".join(f"{a:>6}" for a in ANGLES))
    for k in WINDS:
        lines.append(f"{k:+d}    " + " ".join(f"{('-' if t[(k, a)][0] is None else t[(k, a)][0]):>2}/{t[(k, a)][1]:<3}" for a in ANGLES))
    for k in WINDS:
        cols = {c for (kk, a), (c, _) in t.items() if kk == k and c is not None}
        n300, n100 = windows(cols)
        lines.append(f"wind {k:+d}: columns {sorted(cols)}; wave positions with a 300: {len(n300)} of 9, without a 300 or 100: {9 - len(n100)}")
    return "\n".join(lines)


def to_json(t):
    return {"angles": ANGLES, "winds": list(WINDS), "muzzle": [list(m) for m in MUZZLE], "cannon": list(CANNON_XY),
            "vel": [list(velocity(a)) for a in ANGLES], "grav": GRAV, "land_y": LAND_Y, "out_x": OUT_X,
            "table": {f"{k},{a}": list(v) for (k, a), v in t.items()}}


if __name__ == "__main__":
    tb = table()
    print(report(tb))
    bad = problems(tb)
    for b in bad:
        print("FAIL", b)
    sys.exit(1 if bad else 0)
