"""python3 sheet.py: the contact sheet (round 3 | option 1 | option 2, DMG row then Color row, x3), the tile counts, and the indexed PNGs for the lint (out/stad/lint)."""
import os
import subprocess
import sys

from PIL import Image

import common as C
import park_a3 as A
import park_s1 as S1
import park_s2 as S2

OUT = C.ROOT + '/docs/dev/proposals/smap_stadium'
TMP = C.ROOT + '/out/stad/tmp'
LINT = C.ROOT + '/out/stad/lint'
os.makedirs(LINT, exist_ok=True)

pieces = [('ROUND 3', A), ('OPTION 1 covered grandstand', S1), ('OPTION 2 curved bowl, bunting', S2)]
rows = {False: [], True: []}
for cgb in (False, True):
    for lab, m in pieces:
        C.cgb_unmerge = True
        f = f'{TMP}/{m.__name__}_{"C" if cgb else "D"}.png'
        C.render(m.build(), m.BIOME, m.AT, cgb).save(f)
        rows[cgb].append((f'{lab} {"Color" if cgb else "DMG"}', f))
items = rows[False] + rows[True]
subprocess.run([sys.executable, C.ROOT + '/tools/dev/contact_sheet.py', OUT + '/stadium_r4_sheet.png', '--scale', '3', '--cols', '3', '--title',
                'stadium round 4: round 3 | option 1 | option 2 (DMG above, Color below)'] + [f'{l}={p}' for l, p in items], check=True)
print('round 3', C.tile_count(A.build()))
print('option 1', C.tile_count(S1.build()), 'without pennants', C.tile_count(S1.build(flags=False)))
print('option 2', C.tile_count(S2.build()), 'without pennants', C.tile_count(S2.build(bunting=False)))
for n, m in (('s1', S1), ('s2', S2)):
    c = m.build()
    im = Image.new('P', (c.w, c.h))
    im.putpalette([248, 248, 248, 168, 168, 168, 88, 88, 88, 24, 24, 24] + [0] * 756)
    for y, r in enumerate(c.out()):
        for x, ch in enumerate(r):
            im.putpixel((x, y), int(ch))
    im.save(f'{LINT}/{n}.png')
