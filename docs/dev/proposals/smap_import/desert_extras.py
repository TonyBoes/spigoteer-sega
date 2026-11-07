"""Desert extras (owner 11-07: "small mountains in the desert", "have the desert cross the road a bit. A cactus tile would be nice."): proposal only, nothing in src/ or assets/.
Everything is typed here by hand (gb-pixel-art): the five small peaks, the four cactus pieces, the three spill stretches and every place.

SPILLS  where the road bounds the desert, a few cells of desert ground carry over to the far side of the road: row by row spans (x0, x1) typed, no two neighbouring rows alike.  They are
        whole ground cells (the map's own desert biome, same tiles and the same palette as the rest), the road cells are not touched.
PEAKS   the airbase peaks' family (palette `saloon`: 0 sand, 1 lit rock, 2 shaded rock, 3 ink, light from the top left, lit left, shaded right), smaller: 12 to 18 px wide, 8 to 14 tall,
        each one drawn differently (knob, twin summit, mesa, spire, long slope).  Transparent '.' keeps the ground; every peak is placed in pixels, 3 px or more clear of any other art.
CACTI   four pieces on the palette `cactus` ([sand, light green, dark green, ink]: the map grass' three colours on the desert sand), sand background so they stand on the desert ground:
        S two arms (1 x 2 cells), S2 one arm (1 x 2), B barrel (1 x 1), Q small with one arm (1 x 1).  DMG: the same indices, four shades."""

SPILL_GROUPS = {"N": {27: (21, 25), 26: (22, 24), 25: (23, 24)},      # north of the north road, east of the saloon's sand (rows 28 and 29 are the road)
                "S1": {47: (9, 16), 48: (11, 14)},                   # south of the south road (rows 45 and 46 are the road)
                "S2": {47: (28, 32), 48: (30, 31)}}

D = "."


def sp(*rows):
    """typed rows (lead dots, lit width, shaded width): ink, lit rock, shaded rock, ink"""
    return [D * l + "3" + "1" * a + "2" * b + "3" for (l, a, b) in rows]


PEAKS = {
    # cone: one summit, a steady slope each side (20 x 16)
    "cone": [D * 9 + "33" + D * 9, D * 8 + "3113" + D * 8] + [s + D * (20 - len(s)) for s in
            sp((8, 2, 1), (7, 3, 1), (7, 3, 2), (6, 4, 2), (6, 4, 3), (5, 5, 3), (4, 5, 4), (4, 6, 5), (3, 7, 5), (2, 7, 5), (2, 8, 5), (1, 9, 5), (0, 11, 7))]
            + ["33333233333333333333"],
    # twin: two summits and a saddle, the left one lower (28 x 16)
    "twin": [D * 16 + "33" + D * 10,
             D * 15 + "3113" + D * 9,
             D * 15 + "31123" + D * 8,
             D * 6 + "33" + D * 6 + "311123" + D * 8,
             D * 5 + "3113" + D * 5 + "3111223" + D * 7,
             D * 5 + "31123" + D * 4 + "31111223" + D * 6,
             D * 4 + "311123" + D * 3 + "311112223" + D * 6,
             D * 4 + "3111223" + D * 2 + "3111112223" + D * 5,
             D * 3 + "31111223" + D + "31111122223" + D * 5,
             D * 2 + "3" + "1" * 7 + "22" + "3" + "1" * 4 + "2222" + "3" + D * 6,
             D * 2 + "3" + "1" * 8 + "22" + "3" + "1" * 4 + "22222" + "3" + D * 4,
             D + "3" + "1" * 9 + "222" + "1" * 5 + "22222" + "3" + D * 3,
             D + "3" + "1" * 10 + "222" + "1" * 5 + "222222" + "3" + D,
             "3" + "1" * 11 + "222" + "1" * 5 + "222222" + "3" + D,
             "3" + "1" * 10 + "222" + "1" * 6 + "2222222" + "3",
             "3" * 11 + "2" + "3" * 16],
    # mesa: a flat top, cliffs, a talus skirt (24 x 11)
    "mesa": [D * 4 + "3" * 12 + D * 8] + [s + D * (24 - len(s)) for s in
             sp((3, 10, 2), (3, 10, 3), (3, 10, 3), (3, 10, 3), (3, 10, 3), (2, 12, 4), (1, 14, 4), (1, 15, 5), (0, 17, 5))] + ["3" * 5 + "2" + "3" * 18],
    # spire: tall and thin (14 x 18)
    "spire": [D * 6 + "33" + D * 6, D * 5 + "3113" + D * 5] + [s + D * (14 - len(s)) for s in
              sp((5, 2, 1), (5, 2, 1), (4, 3, 1), (4, 3, 1), (4, 3, 2), (3, 4, 2), (3, 4, 2), (3, 4, 3), (2, 5, 3), (2, 5, 3), (2, 5, 4), (1, 6, 4), (1, 6, 4), (1, 6, 5), (0, 7, 5))]
              + ["33333323333333"],
    # slope: a long gentle shoulder to the left of a summit at the right (30 x 14)
    "slope": [D * 22 + "33" + D * 6, D * 21 + "3113" + D * 5] + [s + D * (30 - len(s)) for s in
              sp((20, 2, 1), (19, 3, 1), (17, 4, 2), (15, 7, 2), (13, 9, 3), (11, 12, 3), (9, 13, 4), (7, 16, 4), (5, 17, 5), (3, 20, 5), (1, 21, 6))]
              + ["3" * 8 + "2" + "3" * 21],
}
MARKS = {"cone": [(9, 5, 6, "2"), (12, 4, 6, "2"), (10, 11, 12, "3")], "twin": [(9, 4, 5, "2"), (12, 4, 7, "2"), (13, 8, 9, "2"), (11, 20, 22, "3")],
         "mesa": [(2, 6, 9, "2"), (4, 5, 8, "2"), (7, 5, 9, "2"), (6, 15, 17, "3")], "spire": [(9, 5, 6, "2"), (13, 3, 5, "2")],
         "slope": [(8, 14, 17, "2"), (10, 11, 14, "2"), (6, 14, 15, "3"), (11, 6, 8, "2"), (10, 21, 24, "3")]}
PEAK_AT = [("twin", 96, 252), ("cone", 176, 250), ("spire", 44, 250), ("slope", 204, 276), ("mesa", 16, 345)]    # (peak, x px, y px of its top-left)

CACTI = {
    "S": ["...33...", "..3113..", "..3113..", "..3113..", "..311333", "..312313", "..312313", "..312113",
          "..312233", "..3123..", "333123..", "313123..", "313123..", "311123..", "333123..", "..3333.."],
    "S2": ["...33...", "..3113..", "..3113..", "..3113..", "..3123..", "..3123..", "..3123..", "..311333",
           "..312313", "..312313", "..312313", "..312113", "..312233", "..3123..", "..3123..", "..3333.."],
    "B": ["........", "..3333..", ".311123.", "31112123", "31121123", "31121123", "31112223", ".333333."],
    "Q": ["...33...", "..3113..", "333113..", "313123..", "311123..", "333123..", "..3123..", "..3333.."],
}
CACTUS_AT = [("S", 9, 31), ("S2", 18, 31), ("Q", 3, 31), ("B", 20, 33), ("B", 11, 43), ("Q", 21, 43), ("B", 27, 43)]     # (piece, cell x, top cell y; a 1 x 1 piece's cell is its y)


def peak_rows(name):
    g = [list(r) for r in PEAKS[name]]
    w = len(g[0])
    for r in g:
        assert len(r) == w, (name, "".join(r))
    for (y, x0, x1, v) in MARKS.get(name, []):
        for x in range(x0, x1 + 1):
            assert g[y][x] in "12", (name, y, x, g[y][x])
            g[y][x] = v
    return ["".join(r) for r in g]


def apply_grid(lay):
    G = lay.GRID
    for grp in SPILL_GROUPS.values():
        for y, (x0, x1) in grp.items():
            for x in range(x0, x1 + 1):
                G[y][x] = "d"
    lay.BIOME_ROWS = ["".join(r) for r in G]
    lay.BIOMES = lay.biomes_from_rows()


def _put(W, WORLDS, x, y, rows, pal, keep_transparent=True):
    for j, row in enumerate(rows):
        for i, ch in enumerate(row):
            if ch == D:
                continue
            for w in WORLDS:
                w.px[y + j][x + i] = int(ch)
    for cy in range(y // 8, (y + len(rows) - 1) // 8 + 1):
        for cx in range(x // 8, (x + len(rows[0]) - 1) // 8 + 1):
            for w in WORLDS:
                w.pal[cy][cx] = pal


ROCKS_CLEARED = [0]


def clear_rocks(W, WORLDS, x0, y0, x1, y1):
    """remove the small rocks (a connected group of at most 40 pixels in desert ground cells) that touch the pixel rectangle: a whole rock goes, never half of one"""
    w0 = W.WORLD
    seen, gone = set(), 0
    for yy in range(max(y0, 0), min(y1, 512)):
        for xx in range(max(x0, 0), min(x1, 512)):
            if w0.px[yy][xx] and (xx, yy) not in seen:
                comp, st = [], [(xx, yy)]
                seen.add((xx, yy))
                while st:
                    cx, cy = st.pop()
                    comp.append((cx, cy))
                    for dx in (-1, 0, 1):
                        for dy in (-1, 0, 1):
                            nx, ny = cx + dx, cy + dy
                            if 0 <= nx < 512 and 0 <= ny < 512 and w0.px[ny][nx] and (nx, ny) not in seen:
                                seen.add((nx, ny))
                                st.append((nx, ny))
                cells = {(px // 8, py // 8) for px, py in comp}
                if len(comp) <= 40 and all(w0.pal[c[1]][c[0]] == "saloon" and w0.kind[c[1]][c[0]] in ("ground", "decor") and c not in w0.roads for c in cells):
                    for px, py in comp:
                        for w in WORLDS:
                            w.px[py][px] = 0
                    gone += 1
    return gone


def apply_world(W, WORLDS, pieces=("peaks", "cacti"), cactus_pal="cactus"):
    cells = []
    ROCKS_CLEARED[0] = 0
    if "peaks" in pieces:
        for name, x, y in PEAK_AT:
            rows = peak_rows(name)
            ROCKS_CLEARED[0] += clear_rocks(W, WORLDS, x - 3, y - 3, x + len(rows[0]) + 3, y + len(rows) + 3)
            _put(W, WORLDS, x, y, rows, "saloon")
            cells.append((name, x, y, len(rows[0]), len(rows)))
    if "cacti" in pieces:
        for name, cx, cy in CACTUS_AT:
            rows = CACTI[name]
            assert all(len(r) == 8 for r in rows), name
            ROCKS_CLEARED[0] += clear_rocks(W, WORLDS, cx * 8 - 2, cy * 8 - 2, cx * 8 + 10, cy * 8 + len(rows) + 2)
            for w in WORLDS:
                for j, row in enumerate(rows):
                    for i, ch in enumerate(row):
                        w.px[cy * 8 + j][cx * 8 + i] = int(ch) if ch != D else 0
                for k in range(len(rows) // 8):
                    w.pal[cy + k][cx] = cactus_pal
            cells.append((name, cx, cy))
    return cells
