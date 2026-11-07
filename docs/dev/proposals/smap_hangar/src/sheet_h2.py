"""python3 sheet_h2.py: round 4b contact sheet: round 3 | option 2 | new A | new B, DMG and Color, close-up (x6) and whole mountain (x2); a fifth row has the grey tarmac
variant.  Prints the unique DMG tile counts.  Preview only."""
import os
import subprocess
import sys

import mtn_h as M
import common as C
from PIL import Image

ROOT = C.ROOT
OUT = ROOT + '/docs/dev/proposals/smap_hangar'
TMP = ROOT + '/out/hangar'

# name: (label, build kwargs)
V = {
    'r3': ('ROUND 3', dict(which='r3')),
    'h2': ('OPTION 2 (round 4a)', dict(which='h2', runway=True)),
    'A': ('NEW A: 45 deg, nose down-right', dict(which='h2e', runway=True, plane='A', raised=True)),
    'B': ('NEW B: nose toward the viewer', dict(which='h2e', runway=True, plane='B', raised=True)),
    'Ag': ('NEW A, grey tarmac', dict(which='h2e', runway=True, plane='A', tone='1', raised=True)),
    'Bg': ('NEW B, grey tarmac', dict(which='h2e', runway=True, plane='B', tone='1', raised=True)),
    'E': ('NEW hangar, no plane (empty), navy strip', dict(which='h2e', runway=True, raised=True)),
}


def render(k, cgb):
    return C.render(M.build(**V[k][1]), M.BIOME, M.AT, cgb)


def crop(im):
    c = im.crop((0, 8 + 32, 8 + 64, 8 + 72))
    return c.resize((c.width * 3, c.height * 3), Image.NEAREST)


print('unique DMG tiles of the mountain piece (cells 0..24 x 0..8; ground tiles and blank cells free)')
for k in V:
    print(f'{V[k][0]:46s} {C.tile_count(M.build(**V[k][1]), M.REGION)}')

items = []
main = ['r3', 'h2', 'A', 'B']
for cgb in (False, True):
    t = 'Color' if cgb else 'DMG'
    for k in main:
        f = f'{TMP}/c2_{k}_{t}.png'
        crop(render(k, cgb)).save(f)
        items.append((f'{V[k][0]}, {t} (x6)', f))
for cgb in (False, True):
    t = 'Color' if cgb else 'DMG'
    for k in main:
        f = f'{TMP}/w2_{k}_{t}.png'
        render(k, cgb).save(f)
        items.append((f'whole mountain, {V[k][0]}, {t} (x2)', f))
for k, cgb in (('Ag', True), ('Bg', True), ('Ag', False), ('Bg', False)):
    t = 'Color' if cgb else 'DMG'
    f = f'{TMP}/c2_{k}_{t}.png'
    crop(render(k, cgb)).save(f)
    items.append((f'{V[k][0]}, {t} (x6)', f))
args = [sys.executable, ROOT + '/tools/dev/contact_sheet.py', OUT + '/hangar_sheet2.png', '--scale', '2', '--cols', '4', '--title',
        'space mountain hangar round 4b: round 3 | option 2 | new A | new B (DMG, then Color; last row: grey tarmac variant)'] + [f'{l}={p}' for l, p in items]
subprocess.run(args, check=True)
