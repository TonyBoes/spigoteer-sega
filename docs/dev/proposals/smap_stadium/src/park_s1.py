"""STADIUM round 4, OPTION 1 "Covered grandstand": a roofed back stand with a striped awning, a lit roof top, roof posts, tiers with lit rails and a crowd, an outfield wall in
red; the roofline steps down to the wings along a 45 degree chamfer (the angle of the stands round the infield); flagpoles with pennants stand on the roof.
Field, foul lines, masts: round 3 (field.py), except the home apron.  Everything of the stands is typed here: SEAT8 (the 8 x 8 crowd tile, typed row by row), ROOF (the 6 roof rows),
FLAGS, and the per-column numbers YT (the roof's first row) and B (the wall's last row + 1), which I typed as runs.  A loop only copies my typed rows into their places."""
import common as C
import field as F
import park_parts as PP
from canvas import Canvas

W, H = F.W, F.H
BIOME, AT = F.BIOME, F.AT
UNMERGE = True

# the crowd tile, typed: row 0 rail (lit tread), 1 riser, 2 heads, 3 shirts; 4 rail, 5 riser, 6 heads (shifted 2 px), 7 shirts.  Heads and shirts: white or red.
SEAT8 = ["11111111", "22222222", "22022212", "22122202", "11111111", "22222222", "02221222", "12220222"]
# the roof, typed per row, x mod 8: top ink edge, lit top plane, grey top plane, awning stripe, awning stripe, ink under the awning
ROOF = ["33333333", "00000000", "11111111", "11110000", "11110000", "33333333"]
FLAG_RED = ["3333", "111", "11", "1"]
FLAG_NAVY = ["3333", "222", "22", "2"]

# per column: the first row of the roof (YT) and the row after the wall (B), typed as runs (x0, x1, value).  Centre 24..71: roof at 7, wall ends at 24.  The chamfer is 1 row per column.
YT_RUNS = [(0, 8, 24), (8, 16, 15), (16, 24, None), (24, 72, 7), (72, 80, None), (80, 88, 15), (88, 96, 24)]
B_RUNS = [(0, 8, 40), (8, 24, 32), (24, 72, 24), (72, 88, 32), (88, 96, 40)]
POSTS = (40, 56)            # roof posts (2 px wide: lit column then ink)
POLES = ((8, FLAG_RED), (32, FLAG_NAVY), (48, FLAG_RED), (64, FLAG_NAVY), (80, FLAG_RED))
ENDS = ((0, 24, 40), (8, 15, 32), (87, 15, 32), (95, 24, 40))       # ink end columns (x, first y, last y + 1)


def runs(rs, w=96):
    out = [None] * w
    for x0, x1, v in rs:
        for x in range(x0, x1):
            out[x] = v
    return out


def stands(c, flags=True):
    yt, b = runs(YT_RUNS), runs(B_RUNS)
    for x in range(16, 24):
        yt[x] = 7 + (24 - x)            # the chamfer, 45 degrees: 8 columns, 8 rows
    for x in range(72, 80):
        yt[x] = 7 + (x - 71)
    for x in range(96):
        t, base = yt[x], b[x]
        for y in range(t, base):
            rel = y - t
            if rel < 6:
                v = ROOF[rel][x % 8]
            elif y >= base - 4:
                v = ("3", "1", "1", "3")[y - (base - 4)]
            else:
                v = SEAT8[y % 8][x % 8]
            c.px[y][x] = v
        if x in POSTS or x - 1 in POSTS:
            for y in range(t + 6, base - 4):
                c.px[y][x] = "0" if x in POSTS else "3"
    for x, y0, y1 in ENDS:
        for y in range(y0, y1):
            c.px[y][x] = "3"
    for px, flag in (POLES if flags else ()):
        t = yt[px]
        for y in range(t - 6, t):
            c.px[y][px] = "3"
        for j, row in enumerate(flag):
            for i, ch in enumerate(row):
                c.px[t - 6 + j][px + 1 + i] = ch
    for col in (0, 11):
        PP.cell(c, col, 0, PP.MAST_HEAD)
        PP.cell(c, col, 1, ["00023000"] * 8)
        PP.cell(c, col, 2, ["00023000"] * 8)


def finish(c):
    keep = [r for r in c.rects]
    c.rects = []
    for cx in range(W // 8):
        for cy in range(H // 8):
            if cy * 8 < F.GRASS_FROM[cx]:
                c.palrect(cx * 8, cy * 8, cx * 8 + 8, cy * 8 + 8, "stadium")
    c.rects += keep


def build(flags=True, apron=True):
    c = Canvas("parkS1", "park", W, H)
    F.field(c, apron)
    stands(c, flags)
    finish(c)
    return c
