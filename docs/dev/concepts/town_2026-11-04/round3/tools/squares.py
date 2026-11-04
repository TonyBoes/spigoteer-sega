"""Read-only: list the isolated 2x2 squares (the lint's rule) with positions.   squares.py IMG.png ..."""
import sys
import numpy as np
from PIL import Image

for f in sys.argv[1:]:
    rgb = np.array(Image.open(f).convert("RGB")).astype(int)
    h, w = rgb.shape[:2]
    hits = []
    for y in range(1, h - 2):
        for x in range(1, w - 2):
            blk = rgb[y:y + 2, x:x + 2].reshape(-1, 3)
            c = blk[0]
            if not (blk == c).all():
                continue
            ring = np.concatenate([rgb[y - 1, x - 1:x + 3], rgb[y + 2, x - 1:x + 3], rgb[y:y + 2, x - 1], rgb[y:y + 2, x + 2]])
            if not (ring == c).all(axis=1).any():
                hits.append((x, y))
    print(f, hits)
