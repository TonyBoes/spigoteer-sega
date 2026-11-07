"""python3 options.py: (1) paving options for DMG presence, (2) Color palette options, close-ups x4 of the lot -> ../milkbar_options.png.
(1) plain paving 0 (the proposal) | a grain of shade 1 on an ordered pattern | grey paving 1 with white lines (0 and 1 exchanged inside the lot, a preview of
the same typed grid: if the owner picks it I redo the bikes' chrome by hand).  (2) the lot in FACTORY (pick), TOWN5, TOWN1."""
import subprocess
import sys

import common as C
import cow_lot as L
from PIL import Image

TMP = C.ROOT + '/out/mb'
OUT = C.ROOT + '/docs/dev/proposals/smap_milkbar'


def swap(c):
    for y in range(L.Y0, L.Y1):
        for x in range(L.X0, L.X1):
            v = c.px[y][x]
            c.px[y][x] = {'0': '1', '1': '0'}.get(v, v)
    return c


def up(**k):
    return L.upright({1: L.UP_A, 3: L.UP_B, 4: L.UP_A}, **k)


def sl(**k):
    return L.slant({1: L.SL_A, 3: L.SL_B, 5: L.SL_A}, **k)


def crop(c, cgb):
    im = C.render(c, L.BIOME, L.AT, cgb).crop((24, 46 + 8, 112, 84))
    return im.resize((im.width * 4, im.height * 4), 0)


items = []
for tag, cgb in (('DMG', False), ('Color', True)):
    for lay, mk in (('upright', up), ('slant', sl)):
        for name, c in (('plain paving 0 (proposal)', mk()), ('grain 25 pct + dark lines', mk(grain=True, line='2')), ('grey paving 1, white lines', swap(mk()))):
            f = f'{TMP}/opt_{lay}_{tag}_{name[:5].strip()}.png'
            crop(c, cgb).save(f)
            items.append((f'{lay} {tag}: {name}', f))
subprocess.run([sys.executable, C.ROOT + '/tools/dev/contact_sheet.py', OUT + '/milkbar_options_paving.png', '--scale', '1', '--cols', '3',
                '--title', 'milk bar lot: paving options (rows: upright DMG, slant DMG, upright Color, slant Color)'] + [f'{l}={p}' for l, p in items], check=True)
items = []
for pname in ('factory', 'town5', 'town1'):
    for lay, mk in (('upright', up), ('slant', sl)):
        L.LOT_PAL = pname
        f = f'{TMP}/pal_{lay}_{pname}.png'
        crop(mk(), True).save(f)
        items.append((f'{lay} {pname.upper()}' + (' (pick)' if pname == 'factory' else ''), f))
subprocess.run([sys.executable, C.ROOT + '/tools/dev/contact_sheet.py', OUT + '/milkbar_options_palette.png', '--scale', '1', '--cols', '2',
                '--title', 'milk bar lot: palette options, all already in the map (FACTORY, TOWN5, TOWN1)'] + [f'{l}={p}' for l, p in items], check=True)
