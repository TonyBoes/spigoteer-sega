"""Round 5: the late DMG world as one indexed 4-shade PNG (a convert step for the lint).  python3 worldpng.py OUT.png [dmg|color]"""
import sys

from PIL import Image

import pal
import world2 as W

w = W.WORLD_DMG if (len(sys.argv) < 3 or sys.argv[2] == "dmg") else W.WORLD
im = Image.new("P", (W.PW, W.PH))
flat = []
for v in (pal.DMG_SHADE[0], pal.DMG_SHADE[1], pal.DMG_SHADE[2], pal.DMG_SHADE[3]):
    flat += [v, v, v]
im.putpalette(flat + [0] * (768 - len(flat)))
im.putdata([w.px[y][x] for y in range(W.PH) for x in range(W.PW)])
im.save(sys.argv[1])
