#!/usr/bin/env python3
"""Adds a big header (phone-readable) above a contact sheet.   bigheader.py IN.png OUT.png "line 1" "line 2" ..."""
import sys

from PIL import Image, ImageDraw, ImageFont

im = Image.open(sys.argv[1]).convert("RGB")
lines = sys.argv[3:]
f = ImageFont.load_default(size=40)
h = 56 * len(lines) + 20
out = Image.new("RGB", (im.width, im.height + h), (30, 30, 30))
d = ImageDraw.Draw(out)
for i, t in enumerate(lines):
    d.text((14, 10 + 56 * i), t, font=f, fill=(255, 255, 255) if i == 0 else (255, 220, 120))
out.paste(im, (0, h))
out.save(sys.argv[2])
