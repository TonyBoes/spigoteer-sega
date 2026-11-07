"""Peak variants for the ranges (stage 1c, owner: "a little bit of variation in mountain tiles").  The approved round 3 peak (smap_venue_redesign3/src/mtn_vert.py, 32 x 24, two summits,
lit left, shaded right, ink outline, '0' caps / '1' lit / '2' shaded / '3' ink) stays as variant A.  Same style, palette and light for the others; all typed here.

B  single summit: the approved main summit and cap rows, then one long shaded slope down to the right (no second summit); 24 rows, strata dashes and dark marks typed.
C  shorter: the approved peak with its two lit-face rows 13 and 14 left out (22 rows): a squatter double summit.
D  taller: the approved peak with its lit-face rows 11 and 12 repeated (26 rows): a steeper double summit.
Rows are copied from my own typed approved rows (C, D) or typed new (B); the stack places each peak with its foot on the tier's base line."""
import mtn_vert as V

A = V.PEAK
D = "."


def _rows_b():
    r = []
    r.append(D * 12 + "3")
    r.append(D * 11 + "303")
    r.append(D * 10 + "30013")
    r.append(D * 9 + "3000313")
    r.append(D * 9 + "3000313")
    r.append(D * 8 + "300013223")
    r.append(D * 8 + "3011113223")
    r.append(D * 7 + "301111132223")
    r.append(D * 7 + "3011111322223")
    r.append(D * 6 + "3" + "0" + "1" * 7 + "3" + "2222" + "3")
    r.append(D * 6 + "3" + "1" * 8 + "2" * 6 + "3")
    r.append(D * 5 + "3" + "1" * 9 + "2" * 7 + "3")
    r.append(D * 5 + "3" + "1" * 10 + "2" * 7 + "3")
    r.append(D * 4 + "3" + "1" * 11 + "2" * 8 + "3")
    r.append(D * 4 + "3" + "1" * 11 + "2" * 9 + "3")
    r.append(D * 3 + "3" + "1" * 12 + "2" * 10 + "3")
    r.append(D * 3 + "3" + "1" * 12 + "2" * 11 + "3")
    r.append(D * 2 + "3" + "1" * 13 + "2" * 11 + "3")
    r.append(D * 2 + "3" + "1" * 14 + "2" * 11 + "3")
    r.append(D * 1 + "3" + "1" * 14 + "2" * 12 + "3")
    r.append(D * 1 + "3" + "1" * 14 + "2" * 12 + "3")
    r.append(D * 2 + "33" + "1" * 13 + "2" * 11 + "33")
    r.append(D * 4 + "333" + "1" * 11 + "2" * 9 + "3333")
    r.append(D * 8 + "3" * 19)
    g = []
    for i, s in enumerate(r):
        s = s + D * (32 - len(s))
        assert len(s) == 32, (i, len(s))
        g.append(list(s))
    for (y, x0, x1, v) in [(11, 7, 10, "2"), (14, 9, 13, "2"), (17, 6, 10, "2"), (20, 5, 9, "2"),       # strata dashes on the lit face, each in a different column range
                           (12, 19, 21, "3"), (16, 20, 22, "3"), (19, 21, 23, "3")]:                    # dark marks on the shaded face
        for x in range(x0, x1 + 1):
            assert g[y][x] in "12", (y, x, g[y][x])
            g[y][x] = v
    return ["".join(s) for s in g]


B = _rows_b()
C = [row for i, row in enumerate(A) if i not in (13, 14)]                         # 22 rows
Dv = A[:13] + [A[11], A[12]] + A[13:]                                              # 26 rows: A's rows 11 and 12 are repeated after row 12... (indices below)
Dv = A[:12] + [A[11], A[12]] + A[12:]
VARIANTS = {"A": A, "B": B, "C": C, "D": Dv}


def paste_peak(c, x, ybase, key):
    """paste variant `key` with its foot (last row) on pixel row ybase - 1 and its left edge at x"""
    import common as K
    rows = VARIANTS[key]
    K.paste(c, x, ybase - len(rows), rows)
