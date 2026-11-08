"""python3 -I to_png.py before|after OUT.png : the teahouse picture (DMG data set) as a 4-shade indexed PNG, for the lint (transcription only)."""
import sys
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[3] / "tools" / "smap_world"))
sys.path.insert(0, str(HERE))
if sys.argv[1] == "after":
    import v_tea_pass as V
else:
    import v_tea as V
rows = V.build(dmg=True).out()
im = Image.new("P", (96, 56))
im.putpalette([248, 248, 248, 168, 168, 168, 88, 88, 88, 24, 24, 24] + [0] * 756)
im.putdata([int(ch) for r in rows for ch in r])
im.save(sys.argv[2])
