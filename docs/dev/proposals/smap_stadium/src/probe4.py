import after  # noqa
from mapctx import W
from collections import Counter
for cx, cy in ((11,5),(11,6),(12,6),(11,7),(12,7)):
    print((cx,cy), W.WORLD.pal[cy][cx], Counter(W.WORLD.px[cy*8+y][cx*8+x] for y in range(8) for x in range(8)))
