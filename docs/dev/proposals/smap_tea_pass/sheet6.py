"""python3 -I sheet3.py OUTDIR : OUTDIR/{v1,A,B}_{color,dmg}_x6.png (render.py) -> sheet_opts_x6.png (fixes | A | B, Color over DMG) and sheet_B_ctx.png (B in the map x3, Color over DMG)."""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

out = Path(sys.argv[1])
F = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 40)
BG = (30, 30, 30)


def lab(im, t):
    o = Image.new("RGB", (im.width, im.height + 62), BG)
    ImageDraw.Draw(o).text((14, 8), t, font=F, fill=(255, 255, 255))
    o.paste(im, (0, 62))
    return o


def col(tag, name, suffix):
    c = lab(Image.open(out / f"{tag}_color{suffix}.png").convert("RGB"), f"{name} Color")
    d = lab(Image.open(out / f"{tag}_dmg{suffix}.png").convert("RGB"), f"{name} DMG")
    o = Image.new("RGB", (c.width, c.height + d.height + 16), BG)
    o.paste(c, (0, 0))
    o.paste(d, (0, c.height + 16))
    return o


def join(cols, title, name):
    W = sum(c.width for c in cols) + 24 * (len(cols) - 1)
    o = Image.new("RGB", (W, cols[0].height + 90), BG)
    ImageDraw.Draw(o).text((14, 12), title, font=F, fill=(255, 220, 120))
    x = 0
    for c in cols:
        o.paste(c, (x, 90))
        x += c.width + 24
    o.save(out / name)
    print(name, o.size)


join([col("BWD", "WALLS + DOOR (2d212801)", "_x6"), col("BWN", "NOREN", "_x6")], "TEAHOUSE noren, x6", "sheet_noren_x6.png")
join([col("BWD", "WALLS + DOOR", "_ctx_x3"), col("BWN", "NOREN", "_ctx_x3")], "TEAHOUSE noren in the map, x3 (light DMG water)", "sheet_noren_ctx.png")
