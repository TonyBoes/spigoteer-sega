#!/usr/bin/env python3
"""Dregs's idle / walk1 / walk2 arm rows at x12, the pixels that differ from idle boxed (magenta), with a note per frame.
Preview only.  Run from the repo root."""
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
S, R0, R1 = 12, 10, 19
notes = ["idle: both arms hang, hands '-' on row 17",
         "walk1: left arm 1 px out from row 14 and its hand '-' one row HIGHER (row 16), free of the hem = FORWARD; right hand stays on row 17 (rest height), arm 1 px out = BACK",
         "walk2: left arm ends at row 15, hand gone behind the body (tucked); right hand on row 17, outline 1 px out. The left arm is the high one in both frames"]
W = 16 * S
im = Image.new("RGB", (3 * (W + 12) + 12, (R1 - R0) * S + 100), (40, 40, 40))
dr = ImageDraw.Draw(im)
for k in range(3):
    ox = 12 + k * (W + 12)
    for y in range(R0, R1):
        for x in range(16):
            dr.rectangle([ox + x * S, 14 + (y - R0) * S, ox + x * S + S - 1, 14 + (y - R0) * S + S - 1], fill=pal[d[k][y][x]])
            if d[k][y][x] != d[0][y][x]:
                dr.rectangle([ox + x * S, 14 + (y - R0) * S, ox + x * S + S - 1, 14 + (y - R0) * S + S - 1], outline=(255, 0, 255))
    dr.text((ox, 2), ["Dregs idle", "Dregs walk1", "Dregs walk2"][k] + f" (rows {R0}-{R1 - 1})", fill=(235, 235, 235), font=font)
    # wrap the note
    words, line, y = notes[k].split(), "", 14 + (R1 - R0) * S + 6
    for w in words:
        if len(line) + len(w) > 34:
            dr.text((ox, y), line, fill=(200, 200, 120), font=font); y += 11; line = ""
        line += w + " "
    dr.text((ox, y), line, fill=(200, 200, 120), font=font)
im.save(OUT / "sal_walk_dregs_annotated_x12.png")
print("ok")
