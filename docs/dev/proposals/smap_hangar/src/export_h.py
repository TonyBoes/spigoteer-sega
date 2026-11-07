"""python3 export_h.py: write each option (with the strip) as an indexed PNG for the lint script: out/hangar/lint/NAME_dmg.png and NAME_cgb.png.  Only transcribes the typed grids."""
import os

import mtn_h as M
import common as C
from PIL import Image

OUT = C.ROOT + '/out/hangar/lint'
os.makedirs(OUT, exist_ok=True)


def write(n, c):
    rows = c.out()
    cs = C.cells(c)
    im = Image.new('P', (c.w, c.h))
    flat = []
    for s in C.P.DMG_SHADE:
        flat += [s, s, s]
    im.putpalette(flat + [0] * (768 - len(flat)))
    for y in range(c.h):
        for x in range(c.w):
            im.putpixel((x, y), int(rows[y][x]))
    im.save(f'{OUT}/{n}_dmg.png')
    pals = []
    for (i, j), (t, p) in cs.items():
        if p not in pals:
            pals.append(p)
    im2 = Image.new('P', (c.w, c.h))
    flat = []
    for p in pals:
        for col in C.P.get(p):
            flat += list(col)
    im2.putpalette(flat + [0] * (768 - len(flat)))
    for y in range(c.h):
        for x in range(c.w):
            p = cs[(x // 8, y // 8)][1]
            im2.putpixel((x, y), pals.index(p) * 4 + int(rows[y][x]))
    im2.save(f'{OUT}/{n}_cgb.png')
    print(n, 'palettes', pals)


for n2, kw in (('k1', dict(which='h2e', runway='c', plane='K1', raised=True)), ('k2', dict(which='h2e', runway='c', plane='K2', raised=True))):
    write('mtn_' + n2, M.build(**kw))
for w in ('r3', 'h1', 'h2'):
    write('mtn_' + w, M.build(w, w != 'r3'))
