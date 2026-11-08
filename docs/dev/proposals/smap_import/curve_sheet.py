"""Step 1 sheets for the smooth bends: python3 curve_sheet.py crops TAG OUTDIR (env SMAP_CURVE=16|24, SMAP_CURVE_LINE=1 as mapctx / roads_smooth) then python3 curve_sheet.py sheet OUTDIR.
The representative bend is the NW one at the stadium gate road (outer corner cell (0, 11), ground cell (2, 13)): x6 close-up and x3 in map context, Color and DMG."""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
CLOSE = (0, 9, 7, 16)
CONTEXT = (0, 8, 16, 24)


def crops(tag, out):
    sys.path.insert(0, str(HERE))
    import mapctx as M
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    for cgb in (True, False):
        n = "color" if cgb else "dmg"
        M.render(cgb, CLOSE, 6).save(out / f"{tag}_close_{n}.png")
        M.render(cgb, CONTEXT, 3).save(out / f"{tag}_ctx_{n}.png")


def label(im, text, size=34, bg=(30, 30, 30)):
    f = ImageFont.truetype(FONT, size)
    h = size + 22
    o = Image.new("RGB", (im.width, im.height + h), bg)
    ImageDraw.Draw(o).text((12, 8), text, font=f, fill=(255, 255, 255))
    o.paste(im, (0, h))
    return o


def stack_h(ims, gap=14):
    o = Image.new("RGB", (sum(i.width for i in ims) + gap * (len(ims) - 1), max(i.height for i in ims)), (30, 30, 30))
    x = 0
    for i in ims:
        o.paste(i, (x, 0))
        x += i.width + gap
    return o


def stack_v(ims, gap=14):
    o = Image.new("RGB", (max(i.width for i in ims), sum(i.height for i in ims) + gap * (len(ims) - 1)), (30, 30, 30))
    y = 0
    for i in ims:
        o.paste(i, (0, y))
        y += i.height + gap
    return o


def sheet(out):
    out = Path(out)
    L = lambda f: Image.open(out / f).convert("RGB")
    names = (("r8", "NOW: radius 8"), ("c16", "RADIUS 16"), ("c24", "RADIUS 24"))
    blank = Image.new("RGB", L("r8_close_color.png").size, (50, 50, 50))
    close = []
    for (t, nm), lt in zip(names, ("r8", "l16", "l24")):
        pre = blank if lt == "r8" else L(f"{lt}_close_color.png")
        close.append(label(stack_v([L(f"{t}_close_color.png"), pre, L(f"{t}_close_dmg.png")], 8), nm + " x6", 32))
    label(stack_h(close, 18), "Bends x6: Color, cream line preview, DMG", 30, bg=(70, 40, 90)).save(out / "sheet_curves_close.png")
    ctx = [label(stack_v([L(f"{t}_ctx_color.png"), L(f"{t}_ctx_dmg.png")], 8), nm + " x3", 32) for t, nm in names]
    label(stack_h(ctx, 18), "In the map: Color over DMG", 40, bg=(70, 40, 90)).save(out / "sheet_curves_context.png")


if __name__ == "__main__":
    if sys.argv[1] == "crops":
        crops(sys.argv[2], sys.argv[3])
    else:
        sheet(sys.argv[2])
