"""python3 sheets.py: the contact sheets of the proposal (read-only on the repo; writes only into docs/dev/proposals/smap_venue_redesign/ and out/redesign/).
  igloo_sheet.png, cow_sheet.png, zoo_sheet.png, mountain_sheet.png : today | option 1 | option 2, DMG row and Color row, x3
  map_in_place.png : the four first-picks on the current map, DMG and Color, x2
Prints the tile counts and the worst-window palette count of the composite."""
import copy
import importlib
import os
import subprocess
import sys
from collections import Counter

import common as C
import today
from PIL import Image, ImageDraw

OUT = C.ROOT + '/docs/dev/proposals/smap_venue_redesign'
TMP = C.ROOT + '/out/redesign/tmp'
os.makedirs(TMP, exist_ok=True)
W, P, T = C.W, C.P, C.T

PIECES = {'igloo': ('igloo_1', 'igloo_2'), 'cow': ('cow_1', 'cow_2'), 'zoo': ('zoo_1', 'zoo_2'), 'mountain': ('mountain_1', 'mountain_2')}
TODAY = {'igloo': 'igloo', 'cow': 'cow', 'zoo': 'zoo', 'mountain': 'space'}
PICK = {'igloo': 'igloo_1', 'cow': 'cow_2', 'zoo': 'zoo_1', 'mountain': 'mountain_2'}
VENUE = {'igloo': 'igloo', 'cow': 'cow', 'zoo': 'zoo', 'mountain': 'space'}


def one_sheet(key):
    tname = TODAY[key]
    biome, at = today.BIO[tname], today.AT[tname]
    imgs = []
    for cgb in (False, True):
        tag = 'Color' if cgb else 'DMG'
        C.cgb_unmerge = False
        tc = today.canvas(tname, dmg=not cgb)
        f = f'{TMP}/{key}_today_{tag}.png'
        C.render(tc, biome, at, cgb).save(f)
        imgs.append((f'TODAY {tag}', f))
        for n in PIECES[key]:
            m = importlib.import_module(n)
            C.cgb_unmerge = getattr(m, 'UNMERGE', False)
            f = f'{TMP}/{n}_{tag}.png'
            C.render(m.build(), biome, at, cgb).save(f)
            imgs.append((f'{n.upper().replace("_", " ")} {tag}', f))
    C.cgb_unmerge = False
    out = f'{OUT}/{key}_sheet.png'
    subprocess.run([sys.executable, C.ROOT + '/tools/dev/contact_sheet.py', out, '--scale', '3', '--cols', '3', '--title', f'{key}: today | option 1 | option 2 (DMG above, Color below)']
                   + [f'{l}={p}' for l, p in imgs], check=True, capture_output=True)
    print('wrote', out)


# ---- the map in place ----
def world_ground(w, cx, cy):
    vs = T.GROUND[W.BIOME_TILES[w.biome[cy][cx]]]
    h = (cx * 7 + cy * 13 + cx * cy) % 13
    return vs[0] if h not in (3, 8, 11) or len(vs) == 1 else vs[1]


def composite(dmg):
    base = W.WORLD_DMG if dmg else W.WORLD
    w = copy.copy(base)
    w.px = [r[:] for r in base.px]
    w.pal = [r[:] for r in base.pal]
    w.kind = [r[:] for r in base.kind]

    def set_tile(cx, cy, rows, pal):
        for j in range(8):
            for i in range(8):
                w.px[cy * 8 + j][cx * 8 + i] = int(rows[j][i])
        w.pal[cy][cx] = pal

    over = set()
    for key, n in PICK.items():
        x0, y0, x1, y1 = base.venue_rect[VENUE[key]]
        for cy in range(y0, y1 + 1):
            for cx in range(x0, x1 + 1):
                set_tile(cx, cy, world_ground(w, cx, cy), w.ground_pal[cy][cx])
        m = importlib.import_module(n)
        c = m.build()
        cw, ch = c.w // 8, c.h // 8
        left = x0 + ((x1 - x0 + 1) - cw) // 2
        top = y1 - ch + 1
        for (i, j), (t, p) in C.cells(c).items():
            cx, cy = left + i, top + j
            if t == C.BLANK:
                continue
            if (cx, cy) in base.roads:
                over.add(n)
            set_tile(cx, cy, t, p if getattr(m, 'UNMERGE', False) else W.MERGE.get(p, p))
        print(n, 'placed at cell', (left, top), 'size', (cw, ch), 'today rect', (x0, y0, x1, y1))
    print('pieces that overlap today\'s roads (the layout is being redone):', sorted(over))
    return w


def render_world(w, cgb):
    im = Image.new('RGB', (W.PW, W.PH))
    for cy in range(W.CH):
        for cx in range(W.CW):
            cols = P.get(w.pal[cy][cx]) if cgb else None
            for j in range(8):
                for i in range(8):
                    v = w.px[cy * 8 + j][cx * 8 + i]
                    im.putpixel((cx * 8 + i, cy * 8 + j), tuple(cols[v]) if cols else (P.DMG_SHADE[v],) * 3)
    return im


def worst_window(w):
    best = (0, None)
    for y0 in range(W.CH - 18):
        for x0 in range(W.CW - 20):
            n = len(Counter(w.pal[y][x] for y in range(y0, y0 + 19) for x in range(x0, x0 + 21)))
            if n > best[0]:
                best = (n, (x0, y0))
    return best


def main():
    for key in PIECES:
        one_sheet(key)
    items = []
    for dmg in (True, False):
        w = composite(dmg)
        f = f'{TMP}/map_{"DMG" if dmg else "Color"}.png'
        render_world(w, not dmg).save(f)
        items.append((('DMG' if dmg else 'Color') + ' map, first picks in place', f))
        if not dmg:
            print('Color worst 21x19 window palettes, with the picks:', worst_window(w), ' today:', worst_window(W.WORLD))
    subprocess.run([sys.executable, C.ROOT + '/tools/dev/contact_sheet.py', f'{OUT}/map_in_place.png', '--scale', '2', '--cols', '1', '--title',
                    'first picks (igloo 1, cow 2, zoo 1, mountain 2) on the current map'] + [f'{l}={p}' for l, p in items], check=True, capture_output=True)
    print('wrote map_in_place.png')


if __name__ == '__main__':
    main()
