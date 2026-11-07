"""Crops the close-up regions of the A4 and A5 renders (cells, inclusive) into out/a5/c/.  python3 -I crops_all.py"""
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[4]
OUT = ROOT / "out" / "a5" / "c"
OUT.mkdir(parents=True, exist_ok=True)
REG = {"fac": (44, 33, 63, 49), "town": (27, 16, 50, 31), "src": (36, 2, 63, 20), "lake": (30, 46, 52, 69)}
SRC = {"a4_cgb": "a4/lay_A4_cgb.png", "a5_cgb": "a5/lay_A5_cgb.png", "a4_dmg": "a4/lay_A4_dmg.png", "a5_dmg": "a5/lay_A5_dmg.png",
       "a5_light": "a5/light/lay_A5_dmg.png"}
for k, f in SRC.items():
    im = Image.open(ROOT / "out" / f)
    for r, (x0, y0, x1, y1) in REG.items():
        im.crop((x0 * 8, y0 * 8, (x1 + 1) * 8, (y1 + 1) * 8)).save(OUT / f"{r}_{k}.png")
print("ok")
