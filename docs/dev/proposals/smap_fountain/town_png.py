"""Transcribes the town picture (96 x 72, the typed index digits) into an indexed DMG PNG, for the lint and the previews.
python3 -I town_png.py OPT OUT.png     OPT = cur (layout A5's town as approved), 1 or 2"""
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
opt = sys.argv[1]
os.environ["SMAP_FOUNTAIN"] = opt
sys.path.insert(0, str(HERE / "src"))
sys.path.append(str(ROOT / "tools" / "smap_world"))
sys.path.append(str(ROOT / "docs" / "dev" / "proposals" / "smap_layout_a5" / "src"))
from PIL import Image  # noqa: E402

if opt == "cur":
    import v_town_a5 as T
else:
    import v_town_fx as T
rows = T.build().rows
im = Image.new("P", (len(rows[0]), len(rows)))
pal = [248, 248, 248, 168, 168, 168, 88, 88, 88, 24, 24, 24]
im.putpalette(pal + [0] * (768 - len(pal)))
for y, r in enumerate(rows):
    for x, ch in enumerate(r):
        im.putpixel((x, y), int(ch))
im.save(sys.argv[2])
print(sys.argv[2], im.size)
