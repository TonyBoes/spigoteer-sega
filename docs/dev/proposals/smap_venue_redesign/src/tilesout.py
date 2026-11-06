"""python3 tilesout.py: the repeating patterns of the proposals as tiles, run through the skill's tiled_preview.py (4 x 4 repeat), one contact sheet of the results"""
import os
import subprocess
import sys

import common as C
import cow_2
import igloo_1
import mountain_1
import zoo_1
import zoo_2
from PIL import Image

OUT = C.ROOT + '/out/redesign/tiles'
os.makedirs(OUT, exist_ok=True)
SCRIPT = os.path.expanduser('~/.claude/skills/gb-pixel-art/scripts/tiled_preview.py')
PATS = {
    'igloo_ice_lit': igloo_1.MID, 'igloo_ice_shade': igloo_1.SHADE, 'igloo_tunnel': igloo_1.LIT,
    'cow_print_16': cow_2.PRINT,
    'zoo_stone': zoo_1.STONE, 'zoo_thatch': zoo_2.THATCH, 'zoo_thatch_shade': zoo_2.THATCH_D, 'zoo_neck': zoo_2.NECK, 'zoo_fence': zoo_2.FENCE,
    'mtn_columns_lit': [mountain_1.COL_L] * 8, 'mtn_columns_shade': [mountain_1.COL_D] * 8, 'mtn_scree_lit': mountain_1.SCREE_L,
}
files = []
for n, rows in PATS.items():
    im = Image.new('P', (len(rows[0]), len(rows)))
    flat = []
    for s in C.P.DMG_SHADE:
        flat += [s, s, s]
    im.putpalette(flat + [0] * (768 - len(flat)))
    for y, r in enumerate(rows):
        for x, ch in enumerate(r):
            im.putpixel((x, y), int(ch))
    f = f'{OUT}/{n}.png'
    im.save(f)
    o = f'{OUT}/{n}_tiled.png'
    subprocess.run([sys.executable, SCRIPT, f, '--repeat', '4', '--scale', '2', '--out', o], check=True, capture_output=True)
    files.append(f'{n}={o}')
subprocess.run([sys.executable, C.ROOT + '/tools/dev/contact_sheet.py', C.ROOT + '/out/redesign/tiled_all.png', '--scale', '1', '--cols', '4'] + files, check=True,
               capture_output=True)
print('ok')
