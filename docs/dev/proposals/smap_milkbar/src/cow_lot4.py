"""Milk bar round 4d: 3/4 bikes angled toward the door, and a lot that is the road's own widening.  Building (y < 56), sign and cow are round 3's cow_a3.
Owner 11-06: "The bikes need to be 3/4 angled toward venue. Parking lot is ok, but needs to be logically connected to the rest of the map."
The trunk road runs on cell rows 30 and 31 (y 56..71 of this piece).  The lot IS those two cell rows: the road with its north kerb taken away (the diner
stands on that side).  Paving = the game's own road tiles (tiles.ROAD: F1 speckle for y 56..63, the ES south edge for y 64..71: body, white line at y 69, kerb at
y 70 and 71), so on Color the lot must sit on the road's palette TOWN1 (cream 0, skin 1, lilac 2, ink 3) to join it.  The road's north kerb simply ends at each end
of the lot (the mouth of the driveway).  Bays: lines at 45 degrees (one column per row) lean up and to the right, toward the door; the bikes are 3/4 views heading
up and right.  Indices: 0 white (paint, chrome), 1 body, 2 slate/kerb, 3 ink.  Everything is typed; the paving rows are the road's own typed tile rows."""
import common as C
import cow_a3
import tiles as T

W = cow_a3.W
BIOME, AT = cow_a3.BIOME, cow_a3.AT
X0, X1, Y0, Y1 = 32, 96, 56, 72
LOT_PAL = 'town1'

# the wheel in 3/4: a ring (ink) seen obliquely, an ellipse elongated along the heading (45 degrees), 5 x 5, with a white hub plus
W34 = [".333.", "3...3", "3.3.3", "3.3.3", "3...3", ".333."]
W_FRONT = [".33.", "3..3", "3..3", "3..3", ".33."]
# a parked motorcycle heading up and to the right, seen from behind and the left, 13 x 12: bars (slanted across the heading) over the front wheel, the tank, seat
# over the rear wheel, the engine and exhaust low between the wheels.  The wheels are pasted at (8, 2) front and (0, 7) rear.
BIKE = [
    "..........3...3.",
    "..........3www3.",
    ".....3333.3.....",
    ".....3w23.3.....",
    ".32223223.3.....",
    ".33333333.3.....",
    "......3ww3.3....",
    "......w33w......",
    ".....33ww3......",
    "....333333......",
    "................",
    "................"]
BIKE_B = BIKE                                            # (a second drawing is made if the first one reads)
WHEELS = ((W_FRONT, 11, 2), (W34, 0, 6))


def paving(c):
    for y in range(Y0, Y1):
        for x in range(X0, X1):
            c.px[y][x] = (T.ROAD['F1'][y % 8][x % 8] if y < 64 else T.ROAD['ES'][y - 64][x % 8])
    for x in range(X0, X1):                              # the diner's foot: one row of kerb colour
        c.px[Y0][x] = "2"


def put(c, x, y, rows, w="0"):
    for j, r in enumerate(rows):
        for i, ch in enumerate(r):
            if ch != ".":
                c.px[y + j][x + i] = w if ch == "w" else ch


def bike(c, x, y, rows=None):
    put(c, x, y, rows or BIKE)
    for (w, wx, wy) in WHEELS:
        put(c, x + wx, y + wy, w)


def build(bikes=((9, 57), (29, 57), (49, 57)), lines=True):
    """bays 20 px apart (x offset of each bike from the lot's left edge); lines at 45 degrees leaning up and right, clipped to the lot"""
    c = cow_a3.build()
    for y in range(Y0, Y1):
        for x in range(X0, X1):
            c.px[y][x] = "0"
    paving(c)
    if lines:
        for k in range(5):
            for y in range(Y0 + 1, 69):
                x = X0 + 20 * k + (68 - y)
                if x < X1:
                    c.px[y][x] = "0"
    for (bx, by) in bikes:
        bike(c, X0 + bx, by)
    c.palrect(X0, Y0, X1, Y1, LOT_PAL)
    return c
