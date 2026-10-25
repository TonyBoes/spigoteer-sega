#!/usr/bin/env python3
"""The TEST-ONLY placeholder pictures of the Practice screen (tests/test_practice_art.py): numbered cards, one picture at 56 unique tiles and one at 80.
They are not art and never ship: the default build reads assets/art/practice only; the tests build a ROM of their own from this directory
(make PRACTICE_ART_DIRS=tests/data/practice_art). `shakeup` has no file on purpose: a game without a picture shows the empty frame.
Rewrites the PNGs (python3 tests/data/practice_art/make_placeholders.py); they are committed so the tests do not depend on this script running."""
import random
from pathlib import Path

from PIL import Image

OUT = Path(__file__).resolve().parent
FONT = {  # 5 x 7
    "0": ["01110", "10001", "10011", "10101", "11001", "10001", "01110"], "1": ["00100", "01100", "00100", "00100", "00100", "00100", "01110"],
    "2": ["01110", "10001", "00001", "00110", "01000", "10000", "11111"], "3": ["01110", "10001", "00001", "00110", "00001", "10001", "01110"],
    "4": ["00010", "00110", "01010", "10010", "11111", "00010", "00010"], "5": ["11111", "10000", "11110", "00001", "00001", "10001", "01110"],
    "6": ["00110", "01000", "10000", "11110", "10001", "10001", "01110"], "7": ["11111", "00001", "00010", "00100", "01000", "01000", "01000"],
    "8": ["01110", "10001", "10001", "01110", "10001", "10001", "01110"], "9": ["01110", "10001", "10001", "01111", "00001", "00010", "01100"],
}
PALS = [  # four distinct colours each, lightest first; every card a different look so a wrong picture or palette shows
    [(248, 240, 200), (216, 144, 72), (136, 64, 40), (40, 16, 16)], [(224, 248, 224), (120, 200, 120), (40, 120, 72), (8, 40, 24)],
    [(232, 240, 255), (128, 168, 232), (56, 88, 176), (16, 24, 72)], [(255, 232, 232), (240, 136, 152), (176, 56, 88), (64, 16, 32)],
    [(248, 248, 216), (208, 208, 72), (128, 120, 24), (40, 40, 8)], [(240, 224, 255), (184, 136, 232), (104, 64, 168), (32, 16, 64)],
    [(224, 255, 248), (88, 216, 200), (32, 128, 136), (8, 40, 56)], [(255, 240, 224), (248, 176, 72), (208, 96, 24), (72, 24, 8)],
    [(240, 240, 240), (170, 170, 170), (96, 96, 96), (16, 16, 16)], [(255, 224, 240), (232, 120, 184), (152, 40, 112), (56, 8, 40)],
    [(224, 240, 208), (152, 192, 96), (80, 120, 40), (24, 40, 8)], [(248, 232, 216), (200, 160, 128), (128, 88, 64), (48, 24, 16)],
    [(216, 232, 248), (136, 168, 200), (72, 96, 136), (24, 32, 56)],
]


def save(name, px, pal):
    im = Image.new("P", (80, 64), 0)
    im.putpalette([c for rgb in pal for c in rgb] + [0] * (768 - 12))
    for y in range(64):
        for x in range(80):
            im.putpixel((x, y), px[y][x])
    im.save(OUT / f"{name}.png", optimize=False)
    tiles = {tuple(tuple(px[ty * 8 + y][tx * 8 + x] for x in range(8)) for y in range(8)) for ty in range(8) for tx in range(10)}
    print(f"{name}: {len(tiles)} unique tiles")


def card(n, pal):
    px = [[0] * 80 for _ in range(64)]
    for y in range(64):
        for x in range(80):
            if x < 8 or x >= 72 or y < 8 or y >= 56:
                px[y][x] = 3 if (x // 8 + y // 8) % 3 else 2        # the ring: two flat tiles
            elif (x + y) % 16 < 2:
                px[y][x] = 1                                         # a diagonal tell
    digits = str(n)
    ox = 40 - (len(digits) * 20 - 4) // 2
    for k, d in enumerate(digits):
        for r, row in enumerate(FONT[d]):
            for c, bit in enumerate(row):
                if bit == "1":
                    for dy in range(3):
                        for dx in range(3):
                            px[18 + r * 4 + dy][ox + k * 20 + c * 4 + dx] = 3
    return px


def unique_cells(n_unique, seed):
    """80 cells, the first n_unique all different (random 2-bit pixels), the rest copies of cell 0, shuffled."""
    rng = random.Random(seed)
    cells, seen = [], set()
    while len(cells) < n_unique:
        c = tuple(tuple(rng.randrange(4) for _ in range(8)) for _ in range(8))
        if c not in seen:
            seen.add(c)
            cells.append(c)
    cells += [cells[0]] * (80 - n_unique)
    rng.shuffle(cells)
    px = [[0] * 80 for _ in range(64)]
    for i, c in enumerate(cells):
        for y in range(8):
            for x in range(8):
                px[(i // 10) * 8 + y][(i % 10) * 8 + x] = c[y][x]
    return px


games = ["quickdraw", "shirtcannon", "logroll", "orderup", "marshmallows", "batterysort", "milkrun", "taikopour", "monkeybusiness", "asteroids"]
for i, g in enumerate(games):
    save(g, card(i + 1, PALS[i]), PALS[i])
save("perfectpour", unique_cells(56, 56), PALS[11])
save("tipshower", unique_cells(80, 80), PALS[12])
