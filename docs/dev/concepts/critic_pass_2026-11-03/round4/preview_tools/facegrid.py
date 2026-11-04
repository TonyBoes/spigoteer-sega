#!/usr/bin/env python3
"""facegrid.py FILE.txt OUT.png [names,...]: draft viewer (preview only). One row per block: the head (rows 0-10, cols 0-24)
at x6 in DMG and Color, then the whole figure at x2 and at true 1x, DMG and Color. Draws the typed grids; decides no pixel."""
import sys
from pathlib import Path
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
from quick import blocks, CGB, DMG  # noqa: E402
from facedraft import draw  # noqa: E402

if __name__ == "__main__":
    f, out = sys.argv[1], sys.argv[2]
    b = blocks(f)
    names = sys.argv[3].split(",") if len(sys.argv) > 3 else [n for n in b if len(b[n]) == 16]
    S = 6
    rowh = 11 * S + 8
    W = 2 * (25 * S + 4) + 2 * (32 * 2 + 4) + 2 * (32 + 4) + 60
    im = Image.new("RGB", (W, len(names) * rowh), (70, 70, 70))
    d = ImageDraw.Draw(im)
    for k, n in enumerate(names):
        y = k * rowh
        d.text((2, y + 2), n, fill=(255, 255, 0))
        x = 60
        for pal in (DMG, CGB):
            im.paste(draw(b[n], pal, S, 11, 25), (x, y)); x += 25 * S + 4
        for pal in (DMG, CGB):
            im.paste(draw(b[n], pal, 2), (x, y)); x += 32 * 2 + 4
        for pal in (DMG, CGB):
            im.paste(draw(b[n], pal, 1), (x, y)); x += 32 + 4
    im.save(out)
    print("wrote", out, im.size)
