"""One BIG mountain (owner 11-07: "a big mountain near the top somewhere. It can go off the screen"), proposal only.  Redrawn after the coordinator's review (the first one had a straight
full-height vertical line and was a scaled copy of the range peak).  Palette `igloo`: 0 snow, 1 pale ice-blue rock, 2 deep blue, 3 ink.  Light from the top left, as the ranges.

A real mountain, drawn row by row from typed numbers (the numbers are the drawing; the code only writes the runs between them):
  - the outline of a main summit (x 32) and a lower shoulder summit to the right (x 62) with a snow valley between them, the two joining at row 18; a ledge on the left foot where a foothill steps out;
    every outline step is 1 to 3 px and no two neighbouring rows repeat the same step.
  - a lit face (1) and a shadow face (2) split along a ridge that jogs 1 px left and right every row or two (RIDGE_M, RIDGE_S), so it zig-zags instead of running straight.  The shoulder's own
    left edge (EDGE_S) is an ink line that lets its lit face sit in front of the main summit's shadow face, then dies into the main ridge's side near the foot.
  - a snow cap on both summits with a ragged lower edge: tongues and gaps typed per row (CAP_L on the lit face, CAP_D on the shadow face where snow is the lit rock shade).
  - strata dashes on the lit faces and dark crevice marks on the shadow faces, all typed (y, x0, x1), none two rows alike.
  - a ragged foot: ink row at the bottom with typed bumps above it.
W x H = 84 x 44.  Placed with the top 4 rows above the map edge (A and B keep the coordinator's places).  The base is pasted BEHIND the small range peaks: pixels that belong to a peak
(a big connected piece of rock, with the snow inside its outline) are never overwritten."""

W, H = 90, 44

# per row y: main summit outline (L, R) for rows 0..17; shoulder summit (Ls, Rs) for rows 12..18; merged outline (L, R) from row 18
MAIN = {0: (31, 33), 1: (30, 34), 2: (29, 35), 3: (29, 36), 4: (28, 38), 5: (27, 39), 6: (27, 40), 7: (26, 42), 8: (25, 43), 9: (25, 44), 10: (24, 46), 11: (23, 47),
        12: (22, 48), 13: (21, 49), 14: (21, 51), 15: (20, 52), 16: (19, 53), 17: (19, 55)}
SHOULDER = {12: (62, 63), 13: (61, 64), 14: (60, 65), 15: (60, 67), 16: (59, 68), 17: (58, 69)}
MERGED_L = [18, 17, 17, 16, 15, 15, 14, 14, 13, 13, 12, 10, 10, 9, 8, 8, 7, 6, 6, 5, 4, 4, 3, 3, 2, 2]               # rows 18..43
MERGED_R = [70, 71, 72, 72, 74, 75, 75, 77, 78, 78, 79, 80, 80, 81, 81, 82, 82, 82, 83, 84, 85, 85, 86, 87, 87, 88]
RIDGE_M = [32, 32, 33, 32, 33, 33, 34, 33, 34, 35, 34, 35, 36, 35, 36, 37, 36, 37, 38, 37, 38, 39, 38, 40, 39, 40, 41, 40, 41, 42, 41, 42, 43, 42, 43, 44, 43, 44, 45, 44, 45, 46, 45, 46]
RIDGE_S = {12: 62, 13: 62, 14: 63, 15: 63, 16: 64, 17: 63, 18: 64, 19: 65, 20: 66, 21: 65, 22: 66, 23: 67, 24: 68, 25: 67, 26: 69, 27: 70, 28: 69, 29: 70, 30: 71, 31: 72, 32: 71, 33: 72,
           34: 73, 35: 74, 36: 73, 37: 74, 38: 75, 39: 76, 40: 75, 41: 76, 42: 77, 43: 78}
EDGE_S = {18: 57, 19: 56, 20: 55, 21: 55, 22: 54, 23: 53, 24: 53, 25: 52, 26: 51, 27: 51, 28: 50, 29: 49, 30: 49, 31: 48, 32: 47, 33: 47, 34: 46}   # the shoulder's left ink edge, a diagonal that dies into the main ridge at row 35
CAP_L = [1, 3, 4, 4, 5, 6, 6, 7, 8, 7, 9, 8, 10, 9, 11, 7, 10, 5, 8, 3, 6, 0, 3, 0, 2]                                       # snow px from the left outline on the lit face, rows 0..24
CAP_D = [0, 1, 1, 2, 1, 3, 2, 4, 3, 5, 3, 6, 4, 5, 2, 3, 0, 2, 0]                                                              # pale-rock-shade snow right of the ridge on the shadow face, rows 0..18
CAP_SL = {12: 1, 13: 2, 14: 3, 15: 3, 16: 4, 17: 2, 18: 5, 19: 3, 20: 4, 21: 1, 22: 3, 23: 0, 24: 2}                          # shoulder snow px on its lit face
CAP_SD = {13: 1, 14: 1, 15: 2, 16: 1, 17: 3, 18: 2, 19: 3, 20: 1, 21: 2}                                                      # and on its shadow face
STRATA = [(25, 20, 25), (27, 15, 19), (28, 28, 33), (30, 12, 16), (31, 22, 27), (33, 14, 18), (34, 30, 35), (35, 10, 13), (36, 18, 23), (37, 8, 12), (38, 26, 30), (39, 13, 17), (40, 20, 25),
          (41, 6, 10), (42, 30, 34), (42, 14, 18),
          (21, 58, 62), (24, 58, 62), (27, 60, 65), (30, 62, 67), (33, 62, 67), (36, 56, 60), (36, 64, 70), (38, 60, 66), (40, 54, 58), (40, 62, 68), (41, 56, 62)]    # on lit rock '1' -> '2'
CREASE = [(10, 38, 40), (13, 42, 44), (15, 45, 47), (17, 48, 50), (20, 45, 47), (22, 42, 44), (23, 49, 51), (25, 44, 47), (27, 50, 52), (29, 46, 49), (31, 43, 45), (32, 48, 50), (34, 45, 48),
          (36, 46, 49), (38, 47, 50), (40, 48, 50), (41, 47, 50),
          (18, 67, 68), (20, 69, 71), (22, 70, 72), (24, 71, 73), (26, 73, 75), (28, 74, 77), (30, 76, 78), (32, 76, 79), (33, 78, 81), (35, 79, 81), (37, 80, 82), (39, 79, 82)]  # shade rock '2' -> '3'
SPURS = [(31, 20, 21), (32, 20, 21), (33, 21, 22), (34, 21, 23), (35, 22, 24), (36, 24, 25), (37, 24, 26), (38, 25, 27), (39, 26, 28), (40, 27, 30), (41, 28, 31), (42, 29, 32),
         (36, 54, 55), (37, 55, 56), (38, 55, 57), (39, 56, 58), (40, 57, 59), (41, 59, 62), (42, 61, 64)]                  # rock spurs in shadow on the lower lit slopes, '1' -> '2', each leaning down to the right
FOOT_BUMPS = [(42, 12, 13), (42, 26, 28), (42, 40, 41), (42, 58, 60), (42, 70, 71)]


def rows():
    g = [["."] * W for _ in range(H)]

    def run(y, a, b, ridge, snow_l, snow_d):
        for x in range(a, b + 1):
            if x in (a, b):
                g[y][x] = "3"
                continue
            v = "1" if x <= ridge else "2"
            if x <= ridge and x - a <= snow_l:
                v = "0"
            elif x > ridge and x - ridge <= snow_d:
                v = "1"
            g[y][x] = v

    for y in range(H):
        rm = RIDGE_M[y]
        cl = CAP_L[y] if y < len(CAP_L) else 0
        cd = CAP_D[y] if y < len(CAP_D) else 0
        if y < 18:
            a, b = MAIN[y]
            run(y, a, b, rm, cl, cd)
            if y in SHOULDER:
                a2, b2 = SHOULDER[y]
                run(y, a2, b2, RIDGE_S[y], CAP_SL.get(y, 0), CAP_SD.get(y, 0))
            continue
        a, b = MERGED_L[y - 18], MERGED_R[y - 18]
        rs = RIDGE_S[y]
        e = EDGE_S.get(y)
        for x in range(a, b + 1):
            if x in (a, b):
                g[y][x] = "3"
            elif x <= rm:
                g[y][x] = "0" if (x - a <= cl) else "1"
            elif e is not None and x < e:
                g[y][x] = "1" if (y < 18 + len(CAP_D) and x - rm <= cd) else "2"
            elif e is not None and x == e:
                g[y][x] = "3"
            else:
                lit = x <= rs
                sl = CAP_SL.get(y, 0)
                sd = CAP_SD.get(y, 0)
                if lit:
                    g[y][x] = "0" if (e is not None and x - e <= sl) else "1"
                else:
                    g[y][x] = "1" if x - rs <= sd else "2"
    for (y, x0, x1) in STRATA:
        for x in range(x0, x1 + 1):
            if g[y][x] == "1":
                g[y][x] = "2"
    for (y, x0, x1) in CREASE:
        for x in range(x0, x1 + 1):
            if g[y][x] == "2":
                g[y][x] = "3"
    for (y, x0, x1) in SPURS:
        for x in range(x0, x1 + 1):
            if g[y][x] == "1":
                g[y][x] = "2"
    for (y, x0, x1) in FOOT_BUMPS:
        for x in range(x0, x1 + 1):
            g[y][x] = "3"
    g[H - 1] = [("3" if g[H - 1][x] != "." else ".") for x in range(W)]
    g[0] = [("3" if c != "." else ".") for c in g[0]]
    return ["".join(r) for r in g]


EXTRA_SNOW = {"B": []}     # west edge of B's snow cells by row: 36 35 34 33 34 (was 36 35 34 34 34, three cells straight)
PLACES = {"A": (444, -4, "the top right corner: cropped by the top edge (4 rows) and the east edge (16 columns), foot on the line under range C, behind the igloo's chimney"),
          "B": (312, -4, "the head of the river: cropped by the top edge (4 rows); its right flank stands over the head of the falls (falls_cave.py)")}


def _pieces(px, x0, y0):
    """big connected pieces of non-snow pixels (8-connected, 30 px or more) inside this mountain's box: the range peaks, trees, the igloo.  Returns a list of pixel lists"""
    X0, X1, Y0, Y1 = max(x0, 0), min(x0 + W, 512), max(y0, 0), min(y0 + H, 512)

    def empty_col(x):
        return all(px[y][x] == 0 for y in range(Y0, Y1))

    while X0 > 0 and not empty_col(X0):                     # widen the box to the nearest columns with nothing in them, so no peak is cut by the box edge
        X0 -= 1
    while X1 < 512 and not empty_col(X1 - 1):
        X1 += 1
    seen, big = set(), []
    for Y in range(Y0, Y1):
        for X in range(X0, X1):
            if px[Y][X] == 0 or (X, Y) in seen:
                continue
            comp, st = [], [(X, Y)]
            seen.add((X, Y))
            while st:
                cx, cy = st.pop()
                comp.append((cx, cy))
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        nx, ny = cx + dx, cy + dy
                        if X0 <= nx < X1 and Y0 <= ny < Y1 and px[ny][nx] != 0 and (nx, ny) not in seen:
                            seen.add((nx, ny))
                            st.append((nx, ny))
            if len(comp) >= 30:
                big.append(comp)
    return big, (X0, X1, Y0, Y1)


def _front(px, x0, y0, sil, back_y=12):
    """The mountain stands behind the FRONT tier of peaks (apex at map row 12 or lower) and behind trees: those pixels, with the snow inside their outlines, are never overwritten.
    Back-tier peaks (apex above row 12) that the mountain's silhouette touches are removed: the big mountain replaces them."""
    big, (X0, X1, Y0, Y1) = _pieces(px, x0, y0)
    keep = set()
    for comp in big:
        if min(y for _, y in comp) < back_y and any(p in sil for p in comp):
            for (X, Y) in comp:
                px[Y][X] = 0
        else:
            keep.update(comp)
    reach, st = set(), []
    for Y in range(Y0, Y1):
        for X in range(X0, X1):
            if (X in (X0, X1 - 1) or Y in (Y0, Y1 - 1)) and (X, Y) not in keep:
                reach.add((X, Y))
                st.append((X, Y))
    while st:
        cx, cy = st.pop()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = cx + dx, cy + dy
            if X0 <= nx < X1 and Y0 <= ny < Y1 and (nx, ny) not in keep and (nx, ny) not in reach:
                reach.add((nx, ny))
                st.append((nx, ny))
    return {(X, Y) for Y in range(Y0, Y1) for X in range(X0, X1) if (X, Y) not in reach}


# The ranges' peaks as the map places them (dump_scenes.py PLAN, stage 1c): (x px, foot row px, variant).  Back tier foot on row 24, front tier foot on row 40.
RANGE_FRONT = [(272, 40, "D"), (304, 40, "C"), (336, 40, "A"), (400, 40, "D"), (432, 40, "B"), (464, 40, "D")]
RANGE_BACK = [(288, 24, "A"), (320, 24, "B"), (352, 24, "C"), (384, 24, "B"), (416, 24, "A"), (448, 24, "C"), (480, 24, "B")]
# B replaces the peaks that stand mostly inside its outline (half or more of their width over the mountain's foot, x 312..401): these are taken out and their neighbours repainted whole
REPLACED_B = {(320, 24), (352, 24), (384, 24), (304, 40), (336, 40)}


def _peak_pixels(x, base, k):
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "smap_venue_redesign3" / "src"))
    import range_peaks as RP
    rws = RP.VARIANTS[k]
    return {(x + i, base - len(rws) + j): int(c) for j, r in enumerate(rws) for i, c in enumerate(r) if c != "."}


def _replace_peaks(WORLDS):
    """take the REPLACED_B peaks out (their pixels back to snow 0), then repaint every other peak that touched one of them, back tier first, so no neighbour is left cut"""
    gone = {}
    for x, base, k in RANGE_BACK + RANGE_FRONT:
        if (x, base) in REPLACED_B:
            gone[(x, base)] = _peak_pixels(x, base, k)
    cut = set().union(*gone.values())
    for w in WORLDS:
        for (X, Y) in cut:
            w.px[Y][X] = 0
        for tier in (RANGE_BACK, RANGE_FRONT):
            for x, base, k in tier:
                if (x, base) in REPLACED_B:
                    continue
                pp = _peak_pixels(x, base, k)
                if any(p in cut for p in pp):
                    for (X, Y), v in pp.items():
                        w.px[Y][X] = v


def _front_peaks():
    """Mountain B stands OVER the remaining back-tier peaks (their pixels under its outline are overwritten, the rest stay: a natural overlap) and BEHIND the remaining front-tier peaks:
    the pixels of the front peaks (every char of their typed rows that is not '.', snow caps included) are never overwritten."""
    out = set()
    for x, base, k in RANGE_FRONT:
        if (x, base) not in REPLACED_B:
            out |= set(_peak_pixels(x, base, k))
    return out


def apply(W_, WORLDS, key):
    """paste the mountain with its top-left at the placement (cropped by the map edges), behind the peaks already there; the cells it touches take the palette `igloo`"""
    x0, y0, _ = PLACES[key]
    rs = rows()
    touched = set()
    sil = {(x0 + i, y0 + j) for j, r in enumerate(rs) for i, c in enumerate(r) if c != "."}
    if key == "B":
        _replace_peaks(WORLDS)
    for w in WORLDS:
        front = _front_peaks() if key == "B" else _front(w.px, x0, y0, sil)
        for j, r in enumerate(rs):
            for i, c in enumerate(r):
                X, Y = x0 + i, y0 + j
                if c == "." or not (0 <= X < 512 and 0 <= Y < 512) or (X, Y) in front:
                    continue
                w.px[Y][X] = int(c)
                touched.add((X // 8, Y // 8))
    for (cx, cy) in touched:
        assert (cx, cy) not in WORLDS[0].roads, (cx, cy)
        for w in WORLDS:
            if w.pal[cy][cx] != "igloo":
                w.pal[cy][cx] = "igloo"
    import os
    if key == "B" and os.environ.get("SMAP_FALLS") in ("A", "B"):     # SMAP_FALLS=A|B: the falls v2 proposals (smap_falls_v2/falls_v2.py), instead of the cave
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "smap_falls_v2"))
        import falls_v2
        touched |= falls_v2.apply(WORLDS, os.environ["SMAP_FALLS"])
    elif key == "B" and os.environ.get("SMAP_NO_CAVE") != "1":      # SMAP_NO_CAVE=1: B at its new place without the cave (to cost the cave)
        import falls_cave                                  # the falls come out of a cave mouth in B's right flank (falls_cave.py)
        touched |= falls_cave.apply(WORLDS)
    for (cx, cy) in EXTRA_SNOW.get(key, []):                # typed: one cell tab on the snowfield's west edge, so the snow / grass line does not run straight down beside the foot
        assert (cx, cy) not in WORLDS[0].roads
        for w in WORLDS:
            w.pal[cy][cx] = "igloo"
        touched.add((cx, cy))
    return touched


if __name__ == "__main__":
    print("\n".join(rows()))
