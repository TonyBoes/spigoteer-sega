"""Previews only (round 2): the world picture, the 160 x 144 screens, the walk.  Reads world2 and the approved v14 sprite sheets; writes images.
Nothing here decides a pixel of the art.  (Scripted preview, not an engine build: a declared deviation, as in round 1.)"""
from pathlib import Path

from PIL import Image

import pal
import world2 as W2
import salwalk

ROOT = Path(__file__).resolve().parents[6]
SPR = ROOT / "assets" / "story_map"
OUT = Path(__file__).resolve().parents[1]
DMG_OBJ = {1: 248, 2: 168, 3: 24}


# ---- sprites -------------------------------------------------------------------------------------------------------------------------------------------
def load_spr(name):
    im = Image.open(SPR / f"obj_{name}.png")
    p = im.getpalette()
    cols = [tuple(p[i * 3:i * 3 + 3]) for i in range(4)]
    px = [[im.getpixel((x, y)) for x in range(im.width)] for y in range(im.height)]
    return px, cols[1:]


SP = {n: load_spr(n) for n in ("ufo", "dot_open", "dot_locked", "bang", "arrow")}
SAL_COLS = [(0xf8, 0xf8, 0xf0), (0xf0, 0xb8, 0x88), (0x20, 0x20, 0x30)]         # assets/palettes.json "bartender"
IDX = {"-": 1, "+": 2, "#": 3, ".": 0}


def sal_sprite(direction, phase):
    rows = salwalk.POSES[direction][phase]
    return [[IDX[c] for c in r] for r in rows], SAL_COLS


def arrow_variants():
    px, cols = SP["arrow"]
    down = [[px[x][y] for x in range(8)] for y in range(8)]
    return {"R": (px, cols), "D": (down, cols), "U": (down[::-1], cols), "L": ([r[::-1] for r in px], cols)}


ARROWS = arrow_variants()


def blit(im, spr, x, y, mode, flip=False):
    px, cols = spr
    Wd, Ht = im.size
    for j, row in enumerate(px):
        for i, v in enumerate(row[::-1] if flip else row):
            if v == 0:
                continue
            X, Y = x + i, y + j
            if 0 <= X < Wd and 0 <= Y < Ht:
                im.putpixel((X, Y), cols[v - 1] if mode == "cgb" else (DMG_OBJ[v],) * 3)


# ---- the world pictures ----------------------------------------------------------------------------------------------------------------------------------
def world_rgb(w, mode):
    im = Image.new("RGB", (W2.PW, W2.PH))
    cache = {}
    for cy in range(W2.CH):
        for cx in range(W2.CW):
            name = w.pal[cy][cx]
            if name not in cache:
                cache[name] = pal.get(name)
            cols = cache[name]
            for j in range(8):
                row = w.px[cy * 8 + j]
                for i in range(8):
                    v = row[cx * 8 + i]
                    im.putpixel((cx * 8 + i, cy * 8 + j), cols[v] if mode == "cgb" else (pal.DMG_SHADE[v],) * 3)
    return im


EARLY_OPEN = {"town", "saloon", "stadium"}
LATE = W2.WORLD
EARLY = W2.with_fog(W2.WORLD, EARLY_OPEN)
IMG = {}


def img(state, mode):
    k = (state, mode)
    if k not in IMG:
        IMG[k] = world_rgb(LATE if state == "late" else EARLY, mode)
    return IMG[k]


# ---- text banner (the name tag): glyphs of the game's own tiles ------------------------------------------------------------------------------------------
GLYPHS = {}


def _load_glyphs():
    for f in ("bar.txt", "story.txt"):
        name, rows = None, []
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
TAG = {"saloon": "CH1 THE SALOON", "stadium": "CH2 THE STADIUM", "lodge": "CH3 LUMBER LODGE", "bistro": "CH4 THE BISTRO",
       "igloo": "CH5 THE IGLOO", "factory": "CH6 ROBOT FACTORY", "cow": "CH7 THE CHROME COW", "tea": "CH8 THE TEAHOUSE",
       "zoo": "CH9 THE JUNGLE ZOO", "space": "CH10 SPACE LOUNGE", "town": "FESTIVAL SQUARE"}


def glyph(ch):
    if ch == " ":
        return GLYPHS["hud_blank"]
    return GLYPHS.get("glyph_" + PUNCT.get(ch, ch))


_p = Image.open(SPR / "map_bg_only_indexed.png").getpalette()
TAG_COLS = [tuple(_p[i * 3:i * 3 + 3]) for i in range(4)]            # BG palette 0 of the v14 map, as the name tag uses it


def banner(im, text, y, mode):
    for cx in range(20):
        g = glyph(text[cx - 1]) if 1 <= cx <= len(text) else GLYPHS["hud_blank"]
        for j in range(8):
            for i in range(8):
                Y = y + j
                if 0 <= Y < im.height:
                    v = g[j][i]
                    im.putpixel((cx * 8 + i, Y), TAG_COLS[v] if mode == "cgb" else (pal.DMG_SHADE[v],) * 3)


# ---- screens -------------------------------------------------------------------------------------------------------------------------------------------------
def clampcam(x, y):
    return max(0, min(W2.PW - 160, x)), max(0, min(W2.PH - 144, y))


def sal_top_left(feet):
    return feet[0] - 8, feet[1] - 24


def frame(state, mode, cam, feet=None, direction="D", phase="stand", here=None, tick=0, text=None, text_y=0, revealed=None, peek=(), bang=False, arrows=True):
    full = img(state, mode)
    cx, cy = cam
    im = full.crop((cx, cy, cx + 160, cy + 144))
    for name, (sx, sy) in W2.STOPS.items():
        if revealed is not None and name not in revealed:
            continue
        blit(im, SP["dot_open"], sx - 4 - cx, sy - 8 - cy, mode)
    for name in peek:
        sx, sy = W2.STOPS[name]
        blit(im, SP["dot_locked"], sx - 4 - cx, sy - 8 - cy, mode)
    if revealed is None or "space" in revealed:
        ux, uy = W2.VENUES["space"][1][0] * 8 + 62, W2.VENUES["space"][1][1] * 8 + 6 + (1 if (tick // 24) % 2 else 0)
        blit(im, SP["ufo"], ux - cx, uy - cy, mode)
    if bang:
        sx, sy = W2.STOPS["town"]
        blit(im, SP["bang"], sx - 4 - cx, sy - 36 - cy, mode)
    if feet is not None:
        x, y = sal_top_left(feet)
        flip = direction == "L"
        spr = sal_sprite("R" if direction == "L" else direction, phase)
        blit(im, spr, x - cx, y - cy, mode, flip=flip)
        if here and arrows:
            nudge = (tick // 12) % 2
            for b in W2.NEIGH[here]:
                if revealed is not None and b not in revealed:
                    continue
                d = W2.exit_dir(here, b)
                ax, ay = {"R": (x + 18 + nudge, y + 8), "L": (x - 10 - nudge, y + 8), "U": (x + 4, y - 9 - nudge), "D": (x + 4, y + 25 + nudge)}[d]
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


def view_cam(stop, bias=(0, 0)):
    sx, sy = W2.STOPS[stop]
    return clampcam(sx - 80 + bias[0], sy - 12 - 72 + bias[1])
