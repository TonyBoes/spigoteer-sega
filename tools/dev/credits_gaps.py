#!/usr/bin/env python3
"""The gaps of the scrolling credits as the screen shows them: blank pixel rows between the last ink of one block and the first ink of the next (CRSCENE / CRSPLIT builds).

    python3 tools/dev/credits_gaps.py ROM [--models dmg,cgb] [--min 6] [--sheet OUT.png] [--cut]

Runs the roll, takes every frame's lines 16-127 into a tall picture of the world (world y = the scroll + the line; Color at double speed as shipped), and lists the runs of blank
rows (every pixel the roll's background colour: black #080818 on Color, shade 3 on a DMG) that are at least --min px long, with the world y they start at and the ink above and below
(the rows' share of non-background pixels). A sprite is ink where it stood when the line was taken. --sheet writes the tall picture, cut at the listed runs: one panel for each run
(its blank rows and 16 px of ink each side), all at the same scale, labelled with the run's number and size. Reads the ROM, writes only --sheet."""
import argparse
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tests"))
sys.path.insert(0, str(ROOT / "tools" / "dev"))
from credits_shots import start      # noqa: E402


def world(rom, model, max_frames=11000):
    gb = start(rom, model)
    rows = {}
    last = -1
    for n in range(max_frames):
        gb.pb.tick(1, True)
        st = gb.read("story_scratch", 30)
        s = st[20] | st[21] << 8
        scy = gb.pb.memory[0xFF42]
        w = (s & ~255) | scy
        if w - s > 128:
            w -= 256
        elif s - w > 128:
            w += 256
        if w == last:
            continue
        last = w
        img = np.asarray(gb.pb.screen.image.convert("RGB")).astype(np.int16)
        for ln in range(96, 128):
            rows[w + ln] = img[ln]
        if gb.mem("story_phase") != 8:
            break
    return rows


def runs(rows, min_len):
    ys = sorted(rows)
    y0, y1 = ys[0], ys[-1]
    bg = np.array((8, 8, 24)) if rows[ys[len(ys) // 2]].shape else None
    # the background colour: the most common colour of the whole picture
    allp = np.concatenate([rows[y] for y in ys[::7]])
    u, c = np.unique(allp, axis=0, return_counts=True)
    bg = u[c.argmax()]
    blank = {y: bool((rows[y] == bg).all()) for y in ys}
    out = []
    y = y0
    while y <= y1:
        if y in blank and blank[y]:
            e = y
            while e + 1 in blank and blank[e + 1]:
                e += 1
            if e - y + 1 >= min_len and y > y0 + 4 and e < y1 - 4:
                out.append((y, e - y + 1))
            y = e + 1
        else:
            y += 1
    return out, bg


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("rom")
    ap.add_argument("--models", default="cgb,dmg")
    ap.add_argument("--min", type=int, default=6)
    ap.add_argument("--sheet")
    ap.add_argument("--yrange", help="Y0,Y1: the sheet shows only the runs that start inside this world-y range")
    a = ap.parse_args()
    for model in a.models.split(","):
        rows = world(a.rom, model)
        rr, bg = runs(rows, a.min)
        ys = sorted(rows)
        print(f"{model}: world y {ys[0]}..{ys[-1]} ({len(ys)} rows), background {tuple(int(v) for v in bg)}, {len(rr)} blank runs >= {a.min} px")
        for i, (y, n) in enumerate(rr):
            print(f"  {i:2d} y {y:5d} (row {y / 8:6.1f}) blank {n:3d} px ({n / 8:.1f} rows)")
        if a.sheet:
            panels = []
            lo_, hi_ = (int(v) for v in a.yrange.split(",")) if a.yrange else (-10**9, 10**9)
            for i, (y, n) in enumerate(rr):
                if not lo_ <= y <= hi_:
                    continue
                lo, hi = y - 16, y + n + 16
                pn = np.zeros((hi - lo, 160, 3), np.uint8)
                for k, yy in enumerate(range(lo, hi)):
                    pn[k] = rows[yy] if yy in rows else (90, 90, 90)
                panels.append((i, n, pn))
            if not panels:
                continue
            mx = max(p[2].shape[0] for p in panels)
            cols = 8
            nr = (len(panels) + cols - 1) // cols
            sheet = Image.new("RGB", (cols * 166, nr * (mx + 14)), (60, 60, 60))
            d = ImageDraw.Draw(sheet)
            for k, (i, n, pn) in enumerate(panels):
                x, yy = (k % cols) * 166, (k // cols) * (mx + 14)
                sheet.paste(Image.fromarray(pn), (x, yy + 12))
                d.text((x + 2, yy), f"{i}: {n}px", fill=(255, 255, 0))
            p = Path(a.sheet)
            sheet.save(p.with_name(p.stem + "_" + model + p.suffix))


if __name__ == "__main__":
    main()
