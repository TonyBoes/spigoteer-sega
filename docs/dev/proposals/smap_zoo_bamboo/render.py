#!/usr/bin/env python3
"""Preview renderer (read-only): a cell region of a story-map picture pair, in Color (the cell palettes of assets/smap/world.json) or in DMG shades.

    from render import crop;  crop(dir_with_world_c_and_d_png, (x0, y0, x1, y1), color=True)  -> PIL image (cells)
"""
import json
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[4]
J = json.loads((ROOT / "assets" / "smap" / "world.json").read_text())


def crop(src, box, color=True):
    x0, y0, x1, y1 = box
    a = np.array(Image.open(Path(src) / ("world_c.png" if color else "world_d.png")))
    out = np.zeros(((y1 - y0) * 8, (x1 - x0) * 8, 3), np.uint8)
    for y in range(y0, y1):
        for x in range(x0, x1):
            t = a[y * 8:y * 8 + 8, x * 8:x * 8 + 8]
            if color:
                pal = J["pal_rgb"][J["pal_names"][ord(J["cell_pal"][y][x]) - 48]]
            else:
                pal = [(g, g, g) for g in J["dmg_shade"]]
            out[(y - y0) * 8:(y - y0) * 8 + 8, (x - x0) * 8:(x - x0) * 8 + 8] = np.array(pal, np.uint8)[t]
    return Image.fromarray(out)
