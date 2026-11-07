"""python3 sheet_h.py: renders round 3 / option 1 / option 2, with and without the strip, DMG and Color; prints the unique DMG tile counts; writes the contact sheet."""
import os
import subprocess
import sys

import mtn_h as M
import common as C
from PIL import Image

ROOT = C.ROOT
OUT = ROOT + '/docs/dev/proposals/smap_hangar'
TMP = ROOT + '/out/hangar'
os.makedirs(TMP, exist_ok=True)
names = [('r3', 'ROUND 3'), ('h1', 'OPTION 1 arch front'), ('h2', 'OPTION 2 curved roof, slid doors')]


def img(which, rw, cgb):
    return C.render(M.build(which, rw), M.BIOME, M.AT, cgb)


def crop(im):
    """the base: cells 0..8 wide, from cell row 5 to the bottom, doubled (preview only, nearest neighbour); the sheet then shows it x6"""
    c = im.crop((0, 8 * 5, 8 * 9, im.height))
    return c.resize((c.width * 2, c.height * 2), Image.NEAREST)


print('unique DMG tiles of the mountain piece (cells 0..24 x 0..8; ground tiles and blank cells free)')
for w, lab in names:
    for rw in (False, True):
        print(f'{lab:36s} strip={rw!s:5s} {C.tile_count(M.build(w, rw), M.REGION)}')

items = []
for cgb in (False, True):
    t = 'Color' if cgb else 'DMG'
    for w, lab in names:
        f = f'{TMP}/crop_{w}_{t}.png'
        crop(img(w, w != 'r3', cgb)).save(f)
        items.append((f'{lab}{" + strip" if w != "r3" else ""}, {t} (x6)', f))
for w, lab in names[1:]:
    f = f'{TMP}/crop_{w}_DMG_nostrip.png'
    crop(img(w, False, False)).save(f)
for cgb in (False, True):
    t = 'Color' if cgb else 'DMG'
    for w, lab in names:
        f = f'{TMP}/whole_{w}_{t}.png'
        img(w, w != 'r3', cgb).save(f)
        items.append((f'whole mountain, {lab}{" + strip" if w != "r3" else ""}, {t} (x3)', f))
args = [sys.executable, ROOT + '/tools/dev/contact_sheet.py', OUT + '/hangar_sheet.png', '--scale', '3', '--cols', '3', '--title',
        'space mountain hangar: round 3 | option 1 | option 2 (DMG rows above, Color below)'] + [f'{l}={p}' for l, p in items]
subprocess.run(args, check=True)
