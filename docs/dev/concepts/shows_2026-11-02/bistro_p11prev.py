#!/usr/bin/env python3
"""Preview only: bistro p10 (left) beside p11 (right, the singer in her own wine palette). Colour only (the DMG keeps today's band).
  bistro_p11prev.py gif OUT.gif   x3, 200 ms a beat
  bistro_p11prev.py sheet OUT.png the singer's 4 frames x6, p10 over p11, plus the 1x scene
"""
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
src = (HERE / "showprev.py").read_text().rsplit("\nmain()", 1)[0]
ns = {"__file__": str(HERE / "showprev.py")}
exec(compile(src, "showprev.py", "exec"), ns)
from PIL import Image, ImageDraw  # noqa: E402
T = "bistro"
LOOPS = ([0, 1, 2, 3], [4, 5, 6, 7], [8, 9, 10, 11, 10, 9])
BAND = [ns["hexrgb"](h) for h in ns["json"].loads((ns["VD"] / f"{T}_show_pal.json").read_text())["obj"]["hex"]]
WINE = [ns["hexrgb"]("#8a1c3a"), BAND[1], BAND[2]]


def scene(fr, beat, base, singer_pal):
    im = base.copy()
    for k, x0 in enumerate((24, 72, 120)):
        f = fr[LOOPS[k][beat % len(LOOPS[k])]]
        p = singer_pal if k == 1 else BAND
        for y, r in enumerate(f):
            for x, c in enumerate(r):
                v = ns["IDX"][c]
                if v:
                    im.putpixel((x0 + x, 8 + y), p[v - 1])
    return im


def main():
    a = ns["blocks"](str(HERE / "bistro_show_p10_cgb.txt"))
    b = ns["blocks"](str(HERE / "bistro_show_p11_cgb.txt"))
    base = ns["stage_img"](T, True)
    if sys.argv[1] == "gif":
        frames = []
        for beat in range(12):
            l, r = scene(a, beat, base, BAND), scene(b, beat, base, WINE)
            im = Image.new("RGB", (160 * 2 + 4, 32), (40, 40, 40))
            im.paste(l, (0, 0)); im.paste(r, (164, 0))
            im = im.resize((im.width * 3, im.height * 3), Image.NEAREST)
            frames.append(im.quantize(256, dither=Image.Dither.NONE))
        frames[0].save(sys.argv[2], save_all=True, append_images=frames[1:], duration=200, loop=0)
        return
    sh = Image.new("RGB", (4 * 110 + 10, 2 * 160 + 120), (40, 40, 40))
    bg = ns["hexrgb"](ns["json"].loads((ns["VD"] / f"{T}_pal.json").read_text())["stage_a"]["hex"][1]) if "stage_a" in ns["json"].loads((ns["VD"] / f"{T}_pal.json").read_text()) else (110, 180, 170)
    for row, (fr, p) in enumerate(((a, BAND), (b, WINE))):
        for i in range(4):
            t = Image.new("RGB", (16, 24), bg)
            for y, r in enumerate(fr[4 + i][:24]):
                for x, c in enumerate(r):
                    v = ns["IDX"][c]
                    if v: t.putpixel((x, y), p[v - 1])
            sh.paste(t.resize((96, 144), Image.NEAREST), (10 + i * 110, 10 + row * 160))
    sh.paste(scene(b, 0, base, WINE).resize((320, 64), Image.NEAREST), (10, 2 * 160 + 20))
    sh.save(sys.argv[2])


main()
