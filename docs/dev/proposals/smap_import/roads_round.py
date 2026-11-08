"""Rounded road corners, ALL 24 (stage 1c; owner: "Round the corners on the road", then Q113 "make all rounded and show me").  Hand-typed pieces; nothing here decides a pixel except by
looking up my typed rows.

The road is 16 px wide: 2 px kerb (lilac, index 2), 1 px light line (index 0), body (index 1, a few index 0 specks).  Its straight tiles are tools/smap_world/tiles.py ROAD.
Letters below: g ground (outside the road), k kerb, l light line, b body, o body speck.  DMG value = index: g 0, k 2, l 0, b 1, o 0.

OUTER corner (a road cell with two open sides): the outer kerb edge is a quarter arc of radius 8 over the corner cell, the kerb stays 2 px thick, the line follows, the body fills inside.
The cell now shows ground in its outer corner (13 px), so on Color it takes a palette that has the LOCAL GROUND colour as index 0 and the road's peach (1) and lilac (2):
  town1@g (grass), town1@n (snow), and for the corner by the town's cobble the grass one.  On Color the light line inside the curve is the body colour (the road palette's cream is index 0).

INNER corner (a road cell with all four sides open but one diagonal missing: the ground block's corner pokes into the road): the ground block's corner is rounded with radius 6, the kerb
following it, the light line and body re-cut round it.  The change spans the notch's four cells.  The ground cell (diagonal to the junction) gets exactly 7 kerb pixels in its corner and
keeps everything else; it needs a palette with the local ground as index 0 and something kerb-like, see INNER below.  Typed once for the case where the ground cell is diagonal south-east
of the junction cell, mirrored for the other three.  Three ground cells hold picture art (the factory yard, the lodge's wood pile, the cow pen fence): their art is kept, the kerb pixels
only replace art pixels where they must (listed in ART_TRIM)."""
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

# new palettes: the road's peach and lilac with the local ground as index 0 (index 3 unused in these cells)
NEW_PALS = {"town1@n": ["e8f8f8", "f0b888", "a090b0", "201828"],       # snow ground (the igloo's index 0)
            "town1@z": ["d8f0a0", "f0b888", "a090b0", "201828"]}       # zoo ground (the zoo palette's index 0)

# outer corners: the palette of the road cell (everything not listed: town1@g)
OUTER_PAL = {(63, 11): "town1@n", (37, 46): "town1", (50, 46): "town1"}      # (37,46) and (50,46): the south middle windows hold 8 palettes already, town1 (cream ground: the compromise) is one of them
# inner corners: ground cell -> (Color palette of the ground cell, the palette index its 7 kerb pixels take on Color).  Not listed: town1@g, 2.
# Existing palettes are used where one has the local ground as index 0 and a kerb-like colour: base (sand, 98a0b0 is close to the kerb's a090b0), factory (packed earth d0c890, steel 88a090).
INNER = {
    (2, 27): ("base", 1),          # the saloon's sand
    (35, 44): ("grass", 1),        # the south middle windows hold 8 palettes already: the grass cell keeps its palette, the 7 kerb pixels take its index 1 (compromise)
    (2, 61): ("town1@z", 2),       # the zoo's pale green
    (61, 13): ("town1@n", 2),      # the igloo's snow
    (52, 44): ("factory", 1),      # the factory yard (art kept)
    (61, 27): ("lodge", 2),        # the lodge wood pile (art trimmed, see ART_TRIM)
    (61, 47): ("cow", 1),          # the cow pen fence (art kept)
}
ART = {(52, 44), (61, 27), (61, 47)}          # ground cells that hold picture art: not cleared, only the kerb pixels are written


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


def apply(W, PAL, skip_outer=(), skip_junction=()):
    """edits W.WORLD (Color) and W.WORLD_DMG in place; returns the list of cells it changed (for the report)"""
    for n, cols in NEW_PALS.items():
        PAL.RGB.setdefault(n, [PAL.h(c) for c in cols])
    roads = W.WORLD.roads
    outer, inner = classify(roads)
    changed = []
    for (cx, cy, k) in outer:
        if (cx, cy) in skip_outer:                                  # a smooth bend (roads_smooth.py) is laid here instead
            continue
        rows = OUTER[k]
        pal = OUTER_PAL.get((cx, cy), "town1@g")
        for w, color in ((W.WORLD, True), (W.WORLD_DMG, False)):
            for y in range(8):
                for x in range(8):
                    ch = rows[y][x]
                    v = {"g": 0, "k": 2, "b": 1}.get(ch)
                    if v is None:                                   # l, o: the light line and the specks
                        v = 1 if (color and pal != "town1") else 0  # Color: the body colour (the cream is not in the @ palettes; town1 has it as index 0); DMG: the light index
                    w.px[cy * 8 + y][cx * 8 + x] = v
            if color:
                w.pal[cy][cx] = pal
        changed.append((cx, cy, "outer " + k + " " + pal))
    for (jx, jy, k) in inner:
        if (jx, jy) in skip_junction:
            continue
        gx, gy = jx + (1 if "e" in k else -1), jy + (1 if "s" in k else -1)         # the ground cell diagonal to the junction cell
        pal, kidx = INNER.get((gx, gy), ("town1@g", 2))
        for w, color in ((W.WORLD, True), (W.WORLD_DMG, False)):
            ox, oy = gx * 8, gy * 8
            if (gx, gy) not in ART:
                for y in range(8):                                                 # the ground cell will hold only ground and kerb: its tuft pixels go (their index would change colour)
                    for x in range(8):
                        w.px[oy + y][ox + x] = 0
            for y, row in IN_SE.items():
                for i, ch in enumerate(row):
                    x = IN_X0 + i
                    ax = ox + x if "e" in k else ox + 7 - x
                    ay = oy + y if "s" in k else oy + 7 - y
                    if (gx, gy) in ART and not (0 <= ax - ox < 8 and 0 <= ay - oy < 8):
                        pass
                    if (gx, gy) in ART and 0 <= ax - ox < 8 and 0 <= ay - oy < 8 and ch != "k":
                        continue                                                   # an art cell keeps everything but the kerb pixels
                    v = {"g": 0, "k": 2, "l": 0, "b": 1}[ch]
                    if color and ch == "k" and 0 <= ax - ox < 8 and 0 <= ay - oy < 8:
                        v = kidx
                    w.px[ay][ax] = v
        if (gx, gy) in INNER or True:
            old = W.WORLD.pal[gy][gx]
            W.WORLD.pal[gy][gx] = pal
            changed.append((gx, gy, "inner ground cell (junction %d,%d %s) %s -> %s" % (jx, jy, k, old, pal)))
    return changed
