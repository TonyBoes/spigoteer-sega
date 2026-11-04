"""Preview only: crop a picture region, Color and DMG side by side, nearest neighbour.   crop.py SRC.txt x0 y0 x1 y1 OUT.png [scale]"""
import sys
from pathlib import Path
from PIL import Image
sys.path.insert(0, str(Path(__file__).resolve().parent))
from render_v2 import parse, render

src, x0, y0, x1, y1, out = sys.argv[1], *map(int, sys.argv[2:6]), sys.argv[6]
sc = int(sys.argv[7]) if len(sys.argv) > 7 else 8
key, pix = parse(src)
a = render(key, pix, 1).crop((x0, y0, x1 + 1, y1 + 1))
b = render(key, pix, 1, dmg=True).crop((x0, y0, x1 + 1, y1 + 1))
w, h = a.size
im = Image.new("RGB", (w * 2 + 2, h), (255, 0, 255))
im.paste(a, (0, 0))
im.paste(b, (w + 2, 0))
im.resize((im.width * sc, im.height * sc), Image.NEAREST).save(out)
