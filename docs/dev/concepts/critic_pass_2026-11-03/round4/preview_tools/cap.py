#!/usr/bin/env python3
"""Capture the Food Critic's poses from a ROM (real engine, PyBoy). usage: cap.py ROM OUTDIR  -> OUTDIR/{dmg,cgb}_{POSE}.png (bar crop, 1x)
Poses WALK STOMP GULP_UP GULP GULP_SWAY GULP_END WINCE TASTE HOLD HOLDHOP HAPPY (the engine draws what it draws; nothing mocked here)."""
import os
import sys
from pathlib import Path

ROM, OUT = sys.argv[1], Path(sys.argv[2])
os.environ["GB_ROM"] = str(Path(ROM).resolve())
sys.path.insert(0, "/workspace/.claude/worktrees/agent-a781dd25b24512d04/out/sc/tests")
from boss_common import fight, frames, row, throw, block_empties, still_regulars, play, to_bar, until  # noqa: E402

OUT.mkdir(parents=True, exist_ok=True)
C = 3
R = row(C)
B = R["bar"]
Y0 = (5 + 3 * B) * 8 - 16
CROP = (0, Y0 + 6, 112, Y0 + 36)


def shot(gb, name, model):
    (OUT / f"{model}_{name}.x").write_text(str(gb.mem("boss_x")))
    gb.image().convert("RGB").crop(CROP).save(OUT / f"{model}_{name}.png")


def one(model):
    with fight(model, C) as gb:
        still_regulars(gb); play(gb); to_bar(gb, B); block_empties(gb)
        frames(gb, 30)
        shot(gb, "WALK", model)
        # STOMP
        until(gb, lambda: (gb.mem("boss_pose") & 15) == 1, 600)
        frames(gb, 1)
        shot(gb, "STOMP", model)
        until(gb, lambda: (gb.mem("boss_pose") & 15) == 0, 100)
        # WINCE
        gb.write("boss_push", 6); frames(gb, 1)
        shot(gb, "WINCE", model)
        gb.write("boss_push", 0); frames(gb, 3)
        # GULP: a perfect drink; sample the glass travel
        throw(gb, B, 72, perfect=True)
        until(gb, lambda: gb.mem("boss_hits") == 1, 40)
        until(gb, lambda: not gb.mem("boss_push"), 40)
        seen = {}
        for i in range(120):
            frames(gb, 1)
            if gb.mem("boss_state") != 1:   # BS_GULP
                break
            p = gb.mem("boss_pose") & 15
            t = gb.mem("boss_t")
            tag = None
            o = gb.oam()[29]
            if i == 50: tag = "GULP_END"
            elif i == 2: tag = "GULP_UP"
            elif i == 16 and p == 2: tag = "GULP"
            elif i >= 20 and p == 8: tag = "GULP_SWAY"
            if tag and tag not in seen:
                seen[tag] = i; shot(gb, tag, model)
        print(model, "gulp seen", seen, "t", gb.mem("boss_t"))
        frames(gb, 14)
        shot(gb, "HOLD", model)
        for _ in range(400):
            frames(gb, 1)
            if gb.mem("boss_xpose") == 7:
                break
        frames(gb, 1)
        shot(gb, "HOLDHOP", model)
        print(model, "xpose", gb.mem("boss_xpose"))
    with fight(model, C) as gb:
        still_regulars(gb); play(gb); to_bar(gb, B); block_empties(gb)
        frames(gb, 5)
        throw(gb, B, 72)
        for _ in range(60):
            frames(gb, 1)
            if gb.mem("crit_sloppy") == 1:
                break
        frames(gb, 10)
        shot(gb, "TASTE", model)
    with fight(model, C) as gb:
        still_regulars(gb); play(gb); to_bar(gb, B); block_empties(gb)
        frames(gb, 5)
        gb.write("boss_state", 5); frames(gb, 4)   # BS_OUTRO
        shot(gb, "HAPPY", model)


for m in ("dmg", "cgb"):
    one(m)
