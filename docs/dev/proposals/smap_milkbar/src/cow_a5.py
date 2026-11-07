"""Milk bar round 4f (owner Q106): round 4e's building, lot and bikes (cow_lot4.build, unchanged) with the bottle sign and the cow repositioned and the hay field
replaced by a cow pasture.  One picture, 96 x 184 px (12 x 23 cells), top left at world cell (50, 47) of the A5 layout: the pasture (cell rows 47 to 54, where the
hay field was), the milk bar piece (rows 55 to 63, with the south lane under the lot) and the verge south of the lane (rows 64 to 69).
All picture cells use the COW palette except the lot (TOWN1, the road's own palette, as in 4e).  The grass is the farm biome's own ground: every cell the picture
leaves blank keeps the world's ground tile.  Everything typed: the fence tiles, the trough, the two cows are the round 2 cow (copied), the sign is round 2 C's bottle
(copied), the pole is shortened by hand in arrangement 2.
Arrangement 1: the sign at the west end of the lane, beside the road where it comes in from the bridge, the pen with two cows and a trough.
Arrangement 2: the sign on the south verge facing the diner across the lane (a shorter pole), one cow on the lawn west of the building, one small cow and the trough in the pen."""
import a5env  # noqa: F401
import common as C
import cow_lot4 as N
import v_cow
from canvas import Canvas
from cow_c import BOTTLE

W, H = 96, 184
BIOME, AT = 'farm', (50, 47)
OFF = 64                                    # the milk bar piece starts 64 px (8 cell rows) down

# fence tiles, 8 x 8: a post (lit left column, dark right) with rails running right (white top row, ink under), a rail-only tile, a post column for the sides
POST = ["13000000", "13000000", "13111111", "13333333", "13000000", "13111111", "13333333", "13000000"]
RAIL = ["00000000", "00000000", "11111111", "33333333", "00000000", "11111111", "33333333", "00000000"]
SIDE = ["00130000"] * 8
TROUGH = ["3333333333333333", "3111111111111113", "3333333333333333", ".3............3.", ".3............3."]


def put(c, x, y, rows):
    for j, r in enumerate(rows):
        for i, ch in enumerate(r):
            if ch not in '._':
                c.px[y + j][x + i] = ch


def sign(c, cx, ytop, base_y, foot=10):
    """round 2 C's bottle (16 wide, centred on the pole) on a pole 4 wide with a two-row foot; the pole runs from the bottle to the foot"""
    put(c, cx - 8, ytop, BOTTLE)
    for y in range(ytop + 23, base_y):
        for i, ch in enumerate("3113"):
            c.px[y][cx - 2 + i] = ch
    for i, ch in enumerate("3" * foot):
        c.px[base_y][cx - foot // 2 + i] = ch
    for i, ch in enumerate("3" + "1" * (foot - 2) + "3"):
        c.px[base_y + 1][cx - foot // 2 + i] = ch


def pen(c):
    for i in range(12):
        t = POST if i % 2 == 0 else RAIL
        put(c, 8 * i, 0, t)
        put(c, 8 * i, 56, t)
    for j in range(1, 7):
        put(c, 0, 8 * j, SIDE)
        put(c, 88, 8 * j, SIDE)
    put(c, 88, 0, POST)
    put(c, 88, 56, POST)


def build(arr, style=None):
    """arr 1 and 2: as round 4f's first set; arr 3 (owner, after Q106): the building with its lot and bikes one cell (8 px) west, a cell of grass between it and
    the north-south road; the cow where the sign was in arrangement 1, the sign beside the building where the cow was; the pen of arrangement 1"""
    c = Canvas("cowA5_%d" % arr, "cow", W, H)
    base = N.build()
    if style:
        import cow_bldg
        cow_bldg.restyle(base, style)
    for y in range(2, 56):                                   # the old sign and cow places are cleared
        for x in range(8, 24):
            base.px[y][x] = "0"
    for y in range(56, 72):                                  # round 2's cow place (x < 32) is left to the lane tiles below
        for x in range(0, 32):
            base.px[y][x] = "0"
    dx = -8 if arr == 3 else 0
    for y in range(72):
        for x in range(96):
            if 0 <= x + dx < 96:
                c.px[y + OFF][x + dx] = base.px[y][x]
    lot0 = 32 + dx
    for y in range(56, 72):                                  # the lane outside the lot: the road's own tiles (F1 above, ES kerb row below), TOWN1
        for x in list(range(0, lot0)) + list(range(96 + dx, 96)):
            c.px[y + OFF][x] = N.T.ROAD['F1'][y % 8][x % 8] if y < 64 else N.T.ROAD['ES'][y - 64][x % 8]
    c.palrect(0, 56 + OFF, 96, 72 + OFF, 'town1')
    pen(c)
    put(c, 14, 40, TROUGH)
    put(c, 62, 36, v_cow.COW)                                # the small cow in the pen
    if arr == 1:
        put(c, 28, 18, v_cow.COW)                            # the cow in the pen
        sign(c, 8, 2 + OFF, 54 + OFF, 8)                     # at the lane's west end, where the road comes in from the bridge (foot 8 wide, clear of Sal's stop)
    elif arr == 3:
        put(c, 28, 18, v_cow.COW)
        put(c, 1, 98, v_cow.COW)                             # the lawn cow, where the sign stood in arrangement 1
        sign(c, 18, 2 + OFF, 46 + OFF, 8)                    # the sign right beside the building, a shorter pole (the foot at y 110, above Sal's box)
    else:
        put(c, 4, 34 + OFF, v_cow.COW)                       # the cow on the lawn west of the building, above the lane
        sign(c, 44, 142, 174)                                # the south verge: bottle y 142..164, a short pole, the foot at y 174
    return c


if __name__ == "__main__":
    for a in (1, 2):
        print(a, C.tile_count(build(a)))
