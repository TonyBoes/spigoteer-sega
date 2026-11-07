"""python3 render_one.py MODE  (MODE = a5 | 4e | arr1 | arr2; for arr1 and arr2 run with env MB_PASTURE=1: the hay field is gone and the cow venue is a stub)
Builds the A5 world (scratch generator), pastes the picture over it, writes out/mb/r6_MODE_{DMG,Color}.png (a crop of the map, 1x, with a red tick at Sal's stop)
and out/mb/r6_MODE.json (unique DMG tiles of the whole map, worst 21 x 19 window anywhere and among the windows that touch the milk bar's area, the worst
Color palette count per 21 x 19 window).  Nothing is written outside out/mb/.
 a5   = the A5 map as it is (hay field, round 2's milk bar)
 4e   = round 4e's piece (cow_lot4.build) over the A5 map, hay field still there
 arr1 / arr2 = cow_a5.build(1 or 2) at cell (50, 47) over the A5 map without the hay field"""
import json
import sys

import a5env  # noqa: F401  (first)
import common as C
import world2 as WD
from PIL import Image

import numpy as np

P = C.P
TMP = C.ROOT + '/out/mb'
mode = sys.argv[1]
X0, Y0, X1, Y1 = 40, 44, 64, 70                 # the crop, in cells
STOP = (418, 508)


def piece():
    if mode == 'a5':
        return None, None
    if mode == '4e':
        import cow_lot4 as N
        return N.build(), (50, 55)
    import cow_a5 as A
    if mode.startswith('roof'):
        return A.build(3, 'A', int(mode[4])), (50, 47)
    if mode.startswith('bld'):
        return A.build(3, mode[3]), (50, 47)
    return A.build(int(mode[3])), (50, 47)


def paste_world(w, c, at):
    cs = C.cells(c)
    if mode == '4e':                                # round 2's venue is in the world: its blank cells under the picture become ground
        rx0, ry0, rx1, ry1 = w.venue_rect['cow']
        for cy in range(ry0, ry1 + 1):
            for cx in range(rx0, rx1 + 1):
                g = C.ground_cell('farm', cx, cy)
                for j in range(8):
                    for i in range(8):
                        w.px[cy * 8 + j][cx * 8 + i] = int(g[j][i])
                w.pal[cy][cx] = 'farm'
    for (i, j), (t, p) in cs.items():
        if t == C.BLANK:
            continue
        cx, cy = at[0] + i, at[1] + j
        for y in range(8):
            for x in range(8):
                w.px[cy * 8 + y][cx * 8 + x] = int(t[y][x])
        w.pal[cy][cx] = p


def tile_rgb(w, cx, cy, cgb):
    cols = P.get(WD.MERGE.get(w.pal[cy][cx], w.pal[cy][cx]))
    im = Image.new('RGB', (8, 8))
    for y in range(8):
        for x in range(8):
            v = w.px[cy * 8 + y][cx * 8 + x]
            im.putpixel((x, y), tuple(cols[v]) if cgb else (P.DMG_SHADE[v],) * 3)
    return im


def shot(w, cgb):
    im = Image.new('RGB', ((X1 - X0) * 8, (Y1 - Y0) * 8))
    for cy in range(Y0, Y1):
        for cx in range(X0, X1):
            im.paste(tile_rgb(w, cx, cy, cgb), ((cx - X0) * 8, (cy - Y0) * 8))
    sx, sy = STOP[0] - X0 * 8, STOP[1] - Y0 * 8
    for d in range(-2, 3):
        im.putpixel((sx + d, sy), (255, 0, 0))
        im.putpixel((sx, sy + d), (255, 0, 0))
    return im


def counts(wd, wc):
    CW, CH = WD.CW, WD.CH
    ids = {}
    g = np.zeros((CH, CW), int)
    for y in range(CH):
        for x in range(CW):
            k = bytes(wd.px[y * 8 + j][x * 8 + i] for j in range(8) for i in range(8))
            g[y, x] = ids.setdefault(k, len(ids))
    best, at, near, nat = 0, None, 0, None
    for y0 in range(CH - 18):
        for x0 in range(CW - 20):
            n = len(np.unique(g[y0:y0 + 19, x0:x0 + 21]))
            if n > best:
                best, at = n, (x0, y0)
            if x0 <= 61 and x0 + 20 >= 50 and y0 <= 69 and y0 + 18 >= 47 and n > near:
                near, nat = n, (x0, y0)
    pg = np.zeros((CH, CW), int)
    pid = {}
    for y in range(CH):
        for x in range(CW):
            pg[y, x] = pid.setdefault(wc.pal[y][x], len(pid))
    pbest = 0
    for y0 in range(CH - 18):
        for x0 in range(CW - 20):
            pbest = max(pbest, len(np.unique(pg[y0:y0 + 19, x0:x0 + 21])))
    return {"unique_tiles": len(ids), "worst_21x19": best, "worst_at": at, "worst_near_milkbar": near, "near_at": nat, "palettes_21x19": pbest}


def main():
    c, at = piece()
    wd, wc = WD.WORLD_DMG, WD.WORLD
    if c is not None:
        paste_world(wd, c, at)
        paste_world(wc, c, at)
    res = counts(wd, wc)
    if c is not None:
        res["piece_tiles"] = C.tile_count(c)
    json.dump(res, open(f'{TMP}/r6_{mode}.json', 'w'), default=str)
    cc = C.render(c, 'farm', at, False, margin=0) if c is not None else None
    if c is not None:
        C.render(c, 'farm', at, False, margin=0).crop((16, 80, 96, 144)).save(f'{TMP}/r6_{mode}_closeDMG.png')
        C.render(c, 'farm', at, True, margin=0).crop((16, 80, 96, 144)).save(f'{TMP}/r6_{mode}_closeColor.png')
    shot(wd, False).save(f'{TMP}/r6_{mode}_DMG.png')
    shot(wc, True).save(f'{TMP}/r6_{mode}_Color.png')
    print(mode, res)


main()
