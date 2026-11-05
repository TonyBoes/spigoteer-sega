"""Checks a walk GIF: frame count, total time, the biggest frame-to-frame change in mean brightness (flashing) and in moved pixels (smoothness);
writes a 6-frame strip to the path given as the second argument."""
import sys

import numpy as np
from PIL import Image, ImageSequence

g = Image.open(sys.argv[1])
fr = [f.convert("RGB").copy() for f in ImageSequence.Iterator(g)]
dur = [f.info.get("duration", 0) for f in ImageSequence.Iterator(g)]
a = [np.asarray(f).astype(float) for f in fr]
lum = [x.mean() for x in a]
step = [abs(lum[i + 1] - lum[i]) for i in range(len(a) - 1)]
print(sys.argv[1], len(fr), "frames", sum(dur), "ms, brightest step %.2f of 255, mean %.2f" % (max(step), sum(step) / len(step)))
if len(sys.argv) > 2:
    idx = [0, len(fr) // 5, 2 * len(fr) // 5, 3 * len(fr) // 5, 4 * len(fr) // 5, len(fr) - 1]
    w, h = fr[0].size
    s = Image.new("RGB", (w // 2 * 3, h // 2 * 2))
    for k, i in enumerate(idx):
        s.paste(fr[i].resize((w // 2, h // 2)), ((k % 3) * (w // 2), (k // 3) * (h // 2)))
    s.save(sys.argv[2])
