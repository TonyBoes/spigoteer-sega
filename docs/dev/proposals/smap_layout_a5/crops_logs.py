"""Crops the river section (with the log landing) of the log renders into out/a5/c/.  python3 -I crops_logs.py"""
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[4]
OUT = ROOT / "out" / "a5" / "c"
OUT.mkdir(parents=True, exist_ok=True)
REGS = {"river": (40, 16, 59, 37), "lake": (36, 52, 49, 69)}
for v in ("old", "v1", "v2", "v1l", "v2l"):
    for model in ("cgb", "dmg"):
        if v.endswith("l") and model == "cgb":
            continue
        im = Image.open(ROOT / "out" / "a5" / f"log_{v}" / f"lay_A5_{model}.png")
        for r, (x0, y0, x1, y1) in REGS.items():
            im.crop((x0 * 8, y0 * 8, (x1 + 1) * 8, (y1 + 1) * 8)).save(OUT / f"log_{r}_{v}_{model}.png")
print("ok")
