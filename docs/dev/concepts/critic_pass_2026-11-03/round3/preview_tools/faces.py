#!/usr/bin/env python3
"""faces.py OUT.png [scale]: the face and hands of every pose, columns now | round 2 A | A3, Color over DMG, x8 (a preview of the
hand-typed grids: this only draws them; the HOLD / HAPPY / GULP glass sprite is mocked where the engine would draw it)."""
import sys
from pathlib import Path

from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import crit_tool as c  # noqa: E402

out = sys.argv[1]
s = int(sys.argv[2]) if len(sys.argv) > 2 else 8
R2 = HERE.parents[1] / "round2" / "A.txt"
VERS = [("now", "cur"), ("round 2 A", str(R2)), ("A3", str(HERE.parent / "A3.txt"))]
POSES = ["WALK", "STOMP", "GULP", "WINCE", "HAPPY", "TASTE", "HOLD"]
loaded = {lab: c.load(v) for lab, v in VERS}
w, h = 30 * s, 16 * s
cell_w, cell_h = w + 6, 2 * h + 8
im = Image.new("RGB", (len(VERS) * cell_w, len(POSES) * cell_h), (70, 70, 70))
d = ImageDraw.Draw(im)
for r, p in enumerate(POSES):
    for k, (lab, v) in enumerate(VERS):
        for m, (pal, cg) in enumerate(((c.CGB, True), (c.DMG, False))):
            t = c.draw_pose(loaded[lab][p], pal, s)
            if lab != "now" and p in c.GLASS:
                c.paste_glass(t, s, c.GLASS[p][0], cg, c.GLASS[p][1])
            t = t.crop((2 * s, 2 * s, 32 * s, 18 * s))
            im.paste(t, (k * cell_w, r * cell_h + m * (h + 2)))
        ImageDraw.Draw(im).text((k * cell_w + 3, r * cell_h + 2), f"{lab} {p}", fill=(255, 255, 0))
im.save(out)
print("wrote", out, im.size)
