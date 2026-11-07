"""Scenes for the previews: pieces placed on a biome's own ground (the world's tuft pattern), cell by cell.  Only non-blank cells of a piece replace the ground,
exactly as the world generator does.  Nothing here decides a pixel."""
from PIL import Image

import common as C

P, W = C.P, C.W


def render_scene(biome, at, cw, ch, placements, cgb, unmerge=True):
    """placements: [(canvas, cell x, cell y)], painted in order"""
    gp = C.BIOME[biome][0]
    cells = {}
    for j in range(ch):
        for i in range(cw):
            cells[(i, j)] = (C.ground_cell(biome, at[0] + i, at[1] + j), gp)
    for (cv, px, py) in placements:
        for (i, j), (t, p) in C.cells(cv).items():
            if t == C.BLANK:
                continue
            if 0 <= px + i < cw and 0 <= py + j < ch:
                cells[(px + i, py + j)] = (t, p if unmerge else W.MERGE.get(p, p))
    im = Image.new('RGB', (cw * 8, ch * 8))
    for (i, j), (t, p) in cells.items():
        cols = P.get(p) if cgb else None
        for y in range(8):
            for x in range(8):
                v = int(t[y][x])
                im.putpixel((i * 8 + x, j * 8 + y), tuple(cols[v]) if cols else (P.DMG_SHADE[v],) * 3)
    return im
