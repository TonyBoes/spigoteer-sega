"""Shared model for the smap_dmg_kit2 proposal: today's DMG map (assets/smap/world_d.png through the build's own Model), tile counts, windows,
scroll-step numbers, and the merge machinery.  Read-only: nothing under assets/, src/ or tests/golden/ is written.
Run scripts from the repo root:  python3 docs/dev/proposals/smap_dmg_kit2/<script>.py"""
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "tools" / "artifacts" / "map_atlas"))
import static as S  # noqa: E402
import gen_smap_world as G  # noqa: E402

CW, CH = G.CW, G.CH
OUT = Path(__file__).resolve().parent
_st = None


def static():
    global _st
    if _st is None:
        _st = S.Static()
    return _st


def model():
    """the DMG Model: ids = distinct 8x8 blocks over all unlock states (animated groups' cells get ids of their own)"""
    return static().dm


def sig_array(dm):
    return np.array([list(s) for s in dm.sigs], dtype=np.int8)           # (ids, 64) shade 0..3


def pinned_ids(dm):
    """ids that an animation rewrites: nothing merges into or out of them"""
    return {i for k, i in dm.ids.items() if isinstance(k, tuple)}


def piece_grid():
    """(CH, CW) of area names from the Atlas piece map: venue names, 'Roads', 'Land: ...'"""
    st = static()
    return [[st.piece_names[int(st.piece[y, x])] for x in range(CW)] for y in range(CH)]


def window_stats(g, ww, wh):
    best, at = 0, None
    for y0 in range(CH - wh + 1):
        for x0 in range(CW - ww + 1):
            n = len(np.unique(g[y0:y0 + wh, x0:x0 + ww]))
            if n > best:
                best, at = n, (x0, y0)
    return best, at


def step_stats(g, ww=22, wh=20):
    """new tile ids brought in by one column / row step (both directions) of a 22x20 window (the loaded region), as the 11-06 count_tiles.py"""
    cnt = []
    for y0 in range(CH - wh + 1):
        for x0 in range(CW - ww):
            win = set(np.unique(g[y0:y0 + wh, x0:x0 + ww]))
            cnt.append(len(set(np.unique(g[y0:y0 + wh, x0 + ww])) - win))
            win2 = set(np.unique(g[y0:y0 + wh, x0 + 1:x0 + ww + 1]))
            cnt.append(len(set(np.unique(g[y0:y0 + wh, x0])) - win2))
    for y0 in range(CH - wh):
        for x0 in range(CW - ww + 1):
            win = set(np.unique(g[y0:y0 + wh, x0:x0 + ww]))
            cnt.append(len(set(np.unique(g[y0 + wh, x0:x0 + ww])) - win))
            win2 = set(np.unique(g[y0 + 1:y0 + wh + 1, x0:x0 + ww]))
            cnt.append(len(set(np.unique(g[y0, x0:x0 + ww])) - win2))
    c = np.array(cnt)
    return dict(mean=float(c.mean()), p95=float(np.percentile(c, 95)), max=int(c.max()), n=len(c))


def metrics(grids, steps=True):
    """grids: {state: (CH, CW) ids}.  Unique and used-once on the finished map (state 11, no fog); worst windows over every state."""
    g = grids[G.NSTATE]
    c = np.bincount(g.ravel())
    r = dict(unique=int((c > 0).sum()), once=int((c == 1).sum()))
    for key, (ww, wh) in (("w21", (21, 19)), ("w22", (22, 20))):
        best = (0, None)
        for p, gg in grids.items():
            b = window_stats(gg, ww, wh)
            if b[0] > best[0]:
                best = (b[0], (p,) + b[1])
        r[key] = best
    if steps:
        r.update({"step_" + k: v for k, v in step_stats(g).items()})
    return r
