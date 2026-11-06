"""JUNGLE ZOO option 1, "Lion gate", 96 x 64.  Palettes ZOO (the trees, the outer 16 columns each side): 0 ground, 1 leaf, 2 deep leaf, 3 ink;
ZOOGATE (the gate, cells x 16 to 79): 0 ground, 1 sand stone, 2 brown, 3 ink.  Light from the top left.
Two stone pillars (one typed 16 x 8 block pattern, so each pillar is two tiles), each crowned with a crowned lion's head (Leo), a wooden ZOO board
hung between them over an iron gate, a jungle tree and a bush with eyes at each side.  The Color build needs ZOOGATE kept as its own palette."""
import common as C
from canvas import Canvas
import v_zoo

W, H = 96, 64
BIOME, AT = 'jungle', (17, 35)
UNMERGE = True

STONE = ["11111112", "11111112", "11111112", "22222222", "11211111", "11211111", "11211111", "22222222"]


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


def build():
    c = Canvas("zoo1", "zoo", W, H)
    c.palrect(16, 0, 80, 64, "zoogate")
    for px in (16, 64):
        # the lion on the pillar, the cap, the shaft of blocks, the plinth
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
    # ---- the board between the pillars ----
    for y in range(28, 40):
        for x in range(32, 64):
            c.px[y][x] = "3" if y in (28, 39) or x in (32, 63) else "1"
    for k, ch in enumerate("ZOO"):
        for j, r in enumerate(v_zoo.LET[ch]):
            for i, v in enumerate(r):
                if v == "1":
                    c.px[30 + j][38 + k * 7 + i] = "3"
    # ---- the iron gate: a lintel, bars every four pixels, two crossbars, the centre seam ----
    for y in range(40, 60):
        for x in range(32, 64):
            c.px[y][x] = "3" if (x % 4) == 1 else "0"
    for x in range(32, 64):
        c.px[40][x] = "3"
        c.px[41][x] = "2"
        c.px[50][x] = "3"
        c.px[58][x] = "3"
    for y in range(40, 60):
        c.px[y][47] = "3"
        c.px[y][48] = "3"
    # ---- a jungle tree and a bush with eyes at each side ----
    for tx in (0, 80):
        C.paste(c, tx, 24, v_zoo.CANOPY)
        C.paste(c, tx, 34, v_zoo.TRUNK)
        C.paste(c, tx, 48, v_zoo.CANOPY)
        C.paste(c, tx + 5, 52, v_zoo.EYES)
    return c
