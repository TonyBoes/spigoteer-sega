"""Shared helpers for the Boss Rush portrait proposals (reads build/boss_<name>_art.h; writes nothing under assets/).

Only parsing, compositing the game's own pixels (body pose 0 + the topper sprite's STILL frame, exactly as src/boss.c draws them), centring by a
whole-pixel shift, tile packing and previews live here. No pixel is invented here; hand-drawn reductions are in options_b.txt (the artist's grids).
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "tools"))
import gen_rush_portraits as g   # noqa: E402

BOSSES = g.BOSSES
HAT_DX = dict(big_tex=16, mascot=8, sasquatch=12, critic=9, yeti=9, prototype=8, duke=16, sumo=16, leo=6, mothership=12)   # src/boss.c rows[].hat_dx
NAMES = dict(big_tex="BIG TEX", mascot="MASCOT", sasquatch="SASQUATCH", critic="CRITIC", yeti="YETI", prototype="PROTOTYPE", duke="DUKE",
             sumo="SUMO", leo="LEO", mothership="MOTHERSHIP")
DMG = [(224, 248, 208), (136, 192, 112), (52, 104, 86), (8, 24, 32)]     # the project's DMG greens


def hat_pixels(build, name):
    """The topper's STILL frame: 8 x 16 pixel indices (an 8x16 OBJ, top tile then bottom tile)."""
    t = (build / f"boss_{name}_art.h").read_text()
    d = [int(x, 16) for x in re.search(r"boss_art_hat\[\d+\] = \{([^}]*)\}", t).group(1).split(",")]
    rows = [[0] * 8 for _ in range(16)]
    for tl in range(2):
        for y in range(8):
            lo, hi = d[tl * 16 + 2 * y], d[tl * 16 + 2 * y + 1]
            for x in range(8):
                rows[tl * 8 + y][x] = ((lo >> (7 - x)) & 1) | (((hi >> (7 - x)) & 1) << 1)
    return rows


def full_boss(build, name):
    """The whole boss as the fight shows him (WALK pose): 24 rows (8 for the topper's upper half, 16 for the body), the body's width.
    Topper drawn over the body (transparent index 0 shows the body). Returns rows, colours (RGB15 x3)."""
    body, pal = g.body_pixels(build, name)
    hat = hat_pixels(build, name)
    w = len(body[0])
    rows = [[0] * w for _ in range(24)]
    for y in range(16):
        rows[8 + y] = list(body[y])
    for y in range(16):
        for x in range(8):
            if hat[y][x]:
                rows[y][HAT_DX[name] + x] = hat[y][x]
    return rows, pal


def bbox(rows):
    ys = [y for y, r in enumerate(rows) if any(r)]
    xs = [x for r in rows for x, v in enumerate(r) if v]
    return min(xs), max(xs), ys[0], ys[-1]


def rgb15(c):
    return (((c & 31) << 3) | ((c & 31) >> 2), (((c >> 5) & 31) << 3) | (((c >> 5) & 31) >> 2), (((c >> 10) & 31) << 3) | (((c >> 10) & 31) >> 2))


def tile_of(rows, tx, ty):
    return tuple(tuple(rows[8 * ty + y][8 * tx + x] for x in range(8)) for y in range(8))


def tile_bytes(t):
    out = []
    for r in t:
        lo = hi = 0
        for v in r:
            lo, hi = (lo << 1) | (v & 1), (hi << 1) | (v >> 1)
        out += [lo, hi]
    return out
