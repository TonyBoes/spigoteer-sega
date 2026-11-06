"""CHROME COW option 1, "Chrome diner", 96 x 64. Palette COW: 0 meadow, 1 chrome, 2 pink neon, 3 purple-black.  Light from the top left.
A streamlined chrome milk-bar diner (a barrel roof, a MILK BAR board in chrome letters on black, a ribbon of pink-glass windows that is one 8 px
pattern, a pink-glass double door, a checker lip) with the neon cow in sunglasses on a tall pylon beside it, and two bikes parked in front."""
import common as C
from canvas import Canvas
import v_cow

W, H = 96, 72
BIOME, AT = 'farm', (39, 22)

LET = {"M": ["10001", "11011", "10101", "10001", "10001"], "I": ["111", "010", "010", "010", "111"], "L": ["100", "100", "100", "100", "111"],
       "K": ["101", "101", "110", "101", "101"], "B": ["110", "101", "110", "101", "110"], "A": ["010", "101", "111", "101", "101"],
       "R": ["110", "101", "110", "101", "101"]}
ROOF = [22, 26, 28, 29, 30, 31, 32, 32]                       # half widths of the barrel roof, y 24 to 31
PANE = ["33333333", "22222233", "22222233", "21222233", "22122233", "22212233", "22222233", "22222233"]      # one pane and its mullion, 8 x 8 (period 8)
DOORD = C.G("3333333333333333", ("3222222332222223", 4), ("3222221331222223", 2), ("3222222332222223", 3), "3333333333333333",
            ("3111111331111113", 4), "3333333333333333")


def build():
    c = Canvas("cow1", "cow", W, H)
    # ---- the pylon: a board with today's neon cow, a pole, a foot ----
    for x in range(0, 32):
        c.px[0][x] = "3"
        c.px[15][x] = "3"
        for y in (1, 14):
            c.px[y][x] = "3" if x in (0, 31) else "1"
    for k, r in enumerate(v_cow.head()):
        row = "3" + "1" + "22" + r + "22" + "1" + "3"
        for i, ch in enumerate(row):
            c.px[2 + k][i] = ch
    for y in range(16, 54):
        for i, ch in enumerate("3113"):
            c.px[y][14 + i] = ch
    for y, row in ((54, "3333333333"), (55, "3111111113")):
        for i, ch in enumerate(row):
            c.px[y][11 + i] = ch
    # ---- the roof: a chrome barrel ----
    C.silh(c, 24, ROOF, 64, lambda x, y, k: "1")
    for x in range(32, 96):
        c.px[31][x] = "3"
    # ---- the MILK BAR board ----
    for y in range(32, 40):
        for x in range(32, 96):
            c.px[y][x] = "3"
    for x in range(34, 94):
        c.px[32][x] = "2"
    text = "MILK BAR"
    x = 48
    for ch in text:
        if ch == " ":
            x += 3
            continue
        for j, r in enumerate(LET[ch]):
            for i, v in enumerate(r):
                if v == "1":
                    c.px[34 + j][x + i] = "1"
        x += len(LET[ch][0]) + 1
    # ---- the body: chrome, a ribbon of windows, the door ----
    for y in range(40, 56):
        for x in range(32, 96):
            c.px[y][x] = "1"
        c.px[y][32] = "3"
        c.px[y][95] = "3"
    for x in range(32, 96):
        c.px[40][x] = "3"
        c.px[41][x] = "2"
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
    C.paste(c, 18, 58, v_cow.COW)
    for bx in (40, 64):
        C.paste(c, bx, 58, v_cow.bike(v_cow.BIKE_BASE))
        C.paste(c, bx, 63, v_cow.WHEEL)
        C.paste(c, bx + 13, 63, v_cow.WHEEL)
    return c
