"""Tree clusters and bamboo (owner 11-07: "Fewer round trees near zoo between it and teahouse. More bamboo." and "we need overlapping tree tiles", proposal only).

OVERLAP PIECES  the map's own trees (decor.ROUND, PINE, JUNGLE_TREE: ink 3, lit 1, shade 2, light from the top left) painted back to front at typed offsets, so the front tree's canopy and its ink
                outline cover the one behind it, the way the range peaks stack: the same pixels as the singles, only combined.  Typed offsets (dx, dy) of each tree, the last one is in front:
                RR_R round pair, front to the lower right; RR_L front to the lower left; RRR three round (back centre, two in front); PP pine pair; PPP three pines; JJ jungle pair (zoo green).
BAMBOO          three clumps drawn here (16 x 24, 16 x 16, 8 x 14): 3 px stalks (ink | lit | shade) with node rings, a few leaf tufts, the ground line at the foot.  Each clump comes in both palettes
                (`zoo` in the jungle ground, `grass` on the lawn): the same pixels, so no new DMG tile for the second palette.
PLACES          typed below: which singles each cluster replaces, and every bamboo clump."""
import decor

D = "."


def combo(piece, offsets):
    rows = piece[1]
    h, w = len(rows), len(rows[0])
    W = max(dx for dx, dy in offsets) + w
    H = max(dy for dx, dy in offsets) + h
    g = [[D] * W for _ in range(H)]
    for dx, dy in offsets:
        for j, r in enumerate(rows):
            for i, c in enumerate(r):
                if c != D:
                    g[dy + j][dx + i] = c
    return (piece[0], ["".join(r) for r in g])


RR_R = combo(decor.ROUND, [(0, 0), (5, 6)])
RR_L = combo(decor.ROUND, [(6, 0), (0, 6)])
RRR = combo(decor.ROUND, [(5, 0), (0, 6), (9, 6)])
PP = combo(decor.PINE, [(0, 0), (5, 6)])
PPP = combo(decor.PINE, [(4, 0), (0, 6), (8, 6)])
JJ = combo(decor.JUNGLE_TREE, [(0, 0), (5, 6)])
JJJ = combo(decor.JUNGLE_TREE, [(5, 0), (0, 6), (9, 6)])


def stalks(w, h, specs, leaves):
    """specs: (x0, top, node rows); leaves: typed (x, y, v)"""
    g = [[D] * w for _ in range(h)]
    for x0, top, nodes in specs:
        for y in range(top, h):
            if y == top:
                g[y][x0 + 1] = "3"
            elif y == top + 1:
                g[y][x0:x0 + 3] = list("313")
            elif y == h - 1 or y in nodes:
                g[y][x0:x0 + 3] = list("333")
            else:
                g[y][x0:x0 + 3] = list("312")
    for (x, y, v) in leaves:
        assert g[y][x] == D, (x, y)
        g[y][x] = v
    return ["".join(r) for r in g]


# tall: three stalks (tops at rows 5, 0, 8), leaf tufts leaning out
TALL = stalks(16, 24, [(3, 5, (9, 15, 21)), (7, 0, (6, 12, 18)), (11, 8, (13, 19))],
              [(0, 7, "3"), (1, 7, "1"), (2, 7, "1"), (0, 12, "3"), (1, 12, "1"), (2, 12, "1"),                                     # left of the first stalk
               (4, 2, "3"), (5, 2, "1"), (6, 2, "1"), (10, 4, "1"), (11, 4, "1"), (12, 4, "3"),                                     # round the middle one's top
               (14, 10, "1"), (15, 10, "3"), (14, 14, "1"), (15, 14, "3"), (10, 16, "1")])
MID = stalks(16, 16, [(3, 3, (8, 13)), (9, 0, (6, 11))],
             [(0, 5, "3"), (1, 5, "1"), (2, 5, "1"), (6, 6, "1"), (7, 6, "3"), (6, 2, "3"), (7, 2, "1"), (8, 2, "1"), (12, 4, "1"), (13, 4, "1"), (14, 4, "3"), (12, 9, "1"), (13, 9, "1"), (14, 9, "3")])
SMALL = stalks(8, 14, [(3, 2, (8,))],
               [(0, 4, "3"), (1, 4, "1"), (2, 4, "1"), (6, 6, "1"), (7, 6, "3"), (1, 9, "1"), (2, 9, "1"), (0, 9, "3")])
BAMBOO = {"TALL": TALL, "MID": MID, "SMALL": SMALL}


def piece(name, pal):
    if name in BAMBOO:
        return (pal, BAMBOO[name])
    p = {"RR_R": RR_R, "RR_L": RR_L, "RRR": RRR, "PP": PP, "PPP": PPP, "JJ": JJ, "JJJ": JJJ}[name]
    return p


# PLACES  (pixel x, y of the top left; a cluster replaces the singles listed, matched by their top left)
REMOVE_ZOO = [("JUNGLE_TREE", 124, 419), ("JUNGLE_TREE", 124, 467), ("JUNGLE_TREE", 76, 403),             # round trees between the zoo and the teahouse (the one at (36, 411) stays, and the zoo's own)
              ("JUNGLE_BUSH", 96, 424), ("JUNGLE_BUSH", 112, 448), ("JUNGLE_BUSH", 144, 440)]
# cell aligned (x and y multiples of 8): every copy of a clump is then the same tiles, so the DMG cost is the clumps' own 12 tiles, not 12 per place
BAMBOO_AT = [("TALL", 104, 400, "zoo"), ("MID", 136, 408, "zoo"), ("SMALL", 120, 432, "zoo"), ("TALL", 104, 456, "zoo"), ("SMALL", 144, 448, "zoo"),
             ("MID", 136, 472, "zoo"), ("MID", 176, 432, "grass"), ("SMALL", 168, 464, "zoo")]
CLUSTERS = [  # (cluster, x, y, [(piece name, x, y) of the singles it replaces])
    ("PPP", 328, 232, [("PINE", 328, 224), ("PINE", 344, 256)]),
    ("PP", 320, 352, [("PINE", 336, 344), ("PINE", 328, 368)]),
    ("PP", 328, 296, [("PINE", 328, 304), ("PINE", 336, 280)]),
    ("PPP", 136, 0, [("PINE", 136, 8), ("PINE", 144, 8)]),
    ("PP", 256, 0, [("PINE", 248, 8)]),
    ("RR_R", 88, 120, [("ROUND", 92, 123)]),
    ("RRR", 200, 128, [("ROUND", 212, 123)]),
    ("RR_L", 144, 192, [("ROUND", 148, 195)]),
    ("JJJ", 128, 440, []),
    ("JJ", 80, 400, []),
]
NAMES = {id(getattr(decor, n)): n for n in ("PINE", "ROUND", "JUNGLE_TREE", "JUNGLE_BUSH", "BUSH", "SPRUCE")}


def apply(lay, trees=True, bamboo=True):
    S = list(lay.SCENERY)

    def drop(kind, x, y):
        for k, (p, sx, sy) in enumerate(S):
            if NAMES.get(id(p)) == kind and (sx, sy) == (x, y):
                del S[k]
                return True
        return False
    miss = []
    if bamboo:
        for kind, x, y in REMOVE_ZOO:
            if not drop(kind, x, y):
                miss.append((kind, x, y))
        for name, x, y, pal in BAMBOO_AT:
            S.append((piece(name, pal), x, y))
    if trees:
        for name, x, y, gone in CLUSTERS:
            for kind, sx, sy in gone:
                if not drop(kind, sx, sy):
                    miss.append((kind, sx, sy))
            S.append((piece(name, None), x, y))
    lay.SCENERY = S
    return miss
