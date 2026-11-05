"""The Jungle Zoo, 80 x 56. Palettes ZOO (jungle, the outer 24 columns each side): 0 light ground, 1 leaf, 2 deep leaf, 3 ink;
ZOOGATE (the middle 32 columns): 0 light ground, 1 sand wood, 2 brown, 3 ink.
A wooden gate with a ZOO board and double doors, bushy trees and hedges either side, and two pairs of eyes in the hedge."""
from canvas import Canvas, piece

W, H = 80, 56
PAL = "zoo"

CANOPY = piece(".:5 3:6 .:5", ".:3 3:2 1:6 3:2 .:3", ".:2 3:1 1:3 0:2 1:5 3:1 .:2", ".:1 3:1 1:2 0:1 1:7 2:2 3:1 .:1",
               "3:1 1:9 2:5 3:1", "3:1 1:6 0:1 1:3 2:4 3:1", "3:1 1:5 2:9 3:1", ".:1 3:1 2:12 3:1 .:1", ".:2 3:2 2:8 3:2 .:2",
               ".:4 3:8 .:4")
TRUNK = piece((".:6 3:1 2:2 3:1 .:6", 8), ".:4 3:8 .:4")
LET = {"Z": ["11111", "00001", "00010", "00100", "01000", "10000", "11111"], "O": ["01110", "10001", "10001", "10001", "10001", "10001", "01110"]}
EYES = piece("3:6", "3:1 0:1 3:1 3:1 0:1 3:1", "3:6")


def build():
    c = Canvas("zoo", PAL, W, H)
    c.palrect(24, 0, 56, 56, "zoogate")
    # ---- the gate: the board, the beam, the two doors between the posts -------------------------------------------------------------------
    c.row(8, "0:24 3:32 0:24")
    for y in range(9, 22):
        c.row(y, "0:24 3:1 2:1 1:28 2:1 3:1 0:24")
    c.row(22, "0:24 3:32 0:24")
    for k, ch in enumerate("ZOO"):
        for j, r in enumerate(LET[ch]):
            for i, v in enumerate(r):
                if v == "1":
                    c.put(30 + k * 7 + i, 12 + j, "3")
    for y in (23, 24, 25):
        c.row(y, "0:24 3:1 2:30 3:1 0:24")
    for y in range(26, 52):
        if y in (32, 44):
            c.row(y, "0:24 3:1 1:2 3:1 2:24 3:1 1:2 3:1 0:24")
        else:
            c.row(y, "0:24 3:1 1:2 3:1 (1:3 2:1)*2 1:3 3:1 3:1 1:3 (2:1 1:3)*2 3:1 1:2 3:1 0:24")
    c.row(52, "0:24 3:32 0:24")
    # ---- trees: a trunk, a canopy, a hedge of two bushes in front ---------------------------------------------------------
    c.paste(4, 29, TRUNK)
    c.paste(4, 19, CANOPY)
    c.paste(59, 25, TRUNK)
    c.paste(59, 15, CANOPY)
    c.paste(0, 39, CANOPY)
    c.paste(8, 41, CANOPY)
    c.paste(57, 41, CANOPY)
    c.paste(64, 39, CANOPY)
    # two pairs of eyes in the bushes
    c.paste(5, 44, EYES)
    c.paste(69, 43, EYES)
    return c


if __name__ == "__main__":
    print(len(build().out()))
