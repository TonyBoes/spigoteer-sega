"""The INTEGRATED story map (stage 1 proposal, nothing imported to assets/): the A5 layout (SMAP_LOG=v1 logs, bridges with raised sides, falls seam fix) with every
approved piece pasted over it, in both data sets (W.WORLD = Color, W.WORLD_DMG = DMG; dark or light water by env SMAP_WATERDMG).

Run dump_scenes.py first (scenes/*.json) and the A5 scratch generators (smap_layout_a5/mk_src.py and mk_a5.py: they write the untracked scratch src/).
Env read here: SMAP_BROKEN=1 gives the fountain's broken state (default: working), SMAP_WATERDMG=light (DMG data set only).
Pieces, at the commits the brief names:
  stadium   BLEND (8950c018): scene + the stadium's own map edits (smap_stadium/src/edits.py: walkway and gate, the five grass cells) and palettes STADIUM / PARK with the map grass
            as index 0 (smap_stadium/src/after.py), the blank cells of the piece left to the map's ground
  igloo     option 1 at (50, 5)             airbase 4i (jet nudged) at (6, 36): three cells west of the piece's dump position, as the animation import has it
  milk bar  final (sign B raised + left, building on `base`) at (49, 47), the pasture instead of the hay field, the tea cell (34, 59) on tea@g
  town      fountain round 3 + awning ink border (smap_fountain/src/v_town_fx.py); broken or working state by env
Read-only: nothing is written except what the callers save."""
from collections import Counter
import importlib.util
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
PROP = ROOT / "docs/dev/proposals"
os.environ["SMAP_LAYOUT"] = "lay_A5"
os.environ["SMAP_FOG"] = "none"
os.environ["SMAP_LOG"] = "v1"
os.environ.setdefault("SMAP_BRIDGE", "new")
sys.path.insert(0, str(PROP / "smap_layout_a5/src"))
sys.path.append(str(ROOT / "tools/smap_world"))
sys.path.append(str(HERE))
sys.path.append(str(PROP / "smap_fountain/src"))
import decor  # noqa: E402
import lay_A5 as lay  # noqa: E402

lay.FIELDS = []
lay.SCENERY = [s for s in lay.SCENERY if s[0] is not decor.HAY]
V = dict(lay.VENUES)
for k in ("cow", "stadium", "igloo", "space"):
    V[k] = ("anim_stub", V[k][1])
V["town"] = ("v_town_fx", V["town"][1])
lay.VENUES = V
lay.RANGES = []                                             # the three hatched placeholder boxes along the top: the round 3 range pieces are pasted instead (scenes/range_*.json)

import pal as PAL  # noqa: E402
import world2 as W  # noqa: E402

CW, CH = W.CW, W.CH
BROKEN = os.environ.get("SMAP_BROKEN") == "1"
LIGHT = os.environ.get("SMAP_WATERDMG") == "light"
SCENES = {}
AT_OVERRIDE = {"mountain": (int(os.environ.get("SMAP_AIRBASE_X", "4")), int(os.environ.get("SMAP_AIRBASE_Y", "34")))}
WORLDS = (W.WORLD, W.WORLD_DMG)
CHOICES = []                                                # every cell where two pieces wanted the same cell: (cell, what was there, what won, why)


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _snap():
    w = W.WORLD
    return {(cx, cy): (bytes(w.px[cy * 8 + y][cx * 8 + x] for y in range(8) for x in range(8)), w.pal[cy][cx]) for cy in range(CH) for cx in range(CW)}


KINDS = {}
STEPS = []                                                  # (name, set of cells it changed)
_last = [_snap()]


def _step(name):
    now = _snap()
    ch = {c for c in now if now[c] != _last[0][c]}
    for n0, c0 in STEPS:
        for c in sorted(ch & c0):
            CHOICES.append((c, n0, name))
    STEPS.append((name, ch))
    KINDS[name] = dict(Counter(W.WORLD.kind[cy][cx] for (cx, cy) in ch))      # what the cells were before the paste: ground / decor / road / venue / ...
    _last[0] = now


def paste(name):
    if os.environ.get("SMAP_NOPASTE"):
        return None
    s = json.load(open(HERE / "scenes" / f"{name}.json"))
    SCENES[name] = s
    for n, col in s["colors"].items():
        PAL.RGB.setdefault(n, [tuple(c) for c in col])
    ax, ay = AT_OVERRIDE.get(name, s["at"])
    if name == "mountain":
        s["mode"] = os.environ.get("SMAP_AIRBASE_MODE", "nonblank")
    s["at_used"] = [ax, ay]
    for key, (rows, p) in s["frames"][0].items():
        i, j = map(int, key.split(","))
        if s["mode"] == "nonblank" and all(set(r) == {"0"} for r in rows):
            continue
        cx, cy = ax + i, ay + j
        for w in WORLDS:
            old = w.pal[cy][cx]
            for y in range(8):
                for x in range(8):
                    w.px[cy * 8 + y][cx * 8 + x] = int(rows[y][x])
            w.pal[cy][cx] = p
    _step(name)
    return s


# the stadium's map palettes: index 0 = the map grass, the field grass = the map grass (smap_stadium/src/after.py)
g0 = PAL.RGB["grass"][0]
PAL.RGB["stadium"] = [g0] + list(PAL.RGB["stadium"][1:])
paste("stadium")
PAL.RGB["park"] = [g0, PAL.RGB["grass"][1]] + list(PAL.RGB["park"][2:])
for _n in ("igloo", "mountain", "cow", "range_a", "range_b", "range_c"):
    paste(_n)
_ed = _load(PROP / "smap_stadium/src/edits.py", "stadium_edits")
_ed.edit(W)
_ed.edit_grass_cells(W)
_step("stadium_edits")
for w in WORLDS:                                            # milk bar: the tea house cell next to the lot's lawn joins tea@g (Color palette only, DMG pixels unchanged)
    w.pal[59][34] = "tea@g"
_step("tea_cell")


def grid(dmg=False):
    w = W.WORLD_DMG if dmg else W.WORLD
    return [row[:] for row in w.px], [row[:] for row in w.pal]


def render(cgb, box=None, scale=1):
    """PIL image of the world (or the cell box (x0, y0, x1, y1) of it)"""
    from PIL import Image
    w = W.WORLD if cgb else W.WORLD_DMG
    x0, y0, x1, y1 = box or (0, 0, CW, CH)
    im = Image.new("RGB", ((x1 - x0) * 8, (y1 - y0) * 8))
    for cy in range(y0, y1):
        for cx in range(x0, x1):
            cols = PAL.get(W.MERGE.get(w.pal[cy][cx], w.pal[cy][cx])) if cgb else None
            for y in range(8):
                for x in range(8):
                    v = w.px[cy * 8 + y][cx * 8 + x]
                    im.putpixel(((cx - x0) * 8 + x, (cy - y0) * 8 + y), tuple(cols[v]) if cols else (PAL.DMG_SHADE[v],) * 3)
    return im.resize((im.width * scale, im.height * scale), Image.NEAREST) if scale != 1 else im
