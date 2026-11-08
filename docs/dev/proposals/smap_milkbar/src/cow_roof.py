"""Milk bar round 4i (owner, after Q106): "versions of the milk bar where the roof isnt domed and the sign on the building looks more like a neon sign".
Base: round 4h option A (dark glass windows and A's doors).  restyle_roof(base, v) redraws, by hand, only the roof and the sign band (x 32..95, y 20..39 of the
96 x 72 piece); the body from y 40 down, the lot, the bikes are untouched.
 v1  flat roof with a parapet: coping, a cornice line and dentils
 v2  flat roof with a raised centre where the sign sits (the classic roadside diner), a low parapet on the two wings
 v3  a canted roof: the top edge climbs left to right in steps, parallel ink stripes, a flat underside
The neon sign (all three): a dark board, a 1 px pink tube border with the corners cut, the letters one pixel thick: a chrome core (the hot tube) with a pink halo
on the dark board (idx 2 on idx 3).  Static.  COW palette only: 0 meadow, 1 chrome, 2 pink, 3 ink.  On DMG the halo is shade 2 and the core shade 1."""
from cow_a3 import LET

GAP = 3                                            # pixels between two letters (the halos need room)
WORD = 5


def clear(px):
    for y in range(18, 40):
        for x in range(32, 96):
            px[y][x] = "0"


def hline(px, y, x0, x1, ch):
    for x in range(x0, x1):
        px[y][x] = ch


def row(px, y, x0, x1, ch, edge="3"):
    """a roof row between x0 and x1 (exclusive), ink at both ends"""
    hline(px, y, x0, x1, ch)
    px[y][x0] = edge
    px[y][x1 - 1] = edge


def border(px, x0, y0, x1, y1):
    """a 1 px pink tube round the inside of a rectangle (x1, y1 inclusive), the four corner pixels left dark"""
    for x in range(x0 + 1, x1):
        px[y0][x] = "2"
        px[y1][x] = "2"
    for y in range(y0 + 1, y1):
        px[y][x0] = "2"
        px[y][x1] = "2"


def text_width():
    w = 0
    for ch in "MILK":
        w += len(LET[ch][0]) + GAP
    w += WORD - GAP
    for ch in "BAR":
        w += len(LET[ch][0]) + GAP
    return w - GAP


def letters(px, x, y):
    """MILK BAR, 5 rows from (x, y): chrome core, pink halo on the dark pixels next to the core"""
    core = []
    for ch in "MILK BAR":
        if ch == " ":
            x += WORD - GAP
            continue
        for j, r in enumerate(LET[ch]):
            for i, v in enumerate(r):
                if v == "1":
                    core.append((x + i, y + j))
        x += len(LET[ch][0]) + GAP
    cs = set(core)
    for (cx, cy) in core:
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = cx + dx, cy + dy
            if (nx, ny) not in cs and px[ny][nx] == "3":
                px[ny][nx] = "2"
    for (cx, cy) in core:
        px[cy][cx] = "1"


def star(px, cx, cy):
    """a tiny neon star (a plus): chrome core, pink halo"""
    pts = [(cx, cy), (cx - 1, cy), (cx + 1, cy), (cx, cy - 1), (cx, cy + 1)]
    for (x, y) in ((cx - 1, cy - 1), (cx + 1, cy - 1), (cx - 1, cy + 1), (cx + 1, cy + 1), (cx - 2, cy), (cx + 2, cy), (cx, cy - 2), (cx, cy + 2)):
        if px[y][x] == "3":
            px[y][x] = "2"
    for (x, y) in pts:
        px[y][x] = "1"


def board(px, x0, y0, x1, y1, ty, stars=False):
    """the dark board x0..x1-1, y0..y1-1 (ink), its tube border on the outer ring inset one pixel, the lettering from row ty"""
    for y in range(y0, y1):
        for x in range(x0, x1):
            px[y][x] = "3"
    border(px, x0 + 1, y0, x1 - 2, y1 - 1)
    tw = text_width()
    tx = x0 + (x1 - x0 - tw) // 2
    letters(px, tx, ty)
    if stars:
        star(px, (x0 + 2 + tx) // 2 + 1, ty + 2)
        star(px, (x1 - 2 + tx + tw) // 2 - 1, ty + 2)


def restyle_roof(base, v, narrow=False):
    """narrow (v2 only): the raised block is 48 px wide (x 40..87) so that its edges fall on cell edges and the two wings are whole cells; the word gap is 4"""
    global WORD
    WORD = 4 if narrow else 5
    px = base.px
    clear(px)
    if v == 1:                                               # flat roof, parapet: coping, cornice line, dentils
        row(px, 25, 32, 96, "3", "3")
        row(px, 26, 32, 96, "1")
        row(px, 27, 32, 96, "1")
        row(px, 28, 32, 96, "3", "3")
        row(px, 29, 32, 96, "1")
        for x in range(34, 94, 4):
            px[29][x] = "3"
        row(px, 30, 32, 96, "3", "3")
        board(px, 32, 31, 96, 40, 33)
    elif v == 2:                                             # raised centre: the sign sits in a taller block, low parapet wings
        for y0, ch in ((28, "3"), (29, "1"), (30, "3")):
            row(px, y0, 32, 96, ch)
        for y in range(31, 40):                              # the wings' wall
            row(px, y, 32, 96, "1")
        for y0, ch in ((21, "3"), (22, "1"), (23, "1"), (24, "3")):
            row(px, y0, 40 if narrow else 38, 88 if narrow else 90, ch)
        board(px, 40, 25, 88, 40, 29, stars=False) if narrow else board(px, 38, 25, 90, 40, 29, stars=False)
        hline(px, 36, 46, 82, "2")                           # an underline tube
        px[36][45] = "3"
        px[36][82] = "3"
    else:                                                    # canted roof: the top climbs to the right
        for x in range(32, 96):
            t = 28 - ((x - 32) * 5) // 64
            for y in range(t, 30):
                px[y][x] = "1"
            px[t][x] = "3"
            if t + 2 < 30:
                px[t + 2][x] = "3"
            px[30][x] = "3"
        for x in (32, 95):
            for y in range(24, 31):
                if px[y][x] != "0":
                    px[y][x] = "3"
        board(px, 32, 31, 96, 40, 33)
    return base
