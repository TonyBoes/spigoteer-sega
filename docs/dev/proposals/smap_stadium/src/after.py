"""python3 after.py TAG: the stadium on the map AFTER my edits (ground = the map's grass: palettes STADIUM and PARK with index 0 = grass, blank cells dropped, walkway to the road)."""
import sys

import edits
import mapctx as M
import park_map
from mapctx import W, PAL

g0 = PAL.RGB["grass"][0]
PAL.RGB["stadium"] = [g0] + PAL.RGB["stadium"][1:]
PAL.RGB["park"] = [g0, PAL.RGB["grass"][1]] + PAL.RGB["park"][2:]      # field grass = the map grass 6aa048 (was 68b048), so PARK and the GRASS palette agree on it
M.apply(piece=park_map, drop_blank=True, edit=lambda W: (edits.edit(W), edits.edit_grass_cells(W)))
if __name__ == "__main__":
    O = str(M.ROOT) + '/out/stad/tmp/'
    tag = sys.argv[1]
    box = (0, 0, 36, 20)
    M.render(W.WORLD, True, box).resize((36 * 24, 20 * 24)).save(O + f'ctx_{tag}_c.png')
    M.render(W.WORLD_DMG, False, box).resize((36 * 24, 20 * 24)).save(O + f'ctx_{tag}_d.png')
