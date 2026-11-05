#!/usr/bin/env python3
"""Fit the story map's walking pace (tools/smap_gear.json) to what the streaming can keep up with.

Every leg of the map is walked, on the real ROM (PyBoy), both ways, on a DMG and on a Color at double speed (the way it ships). For each stretch of each leg the walk's hold frames
(Sal waited for the camera: the stream was behind) and late frames (the frame's logic ran past line 154) are counted. A stretch that had any goes one level down: 2 px a frame, then
1, then 1 px every other frame. The ROM is rebuilt (make) and the legs are walked again, until no stretch has a hold or a late frame (or the lowest level fails).

    python3 tools/dev/smap_gear.py [--rounds N] [--measure-only]

It rewrites tools/smap_gear.json (the levels of each model's stretches); gen_smap_world.py packs them into build/smap_world.h (smapw_gear). Run it again after any change
to the engine (src/smap*.c), the world or the art that moves the streaming's cost. tests/test_story_map_world.py holds the result to zero holds and zero late frames.
"""
import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "tests"))
os.chdir(ROOT)
GEAR = ROOT / "tools" / "smap_gear.json"
DIRS = ["up", "down", "left", "right"]


def measure(model):
    """-> {(leg, stretch): [frames, holds, late]} over every walk of the map (stretch s ends at waypoint s of the leg)."""
    import conftest
    import test_story_map as t
    noi = (ROOT / "build" / "game.noi").read_text()
    v = int(re.search(r"DEF _walk_step (0x[0-9A-F]+)", noi).group(1), 16)
    world = json.loads((ROOT / "build" / "smap_world.json").read_text())
    out = {}
    for s in range(11):
        for d in range(4):
            if world["exits"][s][d] == 255:
                continue
            with conftest.double_speed():
                rom = t.to_map(model, 10, stop=s)
            log = []

            def f(ctx, rom=rom, log=log):
                sc = rom.read("story_scratch", 520)
                V = lambda n: sc[396 + n]
                log.append((V(21), V(22), V(23), V(65), rom.mem16("perf_end_last"), V(20)))

            rom.pb.hook_register(v >> 16, v & 0xFFFF, f, None)
            rom.press(DIRS[d], 6)
            log.clear()
            for fr in range(1500):
                rom.run(1, True)
                if fr > 4 and not rom.read("story_scratch", 520)[396 + 20]:
                    break
            for leg, rev, wk, lag, end, walking in log[1:]:
                stretch = wk + 1 if rev else wk
                e = out.setdefault((leg, stretch), [0, 0, 0])
                e[0] += 1
                e[1] += lag > 0
                e[2] += end >= 154
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rounds", type=int, default=8)
    ap.add_argument("--measure-only", action="store_true")
    ap.add_argument("--models", default="dmg,cgb")
    a = ap.parse_args()
    models = a.models.split(",")
    for rnd in range(a.rounds):
        gear = json.loads(GEAR.read_text())
        changed = 0
        for m in models:
            res = measure(m)
            tot = [sum(r[i] for r in res.values()) for i in range(3)]
            bad = sorted(k for k, r in res.items() if r[1] or r[2])
            print(f"round {rnd} {m}: frames {tot[0]} holds {tot[1]} late {tot[2]}; stretches with trouble: {bad}", flush=True)
            for leg, s in bad:
                if gear[m][leg][s - 1] > 0 and not a.measure_only:
                    gear[m][leg][s - 1] -= 1
                    changed += 1
        if not changed:
            break
        GEAR.write_text("{" + ",\n ".join(f'"{m}": ' + json.dumps(gear[m]) for m in ("dmg", "cgb")) + "}\n")
        subprocess.run(["touch", str(ROOT / "src" / "smap.c")], check=True)
        subprocess.run(["make"], check=True, stdout=subprocess.DEVNULL)


if __name__ == "__main__":
    main()
