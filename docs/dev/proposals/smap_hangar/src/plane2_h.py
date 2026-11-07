"""Round 4c: the 4a side-view plane redrawn bigger (22 px long), nose to the right and down, half out of the doors: tail in the black slot, nose over the apron.
Every pixel is a typed run.  ('v', x, y, "chars", w) writes the characters downward from row y on w columns starting at x (one column group of the fuselage staircase);
('h', y, x, "chars") writes along row y from column x.  Later runs go over earlier ones.  Palette BASE: 0 white/sand (lit), 1 steel (body), 2 navy (shade), 3 ink (outline).

The fuselage is a staircase of column groups, each one row lower than the one before; every group top to bottom is: outline, lit back, body, body, shade, outline ("301123").
P1: groups of 3 columns (a slope of 1 : 3, about 18 degrees: "20").  P2: groups of 2 columns (1 : 2, about 27 degrees: "30").
Both: a pointed nose (the last three columns shrink), a swept tail fin leaning back, a canopy dome with a glint, a small far wing tip peeking over the back and a larger near
wing hanging down and back in front of the belly.
"""

FIN = [('h', 0, 2, "33"), ('h', 1, 2, "3"), ('h', 1, 3, "0"), ('h', 1, 4, "3"),
       ('h', 2, 2, "3"), ('h', 2, 3, "0"), ('h', 2, 4, "1"), ('h', 2, 5, "3"),
       ('h', 3, 2, "3"), ('h', 3, 3, "0"), ('h', 3, 4, "1"), ('h', 3, 5, "1"), ('h', 3, 6, "3")]

P1 = [
    # far wing tip over the back (x 8 to 12)
    ('h', 3, 8, "33"), ('h', 4, 8, "3"), ('h', 4, 9, "011"), ('h', 4, 12, "3"), ('h', 5, 11, "11"), ('h', 5, 13, "3"),
    # fuselage: six groups of 3 columns, tail cap, nose
    ('v', 1, 4, "333", 1),
    ('v', 2, 3, "301123", 3), ('v', 5, 4, "301123", 3), ('v', 8, 5, "301123", 3), ('v', 11, 6, "301123", 3), ('v', 14, 7, "301123", 3), ('v', 17, 8, "301123", 3),
    ('v', 20, 9, "301123", 1), ('v', 21, 10, "3123", 1), ('v', 22, 11, "33", 1),
    # near wing, down and back from the belly (x 5 to 13, rows 11 to 16)
    ('h', 11, 7, "3"), ('h', 11, 8, "000"),
    ('h', 12, 6, "3"), ('h', 12, 7, "0000111"),
    ('h', 13, 5, "3"), ('h', 13, 6, "0011111"), ('h', 13, 13, "3"),
    ('h', 14, 5, "3"), ('h', 14, 6, "001111"), ('h', 14, 12, "3"),
    ('h', 15, 5, "3"), ('h', 15, 6, "011"), ('h', 15, 9, "3"),
    ('h', 16, 5, "33333"),
] + FIN + [
    # canopy dome with a glint, on the back at x 14 to 17
    ('h', 5, 15, "33"), ('h', 6, 14, "3"), ('h', 6, 15, "2"), ('h', 6, 16, "0"), ('h', 6, 17, "3"),
    ('h', 1, 4, "1"), ('h', 9, 21, "1"),     # lint mends: the fin tip off the hazard lintel; the nose top off the hangar's foot line
]

P2 = [
    ('h', 3, 8, "33"), ('h', 4, 7, "3"), ('h', 4, 8, "011"), ('h', 4, 11, "3"), ('h', 5, 10, "11"), ('h', 5, 12, "3"),
    ('v', 1, 4, "333", 1),
    ('v', 2, 3, "301123", 2), ('v', 4, 4, "301123", 2), ('v', 6, 5, "301123", 2), ('v', 8, 6, "301123", 2), ('v', 10, 7, "301123", 2),
    ('v', 12, 8, "301123", 2), ('v', 14, 9, "301123", 2), ('v', 16, 10, "301123", 2), ('v', 18, 11, "301123", 2),
    ('v', 20, 12, "301123", 1), ('v', 21, 13, "3123", 1), ('v', 22, 14, "33", 1),
    # near wing (x 5 to 13, rows 12 to 17)
    ('h', 12, 6, "3"), ('h', 12, 7, "00"),
    ('h', 13, 5, "3"), ('h', 13, 6, "0000111"),
    ('h', 14, 4, "3"), ('h', 14, 5, "0011111"), ('h', 14, 12, "3"),
    ('h', 15, 4, "3"), ('h', 15, 5, "001111"), ('h', 15, 11, "3"),
    ('h', 16, 4, "3"), ('h', 16, 5, "011"), ('h', 16, 8, "3"),
    ('h', 17, 4, "33333"),
] + FIN + [
    ('h', 7, 14, "33"), ('h', 8, 13, "3"), ('h', 8, 14, "2"), ('h', 8, 15, "0"), ('h', 8, 16, "3"),
    ('h', 1, 4, "1"),
]

POSES = {'P1': (P1, 24, 17), 'P2': (P2, 24, 18)}


def pose(name):
    runs, w, h = POSES[name]
    g = [["."] * w for _ in range(h)]
    for r in runs:
        if r[0] == 'h':
            _, y, x, s = r
            for i, ch in enumerate(s):
                g[y][x + i] = ch
        else:
            _, x, y, s, n = r
            for k in range(n):
                for j, ch in enumerate(s):
                    g[y + j][x + k] = ch
    return ["".join(r) for r in g]
