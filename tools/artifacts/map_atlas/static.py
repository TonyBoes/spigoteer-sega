"""Map Atlas, the static half: what the map's data says, measured with the generator's own model (tools/gen_smap_world.py Model, geometry, STOP_VIEW,
WIN_V) so the numbers are the build's.  Everything here is on the finished map (unlock state 11): states 1 and 11 differ only on the fountain's 20 cells."""
import sys
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tools" / "smap_world"))
import gen_smap_world as G  # noqa: E402

W = G.W
CW, CH = G.CW, G.CH
LIM_TILES, LIM_PALS = G.POOL, 8
NAMES = {"saloon": "Saloon", "stadium": "Stadium", "lodge": "Lodge", "bistro": "Bistro", "igloo": "Igloo", "factory": "Factory", "cow": "Rodeo",
         "tea": "Teahouse", "zoo": "Zoo", "space": "Space", "town": "Town"}
VENUE_PX = {"igloo": (80, 48), "town": (96, 72), "bistro": (72, 56), "saloon": (72, 56), "tea": (96, 56), "stadium": (80, 56), "space": (112, 72),
            "cow": (80, 56), "factory": (80, 56), "lodge": (80, 64), "zoo": (112, 64)}      # tools/smap_world/v_*.py: W, H in pixels
LAND = {"grass": "Grass", "saloon": "Desert", "cactus": "Cactus", "water": "Water", "igloo": "Snow", "farm": "Farmland", "base": "Base", "stadium": "Paved",
        "bistro": "Plaza", "factory": "Yard", "zoo": "Jungle", "zoogate": "Zoo gate", "tea": "Moss", "cow": "Ranch", "lodge": "Pines", "park": "Park"}


def cam(fx, fy):
    """smap_cam_target: Sal's feet at the screen's centre (80, 84), clamped to the world (as tools/gen_smap_world.py path_windows)"""
    return min(max(fx - 80, 0), CW * 8 - 160), min(max(fy - G.SAL_Y, 0), CH * 8 - 144)


class Static:
    def __init__(self):
        self.cg, self.dm = cg, dm = G.Model(True), G.Model(False)
        self.gD, self.gC, self.pal = dm.grids[11], cg.grids[11], cg.pals[11]
        self.cntD, self.cntC = np.bincount(self.gD.ravel()), np.bincount(self.gC.ravel())
        self.shD, self.shC = self.cntD[self.gD], self.cntC[self.gC]
        self.names = list(G.PAL_NAMES)
        self.rgb = [[tuple(c) for c in W.RGB[n]] for n in self.names]
        self.stops, self.legs, self.exits, self.exit_leg = G.geometry()
        self.order = list(G.STOP_ORDER)
        self.build_pieces()
        self.build_twins()
        self.cache = {}
        self.build_positions()
        self.build_paths()

    # ---- pieces -------------------------------------------------------------------------------------------------------------------------------------
    def build_pieces(self):
        piece = np.full((CH, CW), -1, dtype=np.int32)
        self.piece_names, self.piece_kind = [], []

        def pid(name, kind):
            if name not in self.piece_names:
                self.piece_names.append(name)
                self.piece_kind.append(kind)
            return self.piece_names.index(name)
        for k, v in W.VENUES.items():
            x, y = v[1]
            w, h = VENUE_PX[k]
            piece[y:y + h // 8, x:x + w // 8] = pid(NAMES[k], "venue")
        road = np.zeros((CH, CW), dtype=bool)
        for a, b, pts in self.legs:
            for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
                n = max(abs(x1 - x0), abs(y1 - y0), 1)
                for i in range(0, n + 1, 4):
                    cx, cy = (x0 + (x1 - x0) * i // n) >> 3, (y0 + (y1 - y0) * i // n) >> 3
                    road[max(cy - 1, 0):cy + 2, max(cx - 1, 0):cx + 2] = True
        for y in range(CH):
            for x in range(CW):
                if piece[y, x] < 0:
                    if road[y, x]:
                        piece[y, x] = pid("Roads", "area")
                    else:
                        n = self.names[self.pal[y, x]]
                        piece[y, x] = pid("Land: " + LAND.get(n.split("@")[0], n), "area")
        self.piece = piece

    def build_twins(self):
        """DMG tiles that differ from another DMG tile in at most 2 of 64 pixels: the near-twins a redraw could merge"""
        s = np.array([list(b) for b in self.dm.sigs], dtype=np.uint8)
        n = len(s)
        self.twin_of = np.full(n, -1, dtype=np.int32)
        self.twin_d = np.full(n, 64, dtype=np.int32)
        for i in range(n):
            d = (s != s[i]).sum(axis=1)
            d[i] = 99
            j = int(d.argmin())
            self.twin_d[i] = d[j]
            if d[j] <= 2:
                self.twin_of[i] = j
        self.twin_cell = self.twin_of[self.gD] >= 0

    # ---- views ----------------------------------------------------------------------------------------------------------------------------------------
    def view(self, cx, cy):
        """the camera at pixel (cx, cy): DMG tiles in the padded window the path rule counts (1 cell on every side, limit 176), in the view's own cells;
        BG palettes in the view's cells (limit 8) and in the padded window; Color tile ids in the padded window"""
        key = (cx >> 3, (cx + 159) >> 3, cy >> 3, (cy + 143) >> 3)
        v = self.cache.get(key)
        if v is None:
            c0, c1, r0, r1 = key
            p0, p1, q0, q1 = max(c0 - 1, 0), min(c1 + 1, CW - 1), max(r0 - 1, 0), min(r1 + 1, CH - 1)
            pv = self.pal[r0:r1 + 1, c0:c1 + 1]
            pp = self.pal[q0:q1 + 1, p0:p1 + 1]
            v = dict(win=(p0, p1, q0, q1), view=key,
                     tiles_pad=len(np.unique(self.gD[q0:q1 + 1, p0:p1 + 1])), tiles_view=len(np.unique(self.gD[r0:r1 + 1, c0:c1 + 1])),
                     ids_pad=len(np.unique(self.gC[q0:q1 + 1, p0:p1 + 1])),
                     pals_view=sorted(set(int(a) for a in np.unique(pv))), pals_pad=len(np.unique(pp)),
                     palcells=Counter(int(a) for a in pv.ravel()))
            self.cache[key] = v
        return v

    def build_positions(self):
        """every feet cell of the map: the view the camera shows with Sal there (the cell's centre)"""
        self.pos = {}
        for y in range(CH):
            for x in range(CW):
                cx, cy = cam(x * 8 + 4, y * 8 + 4)
                self.pos[(x, y)] = self.view(cx, cy)

    def sample_leg(self, pts):
        out = []
        for k in range(len(pts) - 1):
            (x0, y0), (x1, y1) = pts[k], pts[k + 1]
            n = max(abs(x1 - x0), abs(y1 - y0), 1)
            for i in range(n + (k == len(pts) - 2)):
                out.append((x0 + (x1 - x0) * i // n, y0 + (y1 - y0) * i // n))
        return out

    def build_paths(self):
        """every pixel of every leg, a -> b: the camera the walk shows there and its view numbers (the windows tools/gen_smap_world.py path_windows collects)"""
        self.leg_samples = []
        wins = set()
        for a, b, pts in self.legs:
            smp = []
            for (fx, fy) in self.sample_leg(pts):
                cx, cy = cam(fx, fy)
                v = self.view(cx, cy)
                wins.add(v["win"])
                smp.append((fx, fy, v))
            self.leg_samples.append(smp)
        self.rest = []                         # the resting views: (stop index, name, camera px, view)
        for i, (n, (sx, sy)) in enumerate(zip(self.order, self.stops)):
            vx, vy, _ = G.STOP_VIEW.get(n, (None, None, 1))
            cx, cy = cam(sx, sy)
            if vx is not None or vy is not None:
                cx, cy = (cx if vx is None else vx), (cy if vy is None else vy)
            self.rest.append((i, n, (cx, cy), self.view(cx, cy)))
            wins.add(self.view(cx, cy)["win"])
            wins.add(self.view(*cam(sx, sy))["win"])
        for n, (sx, sy) in zip(self.order, self.stops):
            vx, vy, _ = G.STOP_VIEW.get(n, (None, None, 1))
            if vx is not None or vy is not None:
                for i in range(33):
                    fx = sx if vx is None else vx + 80 + (sx - 80 - vx) * i // 32
                    fy = sy if vy is None else vy + G.SAL_Y + (sy - G.SAL_Y - vy) * i // 32
                    wins.add(self.view(*cam(fx, fy))["win"])
        self.path_wins = wins
        self.match_build = wins == set(G.path_windows(self.stops, self.legs))

    def leg_name(self, li):
        a, b, _ = self.legs[li]
        return NAMES[self.order[a]] + " to " + NAMES[self.order[b]]
