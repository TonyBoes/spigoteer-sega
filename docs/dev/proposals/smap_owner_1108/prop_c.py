"""Proposal C, the road-bend wedges on grass (Color only; the DMG data set is not touched: the same pixels, a palette is Color's).

The two cream wedges (cells (35..37, 44..46) and (50..52, 44..46)) are the bend's ground cells on the road palette town1 (index 0 cream) because 63 + 19 of the 21 x 19 views there already
hold 8 BG palettes.  ctx.py takes them off the compromise (roads_round.OUTER_PAL / INNER) so the bend cells are laid on town1@g, grass as index 0, like the other ten bends.  That puts town1@g
in those views; this module frees a palette in each of them:

  C   the tea house on the town's own palette: every cell the teahouse holds on tea@g (cream 0.. no: grass 0, cream 1, brown 2, ink 3) takes town1@g (grass 0, peach 1, lilac 2, ink 3).  The same
      pixels, so DMG and the 2bpp tiles are unchanged; the house's cream walls become peach and its brown ribs lilac.  tea@g leaves every view (it has no other cell) and town1@g, which the
      wedges need anyway, takes its place: the count of a view is unchanged where both were in it, one lower where only tea@g was.
  C3  the two cacti dropped as in C2, and only the house's east end (the 17 cells at x 32..35: roof tip, right lantern, tree, plank end) on town1@g: both wedges laid on grass.
  C2  without touching the house: only the two desert cacti at (21, 43) and (27, 43) are dropped (their cells become plain sand), which frees `cactus` in the 44 views west of x 30; only the
      west wedge (35..37, 44..46) is laid on grass.  The east wedge needs a palette freed in the 19 views that hold both bends, and nothing but the house or the milk bar can free one there.
"""

TEA_CELLS = None


def apply(W, PAL, mode):
    changed = []
    WORLDS = (W.WORLD, W.WORLD_DMG)
    if mode == "C":
        for y in range(W.CH):
            for x in range(W.CW):
                if W.MERGE.get(W.WORLD.pal[y][x], W.WORLD.pal[y][x]) == "tea@g":
                    W.WORLD.pal[y][x] = "town1@g"                 # Color palette only: no pixel changes
                    changed.append((x, y))
    elif mode == "C3":
        for y in range(W.CH):
            for x in range(32, W.CW):                         # the house's east end: the roof tip, the right lantern, the tree and the plank end (x 32..35)
                if W.MERGE.get(W.WORLD.pal[y][x], W.WORLD.pal[y][x]) == "tea@g":
                    W.WORLD.pal[y][x] = "town1@g"
                    changed.append((x, y))
        changed += apply(W, PAL, "C2")
    elif mode == "C2":
        for (x, y) in ((21, 43), (27, 43)):
            assert W.WORLD.pal[y][x] == "cactus", (x, y, W.WORLD.pal[y][x])
            for w in WORLDS:
                for j in range(8):
                    for i in range(8):
                        w.px[y * 8 + j][x * 8 + i] = 0
                w.pal[y][x] = "saloon"
            changed.append((x, y))
    return changed
