#!/usr/bin/env python3
"""A real-speed APNG (60 frames a second, x2) of Last call's quota being met and the boss coming in, on PyBoy: the level stays on screen, his tiles stream in, his
entrance plays and (first time) his HOW TO PLAY card opens, is read and closed, and the fight goes on.

    tools/boss_apng.py <outdir> [--venue 0] [--models dmg cgb]
"""
import argparse
import os
import sys
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--venue", type=int, default=0)
    ap.add_argument("--models", nargs="+", default=["dmg", "cgb"])
    a = ap.parse_args()
    root = Path(__file__).resolve().parent.parent
    os.chdir(root)
    sys.path.insert(0, str(root / "tests"))
    from conftest import bk_block
    from test_boss_in_place import last_call, PAUSED, win, clear_bars
    from test_flow import state
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    for model in a.models:
        frames = []
        with last_call(model, a.venue, bk_block(0)) as gb:
            def snap():
                frames.append(gb.image().convert("RGB").resize((320, 288)))
            for _ in range(30):
                gb.run(1)
                snap()
            win(gb, a.venue, 2)
            card_seen = False
            closed_at = None
            for i in range(1400):
                gb.run(1)
                if i == 3 and not gb.mem("boss_on"):
                    clear_bars(gb)
                snap()
                if state(gb) == PAUSED:
                    card_seen = True
                    if i % 90 == 89:
                        gb.press("a", 2)                 # (turn the page / close it)
                elif card_seen and closed_at is None:
                    closed_at = i
                if closed_at is not None and i > closed_at + 120:
                    break
        path = out / f"boss_inplace_venue{a.venue}_{model}.png"
        frames[0].save(path, save_all=True, append_images=frames[1:], duration=17, loop=0, format="PNG")
        print(path, len(frames), "frames")


if __name__ == "__main__":
    main()
