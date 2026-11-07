"""Before | after sheet for the six one-pixel DMG_TRIM edits (tools/dev/smap_snapshot.py): each spot with a 3-cell margin, x3.
Run from the repo root: python3 docs/dev/proposals/smap_import/dmg_trim_sheet.py"""
import re
import subprocess
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[4]
SHADE = [248, 168, 88, 24]
src = (ROOT / "tools/dev/smap_snapshot.py").read_text()
TRIM = eval(re.search(r"^DMG_TRIM = (\[.*\])$", src, re.M).group(1))
after = Image.open(ROOT / "assets/smap/world_d.png").convert("RGB")
before = after.copy()
out = ROOT / "out" / "trim"
out.mkdir(parents=True, exist_ok=True)
items = []
for n, (cx, cy, px, py, old, new) in enumerate(TRIM, 1):
    X, Y = cx * 8 + px, cy * 8 + py
    assert after.getpixel((X, Y))[0] == SHADE[new]
    before.putpixel((X, Y), (SHADE[old],) * 3)
    box = (max(0, (cx - 3) * 8), max(0, (cy - 3) * 8), min(after.width, (cx + 4) * 8), min(after.height, (cy + 4) * 8))
    for tag, im in (("BEFORE", before), ("AFTER", after)):
        p = out / f"trim{n}_{tag.lower()}.png"
        im.crop(box).save(p)
        items.append(f"{n} {tag} CELL {cx} {cy}={p}")
    before.putpixel((X, Y), (SHADE[new],) * 3)
sheet = ROOT / "docs/dev/proposals/smap_import/dmg_trim_before_after_x3.png"
subprocess.run([sys.executable, str(ROOT / "tools/dev/contact_sheet.py"), str(sheet), "--scale", "3", "--cols", "2",
                "--title", "DMG TRIMS: BEFORE LEFT, AFTER RIGHT"] + items, check=True)
