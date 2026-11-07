"""python3 sheet3.py: final 2 | wavy static (DMG above, Color below, x3), an x6 close-up of the three flag frames, the GIF (8 fps, 3 frames), and the tile counts."""
import subprocess
import sys

from PIL import Image

import common as C
import park_s2 as N
import park_s2_f2 as O

OUT = C.ROOT + '/docs/dev/proposals/smap_stadium'
TMP = C.ROOT + '/out/stad/tmp'
C.cgb_unmerge = True
items, close, gif = [], [], {False: [], True: []}
for cgb in (False, True):
    t = 'Color' if cgb else 'DMG'
    for lab, m in (('FINAL 2 (flat flag)', O), ('WAVY STATIC', N)):
        f = f'{TMP}/w_{m.__name__}_{t}.png'
        C.render(m.build(), m.BIOME, m.AT, cgb).save(f)
        items.append((f'{lab} {t}', f))
    for fr in range(3):
        im = C.render(N.build(frame=fr), N.BIOME, N.AT, cgb)
        crop = im.crop((32, 0, 88, 24))          # the flag and the arch top (render has a 1 cell margin)
        g = f'{TMP}/wf_{t}_{fr}.png'
        crop.save(g)
        close.append((f'{t} frame {fr}', g))
        gif[cgb].append(im.crop((8, 0, 112, 56)).resize((104 * 4, 56 * 4), Image.NEAREST))
subprocess.run([sys.executable, C.ROOT + '/tools/dev/contact_sheet.py', OUT + '/stadium_wavy_sheet.png', '--scale', '3', '--cols', '2', '--title', 'stadium final 2 | wavy static flag (DMG above, Color below)'] + [f'{l}={p}' for l, p in items], check=True)
subprocess.run([sys.executable, C.ROOT + '/tools/dev/contact_sheet.py', OUT + '/stadium_wavy_frames_x6.png', '--scale', '6', '--cols', '3', '--title', 'flag frames 0 1 2, x6 (DMG above, Color below)'] + [f'{l}={p}' for l, p in close], check=True)
for cgb, name in ((False, 'DMG'), (True, 'Color')):
    fr = gif[cgb]
    fr[0].save(f'{OUT}/stadium_flag_wave_{name}.gif', save_all=True, append_images=fr[1:], duration=125, loop=0)
print('tiles final2', C.tile_count(O.build()), 'wavy static', C.tile_count(N.build()), 'frames', [C.tile_count(N.build(frame=f)) for f in range(3)])
cs = [C.cells(N.build(frame=f)) for f in range(3)]
for cell in ((5, 0), (6, 0), (7, 0)):
    print('cell', cell, 'distinct across frames:', len({cs[f][cell][0] for f in range(3)}))
