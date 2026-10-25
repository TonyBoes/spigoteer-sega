#!/usr/bin/env python3
"""Read-only golden diff report: bounding box of each change, and an optional shift test.

    python3 tools/dev/golden_bbox.py [--worktree DIR] [--shift DX,DY] [--sheet OUT.png] [NAME ...]

- Pairs each out/diff/<name>.actual.png with the golden of the same name under tests/golden/ (searched recursively).
  With no NAMEs, every *.actual.png in out/diff/ is checked.
- Prints one row per golden: name | size | changed pixels | bbox (x0,y0,x1,y1 inclusive, in the PNG's pixels).
- --shift DX,DY: also compares the new picture with the old golden moved by (DX,DY), for layout shifts. The residual
  (pixels that still differ inside the overlap) should be only animated sprites; its count and bbox are printed.
  The band the shift uncovers (e.g. the top DY rows) has no old pixels to compare: check it on the --sheet.
- --sheet OUT.png: a contact sheet of old | new | diff for every changed golden (diff in magenta).
Never writes under tests/golden/.
"""
import argparse
import glob
import os
import sys

from PIL import Image, ImageChops


def bbox_and_count(a, b):
    diff = ImageChops.difference(a, b).convert("L").point(lambda v: 255 if v else 0)
    box = diff.getbbox()
    count = diff.histogram()[255]
    return box, count, diff


def shifted_residual(old, new, dx, dy):
    W, H = new.size
    x0, y0 = max(0, dx), max(0, dy)
    x1, y1 = min(W, W + dx), min(H, H + dy)
    if x1 <= x0 or y1 <= y0:
        return None, 0
    new_c = new.crop((x0, y0, x1, y1))
    old_c = old.crop((x0 - dx, y0 - dy, x1 - dx, y1 - dy))
    box, count, _ = bbox_and_count(old_c, new_c)
    if box:
        box = (box[0] + x0, box[1] + y0, box[2] + x0, box[3] + y0)
    return box, count


def fmt(box):
    return "-" if not box else f"{box[0]},{box[1]},{box[2] - 1},{box[3] - 1}"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("names", nargs="*")
    ap.add_argument("--worktree", default=".")
    ap.add_argument("--shift", default="")
    ap.add_argument("--sheet", default="")
    a = ap.parse_args()

    wt = os.path.abspath(a.worktree)
    if a.sheet and os.path.abspath(a.sheet).startswith(os.path.join(wt, "tests", "golden")):
        sys.exit("refusing to write under tests/golden/")
    diff_dir = os.path.join(wt, "out", "diff")
    names = a.names or sorted(os.path.basename(p)[:-len(".actual.png")]
                              for p in glob.glob(os.path.join(diff_dir, "*.actual.png")))
    goldens = {}
    for p in glob.glob(os.path.join(wt, "tests", "golden", "**", "*.png"), recursive=True):
        goldens.setdefault(os.path.basename(p)[:-4], p)
    dx = dy = None
    if a.shift:
        dx, dy = (int(v) for v in a.shift.split(","))

    print("golden | size | changed px | bbox" + (f" | residual after shift {dx},{dy} (px, bbox)" if a.shift else ""))
    if a.shift:
        print(f"(the band uncovered by the shift is not compared: check it on the sheet)")
    sheet_items = []
    for n in names:
        actual = os.path.join(diff_dir, n + ".actual.png")
        if n not in goldens or not os.path.exists(actual):
            print(f"{n} | missing {'golden' if n not in goldens else 'actual'}")
            continue
        old = Image.open(goldens[n]).convert("RGB")
        new = Image.open(actual).convert("RGB")
        if old.size != new.size:
            print(f"{n} | size differs {old.size} -> {new.size}")
            continue
        box, count, diff = bbox_and_count(old, new)
        row = f"{n} | {new.size[0]}x{new.size[1]} | {count} | {fmt(box)}"
        if a.shift:
            rbox, rcount = shifted_residual(old, new, dx, dy)
            row += f" | {rcount}, {fmt(rbox)}"
        print(row)
        if a.sheet and box:
            mask = Image.new("RGB", new.size, (255, 0, 255))
            overlay = Image.composite(mask, new.convert("L").convert("RGB"), diff)
            sheet_items.append((n, old, new, overlay))

    if a.sheet and sheet_items:
        scale = 2 if sheet_items[0][1].width < 400 else 1
        w, h = sheet_items[0][1].width * scale, sheet_items[0][1].height * scale
        S = Image.new("RGB", (w * 3 + 32, (h + 18) * len(sheet_items) + 8), (40, 40, 40))
        from PIL import ImageDraw
        d = ImageDraw.Draw(S)
        for i, (n, o, nw, ov) in enumerate(sheet_items):
            y = 8 + i * (h + 18)
            d.text((8, y), f"{n}: old | new | diff", fill=(235, 235, 235))
            for j, im in enumerate((o, nw, ov)):
                S.paste(im.resize((w, h), Image.NEAREST), (8 + j * (w + 8), y + 14))
        os.makedirs(os.path.dirname(os.path.abspath(a.sheet)), exist_ok=True)
        S.save(a.sheet)
        print(f"sheet: {a.sheet}")


if __name__ == "__main__":
    main()
