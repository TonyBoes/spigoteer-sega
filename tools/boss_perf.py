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
    ap.add_argument("--seeds", type=int, nargs="*", default=[None], help="rng_state pokes at the fight's start (one run each; the numbers are pooled)")
    ap.add_argument("--idle", action="store_true", help="the boss alone: no input, every regular removed every frame (deterministic: what tests/test_boss_in_place.py guards)")
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
            pool = []
            for seed in a.seeds:
                with bc.fight(model, c) as gb:
                    gb.write("tip_chance", 0)
                    if seed is not None:
                        gb.write("rng_state", seed)
                    ph.perf_reset(gb)
                    if a.idle:
                        for _ in range(a.frames):
                            gb.run(1)
                            ph.sample(gb)
                            gb.write("lives", 3)
                            for q in range(16):
                                gb.write(gb.addr("patron_state") + q, 0)
                            gb.write("patrons_live", 0)
                    else:
                        ph.play_script(gb, a.frames, keep=lambda g, i: g.write("lives", 3))
                    pool += gb.perf_samples
            gb.perf_samples = pool
            st = ph.perf_stats(gb)
            res[f"{model}/{c}"] = st
            print(model, c, st, flush=True)
    if a.json:
        json.dump(res, open(a.json, "w"), indent=1)


if __name__ == "__main__":
    main()
