"""JUNGLE ZOO option 2, "Safari hut", 96 x 64.  Palettes ZOO (the bamboo, the outer cells): 0 ground, 1 leaf, 2 deep leaf, 3 ink;
ZOOGATE (the hut, the giraffe, the fence): 0 ground, 1 sand, 2 brown, 3 ink.  Light from the top left.
A thatched ticket hut with a steep 45 degree roof (the slopes are one tile each), a white ZOO board, a counter window under a striped awning and a
plank door; a spotted giraffe looking over a fence on the left; a grove of bamboo on the right.  The Color build needs ZOOGATE as its own palette."""
import common as C
from canvas import Canvas
import v_zoo

W, H = 96, 64
BIOME, AT = 'jungle', (17, 35)
UNMERGE = True

THATCH = ["12111211", "12111211", "11121112", "11121112", "12111211", "12111211", "11121112", "11121112"]
THATCH_D = ["23222322", "23222322", "22232223", "22232223", "23222322", "23222322", "22232223", "22232223"]
NECK = ["31111113", "31221113", "31221113", "31111113", "31111113", "31111223", "31111223", "31111113"]
FENCE = ["31300000", "31300000", "11111111", "33333333", "31300000", "11111111", "33333333", "31300000"]
GHEAD = C.G("___3____3___", "___3____3___", "__33333333__", "333111111333", "333131131333", "__31111113__", "__31133113__", "___311113___", "___333333___")
BAMBOO = ["00312300"] * 7 + ["03312330"]
TUFT = C.G("__3333__", "_311113_", "31112113", "_321123_", "__3123__")
DOORP = ["33333333", "32222223", "32222223", "32222223", "32122223", "32222223", "32222223", "32222223"]


def build():
    c = Canvas("zoo2", "zoo", W, H)
    c.palrect(0, 0, 72, 64, "zoogate")
    # ---- the thatched roof: a 45 degree peak, lit left, shaded right ----
    C.silh(c, 0, [4 + k for k in range(24)], 48, lambda x, y, k: (THATCH_D if x >= 56 else THATCH)[y % 8][x % 8])
    # ---- the eave's fringe, the wall of planks ----
    for y in range(24, 56):
        for x in range(24, 72):
            c.px[y][x] = "3" if x in (24, 71) else ("11121112"[x % 8] if x < 64 else "22232223"[x % 8])
    for x in range(21, 75):
        c.px[24][x] = "3" if (x % 4) < 2 else ("2" if 24 <= x < 72 else "0")
    for x in range(24, 72):
        c.px[56][x] = "3"
    # ---- the board, white with ink letters, on two ropes ----
    for y in range(26, 38):
        for x in range(32, 64):
            c.px[y][x] = "3" if y in (26, 37) or x in (32, 63) else "0"
    for k, ch in enumerate("ZOO"):
        for j, r in enumerate(v_zoo.LET[ch]):
            for i, v in enumerate(r):
                if v == "1":
                    c.px[28 + j][38 + k * 7 + i] = "3"
    # ---- the counter window with its awning, the door ----
    for y in range(40, 56):
        for x in range(32, 48):
            if y == 40 or y == 43 or 44 <= y <= 49 or y == 51:
                v = "3"
            elif y <= 42:
                v = "2" if (x % 8) < 4 else "1"
            elif y == 50:
                v = "1"
            else:
                v = "11121112"[x % 8]
            c.px[y][x] = v
        if y >= 43:
            c.px[y][32] = "3"
            c.px[y][47] = "3"
    for x in range(34, 46):
        c.px[48][x] = "2"
        c.px[49][x] = "2"
    for j, r in enumerate(DOORP + DOORP):
        for i, ch in enumerate(r):
            c.px[40 + j][56 + i] = ch
    # ---- the giraffe over the fence ----
    C.paste(c, 6, 10, GHEAD)
    for y in range(19, 48):
        for x in range(8, 16):
            c.px[y][x] = NECK[y % 8][x % 8]
    for y in range(48, 56):
        for x in range(0, 24):
            if c.px[y][x] == "0" or True:
                c.px[y][x] = FENCE[y % 8][x % 8]
    # ---- bamboo ----
    for col, top in ((9, 12), (10, 20), (11, 8)):
        for y in range(top, 56):
            for x in range(col * 8, col * 8 + 8):
                c.px[y][x] = BAMBOO[y % 8][x % 8]
        C.paste(c, col * 8, top - 4, TUFT)
    return c
