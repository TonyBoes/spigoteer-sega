#!/usr/bin/env python3
"""Per-section frame cost (DIV ticks of 256 cycles) of boss fights, from a -DPERF_SECTIONS build (src/game.h SEC): which part of the frame got slower.

    GB_ROM=<tree>/<build>/game.gb tools/boss_sections.py <tree> --venues 9 7 --frames 600
"""
import argparse
import os
import sys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("tree")
    ap.add_argument("--model", default="cgb")
    ap.add_argument("--frames", type=int, default=600)
    ap.add_argument("--idle", action="store_true", help="no input, every regular removed every frame: the boss alone")
    ap.add_argument("--venues", type=int, nargs="+", default=[0])
    a = ap.parse_args()
    root = os.path.abspath(a.tree)
    os.chdir(root)
    sys.path.insert(0, os.path.join(root, "tests"))
    import perf_helpers as ph
    import boss_common as bc
    names = "FLUSH INPUT MUGS PATRONS COMPOSE QUEUE DRAW_BT DRAW_MUGS FX REST MUSIC LIFT ANIM DLIFT P1 P2 P3 P4 P5 P6 P7 P8 P9 P10 P11 P12".split()
    for c in a.venues:
        with bc.fight(a.model, c) as gb:
            gb.write("tip_chance", 0)
            ph.perf_reset(gb)
            tot = [0] * len(names)
            n = 0
            base = gb.addr("sec_done")
            sf = gb.read("sec_done", len(names))
            held = None
            for i in range(a.frames):
                want = None if a.idle else ph.SCRIPT[i % len(ph.SCRIPT)]
                if want != held:
                    if held:
                        gb.release(held)
                    if want:
                        gb.hold(want)
                    held = want
                gb.run(1)
                gb.write("lives", 3)
                if a.idle:
                    for q in range(16):
                        gb.write(gb.addr("patron_state") + q, 0)
                    gb.write("patrons_live", 0)
                if gb.mem("game_state") == 1 and gb.mem("intro_timer") == 0:
                    d = gb.read("sec_done", len(names))
                    for k in range(len(names)):
                        tot[k] += d[k]
                    n += 1
            print(f"venue {c} ({n} frames): " + " ".join(f"{names[k]}={tot[k] / n:.2f}" for k in range(len(names)) if tot[k]), flush=True)


if __name__ == "__main__":
    main()
