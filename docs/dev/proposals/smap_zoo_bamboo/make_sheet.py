#!/usr/bin/env python3
"""The x4 close-up sheet (read-only on assets): NOW (the picture after smap_zoo_bush.py) | OPTION 1 | OPTION 2, Color on top, DMG below, with big labels.
    python3 docs/dev/proposals/smap_zoo_bamboo/make_sheet.py   (run from the repo root; writes pics/closeup_x4.png)"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from render import ROOT, crop  # noqa: E402

box = (1, 51, 11, 63)
srcs = [("NOW", ROOT / "assets" / "smap"), ("OPT 1", HERE / "build_1"), ("OPT 2", HERE / "build_2")]
S = 4
f = ImageFont.load_default(size=40)
pw, ph = (box[2] - box[0]) * 8 * S, (box[3] - box[1]) * 8 * S
W = 3 * pw + 4 * 12
H = 2 * (ph + 60) + 80
out = Image.new("RGB", (W, H), (30, 30, 30))
d = ImageDraw.Draw(out)
d.text((12, 10), "ZOO BAMBOO x4: Color top, DMG bottom", font=f, fill=(255, 255, 255))
for j, color in enumerate((True, False)):
    for i, (name, src) in enumerate(srcs):
        x, y = 12 + i * (pw + 12), 70 + j * (ph + 60)
        d.text((x, y), name + (" COLOR" if color else " DMG"), font=f, fill=(255, 220, 120))
        out.paste(crop(src, box, color).resize((pw, ph), Image.NEAREST), (x, y + 50))
(HERE / "pics").mkdir(exist_ok=True)
out.save(HERE / "pics" / "closeup_x4.png")
