"""Before / after crops of the falls into out/a5/c/ (before = out/a5/fb/before_*.png, after = the log_v1 renders).  python3 -I crops_falls.py"""
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[4]
OUT = ROOT / "out" / "a5" / "c"
SRC = {"cgb": ("fb/before_cgb.png", "log_v1/lay_A5_cgb.png"), "dmg": ("fb/before_dmg.png", "log_v1/lay_A5_dmg.png"),
       "light": ("fb/before_light.png", "log_v1l/lay_A5_dmg.png")}
FOOT = (44, 6, 49, 10)      # cells, inclusive: the falls' foot, the pool
ALL = (43, 4, 51, 13)       # the whole falls, the pool and the stream
for k, (b, a) in SRC.items():
    for tag, f in (("before", b), ("after", a)):
        im = Image.open(ROOT / "out" / "a5" / f)
        for r, (x0, y0, x1, y1) in (("foot", FOOT), ("all", ALL)):
            im.crop((x0 * 8, y0 * 8, (x1 + 1) * 8, (y1 + 1) * 8)).save(OUT / f"falls_{r}_{tag}_{k}.png")
print("ok")
