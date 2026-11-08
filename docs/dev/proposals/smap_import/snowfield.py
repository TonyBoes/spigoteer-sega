"""One continuous snowfield under ranges B and C (stage 1c, owner review: "snow coloured blocks behind the peaks over the grass read as halos").
The range scenes paste only their non-blank cells, so the blank snow cells between the peaks stayed grass and the pasted ones looked like isolated light-blue squares.
Here the snow ground cells (the igloo palette, index 0 = snow, pixels all 0: the flat tile the map already has) are added by hand-listed rows so every peak stands on snow and the
field's edge is stepped: the west side steps one cell per row, a grass tongue reaches up to the falls source, and a few snow cells hang below the peaks' feet between the pines.
Nothing at the falls source (the water cells from row 5 down at x 46..47) is touched."""

# absolute cells (x, y) added as snow ground
ADD = {
    0: [39, 43, 44, 47, 51, 55, 56, 59, 63],       # the gaps between the peaks along the map's top edge
    3: [46, 62, 63],                               # B's east foot (the grass tongue to the falls source is x 47..49), C's east end joins the igloo's snow below
    4: [62, 63],
    5: [35, 36, 39, 40, 43],                       # the fringe below B's feet, in the gaps between the pines
}


def apply(W):
    changed = []
    for y, xs in ADD.items():
        for x in xs:
            for w in (W.WORLD, W.WORLD_DMG):
                for j in range(8):
                    for i in range(8):
                        w.px[y * 8 + j][x * 8 + i] = 0
                w.pal[y][x] = "igloo"
            changed.append((x, y))
    return changed
