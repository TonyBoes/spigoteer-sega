"""python3 -I win_tiles.py TAG_A TAG_B c0 c1 r0 r1 : the DMG tiles of the cell window (cols c0..c1, rows r0..r1) in snapshot B that are not in A's window, with their cells (read-only)."""
import sys
from pathlib import Path

from PIL import Image

OUT = Path(__file__).resolve().parents[4] / "out" / "owner1108"
a, b = sys.argv[1], sys.argv[2]
c0, c1, r0, r1 = (int(v) for v in sys.argv[3:7])


def blocks(tag):
    im = Image.open(OUT / f"snap_{tag}" / "world_d.png").convert("L")
    px = im.load()
    out = {}
    for cy in range(r0, r1 + 1):
        for cx in range(c0, c1 + 1):
            k = tuple(px[cx * 8 + i, cy * 8 + j] for j in range(8) for i in range(8))
            out.setdefault(k, []).append((cx, cy))
    return out


A, B = blocks(a), blocks(b)
print(a, len(A), "tiles;", b, len(B), "tiles")
print("only in", b, ":", [(len(v), v[:6]) for k, v in B.items() if k not in A])
print("only in", a, ":", [(len(v), v[:6]) for k, v in A.items() if k not in B])
