#!/usr/bin/env python3
"""Preview only (transcribes the hand-drawn grids, decides no pixels): space p5 (left) beside p6 Color (right).

  space_p6prev.py gif OUT.gif     x3, 200 ms a beat, Colour over DMG, the 32-row stage strip uncropped
  space_p6prev.py sheet OUT.png   contact sheet: 1x, x4, every frame x8 (Colour and DMG)
  space_p6prev.py chk             frame sizes and the 8x16 quarter count of p6

p5: 16x24 frames at strip y 8 (as the engine draws them). p6: 16x32 frames, feet on the same strip row, so row 0 is at strip y 0.
Loops: singer 0 1, keytar 2 3, alien frames 4 5 6 5 7 5 (poses A B C B D B).
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
src = (HERE / "showprev.py").read_text().rsplit("\nmain()", 1)[0]
ns = {"__file__": str(HERE / "showprev.py")}
exec(compile(src, "showprev.py", "exec"), ns)
from PIL import Image, ImageDraw  # noqa: E402

T = "space"
LOOP_ALIEN = [4, 5, 6, 5, 7, 5]


def load(path, rows):
    fr = ns["blocks"](path)
    for n, f in enumerate(fr):
        bad = [(y, r) for y, r in enumerate(f) if len(r) != 16 or not set(r) <= set(".-+#")]
        assert len(f) == rows and not bad, f"{path}: frame {n}: {len(f)} rows; bad {bad}"
    return fr


def quarters(frames):
    qs = []
    for f in frames:
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


def scene5(fr, beat, cgb, base):
    im, p = base.copy(), pal()
    for k, x0 in enumerate((24, 72, 120)):
        put(im, fr[2 * k + (beat & 1)], x0, 8, cgb, p)
    return im


def scene6(fr, beat, cgb, base):
    im, p = base.copy(), pal()
    for k, x0 in enumerate((24, 72, 120)):
        i = (beat & 1) + 2 * k if k < 2 else LOOP_ALIEN[beat % len(LOOP_ALIEN)]
        put(im, fr[i], x0, 0, cgb, p)
    return im


def stack(a, b, scale):
    im = Image.new("RGB", (160, 66), (40, 40, 40))
    im.paste(a, (0, 0))
    im.paste(b, (0, 34))
    return im.resize((160 * scale, 66 * scale), Image.NEAREST)


def main():
    cmd = sys.argv[1]
    p5 = load(str(HERE / "space_show_p5.txt"), 24)
    p6 = load(str(HERE / "space_show_p6_cgb.txt"), 32)
    if cmd == "chk":
        print(len(p6), "frames; quarters p6:", quarters(p6), "singer", quarters(p6[0:2]), "keytar", quarters(p6[2:4]),
              "alien", quarters(p6[4:8]))
        return
    bases = (ns["stage_img"](T, True), ns["stage_img"](T, False))
    left = lambda b, s: stack(scene5(p5, b, True, bases[0]), scene5(p5, b, False, bases[1]), s)
    right = lambda b, s: stack(scene6(p6, b, True, bases[0]), scene6(p6, b, False, bases[1]), s)
    out = sys.argv[2]
    if cmd == "gif":
        S, frames = 3, []
        for beat in range(12):
            l, r = left(beat, S), right(beat, S)
            im = Image.new("RGB", (l.width * 2 + 8, l.height + 14), (40, 40, 40))
            d = ImageDraw.Draw(im)
            d.text((2, 1), "p5 today (DMG keeps it): bust + 3 rows", fill=(235, 235, 235))
            d.text((l.width + 10, 1), "p6 Color: full body, alien loops A B C B D B", fill=(235, 235, 235))
            im.paste(l, (0, 14))
            im.paste(r, (l.width + 8, 14))
            frames.append(im.quantize(256, dither=Image.Dither.NONE))
        frames[0].save(out, save_all=True, append_images=frames[1:], duration=200, loop=0)
        return
    # contact sheet: 1x pairs (p5 over p6), x4 p6 scenes, every alien frame x8 on the stage wall, Colour over DMG
    pj = ns["json"].loads((ns["VD"] / f"{T}_pal.json").read_text())
    sh = Image.new("RGB", (1300, 1090), (40, 40, 40))
    d = ImageDraw.Draw(sh)
    d.text((8, 4), "Space show p6 (Color). 1x in game, beats 0-5: p5 (upper pair) over p6 (lower pair); each pair Colour over DMG. Alien loop A B C B D B", fill=(255, 255, 0))
    for b in range(6):
        sh.paste(left(b, 1), (8 + b * 214, 20))
        sh.paste(right(b, 1), (8 + b * 214, 92))
    d.text((8, 166), "x4 p6 beat 0 (alien A) and beat 2 (alien C)", fill=(255, 255, 0))
    for i, b in enumerate((0, 2)):
        sh.paste(right(b, 4), (8 + i * 650, 180))
    d.text((8, 450), "x8 alien frames A B C D: Colour on the stage wall, DMG below", fill=(255, 255, 0))
    for i, fi in enumerate((4, 5, 6, 7)):
        a = Image.new("RGB", (16, 32), ns["hexrgb"](pj["stage_a"]["hex"][1]))
        g = Image.new("RGB", (16, 32), ns["DMG_BG"][2])
        put(a, p6[fi], 0, 0, True, pal())
        put(g, p6[fi], 0, 0, False, pal())
        sh.paste(a.resize((128, 256), Image.NEAREST), (8 + i * 140, 466))
        sh.paste(g.resize((128, 256), Image.NEAREST), (8 + i * 140, 730))
    sh.crop((0, 0, 1300, 1000)).save(out)

main()
