#!/usr/bin/env python3
"""mkcells.py OUTDIR VER... : crop the captures out/cap_<VER>/<model>_<POSE>.png to his bar (x 8..64), mock the (not yet engine-drawn)
empty glass sprite over the HOLD / HOLDHOP hand of a proposal, write OUTDIR/<VER>_<model>_<POSE>.png"""
import sys
from pathlib import Path
from PIL import Image

OUT = Path(sys.argv[1])
OUT.mkdir(parents=True, exist_ok=True)
GE = ["........", "........", "........", "........", ".#-..-#.", ".#....#.", ".#....#.", ".#....#.", ".#....#.", "..#..#..", "...##...", "...##...", "...##...", "...##...", ".######.", "........"]
PAL = {"cgb": {"-": (0xF0, 0xF0, 0xF8), "+": (0xC8, 0xD0, 0xE0), "#": (0x30, 0x30, 0x48)}, "dmg": {"-": (255, 255, 255), "+": (153, 153, 153), "#": (0, 0, 0)}}
POSES = ["WALK", "STOMP", "GULP_UP", "GULP", "GULP_SWAY", "GULP_END", "WINCE", "HAPPY", "TASTE", "HOLD", "HOLDHOP"]
BODY_TOP = 10      # body row 0 in the capture (crop y)
for ver in sys.argv[2:]:
    for model in ("dmg", "cgb"):
        for p in POSES:
            f = Path(f"/workspace/.claude/worktrees/agent-a781dd25b24512d04/out/cap_{ver}/{model}_{p}.png")
            if p == "HOLDHOP":
                f = f.with_name(f"{model}_HOLDHOP.png")
            im = Image.open(f).convert("RGB")
            bx = int((f.with_suffix(".x")).read_text())
            if ver != "cur" and p in ("HOLD", "HOLDHOP"):
                dy = 1 if p == "HOLDHOP" else 0
                for y, r in enumerate(GE):
                    for x, c in enumerate(r):
                        if c != ".":
                            im.putpixel((bx + 24 + x, BODY_TOP - 2 + dy + y), PAL[model][c])
            im.crop((8, 0, 72, 30)).save(OUT / f"{ver}_{model}_{p}.png")
print("ok")
