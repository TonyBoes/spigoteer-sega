"""Round 2 outputs (previews only): python3 build2.py [maps|views|walk|all].  Writes into round2/."""
import sys

from PIL import Image

import render2 as R
import world2 as W

OUT = R.OUT
EARLY = R.EARLY_OPEN
PEEK_EARLY = ("lodge",)


def maps():
    for st in ("early", "late"):
        for mode in ("cgb", "dmg"):
            R.scale(R.img(st, mode), 2).save(OUT / f"map_{st}_{mode}_x2.png")


def view(name, state, stop, here, bias=(0, 0), direction="D"):
    rev = EARLY if state == "early" else None
    peek = PEEK_EARLY if state == "early" else ()
    cam = R.view_cam(stop, bias)
    ims = []
    for mode in ("cgb", "dmg"):
        ims.append(R.scale(R.frame(state, mode, cam, feet=W.STOPS[here], direction=direction, here=here, revealed=rev, peek=peek, tick=0), 3))
    R.stack(*ims).save(OUT / f"view_{name}_x3.png")


def views():
    view("town_early", "early", "town", "town")
    view("saloon_desert", "early", "saloon", "saloon", direction="L")
    view("igloo_edge", "late", "igloo", "igloo", bias=(-20, 0), direction="R")
    view("space_corner", "late", "space", "space", direction="L")
    view("cow_east", "late", "cow", "cow", bias=(30, 0), direction="R")


def walk(a="stadium", b="saloon", state="early"):
    pts = W.leg_points(a, b)
    rev = EARLY
    # phases: 0.5 s still, the walk, then 1.3 s standing with the name tag
    seq = [(pts[0], "D", "stand", False)] * 30
    cyc = ["step1", "stand", "step2", "stand"]
    prev = pts[0]
    for i, p in enumerate(pts[1:]):
        d = "R" if p[0] > prev[0] else "L" if p[0] < prev[0] else "D" if p[1] > prev[1] else "U"
        seq.append((p, d, cyc[(i // 2) % 4], False))
        prev = p
    last = seq[-1]
    seq += [(last[0], last[1], "stand", i > 10) for i in range(90)]
    frames = {"cgb": [], "dmg": []}
    cam = list(R.view_cam(a))
    for n, (p, d, ph, tag) in enumerate(seq):
        tgt = R.clampcam(p[0] - 80, p[1] - 12 - 72)
        for k in (0, 1):
            gap = tgt[k] - cam[k]
            step = max(1, min(4, abs(gap) >> 2)) if gap else 0
            cam[k] += step if gap > 0 else -step
        if n % 2:
            continue
        for mode in ("cgb", "dmg"):
            here = b if n >= len(seq) - 90 else None
            im = R.frame(state, mode, tuple(cam), feet=p, direction=d, phase=ph, here=here, tick=n, text=R.TAG[b] if tag else None, text_y=0,
                         revealed=rev, peek=PEEK_EARLY, arrows=here is not None)
            frames[mode].append(R.scale(im, 3))
    for mode in ("cgb", "dmg"):
        fr = frames[mode]
        fr[0].save(OUT / f"walk_{mode}.gif", save_all=True, append_images=fr[1:], duration=33, loop=0, optimize=False)
    print("walk frames", len(frames["cgb"]), "game frames", len(seq))


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else "all"
    if what in ("maps", "all"):
        maps()
    if what in ("views", "all"):
        views()
    if what in ("walk", "all"):
        walk()
