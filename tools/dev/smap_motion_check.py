#!/usr/bin/env python3
"""Sal's pace on a story-map walk: pixels moved per frame, one digit a frame, from the real ROM (build/game.gb; Color runs at double speed as shipped).

    python3 tools/dev/smap_motion_check.py MODEL:STOP:DIR [...]      # e.g. cgb:8:0 cgb:9:1 (DIR 0 up, 1 down, 2 left, 3 right)

Prints each leg's string; exit 1 if Sal stood still (a 0 px frame) between his first and his last step of a leg. A lone 1 is fine (the ease at the ends, the odd pixel).
"""
import contextlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tests"))

import test_story_map as sm                      # noqa: E402
from conftest import double_speed                # noqa: E402

SV = 396
V_WALK, V_CAMX, V_CAMY, V_FX, V_FY = 20, 12, 14, 16, 18
DIRS = ("up", "down", "left", "right")


def _var(sc, n):
    return sc[SV + n] | sc[SV + n + 1] << 8


def walk_steps(model, stop, d):
    """Sal's px moved on each frame of the walk from `stop` in direction d (0 up, 1 down, 2 left, 3 right), as a list."""
    ctx = double_speed() if model == "cgb" else contextlib.nullcontext()
    with ctx:
        gb = sm.to_map(model, 10, stop=stop)
    gb.press(DIRS[d], 6)
    pos, started = [], False
    for fr in range(1500):
        gb.run(1, True)
        sc = gb.read("story_scratch", 520)
        walking = bool(sc[SV + V_WALK])
        started = started or walking
        if started:
            pos.append((_var(sc, V_FX), _var(sc, V_FY)))
        if fr > 4 and started and not walking:
            break
    return [abs(b[0] - a[0]) + abs(b[1] - a[1]) for a, b in zip(pos, pos[1:])]


def mid_walk_stops(steps):
    """Indexes of the 0 px frames between the first and the last frame in which Sal moved."""
    moving = [i for i, s in enumerate(steps) if s]
    if not moving:
        return list(range(len(steps)))
    return [i for i in range(moving[0], moving[-1] + 1) if not steps[i]]


def main(argv):
    bad = 0
    if argv == ["--all"]:                          # every Color leg, both ways: the 11 stops' open exits
        argv = [f"cgb:{s}:{d}" for s in range(11) for d in range(4) if sm.EXITS[s][d] != 255]
    for arg in argv:
        model, stop, d = arg.split(":")
        steps = walk_steps(model, int(stop), int(d))
        s = "".join(str(min(x, 9)) for x in steps)
        stops = mid_walk_stops(steps)
        print(f"{model} stop {stop} {DIRS[int(d)]}: {len(steps) + 1} frames, Sal px per frame:" + ("" if not stops else f"   STOPS at frames {stops}"))
        for i in range(0, len(s), 80):
            print("  ", s[i:i + 80])
        bad += bool(stops)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
