"""Round 4b: the plane taxiing out of option 2's doors onto the apron, nose leading toward the runway, in the map's 3/4 view.
Every pixel is a typed run: (y, x, "chars") writes the characters at row y from column x.  Palette BASE: 0 white/sand (lit), 1 steel (body), 2 navy (shade), 3 ink (outline).

POSE A, 15 x 15: heading down and to the right at 45 degrees (a staircase of single pixels: the cleanest diagonal there is).  The fuselage is a 4-pixel band (shaded belly on
its lower left, two body pixels, lit back on its upper right) with an ink outline; the wings are broad swept blades (the far wing rises from the upper right of the fuselage,
the near wing falls from its lower left, a little different: its own shading and tip), the canopy is a dark patch on the body.
POSE B, 24 x 14: heading mostly toward the viewer (about 63 degrees: one column right per two rows), the plane seen from above and in front: a chevron, the right wing
(screen right) a long triangle climbing toward its tip, the left wing (screen left) a shorter one, the canopy dark on the nose side.
"""

POSE_A = [
    # far wing (upper right of the fuselage): a broad swept blade, leading edge straight on x 14, trailing edge slanting up and to the left, tip cap on top
    (0, 10, "33333"),
    (1, 9, "3"), (1, 10, "0011"), (1, 14, "3"),
    (2, 9, "3"), (2, 10, "0011"), (2, 14, "3"),
    (3, 8, "3"), (3, 9, "00011"), (3, 14, "3"),
    (4, 8, "3"), (4, 9, "00011"), (4, 14, "3"),
    (5, 9, "00111"), (5, 14, "3"),
    (6, 10, "0111"), (6, 14, "3"),
    (7, 11, "011"), (7, 14, "3"),
    (8, 12, "01"), (8, 14, "3"),
    (9, 13, "1"), (9, 14, "3"),
    (10, 14, "3"),
    # fuselage, one row per step: outline, shade, body, body, lit, outline; tail cap and nose cap
    (1, 1, "3333"),
    (2, 0, "321103"), (3, 1, "321103"), (4, 2, "321103"), (5, 3, "321103"),
    (6, 4, "321103"), (7, 5, "321103"), (8, 6, "321103"), (9, 7, "321103"),
    (10, 8, "321103"), (11, 9, "321103"), (12, 10, "321103"),
    (13, 11, "3333"),
    # near wing (lower left of the fuselage): a broad swept blade, leading edge straight on y 14 (the bottom), tip cap at the left
    (8, 4, "33"),
    (9, 2, "33"), (9, 4, "000"),
    (10, 1, "3"), (10, 2, "000000"),
    (11, 1, "3"), (11, 2, "0000"), (11, 6, "110"),
    (12, 1, "3"), (12, 2, "1111111"), (12, 9, "0"),
    (13, 1, "3"), (13, 2, "11111111"),
    (14, 1, "33333333333"),
    # canopy (dark, on the body)
    (8, 6, "22"), (9, 7, "22"),
    # tailplanes: a small far blade rising from the fuselage's upper right near the tail, a small near blade falling from its lower left
    (0, 6, "33"), (1, 5, "3"), (1, 6, "0"), (1, 7, "3"), (2, 6, "1"), (2, 7, "3"), (3, 7, "3"),
    (4, 0, "33"), (5, 0, "3"), (5, 1, "0"), (5, 2, "1"), (6, 1, "3"), (6, 2, "1"), (6, 3, "1"), (7, 2, "33"),
]

POSE_B = [
    # right wing (screen right): a triangle, top edge flat on y 5, leading edge climbing 1 row per 2 columns
    (5, 13, "3333333333"),
    (6, 13, "000000000"), (6, 22, "3"), (6, 23, "3"),
    (7, 14, "011111"), (7, 20, "33"),
    (8, 14, "0111"), (8, 18, "33"),
    (9, 15, "1"), (9, 16, "33"),
    (10, 15, "3"),
    # left wing (screen left): smaller, top edge flat on y 6, leading edge climbing toward the tip
    (6, 1, "333333"),
    (7, 1, "33"), (7, 3, "00111"),
    (8, 3, "33"), (8, 5, "011"),
    (9, 5, "33"), (9, 7, "01"),
    (10, 7, "33"),
    # fuselage: a staircase, each step one column right per two rows; outline, lit, body, body, shade, outline
    (0, 6, "3333"),
    (1, 5, "301123"), (2, 5, "301123"),
    (3, 6, "301123"), (4, 6, "301123"),
    (5, 7, "301123"), (6, 7, "301123"),
    (7, 8, "301123"), (8, 8, "301123"),
    (9, 9, "301123"), (10, 9, "301123"),
    (11, 10, "301123"), (12, 10, "301123"),
    (13, 10, "333333"),
    # canopy
    (8, 10, "2"), (9, 11, "22"), (10, 11, "2"),
    # tailplanes: a small blade each side of the tail
    (2, 2, "3333"), (3, 2, "3"), (3, 3, "011"), (4, 3, "333"),
    (2, 11, "3333"), (3, 12, "11"), (3, 14, "3"), (4, 12, "333"),
]

POSES = {'A': (POSE_A, 16, 15), 'B': (POSE_B, 24, 14)}


def pose(name):
    runs, w, h = POSES[name]
    g = [["."] * w for _ in range(h)]
    for y, x, s in runs:
        for i, ch in enumerate(s):
            g[y][x + i] = ch
    return ["".join(r) for r in g]
