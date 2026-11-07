"""Typed parts of the Jungle Zoo proposals (round 2): option 1's lion gate (round 1, unchanged) and the accessories taken from option 2 (giraffe, rail fence,
bamboo), re-typed so each stands on the 8 px grid.  Palettes: ZOOGATE 0 ground, 1 sand, 2 brown, 3 ink (gate, giraffe, fence); ZOO 0 ground, 1 leaf, 2 deep leaf, 3 ink."""
import common as C
import kit as K
import v_zoo

STONE = ["11111112", "11111112", "11111112", "22222222", "11211111", "11211111", "11211111", "22222222"]
NECK = ["31111113", "31221113", "31221113", "31111113", "31111113", "31111223", "31111223", "31111113"]
FENCE = ["31300000", "31300000", "11111111", "33333333", "31300000", "11111111", "33333333", "31300000"]
GHEAD = C.G("___3____3___", "___3____3___", "__33333333__", "333111111333", "333131131333", "__31111113__", "__31133113__", "___311113___", "___333333___")
BAMBOO = ["00312300"] * 7 + ["03312330"]
TUFT = C.G("__3333__", "_311113_", "31112113", "_321123_", "__3123__")


class _Mini:
    w = h = 16
    name = "lion"


def _lion():
    m = _Mini()
    m.px = [["_"] * 16 for _ in range(16)]
    C.silh(m, 4, [5, 6, 7, 8, 8, 8, 8, 8, 8, 7, 6, 5], 8, lambda x, y, k: "2")
    C.paste(m, 4, 0, C.G("3__33__3", "31311313", "31111113", "33333333"))
    C.paste(m, 4, 7, C.G("11111111", "13111131", "11111111", "11133111", "11311311", "_113311_", "__1111__"))
    return ["".join(r) for r in m.px]


LION = _lion()


def gate(c, g):
    """option 1's gate: pillars at x g and g + 48, the ZOO board and the iron gate between (x g + 16 to g + 47)"""
    for px in (g, g + 48):
        C.paste(c, px, 8, LION)
        for x in range(px, px + 16):
            c.px[24][x] = "3"
            c.px[25][x] = "1"
            c.px[26][x] = "1"
            c.px[27][x] = "3"
            for y in range(28, 60):
                c.px[y][x] = STONE[y % 8][x % 8]
            c.px[60][x] = "3"
            c.px[61][x] = "2"
            c.px[62][x] = "2"
            c.px[63][x] = "3"
        for y in range(24, 64):
            c.px[y][px] = "3"
            c.px[y][px + 15] = "3"
            if 28 <= y < 60:
                c.px[y][px + 14] = "2"
    for y in range(28, 40):
        for x in range(g + 16, g + 48):
            c.px[y][x] = "3" if y in (28, 39) or x in (g + 16, g + 47) else "1"
    for k, ch in enumerate("ZOO"):
        for j, r in enumerate(v_zoo.LET[ch]):
            for i, v in enumerate(r):
                if v == "1":
                    c.px[30 + j][g + 22 + k * 7 + i] = "3"
    for y in range(40, 60):
        for x in range(g + 16, g + 48):
            c.px[y][x] = "3" if ((x - g) % 4) == 1 else "0"
    for x in range(g + 16, g + 48):
        c.px[40][x] = "3"
        c.px[41][x] = "2"
        c.px[50][x] = "3"
        c.px[58][x] = "3"
    for y in range(40, 60):
        c.px[y][g + 31] = "3"
        c.px[y][g + 32] = "3"


def giraffe(c, x, head_y):
    """a spotted giraffe looking over a rail fence: head typed 12 x 9 at (x - 2, head_y), the neck column on the 8 px grid at x (8 wide), the fence at y 48 to 55"""
    C.paste(c, x - 2, head_y, GHEAD)
    for y in range(head_y + 9, 48):
        for i in range(8):
            c.px[y][x + i] = NECK[y % 8][i]


def fence(c, x0, x1):
    for y in range(48, 56):
        for x in range(x0, x1):
            c.px[y][x] = FENCE[y % 8][x % 8]


def bamboo(c, cols, tops):
    """stalks on whole cell columns (8 px), each with a tuft of leaves on top"""
    for col, top in zip(cols, tops):
        for y in range(top, 56):
            for i in range(8):
                c.px[y][col * 8 + i] = BAMBOO[y % 8][i]
        C.paste(c, col * 8, top - 5, TUFT)


# ---- round 3: a THINNER giraffe neck (the owner: "thinner giraffe neck").  The neck was 8 px wide (6 inside); now 4 wide (2 inside) under the head, widening to 6 wide (4 inside)
# for the last cell row above the fence.  Typed 8-px period rows ('0' = ground at the sides), so each neck section is one tile.
NECK4 = ["00311300", "00322300", "00322300", "00311300", "00311300", "00321300", "00312300", "00311300"]
NECK6 = ["03111130", "03122130", "03122130", "03111130", "03111130", "03111230", "03112230", "03111130"]


def giraffe3(c, x, head_y):
    """the same head (12 x 9 at (x - 2, head_y)), a neck 4 wide down to y 39, 6 wide from y 40 to the fence at y 48"""
    C.paste(c, x - 2, head_y, GHEAD)
    for y in range(head_y + 9, 48):
        row = NECK4[y % 8] if y < 40 else NECK6[y % 8]
        for i in range(8):
            c.px[y][x + i] = row[i]
