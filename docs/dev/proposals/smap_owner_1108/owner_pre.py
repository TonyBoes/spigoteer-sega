"""Pre-world hook for the 11-08 owner proposals (mapctx.py calls apply(lay, decor) when env SMAP_PRE_WORLD=owner_pre, before world2 is imported).
Proposal B, the town (flags in env OWNER, e.g. OWNER=B1,B2,B3):

  B1  the tavern's awning (the rightmost building): an ink edge on its left, a peach hem row and an ink fringe (hand-typed below)
  B2  the paving: the cobbles run up to the building fronts (the strip y 60..63 under the tower, the hall and the tavern was bare grass), and a band of the same cobbles lies south of the road,
      so the road runs through the square
  B4  the east end of the paved band south of the road is rounded (post(W), run after the world is built): a quarter circle of r 12 px (the bottom corner only; the top meets the road square), the cut-away
      pixels show the grass (those cells take the grass palette town1@g, whose index 0 is the grass).  The west end lies on sand, which no palette in the table shares with the town's (a cut-away pixel
      would be the town's cream, a third shade): it stays a cell-level step (row 30 one cell further west than row 31).  The lone sand cell of the biome map beside the hall's west wall (22, 26) is paved
  B3  the town moves SHIFT cells west (default 8, env OWNER_SHIFT): the venue cell, the stop, the legs, the apron, the zone, and the trees the new footprint covers move with it

Placement and typed pixels only: nothing is generated.  Everything is read by ctx.py through the flags, so the unflagged map is byte for byte the snapshot."""
import os

FLAGS = set(filter(None, os.environ.get("OWNER", "").replace(" ", "").split(",")))
SHIFT = int(os.environ.get("OWNER_SHIFT", "8"))
OLD = (31, 19)
TOWN_W, TOWN_H = 12, 9                      # the picture, in cells
ROAD_TOP = 28                               # the trunk road's upper cell row
BEND_X = 34                                 # the first cell of the r32 bend at (37, 28): nothing paved from here south of the road


def town_cell():
    return (OLD[0] - SHIFT, OLD[1]) if "B3" in FLAGS else OLD


def cobble_is_a(cx, cy):
    """the paving's two tiles lie in a chequer by the cell's absolute position (world2's rule for the apron: COBBLE where cx + cy is even)"""
    return (cx + cy) % 2 == 0


# ---- B1: the awning (picture px; x 64..95, y 40..47 are the awning's own cells: palette town5 = cream 0, peach 1, gold 2, ink 3) -------------------------------------------------
def awning(c):
    for y in range(41, 47):
        c.px[y][64] = "3"                   # the left edge: ink, like the right end (x 95): the gold stripe is 3 px wide (65..67) as the cream one at the right end is (92..94)
    for x in range(65, 95):
        if c.px[46][x] == "0":
            c.px[46][x] = "1"               # the hem row: the cream stripes darker (peach), the gold ones stay
    for x in range(68, 95, 4):
        c.px[46][x] = "3"                   # an ink fringe at every stripe change: the hem reads as hanging flaps


# ---- B2: cobbles up to the fronts (picture) -----------------------------------------------------------------------------------------------------------------------------------
def cobbles_up(c, cx0, cy0, tiles):
    """y 60..63 (the lower half of cell row 7, 4 px of bare ground under the buildings) take the lower half of the paving tile of the chequer; the basin (x 32..64) already ends at y 63"""
    COBBLE, COBBLE_B = tiles
    for cx in range(12):
        if 4 <= cx <= 7:
            continue
        t = COBBLE if cobble_is_a(cx0 + cx, cy0 + 7) else COBBLE_B
        for j in range(4):
            for i in range(8):
                c.px[60 + j][cx * 8 + i] = t[4 + j][i]
    for cx in range(12):                    # the forecourt row itself (picture row 8) in the same chequer as the cells beside it
        t = COBBLE if cobble_is_a(cx0 + cx, cy0 + 8) else COBBLE_B
        for j in range(8):
            for i in range(8):
                c.px[64 + j][cx * 8 + i] = t[j][i]


def apply(lay, decor):
    import importlib
    import v_town_fx as FX
    import tiles
    B = FX.B
    cx0, cy0 = town_cell()
    prev = B.picture

    def picture():
        c = prev()
        if "B1" in FLAGS:
            awning(c)
        if "B2" in FLAGS:
            cobbles_up(c, cx0, cy0, (tiles.COBBLE, tiles.COBBLE_B))
        return c
    B.picture = picture
    if "B3" in FLAGS or "B2" in FLAGS:
        layout(lay, decor)
    if "Q10" in FLAGS:                      # the owner's Q10 of 11-08: no round trees or bushes, no overlapping pine clusters, the single pines snapped (q10_pre.py)
        import q10_pre
        q10_pre.apply(lay, decor)


def apron_cells(cx0):
    """B2: row 27 two cells past the picture on each side (as before), the paved band south of the road (rows 30, 31), one cell wider than the picture each side, stopping short of the bend"""
    cells = [(cx0 - 2, 27), (cx0 - 1, 27), (cx0 + TOWN_W, 27), (cx0 + TOWN_W + 1, 27)]
    if "B4" in FLAGS:
        cells.append((cx0 - 1, 26))                       # the lone sand cell of the biome map beside the hall's west wall is paved (it read as a third, pale shade between the grass, the paving and the wall)
    if "B2" in FLAGS:
        for y, (a, b) in ((30, (cx0 - 1, cx0 + TOWN_W)), (31, (cx0, cx0 + TOWN_W - 1))):
            cells += [(x, y) for x in range(a, min(b, BEND_X - 1) + 1)]
    return cells


def layout(lay, decor):
    import layouts
    old_x, old_y = OLD
    nx, ny = town_cell()
    mod, _ = lay.VENUES["town"]
    lay.VENUES["town"] = (mod, (nx, ny))
    lay.APRON = apron_cells(nx) if "B2" in FLAGS else [(x - (OLD[0] - nx), y) for (x, y) in lay.APRON]
    d = OLD[0] - nx
    zx0, zy0, zx1, zy1 = lay.TOWN_ZONE
    lay.TOWN_ZONE = (zx0 - d, zy0, zx1 - d, zy1)
    if d:
        orig_legs = lay.legs

        def legs(S):
            L = orig_legs(S)
            TX = 296
            M = S["town"][1]
            K = S["space"][1]
            L[("space", "town")] = [S["space"], (TX, K), (TX, M), S["town"]]      # up the road at the bend, then west along the trunk road to the stop
            return L
        lay.legs = legs
        lay._S = {n: (lay.VENUES[n][1][0] * 8 + lay.STOP_LOCAL_X[n], lay.ROAD_ROW[n] * 8 + 12) for n in lay.VENUES}
        lay.LEGS = lay.legs(lay._S)
        lay.ROAD_BOXES = layouts.boxes(layouts.road_cells(lay.LEGS))
        global lay_now
        lay_now = lay
        lay.SCENERY = relocate(lay.SCENERY, nx, ny, d)


def footprint(item):
    (pal, rows), x, y = item
    return x // 8, y // 8, (x + len(rows[0]) - 1) // 8, (y + len(rows) - 1) // 8


def relocate(scenery, nx, ny, d):
    """the trees whose cells meet the moved town (its picture, the apron, the paved band and one cell of margin) are lifted and set down again on free grass in the ground the town left
    (east of it, west of the river), nearest to where they stood plus d cells; none is dropped, none overlaps another or anything else"""
    import layouts
    zx0, zx1 = nx - 3, nx + TOWN_W + 2
    zy0, zy1 = ny - 1, 32
    keep, lifted = [], []
    for item in scenery:
        x0, y0, x1, y1 = footprint(item)
        (lifted if (x1 >= zx0 and x0 <= zx1 and y1 >= zy0 and y0 <= zy1) else keep).append(item)
    roads = layouts.road_cells(lay_now.LEGS)
    blocked = set(roads)
    for name, (mod, (vx, vy)) in lay_now.VENUES.items():
        w, h = layouts.SZ.get(name, (12, 9))
        blocked |= {(x, y) for x in range(vx - 1, vx + w + 1) for y in range(vy - 1, vy + h + 1)}
    blocked |= set(lay_now.APRON)
    blocked |= {(x, y) for x in range(nx - 3, nx + TOWN_W + 3) for y in range(ny - 1, 32)}
    ground = {ch: {(x, y) for y, row in enumerate(lay_now.BIOME_ROWS) for x, ch2 in enumerate(row) if ch2 == ch} - set(lay_now.WATER) for ch in "gd"}

    def boxes(it):
        (pal, rows), x, y = it
        return (x - 2, y - 2, x + len(rows[0]) + 2, y + len(rows) + 2)

    def clash(a, b):
        return not (a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1])
    placed = [boxes(i) for i in keep]
    out = list(keep)
    MOVED[:] = []
    DROPPED[:] = []
    for (p, x, y) in lifted:
        best = None
        grass = ground["d"] if p[0] == "saloon" else ground["g"]          # a rock stays in the sand, a tree on the grass
        for dy in range(0, 13):
            for dxs in range(0, 13):
                for sgn_y in (1, -1):
                    for sgn_x in (1, -1):
                        X, Y = x + ((0 if p[0] == "saloon" else d) + sgn_x * dxs) * 8, y + sgn_y * dy * 8
                        it = (p, X, Y)
                        x0, y0, x1, y1 = footprint(it)
                        cells = [(cx, cy) for cx in range(x0, x1 + 1) for cy in range(y0, y1 + 1)]
                        if not (0 <= x0 and x1 < (44 if p[0] != 'saloon' else 30) and 0 <= y0 and y1 < 70) or (p[0] != 'saloon' and x1 >= 39 and y0 <= 20):      # (the top right path windows are at 175 of 176 DMG tiles: no new tree tiles in cols 39.. rows ..20)
                            continue
                        if any(c not in grass or c in blocked for c in cells):
                            continue
                        if any(clash(boxes(it), b) for b in placed):
                            continue
                        cost = dxs * dxs + dy * dy
                        if best is None or cost < best[0]:
                            best = (cost, it)
            if best:
                break
        if not best:
            DROPPED.append((x, y))
            continue
        out.append(best[1])
        placed.append(boxes(best[1]))
        MOVED.append(((x, y), (best[1][1], best[1][2])))
    return out


MOVED = []
DROPPED = []


# ---- B4: the band's rounded ends (hand-placed: a quarter circle at each end, the same cobble texture, the ground showing in the cut-away pixels) -------------------------------------------------
def post(W):
    """round the two free ends of the band (rows 30, 31 of cells; the road lies above it).  Both data sets get the same pixels.  Needs B2 (the band) and B3 (the town's place)"""
    cx0 = town_cell()[0]
    x_w = (cx0 - 1) * 8                                  # the band's west end (px)
    x_e = (min(cx0 + TOWN_W, BEND_X - 1) + 1) * 8        # its east end (px, exclusive)
    y0 = 30 * 8
    R = 12
    yc = y0 + 16 - R                                    # the circles' centre row: the top (against the road) stays square, only the bottom corners are cut
    gone = {}
    for (x0, x1, cxc, west) in ((x_e - R, x_e, x_e - R, False),):          # (the west end lies on sand: a cut-away pixel there would show the town palette's cream, a third shade; it stays a cell-level step)
        for y in range(y0, y0 + 16):
            for x in range(x0, x1):
                inside = (x + .5 - cxc) ** 2 + (y + .5 - yc) ** 2 <= R * R or y + .5 <= yc
                if not inside:
                    gone.setdefault((x // 8, y // 8, west), []).append((x, y))
    cells = set()
    for (cx, cy, west), px in gone.items():
        if len(px) <= 1:                                 # a cell that would lose one pixel only stays whole (it would be one more DMG tile for nothing)
            continue
        cells.add((cx, cy, west))
        for (x, y) in px:
            for w in (W.WORLD, W.WORLD_DMG):
                w.px[y][x] = 0
    for (cx, cy, west) in sorted(cells):
        assert W.WORLD.pal[cy][cx] in ("town1", "town1@g"), (cx, cy, W.WORLD.pal[cy][cx])
        if not west:
            for w in (W.WORLD, W.WORLD_DMG):
                w.pal[cy][cx] = "town1@g"
    return sorted(cells)
