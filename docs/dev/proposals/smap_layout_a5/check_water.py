"""Scratch check: every adjacent water-water pair joins on its shared edge (dark and light sets), and floating logs sit only on flat water tiles.  python3 -I check_water.py"""
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
os.environ["SMAP_LAYOUT"] = "lay_A5"
os.environ["SMAP_FOG"] = "none"
sys.path.insert(0, str(HERE / "src"))
sys.path.append(str(HERE.parents[3] / "tools" / "smap_world"))
import a5art  # noqa: E402
import lay_A5 as L  # noqa: E402
import scen_A5 as S  # noqa: E402

bad = 0


def tile(c, light=False):
    return a5art.water_tile5(L.WATER, c[0], c[1], L.CW, L.CH, dmg=True, light=light, variants=True, special=L.SPECIAL_WATER)


for light in (False, True):
    T = {c: tile(c, light) for c in L.WATER}
    for (x, y), t in T.items():
        e = T.get((x + 1, y))
        if e and [r[-1] for r in t] != [r[0] for r in e]:
            print("join E fail", "light" if light else "dark", (x, y))
            bad += 1
        s = T.get((x, y + 1))
        if s and t[-1] != s[0]:
            print("join S fail", "light" if light else "dark", (x, y))
            bad += 1
flat = {id(a5art.DARK[n]) for n in ("WF", "WA", "WB")}
for pieces in ([[(x, y), (x + 1, y)] for x, y in S.LOGS_H], [[(x, y), (x, y + 1)] for x, y in S.LOGS_V]):
    for cells in pieces:
        for c in cells:
            if any((c[0] + dx, c[1] + dy) not in L.WATER for dx in (-1, 0, 1) for dy in (-1, 0, 1)) or id(tile(c)) not in flat:
                print("log not on flat water", cells)
                bad += 1
                break
print("water check:", "OK" if not bad else f"{bad} problems")
