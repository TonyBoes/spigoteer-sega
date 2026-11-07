"""python3 zoom.py MODULE x0 y0 x1 y1 scale: DMG and Color crop (pixels) of MODULE.build() on its biome ground, to out/r3/zoom.png"""
import importlib
import subprocess
import sys

import common as C

m = importlib.import_module(sys.argv[1])
x0, y0, x1, y1, sc = [int(v) for v in sys.argv[2:7]]
c = m.build()
fs = []
for cgb in (False, True):
    im = C.render(c, m.BIOME, m.AT, cgb, margin=0).crop((x0, y0, x1, y1))
    f = f'{C.ROOT}/out/r3/zoom_{int(cgb)}.png'
    im.save(f)
    fs.append(f)
subprocess.run([sys.executable, C.ROOT + '/tools/dev/contact_sheet.py', C.ROOT + '/out/r3/zoom.png', '--scale', str(sc), '--cols', '2', 'DMG=' + fs[0], 'Color=' + fs[1]], check=True)
