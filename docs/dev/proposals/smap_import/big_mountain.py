"""One BIG mountain (owner 11-07: "a big mountain near the top somewhere. It can go off the screen"), proposal only.  The range peaks' family and light, scaled up: palette `igloo`
(0 snow, 1 pale ice-blue rock, 2 deep blue, 3 ink), light from the top left: lit left, shaded right, ink outline, a snow cap that breaks up into a ragged edge, strata dashes on the lit faces,
dark creases on the shaded faces, a lower second summit on the right shoulder with its own lit face over the main one's shade.
Drawn from typed tables, row by row: the silhouette of each summit (control points of its left and right outline, x per y), the ridge (where lit turns to shaded), the width of the snow cap per
row, and the typed strata and crease marks.  The tables are the drawing: the code only fills a row between the typed outlines.  W x H = 84 x 60.  Rows are drawn from the apex (y 0) down to the
foot (y 59); a placement crops it by the map's top and side edges (the top 24 rows are above the screen in placement A)."""

W, H = 84, 60


def interp(pts, y):
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if y0 <= y <= y1:
            return x0 + (x1 - x0) * (y - y0) / (y1 - y0) if y1 != y0 else x0
    return pts[-1][0]


MAIN_L = [(36, 0), (31, 8), (26, 18), (17, 34), (10, 46), (4, 56), (4, 59)]
MAIN_R = [(37, 0), (43, 8), (50, 18), (56, 26), (60, 34)]
SEC_L = [(63, 14), (59, 22), (56, 28)]
SEC_R = [(64, 14), (69, 22), (75, 34), (80, 48), (82, 56), (80, 59)]
MAIN_RIDGE = [(36, 0), (39, 14), (43, 32), (47, 46), (50, 59)]
SEC_RIDGE = [(63, 14), (66, 28), (69, 42), (71, 59)]
CAP_MAIN = [0, 1, 2, 2, 3, 4, 4, 5, 6, 5, 7, 6, 8, 7, 9, 8, 10, 9, 11, 9, 8, 6, 5, 3]            # snow width on the lit face per row (y 0 to 23); ragged
CAP_SEC = [0, 1, 1, 2, 2, 3, 2, 4, 3, 5, 3, 4, 2, 0]                                           # second summit, rows 14 to 27
# strata dashes on the lit faces (y, x0, x1) written as '2'; creases on the shaded faces (y, x0, x1) written as '3'
STRATA = [(27, 20, 24), (30, 15, 19), (33, 26, 31), (36, 12, 16), (38, 22, 27), (41, 14, 18), (43, 30, 34), (46, 8, 13), (48, 20, 25), (51, 30, 33), (53, 12, 17), (56, 22, 27),
          (31, 64, 67), (37, 62, 66), (44, 66, 69), (50, 64, 68)]
CREASE = [(20, 41, 42), (24, 44, 46), (29, 49, 51), (34, 53, 55), (39, 57, 60), (44, 60, 62), (49, 63, 65), (22, 67, 69), (28, 70, 72), (36, 73, 75), (42, 75, 77), (51, 76, 79), (46, 78, 80),
          (55, 58, 62), (58, 66, 72)]


def rows():
    g = [["."] * W for _ in range(H)]
    for y in range(H):
        mL, mR = round(interp(MAIN_L, y)), round(interp(MAIN_R, y))
        has2 = y >= 14
        sL, sR = (round(interp(SEC_L, y)), round(interp(SEC_R, y))) if has2 else (None, None)
        merged = has2 and sL <= mR + 1
        rm = round(interp(MAIN_RIDGE, y))
        rs = round(interp(SEC_RIDGE, y)) if has2 else None
        right = sR if has2 and merged else mR
        for x in range(mL, (max(mR, right) if merged else mR) + 1):
            pass
        spans = [(mL, right)] if merged else [(mL, mR)] + ([(sL, sR)] if has2 else [])
        for (a, b) in spans:
            for x in range(a, b + 1):
                if x in (a, b) or y == 0:
                    g[y][x] = "3"
                    continue
                v = "1" if x <= rm else "2"
                if has2 and x >= sL and merged and x <= sR:
                    v = "1" if x <= rs else "2"
                    if x == sL:
                        v = "3"
                elif has2 and not merged and a == sL:
                    v = "1" if x <= rs else "2"
                g[y][x] = v
        # snow cap on the lit face
        if y < len(CAP_MAIN):
            for x in range(mL + 1, min(mL + CAP_MAIN[y], rm) + 1):
                if g[y][x] == "1":
                    g[y][x] = "0"
        if has2 and y - 14 < len(CAP_SEC):
            for x in range(sL + 1, min(sL + CAP_SEC[y - 14], rs) + 1):
                if g[y][x] == "1":
                    g[y][x] = "0"
    for (y, x0, x1) in STRATA:
        for x in range(x0, x1 + 1):
            if g[y][x] == "1":
                g[y][x] = "2"
    for (y, x0, x1) in CREASE:
        for x in range(x0, x1 + 1):
            if g[y][x] == "2":
                g[y][x] = "3"
    g[H - 1] = [("3" if g[H - 1][x] != "." or g[H - 2][x] != "." else ".") for x in range(W)]
    return ["".join(r) for r in g]


if __name__ == "__main__":
    print("\n".join(rows()))


PLACES = {"A": (444, -20, "the top right corner: cropped by the top edge (20 rows) and the east edge (16 columns), foot on the line under range C, behind the igloo's chimney"),
          "B": (280, -20, "the head of the river: cropped by the top edge (20 rows), the falls leave its foot to the east")}


def apply(W, WORLDS, key):
    """paste the mountain with its top-left at the placement (cropped by the map edges); the cells it touches take the palette `igloo` (they already have it on rows 0 to 4)"""
    x0, y0, _ = PLACES[key]
    rs = rows()
    touched = set()
    for j, r in enumerate(rs):
        for i, c in enumerate(r):
            X, Y = x0 + i, y0 + j
            if c == "." or not (0 <= X < 512 and 0 <= Y < 512):
                continue
            for w in WORLDS:
                w.px[Y][X] = int(c)
            touched.add((X // 8, Y // 8))
    for (cx, cy) in touched:
        assert (cx, cy) not in WORLDS[0].roads, (cx, cy)
        for w in WORLDS:
            if w.pal[cy][cx] != "igloo":
                w.pal[cy][cx] = "igloo"
    return touched
