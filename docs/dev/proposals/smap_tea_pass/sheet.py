"""python3 -I sheet.py OUTDIR : out/tea/*.png (from render.py) -> sheet_x6.png (before | after, Color over DMG, x6) and sheet_ctx.png (before | after in map context, x3).
Big bold labels, two columns."""
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


def sheet(suffix, title_c, title_d, name):
    cols = []
    for tag, t in (("before", "BEFORE"), ("after", "AFTER")):
        c = lab(Image.open(out / f"{tag}_color{suffix}.png").convert("RGB"), f"{t}  Color")
        d = lab(Image.open(out / f"{tag}_dmg{suffix}.png").convert("RGB"), f"{t}  DMG")
        col = Image.new("RGB", (c.width, c.height + d.height + 16), BG)
        col.paste(c, (0, 0))
        col.paste(d, (0, c.height + 16))
        cols.append(col)
    o = Image.new("RGB", (cols[0].width * 2 + 24, cols[0].height + 90), BG)
    ImageDraw.Draw(o).text((14, 12), title_c, font=F, fill=(255, 220, 120))
    o.paste(cols[0], (0, 90))
    o.paste(cols[1], (cols[0].width + 24, 90))
    o.save(out / name)
    print(name, o.size)


sheet("_x6", "TEAHOUSE quality pass, x6", "", "sheet_x6.png")
sheet("_ctx_x3", "TEAHOUSE in the map, x3", "", "sheet_ctx.png")
