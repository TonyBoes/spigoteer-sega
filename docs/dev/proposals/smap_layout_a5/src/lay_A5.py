"""Layout A5 (A4 with: a river from the top ranges, the lake and pond reshaped, the factory yard, the town edge on the grass; A4: A3 with a flow logic: why each place is where it is): the loop is A3's ring (one road, no crossroads, no dead end, no backtracking, no fog,
no flat pad), the order is saloon, stadium, bistro, IGLOO, LODGE, factory, cow, tea, zoo, space, town; the land follows the story in NOTES.md.

Everything below the legs is typed by hand: the biome map is a grid of letters (rows of 64, run lengths typed), the water is a typed mask (rows and runs),
the scenery is lists of cell coordinates per piece.  Placement only.  The two placeholders (the baseball park, the space lounge with its mountain) and the three
mountain ranges are marked boxes (a4art.Box), not art.  Pieces stand on the 8 px phase they have in today's map (PINE and BUSH on the grid, ROUND and
JUNGLE_TREE at +4, +3, MOUND at y + 7), so every copy is the very tiles of today's pieces.
"""
import os

import decor
import a5art as a4art
import layouts
import lay_today as T

ORDER = ["saloon", "stadium", "bistro", "igloo", "lodge", "factory", "cow", "tea", "zoo", "space"]    # owner 11-06: igloo before lodge (Q97 asks him to confirm)
STOP_LOCAL_X = dict(T.STOP_LOCAL_X)
STOP_LOCAL_X.update({"stadium": 72, "space": 88})       # placeholders: the stop is on the middle of the box's front
CW, CH = 64, 70
L = [11, 28, 45, 62]                                     # lane rows (the upper cell of each road)
Y = [8 * l + 12 for l in L]                              # their feet y

VENUES = {
    "stadium": ("ph_stadium5" if os.environ.get("SMAP_GOLD") == "own" else "ph_stadium", (1, 1)), "bistro": ("v_bistro", (20, 4)), "igloo": ("v_igloo", (50, 5)),
    "saloon": ("v_saloon", (3, 21)), "town": ("v_town_a5", (31, 19)), "lodge": ("v_lodge", (52, 20)),
    "space": ("ph_space", (10, 33)), "factory": ("v_factory", (52, 38)),
    "zoo": ("v_zoo", (3, 55)), "tea": ("v_tea", (24, 55)), "cow": ("v_cow", (50, 55)),
}
ROAD_ROW = {"stadium": 11, "igloo": 11, "bistro": 11, "saloon": 28, "town": 28, "lodge": 28, "space": 45, "factory": 45, "zoo": 62, "tea": 62, "cow": 62}


def legs(S):
    N, M, K, Z = Y                                       # north, middle, south-middle and south lanes (feet y)
    WX, EX = 8, 504                                      # the roads on the map's west and east edges
    MX = 408                                             # the road down from the lodge to the factory (it crosses the mill race on a bridge)
    TX = 296                                             # the town's road: from the space lounge's lane up to the town's door
    return {
        ("stadium", "bistro"): [S["stadium"], S["bistro"]],
        ("bistro", "igloo"): [S["bistro"], S["igloo"]],
        ("igloo", "lodge"): [S["igloo"], (EX, N), (EX, M), S["lodge"]],
        ("lodge", "factory"): [S["lodge"], (MX, M), (MX, K), S["factory"]],
        ("factory", "cow"): [S["factory"], (EX, K), (EX, Z), S["cow"]],
        ("cow", "tea"): [S["cow"], S["tea"]],
        ("tea", "zoo"): [S["tea"], S["zoo"]],
        ("zoo", "space"): [S["zoo"], (WX, Z), (WX, K), S["space"]],
        ("space", "town"): [S["space"], (TX, K), S["town"]],
        ("town", "saloon"): [S["town"], S["saloon"]],
        ("saloon", "stadium"): [S["saloon"], (WX, M), (WX, N), S["stadium"]],
    }


# ---- the biome map ----------------------------------------------------------------------------------------------------------------------------------
# g grass, f forest (grass ground, needles), s snow, d desert, j jungle, a farm, y factory yard, l log yard (grass ground, the lodge's palette: the piles' wood)
GRID = [["g"] * CW for _ in range(CH)]


def rect(ch, x0, y0, x1, y1):
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            GRID[y][x] = ch


def spans(ch, rows):
    """rows: {y: (x0, x1)}, typed one by one so that no edge is a straight line"""
    for y, (x0, x1) in rows.items():
        rect(ch, x0, y, x1, y)


# the forest: the foothills east of the bistro, then the whole east side from the snow's edge to the factory (west edge typed row by row, no two rows alike)
spans("f", {0: (30, 63), 1: (31, 63), 2: (29, 63), 3: (32, 63), 4: (31, 63), 5: (32, 63), 6: (31, 63), 7: (33, 63), 8: (32, 63), 9: (31, 63), 10: (33, 63),
            11: (32, 63), 12: (31, 63),
            13: (41, 63), 14: (42, 63), 15: (40, 63), 16: (42, 63), 17: (41, 63), 18: (43, 63), 19: (45, 63), 20: (44, 63), 21: (46, 63), 22: (45, 63), 23: (44, 63),
            24: (46, 63), 25: (45, 63), 26: (44, 63), 27: (46, 63), 28: (43, 63), 29: (44, 63), 30: (42, 63), 31: (44, 63), 32: (43, 63), 33: (44, 63), 34: (43, 63),
            35: (44, 63), 36: (43, 63)})
# the snowfield: the top right corner from the foothills to the edge of the forest (the east edge of the map is the road)
#   A5: the west edge keeps to column 44 or less down to row 14 (the river's snow-white banks run between them), the tongue below it starts east of the river
spans("s", {5: (50, 63), 6: (50, 63), 7: (50, 63), 8: (50, 63), 9: (50, 63), 10: (49, 63), 11: (49, 63), 12: (49, 63),
            13: (49, 63), 14: (49, 63), 15: (52, 63), 16: (53, 63), 17: (54, 63), 18: (57, 63), 19: (60, 63)})
# the desert: from the saloon (the city's outskirts end here) south round the space lounge
spans("d", {21: (2, 12), 22: (2, 13), 23: (2, 15), 24: (2, 14), 25: (2, 16), 26: (2, 15), 27: (2, 17),
            28: (2, 28), 29: (2, 28), 30: (2, 28), 31: (2, 28), 32: (2, 28), 33: (2, 28), 34: (2, 31), 35: (2, 31), 36: (2, 31), 37: (2, 31), 38: (2, 31), 39: (2, 31),
            40: (2, 31), 41: (2, 31), 42: (2, 31), 43: (2, 31), 44: (2, 31), 45: (2, 31), 46: (2, 31)})
# the jungle of the zoo (rows 47 to 49 are scrub between the sand and the trees)
spans("j", {50: (5, 16), 51: (3, 19), 52: (2, 20)})
rect("j", 2, 53, 20, 69)
spans("j", {56: (21, 21), 60: (21, 21), 64: (21, 21), 58: (22, 22)})
# the factory's yard, the log yard on the bank of the mill pond, the farm
#   A5: the yard is the picture's own ten by seven cells (roads on its west, south and east), packed earth; the two gaps between the stacks and the mast are grass
#   notches (blank cells of the picture), and two bits of earth run out north past the log piles
rect("y", 52, 38, 61, 44)
rect("g", 54, 38, 55, 39)
rect("g", 58, 38, 59, 39)
rect("y", 52, 37, 52, 37)
rect("y", 59, 37, 61, 37)
rect("y", 60, 36, 60, 36)
rect("l", 53, 36, 58, 37)
rect("l", 49, 21, 51, 22)
spans("a", {47: (49, 63), 48: (50, 63), 49: (48, 63), 50: (50, 63), 51: (49, 63), 52: (48, 63), 53: (50, 63), 54: (49, 63)})
rect("a", 48, 55, 63, 69)
BIOME_ROWS = ["".join(r) for r in GRID]
NAMES = {"g": "grass", "f": "forest", "s": "snow", "d": "desert", "j": "jungle", "a": "farm", "y": "yard", "l": "logyard"}


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

# ---- the water (a typed mask: rows and runs of cells) ---------------------------------------------------------------------------------------------------
# the river rises at the foot of the snow, runs south through the lodge's forest beside the town, steps one cell west at row 40 and falls into the lake;
# the mill race leaves it at row 32 to the east, crosses the lodge-factory road on a bridge and ends in the factory's mill pond; the lake is the tea house's
WATER = set()


def wrun(rows):
    for y, runs in rows.items():
        for (x0, x1) in runs:
            for x in range(x0, x1 + 1):
                WATER.add((x, y))


# A5: the river rises under the peaks of the top ranges: a falls two cells wide and two high (rows 5 and 6, columns 46 and 47) under the gap between range B
# and range C, a pool three rows deep (rows 7 to 9, columns 45 to 48), then two cells wide through the snow (rows 10 to 13), three wide from the snow's foot
# (row 14), a step west at rows 23 to 25 and back, the old step west at row 40, into the lake.
wrun({y: [(46, 47)] for y in (5, 6)})                              # the falls (special tiles)
wrun({y: [(45, 48)] for y in (7, 8, 9)})                           # the pool
wrun({y: [(46, 47)] for y in range(10, 14)})                       # the stream in the snow
wrun({y: [(45, 47)] for y in range(14, 23)})                       # the river, widening where the snow ends
wrun({y: [(44, 46)] for y in range(23, 26)})                       # a step west
wrun({y: [(45, 47)] for y in range(26, 40)})                       # and back
wrun({y: [(44, 46)] for y in range(40, 49)})                       # ... one cell west, rows 40 to 48
wrun({y: [(48, 52)] for y in (32, 33, 34)})                        # the mill race
# the mill pond, corners rounded (rows 31 to 35)
wrun({31: [(54, 59)], 32: [(53, 60)], 33: [(53, 60)], 34: [(53, 60)], 35: [(54, 59)]})
# A5: the lake's shoreline, row by row (west x, east x): a rounded top where the river comes in, a west bulge at rows 53 and 54, a headland on the west at
# rows 57 and 58, bays on the east at rows 54 and 55 and 60 and 61, lobes between; it runs off the map's south edge
LAKE = {49: (43, 47), 50: (41, 47), 51: (40, 48), 52: (39, 48), 53: (38, 47), 54: (37, 46), 55: (37, 46), 56: (39, 47), 57: (41, 48), 58: (41, 48), 59: (40, 47),
        60: (38, 46), 61: (37, 46), 62: (37, 47), 63: (37, 47), 64: (38, 47), 65: (39, 47), 66: (39, 47), 67: (38, 48), 68: (37, 48), 69: (37, 47)}
# (every run of a shore column is two rows or more, so no water cell has land on three sides: the tile lookup has no end cap)
wrun({y: [LAKE[y]] for y in range(49, 70)})
# the river in the snow (rows 14 and above) has snow banks: its cells take the palette 'igloo' (index 0 snow white), the same tiles
WATER_PAL = {}                                                     # (the river in the snow keeps the water palette: the snow starts east of its bank, the grass bank is the third pixel-column of a bank tile)
SPECIAL_WATER = {(46, 5): "FL_A", (47, 5): "FR_A", (46, 6): "FL_B", (47, 6): "FR_B", (46, 8): "SPL_A", (47, 8): "SPL_B"}
VARIANTS = True                                                    # the second shore tiles on a typed rhythm (a5art.water_tile5)

# the bridges: the lake (the south road, rows 62 and 63, columns 37 to 47) and the mill race (the lodge-factory road, columns 50 and 51, rows 32 to 34)
BRIDGE_CELLS = {}
for x in range(37, 48):
    BRIDGE_CELLS[(x, 62)] = "T"
    BRIDGE_CELLS[(x, 63)] = "B"
for y in (32, 33, 34):
    BRIDGE_CELLS[(50, y)] = "L"
    BRIDGE_CELLS[(51, y)] = "R"
for x in (46, 47):                                                 # A5: the bistro-igloo road crosses the stream in the snow on a short bridge (rows 11 and 12)
    BRIDGE_CELLS[(x, 11)] = "T"
    BRIDGE_CELLS[(x, 12)] = "B"

# the mountain ranges: placeholder boxes (x, y, w, h, palette, assumed distinct tiles); the separate artist draws them
RANGES = [(17, 0, 15, 4, "igloo", 26), (34, 0, 14, 5, "igloo", 30), (48, 0, 16, 5, "igloo", 36)]

# ---- scenery, typed by hand: cell (x, y) of each piece's top left -------------------------------------------------------------------------------------
from scen_A5 import *  # noqa: E402,F401  (the typed lists)

SCENERY = ([(decor.PINE, x * 8, y * 8) for x, y in PINES] + [(decor.ROUND, x * 8 + 4, y * 8 + 3) for x, y in ROUNDS] +
           [(decor.BUSH, x * 8, y * 8) for x, y in BUSHES] + [(decor.JUNGLE_TREE, x * 8 + 4, y * 8 + 3) for x, y in JTREES] +
           [(decor.JUNGLE_BUSH, x * 8, y * 8) for x, y in JBUSHES] + [(decor.SPRUCE, x * 8, y * 8) for x, y in SPRUCES] +
           [(decor.MOUND, x * 8, y * 8 + 7) for x, y in MOUNDS] + [(decor.ROCK, x * 8, y * 8) for x, y in ROCKS] +
           [(a4art.ROCK_SNOW, x * 8, y * 8) for x, y in ROCKS_SNOW] + [(decor.HAY, x * 8, y * 8) for x, y in HAYS] + [(decor.BARN, x * 8, y * 8) for x, y in BARNS] +
           [(a4art.FLOATLOG_H, x * 8, y * 8 + a4art.LOG_DY) for x, y in LOGS_H] + [(a4art.FLOATLOG_V, x * 8 + a4art.LOG_DX, y * 8) for x, y in LOGS_V] +
           [(a4art.LOGPILE, x * 8, y * 8) for x, y in PILES])

APRON = [(29, 27), (30, 27), (43, 27), (44, 27)]       # the cobbles of the hall's front step, two cells past the picture on each side (no ring)
FIELDS = FIELDS_A4
TOWN_ZONE = (27, 15, 46, 29)

# the roads
_S = {n: (VENUES[n][1][0] * 8 + STOP_LOCAL_X[n], ROAD_ROW[n] * 8 + 12) for n in VENUES}
LEGS = legs(_S)
ROAD_BOXES = layouts.boxes(layouts.road_cells(LEGS))
