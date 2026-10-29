#!/usr/bin/env python3
"""Preview tool for the festival-room proposals (docs/dev/concepts/festival_room/): it only READS the hand-made grids
(stage.txt, bar.txt, attr.txt, bar_attr.txt, floor.txt, pal.json, the patron / bartender art) and transcribes them into
PNGs the way the engine would show them (src/po.c layout). It decides no pixel.

    python3 render.py venue DIR OUT_PREFIX        # DIR/{stage,attr,bar,bar_attr,floor}.txt + pal.json
        -> OUT_PREFIX_{dmg,cgb}_x1.png (Pour-Off, play) and _intro_ (banner up), plus tile counts on stdout
    python3 render.py venue assets/approved/venues/saloon ...  (the saloon's files have prefix saloon_: pass the prefix as DIR/saloon)
"""
import json
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[4] if (Path(__file__).resolve().parents[4] / "assets").exists() else Path.cwd()
DMG = [(255, 255, 255), (153, 153, 153), (85, 85, 85), (0, 0, 0)]       # the goldens' shades (BGP 0xE4)
IDX = {".": 0, "-": 1, "+": 2, "#": 3}
CLEAR = {".": None, "-": 1, "+": 2, "#": 3}


def hexrgb(h):                       # RGB555 truncation, as the goldens show it
    r, g, b = (int(h[i:i + 2], 16) for i in (1, 3, 5))
    return ((r >> 3) << 3, (g >> 3) << 3, (b >> 3) << 3)


def rows_of(path):
    return [l.rstrip() for l in Path(path).read_text().splitlines() if l.strip() and not l.startswith(";")]


def load_venue(prefix):
    """prefix = path without the suffix: 'dir/saloon' reads dir/saloon_stage.txt ...; 'dir' with plain names also works."""
    p = Path(prefix)
    if p.is_dir():
        f = lambda n: p / n
    else:
        f = lambda n: p.parent / f"{p.name}_{n}"
    v = {"stage": rows_of(f("stage.txt")), "bar": rows_of(f("bar.txt")), "floor": rows_of(f("floor.txt")),
         "attr": [[int(c) for c in r] for r in rows_of(f("attr.txt"))],
         "battr": [[int(c) for c in r] for r in rows_of(f("bar_attr.txt"))],
         "pal": json.loads(Path(f("pal.json")).read_text())}
    return v


def tile_key(rows, tx, ty):
    return tuple(rows[ty * 8 + y][tx * 8:tx * 8 + 8] for y in range(8))


def counts(v):
    st = {tile_key(v["stage"], x, y) for y in range(4) for x in range(20)}
    br = {tile_key(v["bar"], x, y) for y in range(3) for x in range(20)}
    br.add(tuple(v["floor"]))
    # keys that matter for CGB: (tile, palette) pairs
    return len(st), len(br)


def parse_frames(path, w=16, h=16):
    """blocks of w x h pixel rows (the patron / bartender art files), comments dropped."""
    out, cur = [], []
    for line in Path(path).read_text().splitlines() + [""]:
        line = line.rstrip()
        if line.startswith(";"):
            continue
        if not line:
            if cur:
                if len(cur) == h and all(len(r) == w for r in cur):
                    out.append(cur)
                cur = []
            continue
        cur.append(line)
    return out


def pal_hex(name, root):
    return json.loads((Path(root) / "assets/palettes.json").read_text())[name]["hex"]


class Screen:
    def __init__(self, mode):
        self.mode = mode
        self.im = Image.new("RGB", (160, 144), (0, 0, 0))

    def col(self, idx, pal):                 # pal: 4 hex strings (CGB) -- DMG ignores the colours
        return hexrgb(pal[idx]) if self.mode == "cgb" else DMG[idx]

    def put(self, x, y, idx, pal):
        if 0 <= x < 160 and 0 <= y < 144:
            self.im.putpixel((x, y), self.col(idx, pal))

    def bg_region(self, x0, y0, rows, pals, w_tiles, attr, flip_x=False):
        pass


def build(v, mode, root, crowd=(), sprites=(), intro=False, hud_from=None, intro_from=None, bar_mirror=True):
    """crowd: [(bar, k, rows16, hex3)] ; sprites: [(x, y, rows, hex3, flip)]"""
    s = Screen(mode)
    pal = v["pal"]
    P = {0: pal["stage_a"]["hex"], 1: pal["stage_b"]["hex"]}
    bar_p = {0: pal["bar"]["hex"], 1: pal.get("bar_b", pal["bar"])["hex"]}
    # stage rows 1-4 (y 8-39)
    for ty in range(4):
        for tx in range(20):
            pp = P[v["attr"][ty][tx]]
            for y in range(8):
                for x in range(8):
                    s.put(tx * 8 + x, 8 + ty * 8 + y, IDX[v["stage"][ty * 8 + y][tx * 8 + x]], pp)
    # bars: 4 x (3 tile rows); columns 0-2 = columns 19-17 mirrored
    def bar_px(tx, r, x, y, bar_rows=v["bar"]):
        return IDX[bar_rows[r * 8 + y][tx * 8 + x]]
    for b in range(4):
        y0 = 40 + 24 * b
        for r in range(3):
            for tx in range(20):
                src, mir = (tx, False) if (tx >= 3 or not bar_mirror) else (19 - tx, True)
                pp = bar_p[v["battr"][r][src]]
                for y in range(8):
                    for x in range(8):
                        sx = 7 - x if mir else x
                        s.put(tx * 8 + x, y0 + r * 8 + y, bar_px(src, r, sx, y), pp)
    # the floor row (row 17)
    for tx in range(20):
        for y in range(8):
            for x in range(8):
                s.put(tx * 8 + x, 136 + y, IDX[v["floor"][y][x]], bar_p[0])
    # the crowd: 24x16 footprint repainted with the wall colour, the 16x16 look at its left
    wall = bar_p[0]
    for (b, k, rows, hx) in crowd:
        x0, y0 = 40 + 32 * k, 40 + 24 * b
        p = [wall[0]] + list(hx)
        for y in range(16):
            for x in range(24):
                s.put(x0 + x, y0 + y, 0, p)
        for y in range(16):
            for x in range(16):
                i = IDX[rows[y][x]]
                if i:
                    s.put(x0 + x, y0 + y, i, p)
    # sprites (transparent idx 0)
    for (x0, y0, rows, hx, flip, dmgmap) in sprites:
        p = ["#000000"] + list(hx)
        h, w = len(rows), len(rows[0])
        for y in range(h):
            for x in range(w):
                i = IDX[rows[y][(w - 1 - x) if flip else x]]
                if i:
                    if mode == "dmg":
                        s.im.putpixel((x0 + x, y0 + y), (dmgmap[i],) * 3)
                    else:
                        s.put(x0 + x, y0 + y, i, p)
    # HUD row 0 from the real screenshot, and (intro) the banner rows from the real intro screenshot
    if hud_from is not None:
        s.im.paste(hud_from.crop((0, 0, 160, 8)), (0, 0))
    if intro and intro_from is not None:
        s.im.paste(intro_from.crop((0, 8, 160, 32)), (0, 8))
    return s.im


def scale(im, n):
    return im.resize((im.width * n, im.height * n), Image.NEAREST)


if __name__ == "__main__":
    if sys.argv[1] == "venue":
        v = load_venue(sys.argv[2])
        print("stage tiles", counts(v)[0], "bar tiles incl. floor", counts(v)[1])
        g = ROOT / "tests/golden"
        for m in ("dmg", "cgb"):
            hud = Image.open(g / f"po_perfect.{m}.png").convert("RGB")
            intro = Image.open(g / f"po_intro.{m}.png").convert("RGB")
            build(v, m, ROOT, hud_from=hud).save(f"{sys.argv[3]}_{m}.png")
            build(v, m, ROOT, hud_from=hud, intro=True, intro_from=intro).save(f"{sys.argv[3]}_intro_{m}.png")
