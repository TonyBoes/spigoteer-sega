"""Previews only: the full map, the screen views, the walk. Reads the layout and the v14 sprites; writes PNG and GIF.
Nothing here decides a pixel of the art."""
from collections import deque
from pathlib import Path

from PIL import Image

import kit
import layout
import world
from world import PAL, DMG_SHADE, SPR, ROOT, ROADS, STOPS, ORDER, TOWN

OUT = Path(__file__).resolve().parents[1]

# ------------------------------------------------------------------------------------------------------------------
# sprites (the approved v14 sprite sheets; OBJ palettes as gen_smap.py: CGB their own, DMG OBP0 = 0xD0)
# ------------------------------------------------------------------------------------------------------------------
DMG_OBJ = {1: DMG_SHADE[0], 2: DMG_SHADE[1], 3: DMG_SHADE[3]}


def load_spr(name):
    im = Image.open(SPR / f"obj_{name}.png")
    pal = im.getpalette()
    cols = [tuple(pal[i * 3:i * 3 + 3]) for i in range(4)]
    px = [[im.getpixel((x, y)) for x in range(im.width)] for y in range(im.height)]
    return px, cols[1:]


SP = {n: load_spr(n) for n in ("sal", "ufo", "dot_open", "dot_locked", "bang", "arrow")}


def arrow_variants():
    px, cols = SP["arrow"]
    down = [[px[x][y] for x in range(8)] for y in range(8)]
    up = down[::-1]
    left = [r[::-1] for r in px]
    return {"R": (px, cols), "D": (down, cols), "U": (up, cols), "L": (left, cols)}


ARROWS = arrow_variants()


def blit(im, spr, x, y, mode, flip=False):
    px, cols = spr
    W, H = im.size
    for j, row in enumerate(px):
        for i, v in enumerate(row[::-1] if flip else row):
            if v == 0:
                continue
            X, Y = x + i, y + j
            if 0 <= X < W and 0 <= Y < H:
                im.putpixel((X, Y), cols[v - 1] if mode == "cgb" else (DMG_OBJ[v],) * 3)


# ------------------------------------------------------------------------------------------------------------------
# the world pictures
# ------------------------------------------------------------------------------------------------------------------
def to_rgb(w, mode):
    im = w.pic()
    out = Image.new("RGB", im.size)
    for y in range(im.height):
        for x in range(im.width):
            v = im.getpixel((x, y))
            out.putpixel((x, y), PAL[v // 4][v % 4] if mode == "cgb" else (DMG_SHADE[v % 4],) * 3)
    return out


EARLY_OPEN = {"town", "saloon", "stadium"}
LATE = layout.build()
EARLY = layout.apply_fog(layout.build(), EARLY_OPEN)
IMG = {(st, m): to_rgb(w, m) for st, w in (("late", LATE), ("early", EARLY)) for m in ("cgb", "dmg")}

# ------------------------------------------------------------------------------------------------------------------
# the legs of the walk: each stop's exits (D-pad direction -> next stop)
# ------------------------------------------------------------------------------------------------------------------
LEGS = {
    "town": {"L": "saloon", "R": "cow"}, "saloon": {"R": "town", "U": "stadium"}, "stadium": {"D": "saloon", "R": "lodge"},
    "lodge": {"L": "stadium", "R": "bistro"}, "bistro": {"L": "lodge", "R": "igloo", "D": "factory"}, "igloo": {"L": "bistro"},
    "factory": {"U": "bistro", "D": "cow"}, "cow": {"U": "factory", "D": "teahouse", "L": "town"},
    "teahouse": {"R": "cow", "L": "zoo"}, "zoo": {"R": "teahouse", "L": "lounge"}, "lounge": {"R": "zoo"}}
WALK = set(ROADS) | {(x, 20) for x in range(TOWN[0], TOWN[2] + 1)}


def path(a, b):
    s, t = STOPS[a], STOPS[b]
    prev = {s: None}
    q = deque([s])
    while q:
        c = q.popleft()
        if c == t:
            break
        for d in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            n = (c[0] + d[0], c[1] + d[1])
            if n in WALK and n not in prev:
                prev[n] = c
                q.append(n)
    out, c = [], t
    while c:
        out.append(c)
        c = prev[c]
    return out[::-1]


def segments(cells):
    """a path as (direction, length in cells) runs: the data the engine would store"""
    segs = []
    for a, b in zip(cells, cells[1:]):
        d = "R" if b[0] > a[0] else "L" if b[0] < a[0] else "D" if b[1] > a[1] else "U"
        if segs and segs[-1][0] == d:
            segs[-1][1] += 1
        else:
            segs.append([d, 1])
    return segs


def sal_xy(cell):
    return cell[0] * 8 - 4, cell[1] * 8 - 6


# ------------------------------------------------------------------------------------------------------------------
# frames
# ------------------------------------------------------------------------------------------------------------------
GLYPHS = {}


def _load_glyphs():
    for f in ("bar.txt", "story.txt"):
        name = None
        rows = []
        for line in (ROOT / "assets" / "tiles" / f).read_text().splitlines() + [""]:
            if line.startswith("@"):
                name, rows = line[1:], []
            elif name and line and not line.startswith(";") and len(line) == 8:
                rows.append(line)
            elif name and rows:
                if len(rows) == 8:
                    GLYPHS[name] = [[{".": 0, "-": 1, "+": 2, "#": 3}[c] for c in r] for r in rows]
                name = None


_load_glyphs()
PUNCT = {"!": "excl", ".": "period", "-": "hyphen", ":": "colon"}


def glyph(ch):
    if ch == " ":
        return GLYPHS["hud_blank"]
    return GLYPHS.get("glyph_" + PUNCT.get(ch, ch))


def banner(im, text, y, mode):
    """the name tag: one row of the window, BG palette 0, light letters on the dark band"""
    pal0 = PAL[0]
    for cx in range(20):
        g = glyph(text[cx - 1]) if 1 <= cx <= len(text) else GLYPHS["hud_blank"]
        for j in range(8):
            for i in range(8):
                Y = y + j
                if 0 <= Y < im.height:
                    v = g[j][i]
                    im.putpixel((cx * 8 + i, Y), pal0[v] if mode == "cgb" else (DMG_SHADE[v],) * 3)


def clampcam(x, y):
    return max(0, min(96, x)), max(0, min(112, y))


def frame(state, mode, cam, sal=None, sal_flip=False, here=None, walking=False, tick=0, text=None, text_y=0, dots=True, arrows=True, bang=False,
          revealed=None, peek=()):
    full = IMG[(state, mode)]
    cx, cy = cam
    im = full.crop((cx, cy, cx + 160, cy + 144))
    # dots at every revealed stop (green open, red locked)
    if dots:
        for name, c in STOPS.items():
            if revealed is not None and name not in revealed:
                continue
            blit(im, SP["dot_open"], c[0] * 8 - cx, c[1] * 8 - cy, mode)
    for name in peek:                      # the next locked stop shows as a red dot on the edge of the fog
        c = STOPS[name]
        blit(im, SP["dot_locked"], c[0] * 8 - cx, c[1] * 8 - cy, mode)
    # the UFO over the desert mountain
    if revealed is None or "lounge" in revealed:
        blit(im, SP["ufo"], 44 - cx, 188 + (1 if (tick // 24) % 2 else 0) - cy, mode)
    if bang:
        blit(im, SP["bang"], 156 - cx, 126 - cy, mode)
    if sal is not None:
        sx, sy = sal
        by = 1 if walking and (tick // 4) % 2 else 0       # a one pixel bob while walking
        blit(im, SP["sal"], sx - cx, sy - cy - by, mode, flip=sal_flip)
        if here and arrows:
            nudge = (tick // 12) % 2
            for d in LEGS[here]:
                if revealed is not None and LEGS[here][d] not in revealed:
                    continue
                ax, ay = {"R": (sx + 16 + nudge, sy + 4), "L": (sx - 8 - nudge, sy + 4), "U": (sx + 4, sy - 6 - nudge),
                          "D": (sx + 4, sy + 16 + nudge)}[d]
                blit(im, ARROWS[d], ax - cx, ay - cy, mode)
    if text:
        banner(im, text, text_y, mode)
    return im


def scale(im, k):
    return im.resize((im.width * k, im.height * k), Image.NEAREST)


def stack(a, b, gap=6, bg=(40, 40, 40)):
    out = Image.new("RGB", (a.width, a.height + b.height + gap), bg)
    out.paste(a, (0, 0))
    out.paste(b, (0, a.height + gap))
    return out


def side(a, b, gap=6, bg=(40, 40, 40)):
    out = Image.new("RGB", (a.width + b.width + gap, a.height), bg)
    out.paste(a, (0, 0))
    out.paste(b, (a.width + gap, 0))
    return out


TAG = {"saloon": "CH1 THE SALOON", "stadium": "CH2 THE STADIUM", "lodge": "CH3 LUMBER LODGE", "bistro": "CH4 THE BISTRO",
       "igloo": "CH5 THE IGLOO", "factory": "CH6 ROBOT FACTORY", "cow": "CH7 THE CHROME COW", "teahouse": "CH8 THE TEAHOUSE",
       "zoo": "CH9 THE JUNGLE ZOO", "lounge": "CH10 SPACE LOUNGE", "town": "FESTIVAL SQUARE"}
EARLY_REV = {"town", "saloon", "stadium"}


def view_cam(c, bias=(0, 0)):
    return clampcam(c[0] * 8 - 80 + bias[0], c[1] * 8 - 72 + bias[1])
