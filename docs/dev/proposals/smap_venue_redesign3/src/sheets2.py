"""python3 sheets2.py: the contact sheets of round 2 (read-only on the repo; writes only into docs/dev/proposals/smap_venue_redesign2/ and out/r2/).
  cow_sheet.png, zoo_sheet.png, mountain_sheet.png, stadium_sheet.png : today | options, DMG above and Color below, x3
  kit_sheet.png : the mountain accessory pieces, desert and snowy, DMG and Color, x4
  range_sheet.png : mountain A with the kit beside it (desert), the igloo with the snowy kit around it, DMG and Color, x2
Prints the DMG unique tile counts."""
import importlib
import os
import subprocess
import sys

import common as C
import mtn_pieces as MP
import scene
import today

OUT = C.ROOT + '/docs/dev/proposals/smap_venue_redesign2'
TMP = C.ROOT + '/out/r3/tmp'
os.makedirs(TMP, exist_ok=True)
SHEET = C.ROOT + '/tools/dev/contact_sheet.py'

GROUPS = {
    'cow': ('cow', ['cow_a', 'cow_b', 'cow_c', 'cow_d'], 3, 4),
    'zoo': ('zoo', ['zoo_a', 'zoo_b'], 3, 3),
    'mountain': ('space', ['mountain_a', 'mountain_b'], 3, 1),
    'stadium': ('stadium', ['park_a', 'park_b'], 3, 3),
}
LABEL = {'cow_a': 'A  option 1 as picked', 'cow_b': 'B  slant roof', 'cow_c': 'C  bottle sign', 'cow_d': 'D  roadside cow', 'zoo_a': 'A  giraffe left, bamboo right',
         'zoo_b': 'B  bamboo left, tall giraffe right', 'mountain_a': 'A  three peaks', 'mountain_b': 'B  twin summits, long range', 'park_a': 'A  wedge field',
         'park_b': 'B  bowl'}


def sheet(path, items, scale, cols, title):
    subprocess.run([sys.executable, SHEET, path, '--scale', str(scale), '--cols', str(cols), '--title', title] + [f'{l}={p}' for l, p in items], check=True, capture_output=True)
    print('wrote', path)


def one(key):
    tname, names, scale, cols = GROUPS[key]
    biome, at = today.BIO[tname], today.AT[tname]
    rows = {False: [], True: []}
    for cgb in (False, True):
        tag = 'Color' if cgb else 'DMG'
        C.cgb_unmerge = False
        tc = today.canvas(tname, dmg=not cgb)
        f = f'{TMP}/{key}_today_{tag}.png'
        C.render(tc, biome, at, cgb).save(f)
        rows[cgb].append((f'TODAY {tag}', f))
        for n in names:
            m = importlib.import_module(n)
            C.cgb_unmerge = getattr(m, 'UNMERGE', True)
            f = f'{TMP}/{n}_{tag}.png'
            C.render(m.build(), m.BIOME, m.AT, cgb).save(f)
            rows[cgb].append((f'{LABEL[n]} {tag}', f))
    C.cgb_unmerge = False
    if cols == 1:
        items = [rows[False][0], rows[False][1], rows[False][2], rows[True][0], rows[True][1], rows[True][2]]
    else:
        items = rows[False] + rows[True]
    sheet(f'{OUT}/{key}_sheet.png', items, scale, len(rows[False]) if cols != 1 else 1, f'{key}: today | options (DMG above, Color below)')
    for n in names:
        m = importlib.import_module(n)
        print(n, m.build().w, m.build().h, 'DMG tiles', C.tile_count(m.build(), getattr(m, 'REGION', None)))


def kit():
    items = []
    for snow, biome, at in ((False, 'desert', (1, 34)), (True, 'snow', (53, 6))):
        c = MP.kit_canvas(snow)
        for cgb in (False, True):
            f = f'{TMP}/kit_{"snow" if snow else "desert"}_{"c" if cgb else "d"}.png'
            C.render(c, biome, at, cgb, margin=1).save(f)
            items.append((f'{"SNOWY" if snow else "DESERT"} kit {"Color" if cgb else "DMG"}', f))
    sheet(f'{OUT}/kit_sheet.png', [items[0], items[2], items[1], items[3]], 4, 2,
          'mountain range pieces: foothill, small peak, medium peak, ridge, spur, rock (desert left, snowy right; DMG above, Color below)')
    for snow in (False, True):
        ps = MP.pieces(snow)
        print('kit', 'snowy' if snow else 'desert', {n: C.tile_count(p) for n, p in ps.items()}, 'all together', C.tile_count(MP.kit_canvas(snow)))
    d, s = MP.kit_canvas(False), MP.kit_canvas(True)
    cd, cs = C.cells(d), C.cells(s)
    shared = sum(1 for k in cd if cd[k][0] == cs[k][0] and cd[k][0] != C.BLANK)
    print('kit cells identical on DMG between desert and snowy:', shared, 'of', sum(1 for k in cd if cd[k][0] != C.BLANK), 'non-blank')


def range_scenes():
    import mountain_a as MA
    import igloo_1 as IG
    d, s = MP.pieces(False), MP.pieces(True)
    ma = MA.build()
    top = 1
    bot = top + 7                                          # the cell row holding the mountain's foot (y 63)
    des = [(ma, 0, top), (d['spur'], 25, bot - 1), (d['peak_s'], 27, bot - 1), (d['ridge'], 29, bot - 1), (d['peak_m'], 33, bot - 2),
           (d['foothill'], 8, bot + 1), (d['foothill'], 21, bot + 1), (d['rock'], 15, bot + 1), (d['foothill'], 29, bot + 1), (d['rock'], 26, bot + 1)]
    ig = IG.build()
    snow = [(s['peak_m'], 0, 1), (s['ridge'], 3, 2), (s['peak_s'], 7, 2), (s['peak_m'], 9, 1), (s['spur'], 12, 2), (s['ridge'], 14, 2), (s['foothill'], 0, 4),
            (s['foothill'], 2, 5), (s['rock'], 17, 6), (s['peak_s'], 17, 3), (ig, 3, 3), (s['foothill'], 14, 9), (s['rock'], 1, 9), (s['foothill'], 15, 10)]
    items = []
    for cgb in (False, True):
        tag = 'Color' if cgb else 'DMG'
        f = f'{TMP}/range_desert_{tag}.png'
        scene.render_scene('desert', (1, 34), 40, 11, des, cgb).save(f)
        items.append((f'desert range, mountain A with the kit {tag}', f))
        f = f'{TMP}/range_snow_{tag}.png'
        scene.render_scene('snow', (53, 6), 20, 12, snow, cgb).save(f)
        items.append((f'igloo option 1 among snowy mountains {tag}', f))
    sheet(f'{OUT}/range_sheet.png', [items[0], items[2], items[1], items[3]], 2, 2, 'range pieces in place (DMG above, Color below)')


if __name__ == '__main__':
    which = sys.argv[1:] or ['cow', 'zoo', 'mountain', 'stadium', 'kit', 'range']
    for w in which:
        if w == 'kit':
            kit()
        elif w == 'range':
            range_scenes()
        else:
            one(w)
