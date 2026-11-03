import sys, subprocess
sys.path.insert(0, "out/spotlight")
import numpy as np
from PIL import Image
import mock

OUT = "out/spotlight"
VEN = ["saloon", "bistro", "space"]
STILL = 30                      # frame index of the stills (the third beat)
bad = {}
for v in VEN:
    d = np.load(f"{OUT}/cap_{v}.npz")
    plate, frames = d["plate"], d["frames"]
    perf = mock.performers(frames[20:], plate)
    print(v, "performer tile columns", perf)
    for name, fn in mock.LOOKS:
        imgs = []
        for i, f in enumerate(frames):
            r = fn(f, plate, i // mock.BEAT, perf)
            imgs.append(r)
            if i == STILL:
                Image.fromarray(r).save(f"{OUT}/{v}_{name}.png")
                # the 4-colour check on the BG pixels of every stage cell
                bg = (f == plate).all(-1)
                n = 0
                for cy in range(1, 5):
                    for cx in range(20):
                        ys, xs = slice(cy * 8, cy * 8 + 8), slice(cx * 8, cx * 8 + 8)
                        m = bg[ys, xs]
                        if len({tuple(p) for p in r[ys, xs][m]}) > 4:
                            n += 1
                bad[(v, name)] = n
        # GIF: x3, one frame per game frame pair (30 fps)
        pil = [Image.fromarray(x).resize((480, 432), Image.NEAREST) for x in imgs[::2]]
        pil[0].save(f"{OUT}/{v}_{name}.gif", save_all=True, append_images=pil[1:], duration=33, loop=0, optimize=False)
print("cells over 4 colours:", {k: x for k, x in bad.items() if x})
