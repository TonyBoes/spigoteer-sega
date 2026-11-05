"""Round 5 working view: the tile-id map of a venue in the DMG world (same letter = same tile).  python3 idmap.py venue"""
import sys

import stats2 as S
import world2 as W

w = W.WORLD_DMG
sg = S.sig_grid(w)
x0, y0, x1, y1 = w.venue_rect[sys.argv[1]]
ids = {}
sym = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
for cy in range(y0, y1 + 1):
    print("".join(sym[ids.setdefault(sg[cy][cx], len(ids)) % len(sym)] for cx in range(x0, x1 + 1)))
print(len(ids), "distinct")
