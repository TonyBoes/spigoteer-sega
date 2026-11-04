#!/usr/bin/env python3
"""Preview: crop one region (x0,y0,x1,y1 in picture pixels) out of several pictures (CGB and DMG renders) into one
labelled contact sheet.   crop_sheet.py OUT.png X0,Y0,X1,Y1 SCALE PIC.txt [PIC.txt ...]"""
import subprocess
import sys
from pathlib import Path

T = Path(__file__).resolve().parent
sys.path.insert(0, str(T))
from render_v2 import parse, render   # noqa: E402

out, box, sc = sys.argv[1], tuple(int(v) for v in sys.argv[2].split(",")), sys.argv[3]
tmp = Path(out).parent / "crop_in"
tmp.mkdir(exist_ok=True)
items = []
for src in sys.argv[4:]:
    key, pix = parse(src)
    stem = Path(src).parent.name + "_" + Path(src).stem
    for dmg in (False, True):
        p = tmp / f"{stem}_{'dmg' if dmg else 'cgb'}.png"
        render(key, pix, 1, dmg=dmg).crop(box).save(p)
        items.append(f"{stem} {'DMG' if dmg else 'Color'}={p}")
subprocess.run([sys.executable, str(T.parents[2] / "tools/dev/contact_sheet.py"), out, "--scale", sc, "--cols", "4"] + items)
