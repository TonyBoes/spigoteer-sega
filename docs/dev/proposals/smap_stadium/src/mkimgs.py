"""python3 mkimgs.py before|after: writes out/stad/tmp/map_{mode}_{crop|whole}_{d|c}.png.  before = the approved stadium pasted at its A5 slot exactly as the animation import does (all cells,
STADIUM and PARK as approved); after = my ground, edge and connection edits (after.py)."""
import sys

mode = sys.argv[1]
if mode == "after":
    import after  # noqa: F401
    import mapctx as M
else:
    import mapctx as M
    M.apply()
from mapctx import W

O = str(M.ROOT) + '/out/stad/tmp/'
crop = (0, 0, 34, 16)
for cgb, t in ((False, 'd'), (True, 'c')):
    w = W.WORLD if cgb else W.WORLD_DMG
    M.render(w, cgb, crop).save(O + f'map_{mode}_crop_{t}.png')
    if cgb:
        M.render(w, True).save(O + f'map_{mode}_whole_c.png')
