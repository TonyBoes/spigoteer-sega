"""Round 2: the scrolling world, 64 x 48 cells (512 x 384 px), composed of hand-typed pieces.
Placement only: where each vignette, tree, road and fog cell goes is decided here by hand; the pixels are in v_*.py, tiles.py, decor.py."""
import importlib

import pal as palmod
import tiles
from tiles import GROUND, ROAD, FOG, FIELD, FIELD_EDGE, COBBLE, COBBLE_B, EDGE_SEQ, turn
import decor

CW, CH = 64, 48
PW, PH = CW * 8, CH * 8

# ---- venues: name -> (module, top-left cell) ---------------------------------------------------------------------------------------------
VENUES = {
    "saloon": ("v_saloon", (3, 23)), "stadium": ("v_stadium", (3, 5)), "lodge": ("v_lodge", (22, 4)), "bistro": ("v_bistro", (38, 5)),
    "igloo": ("v_igloo", (53, 6)), "factory": ("v_factory", (39, 14)), "cow": ("v_cow", (39, 23)), "tea": ("v_tea", (29, 36)),
    "zoo": ("v_zoo", (17, 36)), "space": ("v_space", (1, 34)), "town": ("v_town", (22, 21)),
}
ORDER = ["saloon", "stadium", "lodge", "bistro", "igloo", "factory", "cow", "tea", "zoo", "space"]    # chapters 1 to 10
# where Sal stands on the road in front of each: the middle of his feet, in pixels of the venue's own picture
STOP_LOCAL_X = {"saloon": 19, "stadium": 28, "lodge": 26, "bistro": 30, "igloo": 24, "factory": 16, "cow": 18, "tea": 56, "zoo": 12, "space": 24,
                "town": 48}
# the road row each venue's stop is on (cell row of the road's upper cell)
ROAD_ROW = {"saloon": 30, "stadium": 12, "lodge": 12, "bistro": 12, "igloo": 12, "factory": 21, "cow": 30, "tea": 43, "zoo": 43, "space": 43,
            "town": 30}

# ---- roads: 16 px wide, as boxes of cells (x0, y0, x1, y1) -------------------------------------------------------------------------------------
ROAD_BOXES = [
    (3, 12, 62, 13),        # the north road: stadium, lodge, bistro, igloo
    (13, 12, 14, 31),       # the west spine
    (3, 30, 51, 31),        # the trunk: saloon, the town, the cow
    (50, 12, 51, 44),       # the east spine
    (39, 21, 51, 22),       # the factory's road
    (1, 43, 51, 44),        # the south road: teahouse, zoo, space
]

# ---- biomes: boxes of cells, painted in this order (later over earlier); the ground tiles come from tiles.GROUND -------------------------------------
BIOMES = [
    ("grass", [(0, 0, 63, 47)]),
    ("forest", [(17, 0, 36, 13), (16, 8, 17, 13), (19, 14, 24, 15), (34, 14, 37, 15)]),
    ("paved", [(0, 0, 15, 13), (16, 1, 16, 9), (0, 14, 4, 15), (5, 14, 8, 14)]),
    ("plaza", [(37, 0, 49, 13), (36, 5, 36, 10), (37, 14, 38, 14)]),
    ("snow", [(51, 0, 63, 21), (50, 0, 50, 6), (52, 22, 63, 24), (56, 25, 63, 26)]),
    ("yard", [(38, 13, 49, 22), (36, 15, 37, 20)]),
    ("farm", [(39, 23, 49, 36), (38, 32, 38, 36), (50, 23, 63, 41), (36, 25, 37, 31), (40, 37, 49, 39), (52, 42, 63, 47)]),
    ("desert", [(0, 14, 15, 47), (16, 18, 17, 25), (16, 33, 16, 47), (0, 44, 26, 47), (16, 40, 19, 47)]),
    ("jungle", [(17, 32, 28, 47), (15, 40, 16, 47), (29, 45, 30, 47)]),
    ("moss", [(29, 34, 49, 47), (28, 36, 28, 44)]),
    ("farmcow", [(52, 23, 52, 41)]),                                # the farm's first column east of the spine takes the cow's palette (same ground colour: a path window keeps 9 palettes)
    ("grass", [(16, 15, 37, 29)]),                                  # the land round the town (the block between the roads); the factory's yard and the farm stop at x 38
]
# bites out of the straight borders, by hand: (x, y, biome) cells that cross a border one way or the other
BITES = [(36, 1, "plaza"), (36, 2, "plaza"), (37, 3, "forest"), (37, 4, "forest"), (36, 8, "plaza"), (37, 9, "forest"), (36, 10, "forest"),
         (49, 1, "snow"), (49, 2, "snow"), (50, 4, "plaza"), (50, 5, "plaza"), (49, 8, "snow"), (49, 9, "snow"), (50, 10, "plaza"),
         (16, 2, "forest"), (16, 3, "forest"), (15, 5, "forest"), (16, 7, "paved"), (17, 8, "paved"), (16, 10, "forest"), (15, 11, "forest"),
         (55, 21, "farm"), (56, 21, "farm"), (60, 22, "snow"), (61, 22, "snow"), (53, 23, "snow"), (62, 24, "snow"),
         (28, 33, "moss"), (29, 33, "moss"), (28, 41, "jungle"), (29, 40, "jungle"), (28, 44, "moss"), (28, 46, "moss"), (29, 47, "jungle"),
         (15, 34, "jungle"), (15, 45, "desert"), (16, 46, "desert"), (16, 38, "jungle")]
BIOME_PAL = {"grass": "grass", "forest": "grass", "paved": "stadium", "plaza": "bistro", "snow": "igloo", "yard": "factory", "farm": "farm",
             "desert": "saloon", "jungle": "zoo", "moss": "tea", "farmcow": "cow"}
BIOME_TILES = {"grass": "grass", "forest": "forest", "paved": "paved", "plaza": "plaza", "snow": "snow", "yard": "yard", "farm": "farm",
               "desert": "desert", "jungle": "jungle", "moss": "moss", "farmcow": "farm"}
# ---- scenery placed by hand: (piece, x px, y px); one list for both models (the land kit, owner 11-06) ---------------------------------------------------------
# Every piece stands on flat ground (put_decor wipes the tuft under it) and on the 8 px phase of the same piece inside its venue (the lodge's pines on the grid,
# the zoo's tree one pixel off it, the igloo's spruces on the grid and its drifts at y = 7 mod 8), so a tree on the land is the very tiles of the venue's tree.
SCENERY = [
    (decor.PINE, 144, 8), (decor.PINE, 152, 32), (decor.PINE, 144, 56), (decor.PINE, 264, 8), (decor.PINE, 264, 40),
    (decor.PINE, 160, 72), (decor.PINE, 168, 8),
    (decor.BUSH, 240, 256), (decor.BUSH, 264, 256), (decor.BUSH, 288, 256), (decor.JUNGLE_TREE, 148, 259), (decor.JUNGLE_BUSH, 184, 264),
    (decor.JUNGLE_BUSH, 208, 264),
    (decor.HAY, 440, 264),
    (decor.ROCK, 8, 120), (decor.ROCK, 80, 152), (decor.ROCK, 24, 136), (decor.ROCK, 88, 128),
    (decor.ROCK, 8, 264), (decor.ROCK, 24, 368), (decor.ROCK, 104, 368),
    (decor.SPRUCE, 432, 8), (decor.SPRUCE, 456, 0), (decor.SPRUCE, 480, 8), (decor.SPRUCE, 496, 0),
    (decor.SPRUCE, 424, 120), (decor.SPRUCE, 456, 128), (decor.SPRUCE, 480, 120), (decor.SPRUCE, 496, 144), (decor.SPRUCE, 440, 144), (decor.SPRUCE, 472, 152),
    (decor.MOUND, 472, 31), (decor.MOUND, 424, 31), (decor.MOUND, 448, 159), (decor.MOUND, 424, 159), (decor.MOUND, 488, 167),
    # the land round the town: a pine grove along the west spine, round trees and bushes north and east of the hall
    (decor.PINE, 136, 128), (decor.PINE, 152, 152), (decor.PINE, 136, 176), (decor.PINE, 152, 200),
    (decor.ROUND, 204, 123), (decor.ROUND, 244, 131), (decor.BUSH, 184, 152), (decor.BUSH, 232, 152),
    (decor.PINE, 272, 128), (decor.PINE, 288, 152), (decor.ROUND, 276, 171), (decor.BUSH, 280, 208),
    (decor.BARN, 448, 192), (decor.HAY, 432, 232), (decor.HAY, 472, 240), (decor.HAY, 496, 224), (decor.HAY, 432, 296), (decor.HAY, 480, 328), (decor.HAY, 448, 360),
]
# crop fields on the farm east of the spine: (x0, y0, x1, y1) cells
# the town's paved apron along the trunk road (cell row 29): the picture's own cobbles continue two cells past the hall on each side (the same two tiles, the same parity)
APRON = [(x, 29) for x in (20, 21, 34, 35)]
FIELDS = [(53, 27, 62, 31), (53, 34, 62, 38)]

# ---- the stops and the paths ---------------------------------------------------------------------------------------------------------------------------
# palettes folded to keep a 21 x 19 window within the 8 BG palettes (the roads take the town palette, TOWN1: cream, skin, lilac)
MERGE = {"forest": "grass", "desert": "saloon", "factory_b": "factory", "zoogate": "zoo", "tea_b": "tea", "town3": "town5"}

FEET_DY = 12                                                      # feet are 12 px below the top of the road
SW, SH = 16, 24                                                   # Sal's size


def stop_xy(name):
    mod, (cx, cy) = VENUES[name]
    return cx * 8 + STOP_LOCAL_X[name], ROAD_ROW[name] * 8 + FEET_DY


STOPS = {n: stop_xy(n) for n in VENUES}
# junctions (feet positions): west spine x 112 (cells 13, 14), east spine x 408 (50, 51)
WX, EX = 112, 408
NY, TY, SY, FY = 108, 252, 356, 180
LEGS = {                                                          # waypoints between stops (feet positions)
    ("town", "saloon"): [(224, TY), (STOPS["saloon"][0], TY)],
    ("town", "cow"): [(224, TY), (STOPS["cow"][0], TY)],
    ("cow", "factory"): [(STOPS["cow"][0], TY), (EX, TY), (EX, FY), (STOPS["factory"][0], FY)],
    ("cow", "tea"): [(STOPS["cow"][0], TY), (EX, TY), (EX, SY), (STOPS["tea"][0], SY)],
    ("factory", "bistro"): [(STOPS["factory"][0], FY), (EX, FY), (EX, NY), (STOPS["bistro"][0], NY)],
    ("bistro", "igloo"): [(STOPS["bistro"][0], NY), (STOPS["igloo"][0], NY)],
    ("bistro", "lodge"): [(STOPS["bistro"][0], NY), (STOPS["lodge"][0], NY)],
    ("lodge", "stadium"): [(STOPS["lodge"][0], NY), (STOPS["stadium"][0], NY)],
    ("stadium", "saloon"): [(STOPS["stadium"][0], NY), (WX, NY), (WX, TY), (STOPS["saloon"][0], TY)],
    ("tea", "zoo"): [(STOPS["tea"][0], SY), (STOPS["zoo"][0], SY)],
    ("zoo", "space"): [(STOPS["zoo"][0], SY), (STOPS["space"][0], SY)],
}
NEIGH = {}
for (a, b), pts in LEGS.items():
    NEIGH.setdefault(a, {})[b] = pts
    NEIGH.setdefault(b, {})[a] = pts[::-1]


def exit_dir(a, b):
    """the D-pad direction Sal leaves stop a by, towards b: the first step of the leg"""
    pts = NEIGH[a][b]
    (x0, y0), (x1, y1) = pts[0], pts[1]
    return "R" if x1 > x0 else "L" if x1 < x0 else "D" if y1 > y0 else "U"


def leg_points(a, b):
    """the leg as a list of feet positions, one per 3 px step (Sal walks 3 px a frame)"""
    pts = NEIGH[a][b]
    out = [pts[0]]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        n = max(abs(x1 - x0), abs(y1 - y0))
        sx = 0 if x1 == x0 else (1 if x1 > x0 else -1)
        sy = 0 if y1 == y0 else (1 if y1 > y0 else -1)
        for k in range(3, n + 1, 3):
            out.append((x0 + sx * k, y0 + sy * k))
        if (out[-1] != (x1, y1)):
            out.append((x1, y1))
    return out


# ---- the world ------------------------------------------------------------------------------------------------------------------------------------------
class World:
    def __init__(self, dmg=False):
        self.dmg = dmg                                              # the DMG data set: hand-trimmed variants (round 5), same cells, same kinds
        self.px = [[0] * PW for _ in range(PH)]
        self.pal = [[None] * CW for _ in range(CH)]               # palette name per cell
        self.kind = [[None] * CW for _ in range(CH)]               # 'ground', venue name, 'road', 'decor'
        self.ground_pal = [[None] * CW for _ in range(CH)]         # the biome's palette under whatever is on the cell
        self.biome = [[None] * CW for _ in range(CH)]
        self.venue_rect = {}
        self.build()

    # -- helpers
    def set_tile(self, cx, cy, rows, pal, kind):
        for j in range(8):
            r = rows[j]
            for i in range(8):
                self.px[cy * 8 + j][cx * 8 + i] = int(r[i])
        self.pal[cy][cx] = pal
        self.kind[cy][cx] = kind

    def tile(self, cx, cy):
        return tuple("".join(str(self.px[cy * 8 + j][cx * 8 + i]) for i in range(8)) for j in range(8))

    def build(self):
        # biomes
        for name, boxes in BIOMES:
            for (x0, y0, x1, y1) in boxes:
                for cy in range(y0, y1 + 1):
                    for cx in range(x0, x1 + 1):
                        self.biome[cy][cx] = name
        for (x, y, b) in BITES:
            self.biome[y][x] = b
        # ground tiles: the variants are placed by a fixed pattern of mine (no randomness), mostly the flat one
        for cy in range(CH):
            for cx in range(CW):
                b = self.biome[cy][cx]
                vs = GROUND[BIOME_TILES[b]]                         # the flat tile and one tuft per biome (forest: one needle tile), the same for both models
                h = (cx * 7 + cy * 13 + cx * cy) % 13
                v = vs[0] if h not in (3, 8, 11) or len(vs) == 1 else vs[1]
                if b == "forest":
                    v = vs[1] if h % 4 else vs[3]
                self.set_tile(cx, cy, v, BIOME_PAL[b], "ground")
                self.ground_pal[cy][cx] = BIOME_PAL[b]
        # crop fields on the farm
        for (x0, y0, x1, y1) in FIELDS:
            for cy in range(y0, y1 + 1):
                for cx in range(x0, x1 + 1):
                    self.set_tile(cx, cy, FIELD_EDGE if cy == y0 else FIELD, "farm", "ground")
        for (cx, cy) in APRON:
            self.set_tile(cx, cy, COBBLE if (cx + cy) % 2 == 0 else COBBLE_B, "town1", "ground")
            self.ground_pal[cy][cx] = "town1"
        # the road cells
        self.roads = set()
        for (x0, y0, x1, y1) in ROAD_BOXES:
            for cy in range(y0, y1 + 1):
                for cx in range(x0, x1 + 1):
                    self.roads.add((cx, cy))
        # venues: paste the pictures (they override ground); roads are drawn after, but never over a venue
        for name, (modname, (cx0, cy0)) in VENUES.items():
            c = importlib.import_module(modname).build(dmg=self.dmg)
            rows = c.out()
            cps = c.cellpals()
            h, w = len(rows), len(rows[0])
            self.venue_rect[name] = (cx0, cy0, cx0 + w // 8 - 1, cy0 + h // 8 - 1)
            for j in range(h // 8):
                for i in range(w // 8):
                    cell = tuple(rows[j * 8 + k][i * 8:i * 8 + 8] for k in range(8))
                    pal = cps[j][i]
                    pal = MERGE.get(pal, pal)
                    assert (cx0 + i, cy0 + j) not in self.roads, (name, cx0 + i, cy0 + j)
                    self.set_tile(cx0 + i, cy0 + j, cell, pal, name)
        # scenery
        self.bad = []
        for (pc, x, y) in SCENERY:
            self.put_decor(pc, x, y)
        # roads
        for (cx, cy) in sorted(self.roads):
            n, e, s, w = ((cx, cy - 1) in self.roads, (cx + 1, cy) in self.roads, (cx, cy + 1) in self.roads, (cx - 1, cy) in self.roads)
            nw, ne, se, sw = ((cx - 1, cy - 1) in self.roads, (cx + 1, cy - 1) in self.roads, (cx + 1, cy + 1) in self.roads, (cx - 1, cy + 1) in self.roads)
            self.set_tile(cx, cy, self.road_tile(cx, cy, n, e, s, w, nw, ne, se, sw), "town1", "road")

    def road_tile(self, cx, cy, n, e, s, w, nw, ne, se, sw):
        f = ROAD["F1"] if (cx + cy) % 2 == 0 or self.dmg else ROAD["F2"]          # DMG: one speckled road tile
        if not n and not w:
            return ROAD["CNW"]
        if not n and not e:
            return ROAD["CNE"]
        if not s and not w:
            return ROAD["CSW"]
        if not s and not e:
            return ROAD["CSE"]
        if not n:
            return ROAD["EN"]
        if not s:
            return ROAD["ES"]
        if not w:
            return ROAD["EW"]
        if not e:
            return ROAD["EE"]
        return f

    def put_decor(self, pc, x, y):
        pal, rows = pc
        h, w = len(rows), len(rows[0])
        # a piece stands on flat ground: the tuft under it is not drawn (the same piece is then the same tiles wherever it stands)
        cells = [(cx, cy) for cy in range(y // 8, (y + h - 1) // 8 + 1) for cx in range(x // 8, (x + w - 1) // 8 + 1)]
        if all(0 <= cx < CW and 0 <= cy < CH and (cx, cy) not in self.roads and self.kind[cy][cx] in ("ground", "decor") and self.pal[cy][cx] == pal
               for cx, cy in cells):
            for cx, cy in cells:
                if self.kind[cy][cx] == "ground":
                    for j in range(8):
                        for i in range(8):
                            self.px[cy * 8 + j][cx * 8 + i] = 0
        for j in range(h):
            for i in range(w):
                ch = rows[j][i]
                X, Y = x + i, y + j
                cx, cy = X // 8, Y // 8
                if not (0 <= cx < CW and 0 <= cy < CH):
                    self.bad.append((x, y, "off"))
                    return
        # all cells it touches must be plain ground of the same palette, and not on a road
        for cy in range(y // 8, (y + h - 1) // 8 + 1):
            for cx in range(x // 8, (x + w - 1) // 8 + 1):
                if (cx, cy) in self.roads or self.kind[cy][cx] not in ("ground", "decor") or self.pal[cy][cx] != pal:
                    self.bad.append((x, y, (cx, cy), self.kind[cy][cx], self.pal[cy][cx], pal))
                    return
        for j in range(h):
            for i in range(w):
                ch = rows[j][i]
                if ch != ".":
                    self.px[y + j][x + i] = int(ch)
        for cy in range(y // 8, (y + h - 1) // 8 + 1):
            for cx in range(x // 8, (x + w - 1) // 8 + 1):
                self.kind[cy][cx] = "decor"


# ---- the fog ---------------------------------------------------------------------------------------------------------------------------------------------
GROUND_OWNER = {"stadium": "stadium", "bistro": "bistro", "igloo": "igloo", "factory": "factory", "saloon": "saloon", "zoo": "zoo", "tea": "tea", "farm": "cow", "cow": "cow"}


def zone_of_cell(w, cx, cy):
    """the venue a cell belongs to: a venue's own cells, the town block, else the nearest stop"""
    k = w.kind[cy][cx]
    if k in VENUES:
        return k
    tx0, ty0, tx1, ty1 = 18, 17, 37, 29                    # the town's zone is the block between the roads (16 to 39 x 15 to 31), whatever the picture's size
    if tx0 - 2 <= cx <= tx1 + 2 and ty0 - 2 <= cy <= ty1 + 2:
        return "town"
    gp = w.ground_pal[cy][cx]
    if k in ("ground", "decor") and gp in GROUND_OWNER and not (gp == "saloon" and cy > 31):      # (the desert round the space lounge is not the saloon's)
        return GROUND_OWNER[gp]                                   # a biome's ground is revealed with its own venue
    if k in ("ground", "decor") and w.biome[cy][cx] == "forest":
        return "lodge"
    best, name = 10 ** 9, None
    px, py = cx * 8 + 4, cy * 8 + 4
    for n, (sx, sy) in STOPS.items():
        if n == "town":
            continue
        d = (px - sx) ** 2 + (py - (sy - 20)) ** 2
        if d < best:
            best, name = d, n
    return name


def fog_tiles(w, fog):
    """{cell: (rows, palette)} for every fogged cell.  Interior cells take the billow pattern by parity; a cell with one revealed side takes
    the next tile of the edge sequence (lens, lens, small lens, ...) counted along its run; two adjacent revealed sides take the corner."""
    def isf(x, y):
        return (x, y) in fog or not (0 <= x < CW and 0 <= y < CH)

    kinds = {}
    for (cx, cy) in fog:
        n, e, s, wv = isf(cx, cy - 1), isf(cx + 1, cy), isf(cx, cy + 1), isf(cx - 1, cy)
        kinds[(cx, cy)] = (not n, not e, not s, not wv)
    out = {}
    D = ((1, 0), (0, 1), (-1, 0), (0, -1))                       # the direction an edge sequence runs for sides N, E, S, W
    for (cx, cy), op in kinds.items():
        ground = w.ground_pal[cy][cx]
        if w.kind[cy][cx] in VENUES:
            ground = w.pal[cy][cx]
            if ground.startswith("town"):
                ground = "town1"
            elif ground == "tea":
                ground = "tea"
        k = sum(op)
        if k == 0:
            diag = [not isf(cx - 1, cy - 1), not isf(cx + 1, cy - 1), not isf(cx + 1, cy + 1), not isf(cx - 1, cy + 1)]
            if any(diag):
                out[(cx, cy)] = (turn(FOG["INW"], diag.index(True)), "fog:" + ground)
            else:
                out[(cx, cy)] = (FOG[("FA", "FB", "FC", "FD")[(cx % 2) + 2 * (cy % 2)]], "fog:fogbase")
            continue
        if k == 2 and (op[0] != op[2]) and (op[1] != op[3]):
            t = {(True, False, False, True): 0, (True, True, False, False): 1, (False, True, True, False): 2, (False, False, True, True): 3}[op]
            out[(cx, cy)] = (turn(FOG["CNW"], t), "fog:" + ground)
            continue
        side = op.index(True)
        dx, dy = D[side]
        run, x, y = 0, cx - dx, cy - dy
        while kinds.get((x, y)) == op:
            run += 1
            x, y = x - dx, y - dy
        out[(cx, cy)] = (turn(FOG[EDGE_SEQ[run % len(EDGE_SEQ)]], side), "fog:" + ground)
    # an interior cloud tile has no ground pixel, so it can take any fog palette: the one of the nearest open cell (fewer palettes in a window)
    near, frontier = {}, []
    for y in range(CH):
        for x in range(CW):
            if (x, y) not in fog:
                near[(x, y)] = FOGCLASS.get(w.ground_pal[y][x], "fogbase")
                frontier.append((x, y))
    while frontier:
        nxt = []
        for (x, y) in frontier:
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                c = (x + dx, y + dy)
                if 0 <= c[0] < CW and 0 <= c[1] < CH and c not in near:
                    near[c] = near[(x, y)]
                    nxt.append(c)
        frontier = nxt
    res = {}
    edge_classes = [FOGCLASS.get(p[4:], "fogbase") for c, (t, p) in out.items() if p != "fog:fogbase"]
    inner = max(set(edge_classes), key=edge_classes.count) if edge_classes else "fogbase"
    for c, (t, p) in out.items():
        if p == "fog:fogbase":
            res[c] = (t, "fog:" + inner)
        else:
            res[c] = (t, "fog:" + FOGCLASS.get(p[4:], "fogbase"))
    return res


# the cloud edge shows the ground behind it in one of three colours (at most three fog palettes in any window): green, warm, or the cool light of the rest
FOGCLASS = {"grass": "grass", "lodge": "grass", "farm": "grass", "cow": "grass", "tea": "grass", "zoo": "grass", "saloon": "saloon", "town1": "saloon", "base": "saloon"}


def with_fog(w, revealed):
    """a copy of the world picture with every cell of an unrevealed zone replaced by cloud"""
    import copy
    v = copy.copy(w)
    v.px = [r[:] for r in w.px]
    v.pal = [r[:] for r in w.pal]
    v.kind = [r[:] for r in w.kind]
    fog = {(cx, cy) for cy in range(CH) for cx in range(CW) if ZONE[cy][cx] not in revealed}
    for (cx, cy), (rows, pal) in sorted(fog_tiles(w, fog).items()):
        v.set_tile(cx, cy, rows, pal, "fog")
    v.fog = fog
    return v


WORLD = World()
WORLD_DMG = World(dmg=True)
import palsnap
SNAPPED = palsnap.snap(WORLD, verbose=False)          # cells moved to a neighbouring ground so that no 21 x 19 window needs more than 8 palettes
ZONE = [[zone_of_cell(WORLD, cx, cy) for cx in range(CW)] for cy in range(CH)]
SNAPPED2 = palsnap.snap_states(verbose=False)       # ... and again with the cloud in, for every unlock state
