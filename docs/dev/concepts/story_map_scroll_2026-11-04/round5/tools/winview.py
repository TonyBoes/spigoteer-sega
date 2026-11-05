"""Round 5 working view: one 21 x 19 window of the DMG world at x4; a cell is boxed red when its tile occurs once in the window, orange twice.
python3 winview.py OUT.png X0 Y0"""
import sys
from collections import Counter

from PIL import Image, ImageDraw

import pal
import stats2 as S
import world2 as W

x0, y0 = int(sys.argv[2]), int(sys.argv[3])
K = 5
sg = S.sig_grid(W.WORLD_DMG)
cnt = Counter(sg[y][x] for y in range(y0, y0 + 19) for x in range(x0, x0 + 21))
im = Image.new("RGB", (21 * 8 * K, 19 * 8 * K))
d = ImageDraw.Draw(im)
for cy in range(19):
    for cx in range(21):
        t = sg[y0 + cy][x0 + cx]
        for j in range(8):
            for i in range(8):
                v = pal.DMG_SHADE[t[j][i]]
                d.rectangle([(cx * 8 + i) * K, (cy * 8 + j) * K, (cx * 8 + i + 1) * K - 1, (cy * 8 + j + 1) * K - 1], fill=(v, v, v))
        if cnt[t] <= 2:
            d.rectangle([cx * 8 * K, cy * 8 * K, (cx * 8 + 8) * K - 1, (cy * 8 + 8) * K - 1], outline=(230, 40, 40) if cnt[t] == 1 else (240, 150, 30))
print("distinct", len(cnt), "once", sum(1 for v in cnt.values() if v == 1), "twice", sum(1 for v in cnt.values() if v == 2))
im.save(sys.argv[1])
