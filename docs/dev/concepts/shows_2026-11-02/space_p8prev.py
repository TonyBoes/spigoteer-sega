#!/usr/bin/env python3
"""Preview only (transcribes the hand-drawn grids, decides no pixels): space p6 (left) beside p8 Color (right).

  space_p7prev.py gif OUT.gif     x3, 200 ms a beat, Colour over DMG, the 32-row stage strip uncropped
  space_p7prev.py sheet OUT.png   contact sheet: 1x, x4, every changed frame x8 (Colour and DMG)
  space_p7prev.py chk             frame sizes and the 8x16 quarter count of p7

p6: 16x24 frames, loops singer 0 1, keytar 2 3, alien 4 5 6 5 7 5. p7: singer 0 1, keytar 2 3 4 5, alien 6 7 8 7 9 7.
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
src = (HERE / "showprev.py").read_text().rsplit("\nmain()", 1)[0]
ns = {"__file__": str(HERE / "showprev.py")}
exec(compile(src, "showprev.py", "exec"), ns)
from PIL import Image, ImageDraw  # noqa: E402

T = "space"
LOOP6 = [[0, 1], [2, 3], [4, 5, 6, 5, 7, 5]]
LOOP7 = [[0, 1, 2, 3], [4, 5, 6, 7], [8, 9, 10, 9, 11, 9]]


def load(path, rows):
    fr = ns["blocks"](path)
    for n, f in enumerate(fr):
        bad = [(y, r) for y, r in enumerate(f) if len(r) != 16 or not set(r) <= set(".-+#")]
        assert len(f) == rows and not bad, f"{path}: frame {n}: {len(f)} rows; bad {bad}"
    return fr


def quarters(frames):
    qs = []
    for f in frames:
        f = list(f) + ["." * 16] * 8
        for y0, x0 in ((0, 0), (0, 8), (16, 0), (16, 8)):
            q = tuple(r[x0:x0 + 8] for r in f[y0:y0 + 16])
            if q not in qs:
                qs.append(q)
    return len(qs)


def pal():
    return [ns["hexrgb"](h) for h in ns["json"].loads((ns["VD"] / f"{T}_show_pal.json").read_text())["obj"]["hex"]]


def put(im, f, x0, y0, cgb, p):
    for y, r in enumerate(f):
        for x, c in enumerate(r):
            v = ns["IDX"][c]
            if v:
                im.putpixel((x0 + x, y0 + y), p[v - 1] if cgb else ns["DMG_OBJ"][v])


def scene(fr, loops, beat, cgb, base):
    im, p = base.copy(), pal()
    for k, x0 in enumerate((24, 72, 120)):
        put(im, fr[loops[k][beat % len(loops[k])]], x0, 8, cgb, p)
    return im


def stack(a, b, scale):
    im = Image.new("RGB", (160, 66), (40, 40, 40))
    im.paste(a, (0, 0))
    im.paste(b, (0, 34))
    return im.resize((160 * scale, 66 * scale), Image.NEAREST)


def main():
    cmd = sys.argv[1]
    p6 = load(str(HERE / "space_show_p7_cgb.txt"), 24)
    LOOP6[:] = [[0, 1], [2, 3, 4, 5], [6, 7, 8, 7, 9, 7]]
    p7 = load(str(HERE / "space_show_p8_cgb.txt"), 24)
    if cmd == "chk":
        print(len(p7), "frames; quarters p7:", quarters(p7), "singer", quarters(p7[0:2]), "keytar", quarters(p7[2:6]),
              "alien", quarters(p7[6:10]))
        return
    bases = (ns["stage_img"](T, True), ns["stage_img"](T, False))
    left = lambda b, s: stack(scene(p6, LOOP6, b, True, bases[0]), scene(p6, LOOP6, b, False, bases[1]), s)
    right = lambda b, s: stack(scene(p7, LOOP7, b, True, bases[0]), scene(p7, LOOP7, b, False, bases[1]), s)
    out = sys.argv[2]
    if cmd == "gif":
        S, frames = 3, []
        for beat in range(12):
            l, r = left(beat, S), right(beat, S)
            im = Image.new("RGB", (l.width * 2 + 8, l.height + 14), (40, 40, 40))
            d = ImageDraw.Draw(im)
            d.text((2, 1), "before", fill=(235, 235, 235))
            d.text((l.width + 10, 1), "new: keytar, original alien, maracas", fill=(235, 235, 235))
            im.paste(l, (0, 14))
            im.paste(r, (l.width + 8, 14))
            frames.append(im.quantize(256, dither=Image.Dither.NONE))
        frames[0].save(out, save_all=True, append_images=frames[1:], duration=200, loop=0)
        return
    pj = ns["json"].loads((ns["VD"] / f"{T}_pal.json").read_text())
    sh = Image.new("RGB", (1300, 1230), (40, 40, 40))
    d = ImageDraw.Draw(sh)
    d.text((8, 4), "Space show p7 (Color). 1x in game, beats 0-5: p6 (upper pair) over p7 (lower pair); each pair Colour over DMG. Keytar 2 3 4 5, alien 6 7 8 7 9 7", fill=(255, 255, 0))
    for b in range(6):
        sh.paste(left(b, 1), (8 + b * 214, 20))
        sh.paste(right(b, 1), (8 + b * 214, 92))
    d.text((8, 166), "x4 p7 beat 0 and beat 1 (keytar down, alien B), beat 2, beat 3 (keytar down+tilt)", fill=(255, 255, 0))
    for i, b in enumerate((0, 1, 2, 3)):
        sh.paste(right(b, 4).crop((260, 0, 580, 264)), (8 + i * 324, 180))
    d.text((8, 450), "x8 keytar frames K0-K3 and alien frames A B C D (p7), Colour on the stage wall, DMG below", fill=(255, 255, 0))
    for i, fi in enumerate(range(2, 10)):
        a = Image.new("RGB", (16, 24), ns["hexrgb"](pj["stage_a"]["hex"][1]))
        g = Image.new("RGB", (16, 24), ns["DMG_BG"][2])
        put(a, p7[fi], 0, 0, True, pal())
        put(g, p7[fi], 0, 0, False, pal())
        sh.paste(a.resize((128, 192), Image.NEAREST), (8 + i * 160, 466))
        sh.paste(g.resize((128, 192), Image.NEAREST), (8 + i * 160, 666))
    d.text((8, 866), "x4 old p6 keytar and alien for comparison (frames 2 3 4 5 6 7)", fill=(255, 255, 0))
    for i, fi in enumerate(range(2, 8)):
        a = Image.new("RGB", (16, 24), ns["hexrgb"](pj["stage_a"]["hex"][1]))
        put(a, p6[fi], 0, 0, True, pal())
        sh.paste(a.resize((64, 96), Image.NEAREST), (8 + i * 80, 882))
    sh.save(out)


main()
