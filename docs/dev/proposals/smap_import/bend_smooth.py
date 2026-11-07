"""Smooth road bends, step 1 (owner on Q113: "I was hoping for the curves to be smooth. Not just rounded.").  A proposal to look at, not applied to the map by default.

A bend of the 16 px wide road is a 2 x 2 cell block.  On a bend of OUTER radius R (16 or 24) the road keeps its width all round: the outer edge is a quarter circle of radius R, the
inner edge (the corner of the ground block inside the bend) a quarter circle of radius R - 16 about the same centre.  Layers, from the outside in, constant round the bend:
kerb 2 px (lilac, k), light line 1 px (l), body (b, with specks o), light line 1 px, kerb 2 px, ground (g).  Straight arms continue as the plain road tiles.

The patch is an R x R pixel picture of the outer-corner quadrant, NW orientation (the bend's outer corner at the top left, arms leaving east and south); the other three orientations are
flips of it.  Every ring is a staircase whose runs SHRINK toward the 45 degree point (3 3 2 1 1 1 ... for R 24, 3 2 1 1 1 ... for R 16) and is its own mirror about the diagonal, so the bend
is symmetric.  The staircases are typed below as the number of pixels each row holds on the outside of each ring (a hand-chosen self-conjugate run list per ring, picked next to the ideal
circle with the scaffolds in out/, not generated); the speck cells are typed by hand.

OUT[R]: per row, how many pixels from the left are ground (g), ground + kerb (gk), ground + kerb + line (gkl).
IN[R]: per row counted from the BOTTOM (row R-1 is index 0), how many pixels from the right are ground (G), ground + inner kerb (GK), ground + inner kerb + inner line (GKL)."""

OUT = {
    16: dict(
        g=[12, 9, 7, 6, 5, 4, 3, 2, 2, 1, 1, 1, 0, 0, 0, 0],
        gk=[16, 16, 12, 10, 8, 7, 6, 5, 4, 4, 3, 3, 2, 2, 2, 2],
        gkl=[16, 16, 16, 12, 10, 8, 7, 6, 5, 5, 4, 4, 3, 3, 3, 3]),
    24: dict(
        g=[19, 16, 13, 11, 10, 9, 8, 7, 6, 5, 4, 3, 3, 2, 2, 2, 1, 1, 1, 0, 0, 0, 0, 0],
        gk=[24, 24, 19, 16, 14, 12, 10, 9, 8, 7, 6, 6, 5, 5, 4, 4, 3, 3, 3, 2, 2, 2, 2, 2],
        gkl=[24, 24, 24, 19, 16, 14, 12, 11, 10, 9, 8, 7, 6, 6, 5, 5, 4, 4, 4, 3, 3, 3, 3, 3]),
}
IN = {
    16: dict(G=[0], GK=[2, 2], GKL=[3, 3, 3]),                 # inner radius 0: the ground block's corner stays square, kerb and line square round it
    24: dict(G=[8, 8, 8, 7, 7, 6, 5, 3],                       # inner radius 8
             GK=[10, 10, 10, 9, 9, 8, 8, 7, 5, 3],
             GKL=[11, 11, 11, 10, 10, 10, 9, 8, 7, 6, 3]),
}
# specks (body pixels that read as the light index), about 1 in 16, following the curve, none touching the line or kerb: (x, y) in the patch
SPECKS = {
    16: [(13, 4), (8, 7), (12, 9), (5, 12), (14, 6)],
    24: [(5, 19), (7, 14), (11, 20), (14, 15), (15, 6), (18, 12), (20, 4), (10, 10), (13, 9), (10, 17), (22, 7), (8, 22)],
}


def _at(lst, j):
    return lst[j] if j < len(lst) else 0


def grid(R):
    """the R x R picture (rows of letters g k l b o) of the NW bend of outer radius R"""
    o, i = OUT[R], IN[R]
    rows = []
    for y in range(R):
        g, gk, gkl = o["g"][y], o["gk"][y], o["gkl"][y]
        j = R - 1 - y
        G, GK, GKL = _at(i["G"], j), _at(i["GK"], j), _at(i["GKL"], j)
        row = []
        for x in range(R):
            if x < g:
                c = "g"
            elif x < gk:
                c = "k"
            elif x < gkl:
                c = "l"
            elif x >= R - G and G:
                c = "g"
            elif x >= R - GK and GK:
                c = "k"
            elif x >= R - GKL and GKL:
                c = "l"
            else:
                c = "b"
            row.append(c)
        rows.append(row)
    for (x, y) in SPECKS[R]:
        assert rows[y][x] == "b", (R, x, y)
        rows[y][x] = "o"
    return ["".join(r) for r in rows]


def flip_x(rows):
    return [r[::-1] for r in rows]


def flip_y(rows):
    return rows[::-1]


if __name__ == "__main__":
    import sys
    for R in (16, 24):
        print(R)
        for r in grid(R):
            print(r)
