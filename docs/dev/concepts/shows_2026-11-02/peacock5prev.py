#!/usr/bin/env python3
"""Preview only: transcribes the hand-drawn grids, decides no pixels.

  peacock5prev.py gif OUT.gif      A top, B bottom; Color left, DMG right; x3, 200 ms a beat; HUD strip y 0-7
  peacock5prev.py sheet OUT.png    every beat of the loop (stills of the same scene) on one sheet

Three dancers at x 24/72/120 (the 24-wide Color figures at x = spot - 4). Each performer plays its own loop
(LOOPS below, written in each file's comment line). One beat = 12 game frames = 200 ms. Stage: the zoo's stage art.
"""
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
VD = ROOT / "assets/approved/venues"
IDX = {".": 0, "-": 1, "+": 2, "#": 3}
DMG_BG = [(255, 255, 255), (170, 170, 170), (85, 85, 85), (0, 0, 0)]
DMG_OBJ = [None, (255, 255, 255), (170, 170, 170), (0, 0, 0)]
Z = 3
# 5 frames 0..4: closed, lift, half, full, full-shimmer; each performer a rotation of the 8-beat ping-pong
LOOPS = [[0, 1, 2, 3, 4, 3, 2, 1], [2, 3, 4, 3, 2, 1, 0, 1], [4, 3, 2, 1, 0, 1, 2, 3]]
SETS = {
    "A": ("zoo_show_peacock5a_cgb.txt", "zoo_show_peacock5a_dmg.txt", "zoo_show_pal_peacock.json"),
    "B": ("zoo_show_peacock5b_cgb.txt", "zoo_show_peacock5b_dmg.txt", "zoo_show_pal_peacock_b.json"),
}


def blocks(path):
    res, cur = [], []
    for line in Path(path).read_text().splitlines() + [""]:
        line = line.rstrip()
        if line.startswith(";"):
            continue
        if line == "":
            if cur:
                res.append(cur)
                cur = []
            continue
        cur.append(line)
    return res


def hexrgb(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


def plain(p):
    return [l for l in Path(p).read_text().splitlines() if l and not l.startswith(";")]


def stage_img(cgb):
    t = "zoo"
    rows, attr = plain(VD / f"{t}_stage.txt"), plain(VD / f"{t}_attr.txt")
    pal = json.loads((VD / f"{t}_pal.json").read_text())
    pa, pb = [[hexrgb(h) for h in pal[k]["hex"]] for k in ("stage_a", "stage_b")]
    im = Image.new("RGB", (160, 32))
    for y in range(32):
        for x in range(160):
            v = IDX[rows[y][x]]
            im.putpixel((x, y), (pb if attr[y // 8][x // 8] == "1" else pa)[v] if cgb else DMG_BG[v])
    return im


def scene(frames, loops, beat, cgb, base, pal):
    im = base.copy()
    w = len(frames[0][0])
    for k, spot in enumerate((24, 72, 120)):
        f = frames[loops[k][beat % len(loops[k])]]
        x0 = spot - 4 if w == 24 else spot
        for y, r in enumerate(f[:24]):
            for x, c in enumerate(r):
                v = IDX[c]
                if v:
                    im.putpixel((x0 + x, 8 + y), pal[v - 1] if cgb else DMG_OBJ[v])
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, 159, 7], fill=(0, 0, 0))      # the HUD strip, y 0-7
    return im


def panel(name, beat, cgb, bases):
    cf, df, pj = SETS[name]
    pal = [hexrgb(h) for h in json.loads((HERE / pj).read_text())["obj"]["hex"]]
    fr = blocks(HERE / (cf if cgb else df))
    return scene(fr, LOOPS, beat, cgb, bases[0 if cgb else 1], pal).resize((160 * Z, 32 * Z), Image.NEAREST)


def beat_image(beat, bases, label=True):
    g = 6
    W, H = 160 * Z * 2 + g, 32 * Z * 2 + g + (12 if label else 0)
    im = Image.new("RGB", (W, H), (40, 40, 40))
    d = ImageDraw.Draw(im)
    if label:
        d.text((2, 0), f"peacock 5: A top, B bottom; Color left, DMG right; beat {beat}", fill=(235, 235, 235))
    y0 = 12 if label else 0
    for r, name in enumerate("AB"):
        for c, cgb in enumerate((True, False)):
            im.paste(panel(name, beat, cgb, bases), (c * (160 * Z + g), y0 + r * (32 * Z + g)))
    return im


def still_1x(beat, bases):
    """the in-game picture at 1x: A top, B bottom; Color left, DMG right"""
    im = Image.new("RGB", (160 * 2 + 4, 32 * 2 + 4), (40, 40, 40))
    for r, name in enumerate("AB"):
        for c, cgb in enumerate((True, False)):
            cf, df, pj = SETS[name]
            pal = [hexrgb(h) for h in json.loads((HERE / pj).read_text())["obj"]["hex"]]
            fr = blocks(HERE / (cf if cgb else df))
            im.paste(scene(fr, LOOPS, beat, cgb, bases[0 if cgb else 1], pal), (c * 164, r * 36))
    return im


def frame_strip(name, bases):
    """every frame of A or B alone on the stage wall: Color row over DMG row (x1; the sheet scales it)"""
    cf, df, pj = SETS[name]
    pal = [hexrgb(h) for h in json.loads((HERE / pj).read_text())["obj"]["hex"]]
    rows = []
    for cgb in (True, False):
        fr = blocks(HERE / (cf if cgb else df))
        w = len(fr[0][0])
        row = Image.new("RGB", (len(fr) * 28, 24), (40, 40, 40))
        for i, f in enumerate(fr):
            cell = bases[0 if cgb else 1].crop((8, 8, 32, 32))
            for y, r in enumerate(f[:24]):
                for x, c in enumerate(r):
                    v = IDX[c]
                    if v:
                        cell.putpixel((x + (24 - w) // 2, y), pal[v - 1] if cgb else DMG_OBJ[v])
            row.paste(cell, (i * 28, 0))
        rows.append(row)
    out = Image.new("RGB", (rows[0].width, 52), (40, 40, 40))
    out.paste(rows[0], (0, 0))
    out.paste(rows[1], (0, 28))
    return out


def main():
    bases = (stage_img(True), stage_img(False))
    if sys.argv[1] == "still":
        still_1x(int(sys.argv[2]), bases).save(sys.argv[3])
    elif sys.argv[1] == "frames":
        frame_strip(sys.argv[2], bases).save(sys.argv[3])
    elif sys.argv[1] == "gif":
        frames = [beat_image(b, bases).quantize(256, dither=Image.Dither.NONE) for b in range(8)]
        frames[0].save(sys.argv[2], save_all=True, append_images=frames[1:], duration=200, loop=0)
    else:
        ims = [beat_image(b, bases) for b in range(8)]
        w, h = ims[0].size
        sheet = Image.new("RGB", (w * 2 + 6, h * 4 + 18), (40, 40, 40))
        for i, im in enumerate(ims):
            sheet.paste(im, ((i % 2) * (w + 6), (i // 2) * (h + 6)))
        sheet.save(sys.argv[2])


main()
