#!/usr/bin/env python3
"""Preview only (transcribes the hand-drawn grids, decides no pixels): bistro p5 (2 poses) beside p6 (4 poses a player).

  bistro_p6prev.py gif OUT.gif      x3, 200 ms a beat, p5 left, p6 right, Colour over DMG, the stage strip uncropped
  bistro_p6prev.py still OUT.png    the same scene at 1x, beats 0-3 of p6 side by side (Colour over DMG)

Loops (frame index within a performer's four poses A B C D): accordion A B C D, fiddler A B C D C B, singer A B C D.
Uses showprev.py's stage and palette code (its main() is not run).
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
src = (HERE / "showprev.py").read_text().rsplit("\nmain()", 1)[0]
ns = {"__file__": str(HERE / "showprev.py")}
exec(compile(src, "showprev.py", "exec"), ns)
from PIL import Image, ImageDraw  # noqa: E402

T = "bistro"
LOOPS = ([0, 1, 2, 3], [0, 1, 2, 3, 2, 1], [0, 1, 2, 3])


def scene6(frames, beat, cgb, base):
    im = base.copy()
    pal = [ns["hexrgb"](h) for h in ns["json"].loads((ns["VD"] / f"{T}_show_pal.json").read_text())["obj"]["hex"]]
    for k, x0 in enumerate((24, 72, 120)):
        loop = LOOPS[k]
        f = frames[4 * k + loop[beat % len(loop)]]
        for y, r in enumerate(f):
            for x, c in enumerate(r):
                v = ns["IDX"][c]
                if v:
                    im.putpixel((x0 + x, 8 + y), pal[v - 1] if cgb else ns["DMG_OBJ"][v])
    return im


def stack6(frames, beat, bases, scale):
    a, b = scene6(frames, beat, True, bases[0]), scene6(frames, beat, False, bases[1])
    im = Image.new("RGB", (160, 66), (40, 40, 40))
    im.paste(a, (0, 0))
    im.paste(b, (0, 34))
    return im.resize((160 * scale, 66 * scale), Image.NEAREST)


def main():
    cmd, out = sys.argv[1], sys.argv[2]
    bases = (ns["stage_img"](T, True), ns["stage_img"](T, False))
    p5 = ns["check"](str(HERE / "bistro_show_p5.txt"))
    p6 = ns["check"](str(HERE / "bistro_show_p6_cgb.txt"))
    if cmd == "still":
        ims = [stack6(p6, b, bases, 1) for b in range(4)]
        sheet = Image.new("RGB", (160 * 4 + 12, 66), (40, 40, 40))
        for i, im in enumerate(ims):
            sheet.paste(im, (i * 164, 0))
        sheet.save(out)
        return
    S = 3
    frames = []
    for beat in range(24):
        left = ns["stack"](T, p5, beat, bases) if False else None
        a, b = ns["scene"](T, p5, beat, True, bases[0]), ns["scene"](T, p5, beat, False, bases[1])
        l5 = Image.new("RGB", (160, 66), (40, 40, 40))
        l5.paste(a, (0, 0))
        l5.paste(b, (0, 34))
        l5 = l5.resize((160 * S, 66 * S), Image.NEAREST)
        r6 = stack6(p6, beat, bases, S)
        im = Image.new("RGB", (l5.width * 2 + 8, l5.height + 14), (40, 40, 40))
        d = ImageDraw.Draw(im)
        d.text((2, 1), "p5 today: 2 poses a player", fill=(235, 235, 235))
        d.text((l5.width + 10, 1), "p6 Color: 4 poses (fiddler loops A B C D C B)", fill=(235, 235, 235))
        im.paste(l5, (0, 14))
        im.paste(r6, (l5.width + 8, 14))
        frames.append(im.quantize(256, dither=Image.Dither.NONE))
    frames[0].save(out, save_all=True, append_images=frames[1:], duration=200, loop=0)


main()
