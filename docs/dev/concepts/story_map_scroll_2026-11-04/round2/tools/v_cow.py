"""The Chrome Cow, 80 x 56. Palette COW: 0 pale meadow, 1 chrome, 2 pink, 3 ink.
A chrome diner with a barrel roof, a pink band, a MILK sign, a window with counter stools, a door and a black-and-white checker band,
on its road; two cows behind a fence in the field to the left."""
from canvas import Canvas, piece

W, H = 80, 56
PAL = "cow"

LET = {"M": ["10001", "11011", "10101", "10001", "10001", "10001", "10001"], "I": ["01110", "00100", "00100", "00100", "00100", "00100", "01110"],
       "L": ["10000", "10000", "10000", "10000", "10000", "10000", "11111"], "K": ["10001", "10010", "10100", "11000", "10100", "10010", "10001"]}
COW = piece(".:1 3:1 .:2 3:1 .:9", ".:1 3:4 .:1 3:7 .:1", "3:1 1:4 3:1 1:7 3:1", "3:1 1:1 3:1 1:2 3:1 1:2 3:2 1:3 3:1",
            "3:1 2:3 1:1 3:1 1:5 3:1 1:1 3:1", ".:1 3:4 1:1 1:3 3:2 1:2 3:1", ".:6 3:1 1:6 3:1", ".:6 3:8",
            ".:6 3:1 1:1 3:1 .:1 3:1 1:1 3:1 .:1", ".:6 3:3 .:1 3:3 .:1")
WINDOW = piece("3:26", ("3:1 0:7 1:1 0:8 1:1 0:7 3:1", 8), "3:1 0:3 3:4 0:3 3:4 0:3 3:4 0:3 3:1", ("3:1 0:4 3:2 0:5 3:2 0:5 3:2 0:4 3:1", 2),
               "3:1 2:24 3:1", "3:26")
DOOR = piece("3:10", ("3:1 0:8 3:1", 5), "3:1 1:8 3:1", ("3:1 0:8 3:1", 4), "3:1 1:8 3:1", "3:1 1:6 2:1 1:1 3:1", ("3:1 1:8 3:1", 7), "3:10")


def build():
    c = Canvas("cow", PAL, W, H)
    # ---- the sign: chrome board, pink letters ---------------------------------------------------------------------------
    c.row(0, "0:34 3:36 0:10")
    for y in range(1, 10):
        c.row(y, "0:34 3:1 1:34 3:1 0:10")
    c.row(10, "0:34 3:36 0:10")
    for k, ch in enumerate("MILK"):
        for j, r in enumerate(LET[ch]):
            for i, v in enumerate(r):
                if v == "1":
                    c.put(40 + k * 7 + i, 2 + j, "2")
    # ---- the roof, the pink band, the wall --------------------------------------------------------------------------------
    c.row(11, "0:26 3:52 0:2")
    for y in range(12, 16):
        c.row(y, "0:26 3:1 1:50 3:1 0:2")
    c.row(16, "0:26 3:52 0:2")
    for y in range(17, 20):
        c.row(y, "0:28 3:1 2:46 3:1 0:4")
    for y in range(20, 49):
        c.row(y, "0:28 3:1 1:46 3:1 0:4")
    for y in (38, 39):
        c.row(y, "0:28 3:1 (3:2 0:2)*11 3:2 3:1 0:4")
    for y in (40, 41):
        c.row(y, "0:28 3:1 (0:2 3:2)*11 0:2 3:1 0:4")
    for y in (44, 45, 46):
        c.row(y, "0:28 3:1 2:46 3:1 0:4")
    c.row(49, "0:26 3:52 0:2")
    c.paste(32, 22, WINDOW)
    c.paste(62, 26, DOOR)
    # ---- the foot: grass (the map's own road runs under the picture) --------------------------------------------------------------
    for y in range(50, 56):
        c.row(y, "0:80")
    # ---- the field: a fence and two cows ---------------------------------------------------------------------------------------
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
    c.paste(2, 22, COW)
    c.paste(10, 32, COW)
    return c


if __name__ == "__main__":
    print(len(build().out()))
