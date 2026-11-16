#!/usr/bin/env python3
"""Overrun / drift probe of the credits roll (any CRSCENE / CRSPLIT build).

    GB_ROM=out/b_split/game-unlocked.gb python3 tools/dev/credits_overrun_probe.py cgb|dmg [--ds]

Counts the frames of the whole roll that ran past their VBlank (two frames between two vq_frame_begin calls), the 3+ gaps (the first screen's build is one),
the music ticks' longest interval (frames; the test's limit is 1.6) and the drift of the tune against the frames. --ds runs a Color at double speed as shipped
(the default is the tests' normal speed). Reads the ROM, writes nothing."""
import os
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tests"))
if "--ds" in sys.argv:
    os.environ["GB_DOUBLE_SPEED"] = "1"
from test_credits import *      # noqa: E402,F401,F403
from tick_helpers import FRAME, tick_log      # noqa: E402

model = sys.argv[1]
with Rom(ROM, model) as gb:
    gb.run(120)
    gb.model_name = model
    hold_stage_anim(gb)
    stamps = tick_log(gb)
    noi = ROM.with_suffix(".noi").read_text()
    v = int([x for x in noi.splitlines() if x.startswith("DEF _vq_frame_begin ")][0].split()[2], 16)
    loops = []
    gb.pb.hook_register(v >> 16, v & 0xFFFF, lambda ctx: loops.append((gb.pb._cycles(), bytes(gb.pb.memory[gb.addr('story_scratch') + 38:gb.addr('story_scratch') + 63]))), None)
    title_pick(gb, K_BONUS, K_CREDITS)
    run_until(gb, lambda: gb.mem("story_phase") == SP_CREDITS, 20)
    n0 = len(stamps)
    loops.clear()
    while gb.mem("cur_tune") == TUNE_CREDITS and len(stamps) - n0 < 11000:
        gb.run(1)
    s = stamps[n0:][3:]
    iv = [(b - a) / FRAME for a, b in zip(s, s[1:])]
    gaps = Counter(round((loops[i + 1][0] - loops[i][0]) / FRAME) for i in range(len(loops) - 1))
    print(ROM.name, model, "overruns (2-frame loop gaps)", gaps.get(2, 0), "3+", sum(c for k, c in gaps.items() if k > 2),
          "max interval", round(max(iv[:-1]), 2), "drift", round((s[-1] - s[0]) / FRAME - (len(s) - 1), 2))
