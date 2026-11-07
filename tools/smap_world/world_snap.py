"""The story map's world as the build reads it (stage 2 of the map import, owner Q113 / Q115 A' / Q117 B): the frozen snapshot in assets/smap/ (tools/dev/smap_snapshot.py writes it from the
proposal pipeline), in the shape tools/gen_smap_world.py expects of a world module.

    CW, CH         the cells (64 x 70)
    ORDER, STOPS, LEGS, VENUES    the chapters' order, the stops' feet positions, the legs' waypoints, the venues' picture cells
    WORLD, WORLD_DMG              the Color and the DMG data set: .px[y][x] (0..3, 8 px a cell), .pal[cy][cx] (the cell's palette name)
    ZONE           the zone of each cell: "town" (always shown) or "repair" (the fountain's broken cells: shown broken until the story repairs it, unlock state 11)
    PAL_NAMES, RGB, DMG_SHADE     the 22 BG palettes the map uses and their colours
    with_fog(world, revealed)     the world as an unlock state shows it: the cloud is cut (owner 11-06), so the only cells that change are the REPAIR cells (the broken fountain)
    ANIM_CELLS     cells whose tile an animation rewrites (the flip-merge never merges those: none until the tile animation, stage 3)
"""
import copy
import json
from pathlib import Path

from PIL import Image

ASSETS = Path(__file__).resolve().parent.parent.parent / "assets" / "smap"
_J = json.loads((ASSETS / "world.json").read_text())

CW, CH = _J["cw"], _J["ch"]
ORDER = list(_J["order"])
STOPS = {k: tuple(v) for k, v in _J["stops"].items()}
LEGS = {(a, b): [tuple(q) for q in pts] for a, b, pts in _J["legs"]}
VENUES = {k: (k, tuple(v)) for k, v in _J["venues"].items()}
PAL_NAMES = list(_J["pal_names"])
RGB = {n: [tuple(c) for c in cols] for n, cols in _J["pal_rgb"].items()}
DMG_SHADE = list(_J["dmg_shade"])
ANIM_CELLS = {tuple(c) for c in _J["anim_cells"]}
REPAIR = {(r["x"], r["y"]): r for r in _J["repair"]}
REPAIR_ZONE = "repair"


class World:
    """px[y][x] in 0..3 over CH * 8 rows, pal[cy][cx] palette names"""

    def __init__(self, png, pal=None):
        im = Image.open(ASSETS / png)
        assert im.mode == "P" and im.size == (CW * 8, CH * 8), (png, im.mode, im.size)
        data = list(im.getdata())
        w = CW * 8
        self.px = [data[y * w:(y + 1) * w] for y in range(CH * 8)]
        self.pal = pal

    def copy(self):
        v = copy.copy(self)
        v.px = [r[:] for r in self.px]
        v.pal = [r[:] for r in self.pal] if self.pal else self.pal
        return v


_cp = [[PAL_NAMES[ord(ch) - 48] for ch in row] for row in _J["cell_pal"]]
WORLD = World("world_c.png", _cp)
WORLD_DMG = World("world_d.png", [r[:] for r in _cp])
ZONE = [["town"] * CW for _ in range(CH)]
for (_x, _y) in REPAIR:
    ZONE[_y][_x] = REPAIR_ZONE


def with_fog(w, revealed):
    """the world as the unlock state shows it: with the REPAIR zone not revealed, the fountain's cells show the broken state"""
    if REPAIR_ZONE in revealed:
        return w
    v = w.copy()
    key = "c" if w is WORLD else "d"
    for (x, y), r in REPAIR.items():
        s = r[key]
        for j in range(8):
            for i in range(8):
                v.px[y * 8 + j][x * 8 + i] = int(s[j * 8 + i])
        if key == "c":
            v.pal[y][x] = PAL_NAMES[r["pal"]]
    return v


def get(name):
    return RGB[name]
