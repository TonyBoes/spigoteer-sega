"""python3 -I count.py (SMAP_TEA_PASS=1 or not): distinct 8x8 tiles of the whole DMG-pixel map exact, and with flips merged (quick proxy for measure.py's colour and DMG tile numbers)."""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import swap  # noqa: E402,F401
sys.path.insert(0, str(HERE.parent / "smap_import"))
import mapctx as M  # noqa: E402


def counts(DMG=True):
    g, _ = M.grid(DMG)
    ex, fl = set(), set()
    for cy in range(M.CH):
        for cx in range(M.CW):
            t = tuple(tuple(g[cy * 8 + j][cx * 8:cx * 8 + 8]) for j in range(8))
            ex.add(t)
            v = tuple(reversed(t))
            h = tuple(tuple(reversed(r)) for r in t)
            hv = tuple(tuple(reversed(r)) for r in v)
            fl.add(min(t, v, h, hv))
    return len(ex), len(fl)


if __name__ == "__main__":
    print("DMG tiles", counts(True)[0], " Color tiles", counts(False)[0])
