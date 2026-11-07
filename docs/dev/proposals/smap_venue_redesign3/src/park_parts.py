"""Typed parts of the ballpark proposals.  Palettes: STADIUM (stands, masts, gates) 0 white concrete, 1 red, 2 navy, 3 ink;  PARK (the field cells; proposed, built
only from the game's own colours) 0 chalk / white concrete, 1 mown grass, 2 infield dirt, 3 ink.  Light from the top left."""
import kit as K

# stands: 8 x 8 cells, typed.  Spectators are red dots on navy.  TOP = a striped valance over two tiers, SEAT = two tiers, WALL = a tier over the red outfield wall
TOP = ["33333333", "11110000", "11110000", "33333333", "22222222", "22122212", "22222222", "33333333"]
SEAT = ["22222222", "21222122", "22222222", "33333333", "22222222", "22212221", "22222222", "33333333"]
WALL = ["22222222", "22122212", "22222222", "33333333", "11111111", "11111111", "11111111", "33333333"]
MAST_HEAD = ["33333333", "30303030", "33333333", "30303030", "33333333", "00033000", "00033000", "00033000"]
MAST = ["00033000"] * 8
FRONT = ["22222222", "22222222", "11111111", "11111111", "33333333", "22222222", "22222222", "33333333"]
ARCH_L = ["00033333", "00322222", "03222222", "03222222", "32222222", "32222222", "32222222", "32222222"]
ARCH_R = ["33333000", "22222300", "22222230", "22222230", "22222223", "22222223", "22222223", "22222223"]
ARCH_BL = ["32222222", "32222222", "32222222", "32222222", "32222222", "32222222", "32222222", "33333333"]
ARCH_BR = ["22222223", "22222223", "22222223", "22222223", "22222223", "22222223", "22222223", "33333333"]


def cell(c, cx, cy, rows, left_edge=False, right_edge=False):
    for j, r in enumerate(rows):
        for i, ch in enumerate(r):
            v = ch
            if (left_edge and i == 0 and ch in "123") or (right_edge and i == 7 and ch in "123"):
                v = "3"
            c.px[cy * 8 + j][cx * 8 + i] = v


def stroke(c, x0, y0, n, pattern, w, v, over=None):
    """a line of n columns from (x0, y0): each column moves y by the next entry of the typed pattern, and paints w pixels down from y"""
    x, y = x0, y0
    for k in range(n):
        for t in range(w):
            if 0 <= y + t < c.h and 0 <= x < c.w and (over is None or c.px[y + t][x] in over):
                c.px[y + t][x] = v
        y += pattern[k % len(pattern)]
        x += 1


def rows_at(c, x, y, rows, v, over=None):
    """a blob typed as (first column, width) per row, painted with v"""
    for j, (a, w) in enumerate(rows):
        for i in range(w):
            if over is None or c.px[y + j][x + a + i] in over:
                c.px[y + j][x + a + i] = v


def base(c, x, y):
    """a 3 x 3 chalk base with an ink corner on its shaded side"""
    K.rect(c, x, y, x + 3, y + 3, "0")
    c.px[y + 2][x + 2] = "3"


def plate(c, x, y):
    for j, a in enumerate([(0, 5), (0, 5), (0, 5), (1, 3), (2, 1)]):
        for i in range(a[1]):
            c.px[y + j][x + a[0] + i] = "0"
