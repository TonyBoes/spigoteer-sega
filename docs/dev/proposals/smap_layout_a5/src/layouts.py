"""Layout data for the story-map proposals: where the venue pictures, roads, biomes and scenery go.  Placement only, no pixels.

A layout is a grid of lanes.  A venue picture stands on a horizontal lane (the road in front of it; the stop is on that road); the lanes are
joined by risers at the map's edges or in the gaps between columns; the loop is one closed road and the stops lie on it in the chapter order.
build(...) returns a namespace with the names world2.py reads:
  CW, CH, VENUES, ORDER, STOP_LOCAL_X, ROAD_ROW, ROAD_BOXES, BIOMES, BITES, SCENERY, APRON, FIELDS, legs(STOPS), TOWN_ZONE
Scenery: today's land kit, every group moving with its venue (same pieces, same arrangement); an item that no longer fits (road, another venue,
the map's edge, other ground) is dropped and listed in DROPPED.
"""
from types import SimpleNamespace

import decor  # noqa: F401  (the pieces the scenery list holds)
import lay_today as T

ORDER = ["saloon", "stadium", "lodge", "bistro", "igloo", "factory", "cow", "tea", "zoo", "space"]
MODS = {n: "v_" + n for n in T.VENUES}
BIOME_PAL = {"grass": "grass", "forest": "grass", "farmcow": "cow", "paved": "stadium", "plaza": "bistro", "snow": "igloo", "yard": "factory", "farm": "farm",
             "desert": "saloon", "jungle": "zoo", "moss": "tea"}
# picture sizes in cells (w, h), from today's footprints (the pictures are not touched)
SZ = {"saloon": (9, 7), "stadium": (10, 7), "lodge": (10, 8), "bistro": (9, 7), "igloo": (10, 6), "factory": (10, 7), "cow": (10, 7),
      "tea": (12, 7), "zoo": (10, 7), "space": (14, 9), "town": (12, 9)}
CW = 64
XW, XE = 8, 504                                   # feet x of the vertical roads on the map's west edge (cells 0, 1) and east edge (cells 62, 63)


def riser(c):
    """feet x of a vertical road whose two cells are c and c + 1"""
    return 8 * (c + 1)


def road_cells(legs):
    """the cells of every road: a leg's segments are 2 cells wide (16 px), corners take both cells"""
    cells = set()
    for pts in legs.values():
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            if y0 == y1:                                               # horizontal: the road's upper cell row is (y - 12) // 8
                r = (y0 - 12) // 8
                a, b = sorted((x0, x1))
                for cx in range(a // 8 - (1 if a % 8 == 0 else 0), b // 8 + 1):
                    cells |= {(cx, r), (cx, r + 1)}
            else:                                                      # vertical at x = 8 * (c + 1)
                assert x0 == x1 and x0 % 8 == 0, (x0, y0, x1, y1)
                c = x0 // 8 - 1
                a, b = sorted((y0, y1))
                for cy in range((a - 12) // 8, (b - 12) // 8 + 2):
                    cells |= {(c, cy), (c + 1, cy)}
    return cells


def boxes(cells):
    """cells -> boxes (x0, y0, x1, y1): runs along each row"""
    out = []
    for y in sorted({c[1] for c in cells}):
        xs = sorted(c[0] for c in cells if c[1] == y)
        s = p = xs[0]
        for x in xs[1:]:
            if x != p + 1:
                out.append((s, y, p, y))
                s = x
            p = x
        out.append((s, y, p, y))
    return out


def today_items():
    """today's scenery, each item with the venue it belongs to and its offset from that venue's top-left corner in pixels"""
    S = T.SCENERY
    own = (["lodge"] * 7 + ["tea"] * 3 + ["zoo"] * 3 + ["cow"] + ["saloon"] * 4 + ["saloon"] + ["space"] * 2 + ["igloo"] * 4 + ["igloo"] * 6 +
           ["igloo"] * 5 + ["town"] * 12 + ["cow"] * 7)
    assert len(S) == len(own), (len(S), len(own))
    out = []
    for (pc, x, y), o in zip(S, own):
        vx, vy = T.VENUES[o][1]
        out.append((o, pc, x - vx * 8, y - vy * 8))
    return out


TODAY_ITEMS = today_items()


def build(place, legs_fn, assign, patch=None, P=17, L0=11, cols=(3, 27, 50), margin=6, drop=(), fields=(), bandx=((0, 24), (25, 49), (50, 63)), bandy=None,
          xoff=None, rows=4, lanes=None, cap=212, lands=()):
    """place {venue: (col, row)}; legs_fn(S, Y) -> {(a, b): feet waypoints} with S the stops' feet and Y the lanes' feet y; assign {(col, row): biome};
    xoff {venue: extra cells right of its column's x}; lanes: the lane rows when they are not L0 + P * r"""
    import os
    if os.environ.get('SMAP_COLS'):
        cols = tuple(int(v) for v in os.environ['SMAP_COLS'].split(','))
    L = lanes or [L0 + P * r for r in range(rows)]
    CH = L[-1] + 2 + margin
    Y = [8 * l + 12 for l in L]
    xoff = xoff or {}
    VENUES, ROAD_ROW = {}, {}
    for n, (c, r) in place.items():
        w, h = SZ[n]
        VENUES[n] = (MODS[n], (cols[c] + xoff.get(n, 0), L[r] - h))
        ROAD_ROW[n] = L[r]
    ns = SimpleNamespace(CW=CW, CH=CH, VENUES=VENUES, ORDER=ORDER, STOP_LOCAL_X=T.STOP_LOCAL_X, ROAD_ROW=ROAD_ROW)
    ns.L, ns.Y, ns.place, ns.P, ns.cols = L, Y, place, P, cols

    def legs(S):
        ns.LEGS = legs_fn(S, Y)
        return ns.LEGS
    ns.legs = legs
    S0 = {n: (VENUES[n][1][0] * 8 + T.STOP_LOCAL_X[n], ROAD_ROW[n] * 8 + 12) for n in VENUES}
    legs(S0)
    ns.ROAD_BOXES = boxes(road_cells(ns.LEGS))
    import scene
    return scene.compose(ns, assign, patch or {}, bandx, bandy, drop, cap, fields, lands)
