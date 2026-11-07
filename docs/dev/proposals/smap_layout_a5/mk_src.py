#!/usr/bin/env python3
"""Builds the scratch copies the layout proposals render with (never touches assets/ or tools/):

    src/world2.py    tools/smap_world/world2.py with its layout data (cells, venues, roads, biomes, scenery, legs) read from a layout module
                     (env SMAP_LAYOUT, default lay_today); the code (build, fog, zones) is the original, byte for byte
    src/lay_today.py today's layout data, cut verbatim out of the original file
    src/gen_smap_world.py  tools/gen_smap_world.py with the two literals SMAPW_CW / SMAPW_CH read from the world

Run:  python3 -I docs/dev/proposals/smap_layout/mk_src.py   (from the repo root)"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
SRC = HERE / "src"
SRC.mkdir(exist_ok=True)
t = (ROOT / "tools" / "smap_world" / "world2.py").read_text()


def cut(text, a, b):
    i = text.index(a)
    j = text.index(b, i)
    return text[i:j]


venues = cut(t, "# ---- venues:", "# ---- roads:")
roads = cut(t, "# ---- roads:", "# ---- biomes:")
biomes = cut(t, "# ---- biomes:", "BIOME_PAL = ")
scen = cut(t, "# ---- scenery placed by hand", "# ---- the stops and the paths")
legs = cut(t, "# junctions (feet positions)", "NEIGH = {}")
today = ('"""Today\'s layout (tools/smap_world/world2.py, verbatim data): the control the proposals are measured against."""\n'
         "import decor\n\nCW, CH = 64, 48\n\n" + venues + roads + biomes + scen + "\n"
         "def legs(STOPS):\n" + "".join("    " + ln + "\n" if ln.strip() else "\n" for ln in legs.splitlines()) + "    return LEGS\n"
         "\nTOWN_ZONE = (18, 17, 37, 29)\nMERGE_EXTRA = {}\n")
(SRC / "lay_today.py").write_text(today)

w = t.replace("CW, CH = 64, 48", "import os\nlay = importlib.import_module(os.environ.get('SMAP_LAYOUT', 'lay_today'))\nCW, CH = lay.CW, lay.CH", 1)
w = w.replace(venues + roads + biomes,
              "VENUES, ORDER, STOP_LOCAL_X, ROAD_ROW = lay.VENUES, lay.ORDER, lay.STOP_LOCAL_X, lay.ROAD_ROW\n"
              "ROAD_BOXES, BIOMES, BITES = lay.ROAD_BOXES, lay.BIOMES, lay.BITES\n", 1)
w = w.replace(scen, "SCENERY, APRON, FIELDS = lay.SCENERY, lay.APRON, lay.FIELDS\n\n", 1)
w = w.replace(legs, "LEGS = lay.legs(STOPS)\n", 1)
w = w.replace("tx0, ty0, tx1, ty1 = 18, 17, 37, 29", "tx0, ty0, tx1, ty1 = lay.TOWN_ZONE", 1)
(SRC / "world2.py").write_text(w)

g = (ROOT / "tools" / "gen_smap_world.py").read_text()
g = g.replace('f"#define SMAPW_CW 64", f"#define SMAPW_CH 48"', 'f"#define SMAPW_CW {W.CW}", f"#define SMAPW_CH {W.CH}"', 1)
g = g.replace('ROOT = Path(__file__).resolve().parent.parent\nsys.path.append(str(ROOT / "tools" / "smap_world"))',
              'ROOT = Path(__file__).resolve().parents[5]\nsys.path.insert(0, str(Path(__file__).resolve().parent))\nsys.path.append(str(ROOT / "tools" / "smap_world"))', 1)
(SRC / "gen_smap_world.py").write_text(g)
print("wrote", SRC)
