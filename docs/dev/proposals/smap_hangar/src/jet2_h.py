"""Round 4e: the hangar jet, cleaned up by hand.  Same look as round 4d's jet B (owner's reference; fighter in side view, nose right), redrawn with clean edges.
Every pixel is a typed run: ('h', y, x, "chars") writes along row y from column x; ('v', x, y, "chars") writes downward from row y at column x.  Later runs go over earlier.
Palette BASE: 0 sand/white (lit; the pale yellow of the runway dashes on Color: fin stripes), 1 steel, 2 navy (shade, canopy), 3 ink.

LEVEL (0 degrees): the fuselage is horizontal: a 5-tall rear (outline, lit back, body, shade, outline) x 2 to 13, a 3-tall middle x 14 to 21, a one-row needle nose x 22 to 26;
the outline steps diagonally at x 13/14 and 21/22 (one pixel per step, both sides).  The delta wing is a right-angled triangle under the body: vertical trailing edge on x 7,
leading edge in even runs of 2 going up and forward.  The fin is a trapezoid, trailing edge vertical on x 1, leading edge 1 : 1.  The canopy is a diamond dome.
SLOPE (about 7 degrees): the same parts, the fuselage steps down one row every 8 columns (x 10 and x 18): top and bottom edges parallel, then a symmetric nose cone.
"""

FIN = [
    ('h', 0, 1, "33333"),
    ('h', 1, 1, "3"), ('h', 1, 2, "0000"), ('h', 1, 6, "3"),
    ('h', 2, 1, "3"), ('h', 2, 2, "11111"), ('h', 2, 7, "3"),
    ('h', 3, 1, "3"), ('h', 3, 2, "000000"), ('h', 3, 8, "3"),
    ('h', 4, 1, "3"), ('h', 4, 2, "1111111"), ('h', 4, 9, "3"),
]

LEVEL = FIN + [
    # fuselage
    ('v', 1, 5, "33333"),
    ('h', 5, 2, "3" * 12),
    ('h', 6, 2, "0" * 12), ('h', 6, 14, "3" * 8),
    ('h', 7, 2, "1" * 20), ('h', 7, 22, "33333"),
    ('h', 8, 2, "2" * 12), ('h', 8, 14, "3" * 8),
    ('h', 9, 2, "3" * 12),
    # canopy: a diamond dome, dark with a glint, open into the body
    ('h', 4, 16, "33"), ('h', 5, 15, "3"), ('h', 5, 16, "0"), ('h', 5, 17, "2"), ('h', 5, 18, "3"), ('h', 6, 15, "2222"),
    # delta wing under the body: trailing edge x 7, leading edge in runs of 2
    ('v', 7, 10, "3333"), ('h', 14, 7, "33"),
    ('h', 9, 14, "000"), ('h', 9, 17, "3"),
    ('h', 10, 8, "2"), ('h', 10, 9, "000000"), ('h', 10, 15, "33"),
    ('h', 11, 8, "2"), ('h', 11, 9, "0011"), ('h', 11, 13, "33"),
    ('h', 12, 8, "2"), ('h', 12, 9, "11"), ('h', 12, 11, "33"),
    ('h', 13, 8, "2"), ('h', 13, 9, "33"),
    # tailplane
    ('h', 10, 1, "3"), ('h', 10, 2, "011"), ('h', 10, 5, "3"), ('h', 11, 2, "333"),
]

SLOPE = FIN + [
    ('v', 1, 5, "33333"),
    # body: x 2 to 9 on rows 5 to 9; x 10 to 17 on rows 6 to 10; x 18 to 21 on rows 7 to 11 (parallel edges, a step of one row every 8 columns)
    ('h', 5, 2, "3" * 8), ('h', 6, 2, "0" * 8), ('h', 7, 2, "1" * 8), ('h', 8, 2, "2" * 8), ('h', 9, 2, "3" * 8),
    ('h', 6, 10, "3" * 8), ('h', 7, 10, "0" * 8), ('h', 8, 10, "1" * 8), ('h', 9, 10, "2" * 8), ('h', 10, 10, "3" * 8),
    ('h', 7, 18, "3333"), ('h', 8, 18, "0000"), ('h', 9, 18, "1111"), ('h', 10, 18, "2222"), ('h', 11, 18, "3333"),
    # nose cone: 3 tall x 22 to 23, then the needle
    ('h', 8, 22, "33"), ('h', 9, 22, "11"), ('h', 10, 22, "33"), ('h', 9, 24, "333"),
    # canopy
    ('h', 4, 13, "33"), ('h', 5, 12, "3"), ('h', 5, 13, "0"), ('h', 5, 14, "2"), ('h', 5, 15, "3"), ('h', 6, 12, "2222"),
    # delta wing: trailing edge x 7, leading edge in runs of 2
    ('v', 7, 10, "33333"), ('h', 15, 7, "33"),
    ('h', 10, 8, "20"),
    ('h', 11, 8, "2"), ('h', 11, 9, "0000000"), ('h', 11, 15, "33"),
    ('h', 12, 8, "2"), ('h', 12, 9, "00011"), ('h', 12, 14, "33"),
    ('h', 13, 8, "2"), ('h', 13, 9, "111"), ('h', 13, 12, "33"),
    ('h', 14, 8, "2"), ('h', 14, 9, "33"),
    # tailplane
    ('h', 10, 1, "3"), ('h', 10, 2, "011"), ('h', 10, 5, "3"), ('h', 11, 2, "333"),
]

POSES = {'L': (LEVEL, 27, 15), 'S': (SLOPE, 28, 16)}


def pose(name):
    runs, w, h = POSES[name]
    g = [["."] * w for _ in range(h)]
    for r in runs:
        if r[0] == 'h':
            _, y, x, s = r
            for i, ch in enumerate(s):
                g[y][x + i] = ch
        else:
            _, x, y, s = r
            for j, ch in enumerate(s):
                g[y + j][x] = ch
    return ["".join(r) for r in g]
