import mapctx as M
from mapctx import W

w = W.WORLD
for cy in (10, 11, 12):
    for cx in (6,):
        print("cell", cx, cy, w.pal[cy][cx], "kind", w.kind[cy][cx])
        for y in range(8):
            print("".join(str(w.px[cy * 8 + y][cx * 8 + x]) for x in range(8)))
# the ground tiles of the grass biome
for cx in (0, 1, 2, 3):
    print("ground", cx, 0, w.pal[0][cx])
    for y in range(8):
        print("".join(str(w.px[y][cx * 8 + x]) for x in range(8)))
print(W.PAL.RGB["town1"], W.PAL.RGB["grass"])
print(sorted(set(w.kind[y][x] for y in range(M.CH) for x in range(M.CW))))
