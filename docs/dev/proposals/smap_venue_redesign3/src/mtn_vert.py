"""ROUND 3 RANGE PIECES FOR VERTICAL USE: one hand-typed peak, 32 x 24 (4 x 3 cells), built to be stacked every 16 px so that the next peak down stands IN FRONT of the
foot of the one behind it (the ridge runs north-south; the screen is the front view).  One drawing, two palettes: DESERT (SALOON: 0 sand / sun-bleached crest, 1 lit rock,
2 shaded rock, 3 ink) and SNOWY (IGLOO: 0 snow, 1 pale ice-blue rock, 2 deep blue, 3 ink): the same DMG tiles, only the Color palette differs.  Light from the top left.

Everything below is typed: the peak is 24 typed rows (each row: its first column and the exact characters), the small strata marks are typed (row, first column, last column,
value).  Stacking only PASTES the typed peak at a 16 px pitch (copying my own finished work); where two peaks meet the nearer one's own ink outline is the line.
Why it works vertically: the peak's foot is a rounded curve (rows 19 to 23), so the back peak's feet show as lobes either side of the front peak's apex and the outline
waves in (a saddle) between peaks; the top piece has no peak behind it, the last has its foot closed in ink (end caps).  Why it works horizontally: the same peak
stands alone, 2 px clear of its cell edges, so peaks side by side keep a gap.
"""
import common as C
from canvas import Canvas

PEAK_W, PEAK_H, PITCH = 32, 24, 16

# 24 typed rows of 32 characters ('.' = outside).  0 crest / cap, 1 lit rock, 2 shaded rock, 3 ink.  Two summits: the main one (apex x 12) and a lower one on its right shoulder
# (apex x 21, y 5) with a saddle between them; each summit has its own crease (lit left, shaded right); the feet are rounded (rows 19 to 23) so a peak stacked in front of
# this one leaves its feet showing as lobes.  Typed row by row; the helper below only checks every row is 32 wide.
D = "."
ROWS = [
    D * 12 + "3" + D * 19,
    D * 11 + "303" + D * 18,
    D * 10 + "30013" + D * 17,
    D * 9 + "3000313" + D * 16,
    D * 9 + "3000313" + D * 16,
    D * 8 + "300013223" + D * 4 + "3" + D * 10,
    D * 8 + "301111323" + D * 3 + "303" + D * 9,
    D * 7 + "30111113223" + D + "30313" + D * 8,
    D * 7 + "30111113222" + "301323" + D * 8,
    D * 6 + "30" + "1" * 7 + "3" + "22" + "3" + "111" + "3" + "2" + "3" + D * 7,
    D * 6 + "3" + "1" * 8 + "222" + "3" + "111" + "222" + "3" + D * 6,
    D * 5 + "3" + "1" * 9 + "2222" + "111" + "222" + "3" + D * 6,
    D * 5 + "3" + "1" * 10 + "222" + "1111" + "222" + "3" + D * 5,
    D * 4 + "3" + "1" * 11 + "2222" + "111" + "2222" + "3" + D * 4,
    D * 4 + "3" + "1" * 11 + "2222" + "1111" + "222" + "3" + D * 4,
    D * 3 + "3" + "1" * 14 + "22" + "1111" + "2222" + "3" + D * 3,
    D * 3 + "3" + "1" * 14 + "222" + "1111" + "2222" + "3" + D * 2,
    D * 2 + "3" + "1" * 15 + "222" + "1111" + "2222" + "3" + D * 2,
    D * 2 + "3" + "1" * 16 + "22" + "11111" + "2222" + "3" + D,
    D * 1 + "3" + "1" * 17 + "22" + "11111" + "2222" + "3" + D,
    D * 1 + "3" + "1" * 17 + "22" + "11111" + "2222" + "3" + D,
    D * 2 + "33" + "1" * 15 + "22" + "11111" + "22" + "33" + D * 2,
    D * 4 + "333" + "1" * 12 + "22" + "111" + "3333" + D * 4,
    D * 7 + "3" * 17 + D * 8,
]
MARKS = [(11, 8, 11, "2"), (15, 9, 12, "2"), (19, 5, 9, "2"), (16, 22, 23, "2"),     # strata dashes on the lit faces, each in a different column range
         (13, 17, 18, "3"), (18, 27, 28, "3")]                                       # dark marks on the shaded faces


def peak_rows():
    g = []
    for r, s in enumerate(ROWS):
        assert len(s) == PEAK_W, f"row {r} is {len(s)} wide"
        g.append(list(s))
    for (y, x0, x1, v) in MARKS:
        for x in range(x0, x1 + 1):
            assert g[y][x] in "12", (y, x, g[y][x])
            g[y][x] = v
    return ["".join(r) for r in g]


PEAK = peak_rows()


def canvas(w, h, name, snow):
    return Canvas(name, "igloo" if snow else "saloon", w, h)


def single(snow):
    c = canvas(PEAK_W, PEAK_H, "vpeak", snow)
    C.paste(c, 0, 0, PEAK)
    return c


def column(n, snow):
    """n peaks, each 16 px lower than the one behind it, painted back to front: 32 x (16 (n - 1) + 24)"""
    c = canvas(PEAK_W, PITCH * (n - 1) + PEAK_H, f"vcol{n}", snow)
    for k in range(n):
        C.paste(c, 0, PITCH * k, PEAK)
    return c


def row(xs_ys, w, h, snow):
    """a horizontal arrangement: typed (x, y) places of single peaks"""
    c = canvas(w, h, "vrow", snow)
    for (x, y) in xs_ys:
        C.paste(c, x, y, PEAK)
    return c


def stack(places, w, h, snow=False):
    """peaks pasted back to front at typed (x, y) places"""
    return row(places, w, h, snow)


def previews():
    return [("straight", stack([(0, 0), (0, 16), (0, 32), (0, 48)], 32, 72), 'desert', (1, 34)),
            ("zig8", stack([(0, 0), (8, 16), (0, 32), (8, 48)], 40, 72), 'desert', (1, 34)),
            ("zig8b", stack([(8, 0), (0, 16), (8, 32), (0, 48)], 40, 72), 'desert', (1, 34)),
            ("p8", stack([(0, 0), (8, 8), (0, 16), (8, 24), (0, 32)], 40, 56), 'desert', (1, 34))]


COL_N = 4
ROW_PLACES = [(0, 8), (32, 0), (64, 8), (96, 0)]


def vertical(snow):
    return column(COL_N, snow)


def horizontal(snow):
    return row(ROW_PLACES, 128, 32, snow)


BIOME, AT = 'desert', (1, 34)
REGION = None


def build():
    return column(COL_N, False)


if __name__ == '__main__':
    for r in PEAK:
        print(r.replace('_', '.'))
