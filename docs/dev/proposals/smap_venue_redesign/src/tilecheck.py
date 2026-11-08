"""python3 tilecheck.py: the DMG tiles in the worst 21 x 19 window (the generator's own limit, POOL 176) and in the whole map, today against the picks on their own
and all together.  Read-only; the generator's real build is not run (it would need the layout changed)."""
import importlib

import sheets as S

W = S.W
POOL = 176


def sigs(w):
    return [[tuple("".join(str(w.px[cy * 8 + j][cx * 8 + i]) for i in range(8)) for j in range(8)) for cx in range(W.CW)] for cy in range(W.CH)]


def stats(w):
    s = sigs(w)
    worst = (0, None)
    for y0 in range(W.CH - 18):
        for x0 in range(W.CW - 20):
            n = len({s[y][x] for y in range(y0, y0 + 19) for x in range(x0, x0 + 21)})
            if n > worst[0]:
                worst = (n, (x0, y0))
    return len({t for r in s for t in r}), worst


print('today  whole map, worst 21x19 window:', stats(W.WORLD_DMG))
for key, names in S.PIECES.items():
    for n in names:
        S.PICK.clear()
        S.PICK[key] = n
        print(f'{n:11s}', stats(S.composite(True)))
S.PICK.clear()
S.PICK.update({'igloo': 'igloo_1', 'cow': 'cow_2', 'zoo': 'zoo_1', 'mountain': 'mountain_2'})
print('all four picks', stats(S.composite(True)))
S.PICK.update({'igloo': 'igloo_2', 'cow': 'cow_1', 'zoo': 'zoo_2', 'mountain': 'mountain_1'})
print('the other four', stats(S.composite(True)))
