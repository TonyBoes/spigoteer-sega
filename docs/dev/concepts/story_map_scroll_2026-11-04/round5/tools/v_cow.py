"""The Chrome Cow, 80 x 56: the tough biker bar (docs/story.md: the toughest bar in Fizzwater, a row of motorcycles outside a black, studded
biker bar under a neon sign of a cow in sunglasses; the game's stage look: purple-black wall, white chrome, pink MILK neon, the checker lip).
Palette COW: 0 meadow, 1 chrome, 2 pink neon, 3 purple-black.  A chrome-edged parapet, the neon cow head, a studded wall with the
MILK neon window, a studded door, a checker lip, two motorcycles parked out front; the cow field with its fence stays on the left."""
from canvas import Canvas, piece

W, H = 80, 56
PAL = "cow"

LET = {"M": ["10001", "11011", "10101", "10001", "10001", "10001", "10001"], "I": ["01110", "00100", "00100", "00100", "00100", "00100", "01110"],
       "L": ["10000", "10000", "10000", "10000", "10000", "10000", "11111"], "K": ["10001", "10010", "10100", "11000", "10100", "10010", "10001"]}
COW = piece(".:1 3:1 .:2 3:1 .:9", ".:1 3:4 .:1 3:7 .:1", "3:1 1:4 3:1 1:7 3:1", "3:1 1:1 3:1 1:2 3:1 1:2 3:2 1:3 3:1",
            "3:1 2:3 1:1 3:1 1:5 3:1 1:1 3:1", ".:1 3:4 1:1 1:3 3:2 1:2 3:1", ".:6 3:1 1:6 3:1", ".:6 3:8",
            ".:6 3:1 1:1 3:1 .:1 3:1 1:1 3:1 .:1", ".:6 3:3 .:1 3:3 .:1")

# the neon cow head in sunglasses, 24 x 12, typed row by row as (colour, first x, last x) spans over the pink board
HEAD_SPANS = [
    [(3, 1, 1), (3, 22, 22)],
    [(3, 1, 2), (3, 21, 22)],
    [(3, 2, 3), (3, 20, 21)],
    [(3, 3, 4), (3, 19, 20), (3, 9, 14)],
    [(3, 4, 19)],
    [(3, 3, 20), (1, 4, 4), (1, 19, 19)],
    [(3, 5, 18), (1, 7, 16)],
    [(3, 5, 18), (1, 7, 7), (1, 10, 10), (1, 13, 13), (1, 16, 16)],
    [(3, 5, 18), (1, 7, 10), (1, 13, 16)],
    [(3, 6, 17)],
    [(3, 7, 16), (1, 9, 14), (3, 10, 10), (3, 13, 13)],
    [(3, 8, 15), (1, 10, 13)],
]


def head():
    rows = []
    for spans in HEAD_SPANS:
        r = ["2"] * 24
        for col, a, b in spans:
            for x in range(a, b + 1):
                r[x] = str(col)
        rows.append("".join(r))
    return rows


WHEEL = piece(".:1 3:5 .:1", "3:2 1:3 3:2", "3:1 1:1 3:3 1:1 3:1", "3:1 1:1 3:3 1:1 3:1", "3:1 1:1 3:3 1:1 3:1", "3:2 1:3 3:2", ".:1 3:5 .:1")
# a parked motorcycle facing right, 20 x 12 (the wheels are pasted at y 5): pink tank, dark seat, chrome engine, handlebar and fork
BIKE_BASE = [
    ".............3331...",
    ".........2221..3....",
    "...3333.2222111.3...",
    "..3333333222223.311.",
    ".33333.1111113..3...",
    ".......133331.......",
    ".......133331.......",
    ".......111111.......",
    ".......333333.......",
]
BIKE_BASE2 = [                                           # the second bike: a chopper with a sissy bar behind the seat
    ".............3331...",
    ".........2221..3....",
    ".3.3333.2222111.3...",
    ".3.333333222223.311.",
    ".33333.1111113..3...",
    ".......133331.......",
    ".......133331.......",
    ".......111111.......",
    ".......333333.......",
]


def bike(base):
    assert all(len(r) == 20 for r in base)
    return piece(*[_runs(r) for r in base])


def _runs(r):
    out, i = [], 0
    while i < len(r):
        j = i
        while j < len(r) and r[j] == r[i]:
            j += 1
        out.append(f"{r[i]}:{j - i}")
        i = j
    return " ".join(out)


def build(dmg=False):
    c = Canvas("cow", PAL, W, H)
    for y in range(H):
        c.row(y, "0:80")
    # ---- the neon board: dark rim, chrome rim, the cow in sunglasses on pink ----------------------------------------------
    c.row(0, "0:40 3:28 0:12")
    c.row(1, "0:40 3:1 1:26 3:1 0:12")
    for k, r in enumerate(head()):
        c.row(2 + k, "0:40 3:1 1:1 =" + r + " 1:1 3:1 0:12")
    c.row(14, "0:40 3:1 1:26 3:1 0:12")
    c.row(15, "0:40 3:28 0:12")
    # ---- the parapet, the neon strip, the wall ------------------------------------------------------------------------------
    c.row(16, "0:28 3:52")
    c.row(17, "0:28 3:1 1:50 3:1")
    c.row(18, "0:28 3:1 1:50 3:1")
    c.row(19, "0:28 3:1 2:50 3:1")
    for y in range(20, 34):
        c.row(y, "0:28 3:52")
    c.row(34, "0:28 (1:2 3:2)*13")
    c.row(35, "0:28 (3:2 1:2)*13")
    # the stud rows (chrome rivets, every fourth pixel, offset a row down)
    for x in range(30, 80, 4):
        c.put(x, 21, "1")
    for x in range(32, 80, 4):
        if c.px[32][x] == "3":
            c.put(x, 32, "1")
    # ---- the MILK neon window ---------------------------------------------------------------------------------------------------
    c.row(22, "0:28 3:3 1:36 3:13")
    for y in range(23, 31):
        c.row(y, "0:28 3:3 1:1 3:34 1:1 3:13")
    c.row(31, "0:28 3:3 1:36 3:13")
    x = 31 + 1 + 5
    for k, ch in enumerate("MILK"):
        for j, r in enumerate(LET[ch]):
            for i, v in enumerate(r):
                if v == "1":
                    c.put(x + k * 6 + i, 23 + j, "2")
    # ---- the studded door -------------------------------------------------------------------------------------------------------
    door = piece("1:10", "1:1 3:8 1:1", "1:1 3:1 1:1 3:4 1:1 3:1 1:1", ("1:1 3:8 1:1", 2), "1:1 3:1 1:1 3:4 1:1 3:1 1:1",
                 ("1:1 3:6 1:1 3:1 1:1", 2), "1:1 3:8 1:1", "1:1 3:1 1:1 3:4 1:1 3:1 1:1", "1:1 2:8 1:1", "1:10")
    c.paste(70, 22, door)
    # ---- two motorcycles parked out front ---------------------------------------------------------------------------------------
    for (bx, base) in (((28, BIKE_BASE), (52, BIKE_BASE2)) if dmg else ((28, BIKE_BASE), (49, BIKE_BASE2))):      # DMG: the bikes on the 8 px grid
        c.paste(bx, 37, bike(base))
        c.paste(bx, 42, WHEEL)
        c.paste(bx + 13, 42, WHEEL)
    # ---- the field: a fence and two cows (as before) ----------------------------------------------------------------------------
    for x in (2, 13, 24):
        for y in range(41, 50):
            c.put(x, y, "3")
            c.put(x + 1, y, "3")
    for x in range(0, 26):
        if x not in (2, 3, 13, 14, 24, 25):
            c.put(x, 43, "1")
            c.put(x, 44, "3")
            c.put(x, 46, "1")
            c.put(x, 47, "3")
    c.paste(2, 16 if dmg else 22, COW)                        # DMG: both cows on the same phase of the grid
    c.paste(10, 32, COW)
    return c


if __name__ == "__main__":
    print(len(build().out()))
