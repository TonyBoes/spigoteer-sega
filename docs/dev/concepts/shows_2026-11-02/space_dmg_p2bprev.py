#!/usr/bin/env python3
"""Preview only (transcribes the hand-drawn grids, decides no pixels; a flip is the hardware X-flip): space DMG p2b.

  space_dmg_p2bprev.py chk             frame sizes, 8x16 quarter count
  space_dmg_p2bprev.py gif OUT.gif     x3, 200 ms a beat, DMG: today's band (space_show_p5, left) beside the new (right); 32-row strip uncropped (HUD y 0-7)
  space_dmg_p2bprev.py sheet OUT.png   contact sheet: 1x, x4, frames x8, loop/flip options
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
src = (HERE / "showprev.py").read_text().rsplit("\nmain()", 1)[0]
ns = {"__file__": str(HERE / "showprev.py")}
exec(compile(src, "showprev.py", "exec"), ns)
from PIL import Image, ImageDraw  # noqa: E402

NEW = HERE / "space_show_dmg_p2b.txt"
OLD = HERE / "space_show_dmg_p1.txt"
LOOPS = [[0, 1, 2, 3], [1, 2, 3, 0], [2, 3, 0, 1]]
FLIPS = [1, 0, 0]
XS = (24, 72, 120)


def load(path):
    fr = ns["blocks"](path)
    for n, f in enumerate(fr):
        bad = [(y, r) for y, r in enumerate(f) if len(r) != 16 or not set(r) <= set(".-+#")]
        assert len(f) == 24 and not bad, f"{path}: frame {n}: {len(f)} rows; bad {bad}"
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


def scene_new(fr, beat, base, loops=LOOPS, flips=FLIPS):
    im = base.copy()
    for k, x0 in enumerate(XS):
        put(im, fr[loops[k][beat % len(loops[k])]], x0, 8, flips[k])
    return im


def scene_old(fr, beat, base):
    return scene_new(fr, beat, base)


def main():
    cmd = sys.argv[1]
    new, old = load(NEW), load(OLD)
    if cmd == "chk":
        print(len(new), "frames; quarters new:", quarters(new), "old p1:", quarters(old))
        return
    base = ns["stage_img"]("space", False)
    out = sys.argv[2]
    if cmd == "gif":
        S, frames = 3, []
        for beat in range(8):
            a, b = scene_old(old, beat, base), scene_new(new, beat, base)
            im = Image.new("RGB", (160 * S * 2 + 8, 32 * S + 14), (40, 40, 40))
            d = ImageDraw.Draw(im)
            d.text((2, 1), "DMG p1 (two poses)", fill=(235, 235, 235))
            d.text((160 * S + 10, 1), "DMG p2b: + strum pose C", fill=(235, 235, 235))
            im.paste(a.resize((160 * S, 32 * S), Image.NEAREST), (0, 14))
            im.paste(b.resize((160 * S, 32 * S), Image.NEAREST), (160 * S + 8, 14))
            frames.append(im.quantize(256, dither=Image.Dither.NONE))
        frames[0].save(out, save_all=True, append_images=frames[1:], duration=200, loop=0)
        return
    sh = Image.new("RGB", (1330, 1000), (40, 40, 40))
    d = ImageDraw.Draw(sh)
    y = 4
    d.text((8, y), "Space DMG p2bb, beats 0-5 at 1x (top: p1; bottom: p2, left flipped, loops 0123 / 1230 / 2301)", fill=(255, 255, 0))
    for b in range(6):
        sh.paste(scene_old(old, b, base), (8 + b * 216, 20))
        sh.paste(scene_new(new, b, base), (8 + b * 216, 56))
    y = 96
    d.text((8, y), "x4 new, beats 0 1 2 3 (head up / dip / up / dip + lean)", fill=(255, 255, 0))
    for i in range(4):
        sh.paste(scene_new(new, i, base).resize((640, 128), Image.NEAREST), (8 + (i % 2) * 650, y + 16 + (i // 2) * 134))
    y = 384
    d.text((8, y), "x4 flip options at beat 1 (top) and 3 (bottom): A none flipped | B left flipped (picked) | C both outer flipped", fill=(255, 255, 0))
    for i, fl in enumerate(([0, 0, 0], [1, 0, 0], [1, 0, 1])):
        im2 = Image.new("RGB", (160, 66), (40, 40, 40))
        im2.paste(scene_new(new, 1, base, LOOPS, fl), (0, 0))
        im2.paste(scene_new(new, 3, base, LOOPS, fl), (0, 34))
        sh.paste(im2.resize((320, 132), Image.NEAREST), (8 + i * 330, y + 16))
    y = 540
    d.text((8, y), "x8 top: p2b A (F0), B (F2), C (F1), C lean (F3); bottom: p1 F0 F2 F1 F3", fill=(255, 255, 0))
    for j, fs in enumerate(([new[k] for k in (0, 2, 1, 3)], [old[k] for k in (0, 2, 1, 3)])):
        for i, f in enumerate(fs):
            g = Image.new("RGB", (16, 24), ns["DMG_BG"][1])
            put(g, f, 0, 0, 0)
            sh.paste(g.resize((128, 192), Image.NEAREST), (8 + i * 148, y + 16 + j * 200))
    sh.save(out)


main()
