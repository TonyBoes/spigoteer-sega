"""Color pads (owner Q94 "the blank color outlines around various locations", audit 11-08 rows 12, 25, 36): the flat Color-only pads that were left on the map, removed with the approved
seam treatment (whole ground cells in an irregular staircase, no mixed cell) or, where a cell cannot be re-typed, by changing the art so that the cell takes a palette with the ground as index 0.

Everything here edits the COLOR data set only (W.WORLD, and v_bistro.py's dmg=False branch): the DMG pixels (W.WORLD_DMG) are not touched, so the DMG map is byte for byte what it was.  In the
DMG a snow, earth or grass ground cell is the same all-0 tile, so none of these edges exists there.

  1. bistro        (tools/smap_world/v_bistro.py, Color branch) the BISTRO board is 4 px wider on each side (its letters stay where they were) so its ends lie on cell boundaries: no cell holds the
                   letters (index 0) and the cream margin together, and the margin cells beside the sign take bistro@g (grass index 0) like the rest of the building's margin.  The round
                   table moved 3 px right for the same reason: the terrace's left block (piece cell (0, 5)) held two of its cream pixels.
  2. factory yard  the earth yard was a ten by seven cell rectangle with a straight east edge (rows 36 to 44): earth tongues one cell out on the east, in a staircase of runs 2, 1, 2, 1, 2.
  3. mountain B    the five snow cells hanging under B's feet between the pines (row 5) were flat white squares on the grass: back to grass, the feet and the pines stand on the grass directly.
Not done: the cream wedge at the road bends (35..37, 44..46) and (50..52, 44..46): the fix is a palette with the grass as index 0 (town1@g) for 7 + 5 cells, and 63 + 19 of the 21 x 19 windows
there already hold 8 palettes (tea@g, base, zoogate, cactus, factory, farm, cow in the way); see the report in the commit message."""

YARD_TONGUES = [(62, 37), (62, 38), (62, 40), (63, 40), (62, 41), (62, 43), (62, 44), (63, 44)]
SNOW_FRINGE = [(35, 5), (36, 5), (39, 5), (40, 5), (43, 5)]
YARD_TOP = [(63, 37), (63, 39), (63, 42)]     # more earth cells in the east staircase (flat grass cells; rows above 37 would add a ninth palette to the windows at y0 17 and 18)
SNOW_ROWS = 2                                            # how many staircase rings of snow cells (flat, or only index 0 and 3) go back to grass


def _cells(w, pal):
    return [(x, y) for y in range(len(w.pal)) for x in range(len(w.pal[0])) if w.pal[y][x] == pal]


def _used(w, x, y):
    return {w.px[y * 8 + j][x * 8 + i] for j in range(8) for i in range(8)}


def _flat(w, x, y, pal):
    for j in range(8):
        for i in range(8):
            w.px[y * 8 + j][x * 8 + i] = 0
    w.pal[y][x] = pal


def apply(W, PAL):
    """returns the list of changed cells (Color data set only)"""
    w = W.WORLD
    changed = []
    for (cx, cy) in YARD_TONGUES:                       # the factory yard's east edge
        assert w.kind[cy][cx] == "ground" and w.pal[cy][cx] == "grass", (cx, cy, w.kind[cy][cx], w.pal[cy][cx])
        _flat(w, cx, cy, "factory")
        changed.append((cx, cy))
    for (cx, cy) in SNOW_FRINGE:                        # mountain B's snow fringe
        assert w.pal[cy][cx] == "igloo", (cx, cy, w.pal[cy][cx])
        _flat(w, cx, cy, "grass")
        changed.append((cx, cy))
    for (cx, cy) in YARD_TOP:
        if not (w.kind[cy][cx] == "ground" and w.pal[cy][cx] == "grass" and _used(w, cx, cy) == {0}):
            continue                                    # a tufted or tree cell: leave it
        _flat(w, cx, cy, "factory")
        changed.append((cx, cy))
    # mountain B: the snow field's edge is a staircase of whole cells, no straight run: a snow cell with a grass
    # neighbour goes back to grass when it holds nothing but snow (index 0) and at most a dark outline pixel (index 3:
    # the grass palette's index 3 is the near-black green, indistinguishable from the navy ink at that size)
    box = range(30, 52), range(0, 8)
    for ring in range(SNOW_ROWS):
        todo = []
        for y in box[1]:
            for x in box[0]:
                if w.pal[y][x] != "igloo" or not _used(w, x, y) <= {0, 3}:
                    continue
                nb = [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]
                if any(0 <= a < len(w.pal[0]) and 0 <= b < len(w.pal) and w.pal[b][a] == "grass" for a, b in nb) and (x + y + ring) % 2 == 0:
                    todo.append((x, y))
        for (cx, cy) in todo:
            w.pal[cy][cx] = "grass"
            changed.append((cx, cy))
    return changed
