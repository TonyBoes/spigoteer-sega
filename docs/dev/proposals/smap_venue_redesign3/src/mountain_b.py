"""SPACE LOUNGE MOUNTAIN version B, "Twin summits, a long range", 216 x 80 (27 x 10 cells): the mountain is cells 5 to 26 (22 cells = 176 px wide), the base cells 0 to 4
at its LEFT, a tiny airstrip under the base (cells 0 to 4, row 9).  Palette SALOON: 0 sand, 1 lit rock, 2 shaded rock, 3 ink (BASE for the base and the strip).
Option 2's twin summits on one massif: the tall summit (snowcap, a shoulder on its left flank) and a lower one beside it over a saddle, a hump at each end of the
range.  One typed skyline for the whole range, a crease and a snowcap per summit, a few gullies, strata every 8 rows."""
import common as C
import kit as K
import mtn_massif as MM
import mtn_strata as S
import space_base as SB
from canvas import Canvas

W, H = 216, 80
BIOME, AT = 'desert', (1, 34)
REGION = (0, 0, 26, 9)
YF = 71

SEGS = [(5, -1), (2, -2), (1, 0), (3, -1), (2, -2), (2, -1), (2, -2), (1, -1, "S1"),                                       # the near hump, up
        (2, 1), (1, 0), (3, 2), (2, 1), (2, 2), (3, 1), (1, 2, "V1"),                                                    # and down to the first saddle
        (4, -1), (2, -2), (3, -1), (1, 0), (2, -3), (5, [0, -1, 0, 0, -1]), (3, -2), (2, -3), (2, -1), (3, -2), (1, 0), (2, -3), (2, -1), (3, -2), (2, -1), (1, -2, "A"),
        (2, 0), (2, 2), (2, 1), (3, 3), (1, 0), (3, 2), (2, 1), (3, 3), (2, 1), (1, 1, "V2"),                              # the tall summit and down to the saddle
        (3, -1), (2, -2), (1, 0), (3, -1), (2, -1), (2, -2), (1, 0), (3, -1), (1, -1), (1, -1, "B"),                        # the second summit
        (2, 0), (3, 2), (2, 1), (4, 2), (1, 0), (3, 1), (2, 3), (4, [0, 1]), (3, 2), (4, 3), (3, 2)]
SUMMITS = [dict(x="S1", saddle="V1", crease=[(8, [0, 1]), (30, 0)], rim=4),
           dict(x="A", saddle="V2", crease=[(10, [0, 1]), (10, 0), (16, [0, 1]), (40, 0)], ink_crease_rows=20, rim=20,
                cap=("A", -10, 30, [(2, 1), (2, -1), (2, 1), (2, -1), (2, 1), (2, -1), (2, 1), (2, -1), (2, 1), (2, -1), (2, 1), (2, -1), (2, 1), (2, -1), (2, 0)])),
           dict(x="B", crease=[(8, [0, 1]), (10, 0), (30, [0, 0, 1])], ink_crease_rows=9, rim=10,
                cap=("B", -7, 31, [(2, 1), (2, -1), (2, 1), (2, -1), (2, 1), (2, -1), (2, 1), (2, -1), (1, 0)]))]
HUMP = [(5, -1), (2, -2), (1, 0), (3, -1), (2, -2), (2, -1, "S2"), (3, 1), (2, 2), (1, 0), (3, 2), (2, 3), (2, 3)]


def mountain(c):
    top, labs = MM.massif(c, YF, 40, 72, SEGS, SUMMITS, gullies=[(92, 60, [(10, [-1, 0]), (6, -1)], "2", 2), (122, 38, [(12, [0, 1]), (14, [1, 0])], "3", 1)])
    MM.massif(c, YF, 186, 72, HUMP, [dict(x="S2", crease=[(8, [0, 1]), (30, 0)], rim=6)], verbose=True)
    S.strata(c, {34: ".........c.a.b...S.b.........", 42: "......a.b..a.c.S..b.c.........", 50: "...a.b..c.a..b.S.a.b.c.", 58: ".a.c.a.b.c.b.a.S.b.a.c.b", 66: "b.a.c.b.a.c.b.a.S.c.b.a."}, 40)
    for (x, y, v) in CLEANUP:
        c.px[y][x] = v
    return top


CLEANUP = [(119, 26, '0'), (98, 29, '0'), (143, 30, '0'), (114, 31, '2'), (154, 31, '0'), (154, 32, '2'), (155, 32, '0'), (155, 33, '2'), (156, 33, '0'), (135, 39, '0'), (60, 51, '0'),
           (206, 61, '0'), (46, 63, '0'), (192, 63, '0'), (41, 71, '0'), (187, 71, '0')]      # the corner pixel of each L-shaped double (lint), typed by hand


def build():
    c = Canvas("mountainB", "saloon", W, H)
    c.palrect(0, 0, 40, 80, "base")
    mountain(c)
    SB.dome(c, 2, YF)
    SB.tower(c, 30, YF)
    # a tiny airstrip in front of the base: edge lines, navy runway, a dashed centre line (cell row 9)
    K.hl(c, 73, 0, 40, "3")
    K.rect(c, 0, 74, 40, 78, "2")
    K.hl(c, 75, 0, 40, "2")
    for x in range(0, 40):
        if (x % 8) < 4:
            c.px[76][x] = "0"
    K.hl(c, 78, 0, 40, "3")
    return c
