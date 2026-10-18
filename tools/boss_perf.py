#!/usr/bin/env python3
"""Frame time of every boss fight (src/boss.c) on PyBoy, from the game's own perf_end_last (tests/perf_helpers.py), for one source tree.

    tools/boss_perf.py <tree> [--models dmg cgb] [--frames 900] [--venues 0 1 ...] [--json out.json]

<tree> is a project root (this worktree, or a `git archive` of an older commit, built with `make`): its tests/ helpers start each fight
(boss_common.fight: Last call won, the level turned into his fight, started at once), so the same script measures the flow before and after
a restructure. The fight then runs `--frames` frames with the bartender's level-8 script (pour, serve, change bars; perf_helpers.SCRIPT), lives
topped up, only the PLAYING frames the game itself counts. Prints per boss: median, 90th percentile, worst end line and the late frames
(end line >= 144: the frame ran into the next VBlank).
"""
import argparse
import json
import os
import sys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("tree")
    ap.add_argument("--models", nargs="+", default=["dmg", "cgb"])
    ap.add_argument("--frames", type=int, default=900)
    ap.add_argument("--venues", type=int, nargs="*")
    ap.add_argument("--json")
    a = ap.parse_args()
    root = os.path.abspath(a.tree)
    os.chdir(root)
    sys.path.insert(0, os.path.join(root, "tests"))
    import perf_helpers as ph
    import boss_common as bc
    from test_story import BOSS_BUILT
    res = {}
    for model in a.models:
        for c in (a.venues if a.venues else sorted(BOSS_BUILT)):
            with bc.fight(model, c) as gb:
                gb.write("tip_chance", 0)
                ph.perf_reset(gb)
                ph.play_script(gb, a.frames, keep=lambda g, i: g.write("lives", 3))
                st = ph.perf_stats(gb)
                res[f"{model}/{c}"] = st
                print(model, c, st, flush=True)
    if a.json:
        json.dump(res, open(a.json, "w"), indent=1)


if __name__ == "__main__":
    main()
