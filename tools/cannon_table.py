#!/usr/bin/env python3
"""T-Shirt Cannon's landing table (docs/minigames_bosses.md 4.2; src/ts.c): simulates every (angle, power) shot of the aim and the meter with the
game's own integer physics and checks the fairness rule. tools/gen_ts.py imports this and fails the build when the rule breaks; the same numbers
go to build/ts.json for tests/test_mg_tshirt.py.

The aim: Up / Down step the barrel through ANGLES (45, 52, 60, 68 degrees: the four barrel looks of assets/art/tshirt/cannon.txt, each with its own
muzzle). The golf-style power meter p = 0 .. PMAX sets the launch speed, v = V0 + DV p (8.8 px/f): with vh = v >> 3 the velocity is
vx = (vh COS[a]) >> 5, vy = -((vh SIN[a]) >> 5) (COS, SIN = 256 cos, 256 sin: 8 bits, so the game multiplies 8 x 8 bits), gravity 1/16 px/f^2
(16 in 8.8). One step a frame: x += vx; y += vy; vy += 16; then the shirt's centre is looked up:
 - in a stand column 9-19 (its top row is 11 - (c - 9) / 2) at or below the column's top and above the ad boards (y 104): the CROWD is hit
   (column c - 9); the shirt is FALLING (vy > 0 after the step) or still rising: only a falling shirt can be caught (a flat shot smacks the stand);
 - in the stand at the ad boards (y >= 104) or anywhere down at y 124 (the grass): SHORT;
 - at x >= 168 (past the last column, over the stand): OVER.

Why the falling rule: the stand is a staircase, so a shot at ANY angle lands where it crosses the stand's surface, and the power needed for a column
barely depends on the angle (45 vs 68 degrees shifts a column's window by 3-8 power steps). What the angle changes is HOW the shirt arrives: a flat
shot (45 degrees) crosses most of the stand while still rising and cannot be caught there (only the near and the far columns, where it has topped
out); a lob (52 and up) is falling everywhere. Higher also means a longer flight (47 .. 93 frames: the fan's hands may come down), a bigger short
zone and narrower windows.

Fairness rule: (a) at every angle the meter starts with at least SHORT_MIN steps of short and ends with at least OVER_MIN steps of over (the oops
zones the owner asked for), (b) every stand column 0-10 is hit by some shot, (c) a raised fan reaches the column on each side, so the powers that
catch it span at least REACH_MIN steps at each of the lobs (52 and up) and at least ANGLES_MIN of the 4 angles catch every fan at all (a fan can be
reached by more than one combination), (d) no flight is longer than 120 frames.
"""
import json
import math
import sys

V0, DV, PMAX = 224, 13, 63
ANGLES = (45, 52, 60, 68)
COS = tuple(round(256 * math.cos(math.radians(a))) for a in ANGLES)
SIN = tuple(round(256 * math.sin(math.radians(a))) for a in ANGLES)
MUZZLES = ((44, 107), (44, 106), (43, 105), (41, 105))   # barrel tip (px) of each look (assets/art/tshirt/cannon.txt)
START_ANGLE = 2              # 60 degrees
CANNON_XY = (32, 104)        # the sprite's top-left
FAN_FIRST, FAN_N = 9, 11
BOARD_Y, LAND_Y, OUT_X = 104, 124, 168
SHORT_MIN, OVER_MIN, REACH_MIN, ANGLES_MIN = 8, 6, 5, 3
SHORT, CROWD, OVER = 0, 1, 2


def top_row(c):
    return 11 - (c - FAN_FIRST) // 2


def velocity(a, p):
    vh = (V0 + DV * p) >> 3
    return (vh * COS[a]) >> 5, -((vh * SIN[a]) >> 5)


def fly(a, p):
    """-> (SHORT | CROWD | OVER, column 0-10 (CROWD) else 0, frames of flight, 1 if the shirt was falling when it hit the crowd) for angle a, power p."""
    x, y = MUZZLES[a][0] << 8, MUZZLES[a][1] << 8
    vx, vy = velocity(a, p)
    for t in range(1, 400):
        x += vx
        y += vy
        vy += 16
        px, py = x >> 8, y >> 8
        c = px >> 3
        if FAN_FIRST <= c < FAN_FIRST + FAN_N:
            top = top_row(c) * 8
            if top <= py < BOARD_Y:
                return CROWD, c - FAN_FIRST, t, 1 if vy > 0 else 0
            if py >= BOARD_Y:
                return SHORT, 0, t, 0
        if px >= OUT_X:
            return OVER, 0, t, 0
        if py >= LAND_Y:
            return SHORT, 0, t, 0
    return OVER, 0, 400, 0


def table():
    """[angle][power] -> fly()."""
    return [[fly(a, p) for p in range(PMAX + 1)] for a in range(len(ANGLES))]


def zones(t):
    """-> ([the last short power per angle], [the first over power per angle])."""
    sm, om = [], []
    for row in t:
        sm.append(max(p for p, r in enumerate(row) if all(q[0] == SHORT for q in row[:p + 1])))
        om.append(min(p for p, r in enumerate(row) if all(q[0] == OVER for q in row[p:])))
    return sm, om


def windows(row):
    """-> {column: number of powers of this angle that hit it while the shirt is falling}."""
    w = {c: 0 for c in range(FAN_N)}
    for k, c, _, f in row:
        if k == CROWD and f:
            w[c] += 1
    return w


def reach(row, c):
    """Powers of this angle that a raised fan in column c catches (its own column and one each side, a falling shirt)."""
    return sum(1 for k, cc, _, f in row if k == CROWD and f and abs(cc - c) <= 1)


def problems(t):
    out = []
    sm, om = zones(t)
    for a, ang in enumerate(ANGLES):
        if sm[a] + 1 < SHORT_MIN:
            out.append(f"{ang} degrees: only {sm[a] + 1} steps of short (need {SHORT_MIN})")
        if PMAX + 1 - om[a] < OVER_MIN:
            out.append(f"{ang} degrees: only {PMAX + 1 - om[a]} steps of over (need {OVER_MIN})")
        for p, (k, c, n, f) in enumerate(t[a]):
            if n > 120:
                out.append(f"{ang} degrees, power {p}: the flight takes {n} frames")
    for c in range(FAN_N):
        if not any(k == CROWD and cc == c for row in t for k, cc, _, _ in row):
            out.append(f"column {c} cannot be hit")
        got = [a for a in range(len(ANGLES)) if reach(t[a], c) >= 1]
        if len(got) < ANGLES_MIN:
            out.append(f"a raised fan in column {c} is caught at only {len(got)} angles (need {ANGLES_MIN})")
        for a in range(1, len(ANGLES)):
            if reach(t[a], c) < REACH_MIN:
                out.append(f"a raised fan in column {c} is caught by only {reach(t[a], c)} powers at {ANGLES[a]} degrees (need {REACH_MIN})")
    return out


def report(t):
    sm, om = zones(t)
    lines = [f"universal red on the meter: short 0-{min(sm)}, over {max(om)}-{PMAX}"]
    for a, ang in enumerate(ANGLES):
        w = windows(t[a])
        lines.append(f"{ang}: short 0-{sm[a]}, over {om[a]}-{PMAX}, falling windows " + " ".join(f"c{c}:{n}" for c, n in w.items()) +
                     " | reach " + " ".join(f"c{c}:{reach(t[a], c)}" for c in range(FAN_N)) + f" | longest flight {max(r[2] for r in t[a])}")
    return "\n".join(lines)


def to_json(t):
    sm, om = zones(t)
    return {"v0": V0, "dv": DV, "pmax": PMAX, "angles": list(ANGLES), "cos": list(COS), "sin": list(SIN), "muzzles": [list(m) for m in MUZZLES],
            "start_angle": START_ANGLE, "cannon": list(CANNON_XY), "grav": 16, "board_y": BOARD_Y, "land_y": LAND_Y, "out_x": OUT_X,
            "short_max": sm, "over_min": om, "red_short": min(sm), "red_over": max(om),
            "table": [[list(r) for r in row] for row in t],
            "vel": [[list(velocity(a, p)) for p in range(PMAX + 1)] for a in range(len(ANGLES))]}


if __name__ == "__main__":
    tb = table()
    print(report(tb))
    bad = problems(tb)
    for b in bad:
        print("FAIL", b)
    sys.exit(1 if bad else 0)
