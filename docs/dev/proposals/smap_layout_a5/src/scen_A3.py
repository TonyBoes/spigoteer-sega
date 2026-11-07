"""The typed scenery lists of layout A3 (second pass): the top left cell (x, y) of each piece.  Footprints in cells: PINE 2 x 3, ROUND and JTREE 3 x 3 (drawn 4 px right and
3 px down), BUSH and JBUSH and SPRUCE 2 x 2, MOUND 3 x 2 (drawn 7 px down), ROCK and HAY 2 x 1, BARN 3 x 3.  Every list is grouped by the place it dresses."""
PINES = [
    # the north-west meadow, between the stadium and the bistro
    (15, 0), (18, 1), (19, 7), (23, 0),
    # the lodge forest: north-west edge, the strip behind the lodge, the west and east sides of the lodge, then the tongue towards the snow
    (39, 0), (42, 1), (45, 0), (48, 1), (52, 0), (58, 0), (61, 1),
    (40, 4), (43, 5), (46, 3), (47, 7), (44, 8), (40, 8),
    (60, 4), (62, 5), (60, 8),
    (41, 13), (45, 14), (49, 13),
    # the meadow south of the north road: west end, then the strip north of the town
    (15, 13), (19, 14), (23, 13), (30, 13), (36, 13), (17, 16), (21, 16),
    # the meadow round the town
    (19, 19), (24, 19), (41, 19), (23, 25), (25, 23),
    # the orchard
    (38, 40), (34, 44), (40, 43),
    # the grass between the jungle and the farm, and the band north of the jungle
    (22, 53), (42, 50), (3, 47), (20, 47),
]
ROUNDS = [
    (14, 4), (15, 8),                                   # east of the stadium
    (21, 3),                                            # the north-west meadow
    (37, 6),                                            # east of the bistro
    (20, 23),                                           # town meadow west
    (41, 22),                                           # town meadow east
    (35, 31), (44, 32), (37, 36), (42, 37), (45, 40),   # the orchard between the town street and the snow road, thinner than A2's eight
    (41, 54),                                           # beside the tea house garden
    (28, 47), (33, 47),                                 # north of the tea house
]
BUSHES = [
    (2, 1), (5, 1), (9, 1), (12, 1), (0, 4), (0, 8),    # the hedge behind the stadium
    (22, 8), (25, 8),                                   # the north-west meadow
    (27, 0), (31, 1), (34, 0), (55, 1),                 # behind the bistro, the lodge
    (25, 15), (28, 15), (33, 15), (39, 15),             # the hedge north of the town
    (22, 21), (18, 26),                                 # town meadow west
    (41, 17), (42, 26),                                 # town meadow east
    (34, 35), (45, 36), (46, 45), (39, 30), (35, 40),   # the orchard
    (22, 58), (42, 59),
    (25, 55), (25, 59), (39, 53), (40, 59), (29, 52), (35, 52),      # the tea house garden: loose clumps round the picture
    (8, 47), (13, 47), (18, 47), (36, 47), (39, 47),
    (30, 64), (35, 64),                                 # the strip below the south road
]
JTREES = [
    (3, 50), (8, 49), (13, 50), (17, 51),               # the north edge of the jungle
    (14, 55), (18, 58),                                 # east of the zoo
]
JBUSHES = [
    (5, 53), (11, 53), (19, 54), (14, 59), (17, 55), (6, 64), (14, 64),
]
SPRUCES = [
    (56, 13), (59, 14), (54, 16), (51, 17), (58, 17), (47, 18), (44, 19), (50, 20), (57, 20), (60, 19),
    (50, 30), (54, 31), (58, 30), (61, 32), (52, 33), (57, 33),
]
MOUNDS = [
    (47, 24), (46, 26), (53, 20), (59, 34),
]
ROCKS = [
    (3, 14), (8, 13), (11, 15), (5, 17), (9, 18), (13, 17), (15, 19), (3, 19), (13, 21), (14, 23), (12, 25), (15, 26),
    (3, 31), (8, 30), (12, 32), (18, 31), (23, 30), (27, 33), (5, 34), (15, 34), (21, 34), (29, 31), (10, 35),
    (3, 37), (8, 39), (5, 41), (11, 43), (3, 44), (12, 37), (29, 38), (30, 41), (29, 44),
]
HAYS = [(47, 54), (60, 54), (47, 60)]
BARNS = [(46, 56)]
FIELDS_A3 = [(47, 48, 60, 53)]
