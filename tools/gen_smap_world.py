#!/usr/bin/env python3
"""The scrolling story map's world (owner 2026-11-04, Q76 / Q78): the hand-typed 64 x 48 cell world of tools/smap_world/ (the concept tools of
docs/dev/concepts/story_map_scroll_2026-11-04/round5, kept here as the art's source) -> banked data and the walking geometry.

    python3 tools/gen_smap_world.py build out/preview

writes
  build/smap_world.h     constants, the accessors' prototypes, the stops, the legs and the exits (included by src/smap.c)
  build/smap_wc_a.c      Color: the cells, the zone map, the fog, the slot plan and the palettes   (one bank, with its accessors)
  build/smap_wc_t.c      Color: the 2bpp tiles                                                      (one bank)
  build/smap_wd_a.c      DMG:   the cells, the zone map, the fog and the allocator's hints          (one bank, with its accessors)
  build/smap_wd_t.c      DMG:   the 2bpp tiles (the hand-trimmed DMG data set: world2.WORLD_DMG)    (one bank)
  build/smap_world.json  what the tests check against
  out/preview/smap_world_*.png  the whole world, late and early, Color and DMG

World model.  A cell is 8 x 8 px; cell c = row * 64 + column.  Unlock state p (1..10) = the number of venues open (the town is always open);
a cell is revealed when its zone's order (town 0, then the ten venues in chapter order) is <= p, else it shows cloud.  The cloud is computed as
tools/smap_world/world2.fog_tiles does: a cloud cell with no revealed neighbour (8 neighbours) is "interior" (one of four tiles by the cell's
parity, the state's inner palette); a cloud cell with a revealed neighbour is an "edge" cell and its tile is listed (the generator ran
world2.fog_tiles; the engine does not re-derive the edge sequence).  Both kinds are checked against world2.with_fog for every state.

Tiles.  Both data sets number their tiles in first-use order over the states 1..10 (identical 8 x 8 pixel blocks are one tile; the palette is
the cell's, not the tile's).  Color: a static slot plan (two tiles share a VRAM slot only when no 22 x 20 window of any state holds both; the 352
slots are the pool of ids 0-35 and 93-232 in each of the two VRAM banks); DMG: a dynamic allocator in 176 slots (the same pool, one bank), with a
hint byte per tile (the slot a min-conflict colouring gives it).  The generator fails the build when a 21 x 19 window needs more than 176 tiles on
DMG, more than 8 palettes on Color, or a tile has more than 239 cells in a 22 x 20 window.
"""
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT / "tools" / "smap_world"))
import world_snap as W  # noqa: E402  (the frozen integrated map, assets/smap/: tools/dev/smap_snapshot.py writes it)
PAL = W  # noqa: E402  (W.get(name): a palette's four colours, W.DMG_SHADE)

CW, CH = W.CW, W.CH
NCELLS = CW * CH
POOL = 176                       # BG ids 0-35 and 93-232 in one VRAM bank
MAX_SLOTS_C = 2 * POOL           # Color: both banks
NSTATE = 11                      # unlock states 1..10 = the venues open (the map is the same in all of them: the cloud is cut), 11 = the story is done and the fountain repaired
STATES = range(1, NSTATE + 1)
ORD = {"town": 0, W.REPAIR_ZONE: NSTATE}
for _i, _n in enumerate(W.ORDER):
    ORD[_n] = _i + 1
# the BG palettes the map uses (22: the snapshot lists them; the cloud palettes are gone with the cloud)
PAL_NAMES = list(W.PAL_NAMES)
FOG_PAL0 = 0                     # (the engine's cloud palette slots: unused, the cloud is cut)
STOP_ORDER = list(W.ORDER) + ["town"]            # stop index = chapter 0..9, 10 the town (src/smap.c)
VENUE_IDS = ["saloon", "stadium", "lodge", "bistro", "igloo", "factory", "cow", "tea", "zoo", "space"]       # the venue ids (the content's order: src/order.h)
_ord = [int(v) for v in __import__("re").search(r"ven_at\[10\] = \{([^}]*)\}", (ROOT / "src" / "order.h").read_text()).group(1).split(",")]
assert [VENUE_IDS[v] for v in _ord] == W.ORDER, ("src/order.h ven_at is not the map's order", [VENUE_IDS[v] for v in _ord], W.ORDER)
# The resting view at each stop (owner Q121, 11-07): where the camera stands while Sal does: (x, y, side). x, y: the screen's top-left in the world, None = Sal at the centre as
# when he walks (clamped to the world). side: where the name tag and the venue panel go there (1 the bottom, 0 the top): away from the venue's art.
# Stadium: the floodlights and the flag; space: the UFO and the peak. The other stops show their whole venue with the camera on Sal.
SAL_Y = 110                      # Sal's feet on the screen (owner Q9 11-08: low, so the top rows show on the top road); x stays at 80
STOP_VIEW = {}


def view_bytes(name):
    x, y, side = STOP_VIEW.get(name, (None, None, 1))
    assert all(v is None or (v % 2 == 0 and 0 <= v < 510) for v in (x, y)), (name, x, y)
    return (255 if x is None else x // 2, 255 if y is None else y // 2, side)


WIN_C = (22, 20)              # the loaded region: the 21 x 19 cells a view can show, plus one line ahead on each axis
WIN_V = (21, 19)
MAX_CELLS_IN_WIN = 239           # a DMG slot's use count is a byte (the engine keeps 0xF0.. free)
TILE_MAX = 1024                  # a cell word holds a 10-bit tile id, a 5-bit palette and (Color) the alternate-flip bit 15
FLIP_MERGE = True                # Color: mirror-image blocks share one tile id (see Model.merge_flips)


def rgb555(c):
    return (c[0] >> 3) | ((c[1] >> 3) << 5) | ((c[2] >> 3) << 10)


def sig_of(w, cx, cy):
    px = w.px
    return bytes(px[cy * 8 + j][cx * 8 + i] for j in range(8) for i in range(8))


def enc(sig):
    out = []
    for j in range(8):
        lo = hi = 0
        for i in range(8):
            v = sig[j * 8 + i]
            lo |= (v & 1) << (7 - i)
            hi |= (v >> 1) << (7 - i)
        out += [lo, hi]
    return out


def zone_orders():
    return np.array([[ORD[W.ZONE[y][x]] for x in range(CW)] for y in range(CH)], dtype=np.int32)


def state_world(world, p):
    return W.with_fog(world, {"town"} | set(W.ORDER[:p]) | ({W.REPAIR_ZONE} if p >= NSTATE else set()))


class Model:
    """One data set (Color or DMG): the tiles, the per-state grids, the cell words and the fog lists."""

    def __init__(self, cgb):
        self.cgb = cgb
        world = W.WORLD if cgb else W.WORLD_DMG
        self.world = world
        self.ids = {}                                # pixel block -> distinct block index (first-use order over the states)
        self.sigs = []                               # the distinct pixel blocks
        self.grids = {}                              # p -> (CH, CW) distinct block index; Color: replaced below by the tile id (see merge_flips)
        self.pals = {}                               # p -> (CH, CW) palette indices (Color)
        self.state_end = []
        prev = None
        for p in STATES:
            v = state_world(world, p)
            if prev is not None and v.px == prev.px and v.pal == prev.pal:       # (the same picture as the state before: the same grids)
                self.grids[p], self.pals[p] = self.grids[p - 1], self.pals[p - 1]
                self.state_end.append(len(self.sigs))
                continue
            prev = v
            g = np.zeros((CH, CW), dtype=np.int32)
            pl = np.zeros((CH, CW), dtype=np.int32)
            for y in range(CH):
                for x in range(CW):
                    s = sig_of(v, x, y)
                    t = self.ids.get(s)
                    if t is None:
                        t = self.ids[s] = len(self.sigs)
                        self.sigs.append(s)
                    g[y, x] = t
                    name = v.pal[y][x]
                    assert name in PAL_NAMES, name
                    pl[y, x] = PAL_NAMES.index(name)
            self.grids[p], self.pals[p] = g, pl
            self.state_end.append(len(self.sigs))
        self.nsig = len(self.sigs)                   # distinct 8 x 8 blocks
        self.all_sigs = list(self.sigs)
        self.sg = dict(self.grids)                   # distinct block index per cell and state (the truth the tests compare with)
        self.ustates = [p for p in STATES if p == 1 or self.grids[p] is not self.grids[p - 1]]      # the states that differ from the one before (the window checks run on those)
        self.alt = {p: np.zeros((CH, CW), dtype=np.int32) for p in STATES}      # the cell word's bit 15: the tile is shown with its alternate flip (Color only)
        self.altflip = []                            # per tile id: the alternate's attribute flip bits (1 = X, 2 = Y, 3 = both), 0 = none (Color only)
        if cgb and FLIP_MERGE:
            self.merge_flips()
        if not self.altflip:
            self.altflip = [0] * len(self.sigs)
        self.nt = len(self.sigs)
        assert self.nt < TILE_MAX
        assert not cgb or self.nt * 16 + 69 <= 16384, f"Color: {self.nt} tiles do not fit one ROM bank"
        # revealed display of every cell = the late world (state 10)
        self.cell = [int(self.grids[NSTATE][y, x]) | (int(self.pals[NSTATE][y, x]) << 10 if cgb else 0) | (int(self.alt[NSTATE][y, x]) << 15) for y in range(CH) for x in range(CW)]
        self.build_fog()

    # ---- the Color flip-merge: a tile id stands for a canonical block and one alternate (its mirror image), shown with the attribute's flip bits ------------------
    def merge_flips(self):
        """Two blocks that are mirror images of each other (X, Y or both) share one tile id: the cell word's bit 15 selects the alternate and the slot table's bits 11-12 say which flip
        it is.  A tile id has at most one alternate, so a family of four distinct mirror images takes two ids.  A block shown in an animated cell is pinned (its own id, nothing merged into
        it: the animation rewrites the one tile, every cell of the id would play it)."""
        sigs = self.sigs
        pinned = set()
        for (cx, cy) in getattr(W, "ANIM_CELLS", ()):
            for p in STATES:
                pinned.add(int(self.sg[p][cy, cx]))

        def fx(s):
            return bytes(s[j * 8 + 7 - i] for j in range(8) for i in range(8))

        def fy(s):
            return bytes(s[(7 - j) * 8 + i] for j in range(8) for i in range(8))

        def fxy(s):
            return fx(fy(s))
        FL = ((1, fx), (2, fy), (3, fxy))
        index = {s: i for i, s in enumerate(sigs)}
        family = {}
        for i, s in enumerate(sigs):
            key = min((s, fx(s), fy(s), fxy(s)))
            family.setdefault(key, []).append(i)
        base_of = {}                                  # distinct block index -> (base block index, flip bits to get it: 0 for the base itself)
        for key, mem in family.items():
            free = [i for i in mem if i not in pinned]
            for i in mem:
                if i in pinned:
                    base_of[i] = (i, 0)
            while free:
                b = free.pop(0)
                base_of[b] = (b, 0)
                for k, (code, fn) in enumerate(FL):
                    a = index.get(fn(sigs[b]))
                    if a is not None and a != b and a in free:
                        free.remove(a)
                        base_of[a] = (b, code)
                        break
        # tile ids in first-use order of their base block, so the states' ids stay a prefix
        tid = {}
        new_sigs, altflip = [], []
        for i in range(len(sigs)):
            b, code = base_of[i]
            if b not in tid:
                tid[b] = len(new_sigs)
                new_sigs.append(sigs[b])
                altflip.append(0)
            if code:
                altflip[tid[b]] = code
        # state_end: the number of tile ids once every block first used up to state p is placed
        ends = []
        for e in self.state_end:
            seen_t = {tid[base_of[i][0]] for i in range(e)}
            ends.append(len(seen_t))
        self.merged_from = len(sigs)
        for p in STATES:
            if p > 1 and p not in self.ustates:
                self.grids[p], self.alt[p] = self.grids[p - 1], self.alt[p - 1]
                continue
            g = self.grids[p]
            tg = np.zeros_like(g)
            ag = np.zeros_like(g)
            for y in range(CH):
                for x in range(CW):
                    b, code = base_of[int(g[y, x])]
                    tg[y, x] = tid[b]
                    ag[y, x] = 1 if code else 0
            self.grids[p] = tg
            self.alt[p] = ag
        self.sigs = new_sigs
        self.altflip = altflip
        self.state_end = ends

    def word_sig(self, w):
        """the 64 pixels a cell word shows (Color: the tile id's block, mirrored when bit 15 is set)"""
        s = self.sigs[w & 1023]
        code = self.altflip[w & 1023] if self.cgb and (w >> 15) & 1 else 0
        if code & 1:
            s = bytes(s[j * 8 + 7 - i] for j in range(8) for i in range(8))
        if code & 2:
            s = bytes(s[(7 - j) * 8 + i] for j in range(8) for i in range(8))
        return s

    # ---- the fog ----------------------------------------------------------------------------------------------------------------------
    def build_fog(self):
        Z = zone_orders()
        self.zone = []
        for y in range(CH):
            for x in range(CW):
                nb = [Z[y + dy, x + dx] for dy in (-1, 0, 1) for dx in (-1, 0, 1) if (dx or dy) and 0 <= x + dx < CW and 0 <= y + dy < CH]
                self.zone.append(int(Z[y, x]) | (min(min(nb), 15) << 4))
        self.fog_cell, self.fog_word, self.fog_off = [], [], [0]
        self.inner = [0] * (NSTATE + 1)
        self.fogint = None
        ground = self.world
        for p in STATES:
            if p == NSTATE:
                self.fog_off.append(len(self.fog_cell))
                continue
            fog = {(x, y) for y in range(CH) for x in range(CW) if Z[y, x] > p}
            inner_cls = set()
            for y in range(CH):
                for x in range(CW):
                    if (x, y) not in fog:
                        continue
                    z = self.zone[y * CW + x]
                    t = int(self.grids[p][y, x]) | (int(self.alt[p][y, x]) << 15)      # (the word's tile part: id and the alternate bit)
                    pi = int(self.pals[p][y, x]) if self.cgb else 0
                    if (z >> 4) > p:                 # interior
                        par = (x & 1) | ((y & 1) << 1)
                        if self.fogint is None:
                            self.fogint = [None] * 4
                        if self.fogint[par] is None:
                            self.fogint[par] = t
                        assert self.fogint[par] == t, (p, x, y)
                        if self.cgb:
                            inner_cls.add(pi)
                    else:                            # edge: listed
                        self.fog_cell.append(y * CW + x)
                        self.fog_word.append(t | (pi << 10))
            if self.cgb:
                assert len(inner_cls) <= 1, (p, inner_cls)
                self.inner[p] = inner_cls.pop() if inner_cls else FOG_PAL0 + 2
            else:
                self.inner[p] = FOG_PAL0 + 2
            # sort this state's slice by cell
            lo = self.fog_off[-1]
            pairs = sorted(zip(self.fog_cell[lo:], self.fog_word[lo:]))
            self.fog_cell[lo:] = [c for c, _ in pairs]
            self.fog_word[lo:] = [w for _, w in pairs]
            self.fog_off.append(len(self.fog_cell))
        if self.fogint is None or None in self.fogint:
            self.fogint = [(0 if f is None else f) for f in (self.fogint or [None] * 4)]
        # the cloud tiles must stay in the tile set; the four interior tiles are listed

    def disp(self, c, p):
        """The word the engine shows at cell c in state p (mirrors the generated accessor)."""
        z = self.zone[c]
        if (z & 15) <= p:
            return self.cell[c]
        if (z >> 4) > p:
            return self.fogint[(c & 1) | ((c >> 5) & 2)] | ((self.inner[p] << 10) if self.cgb else 0)
        lo, hi = self.fog_off[p - 1], self.fog_off[p]
        for k in range(lo, hi):
            if self.fog_cell[k] == c:
                return self.fog_word[k]
        raise AssertionError((c, p))

    def verify_fog(self):
        for p in STATES:
            for y in range(CH):
                for x in range(CW):
                    w = self.disp(y * CW + x, p)
                    assert self.word_sig(w) == self.all_sigs[int(self.sg[p][y, x])], (self.cgb, p, x, y)
                    if self.cgb:
                        assert ((w >> 10) & 31) == int(self.pals[p][y, x]), (self.cgb, p, x, y)

    # ---- windows -----------------------------------------------------------------------------------------------------------------------
    def window_max(self, ww, wh):
        best, at = 0, None
        for p in self.ustates:
            g = self.grids[p]
            for y0 in range(CH - wh + 1):
                for x0 in range(CW - ww + 1):
                    n = len(np.unique(g[y0:y0 + wh, x0:x0 + ww]))
                    if n > best:
                        best, at = n, (p, x0, y0)
        return best, at

    def palette_max(self, ww, wh):
        best, at = 0, None
        for p in self.ustates:
            g = self.pals[p]
            for y0 in range(CH - wh + 1):
                for x0 in range(CW - ww + 1):
                    n = len(np.unique(g[y0:y0 + wh, x0:x0 + ww]))
                    if n > best:
                        best, at = n, (p, x0, y0)
        return best, at

    def max_uses(self, ww, wh):
        mx = 0
        for p in self.ustates:
            g = self.grids[p]
            for y0 in range(CH - wh + 1):
                for x0 in range(CW - ww + 1):
                    c = np.bincount(g[y0:y0 + wh, x0:x0 + ww].ravel())
                    mx = max(mx, int(c.max()))
        return mx

    # ---- conflicts: two tiles conflict when one ww x wh window of some state holds both ------------------------------------------------------
    def conflicts(self, ww, wh):
        n = self.nt
        conf = np.zeros((n, n), dtype=bool)
        for p in self.ustates:
            g = self.grids[p]
            present = np.unique(g)
            m = {int(t): i for i, t in enumerate(present)}
            O = np.zeros((len(present), CH, CW), dtype=np.float32)
            for y in range(CH):
                for x in range(CW):
                    O[m[int(g[y, x])], y, x] = 1
            D = dilate(O, ww - 1, wh - 1)
            M = (D.reshape(len(present), -1) @ O.reshape(len(present), -1).T) > 0
            idx = np.array([int(t) for t in present])
            conf[np.ix_(idx, idx)] |= M
        np.fill_diagonal(conf, False)
        return conf


def dilate(O, rx, ry):
    """max-filter by +-rx, +-ry on the last two axes (a 0/1 array): a cell is set when a set cell lies within the radius"""
    def one(a, r, axis):
        n = a.shape[axis]
        pad = [(0, 0)] * a.ndim
        pad[axis] = (r + 1, r)
        c = np.cumsum(np.pad(a, pad), axis=axis)
        hi = np.take(c, np.arange(2 * r + 1, 2 * r + 1 + n), axis=axis)
        lo = np.take(c, np.arange(0, n), axis=axis)
        return (hi - lo) > 0
    a = one(O, rx, O.ndim - 1).astype(np.float32)
    return one(a, ry, O.ndim - 2).astype(np.float32)


def colour(conf, k_max, spread):
    """DSATUR colouring of the conflict graph.  spread: take the allowed colour with the fewest tiles (the tile stays resident longest), else the
    lowest.  Returns (colour per tile, the number of colours used)."""
    n = conf.shape[0]
    col = -np.ones(n, dtype=np.int32)
    sat = [set() for _ in range(n)]
    deg = conf.sum(1)
    used = 0
    size = np.zeros(k_max, dtype=np.int32)
    for _ in range(n):
        best, bv = -1, None
        for v in range(n):
            if col[v] >= 0:
                continue
            key = (len(sat[v]), int(deg[v]))
            if bv is None or key > best:
                best, bv = key, v
        v = bv
        bad = {int(col[u]) for u in np.nonzero(conf[v])[0] if col[u] >= 0}
        if spread:
            allowed = [c for c in range(k_max) if c not in bad]
            c = min(allowed, key=lambda c: (size[c], c))
        else:
            c = 0
            while c in bad:
                c += 1
        assert c < k_max, "no colour left"
        col[v] = c
        size[c] += 1
        used = max(used, c + 1)
        for u in np.nonzero(conf[v])[0]:
            sat[u].add(c)
    return col, used


def min_conflict(conf, weight, k):
    """Colour with at most k colours, allowing conflicts: each tile (most conflicted first) takes the colour with the least conflict weight with
    its already coloured neighbours (ties: the fewest tiles).  Returns the colour per tile and the number of conflicting pairs left."""
    n = conf.shape[0]
    order = sorted(range(n), key=lambda v: -int(conf[v].sum()))
    col = -np.ones(n, dtype=np.int32)
    size = np.zeros(k, dtype=np.int32)
    for v in order:
        cost = np.zeros(k)
        for u in np.nonzero(conf[v])[0]:
            if col[u] >= 0:
                cost[col[u]] += weight[v, u]
        c = min(range(k), key=lambda c: (cost[c], size[c], c))
        col[v] = c
        size[c] += 1
    bad = sum(1 for v in range(n) for u in np.nonzero(conf[v])[0] if u > v and col[u] == col[v])
    return col, bad


def path_windows(stops, legs, pad=1):
    """The cell windows the region can hold while Sal walks: for every pixel of every leg (and every stop) the camera's view (Sal's feet at the screen's
    centre, clamped to the world) in cells, padded by pad cells on every side (the line ahead, the one the drop has not yet taken)."""
    def cam(fx, fy):
        return min(max(fx - 80, 0), CW * 8 - 160), min(max(fy - SAL_Y, 0), CH * 8 - 144)
    wins = set()

    def add(fx, fy):
        cx, cy = cam(fx, fy)
        wins.add((max((cx >> 3) - pad, 0), min(((cx + 159) >> 3) + pad, CW - 1), max((cy >> 3) - pad, 0), min(((cy + 143) >> 3) + pad, CH - 1)))
    for sx, sy in stops:
        add(sx, sy)
    for n, (sx, sy) in zip(STOP_ORDER, stops):           # the resting views (STOP_VIEW): the camera stands there too, and the walk leaves from there
        vx, vy, _ = STOP_VIEW.get(n, (None, None, 1))
        if vx is not None or vy is not None:
            for i in range(33):                          # (and the glide between the view and Sal's follow spot: the camera crosses these windows, in steps of 2 px)
                add(sx if vx is None else vx + 80 + (sx - 80 - vx) * i // 32, sy if vy is None else vy + SAL_Y + (sy - SAL_Y - vy) * i // 32)
    for a, b, pts in legs:
        for k in range(len(pts) - 1):
            (x0, y0), (x1, y1) = pts[k], pts[k + 1]
            n = max(abs(x1 - x0), abs(y1 - y0), 1)
            for i in range(n + 1):
                add(x0 + (x1 - x0) * i // n, y0 + (y1 - y0) * i // n)
    return sorted(wins)


def path_windows_lead(legs, ahead=24):
    """The windows the REGION holds while Sal walks (smap_region_work): the camera's view plus one line ahead on the axis of travel, in the direction of travel; within `ahead` px of a corner
    the next stretch's line too (WALK_AHEAD).  Every leg both ways.  (c0, c1, r0, r1, axis, side): axis 'x' or 'y' and side -1 (low end) or 1 (high end) of the one lead line, or None
    where two lines lead (a corner) or none does."""
    def cam(fx, fy):
        return min(max(fx - 80, 0), CW * 8 - 160), min(max(fy - SAL_Y, 0), CH * 8 - 144)
    sg = lambda v: (v > 0) - (v < 0)
    wins = set()
    for a, b, pts0 in legs:
        for pts in (pts0, pts0[::-1]):
            for k in range(len(pts) - 1):
                (x0, y0), (x1, y1) = pts[k], pts[k + 1]
                n = max(abs(x1 - x0), abs(y1 - y0), 1)
                leads = [(sg(x1 - x0), sg(y1 - y0))]
                nxt = (sg(pts[k + 2][0] - x1), sg(pts[k + 2][1] - y1)) if k + 2 < len(pts) else None
                for i in range(n + 1):
                    cx, cy = cam(x0 + (x1 - x0) * i // n, y0 + (y1 - y0) * i // n)
                    c0, c1, r0, r1 = cx >> 3, (cx + 159) >> 3, cy >> 3, (cy + 143) >> 3
                    ls = leads + ([nxt] if nxt and n - i <= ahead else [])
                    for dx, dy in ls:
                        c0 -= dx < 0; c1 += dx > 0; r0 -= dy < 0; r1 += dy > 0
                    c0, c1, r0, r1 = max(c0, 0), min(c1, CW - 1), max(r0, 0), min(r1, CH - 1)
                    ax, side = None, 0
                    if len(ls) == 1 and (ls[0][0] == 0) != (ls[0][1] == 0):
                        ax, side = ("x", ls[0][0]) if ls[0][0] else ("y", ls[0][1])
                        if (ax == "x" and ((side < 0 and c0 == cx >> 3) or (side > 0 and c1 == (cx + 159) >> 3))) or \
                           (ax == "y" and ((side < 0 and r0 == cy >> 3) or (side > 0 and r1 == (cy + 143) >> 3))):
                            ax = None                    # (the world's edge: no line ahead)
                    wins.add((c0, c1, r0, r1, ax, side))
    return sorted(wins, key=str)


def palette_handovers(cg, wins):
    """The palette hand-over (src/smap_eng.c pal_alias / pal_hand): a window of the region may need a 9th BG palette when the one line that leads holds the only user of one palette (P)
    and the line at the other end, the last one the camera still shows, the only user of another (Q): the lead line is added with P on Q's hardware slot (off the screen), and the slot gets P's
    colours in the VBlank in which the line of Q has left the screen (the camera cannot show the lead line before).  Returns ({P: Q}, [failures])."""
    ret, bad = {}, []
    for p in cg.ustates:
        gr = cg.pals[p]
        for (c0, c1, r0, r1, ax, side) in wins:
            sub = gr[r0:r1 + 1, c0:c1 + 1]
            full = set(int(v) for v in np.unique(sub))
            if len(full) <= 8:
                continue
            if ax is None or len(full) > 9:
                bad.append((len(full), p, (c0, c1, r0, r1)))
                continue
            lo_line = (sub[0:1, :] if ax == "y" else sub[:, 0:1])
            hi_line = (sub[-1:, :] if ax == "y" else sub[:, -1:])
            lead, trail = (lo_line, hi_line) if side < 0 else (hi_line, lo_line)
            rest = (sub[1:, :] if ax == "y" else sub[:, 1:]) if side < 0 else (sub[:-1, :] if ax == "y" else sub[:, :-1])       # the window without the lead line
            aligned = (sub[:-1, :] if ax == "y" else sub[:, :-1]) if side < 0 else (sub[1:, :] if ax == "y" else sub[:, 1:])   # without the trailing line
            a, b = set(int(v) for v in np.unique(rest)), set(int(v) for v in np.unique(aligned))
            ps, qs = full - a, full - b
            if len(a) > 8 or len(b) > 8 or len(ps) != 1 or len(qs) != 1:
                bad.append((len(full), p, (c0, c1, r0, r1)))
                continue
            P, Q = ps.pop(), qs.pop()
            if ret.setdefault(P, Q) != Q:
                bad.append((len(full), p, (c0, c1, r0, r1), "two victims"))
    return ret, bad


def path_max(m, wins, grids):
    """the most distinct values (tile ids, or palettes) any window of wins holds in any unlock state: (n, (state, window))"""
    best, at = 0, None
    for p in m.ustates:
        gr = grids[p]
        for w in wins:
            n = len(np.unique(gr[w[2]:w[3] + 1, w[0]:w[1] + 1]))
            if n > best:
                best, at = n, (p, w)
    return best, at


def path_hints(dm, wins, k):
    """DMG allocator hints: the colouring that matters is the one of the windows the camera can actually show.  Tiles conflict when some such window of
    some state holds both; the weight of a pair is the number of such windows; a min-conflict pass, then local search until no tile gains by moving."""
    n = dm.nt
    conf = np.zeros((n, n), dtype=bool)
    wt = np.zeros((n, n), dtype=np.float32)
    for p in dm.ustates:
        gr = dm.grids[p]
        for (c0, c1, r0, r1) in wins:
            ts = np.unique(gr[r0:r1 + 1, c0:c1 + 1])
            conf[np.ix_(ts, ts)] = True
            wt[np.ix_(ts, ts)] += 1
    np.fill_diagonal(conf, False)
    col, _ = min_conflict(conf, wt, k)
    for _ in range(12):
        moved = 0
        for v in range(n):
            nb = np.nonzero(conf[v])[0]
            cost = np.zeros(k)
            np.add.at(cost, col[nb], wt[v, nb])
            best = int(np.argmin(cost))
            if cost[best] < cost[col[v]]:
                col[v] = best
                moved += 1
        if not moved:
            break
    bad = sum(1 for v in range(n) for u in np.nonzero(conf[v])[0] if u > v and col[u] == col[v])
    return col, bad


# ---- geometry ----------------------------------------------------------------------------------------------------------------------------
def geometry():
    stops = [W.STOPS[n] for n in STOP_ORDER]
    legs = []                                        # (a, b, [(x, y)...]) with a < b in stop index order of the leg's first entry
    seen = set()
    for (an, bn), pts in W.LEGS.items():
        a, b = STOP_ORDER.index(an), STOP_ORDER.index(bn)
        legs.append((a, b, pts))
    exits = [[255] * 4 for _ in stops]               # U, D, L, R: the neighbour stop
    exit_leg = [[255] * 4 for _ in stops]            # leg index | 0x80 when the leg runs b to a
    def leaving(s, pts):                             # the side the road leaves stop s: the first point 16 px or more away, dominant axis (owner 11-08)
        sx, sy = stops[s]
        for (x, y) in pts:
            dx, dy = x - sx, y - sy
            if max(abs(dx), abs(dy)) >= 16:
                return ((3 if dx > 0 else 2) if abs(dx) >= abs(dy) else (1 if dy > 0 else 0))
        raise AssertionError(f"leg of stop {s} never leaves it")
    old = []                                         # the old button, the straight line to the destination: it stays where no road leaves that side (bit 6 of exit_leg: no arrow)
    for li, (a, b, pts) in enumerate(legs):
        for (s, t, rev) in ((a, b, 0), (b, a, 1)):
            d = leaving(s, pts[::-1] if rev else pts)
            assert exits[s][d] == 255, f"two exits of stop {s} lie to the same side"
            exits[s][d] = t
            exit_leg[s][d] = li | (0x80 if rev else 0)
            dx, dy = stops[t][0] - stops[s][0], stops[t][1] - stops[s][1]
            old.append((s, t, li, rev, (3 if dx > 0 else 2) if abs(dx) >= abs(dy) else (1 if dy > 0 else 0)))
    for (s, t, li, rev, d) in old:
        if exits[s][d] == 255:
            exits[s][d] = t
            exit_leg[s][d] = li | (0x80 if rev else 0) | 0x40
    return stops, legs, exits, exit_leg


def reachable(exits, start=10):
    seen, todo = {start}, [start]
    while todo:
        s = todo.pop()
        for t in exits[s]:
            if t != 255 and t not in seen:
                seen.add(t)
                todo.append(t)
    return seen


# ---- output --------------------------------------------------------------------------------------------------------------------------------
def carr(typ, name, vals, per=12, hexw=0, const=True):
    body = []
    for i in range(0, len(vals), per):
        body.append("    " + ", ".join((f"0x{v:0{hexw}X}" if hexw else str(v)) for v in vals[i:i + per]) + ",")
    return f"{'const ' if const else ''}{typ} {name}[{len(vals)}] = {{\n" + "\n".join(body) + "\n};\n"


def emit_accessors_a(m, tag):
    """the cells bank: data and the accessors that read it (every read stays inside the one bank)"""
    cgb = m.cgb
    L = [f"// generated by tools/gen_smap_world.py -- do not edit ({'Color' if cgb else 'DMG'}: cells, zone map, cloud{', slot plan, palettes' if cgb else ', allocator hints'})",
         "#pragma bank 255", "#include <gb/gb.h>", "#include <stdint.h>", '#include "smap_world.h"', '#include "asm_cfg.h"', "", f"BANKREF({tag}_a)", f"BANKREF({tag}_cell)"]
    L.append(carr("uint16_t", f"{tag}_cell", m.cell, 12, 4))
    L.append(carr("uint8_t", f"{tag}_zone", m.zone, 16, 2))
    # the lists of the cloud's edge cells, one per state; states with the same list share it (here the fountain's cells are the same in states 1..10): foff = start, end of each state's
    fc, fw, span, seen = [], [], [], {}
    for i in range(NSTATE):
        lst = (tuple(m.fog_cell[m.fog_off[i]:m.fog_off[i + 1]]), tuple(m.fog_word[m.fog_off[i]:m.fog_off[i + 1]]))
        if lst not in seen:
            seen[lst] = (len(fc), len(fc) + len(lst[0]))
            fc += lst[0]
            fw += lst[1]
        span += list(seen[lst])
    L.append(carr("uint16_t", f"{tag}_fcell", fc or [0], 12, 4))
    L.append(carr("uint16_t", f"{tag}_fword", fw or [0], 12, 4))
    L.append(carr("uint16_t", f"{tag}_foff", span, 12, 4))
    L.append(carr("uint8_t", f"{tag}_inner", m.inner, NSTATE + 1))
    L.append(carr("uint16_t", f"{tag}_fint", m.fogint, 4, 4))
    if cgb:
        L.append(carr("uint16_t", f"{tag}_slotvar", m.slotvar, 12, 4))
        L.append(carr("uint16_t", f"{tag}_pal", m.pal_words, 4, 4))
    else:
        L.append(carr("uint8_t", f"{tag}_hint", m.hint, 16, 2))
    asm_open = asm_close = ""
    if True:
        asm_open = '''#if ASM_SMAP
// asm (behind ASM_SMAP; the C twin follows in the #else): the stack holds, at entry, the return address, the trampoline's 4 bytes, then cx, cy, n, vert, p, out (2).
// The loop's scratch lives in story_scratch's free bytes: V_BCAP (n), V_LIMC (p), V_LIMQ (vert). bc = the cell's index, de = the output pointer.
void smap_d_fetch(uint8_t cx, uint8_t cy, uint8_t n, uint8_t vert, uint8_t p, smap_fc *out) BANKED __naked {
    (void)cx; (void)cy; (void)n; (void)vert; (void)p; (void)out;
__asm
    ldhl sp, #6
    ld   a, (hl+)                           ; cx
    ld   c, a
    ld   a, (hl+)                           ; cy
    ld   e, a
    srl  a
    srl  a
    ld   b, a                               ; the index's high byte: cy >> 2
    ld   a, e
    and  a, #3
    rrca
    rrca                                    ; (cy & 3) << 6
    add  a, c
    ld   c, a
    jr   nc, 0$
    inc  b
0$:
    ld   a, (hl+)                           ; n
    or   a, a
    ret  z
    ld   (_story_scratch + 449), a
    ld   a, (hl+)                           ; vert
    ld   (_story_scratch + 453), a
    ld   a, (hl+)                           ; p
    ld   (_story_scratch + 452), a
    ld   a, (hl+)
    ld   e, a
    ld   d, (hl)                            ; out
1$:
    ld   hl, #_smap_d_zone
    add  hl, bc
    ld   a, (hl)
    ld   h, a                               ; h = z
    and  a, #15
    ld   l, a
    ld   a, (_story_scratch + 452)
    cp   a, l                               ; carry: z & 15 > p
    jr   c, 2$
    ld   hl, #_smap_d_cell                  ; the cell's word
    add  hl, bc
    add  hl, bc
    ld   a, (hl+)
    ld   h, (hl)
    ld   l, a
3$:                                         ; hl = the word to show
    ld   a, l
    ld   (de), a
    inc  de
    ld   a, h
    ld   (de), a
    inc  de
    and  a, #3
    ld   h, a
    push de
    ld   de, #_smap_d_hint
    add  hl, de
    pop  de
    ld   a, (hl)
    ld   (de), a
    inc  de
    xor  a, a
    ld   (de), a
    inc  de
    ld   a, (_story_scratch + 453)
    or   a, a
    jr   z, 5$
    ld   a, c
    add  a, #64
    ld   c, a
    jr   nc, 6$
    inc  b
    jr   6$
5$:
    inc  bc
6$:
    ld   hl, #_story_scratch + 449
    dec  (hl)
    jr   nz, 1$
    ret
2$:                                         ; h = z
    ld   a, h
    swap a
    and  a, #15
    ld   l, a
    ld   a, (_story_scratch + 452)
    cp   a, l
    jr   nc, 4$                             ; z >> 4 <= p: the cloud's edge
    ld   a, c                               ; the cloud's inside: fint[(c & 1) | ((c >> 5) & 2)]
    and  a, #0x40
    swap a
    srl  a
    ld   l, a
    ld   a, c
    and  a, #1
    or   a, l
    add  a, a
    ld   l, a
    ld   h, #0
    push de
    ld   de, #_smap_d_fint
    add  hl, de
    pop  de
    ld   a, (hl+)
    ld   h, (hl)
    ld   l, a
    jr   3$
4$:
    push de
    push bc
    ld   d, b
    ld   e, c
    ld   a, (_story_scratch + 452)
    call _smap_d_fogfind
    ld   h, b
    ld   l, c
    pop  bc
    pop  de
    jr   3$
__endasm;
}
#else
'''
        asm_close = "#endif\n"
        if cgb:                       # the Color's: the same loop, the aux word is slotvar[w & 0x3FF] (a word), the cloud's inside takes inner[p] << 10 (V_PWL is the Color's spare byte)
            asm_open = asm_open.replace("_smap_d_", "_smap_c_").replace("smap_d_fetch", "smap_c_fetch")
            blk = '''    and  a, #3
    ld   h, a
    push de
    ld   de, #_smap_c_hint
    add  hl, de
    pop  de
    ld   a, (hl)
    ld   (de), a
    inc  de
    xor  a, a
    ld   (de), a
    inc  de
'''.replace("_smap_c_hint", "_smap_c_hint")
            blk = blk.replace("_smap_c_hint", "_smap_c_hint")
            asm_open = asm_open.replace(blk.replace("_smap_c_hint", "_smap_c_hint"), '''    and  a, #3
    ld   h, a
    add  hl, hl
    push de
    ld   de, #_smap_c_slotvar
    add  hl, de
    pop  de
    ld   a, (hl+)
    ld   (de), a
    inc  de
    ld   a, (hl)
    ld   (de), a
    inc  de
''')
            assert "_smap_c_slotvar" in asm_open
            old = '''    ld   de, #_smap_c_fint
    add  hl, de
    pop  de
    ld   a, (hl+)
    ld   h, (hl)
    ld   l, a
    jr   3$
'''
            assert old in asm_open
            asm_open = asm_open.replace(old, '''    ld   de, #_smap_c_fint
    add  hl, de
    pop  de
    ld   a, (hl+)
    ld   h, (hl)
    ld   l, a
    push hl
    ld   a, (_story_scratch + 452)
    push de
    ld   e, a
    ld   d, #0
    ld   hl, #_smap_c_inner
    add  hl, de
    ld   a, (hl)
    pop  de
    add  a, a
    add  a, a
    ld   (_story_scratch + 450), a
    pop  hl
    ld   a, (_story_scratch + 450)
    or   a, h
    ld   h, a
    jr   3$
''')
    L.append(f"""
uint16_t {tag}_fogfind(uint16_t c, uint8_t p) {{
    uint16_t base = {tag}_foff[(uint8_t)(p - 1) << 1];          // (the lists of one state are < 256 long: asserted by the generator)
    uint8_t lo = 0, hi = (uint8_t)({tag}_foff[((uint8_t)(p - 1) << 1) + 1] - base), mid;
    while (lo < hi) {{
        mid = (uint8_t)((lo + hi) >> 1);
        if ({tag}_fcell[base + mid] < c) lo = mid + 1; else hi = mid;
    }}
    return {tag}_fword[base + lo];
}}

// n cells of one line (a row, or a column when vert) from (cx, cy) in unlock state p: the word to show ({'palette << 10 | ' if cgb else ''}tile) and the allocator's aux word
{asm_open}void {tag}_fetch(uint8_t cx, uint8_t cy, uint8_t n, uint8_t vert, uint8_t p, smap_fc *out) BANKED {{
    uint16_t c = (uint16_t)cy * 64 + cx, step = vert ? 64 : 1, w;
    uint8_t z;
    while (n--) {{
        z = {tag}_zone[c];
        if ((uint8_t)(z & 15) <= p) w = {tag}_cell[c];
        else if ((uint8_t)(z >> 4) > p) w = {tag}_fint[(uint8_t)(c & 1) | (uint8_t)((c >> 5) & 2)]{f' | ((uint16_t){tag}_inner[p] << 10)' if cgb else ''};
        else w = {tag}_fogfind(c, p);
        out->w = w;
        out->aux = {f'{tag}_slotvar[w & 0x3FF]' if cgb else f'{tag}_hint[w & 0x3FF]'};
        out++; c += step;
    }}
}}
{asm_close}""")
    if cgb:
        L.append(f"""
// palette i (0..17) as 8 bytes (little-endian words)
void {tag}_palette(uint8_t i, uint8_t *dst) BANKED {{
    const uint16_t *s = {tag}_pal + (uint16_t)i * 4;
    uint8_t k;
    for (k = 0; k < 4; k++) {{ *dst++ = (uint8_t)s[k]; *dst++ = (uint8_t)(s[k] >> 8); }}
}}
""")
    else:
        L.append(f"""
// tile t's hint slot (the allocator asks it of the tile a slot holds)
uint8_t {tag}_hintof(uint16_t t) BANKED {{ return {tag}_hint[t]; }}

#if ASM_SMAP
// asm, for smap_dadd (src/smap_eng.c, through the bank trampoline): the hint slot of tile b << 8 | c, in a
void {tag}_hintx(void) BANKED __naked {{
__asm
    ld   h, b
    ld   l, c
    ld   de, #_{tag}_hint
    add  hl, de
    ld   a, (hl)
    ret
__endasm;
}}
#endif
""")
    return "\n".join(L)


def emit_tiles(m, tag):
    data = []
    for s in m.sigs:
        data += enc(s)
    L = [f"// generated by tools/gen_smap_world.py -- do not edit ({'Color' if m.cgb else 'DMG'} tiles: {m.nt} x 16 bytes, first-use order over the unlock states)",
         "#pragma bank 255", "#include <gb/gb.h>", "#include <stdint.h>", '#include "smap_world.h"', '#include "asm_cfg.h"', "", f"BANKREF({tag}_t)",
         carr("uint8_t", f"{tag}_tiles", data, 16, 2),
         f"// tile t's 16 bytes to dst (the engine stages them in WRAM: the copy list reads WRAM only)",
         "#if ASM_SMAP",
         "// asm (the C twin follows in the #else): the stack holds, at entry, the return address, the trampoline's 4 bytes, then t and dst. 16 bytes unrolled: under a line, where the loop took 16",
         f"void {tag}_tile(uint16_t t, uint8_t *dst) BANKED __naked {{",
         "    (void)t; (void)dst;",
         "__asm",
         "    ldhl sp, #6",
         "    ld   a, (hl+)",
         "    ld   e, a",
         "    ld   a, (hl+)",
         "    ld   d, a                               ; de = t",
         "    ld   a, (hl+)",
         "    ld   c, a",
         "    ld   b, (hl)                            ; bc = dst",
         "    ld   h, d",
         "    ld   l, e",
         "    add  hl, hl",
         "    add  hl, hl",
         "    add  hl, hl",
         "    add  hl, hl                             ; hl = t << 4",
         f"    ld   de, #_{tag}_tiles",
         "    add  hl, de",
         "    ld   d, b",
         "    ld   e, c",
         ] + ["    ld   a, (hl+)\n    ld   (de), a\n    inc  de"] * 15 + [
         "    ld   a, (hl)",
         "    ld   (de), a",
         "    ret",
         "__endasm;",
         "}",
         "#else",
         f"void {tag}_tile(uint16_t t, uint8_t *dst) BANKED {{",
         f"    const uint8_t *s = {tag}_tiles + (t << 4);",
         "    uint8_t k;",
         "    for (k = 0; k < 16; k++) dst[k] = s[k];",
         "}",
         "#endif", ""]
    if not m.cgb:        # DMG only: smap_dadd's tile copy (it reaches this bank through the trampoline, with no arguments on the stack)
        tc = [f"#if ASM_SMAP",
              f"// asm, for smap_dadd (through the bank trampoline): tile t (story_scratch + 450, 451: V_PWL, V_PWH) into the staging slot V_NSTG (story_scratch + 438), 16 bytes unrolled",
              f"void {tag}_tcopy(void) BANKED __naked {{",
              "__asm",
              "    ld   a, (_story_scratch + 450)", "    ld   l, a", "    ld   a, (_story_scratch + 451)", "    ld   h, a",
              "    add  hl, hl", "    add  hl, hl", "    add  hl, hl", "    add  hl, hl",
              f"    ld   de, #_{tag}_tiles", "    add  hl, de",
              "    ld   a, (_story_scratch + 438)", "    swap a", "    and  a, #0xF0", "    add  a, #<(_story_scratch + 464)", "    ld   e, a",
              "    ld   a, #>(_story_scratch + 464)", "    adc  a, #0", "    ld   d, a"] + ["    ld   a, (hl+)\n    ld   (de), a\n    inc  de"] * 15 + [
              "    ld   a, (hl)", "    ld   (de), a", "    ret", "__endasm;", "}", "#endif", ""]
        L += tc
    return "\n".join(L), data


def main(build, preview):
    build, preview = Path(build), Path(preview)
    build.mkdir(parents=True, exist_ok=True)
    preview.mkdir(parents=True, exist_ok=True)
    cg, dm = Model(True), Model(False)
    cg.verify_fog()
    dm.verify_fog()
    # ---- budgets (a failed check stops the build) -------------------------------------------------------------------------------------
    fail = []
    n21, at21 = dm.window_max(*WIN_V)
    n22, at22 = dm.window_max(*WIN_C)
    if n21 > POOL:
        fail.append(f"DMG: a 21 x 19 window holds {n21} tiles at {at21}, the pool is {POOL}")
    for w in (WIN_V, (21, 18), (20, 19)):
        if dm.window_max(*w)[0] > POOL:
            fail.append(f"DMG: a {w[0]} x {w[1]} window is over {POOL}")
    p21, pat21 = cg.palette_max(*WIN_V)
    # The generic 21 x 19 sweep counts every position of the map, most of which the camera never shows (it follows the legs, the stops and the glides).  The palette limit is enforced on the real views:
    # the path windows (padded by a line, and the lead windows with the hand-over) a few lines below.  The sweep is kept as a warning, so a new palette near a place the camera could not reach is seen.
    if p21 > 8:
        print(f"smap world WARNING: a generic 21 x 19 window needs {p21} palettes at {pat21} (the path views and the hand-over decide: see the checks below)")
    p22, _ = cg.palette_max(*WIN_C)
    uses = dm.max_uses(*WIN_C)
    if uses > MAX_CELLS_IN_WIN:
        fail.append(f"DMG: a tile fills {uses} cells of a 22 x 20 window (a use count is a byte)")
    if any(cg.fog_off[i + 1] - cg.fog_off[i] > 255 for i in range(NSTATE)) or any(dm.fog_off[i + 1] - dm.fog_off[i] > 255 for i in range(NSTATE)):
        fail.append("a state's list of cloud edge cells is longer than 255")
    # ---- the slot plans ----------------------------------------------------------------------------------------------------------------------
    conf_c = cg.conflicts(*WIN_C)
    col_min, k_min = colour(conf_c, MAX_SLOTS_C, False)
    col_c, k_c = colour(conf_c, MAX_SLOTS_C, True)       # the spread plan: every one of the 352 slots used before two tiles share one
    var_n = Counter(int(c) for c in col_c)
    var_idx, seen = {}, Counter()
    for t in range(cg.nt):
        c = int(col_c[t])
        var_idx[t] = seen[c]
        seen[c] += 1
    nvar = max(seen.values())
    if nvar > 4:
        fail.append(f"Color: a slot is shared by {nvar} tiles (a variant is two bits of the slot table: bits 11-12 are the alternate's flips)")
    nslots = k_c
    cg.slotvar = [int(col_c[t]) | (var_idx[t] << 9) | (cg.altflip[t] << 11) for t in range(cg.nt)]      # slot (9 bits), variant (2 bits), the alternate's flip bits (2 bits)
    cg.pal_words = []
    for name in PAL_NAMES:
        cols = PAL.get(name)
        cg.pal_words += [rgb555(c) for c in cols]
    # the DMG hints: a min-conflict colouring of the DMG tiles in 176 slots (the allocator takes a tile's hint slot when it is free)
    stops, legs, exits, exit_leg = geometry()
    pw = path_windows(stops, legs)
    wd, wp = path_max(dm, pw, dm.grids), path_max(cg, path_windows(stops, legs, 0), cg.pals)       # the windows the camera can hold on the walk and at the stops
    print(f"smap world path windows: DMG worst padded {wd[0]} of {POOL} at {wd[1]}, Color worst view palettes {wp[0]} of 8 at {wp[1]}")
    # (the region holds the view, a line ahead and the line the drop has not taken yet: the padded windows; the plain views hid a 9th palette at the zoo <-> space bend, a hold on Color)
    pwl = path_windows_lead(legs)
    handover, pbad = palette_handovers(cg, pwl)
    print(f"smap world path windows: Color lead windows over 8 palettes handled by the hand-over {dict((PAL_NAMES[k], PAL_NAMES[v]) for k, v in handover.items())}, unhandled {len(pbad)}")
    if wd[0] > POOL:
        fail.append(f"DMG: a padded path window holds {wd[0]} tiles at {wd[1]}, the pool is {POOL}")
    if wp[0] > 8:
        fail.append(f"Color: a path view needs {wp[0]} palettes at {wp[1]}")
    if pbad:
        fail.append(f"Color: a lead window needs more palettes than the hand-over can give (the walk holds for a slot): {pbad[:3]}")
    col_d, bad_d = path_hints(dm, pw, POOL)
    dm.hint = [int(c) for c in col_d]
    if fail:
        print("gen_smap_world: BUDGET FAILURES\n  " + "\n  ".join(fail), file=sys.stderr)
        sys.exit(1)
    # ---- geometry ------------------------------------------------------------------------------------------------------------------------
    assert reachable(exits) == set(range(11)), "a stop cannot be reached from the town along the legs"
    # ---- files -------------------------------------------------------------------------------------------------------------------------------
    ufo = (W.VENUES["space"][1][0] * 8 + 8, W.VENUES["space"][1][1] * 8 + 34)
    h = ["// generated by tools/gen_smap_world.py -- do not edit", "#ifndef SMAP_WORLD_H", "#define SMAP_WORLD_H", "#include <stdint.h>", "",
         f"#define SMAPW_CW 64", f"#define SMAPW_CH {CH}", f"#define SMAPW_C_TILES {cg.nt}", f"#define SMAPW_D_TILES {dm.nt}",
         f"#define SMAPW_C_SLOTS {nslots}", f"#define SMAPW_POOL {POOL}", f"#define SMAPW_NPAL {len(PAL_NAMES)}", f"#define SMAPW_PAL_TOWN {PAL_NAMES.index('town1')}",
         f"#define SMAPW_UFO_X {ufo[0]}", f"#define SMAPW_UFO_Y {ufo[1]}",
         f"#define SMAPW_BANG_X {stops[10][0] - 4}", f"#define SMAPW_BANG_Y {stops[10][1] - 36}",
         "typedef struct { uint16_t w, aux; } smap_fc;   // one fetched cell: the word to show, the allocator's word (Color: slot | variant << 9; DMG: the hint slot)",
         "void smap_c_fetch(uint8_t cx, uint8_t cy, uint8_t n, uint8_t vert, uint8_t p, smap_fc *out) BANKED;",
         "void smap_c_palette(uint8_t i, uint8_t *dst) BANKED;",
         "void smap_c_tile(uint16_t t, uint8_t *dst) BANKED;",
         "void smap_d_fetch(uint8_t cx, uint8_t cy, uint8_t n, uint8_t vert, uint8_t p, smap_fc *out) BANKED;",
         "void smap_d_tile(uint16_t t, uint8_t *dst) BANKED;",
         "uint8_t smap_d_hintof(uint16_t t) BANKED;", "",
         "#ifdef SMAPW_VIEWS      // (src/smap_eng.c alone) each stop's resting view: camera x / 2, y / 2 (255: follow Sal), the side of the tag and the panel (1 the bottom)",
         "static const uint8_t smapw_view[11][3] = { " + ", ".join("{ %d, %d, %d }" % view_bytes(n) for n in STOP_ORDER) + " };",
         "static const uint8_t smapw_ret[%d] = { " % len(PAL_NAMES) + ", ".join(str(handover.get(i, 255)) for i in range(len(PAL_NAMES))) + " };   // the palette hand-over: the palette whose hardware slot palette i may borrow for a line the camera cannot show yet (255: none)",
         "#endif",
         "#ifdef SMAPW_GEOMETRY   // (src/smap.c alone)",
         f"static const uint16_t smapw_stop[11][2] = {{ " + ", ".join("{ %d, %d }" % s for s in stops) + " };",
         f"static const uint8_t smapw_stopc[11][2] = {{ " + ", ".join("{ %d, %d }" % (s[0] >> 3, s[1] >> 3) for s in stops) + " };   // (the stops' cells: the dots' quick cull)",
         "static const uint8_t smapw_exit[11][4] = {   // U, D, L, R: the stop that button walks to (255: none)"]
    for s in range(11):
        h.append("    { " + ", ".join(str(v) for v in exits[s]) + " },")
    h.append("};")
    h.append("static const uint8_t smapw_exit_leg[11][4] = {   // the leg of that exit, bit 7 set when it is walked backwards, bit 6 a button with no arrow (the old direction to the stop)")
    for s in range(11):
        h.append("    { " + ", ".join(str(v) for v in exit_leg[s]) + " },")
    h.append("};")
    h.append(f"static const uint8_t smapw_leg_n[{len(legs)}] = {{ " + ", ".join(str(len(p)) for _, _, p in legs) + " };")
    h.append(f"static const uint16_t smapw_leg_pt[{len(legs)}][4][2] = {{")
    for _, _, p in legs:
        pts = list(p) + [(0, 0)] * (4 - len(p))
        h.append("    { " + ", ".join("{ %d, %d }" % q for q in pts) + " },")
    h.append("};")
    h.append("#endif")
    h.append("#endif")
    (build / "smap_world.h").write_text("\n".join(h) + "\n")
    (build / "smap_wc_a.c").write_text(emit_accessors_a(cg, "smap_c"))
    (build / "smap_wd_a.c").write_text(emit_accessors_a(dm, "smap_d"))
    tc, dc = emit_tiles(cg, "smap_c")
    td, dd = emit_tiles(dm, "smap_d")
    (build / "smap_wc_t.c").write_text(tc)
    (build / "smap_wd_t.c").write_text(td)
    pal_cols = [[rgb555(c) for c in PAL.get(n)] for n in PAL_NAMES]
    info = {
        "stops": stops, "stop_order": STOP_ORDER, "legs": [[a, b, [list(q) for q in p]] for a, b, p in legs], "exits": exits, "exit_leg": exit_leg,
        "ufo": ufo, "cw": CW, "ch": CH, "ndmg": dm.nt, "ncgb": cg.nt, "ncgb_blocks": cg.nsig, "alt_flip_c": cg.altflip, "slots_c": nslots, "slots_c_min": k_min, "vars_max": nvar, "pal_names": PAL_NAMES, "pal": pal_cols,
        "state_end_c": cg.state_end, "state_end_d": dm.state_end, "tiles_c": bytes(dc).hex(), "tiles_d": bytes(dd).hex(),
        "win_d_21x19": n21, "win_d_22x20": n22, "win_c_pal_21x19": p21, "win_c_pal_22x20": p22, "uses_max_22x20": uses, "hint_conflicts": int(bad_d),
        "slot_of_c": [int(c) for c in col_c], "var_of_c": [var_idx[t] for t in range(cg.nt)], "hint_d": dm.hint,
        "fog_c": [cg.fog_off, cg.fog_cell, cg.fog_word], "fog_d": [dm.fog_off, dm.fog_cell, dm.fog_word], "inner_c": cg.inner, "fogint_c": cg.fogint, "fogint_d": dm.fogint,
        "zone": cg.zone, "cell_c": cg.cell, "cell_d": dm.cell,
        "disp_c": [[cg.disp(c, p) for c in range(CW * CH)] for p in STATES], "disp_d": [[dm.disp(c, p) for c in range(CW * CH)] for p in STATES],   # the world shown in unlock state p (the tests expected pictures)
    }
    (build / "smap_world.json").write_text(json.dumps(info, default=int))
    # ---- previews ------------------------------------------------------------------------------------------------------------------------------
    try:
        from PIL import Image
        for name, m in (("cgb", cg), ("dmg", dm)):
            for p in (1, NSTATE):
                im = Image.new("RGB", (CW * 8, CH * 8))
                for y in range(CH):
                    for x in range(CW):
                        w = m.disp(y * CW + x, p)
                        cols = PAL.get(PAL_NAMES[(w >> 10) & 31]) if m.cgb else None
                        s = m.word_sig(w)
                        for j in range(8):
                            for i in range(8):
                                v = s[j * 8 + i]
                                im.putpixel((x * 8 + i, y * 8 + j), tuple(cols[v]) if cols else (PAL.DMG_SHADE[v],) * 3)
                im.save(preview / f"smap_world_{name}_{p}.png")
    except Exception as e:  # previews are a courtesy
        print("preview skipped:", e)
    print(f"smap world: Color {cg.nt} tiles in {nslots} slots (min {k_min}, <= {nvar} per slot, {len(cg.fog_cell)} cloud edge cells), DMG {dm.nt} tiles "
          f"(worst 21x19 window {n21} of {POOL}, 22x20 {n22}; hint conflicts {bad_d}), palettes per window {p21} (22x20: {p22}), tile uses <= {uses}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "build", sys.argv[2] if len(sys.argv) > 2 else "out/preview")
