"""Draws the PLACEHOLDER labels on the A4 map pictures (the boxes are not art) and the venue names on the route copies are drawn by eval_layout.py.
python3 -I mark.py IN.png OUT.png   (IN is the x1 map picture; OUT is x1 too, )"""
import sys

from PIL import Image, ImageDraw, ImageFont

BOXES = [("BASEBALL PARK", "placeholder 16x10", 1, 1, 16, 10), ("SPACE LOUNGE + MOUNTAIN", "placeholder 22x12", 10, 33, 22, 12),
         ("RANGE A", "placeholder", 17, 0, 15, 4), ("RANGE B", "placeholder", 34, 0, 14, 5), ("RANGE C", "placeholder", 48, 0, 16, 5)]
im = Image.open(sys.argv[1]).convert("RGB")
S = 1
big = im.resize((im.width * S, im.height * S), Image.NEAREST)
d = ImageDraw.Draw(big)
f = ImageFont.load_default(size=10)
for name, sub, x, y, w, h in BOXES:
    x0, y0, x1, y1 = x * 8 * S, y * 8 * S, (x + w) * 8 * S, (y + h) * 8 * S
    cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
    tw = max(d.textlength(name, font=f), d.textlength(sub, font=f)) + 8
    d.rectangle((cx - tw / 2, cy - 12, cx + tw / 2, cy + 12), fill=(0, 0, 0))
    d.text((cx, cy - 5), name, fill=(255, 255, 255), font=f, anchor="mm")
    d.text((cx, cy + 6), sub, fill=(255, 220, 120), font=f, anchor="mm")
big.save(sys.argv[2])
