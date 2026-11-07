"""python3 sheet_h6.py: round 4g sheet: (a) jet on the dark runway | (b) jet on a light apron, DMG and Color close-up (x6) and whole mountain (x2); prints tile counts."""
import subprocess
import sys

import jet2_h
import mtn_h as M
import strip4_h
import strip5_h
import common as C
from PIL import Image

ROOT = C.ROOT
OUT = ROOT + '/docs/dev/proposals/smap_hangar'
TMP = ROOT + '/out/hangar'


JX, JY = 32, 52
SHADOW = [(63, 33, '1111111'), (63, 50, '11111'), (62, 51, '111')]


def build(k):
    c = M.build(which='h2e', runway=False, raised=True)
    if k in ('s', 't'):
        strip5_h.strip5(c, taxi=(k == 't'))
        strip5_h.shadow(c, SHADOW)
        C.paste(c, JX, JY, jet2_h.pose('L'))
        return c
    strip4_h.strip4(c, '2' if k == 'a' else '1')
    C.paste(c, 29 if k == 'a' else 4, 55, jet2_h.pose('L'))
    return c


NAMES = {'a': '(a) JET ON THE DARK RUNWAY', 'b': '(b) JET ON A LIGHT APRON', 's': 'JET ON SAND', 't': 'JET ON SAND + TAXI STRIP'}


def render(k, cgb):
    return C.render(build(k), M.BIOME, M.AT, cgb)


def crop(im):
    c = im.crop((0, 8 + 34, 8 + 64, 8 + 72))
    return c.resize((c.width * 6, c.height * 6), Image.NEAREST)


if __name__ == '__main__':
    print('unique DMG tiles of the mountain piece')
    for k in NAMES:
        print(f'{NAMES[k]:34s} {C.tile_count(build(k), M.REGION)}')
    items = []
    for cgb in (False, True):
        t = 'Color' if cgb else 'DMG'
        for k in NAMES:
            f = f'{TMP}/c7_{k}_{t}.png'
            crop(render(k, cgb)).save(f)
            items.append((f'{NAMES[k]}, {t} (x6)', f))
    for cgb in (False, True):
        t = 'Color' if cgb else 'DMG'
        for k in NAMES:
            f = f'{TMP}/w7_{k}_{t}.png'
            im = render(k, cgb)
            im.resize((im.width * 2, im.height * 2), Image.NEAREST).save(f)
            items.append((f'whole mountain, {NAMES[k]}, {t} (x2)', f))
    subprocess.run([sys.executable, ROOT + '/tools/dev/contact_sheet.py', OUT + '/hangar_sheet7.png', '--scale', '1', '--cols', '4', '--title',
                    'space mountain hangar round 4g: (a) | (b) | jet on sand | jet on sand + taxi strip (DMG above, Color below)'] + [f'{l}={p}' for l, p in items], check=True)
