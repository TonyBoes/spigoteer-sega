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


def fall_rows(side, k):
    """rows of one approved falls cell pair on frame k, 16 rows of 8 chars ('.' land, '-' foam, '+' water); only the water columns matter here"""
    cols = range(0, 4) if side == "L" else range(4, 8)
    out = []
    for r in range(16):
        row = list("...-++++" if side == "L" else "++++-...")
        for i, f in enumerate(cols):
            if r < 12 and FALL_COLS[f][(r - FALL_STEP * k) % 12] == "-":
                row[4 + i if side == "L" else i] = "-"
        out.append("".join(row))
    return out


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
    return set(CELLS)
