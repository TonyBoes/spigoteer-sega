#!/usr/bin/env python3
"""facedraft.py FILE.txt OUT.png [names,...]: draft viewer (preview only). For each block of a hand-typed block file: the
head (rows 0-11, cols 0-31) at x8, Color over DMG, then every block side by side at true 1x and at x2 (DMG and Color).
It only draws the typed grids; it decides no pixel."""
import sys
from pathlib import Path
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
from quick import blocks, CGB, DMG  # noqa: E402


def draw(rows, pal, s, h=None, w=32):
    rows = [r.ljust(w, ".") for r in rows][: h or len(rows)]
    im = Image.new("RGB", (w * s, len(rows) * s), pal["."])
    d = ImageDraw.Draw(im)
    for y, r in enumerate(rows):
        for x, c in enumerate(r[:w]):
            if c != ".":
                d.rectangle([x * s, y * s, (x + 1) * s - 1, (y + 1) * s - 1], fill=pal[c])
    return im


if __name__ == "__main__":
    f, out = sys.argv[1], sys.argv[2]
    b = blocks(f)
    names = sys.argv[3].split(",") if len(sys.argv) > 3 else [n for n in b if len(b[n]) == 16]
    S, H = 8, 12
    cw = 32 * S + 6
    top = Image.new("RGB", (len(names) * cw, 2 * H * S + 20), (70, 70, 70))
    for k, n in enumerate(names):
        top.paste(draw(b[n], CGB, S, H), (k * cw, 16))
        top.paste(draw(b[n], DMG, S, H), (k * cw, 16 + H * S + 2))
        ImageDraw.Draw(top).text((k * cw + 2, 2), n, fill=(255, 255, 0))
    # 1x strips: true 1x and x2, DMG row then Color row
    strips = []
    for s in (1, 2):
        for pal in (DMG, CGB):
            st = Image.new("RGB", (len(names) * (32 * s + 8), 16 * s), pal["."])
            for k, n in enumerate(names):
                st.paste(draw(b[n], pal, s), (k * (32 * s + 8), 0))
            strips.append(st)
    W = max(top.width, max(s.width for s in strips))
    Ht = top.height + sum(s.height + 6 for s in strips) + 6
    im = Image.new("RGB", (W, Ht), (70, 70, 70))
    im.paste(top, (0, 0))
    y = top.height + 6
    for st in strips:
        im.paste(st, (0, y))
        y += st.height + 6
    im.save(out)
    print("wrote", out, im.size)
