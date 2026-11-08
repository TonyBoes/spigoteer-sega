"""python3 sheet_q115.py CCDIR OUTDIR : labelled sheets for Q115 from the crops curve_crops.py and trim_crops.py wrote.
Big labels, three columns at most.  Missing crops are skipped."""
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

CC, OUT = Path(sys.argv[1]), Path(sys.argv[2])
OUT.mkdir(parents=True, exist_ok=True)
try:
    FONT = ImageFont.truetype("/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf", 28)
except OSError:
    FONT = ImageFont.load_default()
BG = (30, 30, 34)


def sheet(name, rows, cols=3):
    """rows: list of (label, file) ; laid out in `cols` columns."""
    cells = []
    for label, f in rows:
        p = CC / f
        if p.exists():
            cells.append((label, Image.open(p).convert("RGB")))
    if not cells:
        return
    cw = max(i.width for _, i in cells)
    ch = max(i.height for _, i in cells) + 44
    nr = (len(cells) + cols - 1) // cols
    out = Image.new("RGB", (cols * (cw + 16) + 16, nr * (ch + 16) + 16), BG)
    d = ImageDraw.Draw(out)
    for n, (label, im) in enumerate(cells):
        x, y = 16 + (n % cols) * (cw + 16), 16 + (n // cols) * (ch + 16)
        d.text((x, y), label, fill=(255, 255, 255), font=FONT)
        out.paste(im, (x, y + 44))
    out.save(OUT / name)


for kind in ("close", "ctx"):
    rows = []
    for cgb in ("color", "dmg"):
        for r in (24, 32, 40):
            rows.append(("%s  r%d" % (cgb.upper(), r), "r%d_stadium_%s_%s.png" % (r, kind, cgb)))
    sheet("q115_stadium_%s.png" % kind, rows)

rows = []
for cgb in ("color", "dmg"):
    rows += [("%s  r24 (37,28)" % cgb.upper(), "r24_big0_%s.png" % cgb), ("%s  r120 (37,28)" % cgb.upper(), "r120_big0_%s.png" % cgb),
             ("%s  r96 (0,45)" % cgb.upper(), "r96_big1_%s.png" % cgb)]
sheet("q115_biggest.png", rows)

rows = []
for k, n in (("factory", "0 px trimmed"), ("lodge", "11 px trimmed"), ("cow", "1 px trimmed")):
    for cgb in ("color", "dmg"):
        rows += [("%s BEFORE %s" % (k, cgb), "before_%s_%s.png" % (k, cgb)), ("%s AFTER %s, %s" % (k, cgb, n), "after_%s_%s.png" % (k, cgb))]
sheet("q115_trims.png", rows, cols=2)

sheet("q115_whole_fit.png", [("fit curves COLOR", "fitall_whole_color.png"), ("fit curves DMG", "fitall_whole_dmg.png")], cols=1)
