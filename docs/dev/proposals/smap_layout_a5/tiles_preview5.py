"""Preview only: the typed new tiles of A5 (falls, splash, shore variants, gravel) as 1x strips for the lint (DMG dark, DMG light, Color) and one x8 labelled
sheet.  python3 -I tiles_preview5.py OUTDIR"""
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
os.environ["SMAP_LAYOUT"] = "lay_A5"
os.environ["SMAP_FOG"] = "none"
sys.path.insert(0, str(HERE / "src"))
sys.path.append(str(ROOT / "tools" / "smap_world"))
import a5art as A  # noqa: E402
import pal as P  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

out = Path(sys.argv[1])
out.mkdir(parents=True, exist_ok=True)
NEW = ["FL_A", "FL_B", "FR_A", "FR_B", "SPL_A", "SPL_B", "BN2", "BS2", "BW2", "BE2"]
SHADE = [248, 168, 88, 24]
LSHADE = [248, 168, 88, 24]


def tiles(light):
    S = A.LIGHT if light else A.DARK
    return [(n, S[n]) for n in NEW] + [("GRAVEL", A.GRAVEL)]


def render(ts, pal, dmg, scale):
    im = Image.new("RGB", (8 * scale * len(ts), 8 * scale))
    px = im.load()
    cols = P.get(pal)
    for k, (n, rows) in enumerate(ts):
        for y, r in enumerate(rows):
            for x, c in enumerate(r):
                v = int(c)
                col = (SHADE[v],) * 3 if dmg else tuple(cols[v])
                for j in range(scale):
                    for i in range(scale):
                        px[(k * 8 + x) * scale + i, y * scale + j] = col
    return im


render(tiles(False), "water", True, 1).save(out / "strip_dmg_dark.png")
render(tiles(True), "water", True, 1).save(out / "strip_dmg_light.png")
render(tiles(False), "water", False, 1).save(out / "strip_cgb.png")
S = 8
font = ImageFont.load_default(size=13)
sheet = Image.new("RGB", (11 * 8 * S + 20, 3 * (8 * S + 40) + 10), (40, 40, 40))
d = ImageDraw.Draw(sheet)
for r, (label, light, dmg) in enumerate((("DMG dark", False, True), ("DMG light", True, True), ("Color", False, False))):
    y0 = 24 + r * (8 * S + 40)
    d.text((6, y0 - 20), label, fill=(255, 220, 120), font=font)
    ts = tiles(light)
    sheet.paste(render(ts, "water", dmg, S), (6, y0))
    for k, (n, _) in enumerate(ts):
        d.text((6 + k * 8 * S + 2, y0 + 8 * S + 2), n, fill=(235, 235, 235), font=font)
sheet.save(out / "sheet_new_tiles.png")
print("ok")
