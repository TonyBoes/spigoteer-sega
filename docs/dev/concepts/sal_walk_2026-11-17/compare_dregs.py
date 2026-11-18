#!/usr/bin/env python3
"""P7 against Dregs, side by side at x12 (arm rows 10-18, idle | walk1 | walk2), the pixels that differ from idle boxed, and a
measurement table printed per side: for each arm row the outer edge (x) of the silhouette in idle vs the frame, and the rows /
columns of the hand (skin: Dregs '-', Sal '+'). Preview and measurement only.  Run from the repo root."""
import importlib.util
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("b", HERE / "build.py")
b = importlib.util.module_from_spec(spec)
import contextlib, io
with contextlib.redirect_stdout(io.StringIO()):
    spec.loader.exec_module(b)
font = ImageFont.load_default()
S, R0, R1 = 12, 10, 19
SUBJ = [("Sal now", b.sal, b.SAL_C, "+"), ("Sal P7", b.PROPS["P7"], b.SAL_C, "+"), ("Dregs", b.dregs, b.DREGS_C, "-")]


def edge(f, y, side):
    xs = [x for x, c in enumerate(f[y]) if c != "."]
    return min(xs) if side == "L" else max(xs)


def hand(f, skin, side):
    """skin pixels of the arm: left side x<6, right side x>=10 (rows 14-18)."""
    return [(x, y) for y in range(14, 19) for x in range(16) if f[y][x] == skin and ((x < 6) if side == "L" else (x >= 10))]


print("outer edge per row 14-18 (idle -> frame) and hand skin pixels (x,y):")
for name, fr, pal, skin in SUBJ[1:]:
    for k, nm in ((1, "walk1"), (2, "walk2")):
        for side in ("L", "R"):
            e = [f"{edge(fr[0], y, side)}->{edge(fr[k], y, side)}" for y in range(14, 19)]
            hs = hand(fr[k], skin, side)
            print(f"  {name:8s} {nm} {side}: edge rows14-18 {' '.join(e)}   hand {hs}")
print("  (Dregs's picture-left hand in walk1 and picture-right hand in walk2 are the forward ones; Sal's P7 must match them.)")

W = 16 * S
im = Image.new("RGB", (6 * (W + 8) + 8, (R1 - R0) * S + 40), (40, 40, 40))
dr = ImageDraw.Draw(im)
col = 0
for name, fr, pal, skin in (SUBJ[1], SUBJ[2]):
    for k, nm in ((0, "idle"), (1, "walk1"), (2, "walk2")):
        ox = 8 + col * (W + 8)
        dr.text((ox, 4), f"{name} {nm}", fill=(235, 235, 235), font=font)
        for y in range(R0, R1):
            for x in range(16):
                box = [ox + x * S, 20 + (y - R0) * S, ox + x * S + S - 1, 20 + (y - R0) * S + S - 1]
                dr.rectangle(box, fill=pal[fr[k][y][x]] if fr[k][y][x] in pal else (48, 56, 72))
                if k and fr[k][y][x] != fr[0][y][x]:
                    dr.rectangle(box, outline=(255, 0, 255))
        col += 1
im.save(HERE / "sal_P7_vs_dregs_x12.png")
