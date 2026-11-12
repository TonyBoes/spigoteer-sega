#!/usr/bin/env python3
"""The map walk's numbers over every leg both ways, from a ROM (GB_ROM) and its symbols (GB_NOI): px per frame, holds, late frames, the logic's lines per frame (p90, worst).

    GB_ROM=out/base_game.gb GB_NOI=out/base_game.noi python3 tools/dev/smap_walk_numbers.py dmg cgb     # main's ROM
    python3 tools/dev/smap_walk_numbers.py dmg cgb                                                       # build/game.gb

Color runs at double speed as shipped (owner Q92).  The same hook as tests/test_story_map_world.py walk_frames (a hook on walk_step: one record per game frame)."""
import contextlib
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tests"))

import test_story_map as sm                      # noqa: E402
import test_story_map_world as tw                # noqa: E402
from conftest import double_speed                # noqa: E402

SV, V_LAG, V_FX, V_FY, V_CAMX, V_CAMY, V_WALK = 396, 0, 16, 18, 12, 14, 20
for _n, _v in (("V_LAG", tw.V_LAG),):
    V_LAG = _v


def var(sc, n):
    return sc[SV + n] | sc[SV + n + 1] << 8


def walk_log(model, s, d, noi):
    v = int(re.search(r"DEF _walk_step (0x[0-9A-F]+)", noi).group(1), 16)
    with double_speed() if model == "cgb" else contextlib.nullcontext():
        gb = sm.to_map(model, 10, stop=s)
    log = []

    def f(ctx):
        sc = gb.read("story_scratch", 520)
        log.append((sc[SV + V_LAG], gb.mem16("perf_end_last"), gb.mem16("perf_logic_last"), var(sc, V_FX), var(sc, V_FY)))
    gb.pb.hook_register(v >> 16, v & 0xFFFF, f, None)
    gb.press(tw.DIRS[d], 6)
    log.clear()
    started = False
    for fr in range(1500):
        gb.run(1, True)
        w = bool(gb.read("story_scratch", 520)[SV + V_WALK])
        started = started or w
        if fr > 4 and started and not w:
            break
    return log[1:]


def main(models):
    noi = Path(os.environ.get("GB_NOI", ROOT / "build" / "game.noi")).read_text()
    for model in models:
        frames = px = holds = late = 0
        lines, worst_end = [], 0
        for s, d in tw.LEG_WALKS:
            log = walk_log(model, s, d, noi)
            frames += len(log)
            holds += sum(1 for r in log if r[0] & 1)
            late += sum(1 for r in log if r[1] >= 154)
            worst_end = max([worst_end] + [r[1] for r in log])
            lines += [r[2] for r in log[2:]]
            px += sum(abs(b[3] - a[3]) + abs(b[4] - a[4]) for a, b in zip(log, log[1:]))
        lines.sort()
        print(f"{model}: frames {frames}, px/frame {px / frames:.3f}, holds {holds}, late {late}, logic lines p90 {lines[len(lines) * 9 // 10]}, worst {lines[-1]}, worst frame end {worst_end}")


if __name__ == "__main__":
    main(sys.argv[1:] or ["dmg", "cgb"])
