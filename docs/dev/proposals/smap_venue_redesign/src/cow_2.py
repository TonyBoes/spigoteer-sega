"""CHROME COW option 2, "Cow-print bar", 80 x 72. Palette COW: 0 meadow, 1 chrome, 2 pink neon, 3 purple-black.  Light from the top left.
A flat-fronted biker bar wearing a cow-print wall (one typed 16 x 16 pattern: four tiles for the whole wall), the neon cow in sunglasses standing on
the roof, a chrome cornice with a pink neon trim, a MILK neon board, a pink-lit window with two punks in silhouette, double studded doors, a checker
skirt, and two bikes in front (the same typed bike twice, on the 8 px grid)."""
import common as C
from canvas import Canvas
import v_cow

W, H = 80, 72
BIOME, AT = 'farm', (39, 22)

# the cow print, 16 x 16, typed: two big blotches of ink on chrome, none touching the pattern's edge (so it repeats without seams)
PRINT = C.G("1111111111111111",
            "1113333111111111",
            "1133333331111111",
            "1333333333111111",
            "1333333331111111",
            "1133333311111111",
            "1113331111111111",
            "1111111111111111",
            "1111111111111111",
            "1111111133311111",
            "1111113333331111",
            "1111133333333111",
            "1111133333331111",
            "1111113333311111",
            "1111111133111111",
            "1111111111111111")
PUNK = C.G("3_3_3_", "_3333_", "_3333_", "_3333_", "__33__", "333333", "333333", "333333", "333333", "333333")
BIKER = C.G("_3333_", "333333", "333333", "_3333_", "__33__", "333333", "333333", "333333", "333333", "333333")
# the double door: two identical leaves of 8 x 24 (a top, a middle and a bottom tile each): ink rim, chrome inner rim, studded panel, pink kick plate
LEAF_TOP = ["33333333", "31111113", "31333313", "31313313", "31333313", "31333313", "31313313", "31333313"]
LEAF_MID = ["31333313", "31333313", "31313313", "31333313", "31333313", "31313313", "31333313", "31333313"]
LEAF_BOT = ["31333313", "31333313", "31222213", "31222213", "31333313", "31333313", "31111113", "33333333"]


def build():
    c = Canvas("cow2", "cow", W, H)
    # ---- the neon cow on the roof: a 32 wide board, the cow head of today's art on pink ----
    for x in range(24, 56):
        c.px[0][x] = "3"
        c.px[15][x] = "3"
        for y in (1, 14):
            c.px[y][x] = "3" if x in (24, 55) else "1"
    for k, r in enumerate(v_cow.head()):
        row = "3" + "1" + "22" + r + "22" + "1" + "3"
        for i, ch in enumerate(row):
            c.px[2 + k][24 + i] = ch
    # ---- the cornice ----
    for x in range(8, 72):
        c.px[16][x] = "3"
        c.px[17][x] = "1"
        c.px[18][x] = "1"
        c.px[19][x] = "3"
    # ---- the MILK board: pink neon letters 5 x 7 on the ink board, dashed pink neon rails ----
    for y in range(20, 32):
        for x in range(8, 72):
            c.px[y][x] = "3"
    for x in range(10, 70):
        c.px[20][x] = "2" if (x % 4) < 3 else "3"
        c.px[30][x] = "2" if (x % 4) < 3 else "3"
    for k, ch in enumerate("MILK"):
        x0 = 27 + [0, 7, 14, 21][k]
        for j, r in enumerate(v_cow.LET[ch]):
            for i, v in enumerate(r):
                if v == "1":
                    c.px[22 + j][x0 + i] = "2"
    # ---- the cow-print wall, three cell rows ----
    for y in range(32, 56):
        for x in range(8, 72):
            c.px[y][x] = PRINT[y % 16][x % 16]
        c.px[y][8] = "3"
        c.px[y][71] = "3"
    # ---- the window (16 x 16, two punks in silhouette on pink glass) and the double door ----
    for y in range(40, 56):
        for x in range(16, 32):
            c.px[y][x] = "3" if y == 40 or x in (16, 31) else ("1" if y == 41 or x in (17, 30) else "2")
    C.paste(c, 19, 44, PUNK)
    C.paste(c, 25, 46, BIKER)
    for lx in (48, 56):
        for j in range(8):
            for i in range(8):
                c.px[32 + j][lx + i] = LEAF_TOP[j][i]
                c.px[40 + j][lx + i] = LEAF_MID[j][i]
                c.px[48 + j][lx + i] = LEAF_BOT[j][i]
    # ---- the skirt ----
    for x in range(8, 72):
        c.px[56][x] = "3"
        c.px[57][x] = "1"
        c.px[58][x] = "1"
        c.px[59][x] = "3"
        for y in range(60, 64):
            c.px[y][x] = "3" if (x % 8) < 4 else "1"
    for y in range(56, 64):
        c.px[y][8] = "3"
        c.px[y][71] = "3"
    # ---- the bikes ----
    for bx in (16, 40):
        C.paste(c, bx, 58, v_cow.bike(v_cow.BIKE_BASE))
        C.paste(c, bx, 63, v_cow.WHEEL)
        C.paste(c, bx + 13, 63, v_cow.WHEEL)
    return c
