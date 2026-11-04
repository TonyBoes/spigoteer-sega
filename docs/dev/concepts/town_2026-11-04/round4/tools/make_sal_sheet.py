#!/usr/bin/env python3
"""Sal at night before/after (round 3 | round 4 scratch captures, INTRO p1 and p11), x6. Preview only.
    make_sal_sheet.py OUT.png"""
import subprocess
import sys
from pathlib import Path
from PIL import Image

TOWN = Path(__file__).resolve().parents[1]
REPO = TOWN.parents[1]
IN = TOWN / "sheet_in_r4"
IN.mkdir(exist_ok=True)
items = []
for page, f in (("p1", "INTRO_00"), ("p11", "INTRO_10")):
    for m, mm in (("cgb", "Color"), ("dmg", "DMG")):
        for r in ("r3", "r4"):
            p = IN / f"sal_{page}_{r}_{m}.png"
            Image.open(TOWN / f"cap_{r}" / m / f"{f}.png").convert("RGB").crop((128, 56, 160, 104)).save(p)
            items.append(f"{page} round {r[1]} {mm}={p}")
args = [sys.executable, str(REPO / "tools/dev/contact_sheet.py"), sys.argv[1], "--scale", "5", "--cols", "4",
        "--title", "Sal at night (INTRO p1, p11): round 3 | round 4"] + items
print(subprocess.run(args, capture_output=True, text=True).stdout.strip())
