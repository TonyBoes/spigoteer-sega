"""Repeating ground patches for the tiled preview: python3 tilepatch.py OUTDIR -> one 32 x 32 PNG per terrain, laid with the world's own variant
pattern (so what the preview repeats is what the map shows)."""
import sys
from pathlib import Path

from PIL import Image

import pal
import tiles
import world2 as W

OUT = Path(sys.argv[1])
OUT.mkdir(exist_ok=True)
JOBS = {"grass": "grass", "desert": "saloon", "snow": "igloo", "farm": "farm", "jungle": "zoo", "moss": "tea", "paved": "stadium", "plaza": "bistro",
        "yard": "factory", "forest": "grass"}
for name, pn in JOBS.items():
    vs = W.GROUND[name]
    cols = pal.RGB[pn]
    im = Image.new("RGB", (32, 32))
    for cy in range(4):
        for cx in range(4):
            h = (cx * 7 + cy * 13 + cx * cy) % 13
            v = vs[0] if h not in (3, 8, 11) or len(vs) == 1 else vs[1 + (h // 3) % (len(vs) - 1)]
            if name == "forest":
                v = vs[h % 3] if h % 4 else vs[3]
            for j in range(8):
                for i in range(8):
                    im.putpixel((cx * 8 + i, cy * 8 + j), cols[int(v[j][i])])
    im.save(OUT / f"ground_{name}.png")
# the road (checker of F1, F2 inside the kerbs) in the town palette, the fog interior in its cloud colours
road = Image.new("RGB", (32, 32))
for cy in range(4):
    for cx in range(4):
        t = tiles.ROAD["F1"] if (cx + cy) % 2 == 0 else tiles.ROAD["F2"]
        for j in range(8):
            for i in range(8):
                road.putpixel((cx * 8 + i, cy * 8 + j), pal.RGB["town1"][int(t[j][i])])
road.save(OUT / "road.png")
fog = Image.new("RGB", (32, 32))
for cy in range(4):
    for cx in range(4):
        t = tiles.FOG[("FA", "FB", "FC", "FD")[(cx % 2) + 2 * (cy % 2)]]
        for j in range(8):
            for i in range(8):
                fog.putpixel((cx * 8 + i, cy * 8 + j), pal.get("fog:fogbase")[int(t[j][i])])
fog.save(OUT / "fog.png")
