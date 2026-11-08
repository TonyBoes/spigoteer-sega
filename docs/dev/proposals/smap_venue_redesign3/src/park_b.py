"""STADIUM option B, "Ballpark bowl", 96 x 88 (12 x 11 cells).  Palettes STADIUM (the ring: bleachers on three sides, the front wall with a small gate, two floodlight masts)
and PARK (the field, cells x 1-10, y 3-9): see park_parts.  No scoreboard.  What reads: a rectangle of stands around a mown field with a dirt track along its walls,
chalk foul lines running from home plate to the side stands, the infield diamond (dirt base paths, three chalk bases, a mound, home plate).
The ring is typed 8 x 8 cells (few tiles); the field is typed strokes and discs, the same infield as option A."""
import common as C
import kit as K
import park_parts as PP
from canvas import Canvas

W, H = 96, 88
BIOME, AT = 'paved', (3, 5)
UNMERGE = True

FR = ["33333333", "11111111", "11111111", "22222222", "22222222", "22222222", "22222222", "33333333"]
GL = ["33333333", "11111111", "11111111", "22233333", "22233333", "22233333", "22233333", "33333333"]
GR = ["33333333", "11111111", "11111111", "33333222", "33333222", "33333222", "33333222", "33333333"]


def stadium_cell(c, cx, cy, rows, le=False, re=False):
    PP.cell(c, cx, cy, rows, le, re)
    c.palrect(cx * 8, cy * 8, cx * 8 + 8, cy * 8 + 8, "stadium")


def build():
    c = Canvas("parkB", "park", W, H)
    # ---- the ring ----
    for col in range(12):
        stadium_cell(c, col, 1, PP.TOP, col == 0, col == 11)
        stadium_cell(c, col, 2, PP.WALL, col == 0, col == 11)
        stadium_cell(c, col, 10, FR if col not in (5, 6) else (GL if col == 5 else GR), col == 0, col == 11)
    for row in range(3, 10):
        stadium_cell(c, 0, row, PP.SEAT, True, True)
        stadium_cell(c, 11, row, PP.SEAT, True, True)
    for col in (0, 11):
        stadium_cell(c, col, 0, PP.MAST_HEAD)
    # ---- the field: grass, a dirt track along the walls, chalk foul lines ----
    K.rect(c, 8, 24, 88, 80, "1")
    K.rect(c, 8, 24, 88, 26, "2")
    K.rect(c, 8, 78, 88, 80, "2")
    K.rect(c, 8, 24, 10, 80, "2")
    K.rect(c, 86, 24, 88, 80, "2")
    PP.stroke(c, 48, 73, 38, (-1, -1, 0), 1, "0", over="1")        # the right foul line, up and right from home
    PP.stroke(c, 10, 48, 38, (1, 1, 0), 1, "0", over="1")          # the left foul line, down and right to home
    # ---- the infield, as option A ----
    PP.stroke(c, 48, 68, 24, (-1, 0), 2, "2")
    PP.stroke(c, 48, 44, 24, (1, 0), 2, "2")
    PP.stroke(c, 24, 56, 24, (1, 0), 2, "2")
    PP.stroke(c, 24, 56, 24, (-1, 0), 2, "2")
    PP.rows_at(c, 41, 63, [(4, 6), (2, 10), (1, 12), (1, 12), (2, 10), (4, 6)], "2")
    PP.rows_at(c, 44, 53, [(1, 6), (0, 8), (0, 8), (0, 8), (1, 6)], "2")
    for (bx, by) in ((69, 54), (20, 54), (44, 41)):
        PP.rows_at(c, bx, by, [(1, 5), (0, 7), (0, 7), (0, 7), (1, 5)], "2")
    PP.base(c, 71, 55)
    PP.base(c, 23, 55)
    PP.base(c, 47, 42)
    PP.plate(c, 46, 65)
    K.hl(c, 55, 47, 50, "0")
    for (tx, ty) in ((18, 27), (34, 27), (58, 27), (74, 27), (26, 35), (66, 35)):          # tufts, typed, all on one phase of the 8 px grid
        for (dx, dy) in ((2, 0), (0, 1), (2, 1), (4, 1), (1, 2), (2, 2), (3, 2)):
            if c.px[ty + dy][tx + dx] == "1":
                c.px[ty + dy][tx + dx] = "2"
    return c
