"""Loads the A5 world (scratch copy in ../smap_layout_a5/src; run its mk_src.py and mk_a5.py first) and gives its index grids and a dump helper.
Read-only: nothing is written except the pictures the caller saves."""
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
os.environ["SMAP_LAYOUT"] = "lay_A5"
os.environ["SMAP_FOG"] = "none"
sys.path.insert(0, str(ROOT / "docs/dev/proposals/smap_layout_a5/src"))
sys.path.append(str(ROOT / "tools/smap_world"))
import pal as PAL  # noqa: E402
import world2 as W  # noqa: E402

CW, CH = W.CW, W.CH
wd, wc = W.WORLD_DMG, W.WORLD
DMG_SHADE = PAL.DMG_SHADE


def grid():
    """index grid (list of lists, PH x PW) and palette name per cell"""
    return [row[:] for row in wc.px], [row[:] for row in wc.pal]


def dump(px, x0, y0, x1, y1, ch=".-+#"):
    print("     " + "".join(str((x // 10) % 10) if x % 10 == 0 else " " for x in range(x0, x1 + 1)))
    print("     " + "".join(str(x % 10) for x in range(x0, x1 + 1)))
    for y in range(y0, y1 + 1):
        print(f"{y:4d} " + "".join(ch[px[y][x]] for x in range(x0, x1 + 1)))
