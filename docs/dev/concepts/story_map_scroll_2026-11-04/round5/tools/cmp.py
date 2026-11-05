"""Round 5 working view: DMG full | DMG trimmed from the two worlds.
python3 cmp.py OUT.png venue [venue ...]      one sheet at x4
python3 cmp.py --dir DIR venue [venue ...]    one 1x picture per venue in DIR (for contact_sheet.py --scale 4); a name like region:NAME:x0:y0:x1:y1
                                              takes that box of cells instead of a venue"""
import sys
from pathlib import Path

from PIL import Image

import pal
import world2 as W


def crop(w, box):
    x0, y0, x1, y1 = box
    im = Image.new("RGB", ((x1 - x0 + 1) * 8, (y1 - y0 + 1) * 8))
    for y in range((y1 - y0 + 1) * 8):
        for x in range((x1 - x0 + 1) * 8):
            v = pal.DMG_SHADE[w.px[y0 * 8 + y][x0 * 8 + x]]
            im.putpixel((x, y), (v, v, v))
    return im


def pair(box):
    a, b = crop(W.WORLD, box), crop(W.WORLD_DMG, box)
    o = Image.new("RGB", (a.width * 2 + 6, a.height), (40, 40, 40))
    o.paste(a, (0, 0))
    o.paste(b, (a.width + 6, 0))
    return o


def box_of(name):
    if name.startswith("region:"):
        _, label, x0, y0, x1, y1 = name.split(":")
        return label, (int(x0), int(y0), int(x1), int(y1))
    return name, W.WORLD.venue_rect[name]


if __name__ == "__main__":
    if sys.argv[1] == "--dir":
        out = Path(sys.argv[2])
        out.mkdir(parents=True, exist_ok=True)
        for n in sys.argv[3:]:
            label, box = box_of(n)
            pair(box).save(out / f"cmp_{label}.png")
    else:
        parts = []
        for n in sys.argv[2:]:
            label, box = box_of(n)
            o = pair(box)
            parts.append(o.resize((o.width * 4, o.height * 4), Image.NEAREST))
        H = sum(p.height + 8 for p in parts)
        Wd = max(p.width for p in parts)
        sheet = Image.new("RGB", (Wd, H), (20, 20, 20))
        y = 0
        for p in parts:
            sheet.paste(p, (0, y))
            y += p.height + 8
        sheet.save(sys.argv[1])
