"""Falls v2 (owner: "the waterfall looks like it comes out of a cave ... can the cave be a little bit higher up the mountain ... or maybe the waterfall's coming up from higher up on the
mountain ... the geometry of the mountain walls that kind of jut out at weird angles next to the waterfall").  PROPOSAL ONLY: nothing under assets/.

Two options for mountain B's right flank, both replacing falls_cave.py (the cave mouth and the rock ledge below the foot are gone):
  A  a small cleft partway up the flank, a narrow cascade down the face, a fan where it spreads, then the approved column.
  B  a notch just under the snow line, a gully cut into the face (dark walls), a lip and a short fan-out drop into the approved column.
Both: the ground under the foot is the map's own grass again (the snow ledge cells 45..49 of row 5 are not touched), the two falls cells of row 5 are the APPROVED art again (water palette,
grass banks, the approved bank rim), and the new art lives on and above the mountain's foot line (y 39), in cells that already take the `igloo` palette (row 4 and up).

The art is typed in falls_art.py: each row is a list of (x, string) runs, absolute x; a pixel that is not typed keeps what the mountain generator drew; digits are igloo-palette indices (0 snow,
1 pale rock, 2 deep, 3 ink; light from the top left); letters are flowing-water pixels (animated): 'w' takes the approved streak column of its x ((x - 372) % 8), 'a'..'h' name the approved
streak column 0..7 by hand.  Every pixel is placed by hand in falls_art.py; code only writes it into the map.

Water on the face reuses the approved streak columns (smap_anim/items.py FALL_COLS, step 3 rows, 4 frames): the pixel (x, y) of frame k is foam (index 0) when FALL_COLS[f][(y - 40 - 3k) % 12]
is '-', else water (index 1), so the cascade continues the approved column's pattern upward.  The cascade cells step at video frame 4 mod 9 (the approved falls step at 0, the lip at 6,
the water glints and the igloo smoke at multiples of 15): no step lands on another."""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "smap_import"))
sys.path.insert(0, str(HERE))
import falls_cave as FC  # noqa: E402   (the approved art readers: static_art, fall_rows, to_dmg)
import falls_art as art  # noqa: E402

PHASE = 4                                    # video frames added to the falls step clock for the cascade cells
I = FC._items
FALL_COLS = I.FALL_COLS
FALL_STEP = I.FALL_STEP
WATER_CH = "wabcdefgh"                      # animated water pixels
STATIC_WATER = "WABCDEFGH"                   # water pixels that do not animate (frame 0 of the same streak columns)
OPTIONS = art.OPTIONS



def typed(opt):
    """{(x, y): char} of every typed pixel: a row is a list of (x, string) runs, the string starting at x"""
    out = {}
    for y, runs in OPTIONS[opt]["rows"].items():
        for x, st in runs:
            for i, c in enumerate(st):
                if c != ".":
                    assert (x + i, y) not in out or out[(x + i, y)] == c, ("typed twice", x + i, y)
                    out[(x + i, y)] = c
    return out


def is_foam(x, y, k, f=None):
    f = (x - 372) % 8 if f is None else f
    return FALL_COLS[f][(y - 40 - FALL_STEP * k) % 12] == "-"


def static_water_px(opt):
    out = {}
    for (x, y), c in typed(opt).items():
        if c in STATIC_WATER:
            out[(x, y)] = 0 if is_foam(x, y, 0, None if c == "W" else ord(c) - 65) else 1
    return out


def water_px(opt, k):
    """{(x, y): index} of the flowing-water pixels of the option on frame k (foam 0, water 1)"""
    out = {}
    for (x, y), c in typed(opt).items():
        if c in WATER_CH:
            out[(x, y)] = 0 if is_foam(x, y, k, None if c == "w" else ord(c) - 97) else 1
    return out


def static_px(opt):
    """{(x, y): index} of every typed pixel that is not water"""
    out = {}
    for (x, y), c in typed(opt).items():
        if c not in WATER_CH and c not in STATIC_WATER:
            out[(x, y)] = int(c)
    return out


def paste_row5(WORLDS):
    """the two falls cells of row 5 back to the approved art on the `water` palette (frame 0), DMG through to_dmg"""
    for side, cx in (("L", 46), ("R", 47)):
        t = FC._tile(FC.fall_rows(side, 0)[:8])
        for w in WORLDS:
            dmg = w is WORLDS[1]
            for j in range(8):
                for i in range(8):
                    v = t[j][i]
                    w.px[5 * 8 + j][cx * 8 + i] = FC.to_dmg(v, cx, 5, i) if dmg else v
            w.pal[5][cx] = "water"


def anim_cells(opt):
    """the cells that hold flowing-water pixels of this option (each is animated: 4 images)"""
    return sorted({(x // 8, y // 8) for (x, y) in water_px(opt, 0)})


def apply(WORLDS, opt):
    FC.static_art(WORLDS)
    paste_row5(WORLDS)
    px = dict(static_px(opt))
    px.update(static_water_px(opt))
    px.update(water_px(opt, 0))
    touched = set()
    for w in WORLDS:
        for (x, y), v in px.items():
            w.px[y][x] = v
    for (x, y) in px:
        touched.add((x // 8, y // 8))
    for w in WORLDS:
        for (cx, cy) in touched:
            assert cy <= 4, (cx, cy)                 # the new art stays on the igloo cells (row 4 and up)
            w.pal[cy][cx] = "igloo"
    return touched | {(46, 5), (47, 5), (46, 6), (47, 6), (46, 7), (47, 7), (46, 8), (47, 8)}
