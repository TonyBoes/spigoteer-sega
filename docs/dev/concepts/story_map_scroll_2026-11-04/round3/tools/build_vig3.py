"""The changed vignettes: round 2 (Color) | round 3 (Color) | round 3 (DMG), 1x strips for contact_sheet.py --scale 4."""
from pathlib import Path

from PIL import Image

import render2 as R
import world2 as W

ROUND2 = Path(__file__).resolve().parents[2] / "round2" / "map_late_cgb_x2.png"
OUT = Path(__file__).resolve().parents[1] / "vignettes"
CHANGED = ("saloon", "cow", "town")


def main():
    OUT.mkdir(exist_ok=True)
    src = Image.open(ROUND2)
    for name in CHANGED:
        x0, y0, x1, y1 = W.WORLD.venue_rect[name]
        box = (x0 * 8, y0 * 8, x1 * 8 + 8, y1 * 8 + 8)
        before = src.crop(tuple(v * 2 for v in box)).resize((box[2] - box[0], box[3] - box[1]), Image.NEAREST)
        a_c, a_d = R.img("late", "cgb").crop(box), R.img("late", "dmg").crop(box)
        o = Image.new("RGB", (before.width * 3 + 12, before.height), (40, 40, 40))
        o.paste(before, (0, 0))
        o.paste(a_c, (before.width + 6, 0))
        o.paste(a_d, (before.width * 2 + 12, 0))
        o.save(OUT / f"r3_{name}.png")


if __name__ == "__main__":
    main()
