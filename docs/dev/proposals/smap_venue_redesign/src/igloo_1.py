"""IGLOO option 1, "Cocoa dome", 80 x 64. Palette IGLOO: 0 snow, 1 ice, 2 deep ice, 3 ink.  Light from the top left.
A big ice-block dome in the snow: a snowy cap, a pale tunnel in front with a dark doorway under a COCOA board, two round lit windows,
a stove pipe with smoke, a lamp post and a penguin.  The ice courses are one typed 8 x 8 pattern (period 8, so one tile for the whole dome),
cut to the typed silhouette (the width list HW), as the existing igloo does."""
import common as C
from canvas import Canvas
from v_igloo import DRIFT

W, H = 80, 64
BIOME, AT = 'snow', (53, 5)

# silhouette: half width of each dome row from y = 12 (the cap) down; the dome is centred between x 39 and 40
HW = [4, 7, 9, 11, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 22, 23, 23, 24, 24, 25, 25, 25, 26, 26, 26, 26, 27, 27, 27, 27, 27, 27, 27, 27, 27, 27]
TUN = [8, 10, 11, 12] + [12] * 10                       # the tunnel, y 34 to 47
DOOR = [3, 5, 6] + [6] * 8                              # the doorway, y 37 to 47

MID = ["00000002", "11111112", "11111112", "22222222", "00020000", "11121111", "11121111", "22222222"]     # ice courses, lit top edge, joints
SHADE = ["11111113", "22222223", "22222223", "33333333", "11131111", "22232222", "22232222", "33333333"]   # the same one shade down, right side
LIT = ["00000001", "00000001", "00000001", "11111111", "00010000", "00010000", "00010000", "11111111"]     # the tunnel's pale courses

LET = {"C": ["111", "100", "100", "100", "111"], "O": ["111", "101", "101", "101", "111"], "A": ["010", "101", "111", "101", "101"]}

CHIMNEY = C.G("333333", "311223", "333333", "_3123_", *[("_3123_", 8)])
SMOKE1 = C.G("_1111_", "111111", "111112", "_2222_")
SMOKE2 = C.G("_111_", "11111", "_222_")
LAMP = C.G("___33___", "__3333__", "_333333_", "_300013_", "_300013_", "_300013_", "_333333_", ("___33___", 14))
PENGUIN = C.G("___3333___", "__333333__", "__303303__", "__331133__", "_33300333_", "_33000033_", "_33000033_", "_33000033_", "__300003__",
              "__330033__", "___3333___", "__11__11__")
PORT = C.G("__3333__", "_300003_", "30000013", "30000013", "30000113", "30001113", "_311113_", "__3333__")


def build():
    c = Canvas("igloo1", "igloo", W, H)
    C.paste(c, 49, 4, CHIMNEY)                      # the stove pipe goes in first: the dome is in front of it
    C.paste(c, 49, 0, SMOKE1)

    C.silh(c, 12, HW, 40, lambda x, y, k: "0" if k in (1, 2) else (SHADE if x >= 56 else MID)[y % 8][x % 8])
    for x in range(13, 67):
        c.px[48][x] = "3"


    # ---- the board over the tunnel ----
    for x in range(28, 52):
        c.px[24][x] = "3"
        c.px[32][x] = "3"
    for y in range(25, 32):
        for x in range(28, 52):
            c.px[y][x] = "3" if x in (28, 51) else "0"
    for k, ch in enumerate("COCOA"):
        for j, r in enumerate(LET[ch]):
            for i, v in enumerate(r):
                if v == "1":
                    c.px[26 + j][30 + k * 4 + i] = "3"
    # ---- the tunnel, the doorway ----
    C.silh(c, 34, TUN, 40, lambda x, y, k: (MID if x >= 48 else LIT)[y % 8][x % 8])
    for k, h in enumerate(DOOR):
        for x in range(40 - h, 40 + h):
            c.px[37 + k][x] = "3"
    for y in (46, 47):
        for x in range(36, 44):
            c.px[y][x] = "1"
    for x in range(28, 52):
        c.px[48][x] = "3"
    # ---- contact shadow, drifts ----
    for x in range(15, 65):
        c.px[49][x] = "1"
    for x in list(range(20, 36)) + list(range(42, 58)):
        c.px[50][x] = "1"
    C.paste(c, 0, 55, DRIFT)
    C.paste(c, 56, 55, DRIFT)

    C.paste(c, 69, 38, PENGUIN)
    return c
