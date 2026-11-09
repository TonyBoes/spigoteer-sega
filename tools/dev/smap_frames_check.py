#!/usr/bin/env python3
"""Per-frame picture check of a story-map walk on Color (PyBoy, double speed as shipped): every frame's background must equal the world drawn by the reference at the camera's position,
so no frame ever shows a wrong-palette (or wrong-tile) pixel.  Sprites (Sal, the arrows, the UFO, the dots) are masked out.

    python3 tools/dev/smap_frames_check.py STOP DIR [STOP DIR ...]      # e.g. 8 0 9 1: the legs zoo -> space (stop 8, up) and space -> zoo (stop 9, down)

Prints per leg: frames, frames that matched, the wrong frames (camera, number of wrong pixels, bounding box).  Exit status 1 if any frame is wrong.  Writes nothing (scratch pictures
of the first wrong frame go to out/frames_check/).  Needs build/game.gb and assets/smap/ (the world): run `make` first.
"""
import json
import re
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "tests"))
SV = 396
V_WALK, V_CAMX, V_CAMY, V_FX, V_FY = 20, 12, 14, 16, 18
DIRS = ("up", "down", "left", "right")


def world_rgb():
    js = json.loads((ROOT / "assets" / "smap" / "world.json").read_text())
    names, rgb, cp = js["pal_names"], js["pal_rgb"], js["cell_pal"]
    px = np.array(Image.open(ROOT / "assets" / "smap" / "world_c.png"))
    h, w = px.shape
    out = np.zeros((h, w, 3), np.uint8)
    for cy in range(h // 8):
        for cx in range(w // 8):
            pal = np.array([[((v[0] >> 3) << 3, (v[1] >> 3) << 3, (v[2] >> 3) << 3) for v in rgb[names[ord(cp[cy][cx]) - 48]]]], np.uint8)[0]
            out[cy * 8:cy * 8 + 8, cx * 8:cx * 8 + 8] = pal[px[cy * 8:cy * 8 + 8, cx * 8:cx * 8 + 8]]
    return out


def var(sc, n):
    return sc[SV + n] | sc[SV + n + 1] << 8


def run(stop, d, world):
    import contextlib
    import test_story_map as sm
    from conftest import double_speed
    with double_speed():
        gb = sm.to_map("cgb", 10, stop=stop)
    cams, wrong, n, ok = [], [], 0, 0
    gb.press(DIRS[d], 6)
    started = False
    prev_oam = []
    for fr in range(1500):
        gb.run(1, True)
        sc = gb.read("story_scratch", 520)
        walking = bool(sc[SV + V_WALK])
        started = started or walking
        if started:
            cams.append((var(sc, V_CAMX), var(sc, V_CAMY)))
            img = np.array(gb.image().convert("RGB"))
            mask = np.zeros((144, 160), bool)                # the sprites (Sal, the arrows, the dots, the UFO): this frame's and the last one's OAM, 8 x 16 and a px more each side
            for o in gb.oam() + prev_oam:
                if 0 < o["y"] < 160 and 0 < o["x"] < 168:
                    mask[max(o["y"] - 17, 0):max(o["y"] - 16 + 17, 0), max(o["x"] - 9, 0):max(o["x"] - 8 + 9, 0)] = True
            prev_oam = gb.oam()
            best = None
            for (cx, cy) in cams[-3:][::-1]:
                ref = world[cy:cy + 144, cx:cx + 160]
                bad = np.any(img != ref, axis=2)
                bad &= ~mask
                nb = int(bad.sum())
                if best is None or nb < best[0]:
                    best = (nb, (cx, cy), bad)
            n += 1
            if best[0] == 0:
                ok += 1
            else:
                ys, xs = np.nonzero(best[2])
                wrong.append((fr, best[1], best[0], (int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max()))))
        if fr > 4 and started and not walking:
            break
    return n, ok, wrong


def main():
    a = sys.argv[1:]
    world = world_rgb()
    bad_any = False
    for i in range(0, len(a), 2):
        stop, d = int(a[i]), int(a[i + 1])
        n, ok, wrong = run(stop, d, world)
        print(f"stop {stop} {DIRS[d]}: {n} frames, {ok} match the reference, {len(wrong)} wrong", wrong[:5])
        bad_any = bad_any or bool(wrong)
    sys.exit(1 if bad_any else 0)


main()
