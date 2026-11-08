"""CHROME COW variation B, "Slant roof", 96 x 72. Palette COW: 0 meadow, 1 chrome, 2 pink neon, 3 purple-black.  Light from the top left.
Option 1's diner with a different roof and sign: a Googie shed roof climbing to the right in five 16 px steps (a chrome slab with a pink neon underside),
the neon cow board perched on the high end (no pole), the MILK BAR board as a straight black band under it, the pink double door at the LEFT, the ribbon of
pink-glass windows on the right, the checker lip, two bikes and the cow in front."""
import common as C
import kit as K
from canvas import Canvas
import v_cow

W, H = 96, 72
BIOME, AT = 'farm', (39, 22)

PANE = ["33333333", "22222233", "22222233", "21222233", "22122233", "22212233", "22222233", "22222233"]       # one pane and its mullion (period 8)
DOOR = C.G("3333333333333333", ("3222222332222223", 3), ("3222221331222223", 2), ("3222222332222223", 2), ("3111111331111113", 3), "3333333333333333")
TOPS = [30, 28, 26, 24, 22]                    # the slab's top row in each 16 px block, x 8 to 88


def build():
    c = Canvas("cowB", "cow", W, H)
    # ---- the neon board on the high end of the roof, two struts down to the slab ----
    K.box(c, 56, 4, 88, 20, "3", "1")
    for k, r in enumerate(v_cow.head()):
        row = "3" + "1" + "22" + r + "22" + "1" + "3"
        for i, ch in enumerate(row):
            c.px[6 + k][56 + i] = ch
    K.rect(c, 60, 20, 62, 24, "3")
    K.rect(c, 82, 20, 84, 22, "3")
    # ---- the slab: ink top, two chrome rows, pink underside, ink bottom; a 2 px riser at each step; the wall under it ----
    for b, t in enumerate(TOPS):
        x0 = 8 + 16 * b
        K.hl(c, t, x0, x0 + 16, "3")
        K.hl(c, t + 1, x0, x0 + 16, "1")
        K.hl(c, t + 2, x0, x0 + 16, "1")
        K.hl(c, t + 3, x0, x0 + 16, "2")
        K.hl(c, t + 4, x0, x0 + 16, "3")
        if b > 0:
            K.vl(c, x0, t, t + 3, "3")
        for y in range(t + 5, 35):
            for x in range(x0, x0 + 16):
                c.px[y][x] = "2" if x % 8 == 4 and y > t + 5 else "1"
    K.vl(c, 8, 30, 35, "3")
    K.vl(c, 87, 22, 35, "3")
    # ---- the MILK BAR band ----
    K.rect(c, 8, 35, 88, 44, "3")
    K.hl(c, 35, 8, 88, "2")
    K.hl(c, 43, 8, 88, "2")
    K.text(c, 8 + (80 - K.width("MILK BAR")) // 2, 37, "MILK BAR", "1")
    # ---- the window ribbon (right), the checker lip, the pink double door (left) ----
    for x in range(24, 88):
        for j in range(8):
            c.px[44 + j][x] = PANE[j][x % 8]
        c.px[52][x] = "3"
        c.px[53][x] = "1"
        c.px[54][x] = "1"
        c.px[55][x] = "3" if (x % 8) < 4 else "1"
    K.vl(c, 87, 44, 56, "3")
    for j, r in enumerate(DOOR):
        for i, ch in enumerate(r):
            c.px[44 + j][8 + i] = ch
    # ---- the cow and the bikes ----
    C.paste(c, 8, 58, v_cow.COW)
    for bx in (40, 64):
        C.paste(c, bx, 58, v_cow.bike(v_cow.BIKE_BASE))
        C.paste(c, bx, 63, v_cow.WHEEL)
        C.paste(c, bx + 13, 63, v_cow.WHEEL)
    return c
