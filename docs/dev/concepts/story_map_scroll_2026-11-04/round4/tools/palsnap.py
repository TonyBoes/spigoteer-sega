"""The cell-palette snap (round 3): while some 21 x 19 window needs more than 8 BG palettes, take the palette with the fewest cells in the worst
window, if all of those cells are plain ground, and put each of them back to the ground of the palette that most of its four neighbours have.
Only whole ground cells change (the flat ground tile of the new biome); venues, roads and scenery are never touched.  Reports what it moved."""
from collections import Counter

import pal
import world2 as W

PAL_BIOME = {"grass": "grass", "stadium": "paved", "bistro": "plaza", "igloo": "snow", "factory": "yard", "farm": "farm", "saloon": "desert",
             "zoo": "jungle", "tea": "moss", "town1": None, "cow": "farm", "lodge": "grass"}
CW, CH = W.CW, W.CH
MOVED = set()      # a cell moves once (no ping-pong between two windows)
NEAR = 600              # a cell may only go to a palette whose ground colour is within this (sum of the channel differences) of its own


def _near(q, p):
    a, b = pal.RGB[q][0], pal.RGB[p][0]
    return sum(abs(int(x) - int(y)) for x, y in zip(a, b)) <= NEAR


def window_counts(w, x0, y0):
    return Counter(w.pal[y][x] for y in range(y0, y0 + 19) for x in range(x0, x0 + 21))


def worst_window(w):
    best = (0, None)
    for y0 in range(CH - 18):
        for x0 in range(CW - 20):
            n = len(window_counts(w, x0, y0))
            if n > best[0]:
                best = (n, (x0, y0))
    return best


def snap(w, limit=8, verbose=True):
    moved = []
    for _ in range(400):
        n, at = worst_window(w)
        if n <= limit:
            break
        x0, y0 = at
        cnt = window_counts(w, x0, y0)
        cells = {p: [(x, y) for y in range(y0, y0 + 19) for x in range(x0, x0 + 21) if w.pal[y][x] == p] for p in cnt}
        done = False
        for p in sorted(cnt, key=lambda q: cnt[q]):
            cs = cells[p]
            if any(c in MOVED for c in cs):
                continue
            if p == "town1" or any(w.kind[y][x] != "ground" for (x, y) in cs):
                continue
            for (x, y) in cs:
                nb = Counter(w.ground_pal[y + dy][x + dx] for dy in range(-3, 4) for dx in range(-3, 4)
                             if 0 <= x + dx < CW and 0 <= y + dy < CH and (dx or dy))
                nb.pop(p, None)
                cand = sorted(dict.fromkeys([q for q, _ in nb.most_common() if q in cnt and PAL_BIOME.get(q)] + [q for q in cnt if q != p and PAL_BIOME.get(q) and pal.RGB[q][0] == pal.RGB[p][0]]), key=lambda q: pal.RGB[q][0] != pal.RGB[p][0])
                cand = [q for q in cand if _near(q, p)]
                if not cand:
                    continue
                q = cand[0]
                w.set_tile(x, y, W.GROUND[W.BIOME_TILES[PAL_BIOME[q]]][0], q, "ground")
                w.ground_pal[y][x] = q
                moved.append((x, y, p, q))
                MOVED.add((x, y))
            if moved and moved[-1][2] == p:
                done = True
                break
        if not done:
            if verbose:
                print("stuck at window", at, dict(cnt))
            break
    if verbose:
        print("snap moved", len(moved), "cells; worst window now", worst_window(w))
    return moved




def snap_states(limit=8, max_cells=30, verbose=True):
    """the same snap, judged on every unlock state (the cloud counts: its palettes take slots too): only ground cells of a palette with at most
    max_cells cells in the window move; W.ZONE is made again after each move"""
    moved = []
    for _ in range(300):
        worst = (0, None, None)
        for p in range(0, 10):
            v = W.with_fog(W.WORLD, {"town"} | set(W.ORDER[:p]))
            n, at = worst_window(v)
            if n > worst[0]:
                worst = (n, at, v)
        n, at, v = worst
        if n <= limit:
            break
        x0, y0 = at
        cnt = window_counts(v, x0, y0)
        done = False
        for p in sorted(cnt, key=lambda q: cnt[q]):
            if p.startswith("fog:") or p == "town1" or cnt[p] > max_cells:
                continue
            cs = [(x, y) for y in range(y0, y0 + 19) for x in range(x0, x0 + 21) if v.pal[y][x] == p]
            if any(c in MOVED for c in cs):
                continue
            if any(v.kind[y][x] != "ground" or W.WORLD.kind[y][x] != "ground" for (x, y) in cs):
                continue
            for (x, y) in cs:
                nb = Counter(W.WORLD.ground_pal[y + dy][x + dx] for dy in range(-3, 4) for dx in range(-3, 4)
                             if 0 <= x + dx < CW and 0 <= y + dy < CH and (dx or dy))
                nb.pop(p, None)
                cand = sorted(dict.fromkeys([q for q, _ in nb.most_common() if q in cnt and PAL_BIOME.get(q)] + [q for q in cnt if q != p and PAL_BIOME.get(q) and pal.RGB[q][0] == pal.RGB[p][0]]), key=lambda q: pal.RGB[q][0] != pal.RGB[p][0])
                cand = [q for q in cand if _near(q, p)]
                if cand:
                    q = cand[0]
                    W.WORLD.set_tile(x, y, W.GROUND[W.BIOME_TILES[PAL_BIOME[q]]][0], q, "ground")
                    W.WORLD.ground_pal[y][x] = q
                    moved.append((x, y, p, q))
                    MOVED.add((x, y))
                    done = True
            break
        W.ZONE[:] = [[W.zone_of_cell(W.WORLD, cx, cy) for cx in range(CW)] for cy in range(CH)]
        if not done:
            if verbose:
                print("stuck at", at, dict(cnt))
            break
    if verbose:
        print("state snap moved", len(moved), "cells")
    return moved
