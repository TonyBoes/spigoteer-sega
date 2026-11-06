"""python3 palcheck2.py: the palette cost of each piece on its own (only that piece swapped into the Color map), worst 21 x 19 window and windows over 8"""
from collections import Counter

import importlib
import sheets as S

W = S.W


def stats(w):
    worst, over = (0, None), 0
    for y0 in range(W.CH - 18):
        for x0 in range(W.CW - 20):
            n = len(Counter(w.pal[y][x] for y in range(y0, y0 + 19) for x in range(x0, x0 + 21)))
            if n > worst[0]:
                worst = (n, (x0, y0))
            over += n > 8
    return worst, over


print('today', stats(W.WORLD))
full = dict(S.PICK)
for key, names in S.PIECES.items():
    for n in names:
        for unmerge in ((False, True) if key == 'zoo' else (None,)):
            S.PICK.clear()
            S.PICK[key] = n
            m = importlib.import_module(n)
            if unmerge is not None:
                m.UNMERGE = unmerge
            w = S.composite(False)
            print(n, 'unmerge' if unmerge else '', stats(w))
