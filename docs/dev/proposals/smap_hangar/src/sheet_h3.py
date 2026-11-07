"""python3 sheet_h3.py: round 4c sheet: option 2 (4a) | new 1 | new 2, DMG and Color, close-up (x6) and whole mountain (x2); prints the unique DMG tile counts."""
import subprocess
import sys

import mtn_h as M
import common as C
from PIL import Image

ROOT = C.ROOT
OUT = ROOT + '/docs/dev/proposals/smap_hangar'
TMP = ROOT + '/out/hangar'
V = {
    'h2': ('OPTION 2 (4a)', dict(which='h2', runway=True)),
    'P1': ('NEW 1: nose down about 20 deg', dict(which='h2e', runway='c', plane='P1', raised=True)),
    'P2': ('NEW 2: nose down about 30 deg', dict(which='h2e', runway='c', plane='P2', raised=True)),
    'E': ('new hangar, empty, no plane', dict(which='h2e', runway='c', raised=True)),
}


def render(k, cgb):
    return C.render(M.build(**V[k][1]), M.BIOME, M.AT, cgb)


def crop(im):
    c = im.crop((0, 8 + 34, 8 + 64, 8 + 72))
    return c.resize((c.width * 3, c.height * 3), Image.NEAREST)


print('unique DMG tiles of the mountain piece')
for k in V:
    print(f'{V[k][0]:34s} {C.tile_count(M.build(**V[k][1]), M.REGION)}')
items = []
main = ['h2', 'P1', 'P2']
for cgb in (False, True):
    t = 'Color' if cgb else 'DMG'
    for k in main:
        f = f'{TMP}/c3_{k}_{t}.png'
        crop(render(k, cgb)).save(f)
        items.append((f'{V[k][0]}, {t} (x6)', f))
for cgb in (False, True):
    t = 'Color' if cgb else 'DMG'
    for k in main:
        f = f'{TMP}/w3_{k}_{t}.png'
        render(k, cgb).save(f)
        items.append((f'whole mountain, {V[k][0]}, {t} (x2)', f))
subprocess.run([sys.executable, ROOT + '/tools/dev/contact_sheet.py', OUT + '/hangar_sheet3.png', '--scale', '2', '--cols', '3', '--title',
                'space mountain hangar round 4c: option 2 (4a) | new 1 | new 2 (DMG above, Color below)'] + [f'{l}={p}' for l, p in items], check=True)
