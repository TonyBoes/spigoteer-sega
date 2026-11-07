"""Milk bar round 4c: ONLY the lot and the bikes change; building (y < 56), bottle sign and cow are round 3's cow_a3, pixel for pixel.
Owner (11-06): the whole map is front-on with a little top showing, so no top-down anything.  Three proposals, all front-on:
  A  rear view: narrow upright bikes seen from behind, nose-in to the diner, on a shallow strip of grey paving with short bay lines running up toward the diner.
  B  side view, three bikes in a row along the front, the middle one nearer (2 px lower) and overlapping its neighbours, on the grey paving strip, no bays, no outline.
  C  no lot: two side-view bikes on kickstands on the meadow beside the door, like props (cells in the FARM palette, the ground's own palette).
Lot palette (A, B): FACTORY: 0 white (paint, chrome, lights), 1 paving, 2 slate, 3 ink.  C uses FARM: 0 meadow, 1 gold chrome, 2 brown, 3 dark brown.
Everything is typed: bikes as rows of run specs ('c:n', '.' = transparent, 'w' = the chrome/light shade, set per proposal), pixel lists, bay line runs.
No outline round any lot, no front kerb: open front."""
import common as C
import cow_a3

W = cow_a3.W
BIOME, AT = cow_a3.BIOME, cow_a3.AT
X0, X1, Y0, Y1 = 32, 96, 56, 72


def R(spec):
    out = ""
    for tok in spec.split():
        ch, n = tok.split(":")
        out += ch * int(n)
    return out


# ---- SIDE VIEW, 21 x 12, facing right: handlebar and mirror, headlight, fork, tank (white stripe on its lit left), seat, rear fender, engine block, exhaust/frame,
# two wheels (ink tyre, white rim, ink hub) pasted at y 5 ----
SIDE = [R(s) for s in (
    ".:14 3:1 .:6",
    ".:14 3:1 w:2 3:1 .:3",
    ".:3 3:4 .:1 3:5 .:2 3:1 .:1 w:1 3:1 .:2",
    ".:2 3:6 3:1 w:1 2:2 3:1 .:2 3:1 .:1 w:1 3:1 .:2",
    ".:1 3:7 3:1 2:3 3:1 .:3 3:1 .:4",
    ".:7 3:1 w:5 .:8",
    ".:7 3:1 w:1 3:3 w:1 .:8",
    ".:7 3:1 w:5 .:8",
    ".:7 3:7 .:7",
    ".:21", ".:21", ".:21")]
assert all(len(r) == 21 for r in SIDE) and len(SIDE) == 12
SISSY = [(1, 0), (1, 1), (1, 2), (1, 3)]                    # the chopper: a sissy bar behind the seat
KICK = [(10, 9), (9, 10), (8, 11)]                           # a kickstand, down and back from the frame to the ground line
WHEEL = [".33333.", "33www33", "3w333w3", "3w333w3", "3w333w3", "33www33", ".33333."]

# ---- REAR VIEW, 7 x 13: mirrors, front tyre peeking between the stalks, wide bars, tank, seat, tail light, fender, the rear tyre (a narrow dark column) ----
REAR_CHUNKY = ["3..3..3", "3..3..3", "3wwwww3", ".32223.", ".3w223.", ".32223.", ".33333.", ".33333.", "..3w3..", "..333..", "..333..", "..333..", "..333.."]
REAR_SLIM = [".3.3.3.", ".3.3.3.", ".3www3.", "..323..", "..3w3..", "..3w3..", "..333..", "..333..", "..3w3..", "..333..", "..333..", "..333..", "..333.."]
assert all(len(r) == 7 for r in REAR_CHUNKY + REAR_SLIM) and len(REAR_CHUNKY) == len(REAR_SLIM) == 13


def clear_lot(c):
    for y in range(Y0, Y1):
        for x in range(X0, X1):
            c.px[y][x] = "0"


def paving(c):
    for y in range(Y0, Y1):
        for x in range(X0, X1):
            c.px[y][x] = "1"
    for x in range(X0, X1):                                 # the shade row under the diner
        c.px[Y0][x] = "2"
    c.palrect(X0, Y0, X1, Y1, 'factory')


def put_rows(c, x, y, rows, w):
    for j, r in enumerate(rows):
        for i, ch in enumerate(r):
            if ch != ".":
                c.px[y + j][x + i] = w if ch == "w" else ch


def put_side(c, x, y, w, sissy=False, kick=False):
    put_rows(c, x, y, SIDE, w)
    for wx in (0, 14):
        put_rows(c, x + wx, y + 5, WHEEL, w)
    for on, pts in ((sissy, SISSY), (kick, KICK)):
        if on:
            for (i, j) in pts:
                c.px[y + j][x + i] = "3"


def build_a():
    """rear view in bays: bay lines (white) 8 px apart, short, from y 63 to 71; bikes in bays 1, 3, 5"""
    c = cow_a3.build()
    clear_lot(c)
    paving(c)
    for k in range(8):
        for y in range(63, Y1):
            c.px[y][X0 + 8 * k] = "0"
    for bay, art in ((1, REAR_CHUNKY), (3, REAR_SLIM), (5, REAR_CHUNKY)):
        put_rows(c, X0 + 8 * bay + 1, 58, art, "0")
    return c


def build_b():
    """three side-view bikes along the front; the middle one nearer"""
    c = cow_a3.build()
    clear_lot(c)
    paving(c)
    put_side(c, 33, 58, "0")
    put_side(c, 73, 58, "0")
    put_side(c, 53, 60, "0", sissy=True)
    return c


def build_c():
    """no lot: two side-view bikes on kickstands on the meadow beside the door; the cells under them take the ground's own palette"""
    c = cow_a3.build()
    clear_lot(c)
    put_side(c, 44, 59, "1", kick=True)
    put_side(c, 68, 59, "1", sissy=True, kick=True)
    c.palrect(40, Y0, X1, Y1, 'farm')
    return c


def round3():
    return cow_a3.build()
