"""python3 quick.py MODULE [MODULE...]: scratch render (x3) of DMG and Color for each module, and its DMG tile count."""
import importlib
import subprocess
import sys

import common as C

OUT = C.ROOT + '/out/stad/tmp'
items = []
for n in sys.argv[1:]:
    m = importlib.import_module(n)
    c = m.build()
    print(n, 'DMG tiles', C.tile_count(c))
    for cgb in (False, True):
        C.cgb_unmerge = True
        f = f'{OUT}/{n}_{"C" if cgb else "D"}.png'
        C.render(c, m.BIOME, m.AT, cgb).save(f)
        items.append((f'{n} {"Color" if cgb else "DMG"}', f))
subprocess.run([sys.executable, C.ROOT + '/tools/dev/contact_sheet.py', OUT + '/quick.png', '--scale', '4', '--cols', '2'] + [f'{l}={p}' for l, p in items], check=True)
