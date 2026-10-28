"""Patron tile sharing, counted from the art (assets/art/patrons/*.txt), no atlas needed.
For each group: tiles stored today, unique tiles (exact), unique with the blank shared, and the shift-0 pairs.
Run: python3 tools/dev/patron_dups.py [-v]   (companion of tile_dups.py, which counts the whole VRAM from the atlas)
"""
import sys, os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import gen_art as G

def look_tiles(v, back):
    """-> (shifted: {s: [6 tiles column-major]}, back: [4 tiles]) as bytes tuples for a 16x16 front/back."""
    sh = {}
    for s in range(8):
        canvas = ["." * s + v[y] + "." * (8 - s) for y in range(16)]
        t = []
        for tx in (0, 8, 16):
            t += [bytes(G.tile_bytes(canvas, tx, 0)), bytes(G.tile_bytes(canvas, tx, 8))]
        sh[s] = t
    bk = [bytes(G.tile_bytes(back, tx, ty)) for ty in (0, 8) for tx in (0, 8)]
    return sh, bk

def group(path_front, path_back):
    vs = [r for _, r in G.blocks(path_front)]
    bs = [r for _, r in G.blocks(path_back)]
    return [look_tiles(v, b) for v, b in zip(vs, bs)]

def count(looks):
    """stored today (shifted 6 + shift-0 4 + back 4 per look), unique, unique non-blank, pairs"""
    blank = bytes(16)
    allt = []
    for sh, bk in looks:
        for s in range(1, 8): allt += sh[s]
        allt += sh[0][:4] + bk
    stored = len(allt)
    uniq = len(set(allt))
    nb = len(set(allt) - {blank})
    # 8x16 pairs (top, bottom) shareable for the shift-0 OBJ step
    pairs = []
    for sh, bk in looks:
        for s in range(1, 8):
            pairs += [tuple(sh[s][i:i + 2]) for i in (0, 2, 4)]
        pairs += [tuple(sh[0][i:i + 2]) for i in (0, 2)] + [tuple(bk[i::2]) for i in (0, 1)]
    return stored, uniq, nb, len(pairs), len(set(pairs)), len({p for p in pairs if p != (blank, blank)})

def report(name, looks, verbose):
    blank = bytes(16)
    allt = []
    for sh, bk in looks:
        for s in range(1, 8): allt += sh[s]
        allt += sh[0][:4] + bk
    nblank = allt.count(blank)
    nonblank_dup = len(allt) - nblank - len(set(allt) - {blank})
    st, u, nb, np_, up, upn = count(looks)
    print(f"{name:16} stored {st:3} | blanks {nblank:2} + copies {nonblank_dup:2} = {nblank + nonblank_dup:2} tiles shareable (the blank pair already exists) "
          f"| whole 8x16 columns only: {2 * (np_ - up):2}")

def main():
    verbose = "-v" in sys.argv
    P = G.ROOT / "assets/art/patrons"
    tot = 0
    for g in G.PATRON_GROUPS:
        report(g, group(P / f"{g}.txt", P / f"{g}_back.txt"), verbose)
    report("saloon_x(bank1)", group(P / "saloon_x.txt", P / "saloon_x_back.txt"), verbose)

if __name__ == "__main__":
    main()
