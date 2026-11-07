"""The bridges before | after, each in context at x4, two columns, big labels (phone).  python3 -I sheet_bridges.py
before = out/a5/log_v1 (SMAP_BRIDGE=old look), after = out/a5/br_new (and br_newl for the light DMG water)."""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[4]
A = ROOT / "out" / "a5"
S = 4
BR = [("LAKE BRIDGE", (35, 60, 49, 66)), ("RIVER BRIDGE BY THE POOL", (42, 9, 56, 15)), ("MILL RACE BRIDGE", (44, 30, 58, 36))]
font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 30) if Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf").exists() else ImageFont.load_default(size=30)


def sheet(out, modes):
    w = (15 * 8 * S) * 2 + 70
    rows = [(n, c, m) for n, c in BR for m in modes]
    ph = 7 * 8 * S
    im = Image.new("RGB", (w, 48 + len(rows) * (ph + 50)), (30, 30, 30))
    d = ImageDraw.Draw(im)
    d.text((10, 6), "BEFORE", fill=(255, 120, 120), font=font)
    d.text((15 * 8 * S + 70, 6), "AFTER", fill=(120, 255, 140), font=font)
    for k, (name, (x0, y0, x1, y1), (mname, fb, fa)) in enumerate(rows):
        y = 48 + k * (ph + 50)
        d.text((10, y + 6), f"{name} - {mname}", fill=(255, 235, 120), font=font)
        for col, f in ((0, fb), (1, fa)):
            c = Image.open(A / f).crop((x0 * 8, y0 * 8, (x1 + 1) * 8, (y1 + 1) * 8)).resize((15 * 8 * S, ph), Image.NEAREST)
            im.paste(c, (col * (15 * 8 * S + 70), y + 46))
    im.save(out)
    print(out, im.size)


sheet(ROOT / "out" / "a5" / "sheet_bridges.png", [("COLOR", "log_v1/lay_A5_cgb.png", "br_new/lay_A5_cgb.png"), ("DMG", "log_v1/lay_A5_dmg.png", "br_new/lay_A5_dmg.png")])
sheet(ROOT / "out" / "a5" / "sheet_bridges_light.png", [("DMG LIGHT WATER", "log_v1l/lay_A5_dmg.png", "br_newl/lay_A5_dmg.png")])
