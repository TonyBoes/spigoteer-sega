"""The falls come out of mountain B (owner Q117: "I like b more, but waterfall should be coming out of mountain"), proposal only.

Mountain B is placed 16 px further east (big_mountain.PLACES["B"]) so its right flank stands over the head of the falls.  Under the flank a rock LEDGE steps down to the falls' top row (map row 5,
y 40..47, x 360..391), and a dark CAVE MOUTH is cut into its face over the channel (x 371..380); the water comes out of the dark at the foot of the mouth (y 44..47) and drops into the existing
falls tiles of row 6 and the pool, which are untouched.  Nothing is drawn above the mountain: no river is visible above it.
  - The ledge and mouth are typed below, row by row (LEDGE).  Same look as the mountain: lit left (1), shaded right (2), ink outline (3), snow 0; lit/shade ridge zig-zagging; the outline steps 1
    to 3 px, the flank flares to the right like the mountain's own foot (no straight vertical edge).
  - The two falls cells of row 5, (46,5) and (47,5), take the `igloo` palette together with the ledge cells (45..49, 5), so the flow pixels there are the DMG light map (foam 0, water 1: on Color
    the igloo pale blue 104 168 216 against the water palette's 88 160 216, and snow white against the pool's cream foam).  Row 6 and the pool stay on the `water` palette, approved art.
  - FLOW: the approved falls streaks (FALL_COLS, FALL_STEP, FALL_FRAMES: copied unchanged from smap_anim/items.py) show through the mouth on its bottom 4 rows, the first of them in shadow
    (foam 1, water 2).  The 4 animation frames of each of the two row-5 cells therefore carry the mountain pixels (the ledge and mouth are the same in every frame, only the flow changes).
  Animation cost: the two cells keep their 4 images each (frame 0 is the map tile): the same 6 images as the approved FL_A and FR_A, now with rock in them; no extra cells, so the VBlank peak
  per view is unchanged (igloo view 6 tiles, 96 B)."""

FALL_COLS = ["++-+++-+++-+", "-------++--+", "++---+++---+", "----++-----+", "--+++----++-", "+++---++---+", "-----+++---+", "+++-++-+++-+"]       # approved (smap_anim/items.py)
FALL_STEP, FALL_FRAMES = 3, 4
X0, Y0 = 360, 40                                         # top left of the typed LEDGE block (40 x 8 px)
FLOW_X0, FLOW_Y0 = 372, 44                               # the flow window: x 372..379, y 44..47
# '.' keeps the map's own pixel, 'f' is the flow window, digits are igloo-palette pixels (0 snow, 1 pale rock, 2 deep, 3 ink)
LEDGE = [
    "3" + "1" * 10 + "3" * 10 + "1" * 2 + "2" * 3 + "3" + "." * 13,                                # y 40, x 360..: lit face, the mouth (10 wide, x 371..380), a shaded strip on the right
    ".3" + "1" * 9 + "3" * 10 + "1" * 3 + "2" * 3 + "3" + "." * 12,                                # y 41
    ".3" + "1" * 9 + "3" * 10 + "1" * 4 + "2" * 2 + "3" + "." * 12,                                # y 42
    "..3" + "1" * 8 + "3" + "33233323" + "3" + "1" * 5 + "2" * 2 + "3" + "." * 11,                # y 43: the dark of the mouth, two deep flecks
    "...3" + "1" * 7 + "3" + "f" * 8 + "3" + "1" * 5 + "2" * 3 + "3" + "." * 10,                  # y 44: walls, the flow window opens
    "...3" + "1" * 7 + "3" + "f" * 8 + "3" + "1" * 5 + "2" * 3 + "3" + "." * 10,                  # y 45
    "....3" + "1" * 6 + "3" + "f" * 8 + "3" + "1" * 5 + "2" * 4 + "3" + "." * 9,                  # y 46
    "....." + "3" * 7 + "f" * 8 + "3" * 12 + "." * 8,                                             # y 47: foot line, open where the water leaves
]
for _r in LEDGE:
    assert len(_r) == 40, (len(_r), _r)
ARCH = {36: (373, "333333"), 37: (372, "33233323"), 38: (371, "3333333333"), 39: (371, "3332333233")}      # y: (x start, pixels): the mouth widens 6, 8, 10, 10 px going down into the ledge rows
STRATA = [(0, 4, 7), (0, 15, 19), (1, 4, 8), (1, 20, 22), (4, 6, 9), (4, 22, 24), (6, 8, 9), (6, 22, 25)]       # (y - 40, i0, i1): dashes on the lit face, '1' -> '2'
CREASE = [(0, 23, 24), (4, 26, 27), (5, 27, 28), (6, 27, 28)]                                                    # dark marks on the shaded face, '2' -> '3'
CELLS = [(45, 5), (46, 5), (47, 5), (48, 5), (49, 5)]                           # take the igloo palette


def ledge_rows():
    g = [list(r) for r in LEDGE]
    for (j, a, b) in STRATA:
        for i in range(a, b + 1):
            if g[j][i] == "1":
                g[j][i] = "2"
    for (j, a, b) in CREASE:
        for i in range(a, b + 1):
            if g[j][i] == "2":
                g[j][i] = "3"
    return ["".join(r) for r in g]


import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parent.parent / "smap_anim"))
import items as _items                                   # the approved art itself (typed there, unchanged): falls rows, foot lip frames, glint tiles

LIGHT = {0: 0, 1: 0, 2: 1}                               # approved typed index -> DMG light water index: land and foam 0 (lightest), water 1


def to_dmg(v, cx, cy, i):
    """DMG light-water value of an approved typed pixel v at column i of cell (cx, cy): foam and land read 0, water 1, and the BANK RIM of the falls column (cell column 3 left, 4 right, rows 5 and 6)
    reads 1, so the column keeps an edge against the land it would otherwise melt into (the pool, rows 7 and 8, keeps the plain map)"""
    if v == 1 and cy in (5, 6) and i == (3 if cx == 46 else 4):
        return 1
    return LIGHT[v]


def fall_rows(side, k):
    """16 rows of one approved falls cell pair on frame k, the foot rows 12..15 included ('.' land, '-' foam, '+' water)"""
    return _items.fall_rows(side, k)


def _tile(rows):
    return [[{".": 0, "-": 1, "+": 2}.get(c, None) if not c.isdigit() else int(c) for c in r] for r in rows]


def static_art(WORLDS):
    """the approved falls art on frame 0, missing from the integrated map until now: row 6 (the lower falls, with the foot rows of the streaks), the foam lip cells of row 7 and the two
    glint tiles of row 8 (the splash arcs go).  Color gets the typed indices, DMG reads them through LIGHT (foam against water: 248 on 168)."""
    cells = {}
    for side, cx in (("L", 46), ("R", 47)):
        cells[(cx, 6)] = _tile(fall_rows(side, 0)[8:])
        cells[(cx, 7)] = _tile(_items.foot_tile(side, 0, 0))
    cells[(46, 8)] = _tile(_items.WS["vsubtle"]["A"][0])
    cells[(47, 8)] = _tile(_items.WS["vsubtle"]["B"][0])
    for (cx, cy), t in cells.items():
        for w in WORLDS:
            dmg = w is WORLDS[1]
            for j in range(8):
                for i in range(8):
                    v = t[j][i]
                    w.px[cy * 8 + j][cx * 8 + i] = to_dmg(v, cx, cy, i) if dmg else v
    return set(cells)


def flow(k):
    """4 rows of the 8 flow pixels (x 372..379) on frame k as igloo indices: the top row in shadow (foam 1, water 2), the others foam 0, water 1"""
    L, R = fall_rows("L", k), fall_rows("R", k)
    rows = []
    for t in range(4):
        s = L[4 + t][4:8] + R[4 + t][0:4]
        rows.append([({"-": 1, "+": 2} if t == 0 else {"-": 0, "+": 1})[c] for c in s])
    return rows


def cell_pixels(k=0):
    """the 40 x 8 block (x 360..399, y 40..47) on frame k: dict {(x, y): value} for every typed pixel (the '.' ones are left to the map)"""
    out = {}
    fl = flow(k)
    for j, row in enumerate(ledge_rows()):
        for i, c in enumerate(row):
            if c == ".":
                continue
            if c == "f":
                out[(X0 + i, Y0 + j)] = fl[j - 4][i - 12]
            else:
                out[(X0 + i, Y0 + j)] = int(c)
    return out


def apply(WORLDS):
    px = cell_pixels(0)
    static_art(WORLDS)
    for x in range(X0 + 1, 386):                         # the mountain's own foot line at y 39 opens where the ledge hangs from it (the face above is lit there)
        px[(x, 39)] = 1
    for y, (xs, s) in ARCH.items():                      # the top of the mouth, cut into the mountain's face above the ledge
        for i, c in enumerate(s):
            px[(xs + i, y)] = int(c)
    for w in WORLDS:
        for (cx, cy) in CELLS:                           # the cells' ground is snow now: the grass tufts and the bush that stood there go (the rock and the mouth are typed over it)
            for y in range(cy * 8, cy * 8 + 8):
                for x in range(cx * 8, cx * 8 + 8):
                    w.px[y][x] = 0
        for (x, y), v in px.items():
            w.px[y][x] = v
        for (cx, cy) in CELLS:
            w.pal[cy][cx] = "igloo"
    return set(CELLS) | {(46, 6), (47, 6), (46, 7), (47, 7), (46, 8), (47, 8)}
