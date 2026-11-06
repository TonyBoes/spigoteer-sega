"""python3 export.py: write every option as an indexed PNG for the skill's lint script (out/redesign/lint/NAME_dmg.png and NAME_cgb.png).
The DMG file has the four grey shades (entry 0 lightest); the Color file has one group of four entries per palette the piece uses, each cell in its own group.
This only transcribes the typed grids."""
import importlib
import os

import common as C
from PIL import Image

OUT = C.ROOT + '/out/redesign/lint'
os.makedirs(OUT, exist_ok=True)
NAMES = ['igloo_1', 'igloo_2', 'cow_1', 'cow_2', 'zoo_1', 'zoo_2', 'mountain_1', 'mountain_2']
for n in NAMES:
    m = importlib.import_module(n)
    c = m.build()
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
        p = C.W.MERGE.get(p, p) if not getattr(m, 'UNMERGE', False) else p
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
            p = C.W.MERGE.get(p, p) if not getattr(m, 'UNMERGE', False) else p
            im2.putpixel((x, y), pals.index(p) * 4 + int(rows[y][x]))
    im2.save(f'{OUT}/{n}_cgb.png')
    print(n, c.w, c.h, 'palettes', pals)
