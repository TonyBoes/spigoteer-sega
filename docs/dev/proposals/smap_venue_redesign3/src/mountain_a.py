"""SPACE LOUNGE MOUNTAIN version A, "Three peaks", 200 x 72 (25 x 9 cells): the mountain is cells 7 to 24 (18 cells = 144 px wide), the base is cells 0 to 6 at its LEFT.
Palette SALOON: 0 sand, 1 lit rock, 2 shaded rock, 3 ink (BASE for the base's cells).  Light from the top left.
A tall main peak with a crowned summit, a shoulder on each flank and a snowcap (the lightest value, a ragged lower edge), a lower peak behind it at the left and a
second behind it at the right; every skyline is typed run by run, each lit face is left of its crease, strata dashes every 8 rows, a few gullies."""
import common as C
import mtn_kit as M
import mtn_strata as S
import space_base as SB
from canvas import Canvas

W, H = 200, 72
BIOME, AT = 'desert', (1, 34)
REGION = (0, 0, 24, 8)
YF = 63
FOOT = "33333323"


def mountain(c, x_clip=None):
    # P3, the lower peak behind at the left (apex x 84)
    M.peak(c, YF, (56, 64, [(3, -1), (2, -3), (2, 0), (3, -1), (2, -2), (4, [0, -1, 0, -1]), (3, -3), (2, -1), (3, -2), (2, [-1, 0]), (2, 0)]), (84, 27),
           [(1, 0), (2, 2), (2, 3), (1, 0), (3, 1), (3, 3), (3, 2), (4, [1, 2]), (3, 3), (3, 3), (3, 3)],
           (84, [(9, [0, 1]), (12, 0), (50, [0, 0, 1])]), rim_rows=12, ink_crease_rows=9, foot_ink=FOOT,
           gullies=[(78, 40, [(6, -1), (14, [0, -1, 0, 0, -1])], "2", 2)], x_clip=x_clip)
    # P2, the second peak behind at the right (apex x 180)
    M.peak(c, YF, (140, 64, [(4, -1), (2, -2), (1, 0), (3, -1), (3, -2), (2, 0), (3, -1), (4, [0, -1]), (3, -2), (2, -1), (3, -2), (2, 0), (3, -1), (3, 0), (2, -1)]),
           (180, 24), [(1, 0), (2, 2), (1, 0), (3, 2), (2, 3), (2, 0), (4, 3), (3, 2), (2, 3)],
           (180, [(8, [0, 1]), (10, 0), (60, [0, 0, 1])]), rim_rows=12, ink_crease_rows=8, foot_ink=FOOT, x_clip=x_clip)
    # P1, the main peak, with the snowcap (apex x 130)
    top = M.peak(c, YF, (88, 64, [(4, -1), (2, -2), (1, 0), (3, -1), (2, -3), (6, [0, -1, 0, 0, -1, 0]), (3, -2), (2, -3), (2, -1), (2, -3), (3, -2), (1, 0), (2, -1),
                                  (2, -3), (3, -2), (2, [-1, 0]), (2, 0)]), (130, 4),
                 [(1, 0), (2, 2), (2, 1), (3, 3), (2, 0), (3, 2), (4, [1, 0, 1, 0]), (4, [0, 0, 1, 0]), (3, 3), (2, 1), (4, 3), (3, 2), (3, 1), (2, 2)],
                 (130, [(8, [0, 1]), (12, 0), (12, [0, 0, 1]), (40, 0)]), rim_rows=22, ink_crease_rows=20, foot_ink=FOOT,
                 cap=(116, 24, [(2, 1), (2, 1), (2, -1), (1, 0), (2, 1), (1, 1), (2, -1), (1, -1), (2, 1), (2, 1), (2, -1), (1, 0), (2, 1), (2, 1), (2, -1), (1, -1), (2, 1),
                                (1, 1), (2, -1)]),
                 gullies=[(104, 50, [(8, [-1, 0]), (5, -1)], "2", 2), (138, 40, [(10, [0, 1]), (12, [1, 0])], "3", 1)], x_clip=x_clip)
    # the strata, typed cell by cell (cells 7 to 24; rows 8 apart)
    S.strata(c, {34: ".....b.a.c...........", 42: "...c..a.b..a.S.......", 50: "..a.c.b.a.b..c.S.b..", 58: ".a.b.c.a.b.a.c.b.S..a"}, 56)
    for (x, y, v) in CLEANUP:
        c.px[y][x] = v
    return top


CLEANUP = [(117, 19, '0'), (67, 48, '0'), (98, 51, '1'), (97, 52, '2'), (93, 56, '2'), (57, 63, '0')]      # the corner pixel of each L-shaped double (lint), typed by hand


def build():
    c = Canvas("mountainA", "saloon", W, H)
    c.palrect(0, 0, 56, 72, "base")
    mountain(c)
    SB.dome(c, 4, YF)
    SB.tower(c, 38, YF)
    return c
