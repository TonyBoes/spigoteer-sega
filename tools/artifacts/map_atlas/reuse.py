#!/usr/bin/env python3
"""Story map shape reuse: what the map could gain by drawing the same shape once and giving it a palette per area (analysis only, writes nothing under src/, assets/ or tests/).

Numbers come from the generator's own Model (tools/gen_smap_world.py): a Color id is a distinct 8 x 8 index block after the mirror merge, a DMG tile a distinct block of the DMG
pixel set, windows are the generator's (21 x 19 DMG pixel windows, the padded path windows `path_windows`, Color palettes per 21 x 19 window).  Every opportunity is *simulated*: the
pixels of a copy of the world are edited and the Models are rebuilt, so the savings are measured, not estimated.

    python3 tools/artifacts/map_atlas/reuse.py                 # prints the report tables (a few minutes), writes out/reuse.json
    python3 tools/artifacts/map_atlas/reuse.py --sheet         # also writes out/reuse_sheet.png (the owner's contact sheet)

Run from anywhere; output goes to <repo>/out/.
"""
import copy
import itertools
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path[:0] = [str(ROOT / "tools"), str(ROOT / "tools" / "smap_world")]
import gen_smap_world as G  # noqa: E402

W = G.W
CW, CH = G.CW, G.CH
NAMES = list(G.PAL_NAMES)
PERMS = list(itertools.permutations(range(4)))
OUT = ROOT / "out"
TOWN = NAMES.index("town1")                  # the overlay/window text is drawn with this palette's slot (src/smap.c ui_attr): its colour order is fixed
SMALL = ["cactus", "town1@z", "town5", "town4", "bistro@g", "town1@n"]


# ---- the world as editable arrays --------------------------------------------------------------------------------------------------------------------------
class FakeWorld:
    """what Model reads of a world: .px, .pal (names) and .copy()"""

    def __init__(self, px, pal):
        self.px, self.pal = px, pal

    def copy(self):
        return FakeWorld([r[:] for r in self.px], [r[:] for r in self.pal])


class Edit:
    """a copy of the finished map: pixel arrays for Color (C) and DMG (D), palette index per cell (P)"""

    def __init__(self):
        self.C = np.array(W.WORLD.px, dtype=np.int8)
        self.D = np.array(W.WORLD_DMG.px, dtype=np.int8)
        self.P = np.array([[NAMES.index(n) for n in r] for r in W.WORLD.pal], dtype=np.int32)

    def clone(self):
        e = copy.copy(self)
        e.C, e.D, e.P = self.C.copy(), self.D.copy(), self.P.copy()
        return e

    def models(self):
        """(Color Model, DMG Model) of this edit; the real world objects are put back afterwards"""
        keep = W.WORLD, W.WORLD_DMG
        try:
            pal = [[NAMES[v] for v in r] for r in self.P.tolist()]
            W.WORLD = FakeWorld(self.C.tolist(), pal)
            W.WORLD_DMG = FakeWorld(self.D.tolist(), [r[:] for r in pal])
            G.W = W
            return G.Model(True), G.Model(False)
        finally:
            W.WORLD, W.WORLD_DMG = keep


_WINS = None


def path_wins():
    global _WINS
    if _WINS is None:
        stops, legs, _, _ = G.geometry()
        _WINS = G.path_windows(stops, legs)
    return _WINS


def counts_in(grid, wins):
    """the number of distinct values of `grid` in each window (c0, c1, r0, r1)"""
    return np.array([len(np.unique(grid[r0:r1 + 1, c0:c1 + 1])) for (c0, c1, r0, r1) in wins])


def win21(w=21, h=19):
    return [(x, x + w - 1, y, y + h - 1) for y in range(CH - h + 1) for x in range(CW - w + 1)]


class Metrics:
    """ids, tiles and the window numbers of one edit"""

    def __init__(self, e, wanted=True):
        cg, dm = e.models()
        self.cg, self.dm = cg, dm
        self.ids = cg.nt                                     # Color ids (all states, as the build counts)
        self.tiles = dm.nt                                   # DMG tiles
        self.ids11 = len(np.unique(cg.grids[11]))
        self.tiles11 = len(np.unique(dm.grids[11]))
        gd = dm.grids[11]
        pw = path_wins()
        self.pad = counts_in(gd, pw)                         # DMG tiles in every padded path window
        self.pad_max = int(self.pad.max())
        self.pad_ge174 = int((self.pad >= 174).sum())
        self.w21 = counts_in(gd, win21())
        self.w21_max = int(self.w21.max())
        self.pal_w = counts_in(e.P, win21())                 # Color palettes per 21 x 19 window
        self.pal_max = int(self.pal_w.max())
        self.pal_at8 = int((self.pal_w >= 8).sum())
        self.padC = counts_in(cg.grids[11], pw)              # Color ids in the padded path windows
        self.padC_max = int(self.padC.max())

    def row(self):
        return dict(ids=self.ids, tiles=self.tiles, pad_max=self.pad_max, pad174=self.pad_ge174, w21=self.w21_max, pal_max=self.pal_max, pal8=self.pal_at8,
                    padC=self.padC_max)


def delta(base, m):
    return dict(color_saved=base.ids - m.ids, dmg_saved=base.tiles - m.tiles, pad_max=m.pad_max, pad_d=m.pad_max - base.pad_max, w21=m.w21_max,
                w21_d=m.w21_max - base.w21_max, pal_max=m.pal_max, pal8=m.pal_at8, pal8_d=m.pal_at8 - base.pal_at8)


# ---- 1. relabelling: a permutation of the 4 index values per palette -------------------------------------------------------------------------------------------
def flips(a):
    """a: (n, 64) -> the four flip images (identity, X, Y, XY) as arrays"""
    g = a.reshape(-1, 8, 8)
    return [g.reshape(-1, 64), g[:, :, ::-1].reshape(-1, 64), g[:, ::-1, :].reshape(-1, 64), g[:, ::-1, ::-1].reshape(-1, 64)]


def cell_blocks(img):
    """(CH, CW, 64) the 8 x 8 blocks of a pixel array"""
    return img.reshape(CH, 8, CW, 8).transpose(0, 2, 1, 3).reshape(CH, CW, 64)


class Relabel:
    """coordinate descent over one permutation per palette: the Color id count (distinct blocks after the mirror merge: a family of n distinct mirror images takes ceil(n / 2) ids)"""

    def __init__(self, e, fixed=(TOWN,)):
        self.e = e
        blk = cell_blocks(e.C)
        self.fixed = set(fixed)
        self.use = defaultdict(set)                          # palette -> distinct blocks (bytes)
        for y in range(CH):
            for x in range(CW):
                self.use[int(e.P[y, x])].add(blk[y, x].tobytes())
        self.pals = sorted(self.use)
        self.keys = {}                                       # (p, perm index) -> list of (family key, image)
        for p in self.pals:
            arr = np.array([np.frombuffer(b, dtype=np.uint8) for b in self.use[p]])
            for k, perm in enumerate(PERMS):
                im = np.array(perm, dtype=np.uint8)[arr]
                fl = flips(im)
                out = []
                for i in range(len(im)):
                    cands = [f[i].tobytes() for f in fl]
                    out.append((min(cands), cands[0]))
                self.keys[(p, k)] = out

    def cost(self, choice):
        fam = defaultdict(set)
        for p in self.pals:
            for fk, im in self.keys[(p, choice[p])]:
                fam[fk].add(im)
        return sum((len(v) + 1) // 2 for v in fam.values())

    def run(self, restarts=12, seed=1):
        rng = np.random.default_rng(seed)
        ident = PERMS.index((0, 1, 2, 3))
        base = {p: ident for p in self.pals}
        self.base_cost = self.cost(base)
        best, best_c = dict(base), self.base_cost
        for r in range(restarts):
            ch = dict(base) if r == 0 else {p: (ident if p in self.fixed else int(rng.integers(24))) for p in self.pals}
            cur = self.cost(ch)
            improved = True
            while improved:
                improved = False
                for p in rng.permutation(self.pals):
                    p = int(p)
                    if p in self.fixed:
                        continue
                    bk, bc = ch[p], cur
                    for k in range(24):
                        if k == ch[p]:
                            continue
                        old = ch[p]
                        ch[p] = k
                        c = self.cost(ch)
                        if c < bc:
                            bk, bc = k, c
                        ch[p] = old
                    if bc < cur:
                        ch[p], cur, improved = bk, bc, True
            if cur < best_c:
                best, best_c = dict(ch), cur
        self.best, self.best_cost = best, best_c
        return best

    def apply(self, e, choice):
        e = e.clone()
        for p, k in choice.items():
            m = e.P == p
            if not m.any() or PERMS[k] == (0, 1, 2, 3):
                continue
            cm = np.kron(m, np.ones((8, 8), dtype=bool))
            e.C[cm] = np.array(PERMS[k], dtype=np.int8)[e.C[cm]]
        return e


def canon_classes(sigs, use_flips):
    """group blocks (list of bytes) by the canonical form under colour permutation (and flips)"""
    arr = np.array([np.frombuffer(s, dtype=np.uint8) for s in sigs])
    best = [None] * len(arr)
    for perm in PERMS:
        im = np.array(perm, dtype=np.uint8)[arr]
        fl = flips(im) if use_flips else [im]
        for f in fl:
            for i in range(len(arr)):
                b = f[i].tobytes()
                if best[i] is None or b < best[i]:
                    best[i] = b
    groups = defaultdict(list)
    for i, b in enumerate(best):
        groups[b].append(i)
    return groups


# ---- 2. near reuse: tiles within d pixels of each other after relabelling ----------------------------------------------------------------------------------
class Near:
    """distance between the distinct blocks of an image: D[i, j] = fewest differing pixels between block i and any allowed transform of block j (flips; colour permutations when
    use_perm), T[i, j] the transform's index (perm * 4 + flip)"""

    def __init__(self, blocks, use_flips, use_perm):
        self.blocks = blocks
        arr = self.arr = np.array([np.frombuffer(b, dtype=np.uint8) for b in blocks])
        n = len(arr)
        A = np.zeros((n, 256), dtype=np.float32)
        for k in range(4):
            A[np.arange(n)[:, None], np.arange(64)[None, :] * 4 + k] = (arr == k)
        self.D = np.full((n, n), 99, dtype=np.int32)
        self.T = np.zeros((n, n), dtype=np.int32)
        for pi, perm in enumerate(PERMS if use_perm else [(0, 1, 2, 3)]):
            im = np.array(perm, dtype=np.uint8)[arr]
            for fi, f in enumerate(flips(im) if use_flips else [im]):
                B = np.zeros((n, 256), dtype=np.float32)
                for k in range(4):
                    B[np.arange(n)[:, None], np.arange(64)[None, :] * 4 + k] = (f == k)
                d = 64 - (A @ B.T).astype(np.int32)
                better = d < self.D
                self.D[better] = d[better]
                self.T[better] = pi * 4 + fi
        self.use_perm = use_perm

    def image(self, j, t):
        """block j under transform t"""
        pi, fi = divmod(int(t), 4)
        im = np.array(PERMS[pi], dtype=np.uint8)[self.arr[j]]
        return flips(im[None, :])[fi][0]

    def stars(self, d, skip=(), allowed=None, centers=None):
        """greedy stars at distance <= d: [(centre, [members])]; a member is absorbed once, a centre never absorbed (so no chain)"""
        n = len(self.blocks)
        near = (self.D <= d) & (self.D > 0)
        np.fill_diagonal(near, False)
        skip = set(skip)
        if allowed is not None:
            skip |= set(range(n)) - set(allowed)
        for i in skip:
            near[i, :] = near[:, i] = False
        deg = near.sum(axis=1)
        gone, out = set(), []
        for i in np.argsort(-deg, kind="stable"):
            i = int(i)
            if i in gone or deg[i] == 0 or (centers is not None and i not in centers):
                continue
            mem = [int(j) for j in np.nonzero(near[i])[0] if int(j) not in gone]
            if mem:
                gone.update(mem)
                gone.add(i)
                out.append((i, mem))
        return out


_NEAR = {}


def near_simulate(e, which, d, use_flips, use_perm=False, cat=None, only=None, centre=None):
    """merge the stars at distance <= d for real: every member block is replaced by the centre's pixels (under the best transform) in every cell; returns (edit, groups, cells changed, pixels changed)"""
    img = (e.C if which == "C" else e.D)
    blk = cell_blocks(img)
    seen = {}
    for y in range(CH):
        for x in range(CW):
            seen.setdefault(blk[y, x].tobytes(), []).append((x, y))
    blocks = list(seen)
    key = (which, use_flips, use_perm, hash(tuple(blocks)))
    if key not in _NEAR:
        _NEAR[key] = Near(blocks, use_flips, use_perm)
    nr = _NEAR[key]
    anim = {blocks.index(blk[y, x].tobytes()) for (x, y) in getattr(W, "ANIM_CELLS", ())}
    allowed = None
    if only is not None:                                                  # only blocks all of whose cells lie in categories accepted by `only`
        allowed = {i for i, b in enumerate(blocks) if all(only(str(cat[y, x])) for (x, y) in seen[b])}
    gr = nr.stars(d, skip=anim, allowed=allowed, centers=None if centre is None else {blocks.index(centre)})
    e2 = e.clone()
    img2 = e2.C if which == "C" else e2.D
    cells = px = 0
    for c, mem in gr:
        for m in mem:
            new = nr.image(c, nr.T[m, c]).reshape(8, 8)
            for (x, y) in seen[blocks[m]]:
                img2[y * 8:y * 8 + 8, x * 8:x * 8 + 8] = new
                cells += 1
                px += int(nr.D[m, c])
    return e2, [(blocks[c], [blocks[m] for m in mem], [seen[blocks[c]]] + [seen[blocks[m]] for m in mem], [int(nr.D[m, c]) for m in mem]) for c, mem in gr], cells, px


# ---- 3. object families: template matching and the phase simulation -------------------------------------------------------------------------------------
SEEDS = {"PEAK_A": (152, 248, 32, 24), "PEAK_B": (32, 248, 32, 24), "PEAK_C": (104, 250, 32, 22), "PEAK_D": (400, 14, 32, 26),
         "CACTUS_S": (72, 248, 8, 16), "CACTUS_S2": (144, 248, 8, 16), "CACTUS_B": (184, 272, 8, 8), "CACTUS_Q": (24, 248, 8, 8)}       # where a piece first stands in the finished map (pixels)


def templates(e):
    """name -> rows ('.' clear, digits = index): the decor pieces from tools/smap_world/decor.py, the peaks and cacti cut from the map where they first stand (their clear pixels are the ground, 0)"""
    import decor
    fam = {}

    def rows(r):
        return [x if isinstance(x, str) else "".join(x) for x in r]
    for n in ("PINE", "ROUND", "BUSH", "SPRUCE", "MOUND", "ROCK", "ROCK_S"):
        fam[n] = rows(getattr(decor, n)[1])
    for n, (x, y, w, h) in SEEDS.items():
        blk = e.C[y:y + h, x:x + w]
        fam[n] = ["".join("." if v == 0 else str(int(v)) for v in r) for r in blk]
    return fam


def find(img, rows):
    h, w = len(rows), len(rows[0])
    m = np.array([[-1 if c == "." else int(c) for c in r] for r in rows])
    sel = m >= 0
    res = []
    for y in range(img.shape[0] - h + 1):
        for x in range(img.shape[1] - w + 1):
            if (img[y:y + h, x:x + w][sel] == m[sel]).all():
                res.append((x, y))
    return res


def instances(e, fam, which):
    """{family: [(x px, y px, w, h, palette index of its first cell)]}; a BUSH match inside a ROUND match (the round tree's canopy) is not a bush, a ROCK_S inside nothing else"""
    img = e.C if which == "C" else e.D
    out = {}
    for n, r in fam.items():
        out[n] = [(x, y, len(r[0]), len(r), int(e.P[y // 8, x // 8])) for x, y in find(img, r)]
    keep = []
    for (x, y, w, h, p) in out.get("BUSH", []):
        if any(rx <= x < rx + rw and ry <= y < ry + rh for (rx, ry, rw, rh, _) in out.get("ROUND", [])):
            continue
        keep.append((x, y, w, h, p))
    out["BUSH"] = keep
    return out


def cells_of(x, y, w, h):
    return [(cx, cy) for cy in range(y // 8, (y + h - 1) // 8 + 1) for cx in range(x // 8, (x + w - 1) // 8 + 1)]


def snap_family(e, fam_rows, inst, phase, which):
    """a copy of e in which every instance of the family stands at the pixel phase (px, py) mod 8 (the nearest one: at most 4 px away); returns (edit, moved, blocked)"""
    e2 = e.clone()
    img = e2.C if which == "C" else e2.D
    m = np.array([[-1 if c == "." else int(c) for c in r] for r in fam_rows])
    h, w = m.shape
    moved = blocked = 0
    for (x, y, _, _, p) in sorted(inst, key=lambda t: (t[1], t[0])):
        def near(v, ph):
            cand = [v - ((v - ph) % 8), v - ((v - ph) % 8) + 8]
            return min(cand, key=lambda c: abs(c - v))
        nx, ny = near(x, phase[0]), near(y, phase[1])
        if (nx, ny) == (x, y):
            continue
        oc, nc = cells_of(x, y, w, h), cells_of(nx, ny, w, h)
        ok = 0 <= nx and nx + w <= CW * 8 and 0 <= ny and ny + h <= CH * 8
        if ok:
            for (cx, cy) in nc:
                if (cx, cy) in oc:
                    continue
                blk = img[cy * 8:cy * 8 + 8, cx * 8:cx * 8 + 8]
                if e2.P[cy, cx] != p or not (blk <= 1).all() or (blk > 0).sum() > 8:       # plain ground of the same palette only (flat or one tuft)
                    ok = False
                    break
        if not ok:
            blocked += 1
            continue
        for (cx, cy) in oc:
            img[cy * 8:cy * 8 + 8, cx * 8:cx * 8 + 8] = 0
        for (cx, cy) in nc:
            img[cy * 8:cy * 8 + 8, cx * 8:cx * 8 + 8] = 0
            e2.P[cy, cx] = p
        sel = m >= 0
        sub = img[ny:ny + h, nx:nx + w]
        sub[sel] = m[sel]
        moved += 1
    return e2, moved, blocked


def swap_family(e, which, from_rows, from_inst, to_rows):
    """every instance of one piece replaced by another piece standing on the same foot line and left edge (plain ground of the same palette only); returns (edit, done, blocked)"""
    e2 = e.clone()
    img = e2.C if which == "C" else e2.D
    m = np.array([[-1 if c == "." else int(c) for c in r] for r in to_rows])
    h, w = m.shape
    fh = len(from_rows)
    done = blocked = 0
    for (x, y, fw, _, p) in from_inst:
        ny = y + fh - h
        oc, nc = cells_of(x, y, fw, fh), cells_of(x, ny, w, h)
        ok = ny >= 0 and x + w <= CW * 8
        if ok:
            for (cx, cy) in nc:
                if (cx, cy) in oc:
                    continue
                blk = img[cy * 8:cy * 8 + 8, cx * 8:cx * 8 + 8]
                if e2.P[cy, cx] != p or (blk > 0).sum() > 8:
                    ok = False
                    break
        if not ok:
            blocked += 1
            continue
        for (cx, cy) in oc + nc:
            img[cy * 8:cy * 8 + 8, cx * 8:cx * 8 + 8] = 0
        for (cx, cy) in nc:
            e2.P[cy, cx] = p
        sel = m >= 0
        img[ny:ny + h, x:x + w][sel] = m[sel]
        done += 1
    return e2, done, blocked


# ---- 4. ground textures ------------------------------------------------------------------------------------------------------------------------------------
def ground_tiles(model, e):
    """the ground texture tiles: blocks of at most 12 non-zero pixels used at least 3 times in the finished map, with their cell counts and palettes"""
    g = model.grids[11]
    cnt = Counter(g.ravel().tolist())
    res = defaultdict(lambda: Counter())
    for y in range(CH):
        for x in range(CW):
            s = model.sigs[int(g[y, x])]
            if sum(1 for v in s if v) <= 12 and cnt[int(g[y, x])] >= 3:
                res[int(g[y, x])][NAMES[e.P[y, x]]] += 1
    return res


# ---- 5. palette merges ---------------------------------------------------------------------------------------------------------------------------------------
def palette_distance(a, b):
    """(mean RGB distance of the best colour matching of a's four colours onto b's, the permutation: new index of a's index i is perm[i])"""
    ra = np.array([W.RGB[NAMES[a]][i] for i in range(4)], dtype=float)
    rb = np.array([W.RGB[NAMES[b]][i] for i in range(4)], dtype=float)
    best = (1e9, None)
    for perm in PERMS:
        d = np.mean([np.abs(ra[i] - rb[perm[i]]).sum() for i in range(4)])
        if d < best[0]:
            best = (d, perm)
    return best


def merge_edit(e, a, b, perm):
    """cells of palette a take palette b (their pixel values relabelled by perm so the colours fit)"""
    e2 = e.clone()
    m = e2.P == a
    cm = np.kron(m, np.ones((8, 8), dtype=bool))
    e2.C[cm] = np.array(perm, dtype=np.int8)[e2.C[cm]]
    e2.P[m] = b
    return e2


def is_cgb_only(e):
    return (e.C != e.D).any()


# ---- categories: where the tiles go ---------------------------------------------------------------------------------------------------------------------------
VENUE_PX = {"igloo": (80, 48), "town": (96, 72), "bistro": (72, 56), "saloon": (72, 56), "tea": (96, 56), "stadium": (80, 56), "space": (112, 72), "cow": (80, 56), "factory": (80, 56),
            "lodge": (80, 64), "zoo": (112, 64)}          # picture sizes in pixels (tools/smap_world/v_*.py)
DECOR_NAME = {"PINE": "pine", "ROUND": "round tree", "BUSH": "bush", "SPRUCE": "snow spruce", "MOUND": "snow drift", "ROCK": "rock", "ROCK_S": "rock", "PEAK_A": "peak", "PEAK_B": "peak",
              "PEAK_C": "peak", "PEAK_D": "peak", "CACTUS_S": "cactus", "CACTUS_S2": "cactus", "CACTUS_B": "cactus", "CACTUS_Q": "cactus"}


def categories(e, inst, dm):
    """a category per cell: venue picture, a decor family's box, water, the texture tiles (ground), the other town1 cells (roads), the rest (scenery: mountains, mesa, edges)"""
    cat = np.full((CH, CW), "", dtype=object)
    for k, (_, (x, y)) in W.VENUES.items():
        w, h = VENUE_PX[k]
        cat[y:y + h // 8, x:x + w // 8] = "venue " + k
    for n, lst in inst.items():
        for (x, y, w, h, p) in lst:
            for (cx, cy) in cells_of(x, y, w, h):
                if 0 <= cx < CW and 0 <= cy < CH and not cat[cy, cx]:
                    cat[cy, cx] = DECOR_NAME.get(n, n)
    gd = dm.grids[11]
    cnt = Counter(gd.ravel().tolist())
    for y in range(CH):
        for x in range(CW):
            if cat[y, x]:
                continue
            nm = NAMES[e.P[y, x]]
            t = int(gd[y, x])
            s_ = dm.sigs[t]
            if nm == "water":
                cat[y, x] = "water"
            elif sum(1 for v in s_ if v) <= 12 and cnt[t] >= 3 and not nm.startswith("town1"):
                cat[y, x] = "ground"
            elif nm.startswith("town1"):
                cat[y, x] = "road"
            else:
                cat[y, x] = "other scenery"
    return cat


def cat_table(cat, cg, dm):
    gC, gD = cg.grids[11], dm.grids[11]
    cntC, cntD = np.bincount(gC.ravel()), np.bincount(gD.ravel())
    rows = []
    for c in sorted(set(cat.ravel())):
        m = cat == c
        tD, tC = np.unique(gD[m]), np.unique(gC[m])
        exD = np.setdiff1d(tD, np.unique(gD[~m]))
        rows.append(dict(cat=c, cells=int(m.sum()), dmg_tiles=len(tD), dmg_only_here=len(exD), dmg_single=int((cntD[tD] == 1).sum()), color_ids=len(tC),
                         color_single=int((cntC[tC] == 1).sum())))
    return rows


# ---- the report -----------------------------------------------------------------------------------------------------------------------------------------------
def best_snaps(e0, base, fam, instC, instD, names):
    """one combined edit: every named family snapped to its best phase (Color and DMG each); the per-family results of the single snaps"""
    e = e0.clone()
    plan = {}
    for which, inst in (("C", instC), ("D", instD)):
        for n in names:
            lst = inst[n]
            if len(lst) < 2:
                continue
            phases = Counter((x % 8, y % 8) for x, y, *_ in lst)
            bestph = None
            for ph in [p for p, _ in phases.most_common(3)] + [(0, 0)]:
                e2, mv, bl = snap_family(e0, fam[n], lst, ph, which)
                d = delta(base, Metrics(e2))
                key = d["color_saved"] if which == "C" else d["dmg_saved"]
                if bestph is None or key > bestph[0]:
                    bestph = (key, ph, mv, bl, d)
            plan[(which, n)] = bestph
            e, _, _ = snap_family(e, fam[n], lst, bestph[1], which)
    return e, plan


def main():
    sheet = "--sheet" in sys.argv
    OUT.mkdir(exist_ok=True)
    e0 = Edit()
    if "--sheet-only" in sys.argv:                                      # redraw the sheet from the last run's out/reuse.json
        import reuse_sheet
        fam = templates(e0)
        reuse_sheet.make(e0, instances(e0, fam, "C"), instances(e0, fam, "D"), fam, json.loads((OUT / "reuse.json").read_text()), None)
        return
    base = Metrics(e0)
    cg, dm = base.cg, base.dm
    R = dict(base=base.row())
    wp = path_wins()
    w21 = win21()
    R["worst_pad"] = [(wp[i], int(base.pad[i])) for i in np.argsort(-base.pad)[:3]]
    R["worst_21"] = [(w21[i], int(base.w21[i])) for i in np.argsort(-base.w21)[:3]]
    gC, gD = cg.grids[11], dm.grids[11]
    R["single_use"] = dict(dmg_tiles=int(len(np.unique(gD))), dmg_single=int((np.bincount(gD.ravel()) == 1).sum()), color_ids=int(len(np.unique(gC))),
                           color_single=int((np.bincount(gC.ravel()) == 1).sum()))
    print("BASE", base.row(), "single-use", R["single_use"])
    print("worst padded path windows", R["worst_pad"], "worst 21x19", R["worst_21"])
    fam = templates(e0)
    instC, instD = instances(e0, fam, "C"), instances(e0, fam, "D")
    cat = categories(e0, instD, dm)
    R["categories"] = cat_table(cat, cg, dm)
    for r in R["categories"]:
        print("CAT", r)
    for label, w in (("worst padded window", R["worst_pad"][0][0]), ("worst 21x19", R["worst_21"][0][0])):
        c0, c1, r0, r1 = w
        sub, tl = cat[r0:r1 + 1, c0:c1 + 1], gD[r0:r1 + 1, c0:c1 + 1]
        per = {c: len(np.unique(tl[sub == c])) for c in sorted(set(sub.ravel()))}
        R["window_mix_" + label.replace(" ", "_")] = dict(win=w, tiles=len(np.unique(tl)), per_cat=per)
        print("MIX", label, w, len(np.unique(tl)), per)
    # 1. relabel
    rl = Relabel(e0)
    best = rl.run()
    m1 = Metrics(rl.apply(e0, best))
    moved = {NAMES[p]: PERMS[k] for p, k in best.items() if PERMS[k] != (0, 1, 2, 3)}
    print("RELABEL model", rl.base_cost, "->", rl.best_cost, "real", base.ids, "->", m1.ids, "palettes reordered:", moved)
    R["relabel"] = dict(model=(rl.base_cost, rl.best_cost), real=delta(base, m1), perms={k: list(v) for k, v in moved.items()})
    sigsC = list({cell_blocks(e0.C)[y, x].tobytes() for y in range(CH) for x in range(CW)})
    sigsD = list({cell_blocks(e0.D)[y, x].tobytes() for y in range(CH) for x in range(CW)})
    R["classes"] = dict(color_blocks=len(sigsC), color_classes=len(canon_classes(sigsC, True)), dmg_blocks=len(sigsD), dmg_perm=len(canon_classes(sigsD, False)),
                        dmg_perm_flip=len(canon_classes(sigsD, True)))
    print("CLASSES", R["classes"])
    arrD = np.array([np.frombuffer(s_, dtype=np.uint8) for s_ in sigsD])

    def dmg_classes(perms):
        return len({min(np.array(pm, dtype=np.uint8)[a].tobytes() for pm in perms) for a in arrD})
    R["dmg_shade_classes"] = {"any perm": dmg_classes(PERMS), "keep shade 0": dmg_classes([q for q in PERMS if q[0] == 0]), "swap 1,2 only": dmg_classes([(0, 1, 2, 3), (0, 2, 1, 3)]),
                              "swap 2,3 only": dmg_classes([(0, 1, 2, 3), (0, 1, 3, 2)]), "swap 0,1 only": dmg_classes([(0, 1, 2, 3), (1, 0, 2, 3)])}
    print("DMG shade classes", R["dmg_shade_classes"])
    # 2. near reuse
    near = {}
    for label, which, uf, up in (("Color same colours + flips", "C", True, False), ("Color any colour order + flips", "C", True, True), ("DMG same shades", "D", False, False),
                                 ("DMG any shade order", "D", False, True)):
        blk = cell_blocks(e0.C if which == "C" else e0.D)
        nr = Near(list({blk[y, x].tobytes() for y in range(CH) for x in range(CW)}), uf, up)
        near[label] = {d: sum(len(m) for _, m in nr.stars(d)) for d in (1, 2, 3, 4)}
        print("NEAR (blocks; upper bound)", label, near[label])
    R["near_bound"] = near
    sim = {}
    for d in (1, 2, 3, 4):
        ec, grc, cc, pc = near_simulate(e0, "C", d, True)
        ed, grd, cd, pd_ = near_simulate(e0, "D", d, False)
        eb = ec.clone()
        eb.D = ed.D
        mC, mD = Metrics(ec), Metrics(ed)
        sim[d] = dict(color=dict(saved=base.ids - mC.ids, cells=cc, px=pc, padC=mC.padC_max), dmg=dict(saved=base.tiles - mD.tiles, cells=cd, px=pd_, pad_max=mD.pad_max,
                      pad174=mD.pad_ge174, w21=mD.w21_max), both=delta(base, Metrics(eb)))
        print("NEAR sim d<=%d" % d, sim[d])
        if d in (2, 4):
            top = lambda gr: [dict(n=len(m), cells=[c[0] for c in cs[:4]], dist=ds) for (_, m, cs, ds) in sorted(gr, key=lambda g: -len(g[1]))[:20]]
            sim[d]["groups_dmg"], sim[d]["groups_color"] = top(grd), top(grc)
            bycat = lambda gr: dict(Counter(str(cat[cs[0][0][1], cs[0][0][0]]) for (_, m, cs, ds) in gr for _ in m))
            sim[d]["dmg_by_cat"], sim[d]["color_by_cat"] = bycat(grd), bycat(grc)
    R["near_sim"] = sim
    # the same, one category at a time: what each part of the map would give (and cost) on its own
    venues = sorted(k for k in VENUE_PX)
    sets = {"ground": lambda c: c == "ground", "road": lambda c: c == "road", "water": lambda c: c == "water", "other scenery": lambda c: c == "other scenery",
            "trees, bushes, rocks": lambda c: c in ("pine", "round tree", "bush", "snow spruce", "rock", "snow drift", "peak", "cactus"), "venue pictures (all)": lambda c: c.startswith("venue")}
    for v in venues:
        sets["venue " + v] = (lambda vv: lambda c: c == "venue " + vv)(v)
    bycat = {}
    for name, fn in sets.items():
        row_ = {}
        for d in (2, 4):
            ec, _, cc, pc = near_simulate(e0, "C", d, True, cat=cat, only=fn)
            ed, _, cd, pd_ = near_simulate(e0, "D", d, False, cat=cat, only=fn)
            mC, mD = Metrics(ec), Metrics(ed)
            row_[d] = dict(color_saved=base.ids - mC.ids, color_cells=cc, color_px=pc, dmg_saved=base.tiles - mD.tiles, dmg_cells=cd, dmg_px=pd_, pad_max=mD.pad_max, pad174=mD.pad_ge174,
                           w21=mD.w21_max, padC=mC.padC_max)
        bycat[name] = row_
        print("NEARCAT", name, row_)
    R["near_by_cat"] = bycat
    # 3. families
    famrows = {}
    for n, r in fam.items():
        ic, idd = instC[n], instD[n]
        row = dict(color_inst=len(ic), dmg_inst=len(idd), phases_c=sorted({(x % 8, y % 8) for x, y, *_ in ic}), phases_d=sorted({(x % 8, y % 8) for x, y, *_ in idd}),
                   pals=sorted({NAMES[p] for *_, p in ic}), cells=[(x // 8, y // 8) for x, y, *_ in ic], size=(len(r[0]), len(r)))
        row["tiles_c"] = len({cell_blocks(e0.C)[cy, cx].tobytes() for x, y, w, h, p in ic for cx, cy in cells_of(x, y, w, h)})
        row["tiles_d"] = len({cell_blocks(e0.D)[cy, cx].tobytes() for x, y, w, h, p in idd for cx, cy in cells_of(x, y, w, h)})
        famrows[n] = row
    snap_names = [n for n in fam if len(instC[n]) >= 2 or len(instD[n]) >= 2]
    e_snap, plan = best_snaps(e0, base, fam, instC, instD, snap_names)
    for (which, n), (key, ph, mv, bl, d) in plan.items():
        famrows[n].setdefault("snap", {})[which] = dict(phase=ph, moved=mv, blocked=bl, **d)
        print("SNAP", which, n, ph, "moved", mv, "blocked", bl, "saved", key, "pad", d["pad_max"], "pal8", d["pal8"])
    R["families"] = famrows
    R["snap_all"] = delta(base, Metrics(e_snap))
    print("SNAP ALL", R["snap_all"])
    # 4. ground
    R["ground"] = dict(color=len(ground_tiles(cg, e0)), dmg=len(ground_tiles(dm, e0)))
    # 5. palette merges
    pm = {}
    cnt = Counter(NAMES[v] for v in e0.P.ravel())
    for n in SMALL:
        a = NAMES.index(n)
        cands = sorted((palette_distance(a, b)[0], b, palette_distance(a, b)[1]) for b in range(len(NAMES)) if b != a)
        out = []
        for d, b, perm in cands[:4]:
            m = Metrics(merge_edit(e0, a, b, perm))
            out.append(dict(into=NAMES[b], colour_dist=round(float(d), 1), perm=list(perm), **delta(base, m)))
        pm[n] = dict(cells=cnt[n], options=out)
        print("MERGE", n, cnt[n], [(o["into"], o["colour_dist"], o["pal8"], o["color_saved"]) for o in out])
    R["merge_small"] = pm
    close = []
    for a in range(len(NAMES)):
        for b in range(a + 1, len(NAMES)):
            d, perm = palette_distance(a, b)
            close.append((round(float(d), 1), NAMES[a], NAMES[b], list(perm)))
    close.sort()
    R["close_pairs"] = close[:14]
    wins = win21()
    at8 = [wins[i] for i in np.nonzero(base.pal_w >= 8)[0]]
    cover = {}
    for k, (x0, x1, y0, y1) in {"west (35-37,44-46)": (35, 37, 44, 46), "east (50-52,44-46)": (50, 52, 44, 46)}.items():
        ws = [w for w in at8 if w[0] <= x0 and w[1] >= x1 and w[2] <= y0 and w[3] >= y1]
        pl = Counter()
        for (c0, c1, r0, r1) in ws:
            pl.update(NAMES[v] for v in np.unique(e0.P[r0:r1 + 1, c0:c1 + 1]))
        fixes = []
        for a in range(len(NAMES)):
            if a == TOWN:
                continue
            for b in range(len(NAMES)):
                if b == a:
                    continue
                P = e0.P.copy()
                P[P == a] = b
                if all(len(np.unique(P[r0:r1 + 1, c0:c1 + 1])) < 8 for (c0, c1, r0, r1) in ws):
                    fixes.append((round(float(palette_distance(a, b)[0]), 1), NAMES[a], NAMES[b]))
        fixes.sort()
        cover[k] = dict(windows_at8=len(ws), palettes_in_8_windows=dict(pl), single_merge_fixes=fixes[:8])
    R["win8"] = dict(count=len(at8), of=len(wins), wedges=cover)
    print("WIN8", json.dumps(R["win8"], default=str)[:1800])
    # which sets of up to two merges leave no window over a wedge at 8 palettes (palette masks of the windows, merged as bit moves); cost = summed colour distance
    pd_cache = {(a, b): palette_distance(a, b)[0] for a in range(len(NAMES)) for b in range(len(NAMES)) if a != b}
    for k in ("west", "east", "both"):
        x0, x1, y0, y1 = {"west": (35, 37, 44, 46), "east": (50, 52, 44, 46), "both": (0, 0, 0, 0)}[k]
        if k == "both":
            ws = [w for w in at8 if any(w[0] <= a0 and w[1] >= a1 and w[2] <= b0 and w[3] >= b1 for (a0, a1, b0, b1) in ((35, 37, 44, 46), (50, 52, 44, 46)))]
        else:
            ws = [w for w in at8 if w[0] <= x0 and w[1] >= x1 and w[2] <= y0 and w[3] >= y1]
        masks = [sum(1 << int(v) for v in np.unique(e0.P[r0:r1 + 1, c0:c1 + 1])) for (c0, c1, r0, r1) in ws]

        def clears(merges):
            for m in masks:
                for a, b in merges:
                    if m >> a & 1:
                        m = (m & ~(1 << a)) | (1 << b)
                if bin(m).count("1") >= 8:
                    return False
            return True
        opts = [(a, b) for a in range(len(NAMES)) for b in range(len(NAMES)) if a != b and a != TOWN]
        one = sorted((pd_cache[o], NAMES[o[0]], NAMES[o[1]]) for o in opts if clears([o]))
        two = []
        for i, o1 in enumerate(opts):
            for o2 in opts[i + 1:]:
                if o1[0] == o2[0] or o1[0] == o2[1] or o1[1] == o2[0] or pd_cache[o1] + pd_cache[o2] > 90:
                    continue
                if clears([o1, o2]):
                    two.append((pd_cache[o1] + pd_cache[o2], NAMES[o1[0]] + ">" + NAMES[o1[1]], NAMES[o2[0]] + ">" + NAMES[o2[1]]))
        two.sort()
        R["win8"].setdefault("clear_" + k, dict(windows=len(ws), one=one[:5], two=two[:8]))
        print("CLEAR", k, len(ws), one[:3], two[:5])
    combos = {"cactus->grass": [("cactus", "grass")], "town4+town5->town1": [("town4", "town1"), ("town5", "town1")], "town1@z+town1@n->town1": [("town1@z", "town1"), ("town1@n", "town1")],
              "all six small": [(n, pm[n]["options"][0]["into"]) for n in SMALL]}
    R["merge_combos"] = {}
    for k, lst in combos.items():
        e2 = e0.clone()
        for a, b in lst:
            ai, bi = NAMES.index(a), NAMES.index(b)
            e2 = merge_edit(e2, ai, bi, palette_distance(ai, bi)[1])
        mm = Metrics(e2)
        wl = {nm: int(sum(1 for i, w in enumerate(wins) if mm.pal_w[i] >= 8 and w[0] <= a0 and w[1] >= a1 and w[2] <= b0 and w[3] >= b1))
              for nm, (a0, a1, b0, b1) in (("west", (35, 37, 44, 46)), ("east", (50, 52, 44, 46)))}
        R["merge_combos"][k] = dict(merges=lst, wedge_windows_left=wl, **delta(base, mm))
        print("COMBO", k, R["merge_combos"][k])
    # the stray-pixel fringe tiles (1 to 2 stray pixels on otherwise flat ground) folded into the flat tile; the spruce redrawn as the pine
    fl = bytes(64)
    stray = {}
    for d in (1, 2):
        ec, _, cc, pc = near_simulate(e0, "C", d, True, centre=fl)
        ed, _, cd, pd_ = near_simulate(e0, "D", d, False, centre=fl)
        eb = ec.clone()
        eb.D = ed.D
        stray[d] = dict(color_cells=cc, color_px=pc, dmg_cells=cd, dmg_px=pd_, **delta(base, Metrics(eb)))
        print("STRAY", d, stray[d])
    R["stray"] = stray
    sw = {}
    e_s = e0.clone()
    for which in ("C", "D"):
        e_s, nd, nb = swap_family(e_s, which, fam["SPRUCE"], (instC if which == "C" else instD)["SPRUCE"], fam["PINE"])
        sw[which] = (nd, nb)
    R["spruce_to_pine"] = dict(done=sw, **delta(base, Metrics(e_s)))
    print("SPRUCE->PINE", R["spruce_to_pine"])
    ec, *_ = near_simulate(e_snap, "C", 2, True)
    ed, *_ = near_simulate(ec, "D", 2, False)
    R["all_snap_near2"] = delta(base, Metrics(ed))
    print("ALL snap+near<=2", R["all_snap_near2"])
    (OUT / "reuse.json").write_text(json.dumps(R, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o)))
    print("wrote", OUT / "reuse.json")
    if sheet:
        import reuse_sheet
        reuse_sheet.make(e0, instC, instD, fam, R, sim)


if __name__ == "__main__":
    main()
