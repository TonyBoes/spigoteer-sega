"""The map's layout, hand-placed: ground, biomes, venues, scenery, roads, fog.  (Placement only; pixels are in kit.py and in the
approved v14 picture.)"""
import kit
from world import (World, old, cell_from_rows, rot, road_cell, ROADS, GRASS, SAND, SNOW, CREAM, TOWN)

WHITE = (6, (0,) * 64)                      # the stadium's concrete: a flat tile of palette 6 colour 0


SKIPPED = []


def on(w, ground, x, y, cw=1, ch=1):
    ok = all(0 <= x + i < 32 and 0 <= y + j < 32 and w.c[y + j][x + i] is ground for i in range(cw) for j in range(ch))
    if not ok:
        SKIPPED.append((x, y))
    return ok


def tree(w, x, y, kind=0):
    if on(w, GRASS, x, y, 1, 2):
        w.old(6, 0, 1, 2, x, y)


def deco(w, ground, sx, sy, cw, ch, x, y):
    if on(w, ground, x, y, cw, ch):
        w.old(sx, sy, cw, ch, x, y)


def build():
    w = World()
    w.fill(0, 0, 31, 31, GRASS)
    # ---- biomes: desert in the west, snow in the north-east, a paved yard for the bistro ------------------------------
    sand_rows = {10: 8, 11: 9, 12: 9, 13: 10, 14: 10, 15: 10, 16: 9, 17: 9, 18: 9, 19: 9, 20: 8, 21: 8,
                 22: 8, 23: 8, 24: 7, 25: 7, 26: 7, 27: 7, 28: 8, 29: 11, 30: 11, 31: 11}
    for y, xmax in sand_rows.items():
        w.fill(0, y, xmax, y, SAND)
    snow_rows = {0: 21, 1: 21, 2: 22, 3: 22, 4: 22, 5: 23, 6: 24, 7: 25, 8: 26}
    for y, xmin in snow_rows.items():
        w.fill(xmin, y, 31, y, SNOW)
    w.fill(19, 2, 25, 7, CREAM)
    w.fill(2, 3, 9, 8, WHITE)               # the stadium's yard
    w.fill(*TOWN, CREAM)
    w.fill(9, 11, 22, 11, CREAM)
    # ---- the town: round 6's houses at map scale, the festival's bunting, the fountain, the tent ----------------------
    w.img(10, 13, 4, kit.HOUSE)
    w.img(12, 12, 4, kit.TOWER)
    w.img(14, 14, 4, kit.HALL)
    w.img(20, 13, 4, kit.HOUSE)
    for i, x in enumerate(range(9, 23)):
        w.put(x, 11, cell_from_rows(4, kit.BUNT["AB"[i % 2]]))
    cob = [cell_from_rows(4, kit.COBBLE["1"])] * 2
    for y in range(12, 21):
        for x in range(9, 23):
            if w.c[y][x] is CREAM and (x * 7 + y * 3) % 5 in (0, 2):
                w.put(x, y, cob[(x + y) % 2])
    w.old(10, 8, 3, 3, 15, 16)              # the fountain
    w.old(8, 8, 2, 2, 19, 17)               # the festival tent
    # ---- venues, each in its own room --------------------------------------------------------------------------------
    w.old(1, 9, 3, 3, 3, 17)                # saloon
    w.old(1, 4, 5, 4, 3, 4)                 # stadium (no gate: tiles)
    w.old(1, 0, 5, 3, 12, 3)                # lodge
    w.old(9, 0, 3, 3, 22, 3)                # bistro (palette 4 is the town's now)
    w.old(15, 0, 3, 3, 26, 3)               # igloo
    w.old(15, 5, 4, 3, 25, 8)               # factory
    w.old(15, 10, 5, 3, 25, 19)             # the Chrome Cow
    w.old(15, 13, 5, 1, 25, 22)             # its blue road
    w.old(15, 13, 2, 1, 30, 22)
    w.old(8, 14, 3, 3, 10, 24)              # zoo
    w.old(16, 14, 3, 3, 19, 24)             # teahouse
    w.old(0, 15, 4, 3, 1, 25)               # the desert mountain (the UFO hovers beside it)
    w.img(5, 29, 1, kit.HANGAR)             # air base: hangar, tower, runway
    rw = "DPDPDPDPDPD"
    for i, ch in enumerate(rw):
        w.put(1 + i, 31, cell_from_rows(1, kit.RUNWAY[ch]))
    # ---- scenery: forest round the lodge, bushes, desert stones, the cow field ----------------------------------------
    for (x, y, k) in [(9, 0, 0), (11, 1, 1), (10, 3, 0), (8, 1, 1), (17, 0, 0), (18, 1, 1), (17, 3, 0), (10, 6, 1), (12, 7, 0),
                      (16, 7, 1), (9, 7, 0), (18, 7, 0), (0, 1, 0), (2, 0, 1), (4, 1, 0), (7, 1, 1), (1, 9, 1), (0, 6, 0),
                      (19, 9, 1), (21, 9, 0), (22, 10, 1), (1, 22, 0), (28, 14, 0), (30, 12, 1), (27, 15, 0), (13, 26, 1),
                      (15, 27, 0), (22, 24, 1), (29, 25, 0), (30, 27, 1), (14, 22, 0), (16, 23, 1), (26, 29, 0), (28, 28, 1)]:
        tree(w, x, y, k)
    for (x, y) in [(12, 11), (17, 10), (7, 12), (19, 21), (22, 22), (15, 23), (27, 24), (30, 17), (20, 25), (13, 30), (24, 31),
                   (8, 9), (21, 11), (26, 12), (16, 22)]:
        deco(w, GRASS, 12, 11, 1, 1, x, y)
    # desert
    for (x, y, sx, sy) in [(1, 12, 5, 8), (8, 14, 5, 8), (2, 21, 5, 8), (5, 24, 5, 8), (3, 27, 5, 8), (8, 30, 5, 8), (7, 12, 5, 8),
                           (1, 16, 5, 8), (2, 23, 5, 8)]:
        deco(w, SAND, sx, sy, 1, 1, x, y)
    deco(w, SAND, 3, 13, 1, 2, 7, 25)       # cactus
    deco(w, SAND, 3, 13, 1, 2, 4, 14)
    deco(w, SAND, 3, 13, 1, 2, 1, 18)
    # snow
    for (x, y) in [(24, 0), (28, 1), (30, 3), (30, 7), (27, 8), (22, 1), (31, 5)]:
        if on(w, SNOW, x, y):
            w.put(x, y, cell_from_rows(0, kit.MOUND))
    # the cow field
    for x in range(26, 31):
        w.put(x, 16, cell_from_rows(3, kit.FENCE))
    deco(w, GRASS, 19, 11, 1, 1, 27, 17)
    deco(w, GRASS, 19, 11, 1, 1, 29, 18)
    # ---- roads ----------------------------------------------------------------------------------------------------------
    for (x, y) in sorted(ROADS):
        w.put(x, y, road_cell(x, y))
    return w


# ---- fog ----------------------------------------------------------------------------------------------------------------
# Every cell belongs to one zone, the nearest stop (the square counts as its whole cobbled block); a zone is revealed when its
# venue unlocks, so the fog never leaves a gap.  The partition is a table the engine can hold as a 32 x 32 nibble map (512 B)
# or as rectangles.
from world import STOPS

TOWN_RECT = (9, 11, 22, 20)


def zone_of(x, y):
    best, name = 10 ** 9, None
    for n, (sx, sy) in STOPS.items():
        if n == "town":
            dx = max(TOWN_RECT[0] - x, 0, x - TOWN_RECT[2])
            dy = max(TOWN_RECT[1] - y, 0, y - TOWN_RECT[3])
            d = (dx * dx + dy * dy) * 8 - (1 if dx == 0 and dy == 0 else 0)
        else:
            d = (x - sx) ** 2 + (y - sy) ** 2
        if d < best:
            best, name = d, n
    return name


ZONE = [[zone_of(x, y) for x in range(32)] for y in range(32)]


def fogged(open_zones):
    return {(x, y) for y in range(32) for x in range(32) if ZONE[y][x] not in open_zones}


def apply_fog(w, open_zones):
    fog = fogged(open_zones)
    F0, PA = cell_from_rows(0, kit.FOG["F"]), cell_from_rows(0, kit.FOG["PA"])
    PB = cell_from_rows(0, kit.MOUND)
    EN, CNW, INW = (cell_from_rows(0, kit.FOG[k]) for k in ("EN", "CNW", "INW"))

    def turns(c, n):
        for _ in range(n):
            c = rot(c)
        return c

    def isf(x, y):
        return (x, y) not in w_ground or (x, y) in fog
    w_ground = {(x, y) for y in range(32) for x in range(32)}
    for (x, y) in sorted(fog):
        n, e, s, wv = isf(x, y - 1), isf(x + 1, y), isf(x, y + 1), isf(x - 1, y)
        open_sides = [not n, not e, not s, not wv]      # True where the neighbour is revealed ground
        k = sum(open_sides)
        if k == 0:
            diag = [not isf(x - 1, y - 1), not isf(x + 1, y - 1), not isf(x + 1, y + 1), not isf(x - 1, y + 1)]
            if any(diag):
                w.put(x, y, turns(INW, diag.index(True)))
            else:
                w.put(x, y, PA if (x * x + 3 * y * y + x * y) % 8 == 3 else PB if (x * 3 + y * y * 2 + x * y) % 13 == 5 else F0)
        elif k == 1:
            w.put(x, y, turns(EN, open_sides.index(True)))
        elif k == 2 and (open_sides[0] != open_sides[2]) and (open_sides[1] != open_sides[3]):
            # a corner: which two adjacent sides are open (N+W = 0 turns, N+E = 1, S+E = 2, S+W = 3)
            t = {(True, False, False, True): 0, (True, True, False, False): 1, (False, True, True, False): 2,
                 (False, False, True, True): 3}[tuple(open_sides)]
            w.put(x, y, turns(CNW, t))
        else:
            w.put(x, y, turns(EN, open_sides.index(True)))
    return w
