"""python3 anim_static_sheet.py OUT.png : the pasted approved static art (anim_static.py) on the integrated map, x5, Color above DMG: a sunk log across (42,52), an upright one (45,43), a removed
log (48,33), the lodge smoke cells (58..59,19..20) and a pasture cow tail (55,49)."""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import mapctx as M  # noqa: E402

BOXES = [("log across (42,52)", (41, 51, 46, 55)), ("log upright (45,43)", (44, 42, 48, 46)), ("log removed (48,33)", (47, 32, 52, 35)),
         ("lodge smoke (58,19)", (56, 18, 62, 22)), ("cow tail (55,49)", (53, 47, 58, 52)), ("water glints (40,53)", (39, 52, 43, 56))]
S = 5
font = ImageFont.truetype("/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf", 13)
cols = [(M.render(True, b, S).convert("RGB"), M.render(False, b, S).convert("RGB"), n) for n, b in BOXES]
W = sum(c[0].width + 10 for c in cols) + 10
H = max(c[0].height for c in cols)
sheet = Image.new("RGB", (W, 2 * H + 80), (30, 30, 34))
d = ImageDraw.Draw(sheet)
x = 10
for a, b, n in cols:
    d.text((x, 6), n, fill=(255, 255, 255), font=font)
    sheet.paste(a, (x, 36))
    sheet.paste(b, (x, 44 + H))
    x += a.width + 10
sheet.save(sys.argv[1])
print(sheet.size)
