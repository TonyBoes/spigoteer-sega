#!/usr/bin/env python3
"""headcheck.py FILE.txt [cur]: read-only. The lint's L-double and orphan tests (gb_art_lint.py logic, on the text grid),
reported per pose for the head only (rows 0-9, cols 0-23), so the face pass can be checked pixel by pixel."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import crit_tool as c  # noqa: E402

poses = c.load(sys.argv[1])
for n in ["WALK", "GULP", "WINCE", "HAPPY", "TASTE", "HOLD"]:
    g = poses[n]
    h, w = 16, 32
    D = lambda y, x: 0 <= y < h and 0 <= x < w and g[y][x] == "#"
    ls, orph = [], []
    for y in range(10):
        for x in range(24):
            if D(y, x):
                for dy in (-1, 1):
                    for dx in (-1, 1):
                        if D(y, x + dx) and D(y + dy, x) and not D(y + dy, x + dx):
                            if not D(y, x + 2 * dx) and not D(y + 2 * dy, x):
                                ls.append((x, y))
            if 1 <= y < h - 1 and 1 <= x < w - 1:
                ch = g[y][x]
                same = sum(1 for yy in (y - 1, y, y + 1) for xx in (x - 1, x, x + 1) if g[yy][xx] == ch)
                if same == 1:
                    orph.append((x, y, ch))
    print(f"{n:6s} L-doubles {sorted(set(ls))}  orphans {orph}")
