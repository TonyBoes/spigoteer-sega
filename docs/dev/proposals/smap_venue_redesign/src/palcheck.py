"""python3 palcheck.py: palettes per 21 x 19 window on the Color map, today against the composite of the picks (Color), and which palettes the worst windows use"""
from collections import Counter

import sheets as S

W = S.W
now = W.WORLD
new = S.composite(False)


def worst(w):
    res = []
    for y0 in range(W.CH - 18):
        for x0 in range(W.CW - 20):
            c = Counter(w.pal[y][x] for y in range(y0, y0 + 19) for x in range(x0, x0 + 21))
            res.append((len(c), (x0, y0), c))
    res.sort(key=lambda r: -r[0])
    return res


for name, w in (('today', now), ('picks', new)):
    r = worst(w)
    print(name, 'worst', r[0][0], 'at', r[0][1], dict(r[0][2]))
    print('   windows over 8:', sum(1 for x in r if x[0] > 8))
