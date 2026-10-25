#!/usr/bin/env python3
"""One labelled contact sheet from several images, so a reviewer opens one picture instead of many.

    python3 tools/dev/contact_sheet.py OUT.png [--scale N] [--cols C] [--title TEXT] [LABEL=]IMAGE ...

- Pixel art is scaled with nearest neighbour (no blur). --scale applies to every image (default 2).
- Labels: "DMG before=out/a.png". Without a label, the file name is used.
- --cols: images per row (default: up to 4). Rows wrap; nothing is cropped.
- Keep sheets compact for a phone: side-by-side grids, not long thin strips.
Only reads the inputs; writes OUT.png.
"""
import argparse
import os
import sys

from PIL import Image, ImageDraw, ImageFont

PAD = 8
LABEL_H = 14
BG = (40, 40, 40)
FG = (235, 235, 235)


def parse_item(arg):
    if "=" in arg and not os.path.exists(arg):
        label, path = arg.split("=", 1)
    else:
        label, path = os.path.basename(arg), arg
    return label, path


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("out")
    ap.add_argument("items", nargs="+")
    ap.add_argument("--scale", type=int, default=2)
    ap.add_argument("--cols", type=int, default=0)
    ap.add_argument("--title", default="")
    a = ap.parse_args()

    font = ImageFont.load_default()
    cells = []
    for item in a.items:
        label, path = parse_item(item)
        try:
            im = Image.open(path).convert("RGB")
        except OSError as e:
            print(f"skip {path}: {e}", file=sys.stderr)
            continue
        if a.scale != 1:
            im = im.resize((im.width * a.scale, im.height * a.scale), Image.NEAREST)
        cells.append((label, im))
    if not cells:
        sys.exit("no readable images")

    cols = a.cols or min(4, len(cells))
    rows = [cells[i:i + cols] for i in range(0, len(cells), cols)]
    col_w = [max(r[c][1].width for r in rows if c < len(r)) for c in range(cols)]
    row_h = [max(im.height for _, im in r) + LABEL_H for r in rows]
    title_h = LABEL_H + PAD if a.title else 0
    W = sum(col_w) + PAD * (cols + 1)
    H = title_h + sum(row_h) + PAD * (len(rows) + 1)

    sheet = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(sheet)
    if a.title:
        d.text((PAD, PAD), a.title, fill=FG, font=font)
    y = title_h + PAD
    for r, h in zip(rows, row_h):
        x = PAD
        for c, (label, im) in enumerate(r):
            d.text((x, y), label, fill=FG, font=font)
            sheet.paste(im, (x, y + LABEL_H))
            x += col_w[c] + PAD
        y += h + PAD
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    sheet.save(a.out)
    print(f"{a.out} {W}x{H}, {len(cells)} images")


if __name__ == "__main__":
    main()
