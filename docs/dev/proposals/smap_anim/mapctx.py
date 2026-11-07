"""Loads the A5 world (scratch copy in ../smap_layout_a5/src; run its mk_src.py and mk_a5.py first) with the APPROVED art wired in, and gives its index grid.
  - SMAP_LOG=v1: the brown single logs (water palette index 3 = lodge brown, the falls' rock edge too).
  - town venue = smap_fountain/src/v_town_fx.py (round 3: centred, two spill streams, working state).
  - the cow venue is a stub, the hay field is gone (as smap_milkbar's a5env does), and the stadium, igloo, space mountain and milk bar pictures are pasted from scenes/*.json
    (r4dump.py): stadium (1,1) all cells, igloo (50,5) non-blank, mountain (9,36) all cells, milk bar + pasture (50,47) non-blank.
Read-only: nothing is written except the pictures the caller saves."""
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
os.environ["SMAP_LAYOUT"] = "lay_A5"
os.environ["SMAP_FOG"] = "none"
os.environ["SMAP_LOG"] = "v1"
os.environ.pop("SMAP_BROKEN", None)
sys.path.insert(0, str(ROOT / "docs/dev/proposals/smap_layout_a5/src"))
sys.path.append(str(ROOT / "tools/smap_world"))
sys.path.append(str(HERE))
sys.path.append(str(ROOT / "docs/dev/proposals/smap_fountain/src"))
import decor  # noqa: E402
import lay_A5 as lay  # noqa: E402

lay.FIELDS = []
lay.SCENERY = [s for s in lay.SCENERY if s[0] is not decor.HAY]
V = dict(lay.VENUES)
for k in ("cow", "stadium", "igloo", "space"):
    V[k] = ("anim_stub", V[k][1])
V["town"] = ("v_town_fx", V["town"][1])
lay.VENUES = V

import pal as PAL  # noqa: E402
import world2 as W  # noqa: E402

CW, CH = W.CW, W.CH
wc = W.WORLD
DMG_SHADE = PAL.DMG_SHADE
SCENES = {}
AT_OVERRIDE = {"mountain": (6, 36)}     # the airbase 3 cells west of r4dump's default: its two palettes (base, saloon) stay out of the windows that hold the tea garden and cow field


def paste(name):
    s = json.load(open(HERE / "scenes" / f"{name}.json"))
    SCENES[name] = s
    for n, col in s["colors"].items():                 # a palette the A5 map lacks (the stadium's PARK) comes from the piece's own table
        PAL.RGB.setdefault(n, [tuple(c) for c in col])
    ax, ay = AT_OVERRIDE.get(name, s["at"])
    for key, (rows, p) in s["frames"][0].items():
        i, j = map(int, key.split(","))
        if s["mode"] == "nonblank" and all(set(r) == {"0"} for r in rows):
            continue
        cx, cy = ax + i, ay + j
        for y in range(8):
            for x in range(8):
                wc.px[cy * 8 + y][cx * 8 + x] = int(rows[y][x])
        wc.pal[cy][cx] = p
    return s


for _n in ("stadium", "igloo", "mountain", "cow"):
    paste(_n)


def grid():
    """index grid (list of lists, PH x PW) and palette name per cell"""
    return [row[:] for row in wc.px], [row[:] for row in wc.pal]


def dump(px, x0, y0, x1, y1, ch=".-+#"):
    print("     " + "".join(str((x // 10) % 10) if x % 10 == 0 else " " for x in range(x0, x1 + 1)))
    print("     " + "".join(str(x % 10) for x in range(x0, x1 + 1)))
    for y in range(y0, y1 + 1):
        print(f"{y:4d} " + "".join(ch[px[y][x]] for x in range(x0, x1 + 1)))
