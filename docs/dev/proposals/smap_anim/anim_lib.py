"""Engine of the map-animation mockups (preview only: it composes, previews and measures; every animated pixel is a typed grid in items.py).

A Scene is a pixel-index grid (the DMG value is the index, Color recolours by the cell's palette) plus the palette name of every 8x8 cell.
A TileAnim is one animated tile image: the typed frames of ONE 8x8 tile, a sequence over them, the step period in video frames (60 fps) and a phase.
Every cell of the scene whose tile equals the animated tile's base image changes with it (that is what rewriting VRAM does), so the stats count tiles, not cells.
An Item is one mockup: a scene, a 160 x 144 view and its TileAnims."""
import json
from dataclasses import dataclass, field
from math import gcd
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
DMG_SHADE = [248, 168, 88, 24]
VW, VH = 160, 144
CH_IDX = {".": 0, "-": 1, "+": 2, "#": 3, "0": 0, "1": 1, "2": 2, "3": 3}


def T(*rows):
    """a typed tile: 8 strings of 8 characters ('.' 0 lightest, '-' 1, '+' 2, '#' 3 darkest; digits work too)"""
    assert len(rows) == 8 and all(len(r) == 8 for r in rows), rows
    return tuple("".join(str(CH_IDX[c]) for c in r) for r in rows)


class Scene:
    def __init__(self, px, pal, colors):
        self.px = np.array(px, dtype=np.uint8)         # [y][x]
        self.pal = pal                                  # [cy][cx] palette name
        self.colors = colors                            # name -> [(r, g, b)] * 4
        self.cw, self.ch = self.px.shape[1] // 8, self.px.shape[0] // 8

    def tile(self, cx, cy):
        b = self.px[cy * 8:cy * 8 + 8, cx * 8:cx * 8 + 8]
        return tuple("".join(str(int(v)) for v in row) for row in b)

    def all_tiles(self):
        return {self.tile(x, y) for y in range(self.ch) for x in range(self.cw)}

    def cells_with(self, rows):
        return [(x, y) for y in range(self.ch) for x in range(self.cw) if self.tile(x, y) == rows]

    def show(self, cx, cy):
        for r in self.tile(cx, cy):
            print("".join(".-+#"[int(c)] for c in r))


def load_a5():
    import mapctx as M
    px, pal = M.grid()
    colors = {n: [tuple(c) for c in M.PAL.get(n)] for n in {p for r in pal for p in r}}
    return Scene(px, pal, colors)


def load_r3(name):
    s = json.load(open(HERE.parents[3] / "out" / "an" / "r3.json"))[name]
    return Scene([[int(c) for c in r] for r in s["px"]], s["pal"], {k: [tuple(c) for c in v] for k, v in s["colors"].items()})


@dataclass
class TileAnim:
    name: str
    at: tuple                     # a cell (cx, cy) that holds the base image (frame 0 is read from the scene)
    frames: list                  # typed tiles for frames 1.. (frame 0 = the scene's own tile)
    seq: list                     # frame index per step, looping
    period: int                   # video frames per step
    phase: int = 0                # video frames added to t
    only_at: bool = False         # True: animate only the cell `at` even if the image repeats elsewhere (checked by the stats)
    note: str = ""


@dataclass
class Item:
    key: str
    title: str
    scene: Scene
    view: tuple                   # x0, y0 of the 160 x 144 window (scene px)
    anims: list
    focus: tuple = None           # x0, y0, x1, y1 of the strip crop (scene px), for the frame strip
    edits: dict = field(default_factory=dict)     # {(x, y): index} art that is new even at rest (typed pixels, applied to every frame)
    cells_cache: dict = field(default_factory=dict)

    def base_scene_px(self):
        px = self.scene.px.copy()
        for (x, y), v in self.edits.items():
            px[y, x] = v
        return px

    def tile_at(self, px, cx, cy):
        b = px[cy * 8:cy * 8 + 8, cx * 8:cx * 8 + 8]
        return tuple("".join(str(int(v)) for v in row) for row in b)

    def resolve(self):
        """per anim: the base tile (after statics) and the cells that hold it"""
        px = self.base_scene_px()
        out = []
        for a in self.anims:
            base = self.tile_at(px, *a.at)
            if a.only_at:
                cells = [a.at]
            else:
                cells = [(x, y) for y in range(self.scene.ch) for x in range(self.scene.cw) if self.tile_at(px, x, y) == base]
            out.append((a, base, cells))
        return out

    def loop_len(self):
        n = 1
        for a in self.anims:
            L = len(a.seq) * a.period
            n = n * L // gcd(n, L)
        return n

    def frame_idx(self, a, t):
        return a.seq[((t + a.phase) // a.period) % len(a.seq)]

    def state(self, t, res=None):
        px = self.base_scene_px()
        for a, base, cells in (res or self.resolve()):
            k = self.frame_idx(a, t)
            rows = base if k == 0 else a.frames[k - 1]
            for cx, cy in cells:
                put(px, cx, cy, rows)
        return px


def put(px, cx, cy, rows):
    for j, r in enumerate(rows):
        for i, c in enumerate(r):
            px[cy * 8 + j, cx * 8 + i] = int(c)


def render(scene, px, view, dmg, scale=1, box=None):
    x0, y0 = view if box is None else box[:2]
    w, h = (VW, VH) if box is None else (box[2] - box[0], box[3] - box[1])
    out = np.zeros((h, w, 3), dtype=np.uint8)
    lut = {n: np.array(c, dtype=np.uint8) for n, c in scene.colors.items()}
    g = np.array([[v] * 3 for v in DMG_SHADE], dtype=np.uint8)
    for y in range(h):
        for x in range(w):
            X, Y = x0 + x, y0 + y
            v = int(px[Y, X])
            out[y, x] = g[v] if dmg else lut[scene.pal[Y // 8][X // 8]][v]
    im = Image.fromarray(out)
    return im if scale == 1 else im.resize((w * scale, h * scale), Image.NEAREST)


def side_by_side(a, b, gap=8):
    im = Image.new("RGB", (a.width + gap + b.width, a.height), (40, 40, 40))
    im.paste(a, (0, 0))
    im.paste(b, (a.width + gap, 0))
    return im


def save_gif(frames, path, ms):
    """frames: RGB images; one fixed palette for the whole GIF (exact colours, no dithering), loops forever"""
    cols = {}
    arrs = [np.asarray(f) for f in frames]
    for a in arrs:
        for c in np.unique(a.reshape(-1, 3), axis=0):
            cols.setdefault(tuple(int(v) for v in c), len(cols))
    assert len(cols) <= 256, len(cols)
    pal = [0] * 768
    for c, i in cols.items():
        pal[i * 3:i * 3 + 3] = list(c)
    key = lambda a: (a[..., 0].astype(np.uint32) << 16) | (a[..., 1].astype(np.uint32) << 8) | a[..., 2]
    lut_k = np.array([(c[0] << 16) | (c[1] << 8) | c[2] for c in cols], dtype=np.uint32)
    order = np.argsort(lut_k)
    sk = lut_k[order]
    ims = []
    for a in arrs:
        idx = order[np.searchsorted(sk, key(a))].astype(np.uint8)
        im = Image.fromarray(idx, "P")
        im.putpalette(pal)
        ims.append(im)
    ims[0].save(path, save_all=True, append_images=ims[1:], duration=ms, loop=0, disposal=1, optimize=False)


def E(*items):
    """typed pixel edits: (y, x0, x1, v) is a run on row y; (x, y, v) is one pixel.  Returns {(x, y): v}"""
    d = {}
    for it in items:
        if len(it) == 4:
            y, x0, x1, v = it
            for x in range(x0, x1 + 1):
                d[(x, y)] = v
        else:
            x, y, v = it
            d[(x, y)] = v
    return d


def region_anims(scene, static, frames, seq, period, phase=0, prefix="", only_at=True):
    """frames: [edits for frame 1, 2, ...] on top of the scene (+ the static edits); frame 0 is the scene as it is (+ static).
    One TileAnim per cell that any frame touches; its frame tiles are read from the edited pixels."""
    base = scene.px.copy()
    for (x, y), v in static.items():
        base[y, x] = v
    cells = {}
    for k, ed in enumerate(frames):
        for (x, y) in ed:
            cells.setdefault((x // 8, y // 8), set())
    out = []
    for (cx, cy) in sorted(cells):
        tl = []
        for ed in frames:
            px = base.copy()
            for (x, y), v in ed.items():
                px[y, x] = v
            b = px[cy * 8:cy * 8 + 8, cx * 8:cx * 8 + 8]
            tl.append(tuple("".join(str(int(v)) for v in row) for row in b))
        out.append(TileAnim(f"{prefix}({cx},{cy})", (cx, cy), tl, seq, period, phase, only_at=only_at))
    return out
