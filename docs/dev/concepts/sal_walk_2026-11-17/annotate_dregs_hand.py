#!/usr/bin/env python3
"""Dregs's forward (right) hand in walk2 against idle, rows 13-18, x 6-15, at x20, the pixels that differ boxed. Preview only."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
font = ImageFont.load_default()


def frames(path):
    out, cur = [], None
    for line in path.read_text().split("\n"):
        if line.startswith(";"):
            continue
        if not line.strip():
            if cur:
                out.append(cur); cur = None
            continue
        (cur := cur or []).append(line)
    return out + ([cur] if cur else [])


pal = {"-": (240, 216, 160), "+": (176, 160, 184), "#": (32, 24, 40), ".": (48, 56, 72)}
d = frames(ROOT / "assets/art/dregs/dregs.txt")
S, X0, X1, R0, R1 = 20, 6, 16, 13, 19
im = Image.new("RGB", (2 * ((X1 - X0) * S + 20) + 10, (R1 - R0) * S + 96), (40, 40, 40))
dr = ImageDraw.Draw(im)
notes = ["idle: the right hand '--' (skin) is on x11-12, row 17, inside the arm, torso edge x10 is ink",
         "walk2: the forward hand moves IN one px to x10-11: it covers the torso's right edge pixel (x10), skin against the grey jacket and the ink hem, with ink outline x12-13 on its outer side. It does not leave the idle silhouette (x13 outline)."]
for k, fi in enumerate((0, 2)):
    ox = 10 + k * ((X1 - X0) * S + 20)
    dr.text((ox, 2), ("Dregs idle" if k == 0 else "Dregs walk2") + f" x{X0}-{X1 - 1}, rows {R0}-{R1 - 1}", fill=(235, 235, 235), font=font)
    for y in range(R0, R1):
        for x in range(X0, X1):
            box = [ox + (x - X0) * S, 14 + (y - R0) * S, ox + (x - X0) * S + S - 1, 14 + (y - R0) * S + S - 1]
            dr.rectangle(box, fill=pal[d[fi][y][x]])
            if fi and d[fi][y][x] != d[0][y][x]:
                dr.rectangle(box, outline=(255, 0, 255), width=2)
    words, line, y = notes[k].split(), "", 14 + (R1 - R0) * S + 6
    for w in words:
        if len(line) + len(w) > 36:
            dr.text((ox, y), line, fill=(200, 200, 120), font=font); y += 11; line = ""
        line += w + " "
    dr.text((ox, y), line, fill=(200, 200, 120), font=font)
im.save(OUT / "sal_walk_dregs_forward_hand_x20.png")
print("ok")
