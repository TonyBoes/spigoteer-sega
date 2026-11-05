"""The 11 vignettes, before (round-1 map) | after (round-2 world, Color) | after (DMG), as 1x images for contact_sheet.py --scale 4."""
from pathlib import Path

from PIL import Image

import render2 as R
import world2 as W

ROUND1 = Path(__file__).resolve().parents[2] / "map_late_cgb_x2.png"
# crop boxes of the round-1 picture, in its own x2 pixels (left, top, right, bottom)
BEFORE = {
    "saloon": (32, 260, 120, 332), "stadium": (44, 44, 164, 134), "lodge": (184, 40, 280, 104), "bistro": (344, 44, 408, 104),
    "igloo": (408, 50, 472, 98), "factory": (396, 122, 470, 186), "cow": (396, 250, 500, 354), "tea": (296, 376, 364, 436),
    "zoo": (150, 380, 214, 436), "space": (8, 352, 200, 512), "town": (140, 170, 372, 346),
}
OUT = Path(__file__).resolve().parents[1] / "vignettes"


def main():
    OUT.mkdir(exist_ok=True)
    src = Image.open(ROUND1)
    paths = []
    for name, box in BEFORE.items():
        before = src.crop(box).resize(((box[2] - box[0]) // 2, (box[3] - box[1]) // 2), Image.NEAREST)
        x0, y0, x1, y1 = W.WORLD.venue_rect[name]
        ab = (x0 * 8, y0 * 8, x1 * 8 + 8, y1 * 8 + 8)
        a_c = R.img("late", "cgb").crop(ab)
        a_d = R.img("late", "dmg").crop(ab)
        h = max(before.height, a_c.height)
        o = Image.new("RGB", (before.width + a_c.width + a_d.width + 12, h), (40, 40, 40))
        o.paste(before, (0, 0))
        o.paste(a_c, (before.width + 6, 0))
        o.paste(a_d, (before.width + a_c.width + 12, 0))
        p = OUT / f"{name}.png"
        o.save(p)
        paths.append(p)
        print(name, before.size, a_c.size)


if __name__ == "__main__":
    main()
