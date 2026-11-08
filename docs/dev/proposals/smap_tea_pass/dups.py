"""python3 -I dups.py (env as count.py; TEA_COLOR=1 for the Color data set): for every cell of the teahouse box, how many cells of the whole map hold the same 8x8 pixels (1 = its own tile)."""
import os
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import swap  # noqa: E402,F401
sys.path.insert(0, str(HERE.parent / "smap_import"))
import mapctx as M  # noqa: E402

g, _ = M.grid(os.environ.get("TEA_COLOR") != "1")
T = lambda cx, cy: tuple(tuple(g[cy * 8 + j][cx * 8:cx * 8 + 8]) for j in range(8))
cnt = Counter(T(x, y) for y in range(M.CH) for x in range(M.CW))
print("distinct whole map", len(cnt))
for cy in range(55, 62):
    print(" ".join("%4d" % cnt[T(cx, cy)] for cx in range(24, 36)))
