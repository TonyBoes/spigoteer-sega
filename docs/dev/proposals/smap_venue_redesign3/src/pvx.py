"""python3 pvx.py MODULE [scale]: quick look at MODULE.previews() = [(label, canvas, biome, at)], DMG above and Color below, one sheet out/r3/MODULE_pvx.png"""
import importlib
import subprocess
import sys

import common as C

OUT = C.ROOT + '/out/r3'


def look(name, scale=5):
    m = importlib.import_module(name)
    items = {False: [], True: []}
    for lab, c, biome, at in m.previews():
        print(lab, c.w, c.h, 'tiles', C.tile_count(c))
        for cgb in (False, True):
            f = f'{OUT}/{name}_{lab}_{"c" if cgb else "d"}.png'
            C.render(c, biome, at, cgb, margin=1).save(f)
            items[cgb].append(f'{lab} {"Color" if cgb else "DMG"}={f}')
    out = f'{OUT}/{name}_pvx.png'
    subprocess.run([sys.executable, C.ROOT + '/tools/dev/contact_sheet.py', out, '--scale', str(scale), '--cols', str(len(items[False]))] + items[False] + items[True],
                   check=True, capture_output=True)
    print('->', out)


if __name__ == '__main__':
    look(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 5)
