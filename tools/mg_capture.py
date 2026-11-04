#!/usr/bin/env python3
"""Stills of a mini-game on SameBoy (the timing truth: mid-frame palette / scroll effects show here, not in PyBoy).

gbcheck / sameboy_tester save only the last frame of a whole-second run, so this patches the AUTO_MG ROM (src/debug.c auto_mg) and runs it for
several lengths. The hook boots, enters game ID at frame 100 + delay (the full card first with --card), plays a fixed button pattern, and at
play frame 4*END forces the timer out with a score of 16*SCORE.

    make BUILD=out/mgc/build OUT=out/mgc/out DEBUGFLAGS="-DDEBUG_MENU -DAUTO_MG"
    tools/mg_capture.py out/mgc/build/game.gb out/mgc/shots --games 7,0 --models cgb,dmg [--mode 1] [--secs 2 4 6 ...] [--delays 0] [--score 200]

Writes <out>/<game>_<model>_s<secs>_d<delay>.png (x1). CGB runs at double speed (ROM byte 0x3FFE 0xFF) unless --normal.
"""
import argparse
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image

NAMES = {0: "qd", 1: "ts", 2: "lr", 3: "ou", 4: "mm", 5: "bs", 6: "mr", 7: "tk", 8: "mk", 9: "ad", 11: "po", 12: "b0", 13: "b1", 14: "b2"}


def one(data, game, model, secs, delay, a, out):
    with tempfile.TemporaryDirectory() as td:
        rom = Path(td) / "r.gb"
        b = bytearray(data)
        b[0x3FFF] = delay if delay else 0xFF
        b[0x3FFE] = 0 if a.normal else 0xFF
        b[0x3FFD] = game
        b[0x3FFC] = a.mode
        b[0x3FFB] = a.end
        b[0x3FFA] = a.score
        b[0x3FF9] = 1 if a.card else 0
        b[0x3FF8] = 2 if a.story else 1 if a.list else 0
        rom.write_bytes(b)
        subprocess.run(["sameboy_tester", f"--{model}", "--length", str(secs), str(rom)], capture_output=True, timeout=600)
        png = out / f"{NAMES[game]}_{model}_s{secs}_d{delay:02d}.png"
        Image.open(rom.with_suffix(".bmp")).convert("RGB").save(png)
        return png


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("rom")
    ap.add_argument("out")
    ap.add_argument("--games", default=",".join(map(str, NAMES)))
    ap.add_argument("--models", default="cgb,dmg")
    ap.add_argument("--mode", type=int, default=1)
    ap.add_argument("--secs", type=int, nargs="+", default=[2, 4, 5, 6, 7, 8, 9, 10, 12, 16])
    ap.add_argument("--delays", type=int, nargs="+", default=[0])
    ap.add_argument("--end", type=int, default=50)
    ap.add_argument("--score", type=int, default=200)
    ap.add_argument("--card", action="store_true")
    ap.add_argument("--list", action="store_true", help="enter through BONUS > MINI GAMES (the player's way)")
    ap.add_argument("--story", action="store_true", help="the story's mini-game step of chapter GAME (ids 0-9)")
    ap.add_argument("--normal", action="store_true")
    ap.add_argument("--jobs", type=int, default=6)
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    data = Path(a.rom).read_bytes()
    jobs = [(int(g), m, s, d) for g in a.games.split(",") for m in a.models.split(",") for s in a.secs for d in a.delays]
    with ThreadPoolExecutor(a.jobs) as ex:
        list(ex.map(lambda j: one(data, j[0], j[1], j[2], j[3], a, out), jobs))
    print(f"{len(jobs)} frames in {out}")


if __name__ == "__main__":
    sys.exit(main())
