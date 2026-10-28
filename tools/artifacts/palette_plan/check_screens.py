#!/usr/bin/env python3
"""Check the Graphics Atlas "Screen" composite against the real game screenshot of the same capture.

    python3 tools/artifacts/palette_plan/check_screens.py [ATLAS_DATA_DIR]

For every venue on Color and DMG: screen_composite() (build.py: the attribute map, VRAM bank, palette and flips drawn from the captured tiles)
against the still of the representative frame in out/atlas/img/level_<venue>.png, pixel by pixel, leaving out the pixels under a sprite
(the composite is the background layer only). Prints the differing pixel count per venue and model; exit 1 if any is not 0.
"""
import os
import runpy
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
data = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(HERE))), "out/atlas/data")
tmp = tempfile.mkdtemp(prefix="atlascheck")
sys.argv = [os.path.join(HERE, "build.py"), data, os.path.join(tmp, "index.html")]
G = runpy.run_path(os.path.join(HERE, "build.py"))
from PIL import Image  # noqa: E402

bad = 0
for v in G["venues"]:
    lv = G["load"]("level_" + v["key"])
    row = []
    for model in ("cgb", "dmg"):
        rec = lv[model]
        pk = rec["pack"]
        src = Image.open(os.path.join(os.path.dirname(G["DATA"]), pk["png"])).convert("RGB")
        sx, sy = pk["still"]
        real = src.crop((sx, sy, sx + 160, sy + 144))
        mine = G["screen_composite"](v, model)
        if model == "dmg":                                      # the atlas sheets show PyBoy's DMG light grey (153) as 170
            real = real.point(lambda p: 170 if p == 153 else p)
        mask = set()
        h = rec["obj_h"]
        for o in rec["oam"]["table"]:
            for y in range(o["y"] - 3, o["y"] + h + 3):          # the table holds screen coordinates; moving sprites (dust, mugs) are a few px off the still
                for x in range(o["x"] - 3, o["x"] + 11):
                    mask.add((x, y))
        for r in range(18):                                     # animated tiles (the stage's lights): VRAM holds one phase, the still another
            for c in range(20):
                sl = rec["attr"]["slot"][r][c]
                bank = (int(rec["attr"]["flags"][r][c], 16) >> 2) & 1 if model == "cgb" else 0
                if sl in rec["tiles"][bank]["changed"]:
                    mask.update((c * 8 + i, r * 8 + j) for i in range(8) for j in range(8))
        n = 0
        box = None
        for y in range(144):
            for x in range(160):
                if (x, y) in mask:
                    continue
                if real.getpixel((x, y)) != mine.getpixel((x, y)):
                    n += 1
                    box = [x, y, x, y] if box is None else [min(box[0], x), min(box[1], y), max(box[2], x), max(box[3], y)]
        bad += n
        row.append("%s %d%s" % (model, n, (" in %s" % box) if n else ""))
        if n:
            mine.save(os.path.join(tmp, "%s_%s_mine.png" % (v["key"], model)))
            real.save(os.path.join(tmp, "%s_%s_real.png" % (v["key"], model)))
    print("%-12s %s" % (v["key"], "   ".join(row)))
print("total differing pixels: %d%s" % (bad, "" if not bad else "  (pictures in %s)" % tmp))
sys.exit(1 if bad else 0)
