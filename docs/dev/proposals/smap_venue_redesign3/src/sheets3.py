"""python3 sheets3.py [mountain stadium cow zoo range]: the contact sheets of round 3 (writes only into docs/dev/proposals/smap_venue_redesign3/ and out/r3/).
Every sheet: round 2 | round 3, DMG above and Color below, x3 (the range sheets x3 as well).  Prints the unique DMG tile counts."""
import importlib
import os
import subprocess
import sys

import common as C
import mtn_pieces as MP
import mtn_vert as V
import scene

OUT = C.ROOT + '/docs/dev/proposals/smap_venue_redesign3'
TMP = C.ROOT + '/out/r3/tmp'
os.makedirs(TMP, exist_ok=True)
SHEET = C.ROOT + '/tools/dev/contact_sheet.py'


def sheet(path, items, scale, cols, title):
    subprocess.run([sys.executable, SHEET, path, '--scale', str(scale), '--cols', str(cols), '--title', title] + [f'{l}={p}' for l, p in items], check=True, capture_output=True)
    print('wrote', path)


def mod(n):
    return importlib.import_module(n)


def render_items(entries, tag):
    """entries: [(label, module name)] -> DMG items then Color items"""
    rows = {False: [], True: []}
    for cgb in (False, True):
        t = 'Color' if cgb else 'DMG'
        for lab, n in entries:
            m = mod(n)
            C.cgb_unmerge = getattr(m, 'UNMERGE', True)
            f = f'{TMP}/{tag}_{n}_{t}.png'
            C.render(m.build(), m.BIOME, m.AT, cgb).save(f)
            rows[cgb].append((f'{lab} {t}', f))
    C.cgb_unmerge = False
    for lab, n in entries:
        m = mod(n)
        print(tag, n, 'DMG tiles', C.tile_count(m.build(), getattr(m, 'REGION', None)))
    return rows[False] + rows[True]


def mountain():
    items = render_items([('ROUND 2 A', 'mountain_a'), ('ROUND 3 A (no runway)', 'mountain_a3'), ('ROUND 3 A with angled runway (variant)', 'mountain_a3r')], 'mtn')
    sheet(f'{OUT}/mountain_sheet.png', [items[0], items[1], items[2], items[3], items[4], items[5]], 3, 1, 'space mountain: round 2 | round 3 (DMG rows then Color rows)')


def stadium():
    items = render_items([('ROUND 2 A', 'park_a'), ('ROUND 3 A', 'park_a3')], 'park')
    sheet(f'{OUT}/stadium_sheet.png', items, 3, 2, 'stadium A: round 2 | round 3 quality pass (DMG above, Color below)')


def cow():
    items = render_items([('ROUND 2 A', 'cow_a'), ('ROUND 2 C (the bottle sign)', 'cow_c'), ('ROUND 3 A + C sign + lot', 'cow_a3')], 'cow')
    sheet(f'{OUT}/cow_sheet.png', items, 3, 3, 'milk bar: round 2 A and C | round 3 (DMG above, Color below)')


def zoo():
    items = render_items([('ROUND 2 A', 'zoo_a'), ('ROUND 3 A thin neck', 'zoo_a3'), ('ROUND 2 B', 'zoo_b'), ('ROUND 3 B thin neck', 'zoo_b3')], 'zoo')
    sheet(f'{OUT}/zoo_sheet.png', items, 3, 4, 'zoo A and B: round 2 | round 3 thinner giraffe neck (DMG above, Color below)')


def range_sheets():
    d2, s2 = MP.pieces(False), MP.pieces(True)
    items_v, items_h = [], []
    for snow, biome, at in ((False, 'desert', (1, 34)), (True, 'snow', (53, 6))):
        # vertical: round 2 pieces stacked (peak_m every 16 px, whole cells replace each other), then round 3 straight column, zigzag column
        pm, rg = (s2 if snow else d2)['peak_m'], (s2 if snow else d2)['ridge']
        zig = V.stack([(0, 0), (8, 16), (0, 32), (8, 48), (0, 64)], 40, 88, snow)
        col = V.column(4, snow)
        place_v = [(pm, 1, 0), (pm, 1, 2), (pm, 1, 4), (pm, 1, 6), (col, 7, 0), (zig, 13, 0)]
        for cgb in (False, True):
            f = f'{TMP}/rangeV_{"snow" if snow else "desert"}_{"c" if cgb else "d"}.png'
            scene.render_scene(biome, at, 19, 12, place_v, cgb).save(f)
            items_v.append((f'{"SNOWY" if snow else "DESERT"} {"Color" if cgb else "DMG"}', f))
        # horizontal: round 2 kit in a row | round 3 staggered row
        hor = V.horizontal(snow)
        place_h = [((s2 if snow else d2)['peak_m'], 0, 3), ((s2 if snow else d2)['ridge'], 3, 4), ((s2 if snow else d2)['peak_s'], 7, 4), ((s2 if snow else d2)['peak_m'], 9, 3),
                   (hor, 0, 7)]
        for cgb in (False, True):
            f = f'{TMP}/rangeH_{"snow" if snow else "desert"}_{"c" if cgb else "d"}.png'
            scene.render_scene(biome, at, 16, 11, place_h, cgb).save(f)
            items_h.append((f'{"SNOWY" if snow else "DESERT"} {"Color" if cgb else "DMG"}', f))
    # order: DMG desert, DMG snowy, Color desert, Color snowy
    sheet(f'{OUT}/range_vertical_sheet.png', [items_v[0], items_v[2], items_v[1], items_v[3]], 3, 2, 'VERTICAL: left to right round 2 peak_m stacked, round 3 column of 4, round 3 zigzag column of 5 (DMG above, Color below; desert left, snowy right)')
    sheet(f'{OUT}/range_horizontal_sheet.png', [items_h[0], items_h[2], items_h[1], items_h[3]], 3, 2, 'HORIZONTAL: top round 2 pieces, bottom round 3 peaks in a staggered row (DMG above, Color below; desert left, snowy right)')
    ps = {n: C.tile_count(p) for n, p in V.__dict__.items() if False}
    print('round 3 single peak', C.tile_count(V.single(False)), 'column 2..5', [C.tile_count(V.column(n, False)) for n in (2, 3, 4, 5)],
          'zigzag 5', C.tile_count(V.stack([(0, 0), (8, 16), (0, 32), (8, 48), (0, 64)], 40, 88)), 'horizontal row', C.tile_count(V.horizontal(False)))
    print('round 2 kit (6 pieces) together', C.tile_count(MP.kit_canvas(False)))
    d, s = V.column(4, False), V.column(4, True)
    cd, cs = C.cells(d), C.cells(s)
    print('desert/snowy cells identical on DMG:', sum(1 for k in cd if cd[k][0] == cs[k][0] and cd[k][0] != C.BLANK), 'of', sum(1 for k in cd if cd[k][0] != C.BLANK))


if __name__ == '__main__':
    which = sys.argv[1:] or ['mountain', 'stadium', 'cow', 'zoo', 'range']
    for w in which:
        {'mountain': mountain, 'stadium': stadium, 'cow': cow, 'zoo': zoo, 'range': range_sheets}[w]()
