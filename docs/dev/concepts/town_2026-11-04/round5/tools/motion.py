#!/usr/bin/env python3
"""Motion mockups for round 4 (preview only: the engine is not changed). Builds GIFs of the town pictures with
  - the fountain water flowing: BG tile frames, 4 phases, one step every 8 game frames. The highlight pixels of each
    phase are HAND-LISTED below (WATER); the script only turns the jets' other W pixels to b and stamps the list;
  - the clouds drifting (Color only): the BG cloud cells swapped to plain sky, the hand-drawn clouds of master.py as
    OBJ sprites one pixel right every 8 game frames, behind the Golden Spigot (mask sprites = the spigot's own pixels,
    lower OAM index, so CGB draws them over the clouds).
    motion.py PICS_DIR OUT_DIR
writes OUT_DIR/<name>.gif (x3, 32 steps = 256 game frames = 4.3 s, 133 ms a step) and prints the flicker check."""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PIL import Image
from render_v2 import parse, render
import master as M

STEPS, MS, SCALE = 32, 133, 3

# ---- the jets: per picture, the jet pixel pairs (y, x_left, x_right) the flow runs over (all b or W in the art) ----
JET_L = [(y, 85, 86) for y in (50, 51)] + [(y, 84, 85) for y in range(52, 58)] + \
        [(y, 83, 84) for y in range(58, 67)] + [(y, 82, 83) for y in (67, 68)]
JET_R = [(y, 121, 122) for y in (50, 51)] + [(y, 122, 123) for y in range(52, 58)] + \
        [(y, 123, 124) for y in range(58, 67)] + [(y, 124, 125) for y in (67, 68)]
JET_R_GLASS = [j for j in JET_R if j[0] <= 58]          # FINALE: the jet runs into the Spigoteer's glass at y 59

# ---- the hand-placed highlights (W) of each phase; phase 0 is the art as drawn. The left jet's light is on its left
# pixel, the right jet's on its right pixel (as drawn); each phase moves every highlight one row down the jet ----
L = [[(85, 50), (84, 54), (83, 58), (83, 62), (83, 66)],
     [(85, 51), (84, 55), (83, 59), (83, 63), (82, 67)],
     [(84, 52), (84, 56), (83, 60), (83, 64), (82, 68)],
     [(84, 53), (84, 57), (83, 61), (83, 65)]]
R = [[(122, 50), (123, 54), (124, 58), (124, 62), (123, 66), (124, 66)],
     [(122, 51), (123, 55), (124, 59), (124, 63), (125, 67)],
     [(123, 52), (123, 56), (124, 60), (124, 64), (125, 68)],
     [(123, 53), (123, 57), (124, 61), (124, 65)]]
R_GLASS = [[(122, 50), (123, 54), (124, 58)],
           [(122, 51), (123, 55)],
           [(123, 52), (123, 56)],
           [(123, 53), (123, 57)]]
WATER = {"intro_before": [(JET_L, L), (JET_R, R)],
         "finale_a": [(JET_L, L), (JET_R_GLASS, R_GLASS)],
         "credits_b": [(JET_L, L), (JET_R, R)]}

# ---- the sky: (piece, x, y, key) OBJ clouds and the mask rectangle (x0, y0, x1, y1) of the spigot's pixels ----
SKY = {"finale_a": ([("CLOUD_A", 40, 16, "o"), ("CLOUD_B", 128, 18, "o"), ("CLOUD_C", 3, 20, "o")], (95, 16, 118, 23)),
       "credits_b": ([("STRIP_A", 50, 14, "O"), ("STRIP_B", 124, 22, "O")], (95, 14, 118, 23))}
SKY_START = 24      # the mockup starts 24 steps into the drift so the GIF shows a cloud passing behind the spigot


def water(pix, name, ph):
    g = [list(r) for r in pix]
    for jet, phases in WATER.get(name, []):
        cells = {(x, y) for (y, a, b) in jet for x in (a, b)}
        for (x, y) in cells:
            assert g[y][x] in "bW", (name, x, y, g[y][x])
            g[y][x] = "b"
        for (x, y) in phases[ph]:
            assert (x, y) in cells, (name, x, y)
            g[y][x] = "W"
    return g


def sky(g, name, step, cgb):
    if not cgb or name not in SKY:
        return g
    clouds, (mx0, my0, mx1, my1) = SKY[name]
    keys = {k for (_, _, _, k) in clouds}
    for y in range(0, 32):                                    # the BG cloud cells -> the plain sky tile (CGB only)
        for x in range(160):
            if g[y][x] in keys:
                g[y][x] = "."
    base = [r[:] for r in g]
    for piece, x0, y0, k in clouds:
        rows = getattr(M, piece).split("\n")
        ox = ((x0 + 8 + SKY_START + step) & 255) - 8          # OAM x wraps at 256: 88 steps off screen, no jump
        for dy, r in enumerate(rows):
            for dx, c in enumerate(r):
                x, y = ox + dx, y0 + dy
                if c != k or not 0 <= x < 160:
                    continue
                if mx0 <= x <= mx1 and my0 <= y <= my1 and base[y][x] != ".":
                    continue                                  # the mask sprite (the spigot's own pixel) is in front
                g[y][x] = k
    return g


def frames(path, name, cgb):
    key, pix = parse(path)
    out = []
    for s in range(STEPS):
        g = sky(water(pix, name, s % 4), name, s, cgb)
        out.append(["".join(r) for r in g])
    return key, out


def flicker(fr):
    """per pixel: the number of changes over the loop, and the shortest run of one value (1 = a pixel that shows a
    colour for a single step); a 2-step on/off toggle all over a region would be strobing"""
    ch, short = 0, 99
    h, w = len(fr[0]), len(fr[0][0])
    for y in range(h):
        for x in range(w):
            seq = [f[y][x] for f in fr]
            n = sum(seq[i] != seq[i - 1] for i in range(len(seq)))
            ch = max(ch, n)
    changed = sum(1 for f0, f1 in zip(fr, fr[1:] + fr[:1]) for r0, r1 in zip(f0, f1) for a, b in zip(r0, r1) if a != b)
    return ch, changed / len(fr)


def dump(src, out):
    """water phases 1-3 as picture sources (OUT/phaseN/<name>.txt) for lint_all.py: the tiles the engine would swap in"""
    for ph in (1, 2, 3):
        d = os.path.join(out, f"phase{ph}")
        os.makedirs(d, exist_ok=True)
        for name in ("intro_before", "intro_a", "finale_a", "credits_b"):
            text = open(os.path.join(src, name + ".txt")).read().split("\n")
            i = next(n for n, ln in enumerate(text) if ln.startswith("@pixels"))
            key, pix = parse(os.path.join(src, name + ".txt"))
            g = ["".join(r) for r in water(pix, name, ph)]
            open(os.path.join(d, name + ".txt"), "w").write("\n".join(text[:i + 1] + g) + "\n")


def main():
    src, out = sys.argv[1], sys.argv[2]
    if len(sys.argv) > 3 and sys.argv[3] == "--dump":
        return dump(src, out)
    os.makedirs(out, exist_ok=True)
    for name, label in (("finale_a", "day"), ("intro_before", "night"), ("credits_b", "dawn")):
        for cgb in (True, False):
            if name == "credits_b" and not cgb:
                continue
            key, fr = frames(os.path.join(src, name + ".txt"), name, cgb)
            ims = [render(key, f, SCALE, dmg=not cgb).convert("P", palette=Image.ADAPTIVE, colors=16) for f in fr]
            fn = os.path.join(out, f"{label}_{'color' if cgb else 'dmg'}.gif")
            ims[0].save(fn, save_all=True, append_images=ims[1:], duration=MS, loop=0, optimize=True, disposal=1)
            mx, avg = flicker(fr)
            print(f"{fn}: {len(fr)} steps, {os.path.getsize(fn) // 1024} KB, most changes of one pixel {mx}, "
                  f"pixels changed per step {avg:.1f}")


if __name__ == "__main__":
    main()
