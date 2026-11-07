"""scratch: zoom on the plane (preview only)"""
import sys

import mtn_h as M
import common as C
from PIL import Image

combos = [('A', '2', False), ('B', '2', False)]
out = []
for plane, tone, cgb in combos:
    out.append(C.render(M.build('h2e', True, plane, tone, True), M.BIOME, M.AT, cgb).crop((8 + 4, 8 + 52, 8 + 40, 8 + 72)))
w = Image.new('RGB', (out[0].width * 2 + 10, (out[0].height + 10) * 2), (40, 40, 40))
for k, im in enumerate(out):
    w.paste(im, ((k % 2) * (im.width + 10), (k // 2) * (im.height + 10)))
w.resize((w.width * 14, w.height * 14), Image.NEAREST).save(C.ROOT + '/out/hangar/zq.png')
