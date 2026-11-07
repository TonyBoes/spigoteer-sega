"""Milk bar round 4: ONLY the lot and the bikes change.  The building (y < 56), the bottle sign and the cow are round 3's cow_a3, pixel for pixel
(checked by lot_check in sheet.py).  Lot = whole cells x 32..95, y 56..71 (8 x 2 cells) in its own palette (cell palette, set with palrect).
Palette indices in the lot's palette (FACTORY on Color): 0 paving (light), 1 paint lines and chrome, 2 shade row and tank, 3 ink.
Everything below is typed: bay tiles are 8 px wide x 16 rows (y 56 to 71) as ASCII, bike rows are typed per row.  '.' in a typed row is transparent.
DMG: paving is shade 0 (lightest), the lot has NO outline and NO front kerb: the bays simply run off the bottom of the piece."""
import common as C
import cow_a3

W, H = cow_a3.W, cow_a3.H
BIOME, AT = cow_a3.BIOME, cow_a3.AT
LOT_PAL = 'factory'
X0, Y0, X1, Y1 = 32, 56, 96, 72
REGION = None

# ---- UPRIGHT: vertical bays 8 px apart (one cell), the line at the bay's left column, nose-in (front wheel up, toward the diner) ----
# a bike seen from above and behind, 7 wide x 13 tall (local columns 0 to 6, centre 3), pasted at y 58; in the bay it sits at columns 1 to 7
UP_A = C.G(
    "...3...",
    "...3...",
    ".3.3.3.",
    ".31113.",
    "..323..",
    ".31223.",
    ".31223.",
    ".31223.",
    "..333..",
    ".13331.",
    ".13331.",
    "..333..",
    "...3...")
UP_B = C.G(                                               # the chopper: a sissy bar behind the seat
    "...3...",
    "...3...",
    ".3.3.3.",
    ".31113.",
    "..323..",
    ".31223.",
    ".31223.",
    ".31223.",
    "..333..",
    ".13331.",
    ".31113.",
    ".3.3.3.",
    "...3...")


def upright(bikes, grain=False, line="1"):
    """bikes: {bay k: typed bike}"""
    c = cow_a3.build()
    clear_lot(c)
    if grain:
        paving_grain(c)
    for k in range(8):
        x = X0 + 8 * k
        for y in range(Y0, Y1):
            c.px[y][x] = line if y > Y0 else "2"
        for y in range(1):
            for i in range(1, 8):
                c.px[Y0][x + i] = "2"
    for y in range(Y0 + 1, Y1):                           # the right edge of the last bay
        c.px[y][X1 - 1] = line
    for k, b in bikes.items():
        C.paste(c, X0 + 8 * k + 1, 58, b)
    c.palrect(X0, Y0, X1, Y1, LOT_PAL)
    return c


# ---- SLANT: angled bays, lines at 1 column per 2 rows leaning to the upper right, nose-in (front wheel up and to the right) ----
# a bay is one cell wide (the line starts at the cell's column 0 on the bottom row, y 71, and reaches column 7 at the top, y 57); the bike sits
# between its line and the next one, so it spills into the next cell.  Each bike row is typed as (first frame column, 7 characters), frame
# column 0 = the bay's cell column 0, y 58 to 70 (13 rows).
SL_A = [
    (7, "...3..."),   # y58
    (7, "...3..."),   # y59
    (6, ".3.3.3."),   # y60
    (6, ".31113."),   # y61
    (5, "..323.."),   # y62
    (5, ".31223."),   # y63
    (4, ".31223."),   # y64
    (4, ".31223."),   # y65
    (3, "..333.."),   # y66
    (3, ".13331."),   # y67
    (2, ".13331."),   # y68
    (2, "..333.."),   # y69
    (1, "...3...")]   # y70
SL_B = [
    (7, "...3..."),
    (7, "...3..."),
    (6, ".3.3.3."),
    (6, ".31113."),
    (5, "..323.."),
    (5, ".31223."),
    (4, ".31223."),
    (4, ".31223."),
    (3, "..333.."),
    (3, ".13331."),
    (2, ".31113."),
    (2, ".3.3.3."),
    (1, "...3...")]
LINE_RUNS = [1, 2, 2, 2, 2, 2, 2, 2]       # rows per column, from the top (y 57) down: column 7 for 1 row, then 6, 5, ... 0 for 2 rows (y 71 and 70)


def slant(bikes, grain=False, line="1"):
    c = cow_a3.build()
    clear_lot(c)
    if grain:
        paving_grain(c)
    for k in range(8):
        x = X0 + 8 * k
        for i in range(8):                                 # shade row under the diner
            c.px[Y0][x + i] = "2"
        y, col = Y0 + 1, 7
        for n in LINE_RUNS:
            for _ in range(n):
                c.px[y][x + col] = line
                y += 1
            col -= 1
        assert y == Y1 + 0, y
    for k, b in bikes.items():
        x = X0 + 8 * k
        for j, (off, s) in enumerate(b):
            for i, ch in enumerate(s):
                if ch != ".":
                    c.px[58 + j][x + off + i] = ch
    c.palrect(X0, Y0, X1, Y1, LOT_PAL)
    return c


def paving_grain(c):
    """the paving's grain: shade 1 on an ordered 25 percent pattern (brick-staggered, period 4 x 4, tile-aligned) under the shade row"""
    for y in range(Y0 + 1, Y1):
        for x in range(X0, X1):
            if (x + (y % 4 >= 2) * 2) % 4 == 1 and y % 2 == 1:
                c.px[y][x] = "1"


def clear_lot(c):
    for y in range(Y0, Y1):
        for x in range(X0, X1):
            c.px[y][x] = "0"


def round3():
    return cow_a3.build()
