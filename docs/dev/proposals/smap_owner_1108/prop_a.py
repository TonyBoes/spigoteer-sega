"""Proposal A, desert peaks (owner 11-08: "take some of the smaller mountains that you made for the snowy section and put desert-colored ones above the big mountain in the desert, replacing the
scattered random mountain tiles that you have there").

The pieces are the approved round 3 peak and its three variants (smap_import/range_peaks.py: A approved, B one summit, C shorter, D taller), copied unchanged: nothing is redrawn.  In the snowy
ranges they stand with their left edge on a cell boundary and their foot on a cell row's end; here they do too, so every tile of a peak is the very tile of the snowy one (the DMG pixels are the
same, only the Color palette differs: `saloon`, the desert's own: 0 sand = crest, 1 lit rock, 2 shaded rock, 3 ink, as the round 3 sheet's DESERT version).
The five old scattered peaks (desert_extras PEAKS: cone, twin, spire, slope, mesa) are not laid (ctx.py sets SMAP_DESERT_PIECES=cacti); the mesa below the airbase is laid again unchanged
(it is not above the mountain); the cacti stay where they are.  The peaks avoid the cacti's cells, the road, and the cells x >= 22 of rows 30 and 31 (proposal B's paved band south of the road).

place(): back to front onto a pixel map, then every cell the pieces touch is written whole (clear = index 0, the sand), palette saloon.  Both data sets get the same pixels."""
import sys

import desert_extras as DX

PROPS = __import__("pathlib").Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROPS / "smap_venue_redesign3" / "src"))
import range_peaks as RP  # noqa: E402

D = "."
# (variant, x px, y px of the foot line = the first row below the peak); x and y are multiples of 8, as in the snowy ranges
ARRANGEMENTS = {
    # A1: three peaks standing apart on one foot line (y 272), sand between them; every cactus where it was
    "A1": [("B", 40, 272), ("A", 80, 272), ("C", 112, 272)],
    # A2: a ridge: the tall peak behind, the short one in front of its right foot (they overlap by 8 px), a single-summit peak apart on their left and the approved peak apart on their
    # right, one cell further left (11-08: clear sand between it and the south paving's west end); the barrel cactus that stood under the right-hand peak (20, 33) moves to the free sand at (23, 34)
    "A2": [("D", 80, 272), ("C", 104, 272), ("B", 32, 272), ("A", 144, 272)],
}
# (S2: one cell left, so that the peak A moved left has clear sand beside it; the barrel at (27, 43) one row down: the walk space -> town stalled at the tavern awning (palette town5, a 9th palette in the window) until the camera had
# dropped the row of this barrel (palette cactus), 28 frames of holds: at row 44 its row drops first)
MOVE_CACTI = {"A1": [], "A2": [("B", (20, 33), (23, 34)), ("S2", (18, 31), (17, 31)), ("B", (27, 43), (27, 44))]}


def rows_of(key):
    return RP.VARIANTS[key]


def place(W, WORLDS, peaks):
    canvas = {}
    for (key, x, yb) in peaks:                                   # back to front: the list's order
        rows = rows_of(key)
        y = yb - len(rows)
        assert x % 8 == 0 and yb % 8 == 0, (key, x, yb)
        for j, r in enumerate(rows):
            for i, ch in enumerate(r):
                if ch != D:
                    canvas[(x + i, y + j)] = int(ch)
    cells = sorted({(px // 8, py // 8) for (px, py) in canvas})
    box = [(min(c[0] for c in cells), min(c[1] for c in cells)), (max(c[0] for c in cells), max(c[1] for c in cells))]
    w0 = W.WORLD
    for (cx, cy) in cells:
        bare = {w0.px[cy * 8 + j][cx * 8 + i] for j in range(8) for i in range(8)} <= {0, 1}          # sand and its ripples only (the airbase venue's top row is blank sand)
        assert w0.pal[cy][cx] == "saloon" and w0.kind[cy][cx] in ("ground", "decor", "space") and bare and (cx, cy) not in w0.roads, ("peak cell not plain desert", cx, cy, w0.pal[cy][cx], w0.kind[cy][cx])
        for w in WORLDS:
            for j in range(8):
                for i in range(8):
                    w.px[cy * 8 + j][cx * 8 + i] = canvas.get((cx * 8 + i, cy * 8 + j), 0)
            w.pal[cy][cx] = "saloon"
    return cells, box


def apply(W, PAL, arr):
    WORLDS = (W.WORLD, W.WORLD_DMG)
    peaks = ARRANGEMENTS[arr]
    # the rocks in the way go (a whole rock, never half of one)
    for (key, x, yb) in peaks:
        h = len(rows_of(key))
        DX.clear_rocks(W, WORLDS, x - 3, yb - h - 3, x + 32 + 3, yb + 3)
    for (name, (ox, oy), (nx, ny)) in MOVE_CACTI[arr]:
        rows = DX.CACTI[name]
        for k in range(len(rows) // 8):                          # the old cells back to plain sand
            assert W.WORLD.pal[oy + k][ox] == "cactus", (name, ox, oy + k)
            for w in WORLDS:
                for j in range(8):
                    for i in range(8):
                        w.px[(oy + k) * 8 + j][ox * 8 + i] = 0
                w.pal[oy + k][ox] = "saloon"
        DX.clear_rocks(W, WORLDS, nx * 8 - 2, ny * 8 - 2, nx * 8 + 10, ny * 8 + len(rows) + 2)
        for k in range(len(rows) // 8):
            assert W.WORLD.pal[ny + k][nx] == "saloon" and W.WORLD.kind[ny + k][nx] in ("ground", "decor"), (name, nx, ny + k)
        for w in WORLDS:
            for j, row in enumerate(rows):
                for i, ch in enumerate(row):
                    w.px[ny * 8 + j][nx * 8 + i] = int(ch) if ch != D else 0
            for k in range(len(rows) // 8):
                w.pal[ny + k][nx] = "cactus"
    cells, box = place(W, WORLDS, peaks)
    # the mesa below the airbase's tower stays where it was (it is not above the mountain)
    rows = DX.peak_rows("mesa")
    x, y = 16, 345
    DX._put(W, WORLDS, x, y, rows, "saloon")
    return {"peaks": peaks, "cells": cells, "box": box}
