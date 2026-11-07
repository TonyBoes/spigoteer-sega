"""python3 sheet2.py: option 2 (as proposed) | final, DMG and Color x3, and an x6 close-up of the top; prints tile counts and writes the lint PNG."""
import subprocess
import sys

from PIL import Image

import common as C
import park_s2 as N
import park_s2_old as O

OUT = C.ROOT + '/docs/dev/proposals/smap_stadium'
TMP = C.ROOT + '/out/stad/tmp'
items, top = [], []
for cgb in (False, True):
    C.cgb_unmerge = True
    for lab, m in (('OPTION 2 as proposed', O), ('FINAL', N)):
        f = f'{TMP}/f_{m.__name__}_{"C" if cgb else "D"}.png'
        im = C.render(m.build(), m.BIOME, m.AT, cgb)
        im.save(f)
        items.append((f'{lab} {"Color" if cgb else "DMG"}', f))
        g = f'{TMP}/top_{m.__name__}_{"C" if cgb else "D"}.png'
        im.crop((0, 0, 112, 56)).save(g)
        top.append((f'{lab} {"Color" if cgb else "DMG"} top', g))
subprocess.run([sys.executable, C.ROOT + '/tools/dev/contact_sheet.py', OUT + '/stadium_final_sheet.png', '--scale', '3', '--cols', '2', '--title', 'stadium option 2 | final (DMG above, Color below)'] + [f'{l}={p}' for l, p in items], check=True)
subprocess.run([sys.executable, C.ROOT + '/tools/dev/contact_sheet.py', OUT + '/stadium_final_top_x6.png', '--scale', '6', '--cols', '2', '--title', 'close-up of the top, x6'] + [f'{l}={p}' for l, p in top], check=True)
print('option 2 as proposed', C.tile_count(O.build()), 'final', C.tile_count(N.build()), 'final without flag/bunting', C.tile_count(N.build(bunting=False)))
c = N.build()
im = Image.new('P', (c.w, c.h))
im.putpalette([248, 248, 248, 168, 168, 168, 88, 88, 88, 24, 24, 24] + [0] * 756)
for y, r in enumerate(c.out()):
    for x, ch in enumerate(r):
        im.putpixel((x, y), int(ch))
im.save(C.ROOT + '/out/stad/lint/final.png')
