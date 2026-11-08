"""Before | after sheet of the re-typed ground seams (seam_edges.py).  python3 seam_sheet.py crops TAG OUTDIR (TAG before: run with env SMAP_NO_SEAMS=1; after: no env), then python3 seam_sheet.py sheet OUTDIR.
Two columns, Color over DMG, x3, one row per seam."""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
SEAMS = [
    ("s1", "Saloon sand, north edge and north east edge", (0, 19, 21, 29)),
    ("s2", "Airbase sand, east edge (x 28 to 33)", (20, 29, 41, 47)),
    ("s3", "Airbase sand, west strip", (0, 29, 21, 47)),
    ("s4", "Zoo, north edge", (0, 46, 21, 56)),
    ("s5", "Zoo, west strip and east edge", (0, 52, 23, 70)),
]


def crops(tag, out):
    sys.path.insert(0, str(HERE))
    import mapctx as M
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    for key, _, box in SEAMS:
        b = (box[0], box[1], box[2], min(box[3], M.CH))
        for cgb in (True, False):
            M.render(cgb, b, 3).save(out / f"{tag}_{key}_{'color' if cgb else 'dmg'}.png")


def label(im, text, size=34, bg=(30, 30, 30)):
    f = ImageFont.truetype(FONT, size)
    h = size + 22
    o = Image.new("RGB", (im.width, im.height + h), bg)
    ImageDraw.Draw(o).text((12, 8), text, font=f, fill=(255, 255, 255))
    o.paste(im, (0, h))
    return o


def stack(ims, vertical, gap=10):
    if vertical:
        o = Image.new("RGB", (max(i.width for i in ims), sum(i.height for i in ims) + gap * (len(ims) - 1)), (30, 30, 30))
        y = 0
        for i in ims:
            o.paste(i, (0, y))
            y += i.height + gap
    else:
        o = Image.new("RGB", (sum(i.width for i in ims) + gap * (len(ims) - 1), max(i.height for i in ims)), (30, 30, 30))
        x = 0
        for i in ims:
            o.paste(i, (x, 0))
            x += i.width + gap
    return o


def sheet(out):
    out = Path(out)
    L = lambda f: Image.open(out / f).convert("RGB")
    rows = []
    for key, text, _ in SEAMS:
        cols = [label(stack([L(f"{t}_{key}_color.png"), L(f"{t}_{key}_dmg.png")], True, 6), nm + " x3", 30) for t, nm in (("before", "BEFORE"), ("after", "AFTER"))]
        rows.append(label(stack(cols, False, 20), text, 38, bg=(70, 40, 90)))
    # two sheets: the first three seams, then the rest
    stack(rows[:3], True, 30).save(out / "sheet_seams_1.png")
    stack(rows[3:], True, 30).save(out / "sheet_seams_2.png")


if __name__ == "__main__":
    if sys.argv[1] == "crops":
        crops(sys.argv[2], sys.argv[3])
    else:
        sheet(sys.argv[2])
