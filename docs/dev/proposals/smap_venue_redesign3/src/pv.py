"""python3 pv.py NAME [scale]: quick look at one piece, DMG and Color, over its biome's ground; prints the DMG unique tile count."""
import importlib
import os
import subprocess
import sys

import common as C

OUT = C.ROOT + '/out/r3'
os.makedirs(OUT, exist_ok=True)


def look(name, scale=4):
    m = importlib.import_module(name)
    c = m.build()
    C.cgb_unmerge = getattr(m, 'UNMERGE', True)
    fs = []
    for cgb in (False, True):
        f = f'{OUT}/{name}_{"c" if cgb else "d"}.png'
        C.render(c, m.BIOME, m.AT, cgb, margin=getattr(m, 'MARGIN', 1)).save(f)
        fs.append(f'{"Color" if cgb else "DMG"}={f}')
    out = f'{OUT}/{name}_pv.png'
    subprocess.run([sys.executable, C.ROOT + '/tools/dev/contact_sheet.py', out, '--scale', str(scale), '--cols', '2', '--title', f'{name} {c.w}x{c.h}'] + fs,
                   check=True, capture_output=True)
    print(name, c.w, c.h, 'DMG tiles', C.tile_count(c, getattr(m, 'REGION', None)), '->', out)


if __name__ == '__main__':
    look(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 4)
