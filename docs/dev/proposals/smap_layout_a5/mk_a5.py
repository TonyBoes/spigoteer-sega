"""Makes src/world2.py, src/gen_smap_world.py and src/pal.py for layouts A2 and A3 from the scratch copies that mk_src.py writes (run mk_src.py first).
All changes are placement or palette assignment, no pixel is drawn:
 1. a biome 'townsq' (A2 only: the town square, palette TOWN1, today's two cobble tiles in a chequer)
 2. a cell of a venue picture that is all index 0 takes the palette of the ground under it (the tile is the same all-zero tile)
 3. A3: in the stadium, the bistro and the tea house, a cell that has margin pixels (index 0 outside the building) and no index 0 inside the art takes the venue's
    palette with the ground colour as index 0 ('stadium@g', 'bistro@g', 'tea@g'): no pixel changes, nothing visible is recoloured
 4. SMAP_FOG=none: no cloud at all (the generator's empty arrays get one dummy element so that the ROM builds); SMAP_FOG=one: one cloud palette instead of three
 5. A3: the three variant palettes take the three slots of the cloud palettes in the generator's palette list (18 in all, the engine's table size)"""
from pathlib import Path

HERE = Path(__file__).resolve().parent
LAYS = '("lay_A2", "lay_A3", "lay_A4", "lay_A5")'
p = HERE / "src" / "world2.py"
s = p.read_text()
s = s.replace('"moss": "tea", "farmcow": "cow"}', '"moss": "tea", "farmcow": "cow", "townsq": "town1"}', 1)
s = s.replace('"moss": "moss", "farmcow": "farm"}', '"moss": "moss", "farmcow": "farm", "townsq": "grass"}', 1)
s = s.replace('''                if b == "forest":
                    v = vs[1] if h % 4 else vs[3]
''', '''                if b == "forest":
                    v = vs[1] if h % 4 else vs[3]
                if b == "townsq":
                    v = COBBLE if (cx + cy) % 2 == 0 else COBBLE_B
''', 1)
s = s.replace('''        # venues: paste the pictures (they override ground); roads are drawn after, but never over a venue
        for name, (modname, (cx0, cy0)) in VENUES.items():
            c = importlib.import_module(modname).build(dmg=self.dmg)
            rows = c.out()''', '''        # venues: paste the pictures (they override ground); roads are drawn after, but never over a venue
        for name, (modname, (cx0, cy0)) in VENUES.items():
            c = importlib.import_module(modname).build(dmg=self.dmg)
            rows = c.out()
            outside = outside_cells(rows) if (os.environ.get("SMAP_LAYOUT") in ("lay_A3", "lay_A4", "lay_A5") and name in ("stadium", "bistro", "tea")) else set()''', 1)
s = s.replace('''                    pal = MERGE.get(pal, pal)
                    assert (cx0 + i, cy0 + j) not in self.roads, (name, cx0 + i, cy0 + j)''', '''                    pal = MERGE.get(pal, pal)
                    if os.environ.get("SMAP_LAYOUT") in ''' + LAYS + ''' and all(set(r) == {"0"} for r in cell):
                        pal = BIOME_PAL[self.biome[cy0 + j][cx0 + i]]          # a blank cell of a picture is the ground under it
                    elif outside:
                        pads = [(i * 8 + a, j * 8 + k) for k in range(8) for a in range(8) if (i * 8 + a, j * 8 + k) in outside]
                        inner = {rows[y][x] for y in range(j * 8, j * 8 + 8) for x in range(i * 8, i * 8 + 8) if (x, y) not in outside}
                        if pads and "0" not in inner:
                            assert BIOME_PAL[self.biome[cy0 + j][cx0 + i]] == "grass", (name, i, j)
                            pal = pal + "@g"                                     # the venue's palette with the ground colour as index 0
                    assert (cx0 + i, cy0 + j) not in self.roads, (name, cx0 + i, cy0 + j)''', 1)
s = s.replace('''def zone_of_cell(w, cx, cy):''', '''def outside_cells(rows):
    """the index 0 pixels of a picture that are reachable from its edge through index 0: the margin round the building"""
    h, w = len(rows), len(rows[0])
    seen = set()
    st = [(x, y) for x in range(w) for y in (0, h - 1)] + [(x, y) for y in range(h) for x in (0, w - 1)]
    st = [q for q in st if rows[q[1]][q[0]] == "0"]
    while st:
        x, y = st.pop()
        if (x, y) in seen:
            continue
        seen.add((x, y))
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            a, b = x + dx, y + dy
            if 0 <= a < w and 0 <= b < h and rows[b][a] == "0" and (a, b) not in seen:
                st.append((a, b))
    return seen


def zone_of_cell(w, cx, cy):''', 1)
s = s.replace('''    k = w.kind[cy][cx]
    if k in VENUES:
        return k''', '''    if os.environ.get("SMAP_FOG") == "none":
        return "town"
    k = w.kind[cy][cx]
    if k in VENUES:
        return k''', 1)
s = s.replace('''def with_fog(w, revealed):''', '''if os.environ.get("SMAP_FOG") == "one":
    FOGCLASS = {}


def with_fog(w, revealed):''', 1)
p.write_text(s)

# ---- A4: water, bridges, the log yard, placeholder ranges ----------------------------------------------------------------------------------------------
s = s.replace("import decor\n", "import decor\nimport a5art as a4art\nGROUND['waterflat'] = [a4art.WF]\n", 1)
s = s.replace('"townsq": "town1"}', '"townsq": "town1", "water": "water", "logyard": "lodge"}', 1)
s = s.replace('"townsq": "grass"}', '"townsq": "grass", "water": "waterflat", "logyard": "grass"}', 1)
s = s.replace("""            self.ground_pal[cy][cx] = "town1"
        # the road cells""", """            self.ground_pal[cy][cx] = "town1"
        for (cx, cy) in sorted(getattr(lay, "WATER", ())):
            wp = getattr(lay, "WATER_PAL", {}).get((cx, cy), "water")                    # A5: the river in the snow takes the snow's palette (bank = snow)
            self.set_tile(cx, cy, a4art.water_tile5(lay.WATER, cx, cy, CW, CH, dmg=self.dmg, light=WATERLIGHT, variants=getattr(lay, "VARIANTS", False),
                                                    special=getattr(lay, "SPECIAL_WATER", None)), wp, "ground")
            self.ground_pal[cy][cx] = wp
            self.biome[cy][cx] = "water"
        # the road cells""", 1)
s = s.replace("""                            self.px[cy * 8 + j][cx * 8 + i] = 0
""", """                            self.px[cy * 8 + j][cx * 8 + i] = (1 if WATERLIGHT and self.dmg else 2) if pal == "water" else 0
""", 1)
s = s.replace("""        # roads
        for (cx, cy) in sorted(self.roads):""", """        for (rx, ry, rw, rh, rpal, rn) in getattr(lay, "RANGES", ()):          # placeholder mountain ranges (boxes, not art)
            rows = a4art.Box(rw, rh, rpal, rn).out()
            for j in range(rh):
                for i in range(rw):
                    assert self.kind[ry + j][rx + i] in ("ground", "decor") and (rx + i, ry + j) not in self.roads, ("range", rx + i, ry + j)
                    self.set_tile(rx + i, ry + j, tuple(rows[j * 8 + k][i * 8:i * 8 + 8] for k in range(8)), rpal, "decor")
        # roads
        for (cx, cy) in sorted(self.roads):""", 1)
s = s.replace("""            self.set_tile(cx, cy, self.road_tile(cx, cy, n, e, s, w, nw, ne, se, sw), "town1", "road")
""", """            self.set_tile(cx, cy, self.road_tile(cx, cy, n, e, s, w, nw, ne, se, sw), "town1", "road")
        for (cx, cy), t in getattr(lay, "BRIDGE_CELLS", {}).items():
            self.set_tile(cx, cy, a4art.BRIDGE_TILES[t], "town1", "road")
""", 1)
s = s.replace("""    def put_decor(self, pc, x, y):
        pal, rows = pc""", """    def put_decor(self, pc, x, y):
        if WATERLIGHT and self.dmg:
            pc = a4art.LIGHT_PIECE.get(id(pc), pc)                    # DMG light water: the logs typed for it
        pal, rows = pc""", 1)
s = s.replace("""CW, CH = lay.CW, lay.CH
""", """CW, CH = lay.CW, lay.CH
WATERLIGHT = os.environ.get("SMAP_WATERDMG", "light") != "dark"            # DMG data set only: the light water is the default (owner Q101); SMAP_WATERDMG=dark gives the old dark water
if os.environ.get("SMAP_LAYOUT") == "lay_A5":
    GROUND["yard"] = [GROUND["grass"][0], a4art.GRAVEL]            # the factory yard: packed earth with gravel
""", 1)
p.write_text(s)

g = HERE / "src" / "gen_smap_world.py"
t = g.read_text()
t = t.replace('''    body = []
    for i in range(0, len(vals), per):''', '''    vals = list(vals) or [0]                      # (an empty array does not compile: one dummy element)
    body = []
    for i in range(0, len(vals), per):''', 1)
t = t.replace('m.fogint, 4, 4', '(m.fogint or [0, 0, 0, 0]), 4, 4', 1)
t = t.replace('FOG_PAL0 = 15', """FOG_PAL0 = 15
import os as _os
if _os.environ.get("SMAP_LAYOUT") == "lay_A3":
    PAL_NAMES[15:18] = ["stadium@g", "bistro@g", "tea@g"]      # the cloud's three slots hold the three venue palettes with the ground as index 0
if _os.environ.get("SMAP_LAYOUT") == "lay_A4":
    PAL_NAMES[15:18] = ["water", "bistro@g", "tea@g"]          # ... and in A4 the first of them is the water (the stadium is a placeholder)
if _os.environ.get("SMAP_LAYOUT") == "lay_A5":                 # A5: 18 again.  The two reserved slots (the lounge's base, the ballpark's stadium) hold the town's two edge palettes
    PAL_NAMES[:] = ["town1@g", "bistro", "cow", "factory", "farm", "grass", "igloo", "lodge", "saloon", "stadium", "tea", "town1", "town4", "town5", "zoo",
                    "water", "bistro@g", "tea@g"]
    if _os.environ.get("SMAP_GOLD") == "own":
        PAL_NAMES[9] = 'town5@g'""", 1)
g.write_text(t)

q = HERE / "src" / "pal.py"
base = (HERE / ".." / ".." / ".." / ".." / "tools" / "smap_world" / "pal.py").resolve().read_text()
base += """

# ---- scratch additions: a venue's palette with the grass ground as index 0 (layout A3, A4), and the water of A4 ----
for _v in ("stadium", "bistro", "tea"):
    PALS[_v + "@g"] = [PALS["grass"][0]] + PALS[_v][1:]
    RGB[_v + "@g"] = [h(c) for c in PALS[_v + "@g"]]
PALS["water"] = ["b0d080", "e8f0d8", "5ca4d8", "2c4c78"]        # 0 grass bank, 1 foam: rim, glints and log wood, 2 water, 3 deep (log outline)
RGB["water"] = [h(c) for c in PALS["water"]]

# ---- A5 ----
import os as _o
if _o.environ.get("SMAP_LAYOUT") == "lay_A5":
    PALS["town1@g"] = [PALS["grass"][0]] + PALS["town1"][1:]            # the town's edge cells: the grass is index 0 (cream, terracotta, lilac, ink with the cream replaced)
    PALS["town5@g"] = [PALS["grass"][0]] + PALS["town5"][1:]
    PALS["factory"] = ["d0c890", "88a090", "385048", "101818"]          # re-tint: 0 packed earth (was pale grey e8e8e0), 1 steel (was blue grey), 2 dark steel, 3 ink
    if _o.environ.get("SMAP_LOG", "old") != "old":                          # the redrawn logs: the water palette's 'deep' (3) is wood brown 905830, the lodge wood (the falls' rock edge takes it too)
        PALS["water"] = PALS["water"][:3] + ["905830"]
    for _k in ("town1@g", "town5@g", "factory", "water"):
        RGB[_k] = [h(c) for c in PALS[_k]]
"""
q.write_text(base)
print("patched")
