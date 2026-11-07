"""My hand-typed edits for the stadium on the A5 map (map cell = piece cell + (1, 1)).  Everything here is typed: the gate cells and the road's opening.
THE CONNECTION: the stadium's home plate is on the map at x 56, its blank bottom cell row (cells y 10) lies between the apron (ends at map y 79) and the road (cell row 11, y 88 to 103).
A 16 px walkway (12 px inside) (2 px lilac borders like the road's, peach inside) runs from the apron to the road, with a gate pillar (2 px ink with a lilac lit corner, 4 rows) at each side where it leaves the field.
Palette: the two cells in town1, the road's own (no grass pixel in them).  The road cells (6, 11) and (7, 11) lose their top border where the walkway joins."""

# cell (6, 10) and (7, 10), 8 rows each, typed.  1 peach, 2 lilac, 3 ink, 0 cream dot.  16 px wide, no grass pixel in them, so they can stay in the road's own town1 palette
GATE_L = ["23111111", "33111111", "33111111", "33111111", "22111111", "22111111", "22110111", "22111111"]
GATE_R = ["11111123", "11111133", "11011133", "11111133", "11111122", "11111122", "11111122", "11111122"]
# the road cells' top three rows, typed: the border (x 48, 49 and 62, 63) runs on into the road, the opening between
OPEN_L = ["22111111", "22111111", "22111111"]
OPEN_R = ["11111122", "11111122", "11111122"]


def edit(W):
    for w in (W.WORLD, W.WORLD_DMG):
        for cx, rows in ((6, GATE_L), (7, GATE_R)):
            for y in range(8):
                for x in range(8):
                    w.px[10 * 8 + y][cx * 8 + x] = int(rows[y][x])
            w.pal[10][cx] = "town1"
        for cx, rows in ((6, OPEN_L), (7, OPEN_R)):
            for y in range(3):
                for x in range(8):
                    w.px[11 * 8 + y][cx * 8 + x] = int(rows[y][x])


# the right-hand field cells (map cells (11,5) (11,6) (12,6) (11,7) (12,7)) are the only PARK cells that share a 21 x 19 window with the bistro and the town: there they take the map's own
# GRASS palette (field grass 1 is 6aa048 against PARK's 68b048; the 2 px foul line there turns dark green 28603c): no PARK in windows x 11 and 12, so 8 palettes, not 9.
GRASS_CELLS = ((11, 5), (11, 6), (12, 6), (11, 7), (12, 7))


def edit_grass_cells(W):
    for w in (W.WORLD, W.WORLD_DMG):
        for cx, cy in GRASS_CELLS:
            w.pal[cy][cx] = "grass"
