"""STADIUM round 4, OPTION 2 "Curved bowl with bunting": an open bowl (no roof).  The back wall's coping runs along a smooth arch (typed run lengths 12, 6, 5, 4, 3, 3, 2, 2, 1, 1, 1 on each
side, shrinking toward the ends like the curve rule), a white coping, a navy back wall with a string of red and white pennants hanging along it (the pennants follow the curve),
then the tiers, whose rails curve with the arch (rows are counted from the coping, not from the ground), then the red outfield wall.  Field and masts: round 3 (field.py).
Typed here: SEAT8 (crowd tile), BACK (the 8 back-wall rows incl. the bunting, x mod 8), the arch's run lengths; a loop only copies my typed rows into place."""
import common as C
import field as F
import park_parts as PP
from canvas import Canvas

W, H = F.W, F.H
BIOME, AT = F.BIOME, F.AT
UNMERGE = True

# back wall, typed (x mod 8): coping edge, coping top, cornice, ink string, bunting row (white flag x0-2, red flag x4-6), bunting tip row, navy wall, ink base
BACK = ["33333333", "00000000", "33333333"]
FLAGS = (["20000022", "22000222", "22202222"], ["21111122", "22111222", "22212222"])      # a hanging pennant 5 wide, 3 tall: white in even cells, red in odd cells
TAIL = ["33333333"]
PLAIN = ["22222222", "22222222", "22222222"]
# the crowd tile counted from the coping: riser, heads, shirts, rail, riser, heads (shifted), shirts, rail
SEAT8 = ["22222222", "22022212", "22122202", "11111111", "22222222", "02221222", "12220222", "11111111"]

# the arch's roof row per column: (first x, last x, y), typed outward from the middle, left half and right half separately
LEFT = [(36, 47, 6), (30, 35, 7), (25, 29, 8), (21, 24, 9), (18, 20, 10), (15, 17, 11), (13, 14, 12), (11, 12, 13), (10, 10, 14), (9, 9, 15), (8, 8, 16)]
RIGHT = [(48, 59, 6), (60, 65, 7), (66, 70, 8), (71, 74, 9), (75, 77, 10), (78, 80, 11), (81, 82, 12), (83, 84, 13), (85, 85, 14), (86, 86, 15), (87, 87, 16)]
OUTER = [(0, 7, 24), (88, 95, 24)]
B_RUNS = [(0, 8, 40), (8, 24, 32), (24, 72, 24), (72, 88, 32), (88, 96, 40)]
ENDS = ((0, 24, 40), (8, 16, 32), (87, 16, 32), (95, 24, 40))


FLAG = ["333333333", "311111113", "300000003", "333333333"]      # the big flag on the arch top, 9 x 4, ink pole at x 47
FLAGX = 47
PLAIN_X = tuple(range(8, 15)) + tuple(range(81, 88))      # steep wing columns: plain wall, no pennants (clean-up)


def stands(c, bunting=True):
    yt, b = [None] * 96, [None] * 96
    for x0, x1, y in LEFT + RIGHT + OUTER:
        for x in range(x0, x1 + 1):
            yt[x] = y
    for x0, x1, v in B_RUNS:
        for x in range(x0, x1):
            b[x] = v
    for x in range(96):
        t, base = yt[x], b[x]
        for y in range(t, base):
            rel = y - t
            if rel < 3:
                v = BACK[rel][x % 8]
            elif rel < 6:
                v = (FLAGS[(x // 8) % 2] if bunting and x not in PLAIN_X else PLAIN)[rel - 3][x % 8]
            elif rel == 6:
                v = TAIL[0][x % 8]
            elif y >= base - 4:
                v = ("3", "1", "1", "3")[y - (base - 4)]
            else:
                v = SEAT8[(y - (min(t, 9) + 7)) % 8][x % 8]            # the tiers curve with the arch only down to row 9, then run level
            c.px[y][x] = v
    for x, y0, y1 in ENDS:
        for y in range(y0, y1):
            c.px[y][x] = "3"
    if bunting:
        for y in range(0, 6):
            c.px[y][FLAGX] = "3"
        for j, row in enumerate(FLAG):
            for i, ch in enumerate(row):
                c.px[j][FLAGX + i] = ch
    for col in (0, 11):
        PP.cell(c, col, 0, PP.MAST_HEAD)
        PP.cell(c, col, 1, ["00023000"] * 8)
        PP.cell(c, col, 2, ["00023000"] * 8)


def finish(c):
    keep = list(c.rects)
    c.rects = []
    for cx in range(W // 8):
        for cy in range(H // 8):
            if cy * 8 < F.GRASS_FROM[cx]:
                c.palrect(cx * 8, cy * 8, cx * 8 + 8, cy * 8 + 8, "stadium")
    c.rects += keep


def build(bunting=True):
    c = Canvas("parkS2", "park", W, H)
    F.field(c)
    stands(c, bunting)
    finish(c)
    return c
