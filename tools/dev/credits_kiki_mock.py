#!/usr/bin/env python3
"""MOCK, no build change: Kiki's Color page as built (A: her lips in the BG's orange-brown, every room pixel as approved) against Kiki with the art branch's red lips (B), where the
room pixels the palette search has to change are changed. Reads the roll's capture (credits_pages_vs_approved.py --shots) and the approved card, asks tools/gen_scene_pages.py's
_plan_moves (room pixels allowed) which pixels a page with her accents would need changed, and writes one sheet: the x8 crop and the full card at x3 for A and B, and a third panel with the
changed room pixels in magenta; prints each pixel as old colour -> new colour.

    CRART=18 python3 tools/dev/credits_kiki_mock.py ROLL_SHOT.png APPROVED_CARD.png OUT.png [--pals N] [--objs N] [--kmax K]

--pals / --objs: the OBJ palettes / objects the page may use (the build allows 6 and 23); the plan is for those limits. Writes only OUT.png."""
import argparse
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tools" / "credits_scenes18"))
import gen_scene_pages as G      # noqa: E402
import scenes_final as FIN       # noqa: E402


def plan(key, pals, objs, kmax):
    v = [x for x in G.F.VENUES if x.key == key][0]
    with FIN.configured(key):
        cfg = dict(FIN.CONFIG[key])
        limits = {"line": 8, "objs": objs, "pals": pals}
        try:
            G._scene(v, True, limits, [])
            return 0, [], None
        except G.PackFail as e:
            res = G._plan_moves(e, kmax=kmax, rounds=25, room_ok=True)
    return (None, None, None) if res is None else (res[0], res[1], limits)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("roll")
    ap.add_argument("approved")
    ap.add_argument("out")
    ap.add_argument("--pals", type=int, default=6)
    ap.add_argument("--objs", type=int, default=23)
    ap.add_argument("--kmax", type=int, default=2)
    ap.add_argument("--key", default="zoo")
    a = ap.parse_args()
    # the page with its accents: scenes_final's zoo entry without them (the build) gets them here
    FIN.CONFIG[a.key] = dict(FIN.CONFIG[a.key], accents=True)
    total, extras, limits = plan(a.key, a.pals, a.objs, a.kmax)
    print(f"limits OBJ palettes {a.pals}, objects {a.objs}: pixels to change {total}", None if extras is None else {k: sum(1 for q in extras if q[5] == k) for k in ('own', 'room', 'ring')})
    A = np.asarray(Image.open(a.roll).convert("RGB")).astype(int)
    B = np.asarray(Image.open(a.approved).convert("RGB")).astype(int)
    rows = []
    mark = np.zeros((144, 160), bool)
    if extras:
        for ox, oy, old, new, nsh, kind in extras:
            if kind == "own":
                continue
            x, y = 24 + ox, 64 + oy
            if 0 <= y < 144 and 0 <= x < 160:
                h = lambda c: tuple(int(c[i:i + 2], 16) for i in (1, 3, 5))
                oldrgb, newrgb = h(old), h(new)
                rows.append((x, y, old, new, kind))
                B[y, x] = newrgb
                mark[y, x] = True
    for x, y, old, new, kind in sorted(rows, key=lambda r: (r[1], r[0])):
        print(f"  ({x},{y}) {kind}: {old} -> {new}")
    M = B.copy()
    M[mark] = (255, 0, 255)
    S8, S3 = 8, 3
    if rows:
        ys = [r[1] for r in rows]; xs = [r[0] for r in rows]
        y0, y1, x0, x1 = max(0, min(ys) - 4), min(144, max(ys) + 5), max(0, min(xs) - 4), min(160, max(xs) + 5)
    else:
        y0, y1, x0, x1 = 90, 112, 28, 76
    y0, y1, x0, x1 = min(y0, 92), max(y1, 108), min(x0, 30), max(x1, 74)
    cw, ch = (x1 - x0) * S8, (y1 - y0) * S8
    sheet = Image.new("RGB", (max(3 * cw + 16, 3 * 160 * S3 + 16), ch + 160 + 144 * S3 + 40), (40, 40, 40))
    dr = ImageDraw.Draw(sheet)
    labs = ("A: as built (lips #b05020)", "B: red lips, room pixels changed", "B: changed room pixels in magenta")
    for k, im in enumerate((A, B, M)):
        crop = Image.fromarray(im[y0:y1, x0:x1].astype(np.uint8)).resize((cw, ch), Image.NEAREST)
        sheet.paste(crop, (k * (cw + 8), 16))
        dr.text((k * (cw + 8) + 2, 2), f"{labs[k]}  x8  box x{x0}-{x1} y{y0}-{y1}", fill=(255, 255, 0))
        full = Image.fromarray(im.astype(np.uint8)).resize((160 * S3, 144 * S3), Image.NEAREST)
        sheet.paste(full, (k * (160 * S3 + 8), ch + 40))
        dr.text((k * (160 * S3 + 8) + 2, ch + 26), labs[k] + "  full card x3", fill=(255, 255, 0))
    sheet.save(a.out)
    print("sheet", sheet.size, a.out)


if __name__ == "__main__":
    main()
