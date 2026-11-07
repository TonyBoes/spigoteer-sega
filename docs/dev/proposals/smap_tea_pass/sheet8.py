"""python3 -I sheet7.py OUTDIR : OUTDIR/{BWN,C1,C2,C3,C4}_{color,dmg}_x6.png and _ctx_x3.png (render.py) -> sheet_c1s_x6.png (current noren + 4 concepts, 3 columns wrapping,
Color above DMG, x6, the house and tree only) and sheet_c1s_ctx.png (each at x3 in the map, light DMG water)."""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

out = Path(sys.argv[1])
F = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 40)
BG = (30, 30, 30)
ITEMS = [("C1", "C1 SLIT"), ("C1S", "C1S NO SLIT")]


def lab(im, t):
    o = Image.new("RGB", (im.width, im.height + 62), BG)
    ImageDraw.Draw(o).text((10, 8), t, font=F, fill=(255, 255, 255))
    o.paste(im, (0, 62))
    return o


def cell(tag, name, suffix, box):
    ims = [Image.open(out / f"{tag}_{m}{suffix}.png").convert("RGB").crop(box) for m in ("color", "dmg")]
    c = lab(ims[0], name + " Color")
    d = lab(ims[1], name + " DMG")
    o = Image.new("RGB", (c.width, c.height + d.height + 10), BG)
    o.paste(c, (0, 0))
    o.paste(d, (0, c.height + 10))
    return o


def grid(cells, title, name):
    w, h = cells[0].width, cells[0].height
    cols = 2
    rows = (len(cells) + cols - 1) // cols
    o = Image.new("RGB", (cols * w + (cols - 1) * 20, 90 + rows * h + (rows - 1) * 20), BG)
    ImageDraw.Draw(o).text((10, 12), title, font=F, fill=(255, 220, 120))
    for i, c in enumerate(cells):
        o.paste(c, ((i % cols) * (w + 20), 90 + (i // cols) * (h + 20)))
    o.save(out / name)
    print(name, o.size)


grid([cell(t, n, "_x6", (0, 0, 576, 336)) for t, n in ITEMS], "C1 vs C1S, x6", "sheet_c1s_x6.png")
# ctx images are the map box (14,47)-(50,64) at x3: crop cells 18..40, rows 49..62
grid([cell(t, n, "_ctx_x3", (96, 48, 96 + 528, 48 + 312)) for t, n in ITEMS], "C1S in the map, x3", "sheet_c1s_ctx.png")
