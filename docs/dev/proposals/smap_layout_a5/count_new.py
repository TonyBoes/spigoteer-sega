"""Counts what A4 adds, read only.  python3 -I count_new.py
1. DMG tiles that exist only because of the new land pieces (water, banks, bridges, floating logs, log piles).
2. For the placeholders: the most unique tiles each group of them may spend so that no 21 x 19 window passes 176 (the window's other tiles counted as the map has them)."""
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
os.environ["SMAP_LAYOUT"] = "lay_A4"
os.environ["SMAP_FOG"] = "none"
sys.path.insert(0, str(HERE / "src"))
sys.path.append(str(ROOT / "tools" / "smap_world"))
import world2 as W  # noqa: E402
import a4art  # noqa: E402

w = W.WORLD_DMG
lay = W.lay
CW, CH = W.CW, W.CH


def sig(x, y):
    return bytes(w.px[y * 8 + j][x * 8 + i] for j in range(8) for i in range(8))


new_cells = set(lay.WATER) | set(lay.BRIDGE_CELLS)
for (px, py) in lay.PILES:
    new_cells |= {(px + i, py + j) for i in range(3) for j in range(2)}
other = {sig(x, y) for y in range(CH) for x in range(CW) if (x, y) not in new_cells}
mine = {sig(x, y) for (x, y) in new_cells}
only = mine - other
print("tiles only in the new pieces:", len(only), "of", len(mine), "used by those cells")
# by kind
water = {sig(x, y) for (x, y) in lay.WATER if (x, y) not in lay.BRIDGE_CELLS}
print("  water + banks + logs on water:", len(water - other))
print("  bridge tiles:", len({sig(x, y) for (x, y) in lay.BRIDGE_CELLS}))
print("  pile tiles:", len({sig(px + i, py + j) for (px, py) in lay.PILES for i in range(3) for j in range(2)} - other))
print("  typed art: 3 water + 12 banks and corners + 4 bridge + floating logs 2 (across) + 2 (down) + log pile 6 =", 3 + 12 + 4 + 4 + 6)

GROUPS = {"space lounge + mountain": [(10, 33, 22, 12)], "baseball park": [(1, 1, 16, 10)],
          "ranges A, B, C": [(17, 0, 15, 4), (34, 0, 14, 5), (48, 0, 16, 5)]}
ph = set()
cells_of = {}
for g, boxes in GROUPS.items():
    cs = {(x + i, y + j) for (x, y, bw, bh) in boxes for i in range(bw) for j in range(bh)}
    cells_of[g] = cs
    ph |= cs
for g, cs in cells_of.items():
    rows = []
    for y0 in range(CH - 18):
        for x0 in range(CW - 20):
            win = {(x, y) for y in range(y0, y0 + 19) for x in range(x0, x0 + 21)}
            cov = len(win & cs)
            if not cov:
                continue
            rest = {sig(x, y) for (x, y) in win - ph}
            others = {sig(x, y) for (x, y) in (win & ph) - cs}
            rows.append((cov, 176 - len(rest | others), (x0, y0)))
    top = max(rows)                                                   # the window that shows most of the group
    tight = min(r for r in rows if r[0] >= 0.6 * top[0])             # the tightest window that shows at least 60 percent as much
    print(f"{g}: {len(cs)} cells; the window showing most of it {top[2]} shows {top[0]} cells and leaves {top[1]} tiles for the group; "
          f"tightest of the wide views {tight[2]} ({tight[0]} cells) leaves {tight[1]}")
