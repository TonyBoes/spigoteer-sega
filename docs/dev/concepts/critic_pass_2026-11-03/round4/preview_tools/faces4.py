#!/usr/bin/env python3
"""faces4.py OUT.png: faces_1x_and_x8 for round 4 (preview only; draws the hand-typed grids, decides no pixel).
Top: the WALK face (rows 0-10, cols 0-24) at x8, now | F1 | F2 | F3, DMG row over Color row.
Bottom: every pose at true 1x per version (one line per version and machine), then the same at x2, for the stranger test."""
import sys
from pathlib import Path

from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import crit_tool as c  # noqa: E402

R4 = HERE.parent
VERS = [("now", "cur"), ("F1 hmph", str(R4 / "F1.txt")), ("F2 cocked brow", str(R4 / "F2.txt")), ("F3 side-eye", str(R4 / "F3.txt"))]
POSES = ["WALK", "GULP", "WINCE", "HAPPY", "TASTE", "HOLD"]
PALS = [("DMG", c.DMG, False), ("Color", c.CGB, True)]
BG = (40, 40, 40)
FG = (235, 235, 235)


def fig(rows, pal, s, cg, name, mock):
    im = c.draw_pose(rows, pal, s).crop((0, 2 * s, 32 * s, 18 * s))
    if mock and name in c.GLASS:
        t = c.draw_pose(rows, pal, s)
        c.paste_glass(t, s, c.GLASS[name][0], cg, c.GLASS[name][1])
        im = t.crop((0, 2 * s, 32 * s, 18 * s))
    return im


loaded = {lab: c.load(v) for lab, v in VERS}
S = 8
fw, fh = 25 * S, 11 * S
blocks = []
# x8 faces
top = Image.new("RGB", (4 * (fw + 12) + 60, 2 * (fh + 6) + 20), BG)
d = ImageDraw.Draw(top)
for k, (lab, _) in enumerate(VERS):
    d.text((60 + k * (fw + 12), 4), lab + "  WALK x8", fill=FG)
    for m, (pn, pal, cg) in enumerate(PALS):
        f = fig(loaded[lab]["WALK"], pal, S, cg, "WALK", False).crop((0, 0, fw, fh))
        top.paste(f, (60 + k * (fw + 12), 18 + m * (fh + 6)))
for m, (pn, _, _) in enumerate(PALS):
    d.text((4, 18 + m * (fh + 6) + fh // 2), pn, fill=FG)
blocks.append(top)
# 1x and x2 lines
for s in (1, 2):
    gap = 6 * s
    lw = 60 + len(POSES) * (32 * s + gap)
    band = Image.new("RGB", (lw, 14 + len(VERS) * 2 * (16 * s + 4)), BG)
    d = ImageDraw.Draw(band)
    d.text((4, 2), f"every pose at {'true 1x' if s == 1 else 'x2'}: " + " ".join(POSES), fill=FG)
    y = 14
    for lab, _ in VERS:
        for pn, pal, cg in PALS:
            d.text((4, y + 16 * s // 2 - 5), f"{lab.split()[0]} {pn}", fill=FG)
            strip = Image.new("RGB", (len(POSES) * (32 * s + gap), 16 * s), pal["."])
            for i, n in enumerate(POSES):
                strip.paste(fig(loaded[lab][n], pal, s, cg, n, lab != "now"), (i * (32 * s + gap), 0))
            band.paste(strip, (60, y))
            y += 16 * s + 4
    blocks.append(band)
W = max(b.width for b in blocks)
H = sum(b.height + 8 for b in blocks)
out = Image.new("RGB", (W, H), BG)
y = 0
for b in blocks:
    out.paste(b, (0, y))
    y += b.height + 8
out.save(sys.argv[1])
print("wrote", sys.argv[1], out.size)
