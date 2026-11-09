"""Read-only: which palettes the 21 x 19 windows round the two cream road-bend wedges hold, from the frozen snapshot (assets/smap/world.json cell palettes).
    python3 -I pal_windows.py          # prints, per wedge, the windows that already hold 8 palettes and what is in them"""
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
J = json.loads((ROOT / "assets/smap/world.json").read_text())
NAMES = J["pal_names"]
CP = [[NAMES[ord(c) - 48] for c in row] for row in J["cell_pal"]]
CW, CH = J["cw"], J["ch"]
WIN_W, WIN_H = 21, 19


def windows_with(cells):
    """windows (x0, y0) of 21 x 19 cells that contain at least one of the cells"""
    out = []
    for y0 in range(CH - WIN_H + 1):
        for x0 in range(CW - WIN_W + 1):
            if any(x0 <= x < x0 + WIN_W and y0 <= y < y0 + WIN_H for (x, y) in cells):
                out.append((x0, y0))
    return out


def pals(x0, y0):
    c = Counter()
    for y in range(y0, y0 + WIN_H):
        for x in range(x0, x0 + WIN_W):
            c[CP[y][x]] += 1
    return c


if __name__ == "__main__":
    for name, box in (("west wedge", (35, 44, 37, 46)), ("east wedge", (50, 44, 52, 46))):
        cells = [(x, y) for y in range(box[1], box[3] + 1) for x in range(box[0], box[2] + 1)]
        print(name, "cells", box, [CP[y][x] for (x, y) in cells])
        ws = windows_with(cells)
        hist = Counter(len(pals(*w)) for w in ws)
        print("  windows touching it:", len(ws), "palettes per window:", dict(sorted(hist.items())))
        full = [w for w in ws if len(pals(*w)) >= 8]
        # the palettes that appear in every full window, with the smallest cell count over those windows
        common = Counter()
        for w in full:
            for p, n in pals(*w).items():
                common[p] += 1
        print("  full windows:", len(full))
        for p, n in common.most_common():
            mn = min(pals(*w)[p] for w in full if p in pals(*w))
            mx = max(pals(*w)[p] for w in full if p in pals(*w))
            print(f"    {p:10s} in {n:3d} full windows, {mn}..{mx} cells")
