#!/usr/bin/env python3
"""Round 5 | round 6 with roof | round 6 without roof, from the scratch-ROM capture sets (picture rows), Color over DMG,
x3. Preview only (crops and nearest-neighbour scaling; tools/dev/contact_sheet.py lays it out).   make_r6_sheet.py OUT.png"""
import subprocess
import sys
from pathlib import Path
from PIL import Image

TOWN = Path(__file__).resolve().parents[1]
REPO = TOWN.parents[1]
IN = TOWN / "sheet_in_r6"
IN.mkdir(exist_ok=True)
SETS = [("round 5", "cap_r5"), ("round 6 roof", "cap_r6r"), ("round 6 no roof", "cap_r6")]
PAGES = [("INTRO p1", "INTRO_00"), ("INTRO p11", "INTRO_10"), ("FINALE", "FINALE_A_00"), ("CREDITS", "CREDITS_00")]
items = []
for lab, f in PAGES:
    for m, mm in (("cgb", "Color"), ("dmg", "DMG")):
        for tag, d in SETS:
            im = Image.open(TOWN / d / m / f"{f}.png").convert("RGB").crop((0, 0, 160, 104))
            p = IN / f"{f}_{d}_{m}.png"
            im.resize((480, 312), Image.NEAREST).save(p)
            items.append(f"{lab} {tag} {mm}={p}")
args = [sys.executable, str(REPO / "tools/dev/contact_sheet.py"), sys.argv[1], "--scale", "1", "--cols", "3",
        "--title", "Town round 5 | round 6 roof | round 6 no roof (scratch ROM captures): Color over DMG, x3"] + items
print(subprocess.run(args, capture_output=True, text=True).stdout.strip())
