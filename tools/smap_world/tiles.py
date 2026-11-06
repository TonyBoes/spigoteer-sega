"""Hand-typed 8 x 8 tiles of round 2: ground variants per biome, the road set, the cobble, the fog set.
Every tile is eight strings of eight palette indices (0 to 3).  Tiles that differ only by a quarter turn (fog edges and corners, road
corners) are typed once and turned by the loader (my own drawing, no hardware flip needed on the DMG); everything else is typed out."""

# ---- palettes (see pal.py): GRASS 0 ground, 1 tuft, 2 leaf, 3 ink; DESERT 0 sand, 1 ripple, 2 stone, 3 ink; SNOW 0 snow, 1 shade, 2 deep, 3 ink ----
# One shape per ground texture (owner 11-06, Q92, the land kit): the DMG shows the same pixels in every biome that uses a shape, the Color build the cell's own
# palette (greens on grass, yellow-green on the farm, ochre on sand, pale blue on snow ...). Every shape is one of the owner's own tufts, copied unchanged.
FLAT = ["00000000"] * 8
SPROUT = ["00000000", "00000000", "00001000", "00101010", "00011100", "00000000", "00000000", "00000000"]     # grass, farm, moss garden, jungle
RIPPLE = ["00000000", "00000000", "01100000", "00011000", "00000110", "00000000", "00000000", "00000000"]     # desert and snow
NEEDLE = ["00000000", "01000100", "10101010", "01000100", "00000000", "00010001", "00101010", "00010001"]     # the forest floor
ACCENT = ["00000000", "01100110", "01100110", "00000000", "00000000", "01100110", "01100110", "00000000"]     # the studs of the bistro plaza and the factory yard
GROUND = {
    "grass": [FLAT, SPROUT],
    "desert": [FLAT, RIPPLE],
    "snow": [FLAT, RIPPLE],
    "farm": [FLAT, SPROUT],
    "jungle": [FLAT, SPROUT],
    "paved": [FLAT],                                               # the stadium yard: white concrete
    "plaza": [FLAT, ACCENT],                                       # the bistro's yard: cream, with teal studs
    "yard": [FLAT, ACCENT],                                        # the factory's yard: concrete with steel studs
    "moss": [FLAT, SPROUT],                                        # the teahouse garden
    "forest": [FLAT, NEEDLE, FLAT, FLAT],                          # the grass, denser (needles)
}

# the crop rows of the farm (palette FARM: 1 stubble, 2 soil)
FIELD = ["00000000", "11111111", "11111111", "22222222", "00000000", "11111111", "11111111", "22222222"]
FIELD_EDGE = ["22222222", "00000000", "00000000", "00000000", "00000000", "00000000", "00000000", "00000000"]

# the town's cobble (palette TOWN1: p = 1, q = 2, h = 0) as the approved picture has it
COBBLE = ["11120001", "11121111", "11121111", "22222222", "11110002", "11111112", "11111112", "22222222"]
COBBLE_B = ["11121111", "11121111", "22222222", "11111112", "11111112", "22222222", "11120001", "11121111"]

# ---- the road: pure road, never any ground pixel (palette ROAD: 0 light, 1 body, 2 kerb, 3 ink) ----------------------------------------
ROAD = {
    "F1": ["11111111", "11111011", "11111111", "11011111", "11111111", "11111110", "10111111", "11111111"],
    "F2": ["11111111", "11011111", "11111111", "11111101", "11101111", "11111111", "11111011", "11111111"],
    "EN": ["22222222", "22222222", "00000000", "11111111", "11111011", "11111111", "11011111", "11111111"],
    "ES": ["11111111", "11011111", "11111111", "11111011", "11111111", "00000000", "22222222", "22222222"],
    "EW": ["22011111", "22011111", "22011101", "22011111", "22011111", "22010111", "22011111", "22011111"],
    "EE": ["11111022", "11111022", "10111022", "11111022", "11111022", "11110122", "11111022", "11111022"],
    "CNW": ["22222222", "22222222", "22000000", "22011111", "22011111", "22011111", "22011111", "22011111"],
    "CNE": ["22222222", "22222222", "00000022", "11111022", "11111022", "11111022", "11111022", "11111022"],
    "CSW": ["22011111", "22011111", "22011111", "22011111", "22011111", "22000000", "22222222", "22222222"],
    "CSE": ["11111022", "11111022", "11111022", "11111022", "11111022", "00000022", "22222222", "22222222"],
}

# ---- the fog (palette per ground: 0 = the ground of that cell, 1 cloud, 2 cloud shade, 3 cloud deep) ----------------------------------
# the interior: a 16 x 16 pattern of billows (a shaded arc under each), cut into four tiles laid by the cell's x and y parity
_P = ["1111111111111111", "1111111111111111", "1112211111111111", "1111111111111111", "1111111111111111", "1111111111222111",
      "1111111111111111", "1111111111111111", "1111111111111111", "1221111111111111", "1111111111111111", "1111111111111111",
      "1111111222111111", "1111111111111111", "1111111111111211", "1111111111111111"]
FOG = {
    "FA": [r[:8] for r in _P[:8]], "FB": [r[8:] for r in _P[:8]], "FC": [r[:8] for r in _P[8:]], "FD": [r[8:] for r in _P[8:]],
    # the edge: a lens 16 px wide over two cells (B0 the west half, B1 the east half) or a small lens of one cell (S); ground (0) above it;
    # a one pixel soft outline (2) runs round the cloud
    "B0": ["00000022", "00022111", "00211111", "02111111", "21111111", "11111111", "11111111", "11111111"],
    "B1": ["22000000", "11122000", "11111200", "11111120", "11111112", "11111111", "11111111", "11111111"],
    "S": ["00022000", "00211200", "02111120", "21111112", "11111111", "11111111", "11111111", "11111111"],
    "CNW": ["00000022", "00002111", "00211111", "02111111", "02111111", "21111111", "21111111", "21111111"],
    "INW": ["00211111", "02111111", "21111111", "11111111", "11111111", "11111111", "11111111", "11111111"],
}
EDGE_SEQ = ["B0", "B1", "S", "B0", "B1", "S", "S", "B0", "B1", "B0", "B1", "S"]


def turn(t, n=1):
    """a quarter turn clockwise of one of my own tiles, n times"""
    for _ in range(n % 4):
        t = ["".join(t[7 - c][r] for c in range(8)) for r in range(8)]
    return t
