"""CHROME COW variation D, "Roadside cow", 96 x 72. Palette COW: 0 meadow, 1 chrome, 2 pink neon, 3 purple-black.  Light from the top left.
Option 1's diner exactly (barrel roof, MILK BAR board, ribbon of windows, door, checker lip), with the pylon sign replaced by a roadside statue: a big spotted
cow (24 x 16) standing on a pink plinth, and the two bikes parked in a row facing the door.  The roof stays clean."""
import common as C
import kit as K
from canvas import Canvas
import v_cow

W, H = 96, 72
BIOME, AT = 'farm', (39, 22)

ROOF = [22, 26, 28, 29, 30, 31, 32, 32]
PANE = ["33333333", "22222233", "22222233", "21222233", "22122233", "22212233", "22222233", "22222233"]
DOORD = C.G("3333333333333333", ("3222222332222223", 4), ("3222221331222223", 2), ("3222222332222223", 3), "3333333333333333", ("3111111331111113", 4), "3333333333333333")
# the statue, facing right: horns, ears, a spotted chrome body, a pink nose and udder, four legs, a tail with a tuft (typed row by row, left justified, padded with '_')
COWBIG = [
    "________________________",
    "___________________3__3_",
    "___________________3__3_",
    "____" + "3" * 19 + "_",
    "__33" + "1111111111111" + "3" + "11111" + "3",
    "_3_3" + "11333" + "11111111" + "3" + "11131" + "3",
    "_3_3" + "13333" + "11111111" + "3" + "11111" + "3",
    "_3_3" + "11333111333" + "11" + "3" + "11111" + "3",
    "_3_3" + "1111111333331" + "3" + "11222" + "3",
    "33_3" + "1111111133311" + "3" + "11222" + "3",
    "33_3" + "1111111111111" + "3" + "33333" + "_",
    "___3" + "1111111111111" + "3" + "______",
    "___" + "3" * 15 + "______",
    "____313_313_313_313_____",
    "____313_313_313_313_____",
    "____333_333_333_333_____",
]


def pad(rows, w):
    return [r.ljust(w, "_") for r in rows]


def build():
    c = Canvas("cowD", "cow", W, H)
    # ---- the barrel roof (as option 1) ----
    C.silh(c, 24, ROOF, 64, lambda x, y, k: "1")
    for x in range(32, 96):
        c.px[31][x] = "3"
    # ---- the MILK BAR board and the body, as option 1 ----
    K.rect(c, 32, 32, 96, 40, "3")
    K.hl(c, 32, 34, 94, "2")
    K.text(c, 48, 34, "MILK BAR", "1")
    for y in range(40, 56):
        K.hl(c, y, 32, 96, "1")
        c.px[y][32] = "3"
        c.px[y][95] = "3"
    K.hl(c, 40, 32, 96, "3")
    K.hl(c, 41, 32, 96, "2")
    for x in range(40, 80):
        for j in range(8):
            c.px[42 + j][x] = PANE[j][x % 8]
        c.px[50][x] = "1"
        c.px[51][x] = "3"
    for x in range(32, 80):
        c.px[52][x] = "3"
        c.px[53][x] = "1"
        c.px[54][x] = "1"
        c.px[55][x] = "3" if (x % 8) < 4 else "1"
    for j, r in enumerate(DOORD):
        for i, ch in enumerate(r):
            c.px[40 + j][80 + i] = ch
    # ---- the statue on its plinth ----
    C.paste(c, 0, 40, pad(COWBIG, 24))
    K.box(c, 0, 56, 28, 60, "3", "2")
    K.hl(c, 57, 1, 27, "1")
    # ---- the bikes, in a row facing the door ----
    for bx in (36, 62):
        C.paste(c, bx, 58, v_cow.bike(v_cow.BIKE_BASE))
        C.paste(c, bx, 63, v_cow.WHEEL)
        C.paste(c, bx + 13, 63, v_cow.WHEEL)
    return c
