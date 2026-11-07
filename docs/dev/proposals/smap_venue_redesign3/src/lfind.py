"""python3 lfind.py NAME: list the lint's L-shaped doubles (ink pixels with an ink neighbour across and one up or down, the corner open, both arms 1 px) in a piece, with
the value of the neighbouring non-ink pixel that I would put there, as a literal list to paste into the piece's CLEANUP (my hand decisions are the pasted values)."""
import importlib
import sys

import common as C


def find(px, w, h):
    out = []
    for y in range(h):
        for x in range(w):
            if px[y][x] != "3":
                continue
            hit = False
            for dy in (-1, 1):
                for dx in (-1, 1):
                    yy, xx = y + dy, x + dx
                    if 0 <= yy < h and 0 <= xx < w and px[y][xx] == "3" and px[yy][x] == "3" and px[yy][xx] != "3":
                        bh = 0 <= x + 2 * dx < w and px[y][x + 2 * dx] == "3"
                        bv = 0 <= y + 2 * dy < h and px[y + 2 * dy][x] == "3"
                        if not bh and not bv:
                            hit = True
            if hit:
                nb = [px[y + dy][x + dx] for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)) if 0 <= x + dx < w and 0 <= y + dy < h and px[y + dy][x + dx] != "3"]
                out.append((x, y, "0" if "0" in nb else nb[0]))
    return out


if __name__ == "__main__":
    m = importlib.import_module(sys.argv[1])
    c = m.build() if len(sys.argv) < 3 else getattr(m, sys.argv[2])(False, "saloon")
    print(find(c.px, c.w, c.h))
