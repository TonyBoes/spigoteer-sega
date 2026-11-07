"""MOUNTAIN RANGE ACCESSORY PIECES (round 2): small peaks, a ridge, a foothill and a rock, to stand beside the big mountain and around the igloo.
One drawing serves both biomes: the DESERT set (palette SALOON: 0 sand, 1 lit rock, 2 shaded rock, 3 ink) and the SNOWY set (palette IGLOO: 0 snow, 1 pale ice-blue rock,
2 deep blue shade, 3 ink) share every skyline, face, cap and tile: the same DMG tiles, only the Color palette differs (the cap is the lightest value: snow on the snowy set, a sun-bleached crest on the desert set).
Each piece stands on its bottom row (the foot).  Light from the top left.  Skylines, creases and caps are typed run by run (mtn_kit / mtn_massif); the rock is typed rows."""
import mtn_kit as M
import mtn_massif as MM
from canvas import Canvas

NAMES = ["foothill", "peak_s", "peak_m", "ridge", "spur", "rock"]
FOOT = "33333323"
ROCK = ["________", "__3333__", "_311113_", "31111123", "31111223", "33222233", "_3333333", "________"]


def foothill(snow, pal):
    c = Canvas("foothill", pal, 16, 8)
    M.peak(c, 7, (0, 8, [(2, -1), (1, 0), (2, -1), (1, -1), (1, -1)]), (7, 2), [(1, 0), (2, 1), (1, 0), (2, 1), (2, 2)], (7, [(8, 0)]), rim_rows=3, foot_ink=FOOT,
           cap=((5, 3, [(2, 1), (2, 0)])))
    return c


def peak_s(snow, pal):
    c = Canvas("peak_s", pal, 16, 16)
    M.peak(c, 15, (0, 16, [(1, -1), (2, -2), (1, 0), (2, -3), (1, -1)]), (7, 3), [(1, 0), (2, 2), (1, 0), (2, 3), (2, 3)], (7, [(4, [0, 1]), (16, 0)]), rim_rows=6, foot_ink=FOOT,
           ink_crease_rows=4, cap=((4, 6, [(2, 1), (2, -1), (2, 1), (2, 0)])))
    for (x, y, v) in [(8, 3, "0"), (10, 8, "2"), (2, 11, "0")]:           # corner pixels of L-shaped doubles (lint), typed by hand
        c.px[y][x] = v
    return c


def peak_m(snow, pal):
    c = Canvas("peak_m", pal, 24, 24)
    M.peak(c, 23, (0, 24, [(1, -1), (2, -2), (1, 0), (2, -2), (1, -1), (2, -3), (1, -2), (1, -1)]), (11, 4), [(1, 0), (2, 2), (2, 1), (2, 3), (2, 0), (2, 2), (1, 3)],
           (11, [(6, [0, 1]), (20, 0)]), rim_rows=10, foot_ink=FOOT, ink_crease_rows=8,
           cap=((6, 10, [(2, 1), (2, -1), (2, 1), (2, -1), (2, 1), (2, 0), (2, -1)])))
    for (x, y, v) in [(12, 4, "0"), (2, 19, "0")]:
        c.px[y][x] = v
    return c


def ridge(snow, pal):
    c = Canvas("ridge", pal, 32, 16)
    MM.massif(c, 15, 0, 16, [(2, -1), (1, 0), (2, -2), (1, -1), (2, -2), (1, -1, "a"), (2, 1), (1, 0), (2, 1), (2, 1), (1, 1, "v"), (2, -1), (1, 0), (1, -2), (2, -1), (1, -1),
                              (1, -1, "b"), (1, 0), (2, 2), (1, 0), (1, 3), (2, 3)],
              [dict(x="a", saddle="v", crease=[(10, 0)], rim=4, cap=("a", -3, 7, [(2, 1), (2, -1), (2, 1), (1, 0)])),
               dict(x="b", crease=[(10, 0)], rim=4, cap=("b", -3, 6, [(2, 1), (2, -1), (2, 0)]))], verbose=False)
    return c


def spur(snow, pal):
    c = Canvas("spur", pal, 16, 16)
    M.peak(c, 15, (0, 16, [(1, -1), (1, -3), (1, -4), (1, -3), (1, -1)]), (5, 3), [(2, 1), (1, 0), (2, 1), (2, 2), (1, 0), (2, 2), (2, 2)], (5, [(4, [0, 1]), (16, 0)]),
           rim_rows=4, foot_ink=FOOT, ink_crease_rows=3, cap=((3, 7, [(2, 1), (2, 0)])))
    for (x, y, v) in [(13, 11, "0")]:
        c.px[y][x] = v
    return c


def rock(snow, pal):
    c = Canvas("rock", pal, 8, 8)
    for y, r in enumerate(ROCK):
        for x, ch in enumerate(r):
            c.px[y][x] = "0" if ch == "_" else ch
    return c


def pieces(snow):
    pal = "igloo" if snow else "saloon"
    return {"foothill": foothill(snow, pal), "peak_s": peak_s(snow, pal), "peak_m": peak_m(snow, pal), "ridge": ridge(snow, pal), "spur": spur(snow, pal), "rock": rock(snow, pal)}


def kit_canvas(snow):
    """all five on one canvas, bottoms aligned, a cell between them: 152 x 24"""
    ps = pieces(snow)
    c = Canvas("kit", "igloo" if snow else "saloon", 152, 24)
    x = 0
    for n in NAMES:
        p = ps[n]
        for y in range(p.h):
            for xx in range(p.w):
                c.px[24 - p.h + y][x + xx] = p.px[y][xx]
        x += p.w + 8
    return c


BIOME, AT = 'desert', (1, 34)
REGION = None


def build():
    return kit_canvas(False)
