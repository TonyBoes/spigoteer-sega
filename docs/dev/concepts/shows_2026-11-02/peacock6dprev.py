#!/usr/bin/env python3
"""Preview only: transcribes the hand-drawn grids, decides no pixels. The X flip is the OAM flag the engine uses.

  peacock6bprev.py gif OUT.gif          Color top, DMG below; Zoo stage; x3; 200 ms a beat; HUD y 0-7; uncropped
  peacock6bprev.py still BEAT OUT.png   Color and DMG at 1x, one beat
  peacock6bprev.py x4 BEAT OUT.png      Color above DMG at x4
  peacock6bprev.py frames OUT.png       every frame of both files, flipped copy of A too (x4)

Three performers at x 24/72/120 (24-wide Color figures at x = spot - 4). The loops are the ones in each file's comment lines.
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
A_LOOP_C = [0, 1, 2, 3, 4, 3, 2, 1]
LOOPS_C = [(A_LOOP_C, 1), ([5, 6, 7, 8], 0), (A_LOOP_C, 0)]
A_LOOP_D = [0, 0, 1, 2, 2, 2, 1, 1]
LOOPS_D = [(A_LOOP_D, 1), ([3, 4, 3, 4, 3, 4, 3, 4], 0), (A_LOOP_D, 0)]
PAL = ["#e0f060", "#20a8d8", "#182888"]


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


def put(im, f, x0, flip, cgb, y0=8):
    pal = [hexrgb(h) for h in PAL]
    w = len(f[0])
    for y, r in enumerate(f[:24]):
        for x, c in enumerate(r):
            v = IDX[c]
            if v:
                xx = x0 + (w - 1 - x if flip else x)
                im.putpixel((xx, y0 + y), pal[v - 1] if cgb else DMG_OBJ[v])


def scene(frames, loops, beat, cgb, base):
    im = base.copy()
    w = len(frames[0][0])
    for k, spot in enumerate((24, 72, 120)):
        loop, flip = loops[k]
        put(im, frames[loop[beat % len(loop)]], spot - 4 if w == 24 else spot, flip, cgb)
    ImageDraw.Draw(im).rectangle([0, 0, 159, 7], fill=(0, 0, 0))   # the HUD strip, y 0-7
    return im


def load():
    return blocks(HERE / "zoo_show_peacock6d_cgb.txt"), blocks(HERE / "zoo_show_peacock6_dmg.txt")


def both(beat, bases):
    fc, fd = load()
    return scene(fc, LOOPS_C, beat, True, bases[0]), scene(fd, LOOPS_D, beat, False, bases[1])


def stacked(beat, bases, z, label=True):
    c, d = both(beat, bases)
    g = 6
    im = Image.new("RGB", (160 * z, 64 * z + g + (12 if label else 0)), (40, 40, 40))
    y0 = 12 if label else 0
    if label:
        ImageDraw.Draw(im).text((2, 0), f"peacock 6d: Color top, DMG below; beat {beat}", fill=(235, 235, 235))
    im.paste(c.resize((160 * z, 32 * z), Image.NEAREST), (0, y0))
    im.paste(d.resize((160 * z, 32 * z), Image.NEAREST), (0, y0 + 32 * z + g))
    return im


def frame_strip(bases):
    fc, fd = load()
    pad = 4
    cw = max(len(fc) * (24 + pad), len(fd) * (24 + pad))
    im = Image.new("RGB", (cw, 24 * 3 + 12 + 8), (40, 40, 40))
    for i, f in enumerate(fc):
        cell = bases[0].crop((8, 8, 32, 32))
        put(cell, f, 0, 0, True, 0)
        im.paste(cell, (i * (24 + pad), 0))
    for i, f in enumerate(fc[:5]):       # the left performer's X flip of A
        cell = bases[0].crop((8, 8, 32, 32))
        put(cell, f, 0, 1, True, 0)
        im.paste(cell, (i * (24 + pad), 24 + 4))
    for i, f in enumerate(fd):
        cell = bases[1].crop((8, 8, 32, 32))
        put(cell, f, 4, 0, False, 0)
        im.paste(cell, (i * (24 + pad), 52))
    return im.resize((im.width * 4, im.height * 4), Image.NEAREST)


def main():
    bases = (stage_img(True), stage_img(False))
    m = sys.argv[1]
    if m == "gif":
        frames = [stacked(b, bases, Z).quantize(256, dither=Image.Dither.NONE) for b in range(8)]
        frames[0].save(sys.argv[2], save_all=True, append_images=frames[1:], duration=200, loop=0)
    elif m == "still":
        c, d = both(int(sys.argv[2]), bases)
        im = Image.new("RGB", (160, 68), (40, 40, 40))
        im.paste(c, (0, 0))
        im.paste(d, (0, 36))
        im.save(sys.argv[3])
    elif m == "x4":
        stacked(int(sys.argv[2]), bases, 4, False).save(sys.argv[3])
    else:
        frame_strip(bases).save(sys.argv[2])


main()
