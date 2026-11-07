"""python3 sheet_h4.py: round 4d sheet: reference | 4c new 1 | jet A | jet B, DMG and Color close-up (x6) and whole mountain (x2); prints the unique DMG tile counts."""
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
    'P1': ('4c NEW 1', dict(which='h2e', runway='c', plane='P1', raised=True)),
    'J1': ('JET A: fully out on the apron', dict(which='h2e', runway='c', plane='J1', raised=True)),
    'J2': ('JET B: tail still in the doors', dict(which='h2e', runway='c', plane='J2', raised=True)),
}


def render(k, cgb):
    return C.render(M.build(**V[k][1]), M.BIOME, M.AT, cgb)


def crop(im):
    c = im.crop((0, 8 + 34, 8 + 64, 8 + 72))
    return c.resize((c.width * 3, c.height * 3), Image.NEAREST)


ref = Image.open(OUT + '/owner_jet_example.webp').convert('RGBA')
bg = Image.new('RGBA', ref.size, (200, 200, 200, 255))
bg.alpha_composite(ref)
bg = bg.convert('RGB').crop((100, 120, 700, 340))
bg = bg.resize((bg.width // 2, bg.height // 2), Image.NEAREST)
bg.save(f'{TMP}/ref_small.png')

print('unique DMG tiles of the mountain piece')
for k in V:
    print(f'{V[k][0]:34s} {C.tile_count(M.build(**V[k][1]), M.REGION)}')
items = []
for cgb in (False, True):
    t = 'Color' if cgb else 'DMG'
    items.append((f'owner reference (as sent)', f'{TMP}/ref_small.png'))
    for k in ('P1', 'J1', 'J2'):
        f = f'{TMP}/c4_{k}_{t}.png'
        crop(render(k, cgb)).save(f)
        items.append((f'{V[k][0]}, {t} (x6)', f))
for cgb in (False, True):
    t = 'Color' if cgb else 'DMG'
    for k in ('h2', 'P1', 'J1', 'J2'):
        f = f'{TMP}/w4_{k}_{t}.png'
        render(k, cgb).save(f)
        items.append((f'whole mountain, {V[k][0]}, {t} (x2)', f))
subprocess.run([sys.executable, ROOT + '/tools/dev/contact_sheet.py', OUT + '/hangar_sheet4.png', '--scale', '2', '--cols', '4', '--title',
                'space mountain hangar round 4d: reference | 4c new 1 | jet A | jet B (DMG above, Color below)'] + [f'{l}={p}' for l, p in items], check=True)
