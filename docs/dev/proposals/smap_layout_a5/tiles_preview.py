"""Preview only: the typed new tiles of A4 as one picture (DMG row over Color row), tiles x8.  python3 -I tiles_preview.py OUT.png"""
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
os.environ["SMAP_LAYOUT"] = "lay_A4"
os.environ["SMAP_FOG"] = "none"
sys.path.insert(0, str(HERE / "src"))
sys.path.append(str(ROOT / "tools" / "smap_world"))
import a4art as A  # noqa: E402
import pal as P  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

GROUPS = [("water", ["WF", "WA", "WB"], "water"), ("banks", ["BN", "BE", "BS", "BW"], "water"), ("outer corners", ["CNW", "CNE", "CSE", "CSW"], "water"),
          ("inner corners", ["INW", "INE", "ISE", "ISW"], "water")]
BR = [("T", A.BR_T), ("B", A.BR_B), ("L", A.BR_L), ("R", A.BR_R)]
S = 8
items = []
for g, names, pal in GROUPS:
    items.append((g, [(n, A.WATER_TILES[n], pal) for n in names]))
items.append(("bridges", [(n, t, "town1") for n, t in BR]))


def draw(rows, pal, dmg):
    im = Image.new("RGB", (8 * S, 8 * S))
    px = im.load()
    cols = P.get(pal)
    for y, r in enumerate(rows):
        for x, c in enumerate(r):
            v = int(c)
            col = (P.DMG_SHADE[v],) * 3 if dmg else tuple(cols[v])
            for j in range(S):
                for i in range(S):
                    px[x * S + i, y * S + j] = col
    return im


# floating logs and the pile on their background (flat water, grass)
def piece_img(rows, pal, bg, dmg):
    h, w = len(rows), len(rows[0])
    im = Image.new("RGB", (w * S, h * S))
    px = im.load()
    cols = P.get(pal)
    bgc = P.get(pal)[bg]
    for y, r in enumerate(rows):
        for x, c in enumerate(r):
            v = bg if c == "." else int(c)
            col = (P.DMG_SHADE[v],) * 3 if dmg else tuple(cols[v])
            for j in range(S):
                for i in range(S):
                    px[x * S + i, y * S + j] = col
    return im


font = ImageFont.load_default(size=13)
W = 1700
sheet = Image.new("RGB", (W, 2 * 310 + 40), (40, 40, 40))
d = ImageDraw.Draw(sheet)
for row, dmg in enumerate((True, False)):
    y0 = 30 + row * 310
    d.text((6, y0 - 22), "DMG" if dmg else "Color", fill=(235, 235, 235), font=font)
    x = 6
    for g, ts in items:
        d.text((x, y0), g, fill=(255, 220, 120), font=font)
        xx = x
        for n, t, pal in ts:
            sheet.paste(draw(t, pal, dmg), (xx, y0 + 18))
            d.text((xx, y0 + 18 + 8 * S + 2), n, fill=(235, 235, 235), font=font)
            xx += 8 * S + 6
        x = xx + 14
    # pieces
    lg = piece_img(A.LOGH, "water", 2, dmg)
    lv = piece_img(A.LOGV, "water", 2, dmg)
    pile = piece_img(A.LOGPILE[1], "lodge", 0, dmg)
    sheet.paste(lg, (6, y0 + 130))
    d.text((6, y0 + 130 + 6 * S + 2), "log across (16x6)", fill=(235, 235, 235), font=font)
    sheet.paste(lv, (220, y0 + 130))
    d.text((220, y0 + 130 + 16 * S + 2), "log down (6x16)", fill=(235, 235, 235), font=font)
    sheet.paste(pile, (380, y0 + 130))
    d.text((380, y0 + 130 + 16 * S + 2), "log pile (22x16), the lodge's own log ends", fill=(235, 235, 235), font=font)
sheet.save(sys.argv[1])

# the typed tiles as one indexed strip (DMG shades, index 0 lightest) so that the owner's lint script can read them
names = [n for g, ts in items for (n, t, p) in ts]
tiles = [t for g, ts in items for (n, t, p) in ts]
strip = Image.new("P", (8 * len(tiles), 8))
strip.putpalette([c for s in P.DMG_SHADE for c in (s, s, s)] + [0] * (768 - 12))
for k, t in enumerate(tiles):
    for y, r in enumerate(t):
        for x, c in enumerate(r):
            strip.putpixel((k * 8 + x, y), int(c))
strip.save(str(Path(sys.argv[1]).with_name("water_tiles_strip.png")))
