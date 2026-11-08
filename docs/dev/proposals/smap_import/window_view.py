"""python3 window_view.py KEY OUT.png : a larger windowed view of a big-mountain placement (owner Q117): the top band of the map, 40 cells wide and 20 tall, centred on the mountain (clamped to
the map), Color above DMG, at x4 (1280 px wide).  KEY = A or B (set SMAP_BIG to the same key)."""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import mapctx as M  # noqa: E402
import big_mountain as BM  # noqa: E402

key, out = sys.argv[1], sys.argv[2]
x0, y0, _ = BM.PLACES[key]
cx = (max(x0, 0) + min(x0 + BM.W, 512)) // 2 // 8              # the mountain's visible centre, in cells
bx = max(0, min(cx - 20, M.CW - 40))
box = (bx, 0, bx + 40, 20)
S = 4
try:
    font = ImageFont.truetype("/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf", 30)
except OSError:
    font = ImageFont.load_default()
a, b = M.render(True, box, S).convert("RGB"), M.render(False, box, S).convert("RGB")
img = Image.new("RGB", (a.width + 32, a.height * 2 + 120), (30, 30, 34))
d = ImageDraw.Draw(img)
d.text((16, 10), "mountain %s   COLOR   cells %d..%d, rows 0..19, x4" % (key, box[0], box[2] - 1), fill=(255, 255, 255), font=font)
img.paste(a, (16, 56))
d.text((16, 66 + a.height), "mountain %s   DMG" % key, fill=(255, 255, 255), font=font)
img.paste(b, (16, 112 + a.height))
img.save(out)
print(key, box, img.size)
