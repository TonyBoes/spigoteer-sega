#!/usr/bin/env python3
"""Full-screen Pour-Off mockups of a proposal in the real engine's layout (src/po.c), built from the real art files:
the four bars, Sal and Dregs, the crowd of six looks, a few mugs, and the HUD / banner rows from the real goldens.

    python3 mock.py A            # -> A/mock_{dmg,cgb}_x3.png, A/mock_intro_{dmg,cgb}_x3.png (+ 1x versions in A/)
It only places already-drawn art (no pixel decided here). The saloon can be mocked with:  python3 mock.py saloon
"""
import json
import sys
from pathlib import Path

from PIL import Image

import render

ROOT = render.ROOT
HERE = Path(__file__).resolve().parent
PAT = ROOT / "assets/art/patrons"
PAL = json.loads((ROOT / "assets/palettes.json").read_text())


def hexes(name):
    return PAL[name]["hex"]


def first(path, w=16, h=16):
    return render.parse_frames(path, w, h)[0]


def looks():
    """name -> (rows, hex3, source)"""
    redo = ROOT / "docs/dev/concepts/new_patrons/v2/redo.txt"
    return {
        "CLOWN": (first(redo), ["#f8c8a0", "#e04040", "#2838a0"]),            # BIGWIG v2 (Color-only concept), its @fig palette
        "DUSTY": (first(PAT / "cowboys.txt"), hexes("cowboys_a")),
        "PETE": (first(PAT / "sports.txt"), hexes("sports_a")),
        "CEDAR": (first(PAT / "lumberjacks.txt"), hexes("lumberjacks_a")),
        "PIERRE": (first(PAT / "chefs.txt"), hexes("chefs_a")),
        "ZORP": (first(PAT / "aliens.txt"), hexes("aliens_a")),
    }


# (bar, seat k, look): at most 2 a bar in play; each of the six looks shows
LINEUP = [(0, 0, "CLOWN"), (0, 2, "DUSTY"),
          (1, 1, "PETE"), (1, 2, "PIERRE"),
          (2, 0, "CEDAR"), (2, 2, "ZORP"),
          (3, 0, "ZORP"), (3, 1, "CLOWN")]


def mock(venue_prefix, mode, intro=False, lineup=LINEUP):
    v = render.load_venue(venue_prefix)
    L = looks()
    crowd = [(b, k, L[n][0], L[n][1]) for (b, k, n) in lineup]
    sal = render.parse_frames(ROOT / "assets/art/bartender.txt", 16, 24)[0]
    dregs = render.parse_frames(ROOT / "assets/art/dregs/dregs.txt", 16, 24)[0]
    mug = render.parse_frames(ROOT / "assets/art/mug.txt", 8, 16)[0]
    sprites = [
        (120, 40 + 24 * 1 + 2, sal, hexes("bartender"), False, [0, 255, 153, 0]),
        (24, 40 + 24 * 2 + 2, dregs, ["#f0d8a0", "#b0a0b8", "#201828"], True, [0, 153, 85, 0]),
        (88, 40 + 24 * 1 + 4, mug, hexes("mug_full"), False, [0, 255, 153, 0]),       # a full drink sliding to the left
        (56, 40 + 24 * 3 + 4, mug, hexes("mug_full"), False, [0, 255, 153, 0]),
    ]
    g = ROOT / "tests/golden"
    hud = Image.open(g / f"po_perfect.{mode}.png").convert("RGB")
    ig = Image.open(g / f"po_intro.{mode}.png").convert("RGB")
    return render.build(v, mode, ROOT, crowd=crowd, sprites=sprites, intro=intro, hud_from=hud, intro_from=ig)


if __name__ == "__main__":
    d = sys.argv[1]
    prefix = ROOT / "assets/approved/venues/saloon" if d == "saloon" else HERE / d
    outd = HERE / d if d != "saloon" else Path(sys.argv[2])
    for m in ("dmg", "cgb"):
        for intro in (False, True):
            im = mock(prefix, m, intro)
            tag = ("intro_" if intro else "") + m
            im.save(outd / f"mock_{tag}_x1.png")
            render.scale(im, 3).save(outd / f"mock_{tag}_x3.png")
