"""The town at map scale, 160 x 104: the approved round 6 picture with the roof (pictures_roof/finale_a.txt, the day colours) read in as it is,
with these changes by hand, all typed below:
  - the sky behind the houses becomes the plaza's cream (the map has no sky),
  - Sal and Dregs are taken out: the rectangles they stood in are given back the wall, and the bottom 15 rows (the crowd of silhouettes)
    are retyped as the plaza's cobbles, which are a pattern of period 8,
  - each 8 x 8 cell gets one of five town palettes (the picture already keeps every cell to four colours).
Everything else (buildings, bunting, clock tower, tavern front, banner, fountain and the Golden Spigot) is the approved art, pixel for pixel.
Palettes: TOWN1 cream/terracotta/lilac/ink, TOWN2 cream/water/gold/ink, TOWN3 cream/terracotta/orange/ink, TOWN4 cream/water/lilac/ink,
TOWN5 cream/terracotta/gold/ink."""
import sys
from pathlib import Path

from canvas import Canvas
from art import R

ROOT = Path(__file__).resolve().parents[6]
SRC = ROOT / "docs/dev/concepts/town_2026-11-04/round6/pictures_roof/finale_a.txt"
SRC_INTRO = ROOT / "docs/dev/concepts/town_2026-11-04/round6/pictures_roof/intro_before.txt"
W, H = 160, 104
PAL = "town1"

# which index each character of the approved picture takes in the map, and what it means (the picture's own key says what each is)
IDX = {c: "0" for c in ".OoALQWYceghm"}
IDX.update({c: "1" for c in "RSXpb"})
IDX.update({c: "2" for c in "BHUiqryPa"})
IDX.update({c: "3" for c in "#du"})
KIND1 = {c: "T" for c in "RSXp"}
KIND1["b"] = "water"
KIND2 = {c: "lilac" for c in "BHUiqr"}
KIND2.update({"P": "orange", "a": "orange", "y": "gold"})
PALNAME = {("T", "lilac"): "town1", ("water", "gold"): "town2", ("T", "orange"): "town3", ("water", "lilac"): "town4", ("T", "gold"): "town5"}


def load(path=None):
    rows, sec = [], None
    for ln in (path or SRC).read_text().split("\n"):
        if ln.startswith("@pixels"):
            sec = "pix"
        elif sec == "pix":
            if not ln.strip():
                break
            rows.append(list(ln))
    assert len(rows) == H and len(rows[0]) == W
    return rows


def cobbles():
    """the plaza's cobbles from y 89, typed as the picture has them: periodic, 8 wide, mortar rows at y 94 and 100"""
    spec = {89: "(p:3 q:1 h:3 p:1)*20", 90: "(p:3 q:1 p:4)*20", 91: "(p:3 q:1 p:4)*20", 92: "(p:3 q:1 p:4)*20", 93: "(p:3 q:1 p:4)*20", 94: "q:160",
            95: "(p:4 h:3 q:1)*20", 96: "(p:7 q:1)*20", 97: "(p:7 q:1)*20", 98: "(p:7 q:1)*20", 99: "(p:7 q:1)*20", 100: "q:160",
            101: "(p:3 q:1 h:3 p:1)*20", 102: "(p:3 q:1 p:4)*20", 103: "(p:3 q:1 p:4)*20"}
    out = {}
    for y, s in spec.items():
        out[y] = list(R(s, W))
    return out


def build():
    g = load()
    # Sal and Dregs out: the right house's wall where Dregs stood, the basin and the hall where Sal stood
    for y in range(66, 88):
        for x in range(138, 159):
            if g[y][x] != "B":
                g[y][x] = "B"
    # Sal: the rectangle he stood in (x 120 to 137, y 66 to 87) is read from the approved intro picture of the same square, where it is empty
    intro = load(SRC_INTRO)
    for y in range(66, 88):
        for x in range(120, 138):
            g[y][x] = intro[y][x]
    for y, row in cobbles().items():
        g[y] = row
    c = Canvas("town", PAL, W, H)
    cp = [[PAL] * (W // 8) for _ in range(H // 8)]
    for cy in range(H // 8):
        for cx in range(W // 8):
            k1, k2 = set(), set()
            for y in range(cy * 8, cy * 8 + 8):
                for x in range(cx * 8, cx * 8 + 8):
                    ch = g[y][x]
                    c.px[y][x] = IDX[ch]
                    if ch in KIND1:
                        k1.add(KIND1[ch])
                    if ch in KIND2:
                        k2.add(KIND2[ch])
            assert len(k1) <= 1 and len(k2) <= 1, (cx, cy, k1, k2)
            a = next(iter(k1)) if k1 else "T"
            b = next(iter(k2)) if k2 else "lilac"
            if not k1 and k2 == {"orange"}:
                a = "T"
            cp[cy][cx] = PALNAME[(a, b)]
    c.cellpal_grid = cp
    return c


def cellpals_of(c):
    return c.cellpal_grid


if __name__ == "__main__":
    c = build()
    from collections import Counter
    print(Counter(p for r in c.cellpal_grid for p in r))
