"""python3 sheet_h8.py: round 4h sheet: 4g jet on sand | fixed (jet clear of hangar and tower, all BASE cells), DMG and Color close-up (x6) and whole mountain (x2); prints tile counts."""
import subprocess
import sys

import jet2_h
import mtn_h as M
import strip5_h
import strip6_h
import common as C
from PIL import Image

ROOT = C.ROOT
OUT = ROOT + '/docs/dev/proposals/smap_hangar'
TMP = ROOT + '/out/hangar'
SHADOW = [(63, 33, '1111111'), (63, 50, '11111'), (62, 51, '111')]


def build(k):
    c = M.build(which='h2e', runway=False, raised=True)
    if k == 's':
        strip5_h.strip5(c)
        strip5_h.shadow(c, SHADOW)
        C.paste(c, 32, 52, jet2_h.pose('L'))
    else:
        strip6_h.strip6(c)
        C.paste(c, 4, 57, jet2_h.pose('L'))
    return c


NAMES = {'s': '4g JET ON SAND', 'f': 'FIXED: JET CLEAR OF HANGAR AND TOWER'}


def render(k, cgb):
    return C.render(build(k), M.BIOME, M.AT, cgb)


def crop(im):
    c = im.crop((0, 8 + 34, 8 + 64, 8 + 72))
    return c.resize((c.width * 6, c.height * 6), Image.NEAREST)


if __name__ == '__main__':
    print('unique DMG tiles of the mountain piece')
    for k in NAMES:
        print(f'{NAMES[k]:40s} {C.tile_count(build(k), M.REGION)}')
    items = []
    for cgb in (False, True):
        t = 'Color' if cgb else 'DMG'
        for k in NAMES:
            f = f'{TMP}/c8_{k}_{t}.png'
            crop(render(k, cgb)).save(f)
            items.append((f'{NAMES[k]}, {t} (x6)', f))
    for cgb in (False, True):
        t = 'Color' if cgb else 'DMG'
        for k in NAMES:
            f = f'{TMP}/w8_{k}_{t}.png'
            im = render(k, cgb)
            im.resize((im.width * 2, im.height * 2), Image.NEAREST).save(f)
            items.append((f'whole mountain, {NAMES[k]}, {t} (x2)', f))
    subprocess.run([sys.executable, ROOT + '/tools/dev/contact_sheet.py', OUT + '/hangar_sheet8.png', '--scale', '1', '--cols', '2', '--title',
                    'space mountain hangar round 4h: 4g jet on sand | fixed (DMG above, Color below)'] + [f'{l}={p}' for l, p in items], check=True)
