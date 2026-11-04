"""Compose the 256 x 256 story map from hand-drawn grids (kit.py) and cut-out cells of the approved v14 map.

Placement only: where each stamp, tree, road and fog cell goes is decided here by hand; nothing here draws a pixel.
"""
from pathlib import Path

from PIL import Image

import kit

ROOT = Path(__file__).resolve().parents[5]
OLD = Image.open(ROOT / "assets" / "story_map" / "map_bg_only_indexed.png")
SPR = ROOT / "assets" / "story_map"

N = 32                                      # cells per side: 256 px, the hardware BG map
DMG_SHADE = [248, 168, 88, 24]              # as tools/gen_smap.py previews

# BG palettes: the v14 set, with 4 (teal) replaced by the round-6 town palette and 5's cream matched to it
_old_pal = OLD.getpalette()
PAL = [[tuple(_old_pal[(p * 4 + i) * 3:(p * 4 + i) * 3 + 3]) for i in range(4)] for p in range(8)]
PAL[4] = [(248, 240, 176), (240, 184, 136), (160, 144, 176), (32, 24, 40)]
PAL[5][0] = (248, 240, 176)


def old(x, y):
    """cell (x, y) of the v14 picture -> (palette, 64 colour indices)"""
    px = [OLD.getpixel((x * 8 + i, y * 8 + j)) for j in range(8) for i in range(8)]
    pals = {v // 4 for v in px}
    assert len(pals) == 1, (x, y, pals)
    return (pals.pop(), tuple(v % 4 for v in px))


def cell_from_rows(pal, rows):
    return (pal, tuple(int(c) if c != "." else 0 for r in rows for c in r))


def rot(cell):
    """a quarter turn clockwise of one of my own tiles"""
    pal, t = cell
    return (pal, tuple(t[(7 - c) * 8 + r] for r in range(8) for c in range(8)))


class World:
    def __init__(self):
        self.c = [[None] * N for _ in range(N)]

    def put(self, x, y, cell):
        if 0 <= x < N and 0 <= y < N:
            self.c[y][x] = cell

    def fill(self, x0, y0, x1, y1, cell):
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                self.put(x, y, cell)

    def old(self, sx, sy, w, h, dx, dy):
        for j in range(h):
            for i in range(w):
                self.put(dx + i, dy + j, old(sx + i, sy + j))

    def img(self, dx, dy, pal, rows):
        h, w = len(rows), len(rows[0])
        assert w % 8 == 0 and h % 8 == 0
        for j in range(h // 8):
            for i in range(w // 8):
                self.put(dx + i, dy + j, cell_from_rows(pal, [r[i * 8:i * 8 + 8] for r in rows[j * 8:j * 8 + 8]]))

    def pic(self):
        im = Image.new("P", (N * 8, N * 8))
        flat = []
        for p in PAL:
            for c in p:
                flat += list(c)
        im.putpalette(flat)
        for y in range(N):
            for x in range(N):
                pal, t = self.c[y][x]
                for j in range(8):
                    for i in range(8):
                        im.putpixel((x * 8 + i, y * 8 + j), pal * 4 + t[j * 8 + i])
        return im


# plain ground cells of the v14 picture
GRASS = old(7, 0)
SAND = old(2, 8)
SNOW = old(17, 0)
CREAM = old(12, 0)

# ----------------------------------------------------------------------------------------------------------------
# where things are (cell coordinates; the map is 32 x 32 cells)
# ----------------------------------------------------------------------------------------------------------------
TOWN = (9, 12, 22, 20)                       # cobbled square, x0 y0 x1 y1
STOPS = {                                    # the cell Sal stands on
    "town": (16, 20), "saloon": (6, 20), "stadium": (6, 9), "lodge": (14, 6), "bistro": (24, 6), "igloo": (27, 6),
    "factory": (24, 10), "cow": (24, 20), "teahouse": (20, 28), "zoo": (11, 28), "lounge": (7, 28)}
ORDER = ["saloon", "stadium", "lodge", "bistro", "igloo", "factory", "cow", "teahouse", "zoo", "lounge"]   # chapters 1-10

# road cells (hand-chosen runs); the tile for each cell follows from which neighbours are roads
ROADS = set()


def run(x0, y0, x1, y1):
    for y in range(min(y0, y1), max(y0, y1) + 1):
        for x in range(min(x0, x1), max(x0, x1) + 1):
            ROADS.add((x, y))


run(6, 20, 8, 20)        # town west mouth to the saloon
run(6, 9, 6, 20)         # the saloon's lane north to the stadium
run(6, 9, 14, 9)         # the stadium east
run(14, 6, 14, 9)        # up to the lodge
run(14, 6, 27, 6)        # the long north road: lodge, bistro, igloo
run(24, 6, 24, 28)       # down the east side: factory, the Chrome Cow, the teahouse
run(23, 20, 24, 20)      # town east mouth
run(7, 28, 24, 28)       # the south road: teahouse, zoo, space lounge

ROAD_NAME = {  # (N, E, S, W) open sides -> tile
    (0, 1, 0, 1): "H", (1, 0, 1, 0): "V", (0, 1, 1, 0): "SE", (0, 0, 1, 1): "SW", (1, 1, 0, 0): "NE", (1, 0, 0, 1): "NW",
    (0, 1, 1, 1): "TS", (1, 1, 0, 1): "TN", (1, 1, 1, 0): "TE", (1, 0, 1, 1): "TW", (1, 1, 1, 1): "X"}


def road_cell(x, y):
    k = tuple(int(p in ROADS) for p in ((x, y - 1), (x + 1, y), (x, y + 1), (x - 1, y)))
    if k in ROAD_NAME:
        return cell_from_rows(1, kit.ROAD[ROAD_NAME[k]])
    # dead ends: the road simply stops, drawn as the straight piece (its edges close the open end)
    if k[1] or k[3]:
        return cell_from_rows(1, kit.ROAD["H"])
    return cell_from_rows(1, kit.ROAD["V"])


