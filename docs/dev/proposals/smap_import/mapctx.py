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
# THE DEFAULT MAP is the owner's pick A' (Q115 a, Q117 a): the four long bends (0,11) (0,45) (37,28) (63,11) at r32, every other bend at r24 with the art trims (factory 0 px, lodge 11, cow 1),
# all extras (desert peaks, cacti, spill, bamboo, tree clusters), big mountain A, the stadium bush at x 40, light water.  Each switch still overrides: SMAP_CURVE=none gives the r8 corners,
# SMAP_CURVE=24 uniform r24, SMAP_BIG=none or B, SMAP_CURVE_TRIM=0, SMAP_RADII=... any set.
if os.environ.get("SMAP_BEFORE_1C") != "1":
    os.environ.setdefault("SMAP_BIG", "B")
    os.environ.setdefault("SMAP_STADIUM_BUSH_X", "40")
    os.environ.setdefault("SMAP_CURVE_TRIM", "1")
    if "SMAP_CURVE" not in os.environ:
        os.environ["SMAP_CURVE"] = "radii"
        os.environ.setdefault("SMAP_RADII", "0,29:24!;0,63:24!;37,46:24!;50,28:24!;50,46:24!;63,29:24!;63,45:24!;63,63:24!;0,11:32!;0,45:32!;37,28:32!;63,11:32!")
sys.path.insert(0, str(PROP / "smap_layout_a5/src"))
sys.path.append(str(ROOT / "tools/smap_world"))
sys.path.append(str(HERE))
sys.path.append(str(PROP / "smap_fountain/src"))
import decor  # noqa: E402
import lay_A5 as lay  # noqa: E402

lay.FIELDS = []
lay.SCENERY = [s for s in lay.SCENERY if s[0] is not decor.HAY]
BEFORE_1C = os.environ.get("SMAP_BEFORE_1C") == "1"         # the stage 1b state (square road corners, range A, uniform peaks): for the before | after renders
if not BEFORE_1C:
    # stage 1c: the round tree-bush at cell (2, 13) moves one cell east (its pixels sat in the ground cell the inner road corner at the stadium's gate road rounds into)
    lay.SCENERY = [(p, int(os.environ.get("SMAP_STADIUM_BUSH_X", "24")), 104) if (p is decor.BUSH and x == 16 and y == 104) else (p, x, y) for (p, x, y) in lay.SCENERY]
    # range A removed: its ground is the lawn round it; five of the map's own pines stand there, about the density of the lawn east of the bistro
    lay.SCENERY = lay.SCENERY + [(decor.PINE, x * 8, y * 8) for (x, y) in [(18, 1), (22, 0), (25, 2), (28, 0), (31, 1)]]
if not BEFORE_1C and os.environ.get("SMAP_NO_CLUSTERS") != "1":
    import clusters                                         # overlapping tree clusters and the zoo bamboo (clusters.py); SMAP_CLUSTERS=trees|bamboo limits it
    _w = os.environ.get("SMAP_CLUSTERS", "trees,bamboo")
    CLUSTER_MISS = clusters.apply(lay, trees="trees" in _w, bamboo="bamboo" in _w)
V = dict(lay.VENUES)
for k in ("cow", "stadium", "igloo", "space"):
    V[k] = ("anim_stub", V[k][1])
V["town"] = ("v_town_fx", V["town"][1])
lay.VENUES = V
lay.RANGES = []                                             # the three hatched placeholder boxes along the top: the round 3 range pieces are pasted instead (scenes/range_*.json)

SEAMS = not BEFORE_1C and os.environ.get("SMAP_NO_SEAMS") != "1"
if SEAMS:                                                   # irregular ground seams (seam_edges.py), typed before the world is built
    import seam_edges
    seam_edges.apply(lay)

DESERT = not BEFORE_1C and os.environ.get("SMAP_NO_DESERT") != "1"
if DESERT:                                                  # desert spills across the road (desert_extras.py): ground cells, typed before the world is built
    import desert_extras
    desert_extras.apply_grid(lay)

if os.environ.get("SMAP_PRE_WORLD"):                        # owner proposals 11-08 (docs/dev/proposals/smap_owner_1108): a module whose apply(lay, decor) edits the layout before the world is built; off by default
    importlib.import_module(os.environ["SMAP_PRE_WORLD"]).apply(lay, decor)

import pal as PAL  # noqa: E402
import world2 as W  # noqa: E402

CW, CH = W.CW, W.CH
BROKEN = os.environ.get("SMAP_BROKEN") == "1"
LIGHT = os.environ.get("SMAP_WATERDMG", "light") != "dark"       # light DMG water is the default (owner Q101, 11-06)
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
for _n in ("igloo", "mountain", "cow") + (("range_a", "range_b", "range_c") if BEFORE_1C else ("range_b2", "range_c2")):
    paste(_n)
_ed = _load(PROP / "smap_stadium/src/edits.py", "stadium_edits")
_ed.edit(W)
_ed.edit_grass_cells(W)
_step("stadium_edits")
if not BEFORE_1C:
    import snowfield
    SNOW_CHANGES = snowfield.apply(W)                       # one continuous snowfield under ranges B and C
    _step("snowfield")
BIGKEY = os.environ.get("SMAP_BIG", "none")                  # the big mountain proposal: A (top right) or B (head of the river); default none (the owner picks)
if BIGKEY in ("A", "B"):
    import big_mountain
    BIG_TOUCHED = big_mountain.apply(W, WORLDS, BIGKEY)
    _step("big_mountain")
if DESERT:                                                  # small desert peaks and cacti (hand-typed in desert_extras.py); the cactus palette is the map grass' colours on the desert sand
    PAL.RGB["cactus"] = [PAL.RGB["saloon"][0]] + list(PAL.RGB["grass"][1:])
    DESERT_PLACED = desert_extras.apply_world(W, WORLDS, pieces=tuple(os.environ.get("SMAP_DESERT_PIECES", "peaks,cacti").split(",")),
                                              cactus_pal=os.environ.get("SMAP_CACTUS_PAL", "cactus"))
    _step("desert_extras")
if not BEFORE_1C and os.environ.get("SMAP_NO_ROADS") != "1":
    import roads_round
    CURVE = os.environ.get("SMAP_CURVE")                   # step 1 of the smooth bends: "16" or "24" lays the smooth bends of that outer radius instead of the r8 ones (not the default)
    if CURVE in ("16", "24", "32", "40", "48", "56", "80", "96", "120", "fit", "mix", "radii"):
        import roads_smooth
        ROAD_CHANGES = []
        if CURVE == "radii":                                # SMAP_RADII="x,y:r;x,y:r": those bends at r (or the next smaller that fits), the others keep r16 (bisecting the fit map)
            _rad = {}
            for _it in os.environ["SMAP_RADII"].split(";"):
                _k, _r = _it.split(":")
                _x, _y = (int(v) for v in _k.split(","))
                _rad[(_x, _y)] = [int(_r[:-1])] if _r.endswith("!") else [r for r in (120, 96, 80, 56, 48, 40, 32, 24, 16) if r <= int(_r)]       # "24!" = exactly r24 or the bend stays r8 (no r16)
            CURVE_LAID, CURVE_SKIPPED, CURVE_TRIMMED = roads_smooth.apply(W, PAL, 16, radii=_rad)
        elif CURVE == "mix":                                  # owner Q115 follow-up: r40 everywhere it fits (then 32, 24, 16), the long sweeps (0,45) r96 and (37,28) r120
            _mix = {(0, 45): [96, 80, 56, 48, 40, 32, 24, 16], (37, 28): [120, 96, 80, 56, 48, 40, 32, 24, 16]}
            _dflt = [40, 32, 24, 16]
            _rad = {(x, y): _mix.get((x, y), _dflt) for (x, y) in [(0, 11), (0, 29), (0, 45), (0, 63), (37, 28), (37, 46), (50, 28), (50, 46), (63, 11), (63, 29), (63, 45), (63, 63)]}
            CURVE_LAID, CURVE_SKIPPED, CURVE_TRIMMED = roads_smooth.apply(W, PAL, 40, radii=_rad)
        else:
            CURVE_LAID, CURVE_SKIPPED, CURVE_TRIMMED = roads_smooth.apply(W, PAL, CURVE if CURVE == "fit" else int(CURVE))
    else:
        ROAD_CHANGES = roads_round.apply(W, PAL)           # rounded outer and inner corners of the road loops (hand-typed pieces in roads_round.py)
    _step("road_corners")
for w in WORLDS:                                            # milk bar: the tea house cell next to the lot's lawn joins tea@g (Color palette only, DMG pixels unchanged)
    w.pal[59][34] = "tea@g"
_step("tea_cell")
if not BEFORE_1C:                                           # stage 1c, rounded corners: a tea cell with no index 0 pixel looks the same on tea@g: the tea house's wall and roof cells join it,
    for _y in range(CH):                                    # which frees the `tea` palette in the south middle windows (the rounded corners there need one more)
        for _x in range(CW):
            if W.WORLD.pal[_y][_x] == "tea" and all(W.WORLD.px[_y * 8 + j][_x * 8 + i] != 0 for j in range(8) for i in range(8)):
                W.WORLD.pal[_y][_x] = "tea@g"
    _step("tea_cells_to_tea_g")


# smap_venue_redesign3/src/common.py (imported later through big_mountain -> range_peaks) puts the pre-blend PARK back (d4d8e4 chalk, 68b048); the approved BLEND is the map grass as index 0
# and the map's field grass as index 1, so the stadium's pads and the right-hand wedge vanish on Color (owner Q110 / Q112): set it again after every import has run
PAL.RGB["park"] = [g0, PAL.RGB["grass"][1]] + list(PAL.RGB["park"][2:])


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


# stage 1l: the approved animation art the map did not carry (new static tiles of smap_anim/items.py: water glints, the six low logs, lodge smoke cells, cow tails), pasted exactly as approved
if os.environ.get("SMAP_NO_ANIM_STATIC") != "1" and not os.environ.get("SMAP_NOPASTE"):
    import anim_static
    ANIM_STATIC_CELLS = anim_static.apply(W, WORLDS, sys.modules[__name__])
    _step("anim_static")

# the remaining Color pads (pads.py: the bistro sign, the factory yard's east edge, mountain B's snow fringe); Color data set only
if not BEFORE_1C and os.environ.get("SMAP_NO_PADS") != "1" and not os.environ.get("SMAP_NOPASTE"):
    import pads
    PADS_CHANGED = pads.apply(W, PAL)
    _step("pads")
