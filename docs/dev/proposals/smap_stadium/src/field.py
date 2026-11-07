"""The ballpark's FIELD, round 3 pixel for pixel (foul lines, base paths, bases, mound, tufts, plate) except the home apron, which is re-typed here (lighter on DMG).
The stands and masts are NOT here: park_s1.py and park_s2.py draw them.  Light from the top left.  Palettes: STADIUM (stands) and PARK (field); PARKHOME is PARK with a
pale sand in slot 1, used only by the cell row holding the apron (Color only; DMG is unchanged by it)."""
import common as C
import kit as K
import park_parts as PP
from canvas import Canvas
import pal as P

W, H = 96, 80
BIOME, AT = 'paved', (3, 5)
UNMERGE = True
P.RGB['parkhome'] = [P.h(x) for x in ('d4d8e4', 'e0c488', 'c09050', '101428')]

GRASS_FROM = {0: 40, 1: 32, 2: 32, 3: 24, 4: 24, 5: 24, 6: 24, 7: 24, 8: 24, 9: 32, 10: 32, 11: 40}      # per cell column, the first grass row (px)

# the new home apron, typed: y 64 to 71, x 38 to 57 (first column, then the row).  A solid dirt rim all round (it keeps the apron apart from the grass on DMG) and a
# 1/2 checker inside (shade 1 and shade 2 on DMG: lighter than the solid dirt of round 3; slot 1 is pale sand on Color).
APRON = [          # solid shade 1 (PARK slot 1) inside a 1 px dirt rim, y 64 to 71: one step lighter than round 3's solid dirt on DMG, existing palette
    (42, "222222222222"),
    (40, "2" + "1" * 14 + "2"),
    (39, "2" + "1" * 16 + "2"),
    (38, "2" + "1" * 18 + "2"),
    (38, "2" + "1" * 18 + "2"),
    (39, "2" + "1" * 16 + "2"),
    (41, "2" + "1" * 12 + "2"),
    (44, "22222222"),
]


def field(c, apron=True):
    foul = {}
    for x in range(0, 48):
        foul[x] = 57 + (x - 23) // 2
    for x in range(48, 96):
        foul[x] = 69 - (x - 47) // 2
    for x in range(96):
        K.vl(c, x, GRASS_FROM[x // 8], foul[x] - 1, "1")
        K.vl(c, x, foul[x] - 1, foul[x] + 1, "2")
    PP.stroke(c, 48, 68, 24, (-1, 0), 2, "2")
    PP.stroke(c, 48, 44, 24, (1, 0), 2, "2")
    PP.stroke(c, 24, 56, 24, (1, 0), 2, "2")
    PP.stroke(c, 24, 56, 24, (-1, 0), 2, "2")
    if apron:
        for j, (x0, row) in enumerate(APRON):
            for i, ch in enumerate(row):
                c.px[64 + j][x0 + i] = ch
    else:
        PP.rows_at(c, 0, 63, [(44, 8), (41, 14), (39, 18), (38, 20), (38, 20), (39, 18), (40, 16), (42, 12), (45, 6)], "2")
    PP.rows_at(c, 44, 53, [(1, 6), (0, 8), (0, 8), (0, 8), (1, 6)], "2")
    for (bx, by) in ((69, 54), (20, 54), (44, 41)):
        PP.rows_at(c, bx, by, [(1, 5), (0, 7), (0, 7), (0, 7), (1, 5)], "2")
    PP.base(c, 71, 55)
    PP.base(c, 23, 55)
    PP.base(c, 47, 42)
    PP.plate(c, 46, 65)
    for (tx, ty) in ((10, 35), (34, 27), (58, 27), (82, 35), (34, 43), (58, 43)):
        for (dx, dy) in ((2, 0), (0, 1), (2, 1), (4, 1), (1, 2), (2, 2), (3, 2)):
            if c.px[ty + dy][tx + dx] == "1":
                c.px[ty + dy][tx + dx] = "2"
    K.hl(c, 55, 47, 50, "0")
