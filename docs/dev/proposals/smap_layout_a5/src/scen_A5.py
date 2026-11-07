"""The typed scenery lists of layout A5 (A4's, with the pieces that stood on the new river, the new snow edge and the new lake moved by hand): the top left
cell (x, y) of each piece.  Footprints in cells: PINE 2 x 3, ROUND and JTREE 3 x 3 (drawn 4 px right and 3 px down), BUSH and JBUSH and SPRUCE 2 x 2, MOUND 3 x 2,
ROCK and HAY 2 x 1, BARN 3 x 3; LOGS_H 2 x 1 and LOGS_V 1 x 2 (floating logs, on open water), PILES 3 x 2 (the log yard), ROCKS_SNOW 2 x 1 (boulders in the snow at the spring)."""
PINES = [
    # between the baseball park and the bistro
    (17, 1), (17, 5), (18, 8),
    # the foothills east of the bistro (the pines thicken towards the snow)
    (32, 5), (35, 6), (33, 8), (37, 5), (38, 8), (41, 5), (41, 8),
    # the forest west of the river, then between the river and the lodge
    (42, 14), (43, 20), (41, 28), (43, 32), (42, 35),
    (48, 16), (50, 17), (49, 24), (48, 28), (48, 36), (48, 39),
    # south of the river's bend, between the river and the road
    (41, 38), (42, 43), (41, 46),
    # the scrub north of the tea house and the lake
    (22, 48), (31, 49),
]
ROUNDS = [
    # the city's outskirts: the strip between the baseball park's road and the saloon's desert
    (5, 14), (11, 15), (20, 14), (26, 15), (14, 18), (22, 17), (2, 17), (28, 19), (18, 24),
    # the meadow round the town
    (25, 22), (26, 25),
    # the tea house garden and the lake's shore
    (28, 50), (33, 50),
]
BUSHES = [
    (2, 13), (8, 18), (9, 13), (16, 14), (17, 17), (24, 13), (30, 14), (11, 19), (4, 19), (13, 16), (21, 20),
    (34, 13),
    (24, 21), (40, 28), (40, 31), (43, 37),
    (26, 53), (31, 52), (22, 53),
    (14, 48), (19, 48), (26, 47), (33, 47), (38, 47),
]
JTREES = [
    (4, 51), (9, 50), (15, 52), (15, 58), (4, 65), (10, 65), (16, 66),
]
JBUSHES = [
    (6, 53), (12, 53), (18, 55), (14, 56), (17, 64), (8, 64),
]
SPRUCES = [
    # the snow round the igloo and along the river's banks
    (60, 6), (60, 9), (49, 13),
    (55, 16), (58, 14), (57, 17), (60, 16),
]
MOUNDS = []
ROCKS = [
    (12, 22), (14, 25), (14, 27), (13, 24), (3, 31), (14, 31), (22, 30), (26, 31), (6, 36), (3, 40), (8, 43), (4, 34), (7, 38), (7, 41), (3, 44), (8, 33),
]
ROCKS_SNOW = [(44, 5), (48, 5)]
HAYS = [(48, 56), (48, 59), (51, 54), (58, 53)]
BARNS = []
FIELDS_A4 = [(51, 48, 60, 53)]
# floating logs: on open water only (both cells plain water cells with water on every side; asserted by check_water.py)
LOGS_H = [(48, 33), (54, 33), (57, 32), (42, 52), (43, 57), (42, 65), (44, 68)]
LOGS_V = [(46, 20), (46, 29), (46, 36), (45, 43), (45, 46)]
# the log yards: two piles on the pond's bank in front of the factory's roof, one on the river's east bank (the lodge's landing)
PILES = [(53, 36), (56, 36), (49, 21)]
