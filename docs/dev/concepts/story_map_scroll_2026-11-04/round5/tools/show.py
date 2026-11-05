"""Preview one vignette: python3 show.py saloon [scale] -> scratch png (Color | DMG)."""
import importlib
import sys

from PIL import Image

import pal

S = "/tmp/claude-1000/-workspace/64761c6b-46f6-4217-a6f1-457b4de3152f/scratchpad/w/"


def render(c, mode):
    rows, cp = c.out(), c.cellpals()
    w, h = len(rows[0]), len(rows)
    im = Image.new("RGB", (w, h))
    for y, r in enumerate(rows):
        for x, ch in enumerate(r):
            v = int(ch)
            im.putpixel((x, y), pal.RGB[cp[y // 8][x // 8]][v] if mode == "cgb" else (pal.DMG_SHADE[v],) * 3)
    return im


def sheet(c, k=6, out=None):
    a, b = render(c, "cgb"), render(c, "dmg")
    o = Image.new("RGB", (a.width * k * 2 + 8, a.height * k), (40, 40, 40))
    o.paste(a.resize((a.width * k, a.height * k), 0), (0, 0))
    o.paste(b.resize((a.width * k, a.height * k), 0), (a.width * k + 8, 0))
    if out:
        o.save(out)
    return o


if __name__ == "__main__":
    name = sys.argv[1]
    k = int(sys.argv[2]) if len(sys.argv) > 2 else 6
    m = importlib.import_module("v_" + name)
    c = m.build()
    sheet(c, k, S + f"show_{name}.png")
    print(name, c.w, "x", c.h)
