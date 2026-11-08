"""Layout A3 (A2, second pass: no cloud, no town square, no forecourt or plaza, the south strip cut): layout A's ring (same loop order, same lanes, no junction, no dead end), with a logic pass on the land.

Everything below the legs is typed by hand: the biome map is a grid of letters (one row of 64 per map row, run lengths typed), the scenery is lists of
cell coordinates per piece.  Placement only; no pixel is drawn here.  Pieces stand on the 8 px phase they have in today's map (PINE and BUSH on the grid,
ROUND and JUNGLE_TREE at +4, +3, MOUND at y + 7), so every copy is the very tiles of today's pieces (no new DMG tile).
"""
import decor
import layouts
import lay_today as T

ORDER = ["saloon", "stadium", "bistro", "lodge", "igloo", "factory", "cow", "tea", "zoo", "space"]    # owner 11-06: the lodge and the bistro swapped, the lodge beside the igloo
STOP_LOCAL_X = T.STOP_LOCAL_X
CW, CH = 64, 67
L = [11, 28, 45, 62]                                     # lane rows (the upper cell of each road)
Y = [8 * l + 12 for l in L]                              # their feet y

VENUES = {
    "stadium": ("v_stadium", (3, 4)), "bistro": ("v_bistro", (27, 4)), "lodge": ("v_lodge", (50, 3)),
    "saloon": ("v_saloon", (3, 21)), "town": ("v_town", (27, 19)), "igloo": ("v_igloo", (50, 22)),
    "space": ("v_space", (15, 36)), "factory": ("v_factory", (50, 38)),
    "zoo": ("v_zoo", (3, 55)), "tea": ("v_tea", (27, 55)), "cow": ("v_cow", (50, 55)),
}
ROAD_ROW = {"stadium": 11, "lodge": 11, "bistro": 11, "saloon": 28, "town": 28, "igloo": 28, "space": 45, "factory": 45, "zoo": 62, "tea": 62, "cow": 62}


def legs(S):
    N, M, K, Z = Y                                       # north, middle, south-middle and south lanes (feet y)
    WX, EX = 8, 504                                      # the roads on the map's west and east edges
    MX = 392                                             # the road down between the igloo and the factory
    TX = 264                                             # the town's main street: down from the town's door to the space lounge's lane
    return {
        ("stadium", "bistro"): [S["stadium"], S["bistro"]],
        ("bistro", "lodge"): [S["bistro"], S["lodge"]],
        ("lodge", "igloo"): [S["lodge"], (EX, N), (EX, M), S["igloo"]],
        ("igloo", "factory"): [S["igloo"], (MX, M), (MX, K), S["factory"]],
        ("factory", "cow"): [S["factory"], (EX, K), (EX, Z), S["cow"]],
        ("cow", "tea"): [S["cow"], S["tea"]],
        ("tea", "zoo"): [S["tea"], S["zoo"]],
        ("zoo", "space"): [S["zoo"], (WX, Z), (WX, K), S["space"]],
        ("space", "town"): [S["space"], (TX, K), S["town"]],
        ("town", "saloon"): [S["town"], S["saloon"]],
        ("saloon", "stadium"): [S["saloon"], (WX, M), (WX, N), S["stadium"]],
    }


# ---- the biome map ----------------------------------------------------------------------------------------------------------------------------------
# g grass, f forest (grass ground, needles), s snow, d desert, j jungle, m moss, a farm, y factory yard, p stadium forecourt, z bistro plaza, t town square
GRID = [["g"] * CW for _ in range(CH)]


def rect(ch, x0, y0, x1, y1):
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            GRID[y][x] = ch


def spans(ch, rows):
    """rows: {y: (x0, x1)}, typed one by one so that no edge is a straight line"""
    for y, (x0, x1) in rows.items():
        rect(ch, x0, y, x1, y)


# the lodge's forest in the north-east: start column of each row (it runs to the east road), no two rows alike
spans("f", {0: (39, 63), 1: (40, 63), 2: (38, 63), 3: (40, 63), 4: (39, 63), 5: (41, 63), 6: (39, 63), 7: (40, 63), 8: (38, 63), 9: (41, 63), 10: (39, 63),
            11: (39, 63), 12: (40, 63),
            # ... and the tongue that runs south into the snow, against the snowfield's diagonal edge
            13: (40, 55), 14: (41, 53), 15: (43, 51), 16: (44, 49), 17: (43, 46), 18: (44, 45)})
# the desert of the saloon, west
spans("d", {13: (2, 13), 14: (2, 13), 15: (2, 14), 16: (2, 14), 17: (2, 15), 18: (2, 15), 19: (2, 17), 20: (2, 17), 21: (2, 16), 22: (2, 17), 23: (2, 17), 24: (2, 17),
            25: (2, 16), 26: (2, 17), 27: (2, 16)})
# the snowfield: from the forest's edge to the factory yard, against the east road
spans("s", {13: (56, 63), 14: (54, 63), 15: (52, 63), 16: (50, 63), 17: (47, 63), 18: (46, 63), 19: (43, 63), 20: (43, 63), 21: (45, 63), 22: (46, 63), 23: (46, 63),
            24: (46, 63), 25: (46, 63), 26: (46, 63), 27: (46, 63),
            28: (48, 63), 29: (48, 63), 30: (48, 63), 31: (49, 63), 32: (48, 63), 33: (50, 63), 34: (50, 63), 35: (51, 63)})
# the west desert round the space lounge
rect("d", 2, 28, 31, 46)
spans("d", {})
# the factory's yard
rect("y", 50, 36, 63, 46)
spans("y", {35: (52, 55)})
# farm, moss garden, jungle
spans("a", {47: (47, 63), 48: (45, 63), 49: (46, 63), 50: (45, 63), 51: (44, 63), 52: (45, 63), 53: (44, 63), 54: (45, 63)})
rect("a", 45, 55, 63, 66)
spans("a", {55: (44, 44), 58: (44, 44), 60: (44, 44), 64: (44, 44), 66: (44, 44)})
spans("j", {49: (5, 18), 50: (3, 19), 51: (2, 20), 52: (2, 20), 53: (2, 21), 54: (2, 20)})
rect("j", 2, 55, 20, 66)
spans("j", {56: (21, 21), 60: (21, 21), 64: (21, 21), 58: (2, 2)})
BIOME_ROWS = ["".join(r) for r in GRID]
NAMES = {"g": "grass", "f": "forest", "s": "snow", "d": "desert", "j": "jungle", "m": "moss", "a": "farm", "y": "yard", "p": "paved", "z": "plaza", "t": "townsq"}


def biomes_from_rows():
    out = {}
    for y, row in enumerate(BIOME_ROWS):
        x = 0
        while x < CW:
            x1 = x
            while x1 + 1 < CW and row[x1 + 1] == row[x]:
                x1 += 1
            out.setdefault(NAMES[row[x]], []).append((x, y, x1, y))
            x = x1 + 1
    return [(k, v) for k, v in out.items()]


BIOMES = biomes_from_rows()
BITES = []

# ---- scenery, typed by hand: cell (x, y) of each piece's top left -------------------------------------------------------------------------------------
from scen_A3 import *  # noqa: E402,F401  (the typed lists)

SCENERY = ([(decor.PINE, x * 8, y * 8) for x, y in PINES] + [(decor.ROUND, x * 8 + 4, y * 8 + 3) for x, y in ROUNDS] +
           [(decor.BUSH, x * 8, y * 8) for x, y in BUSHES] + [(decor.JUNGLE_TREE, x * 8 + 4, y * 8 + 3) for x, y in JTREES] +
           [(decor.JUNGLE_BUSH, x * 8, y * 8) for x, y in JBUSHES] + [(decor.SPRUCE, x * 8, y * 8) for x, y in SPRUCES] +
           [(decor.MOUND, x * 8, y * 8 + 7) for x, y in MOUNDS] + [(decor.ROCK, x * 8, y * 8) for x, y in ROCKS] +
           [(decor.HAY, x * 8, y * 8) for x, y in HAYS] + [(decor.BARN, x * 8, y * 8) for x, y in BARNS])

APRON = [(25, 27), (26, 27), (39, 27), (40, 27)]       # the cobbles of the hall's front step, two cells past the picture on each side (no ring)
FIELDS = FIELDS_A3
TOWN_ZONE = (23, 15, 42, 29)

# the roads
_S = {n: (VENUES[n][1][0] * 8 + STOP_LOCAL_X[n], ROAD_ROW[n] * 8 + 12) for n in VENUES}
LEGS = legs(_S)
ROAD_BOXES = layouts.boxes(layouts.road_cells(LEGS))
