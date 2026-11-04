"""Read-only: print a picture's 20x13 cell map, each cell numbered by its unique tile (first-seen order); '*' marks a tile
that occurs once. Optional second picture: '+' marks cells whose tile is not in the other picture.   tilemap.py A.txt [B.txt]"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from render_v2 import parse


def tiles(path):
    key, pix = parse(path)
    out = {}
    for ty in range(13):
        for tx in range(20):
            out[(tx, ty)] = tuple(tuple(key[pix[y][x]] for x in range(tx * 8, tx * 8 + 8)) for y in range(ty * 8, ty * 8 + 8))
    return out


a = tiles(sys.argv[1])
b = set(tiles(sys.argv[2]).values()) if len(sys.argv) > 2 else None
from collections import Counter
cnt = Counter(a.values())
print("unique", len(cnt), "singletons", sum(1 for v in cnt.values() if v == 1))
for ty in range(13):
    line = []
    for tx in range(20):
        t = a[(tx, ty)]
        mark = "+" if b is not None and t not in b else ("*" if cnt[t] == 1 else ".")
        line.append(mark)
    print(f"{ty:2d} " + "".join(line))
