"""Helpers for the venue redesign proposals: typed ASCII pieces (my grids), the render of a piece on its biome's ground, the DMG tile count.
Nothing here decides a pixel.  A piece is typed as ASCII rows: '0'..'3' are palette indices, '_' is transparent (pieces only)."""
import sys

ROOT = '/workspace/.claude/worktrees/agent-ad92c4ce81f826634'
sys.path.insert(0, ROOT + '/tools/smap_world')
from PIL import Image  # noqa: E402

import pal as P  # noqa: E402
import tiles as T  # noqa: E402
import world2 as W  # noqa: E402
from canvas import Canvas  # noqa: E402

BIOME = {  # biome -> (ground palette, ground tile set)
    'snow': ('igloo', 'snow'), 'farm': ('farm', 'farm'), 'jungle': ('zoo', 'jungle'), 'desert': ('saloon', 'desert'), 'paved': ('stadium', 'paved'),
}
# PARK (proposed, for the ballpark's field cells only): chalk / white concrete (the stadium yard's own colour), mown grass, infield dirt, ink.
# Same colours as the game already has: 0 and 3 from STADIUM, the grass from GRASS (6aa048), the dirt from ROAD (c8a068).
P.RGB['park'] = [P.h(x) for x in ('d4d8e4', '68b048', 'c09050', '101428')]
P.RGB['mtnsnow'] = P.RGB['igloo']


def G(*rows):
    """typed rows -> list of strings; every row must have the same width; a (row, n) tuple repeats the row n times"""
    out = []
    for r in rows:
        if isinstance(r, tuple):
            out += [r[0]] * r[1]
        else:
            out.append(r)
    w = len(out[0])
    for i, r in enumerate(out):
        assert len(r) == w, f"row {i} is {len(r)} wide, wanted {w}: {r}"
    return out


def paste(c, x, y, rows, pal=None):
    """paste typed rows into a Canvas at (x, y); '_' and '.' are transparent"""
    for j, r in enumerate(rows):
        for i, ch in enumerate(r):
            if ch not in '_.':
                X, Y = x + i, y + j
                assert 0 <= X < c.w and 0 <= Y < c.h, f"{c.name}: goes off the picture at {X},{Y}"
                c.px[Y][X] = ch


def ground_cell(biome, cx, cy):
    """the world's own ground tile for a cell (same hash as World.build): flat, or the tuft now and then"""
    vs = T.GROUND[BIOME[biome][1]]
    h = (cx * 7 + cy * 13 + cx * cy) % 13
    return vs[0] if h not in (3, 8, 11) or len(vs) == 1 else vs[1]


def cells(c):
    """a Canvas -> {(i, j): (rows, palette)}"""
    rows = c.out()
    cps = c.cellpals()
    out = {}
    for j in range(c.h // 8):
        for i in range(c.w // 8):
            out[(i, j)] = (tuple(rows[j * 8 + k][i * 8:i * 8 + 8] for k in range(8)), cps[j][i])
    return out


BLANK = tuple(["00000000"] * 8)
GROUND_TILES = {tuple(t) for g in T.GROUND.values() for t in g}


def tile_count(c, region=None):
    """unique DMG tiles of a piece, exactly as the DMG data set counts them (no flips); an all-index-0 cell and the biome's ground tiles are free"""
    seen = set()
    for (i, j), (t, p) in cells(c).items():
        if region and not (region[0] <= i <= region[2] and region[1] <= j <= region[3]):
            continue
        if t == BLANK or t in GROUND_TILES:
            continue
        seen.add(t)
    return len(seen)


def render(c, biome, at, cgb, margin=1, region=None):
    """the piece over its biome's ground, margin cells all round; blank cells inside the piece take the ground's tiles too (no flat pad).
    at = the piece's top left cell in the world; returns a PIL image"""
    gp = BIOME[biome][0]
    cw, ch = c.w // 8, c.h // 8
    im = Image.new('RGB', ((cw + 2 * margin) * 8, (ch + 2 * margin) * 8))
    cs = cells(c)
    for j in range(-margin, ch + margin):
        for i in range(-margin, cw + margin):
            if (i, j) in cs and cs[(i, j)][0] != BLANK:
                t, p = cs[(i, j)]
                p = W.MERGE.get(p, p) if not cgb_unmerge else p
            else:
                t, p = ground_cell(biome, at[0] + i, at[1] + j), gp
            cols = P.get(p) if cgb else None
            for y in range(8):
                for x in range(8):
                    v = int(t[y][x])
                    im.putpixel(((i + margin) * 8 + x, (j + margin) * 8 + y), tuple(cols[v]) if cols else (P.DMG_SHADE[v],) * 3)
    return im


cgb_unmerge = False   # set True to show ZOOGATE as its own palette (the game folds it into ZOO today)


def tilemap(c):
    """print the cell grid: '.' blank/ground, a letter per unique tile (a repeated tile gets its letter again)"""
    ids = {}
    names = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
    cs = cells(c)
    for j in range(c.h // 8):
        line = ''
        for i in range(c.w // 8):
            t = cs[(i, j)][0]
            if t == BLANK or t in GROUND_TILES:
                line += '.'
            else:
                ids.setdefault(t, names[len(ids) % len(names)])
                line += ids[t]
        print(line)
    print(len(ids), 'unique')


def silh(c, y0, hw, cx, body, top_ink=True):
    """a symmetric dome-like silhouette typed as half widths per row (the width list is mine, row by row): the outline is the typed edge of each row,
    with the run that joins it to the row above when the edge jumps by more than a pixel; body(x, y, k) is the interior pixel.  Centred between cx-1 and cx."""
    pl = pr = None
    for k, h in enumerate(hw):
        y = y0 + k
        L, R = cx - h, cx + h - 1
        for x in range(L, R + 1):
            ink = x in (L, R) or (k == 0 and top_ink)
            if pl is not None:
                ink = ink or (L <= x < pl) or (pr < x <= R)
            c.px[y][x] = '3' if ink else body(x, y, k)
        pl, pr = L, R
