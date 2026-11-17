#!/usr/bin/env python3
"""MOCK, no build change: the Color credits with ONE black background, #080818, instead of the navy #181040 (and the stage colour that Bistro's and Factory's margins take).

    python3 tools/dev/credits_black_mock.py PAGES_DIR OUT_DIR

PAGES_DIR holds <venue>_roll.png captures (credits_pages_vs_approved.py --shots, Color: cgb_<venue>_roll.png). For every page: today | the mock | the mock with the art pixels whose colour
shifts marked (red). Navy, and the stage colour of the margins, become #080818 (as the screen shows it). On Bistro and Factory the margins would use the palette entry that holds the page's
darkest picture colour (#202030, #001810): that entry is set to #080818 exactly, so every art pixel of that colour shifts to #080818: those are the marked pixels. Writes only OUT_DIR."""
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "credits_scenes18"))
from scenes_lib import cc, hexrgb, q5      # noqa: E402

NAVY = tuple(cc(hexrgb(q5("#181040"))))
BLACK = tuple(cc(hexrgb(q5("#080818"))))
DARKEST = {"bistro": ("#202030", "#082830"), "factory": ("#001810", "#101818")}      # (the darkest picture colour, the stage colour the margins take today)
KEYS = ["saloon", "sports", "lodge", "bistro", "igloo", "factory", "biker", "teahouse", "zoo", "space"]


def main():
    src, out = Path(sys.argv[1]), Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    allm = []
    for k in KEYS:
        im = np.asarray(Image.open(src / f"cgb_{k}_roll.png").convert("RGB")).astype(int)
        mock = im.copy()
        marked = np.zeros(im.shape[:2], bool)
        navy = (im == np.array(NAVY)).all(axis=2)
        mock[navy] = BLACK
        if k in DARKEST:
            dk = tuple(cc(hexrgb(q5(DARKEST[k][0]))))
            st = tuple(cc(hexrgb(q5(DARKEST[k][1]))))
            ys, xs = np.mgrid[0:144, 0:160]
            outside = ~((xs >= 24) & (xs < 136) & (ys >= 64) & (ys < 136))
            margin = (im == np.array(st)).all(axis=2) & outside & ~((ys >= 8) & (ys < 32))
            mock[margin] = BLACK
            art = (im == np.array(dk)).all(axis=2)
            mock[art] = BLACK
            marked = art
        diffimg = mock.copy()
        diffimg[marked] = (255, 0, 0)
        S = 3
        sheet = Image.new("RGB", (160 * S * 3 + 24, 144 * S + 16), (40, 40, 40))
        d = ImageDraw.Draw(sheet)
        for i, (lab, a) in enumerate((("today", im), ("mock: one black #080818", mock), (f"art pixels that shift: {int(marked.sum())} (red)", diffimg))):
            sheet.paste(Image.fromarray(a.astype(np.uint8)).resize((160 * S, 144 * S), Image.NEAREST), (i * (160 * S + 8), 16))
            d.text((i * (160 * S + 8) + 2, 2), f"{k}: {lab}", fill=(235, 235, 235))
        sheet.save(out / f"mock_{k}.png")
        allm.append((k, mock))
    S = 2
    ov = Image.new("RGB", (5 * (160 * S + 6), 2 * (144 * S + 16)), (40, 40, 40))
    d = ImageDraw.Draw(ov)
    for i, (k, a) in enumerate(allm):
        x, y = (i % 5) * (160 * S + 6), (i // 5) * (144 * S + 16)
        ov.paste(Image.fromarray(a.astype(np.uint8)).resize((160 * S, 144 * S), Image.NEAREST), (x, y + 14))
        d.text((x + 2, y + 1), k, fill=(235, 235, 235))
    ov.save(out / "mock_all.png")
    print("black", BLACK, "navy", NAVY)


if __name__ == "__main__":
    main()
