"""python3 export3.py: write every option as an indexed PNG for the skill's lint script (out/r3/lint/NAME_dmg.png and NAME_cgb.png).
The DMG file has the four grey shades (entry 0 lightest); the Color file has one group of four entries per palette the piece uses, each cell in its own group.
This only transcribes the typed grids."""
import importlib
import os

import common as C
import mtn_vert as V
from PIL import Image

OUT = C.ROOT + '/out/r3/lint'
os.makedirs(OUT, exist_ok=True)
NAMES = ['cow_a3', 'zoo_a3', 'zoo_b3', 'mountain_a3', 'mountain_a3r', 'park_a3']


def write(n, c, unmerge=True):
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
        p = p if unmerge else C.W.MERGE.get(p, p)
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
            p = p if unmerge else C.W.MERGE.get(p, p)
            im2.putpixel((x, y), pals.index(p) * 4 + int(rows[y][x]))
    im2.save(f'{OUT}/{n}_cgb.png')
    print(n, c.w, c.h, 'palettes', pals)


for n in NAMES:
    m = importlib.import_module(n)
    write(n, m.build())
write('vert_column_desert', V.column(4, False))
write('vert_column_snowy', V.column(4, True))
write('vert_zigzag_desert', V.stack([(0, 0), (8, 16), (0, 32), (8, 48), (0, 64)], 40, 88, False))
write('vert_single', V.single(False))
write('horiz_row_desert', V.horizontal(False))
