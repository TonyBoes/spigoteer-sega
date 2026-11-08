"""python3 preview.py NAME [scale]: render src/NAME.py (a module with build() and BIOME/AT) as DMG and Color on its ground, print the tile count."""
import importlib
import sys

import common as C
from PIL import Image

name = sys.argv[1]
sc = int(sys.argv[2]) if len(sys.argv) > 2 else 4
m = importlib.import_module(name)
c = m.build()
C.cgb_unmerge = getattr(m, 'UNMERGE', False)
reg = getattr(m, 'REGION', None)
a = C.render(c, m.BIOME, m.AT, False)
b = C.render(c, m.BIOME, m.AT, True)
sheet = Image.new('RGB', (a.width * 2 + 8, a.height), (40, 40, 40))
sheet.paste(a, (0, 0))
sheet.paste(b, (a.width + 8, 0))
sheet = sheet.resize((sheet.width * sc, sheet.height * sc), Image.NEAREST)
out = C.ROOT + f'/out/redesign/{name}.png'
sheet.save(out)
print(name, c.w, c.h, 'DMG tiles', C.tile_count(c, reg), out)
