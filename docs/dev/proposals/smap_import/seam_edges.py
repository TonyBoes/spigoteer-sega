"""Irregular ground seams (owner: "Look at the area next to the saloon to see the effect where you've kind of dithered the gas tiles so it doesn't look like a straight transition. I want that
applied to all the areas where two things meet.").  The model is the saloon's north-east edge in the A5 biome map: the edge typed row by row, a cell or two in or out per row, no two
neighbouring rows alike.  There the sand and the grass never share a cell (no mixed cell, so no extra palette and no extra tile): the edge is a staircase of whole ground cells.
The straight runs the map still had (found by out/smap_import/seams2.py, runs of 3 or more cells between two plain ground cells) are re-typed here the same way, before the world is built.
Every row below is typed by hand: x0..x1 is the span of that biome in the row, every other cell of the stretch is grass.

  desert | grass   east edge x 28|29 rows 30..33 and x 31|32 rows 34..44 (15 straight rows), west strip x 1|2 rows 30..44, the north edge beside the saloon (row 21)
  jungle | grass   the zoo's north edge (rows 49..52), its west strip (rows 64..69) and its east edge (rows 53..69: the old notches every 4th row marched)"""

# desert: row -> (x0, x1); rows 28, 29, 45, 46 lie under the road and keep their span
DESERT = {
    21: (3, 11), 22: (2, 13),
    30: (2, 28), 31: (3, 27), 32: (3, 29), 33: (2, 28),
    34: (2, 30), 35: (4, 32), 36: (3, 30), 37: (2, 31), 38: (3, 32), 39: (3, 30), 40: (4, 29), 41: (3, 31), 42: (2, 32), 43: (2, 30), 44: (3, 31),
}
# jungle: row -> list of (x0, x1)
JUNGLE = {
    49: [(7, 8), (11, 12), (15, 16)],
    50: [(6, 17)], 51: [(3, 18)], 52: [(2, 19)],
    53: [(2, 20)], 54: [(2, 19)], 55: [(2, 20)], 56: [(2, 21)], 57: [(2, 20)], 58: [(2, 22)], 59: [(2, 21)], 60: [(2, 19)], 61: [(2, 20)],
    62: [(2, 21)], 63: [(2, 20)], 64: [(3, 19)], 65: [(2, 21)], 66: [(2, 20)], 67: [(3, 19)], 68: [(4, 21)], 69: [(2, 20)],
}


def apply(lay):
    G = lay.GRID
    for y, (x0, x1) in DESERT.items():
        for x in range(1, 36):                       # the stretch of the row the desert may touch
            if G[y][x] == "d":
                G[y][x] = "g"
        for x in range(x0, x1 + 1):
            G[y][x] = "d"
    for y, segs in JUNGLE.items():
        for x in range(2, 24):
            if G[y][x] == "j":
                G[y][x] = "g"
        for (x0, x1) in segs:
            for x in range(x0, x1 + 1):
                G[y][x] = "j"
    lay.BIOME_ROWS = ["".join(r) for r in G]
    lay.BIOMES = lay.biomes_from_rows()
