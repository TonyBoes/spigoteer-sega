"""STADIUM option A, "Ballpark wedge", 96 x 80 (12 x 10 cells).  Palettes STADIUM (stands and light masts, cells listed in STANDS and MASTS) and PARK (the field): see park_parts.
No scoreboard anywhere.  What reads: a grass wedge between two foul lines running up from home plate, an infield (dirt base paths in a diamond, three chalk bases, a
mound, home plate) and the outfield wall with a band of navy bleachers and red wall behind it, stepped in whole cells, two floodlight masts.
The grass is cut by the foul lines (typed runs of 2 rows per 3 columns); the stands are typed 8 x 8 cells."""
import common as C
import kit as K
import park_parts as PP
from canvas import Canvas

W, H = 96, 80
BIOME, AT = 'paved', (3, 5)
UNMERGE = True

TOPS = {3: 1, 4: 1, 5: 1, 6: 1, 7: 1, 8: 1, 1: 2, 2: 2, 9: 2, 10: 2, 0: 3, 11: 3}        # column -> the row of its valance cell; the wall cell is the next row
LEFT_EDGE = {(3, 1), (1, 2), (0, 3), (0, 4), (9, 3), (11, 4)}
RIGHT_EDGE = {(8, 1), (10, 2), (11, 3), (11, 4), (2, 3), (0, 4)}
GRASS_FROM = {0: 40, 1: 32, 2: 32, 3: 24, 4: 24, 5: 24, 6: 24, 7: 24, 8: 24, 9: 32, 10: 32, 11: 40}      # per cell column, the first grass row (px)


MAST3 = ["00023000"] * 8                      # the light tower's pole with a lit (navy) left side and an ink right side


def build():
    c = Canvas("parkA3", "park", W, H)
    # ---- stands and masts (STADIUM cells) ----
    for col, r in TOPS.items():
        for row, tile in ((r, PP.TOP), (r + 1, PP.WALL)):
            PP.cell(c, col, row, tile, (col, row) in LEFT_EDGE, (col, row) in RIGHT_EDGE)
            c.palrect(col * 8, row * 8, col * 8 + 8, row * 8 + 8, "stadium")
    for col in (0, 11):
        PP.cell(c, col, 0, PP.MAST_HEAD)
        PP.cell(c, col, 1, MAST3)
        PP.cell(c, col, 2, MAST3)
        for row in range(3):
            c.palrect(col * 8, row * 8, col * 8 + 8, row * 8 + 8, "stadium")
    # ---- the grass wedge, round 3: ONE straight foul line per side, 1 row per 2 columns like the base paths, and lying ON the home-to-first and home-to-third paths (their lower row
    # is the line), so the line and the diamond share one slope.  yb(x) = the lower row of the path: left 57 + (x - 23) // 2, right 69 - (x - 47) // 2.  Grass above, a 2 px dirt line on it.
    foul = {}
    for x in range(0, 48):
        foul[x] = 57 + (x - 23) // 2
    for x in range(48, 96):
        foul[x] = 69 - (x - 47) // 2
    for x in range(96):
        K.vl(c, x, GRASS_FROM[x // 8], foul[x] - 1, "1")
        K.vl(c, x, foul[x] - 1, foul[x] + 1, "2")                               # the dirt line along the foul line, 2 px like the paths
    # ---- the infield: four base paths 3 px thick (1 row per 2 columns), a dirt disc at home, one at the mound, a dirt patch under each base ----
    PP.stroke(c, 48, 68, 24, (-1, 0), 2, "2")          # home to first
    PP.stroke(c, 48, 44, 24, (1, 0), 2, "2")           # second to first
    PP.stroke(c, 24, 56, 24, (1, 0), 2, "2")           # third to home
    PP.stroke(c, 24, 56, 24, (-1, 0), 2, "2")          # third to second
    # the dirt apron round home plate, rounded behind the plate (typed: first column and width per row, y 63 to 71)
    PP.rows_at(c, 0, 63, [(44, 8), (41, 14), (39, 18), (38, 20), (38, 20), (39, 18), (40, 16), (42, 12), (45, 6)], "2")
    PP.rows_at(c, 44, 53, [(1, 6), (0, 8), (0, 8), (0, 8), (1, 6)], "2")
    for (bx, by) in ((69, 54), (20, 54), (44, 41)):
        PP.rows_at(c, bx, by, [(1, 5), (0, 7), (0, 7), (0, 7), (1, 5)], "2")
    PP.base(c, 71, 55)
    PP.base(c, 23, 55)
    PP.base(c, 47, 42)
    PP.plate(c, 46, 65)
    for (tx, ty) in ((10, 35), (34, 27), (58, 27), (82, 35), (34, 43), (58, 43)):          # tufts, typed, all on one phase of the 8 px grid (the same tile each)
        for (dx, dy) in ((2, 0), (0, 1), (2, 1), (4, 1), (1, 2), (2, 2), (3, 2)):
            if c.px[ty + dy][tx + dx] == "1":
                c.px[ty + dy][tx + dx] = "2"
    K.hl(c, 55, 47, 50, "0")
    return c
