"""python3 export.py: transcribe each proposal into indexed PNGs for the skill's lint (out/mb/lint/NAME_dmg.png, NAME_cgb.png). Only transcribes the typed grids."""
import os

import common as C
import cow_lot as L
from PIL import Image

OUT = C.ROOT + '/out/mb/lint'
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


import cow_a3
write('A', L.build_a())
write('B', L.build_b())
write('C', L.build_c())
