"""CHROME COW variation C, "Bottle sign", 96 x 72. Palette COW: 0 meadow, 1 chrome, 2 pink neon, 3 purple-black.  Light from the top left.
Option 1's diner with a different sign, nose and trim: a bullet-nosed chrome diner (rounded left end, a rocket tail fin at the right end of the roof, a
chrome belt line), a pole sign that is a giant MILK BOTTLE (pink cap, chrome glass, pink label with cow spots) instead of the cow board, the black MILK BAR
band, a ribbon of pink-glass windows, the pink double door, two bikes and the cow in front."""
import common as C
import kit as K
from canvas import Canvas
import v_cow

W, H = 96, 72
BIOME, AT = 'farm', (39, 22)

PANE = ["33333333", "22222233", "22222233", "21222233", "22122233", "22212233", "22222233", "22222233"]
DOORD = C.G("3333333333333333", ("3222222332222223", 4), ("3222221331222223", 2), ("3222222332222223", 3), "3333333333333333", ("3111111331111113", 1))
NOSE = [8, 5, 3, 2, 1, 1, 0, 0]                      # the rounded left end: first column of each row from y 30 (typed)
BOTTLE = C.G("____33333333____", "____32222223____", "____33333333____",
             "_____311113_____", "_____311113_____", "_____311113_____",
             "____31111113____", "___3111111113___", "__311111111113__", "_31111111111113_",
             "3111111111111113", "3111111111111113",
             "3222222222222223", "3222332222222223", "3223332222233223", "3222332222333223", "3222222222332223", "3222222222222223",
             "3111111111111113", "3111111111111113", "3111111111111113",
             "_31111111111113_", "__333333333333__")
FIN = C.G("__________33", "_________313", "________3123", "_______31123", "______311123", "_____3111123", "____31111123", "___311111123")


def build():
    c = Canvas("cowC", "cow", W, H)
    # ---- the bottle on its pole ----
    C.paste(c, 80, 2, BOTTLE)
    for y in range(25, 54):
        for i, ch in enumerate("3113"):
            c.px[y][86 + i] = ch
    for y, row in ((54, "3333333333"), (55, "3111111113")):
        for i, ch in enumerate(row):
            c.px[y][83 + i] = ch
    # ---- the bullet-nosed body, x 0 to 71, y 30 to 55 ----
    for y in range(30, 56):
        L = NOSE[y - 30] if y - 30 < len(NOSE) else 0
        pl = NOSE[y - 31] if 0 < y - 30 < len(NOSE) else None
        for x in range(L, 72):
            if y == 30:
                v = "3"
            elif y in (31, 32):
                v = "1"
            elif y == 33:
                v = "2"
            elif y == 34:
                v = "3"
            elif 35 <= y <= 41:
                v = "3"
            elif y == 42:
                v = "2"
            elif 43 <= y <= 50:
                v = "1"
            else:
                v = "1"
            c.px[y][x] = v
        c.px[y][L] = "3"
        c.px[y][71] = "3"
        if y > 30 and y - 31 < len(NOSE):
            for x in range(L, NOSE[y - 31]):
                c.px[y][x] = "3"
    # ---- the tail fin ----
    C.paste(c, 60, 22, FIN)
    K.vl(c, 71, 22, 30, "3")
    K.vl(c, 70, 24, 30, "2")
    # ---- the band, the belt, the windows, the lip, the door ----
    K.text(c, 12 + (56 - K.width("MILK BAR")) // 2, 36, "MILK BAR", "1")
    for x in range(16, 56):
        for j in range(8):
            c.px[43 + j][x] = PANE[j][x % 8]
    K.hl(c, 51, 1, 72, "3")
    K.hl(c, 52, 1, 72, "1")
    for x in range(0, 72):
        c.px[53][x] = "1" if c.px[53][x] != "0" else "0"
        c.px[54][x] = "1" if c.px[54][x] != "0" else "0"
        c.px[55][x] = "3" if (x % 8) < 4 else "1"
    for j, r in enumerate(DOORD):
        for i, ch in enumerate(r):
            c.px[40 + j][56 + i] = ch
    C.paste(c, 62, 58, v_cow.COW)
    for bx in (6, 32):
        C.paste(c, bx, 58, v_cow.bike(v_cow.BIKE_BASE))
        C.paste(c, bx, 63, v_cow.WHEEL)
        C.paste(c, bx + 13, 63, v_cow.WHEEL)
    return c
