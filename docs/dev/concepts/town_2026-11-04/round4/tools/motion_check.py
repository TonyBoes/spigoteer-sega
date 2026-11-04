#!/usr/bin/env python3
"""Preview: the GIFs' frames side by side for the frame-by-frame check (water phases 0-3 zoomed; sky every 8 steps)."""
import sys
from PIL import Image, ImageSequence

src, out = sys.argv[1], sys.argv[2]
crop_box = tuple(int(v) for v in sys.argv[3].split(","))   # in GIF pixels (x3)
pick = [int(v) for v in sys.argv[4].split(",")]
zoom = int(sys.argv[5]) if len(sys.argv) > 5 else 2
fr = [f.convert("RGB") for f in ImageSequence.Iterator(Image.open(src))]
w, h = crop_box[2] - crop_box[0], crop_box[3] - crop_box[1]
sheet = Image.new("RGB", ((w * zoom + 6) * len(pick), h * zoom), (255, 0, 255))
for i, k in enumerate(pick):
    c = fr[k].crop(crop_box).resize((w * zoom, h * zoom), Image.NEAREST)
    sheet.paste(c, (i * (w * zoom + 6), 0))
sheet.save(out)
