"""Rounded road corners (stage 1c, owner: "Round the corners on the road").  Hand-typed pieces; nothing here decides a pixel except by looking up my typed rows.

The road is 16 px wide: 2 px kerb (lilac, index 2), 1 px light line (index 0), body (index 1, a few index 0 specks).  Its straight tiles are tools/smap_world/tiles.py ROAD.
Letters below: g ground (outside the road), k kerb, l light line, b body, o body speck.  DMG value = index: g 0, k 2, l 0, b 1, o 0.

OUTER corner (a road cell with two open sides): the outer kerb edge is a quarter arc of radius 8 over the corner cell, the kerb stays 2 px thick, the line follows, the body fills inside.
The cell now shows ground in its outer corner (13 px), so on Color it takes a palette that has the ground colour as index 0 and keeps the road's cream line:
  ROADG = [map grass, road body, road kerb, road cream]: the line and specks are index 3 in the COLOR data, index 0 in the DMG data (the two data sets are separate; the DMG value is what
  the generator counts).  Two corners sit beside snow / town cobble, not grass: there the cell keeps the road palette TOWN1 (cream is index 0: ground pixels read cream, line cream).

INNER corner (a road cell with all four sides open but one diagonal missing: the ground block's corner pokes into the road): the ground block's corner is rounded with radius 6, the kerb
following it, the light line and body re-cut round it.  The change spans the notch's four cells; only the ground cell takes a new palette (TOWN1@g, or TOWN1 where the ground is sand,
snow, earth or zoo green): it holds only ground and kerb pixels.  Typed once for the case where the ground cell is diagonal south-east of the junction cell, mirrored for the other three."""
import sys

OUT_NW = [
    "gggggkkk",
    "gggkkkkk",
    "ggkkkkll",
    "gkkkllbb",
    "gkklbobb",
    "kklbbbbb",
    "kklbbbbb",
    "kklobbbb",
]

# the INNER patch for "ground cell south-east of the junction cell": columns x -4..5, rows y -3..5 relative to the ground cell's top left (x 0 y 0)
IN_SE = {
    -3: "bbbbbbblll",
    -2: "bbbbbllkkk",
    -1: "bbbblkkkkk",
    0: "bbblkkkkgg",
    1: "bblkkkgggg",
    2: "bblkkggggg",
    3: "blkkgggggg",
    4: "blkkgggggg",
    5: "blkkgggggg",
}
IN_X0 = -4


def flip_x(rows):
    return [r[::-1] for r in rows]


def flip_y(rows):
    return rows[::-1]


OUTER = {"NW": OUT_NW, "NE": flip_x(OUT_NW), "SW": flip_y(OUT_NW), "SE": flip_y(flip_x(OUT_NW))}
GROUND_G = {"grass", "farm", "cow", "lodge"}            # inner ground cells that take TOWN1@g (ground colour near the map grass)
TOWN1_OUTER = {(63, 11), (37, 28)}
SKIP_INNER = {(52, 44), (61, 27), (61, 47)}               # ground cells that hold picture art (factory yard, lodge, the cow pen fence): their palette cannot change, so these three inner corners stay square                        # outer corners beside snow and town cobble: TOWN1


def classify(roads):
    outer, inner = [], []
    for (cx, cy) in sorted(roads):
        n, e, s, w = ((cx, cy - 1) in roads, (cx + 1, cy) in roads, (cx, cy + 1) in roads, (cx - 1, cy) in roads)
        if not n and not w:
            outer.append((cx, cy, "NW"))
        elif not n and not e:
            outer.append((cx, cy, "NE"))
        elif not s and not w:
            outer.append((cx, cy, "SW"))
        elif not s and not e:
            outer.append((cx, cy, "SE"))
        elif n and e and s and w:
            for k, (dx, dy) in {"nw": (-1, -1), "ne": (1, -1), "se": (1, 1), "sw": (-1, 1)}.items():
                if (cx + dx, cy + dy) not in roads:
                    inner.append((cx, cy, k))
    return outer, inner


import os
# corners left square: the windows round the south middle junction already hold 8 palettes (base, grass, saloon, tea, tea@g, town1, water, zoo), a rounded corner needs TOWN1@g as a ninth
PALETTE_LIMITED = {(35, 44), (37, 46), (50, 46)}          # inner ground cell (35,44), outer corners (37,46) and (50,46)
EXCL = PALETTE_LIMITED | {tuple(int(v) for v in t.split(",")) for t in os.environ.get("SMAP_ROUND_EXCL", "").split(";") if t}


def apply(W, PAL):
    """edits W.WORLD (Color) and W.WORLD_DMG in place; returns the list of cells it changed (for the report)"""
    roads = W.WORLD.roads
    outer, inner = classify(roads)
    changed = []
    for (cx, cy, k) in outer:
        if (cx, cy) in EXCL:
            continue
        rows = OUTER[k]
        for w, color in ((W.WORLD, True), (W.WORLD_DMG, False)):
            for y in range(8):
                for x in range(8):
                    ch = rows[y][x]
                    v = {"g": 0, "k": 2, "b": 1}.get(ch)
                    if v is None:                                   # l, o: the light line and the specks
                        v = 1 if (color and (cx, cy) not in TOWN1_OUTER) else 0      # Color on TOWN1@g: no cream available (index 3 is ink), the line is left out of the corner curve
                    w.px[cy * 8 + y][cx * 8 + x] = v
            if color:
                w.pal[cy][cx] = "town1" if (cx, cy) in TOWN1_OUTER else "town1@g"
        changed.append((cx, cy, "outer " + k))
    for (jx, jy, k) in inner:
        gx, gy = jx + (1 if "e" in k else -1), jy + (1 if "s" in k else -1)         # the ground cell diagonal to the junction cell
        if (gx, gy) in SKIP_INNER or (gx, gy) in EXCL:
            changed.append((gx, gy, "inner corner NOT rounded (ground cell holds art)"))
            continue
        for w, color in ((W.WORLD, True), (W.WORLD_DMG, False)):
            ox, oy = gx * 8, gy * 8
            for y in range(8):                                                     # the ground cell will hold only ground and kerb: its tuft pixels go (their index would change colour)
                for x in range(8):
                    w.px[oy + y][ox + x] = 0
            for y, row in IN_SE.items():
                for i, ch in enumerate(row):
                    x = IN_X0 + i
                    ax = ox + x if "e" in k else ox + 7 - x
                    ay = oy + y if "s" in k else oy + 7 - y
                    w.px[ay][ax] = {"g": 0, "k": 2, "l": 0, "b": 1}[ch]
        gp = W.WORLD.pal[gy][gx]
        W.WORLD.pal[gy][gx] = "town1@g" if gp in GROUND_G else "town1"
        changed.append((gx, gy, "inner ground cell (junction %d,%d %s) %s -> %s" % (jx, jy, k, gp, W.WORLD.pal[gy][gx])))
    return changed
