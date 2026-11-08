"""python3 view2.py TAG: the stadium on the map with the ground = the map's grass: blank cells dropped, palettes STADIUM and PARK with index 0 = the grass ground."""
import mapctx as M
from mapctx import W, PAL

g0 = PAL.RGB["grass"][0]
PAL.RGB["stadium"] = [g0] + PAL.RGB["stadium"][1:]
PAL.RGB["park"] = [g0] + PAL.RGB["park"][1:]
import sys
M.apply(drop_blank=True)
O = str(M.ROOT) + '/out/stad/tmp/'
tag = sys.argv[1]
box = (0, 0, 36, 20)
M.render(W.WORLD, True, box).resize((36 * 24, 20 * 24)).save(O + f'ctx_{tag}_c.png')
M.render(W.WORLD_DMG, False, box).resize((36 * 24, 20 * 24)).save(O + f'ctx_{tag}_d.png')
