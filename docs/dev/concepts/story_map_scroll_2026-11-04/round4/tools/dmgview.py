"""DMG full vs DMG trimmed (round 4): the late world rebuilt through the merge table, and each vignette at x4, full | trimmed.
python3 dmgview.py MERGE.json OUTDIR"""
import json
import sys
from pathlib import Path

from PIL import Image

import pal
import render2 as R
import stats2 as S
import world2 as W

mp_raw = json.load(open(sys.argv[1]))
mp = {tuple(tuple(r) for r in a): tuple(tuple(r) for r in b) for a, b in mp_raw}
OUT = Path(sys.argv[2])
OUT.mkdir(parents=True, exist_ok=True)


def trimmed_image(w):
    sg = S.sig_grid(w)
    im = Image.new("RGB", (W.PW, W.PH))
    for cy in range(W.CH):
        for cx in range(W.CW):
            t = mp.get(sg[cy][cx], sg[cy][cx])
            for j in range(8):
                for i in range(8):
                    im.putpixel((cx * 8 + i, cy * 8 + j), (pal.DMG_SHADE[t[j][i]],) * 3)
    return im


if __name__ == "__main__":
    full = R.img("late", "dmg")
    trim = trimmed_image(W.WORLD)
    trim.save(OUT / "world_late_dmg_trim.png")
    for st, opened in (("early", R.EARLY_OPEN),):
        trimmed_image(W.with_fog(W.WORLD, opened)).save(OUT / "world_early_dmg_trim.png")
    for name, (x0, y0, x1, y1) in W.WORLD.venue_rect.items():
        box = (x0 * 8, y0 * 8, x1 * 8 + 8, y1 * 8 + 8)
        a, b = full.crop(box), trim.crop(box)
        o = Image.new("RGB", (a.width * 2 + 6, a.height), (40, 40, 40))
        o.paste(a, (0, 0))
        o.paste(b, (a.width + 6, 0))
        o.save(OUT / f"dmg_{name}.png")
        diff = sum(1 for p, q in zip(a.getdata(), b.getdata()) if p != q)
        print(f"{name:8s} {a.width}x{a.height}: {diff} of {a.width * a.height} pixels differ ({100 * diff / (a.width * a.height):.1f}%)")
