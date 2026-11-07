import mapctx as M
from mapctx import W

w = W.WORLD
print(type(w.biome[0][0]), w.biome[2][2], w.biome[0][0], w.biome[10][8])
for y in range(0, 14):
    print(y, "".join(str(w.biome[y][x])[0] for x in range(0, 26)), " ".join(w.pal[y][x][:3] for x in range(0, 14)))
print(sorted(w.roads)[:5] if hasattr(w, 'roads') else None)
print([(k, v) for k, v in w.venue_rect.items()][:3])
