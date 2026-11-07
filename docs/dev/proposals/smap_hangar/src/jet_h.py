"""Round 4d: a small fighter jet for the hangar, drawn by hand at map size (26 x 15) in the look of the owner's reference (docs/dev/proposals/smap_hangar/owner_jet_example.webp):
side view, nose to the right and slightly down, long pointed nose, dark canopy forward, a low swept delta wing (near wing big, far wing peeking over the back), a tall
swept-back tail fin with two stripes, a low tailplane, an ink outline.  Not traced, not scaled: typed here.  Palette BASE: 0 sand/white (lit; on Color the pale yellow of the
runway dashes, used for the fin stripes), 1 steel, 2 navy (shade, canopy), 3 ink.
Runs: ('v', x, y, "chars", w) writes the characters downward from row y on w columns from x (a fuselage column group); ('h', y, x, "chars") writes along row y.  Later runs go over earlier.
The descent (about 12 degrees) is the staircase of column groups, each group a little lower than the one before.
"""

JET = [
    # far wing tip over the back
    ('h', 3, 10, "33"), ('h', 4, 8, "3"), ('h', 4, 9, "011"), ('h', 4, 12, "3"),
    # fuselage: rear (5 tall: outline, lit, body, shade, outline), mid (4 tall), nose (3 tall), tip
    ('v', 2, 4, "30123", 5), ('v', 7, 5, "30123", 6), ('v', 13, 6, "3013", 4), ('v', 17, 7, "3013", 4), ('v', 21, 8, "313", 3),
    ('v', 24, 9, "33", 1), ('v', 25, 10, "3", 1),
    # tail fin: tall, swept back (leans to the left going up), two stripes (index 0)
    ('h', 0, 1, "3333"),
    ('h', 1, 1, "3"), ('h', 1, 2, "000"), ('h', 1, 5, "3"),
    ('h', 2, 1, "3"), ('h', 2, 2, "1111"), ('h', 2, 6, "3"),
    ('h', 3, 2, "3"), ('h', 3, 3, "0000"), ('h', 3, 7, "3"),
    ('h', 4, 2, "3"), ('h', 4, 3, "11111"), ('h', 4, 8, "3"),
    # low tailplane
    ('h', 9, 1, "3"), ('h', 9, 2, "011"), ('h', 9, 5, "3"), ('h', 10, 2, "3333"),
    # near wing: a big low delta under the fuselage, trailing edge dark on x 8, leading edge sloping up to the fuselage
    ('h', 10, 7, "3"), ('h', 10, 8, "2"), ('h', 10, 9, "00001111"),
    ('h', 11, 7, "3"), ('h', 11, 8, "2"), ('h', 11, 9, "00011"), ('h', 11, 14, "333"),
    ('h', 12, 7, "3"), ('h', 12, 8, "2"), ('h', 12, 9, "001"), ('h', 12, 12, "33"),
    ('h', 13, 7, "3"), ('h', 13, 8, "21"), ('h', 13, 10, "33"),
    ('h', 14, 7, "333"),
    # canopy: a dark dome forward on the back, with a glint
    ('h', 4, 14, "33"), ('h', 5, 13, "3"), ('h', 5, 14, "2"), ('h', 5, 15, "0"), ('h', 5, 16, "3"), ('h', 6, 17, "3"),
]

W, H = 26, 15


def pose():
    g = [["."] * W for _ in range(H)]
    for r in JET:
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
