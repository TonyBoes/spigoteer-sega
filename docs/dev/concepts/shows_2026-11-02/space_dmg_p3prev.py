#!/usr/bin/env python3
"""Preview only (transcribes the hand-drawn grids, decides no pixels; a flip is the hardware X-flip): space DMG p3.

  space_dmg_p3prev.py chk             frame sizes, 8x16 quarter count, changed cells vs p1 per frame
  space_dmg_p3prev.py gif OUT.gif     x3, 200 ms a beat, DMG: p1 | p3a | p3b side by side, on the stage
  space_dmg_p3prev.py sheet OUT.png   contact sheet: strum frames x8, each band at 1x
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
src = (HERE / "showprev.py").read_text().rsplit("\nmain()", 1)[0]
ns = {"__file__": str(HERE / "showprev.py")}
exec(compile(src, "showprev.py", "exec"), ns)
from PIL import Image, ImageDraw  # noqa: E402

P1 = HERE / "space_show_dmg_p1.txt"
PA = HERE / "space_show_dmg_p3a.txt"
PB = HERE / "space_show_dmg_p3b.txt"
LOOPS = [[0, 1, 2, 3], [1, 2, 3, 0], [2, 3, 0, 1]]
FLIPS = [1, 0, 0]
XS = (24, 72, 120)


def load(path):
    fr = ns["blocks"](path)
    for n, f in enumerate(fr):
        bad = [(y, r) for y, r in enumerate(f) if len(r) != 16 or not set(r) <= set(".-+#")]
        assert len(f) == 24 and not bad, f"{path}: frame {n}: {len(f)} rows; bad {bad}"
    assert len(fr) == 4
    return fr


def quarters(frames):
    qs = []
    for f in frames:
        f = list(f) + ["." * 16] * 8
        cells = 0
        for y0, x0 in ((0, 0), (0, 8), (16, 0), (16, 8)):
            q = tuple(r[x0:x0 + 8] for r in f[y0:y0 + 16])
            if any(c != "." for r in q for c in r):
                cells += 1
                if q not in qs:
                    qs.append(q)
        assert cells <= 4
    return len(qs)


def put(im, f, x0, y0, flip):
    for y, r in enumerate(f):
        for x, c in enumerate(r):
            v = ns["IDX"][c]
            if v:
                im.putpixel((x0 + (15 - x if flip else x), y0 + y), ns["DMG_OBJ"][v])


def scene(fr, beat, base):
    im = base.copy()
    for k, x0 in enumerate(XS):
        put(im, fr[LOOPS[k][beat % 4]], x0, 8, FLIPS[k])
    return im


def changed(a, b):
    out = []
    for n in range(4):
        out.append([(x, y) for y in range(24) for x in range(16) if a[n][y][x] != b[n][y][x]])
    return out


def report(name, new, old):
    print(name, "quarters", quarters(new), "(p1", quarters(old), ")")
    for n, c in enumerate(changed(old, new)):
        # head rows: F0/F2 rows 0-11, F1/F3 rows 0-13 (dip); feet rows 20-23 must be untouched
        head = 11 if n in (0, 2) else 13
        # a head pixel (non-transparent in p1) may not change; new pixels beside the head are effect/arm; feet rows untouched
        bad = [(x, y) for x, y in c if (y <= head and old[n][y][x] != ".") or y >= 20]
        xs = [x for x, y in c]
        ys = [y for x, y in c]
        box = f"x{min(xs)}-{max(xs)} y{min(ys)}-{max(ys)}" if c else "none"
        print(f"  F{n}: {len(c)} cells changed, box {box}, outside arm/hand/harp/effect rows: {bad if bad else 'none'}")


def main():
    cmd = sys.argv[1]
    p1, pa, pb = load(P1), load(PA), load(PB)
    if cmd == "chk":
        report("p3a", pa, p1)
        report("p3b", pb, p1)
        return
    base = ns["stage_img"]("space", False)
    out = sys.argv[2]
    S = 3
    names = ("DMG p1", "DMG p3a", "DMG p3b")
    sets = (p1, pa, pb)
    if cmd == "gif":
        frames = []
        for beat in range(8):
            W = 160 * S
            im = Image.new("RGB", (W * 3 + 16, 32 * S + 14), (40, 40, 40))
            d = ImageDraw.Draw(im)
            for i in range(3):
                d.text((i * (W + 8) + 2, 1), names[i], fill=(235, 235, 235))
                im.paste(scene(sets[i], beat, base).resize((W, 32 * S), Image.NEAREST), (i * (W + 8), 14))
            frames.append(im.quantize(256, dither=Image.Dither.NONE))
        frames[0].save(out, save_all=True, append_images=frames[1:], duration=200, loop=0)
        return
    sh = Image.new("RGB", (1310, 1180), (40, 40, 40))
    d = ImageDraw.Draw(sh)
    y = 4
    d.text((8, y), "x8: p1 (top), p3a, p3b: frames F0 F1 F2 F3 (F0/F2 head up, F1/F3 dip, F3 leaned)", fill=(255, 255, 0))
    for j, fs in enumerate(sets):
        for i, f in enumerate(fs):
            g = Image.new("RGB", (16, 24), ns["DMG_BG"][1])
            put(g, f, 0, 0, 0)
            sh.paste(g.resize((128, 192), Image.NEAREST), (8 + i * 148 + 0, y + 16 + j * 200))
    d.text((620, 20), "p1", fill=(255, 255, 0))
    d.text((620, 220), "p3a", fill=(255, 255, 0))
    d.text((620, 420), "p3b", fill=(255, 255, 0))
    y = 620
    d.text((8, y), "1x, the band, beats 0 1 2 3 (left to right): p1, p3a, p3b rows", fill=(255, 255, 0))
    for j, fs in enumerate(sets):
        for b in range(4):
            sh.paste(scene(fs, b, base), (8 + (b % 2) * 170 + (b // 2) * 340, y + 16 + j * 40) if False else (8 + b * 170, y + 16 + j * 40))
    y = 760
    d.text((8, y), "x4 band: left beat 1 (F1 on the middle performer: dip), right beat 3 (F3: dip + lean); rows p1, p3a, p3b", fill=(255, 255, 0))
    for j, fs in enumerate(sets):
        for i, b in enumerate((1, 3)):
            sh.paste(scene(fs, b, base).resize((640, 128), Image.NEAREST), (8 + i * 650, y + 16 + j * 134))
    sh.save(out)


main()
