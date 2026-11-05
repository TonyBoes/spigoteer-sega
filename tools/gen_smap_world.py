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
import world2 as W  # noqa: E402  (the concept world; builds both data sets, 1 s)
import pal as PAL  # noqa: E402

CW, CH = W.CW, W.CH
NCELLS = CW * CH
POOL = 176                       # BG ids 0-35 and 93-232 in one VRAM bank
MAX_SLOTS_C = 2 * POOL           # Color: both banks
ORD = {"town": 0}
for _i, _n in enumerate(W.ORDER):
    ORD[_n] = _i + 1
# the 18 BG palettes (NOTES round 5): the 15 ground / venue palettes and the 3 cloud palettes
PAL_NAMES = ["base", "bistro", "cow", "factory", "farm", "grass", "igloo", "lodge", "saloon", "stadium", "tea", "town1", "town4", "town5", "zoo",
             "fog:grass", "fog:saloon", "fog:fogbase"]
FOG_PAL0 = 15
STOP_ORDER = list(W.ORDER) + ["town"]            # stop index = chapter 0..9, 10 the town (src/smap.c)
WIN_C = (22, 20)                 # the loaded region: the 21 x 19 cells a view can show, plus one line ahead on each axis
WIN_V = (21, 19)
MAX_CELLS_IN_WIN = 239           # a DMG slot's use count is a byte (the engine keeps 0xF0.. free)
TILE_MAX = 1024                  # a cell word holds a 10-bit tile id and a 5-bit palette


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
    return W.with_fog(world, {"town"} | set(W.ORDER[:p])) if p < 10 else world


class Model:
    """One data set (Color or DMG): the tiles, the per-state grids, the cell words and the fog lists."""

    def __init__(self, cgb):
        self.cgb = cgb
        world = W.WORLD if cgb else W.WORLD_DMG
        self.world = world
        self.ids = {}                                # pixel block -> tile id
        self.sigs = []
        self.grids = {}                              # p -> (CH, CW) tile ids
        self.pals = {}                               # p -> (CH, CW) palette indices (Color)
        self.state_end = []
        for p in range(1, 11):
            v = state_world(world, p)
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
        self.nt = len(self.sigs)
        assert self.nt < TILE_MAX
        # revealed display of every cell = the late world (state 10)
        self.cell = [int(self.grids[10][y, x]) | (int(self.pals[10][y, x]) << 10 if cgb else 0) for y in range(CH) for x in range(CW)]
        self.build_fog()

    # ---- the fog ----------------------------------------------------------------------------------------------------------------------
    def build_fog(self):
        Z = zone_orders()
        self.zone = []
        for y in range(CH):
            for x in range(CW):
                nb = [Z[y + dy, x + dx] for dy in (-1, 0, 1) for dx in (-1, 0, 1) if (dx or dy) and 0 <= x + dx < CW and 0 <= y + dy < CH]
                self.zone.append(int(Z[y, x]) | (min(min(nb), 15) << 4))
        self.fog_cell, self.fog_word, self.fog_off = [], [], [0]
        self.inner = [0] * 11
        self.fogint = None
        ground = self.world
        for p in range(1, 11):
            v = state_world(self.world, p)
            if p == 10:
                self.fog_off.append(len(self.fog_cell))
                continue
            fog = {(x, y) for y in range(CH) for x in range(CW) if Z[y, x] > p}
            ft = W.fog_tiles(self.world, fog)
            inner_cls = set()
            for y in range(CH):
                for x in range(CW):
                    if (x, y) not in fog:
                        continue
                    z = self.zone[y * CW + x]
                    t = int(self.grids[p][y, x])
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
        for p in range(1, 11):
            for y in range(CH):
                for x in range(CW):
                    w = self.disp(y * CW + x, p)
                    assert (w & 1023) == int(self.grids[p][y, x]), (self.cgb, p, x, y)
                    if self.cgb:
                        assert (w >> 10) == int(self.pals[p][y, x]), (self.cgb, p, x, y)

    # ---- windows -----------------------------------------------------------------------------------------------------------------------
    def window_max(self, ww, wh):
        best, at = 0, None
        for p in range(1, 11):
            g = self.grids[p]
            for y0 in range(CH - wh + 1):
                for x0 in range(CW - ww + 1):
                    n = len(np.unique(g[y0:y0 + wh, x0:x0 + ww]))
                    if n > best:
                        best, at = n, (p, x0, y0)
        return best, at

    def palette_max(self, ww, wh):
        best, at = 0, None
        for p in range(1, 11):
            g = self.pals[p]
            for y0 in range(CH - wh + 1):
                for x0 in range(CW - ww + 1):
                    n = len(np.unique(g[y0:y0 + wh, x0:x0 + ww]))
                    if n > best:
                        best, at = n, (p, x0, y0)
        return best, at

    def max_uses(self, ww, wh):
        mx = 0
        for p in range(1, 11):
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
        for p in range(1, 11):
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
        return min(max(fx - 80, 0), CW * 8 - 160), min(max(fy - 84, 0), CH * 8 - 144)
    wins = set()

    def add(fx, fy):
        cx, cy = cam(fx, fy)
        wins.add((max((cx >> 3) - pad, 0), min(((cx + 159) >> 3) + pad, CW - 1), max((cy >> 3) - pad, 0), min(((cy + 143) >> 3) + pad, CH - 1)))
    for sx, sy in stops:
        add(sx, sy)
    for a, b, pts in legs:
        for k in range(len(pts) - 1):
            (x0, y0), (x1, y1) = pts[k], pts[k + 1]
            n = max(abs(x1 - x0), abs(y1 - y0), 1)
            for i in range(n + 1):
                add(x0 + (x1 - x0) * i // n, y0 + (y1 - y0) * i // n)
    return sorted(wins)


def path_hints(dm, wins, k):
    """DMG allocator hints: the colouring that matters is the one of the windows the camera can actually show.  Tiles conflict when some such window of
    some state holds both; the weight of a pair is the number of such windows; a min-conflict pass, then local search until no tile gains by moving."""
    n = dm.nt
    conf = np.zeros((n, n), dtype=bool)
    wt = np.zeros((n, n), dtype=np.float32)
    for p in range(1, 11):
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
    for li, (a, b, pts) in enumerate(legs):
        for (s, t, rev) in ((a, b, 0), (b, a, 1)):
            dx, dy = stops[t][0] - stops[s][0], stops[t][1] - stops[s][1]
            d = (3 if dx > 0 else 2) if abs(dx) >= abs(dy) else (1 if dy > 0 else 0)
            assert exits[s][d] == 255, f"two exits of stop {s} lie to the same side"
            exits[s][d] = t
            exit_leg[s][d] = li | (0x80 if rev else 0)
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
    L.append(carr("uint16_t", f"{tag}_fcell", m.fog_cell, 12, 4))
    L.append(carr("uint16_t", f"{tag}_fword", m.fog_word, 12, 4))
    L.append(carr("uint16_t", f"{tag}_foff", m.fog_off, 12, 4))
    L.append(carr("uint8_t", f"{tag}_inner", m.inner, 11))
    L.append(carr("uint16_t", f"{tag}_fint", m.fogint, 4, 4))
    if cgb:
        L.append(carr("uint16_t", f"{tag}_slotvar", m.slotvar, 12, 4))
        L.append(carr("uint16_t", f"{tag}_pal", m.pal_words, 4, 4))
    else:
        L.append(carr("uint8_t", f"{tag}_hint", m.hint, 16, 2))
    asm_open = asm_close = ""
    if not cgb:
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
    L.append(f"""
{'static ' if cgb else ''}uint16_t {tag}_fogfind(uint16_t c, uint8_t p) {{
    uint16_t base = {tag}_foff[p - 1];                          // (the lists of one state are < 256 long: asserted by the generator)
    uint8_t lo = 0, hi = (uint8_t)({tag}_foff[p] - base), mid;
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
    if p21 > 8:
        fail.append(f"Color: a 21 x 19 window needs {p21} palettes at {pat21}")
    p22, _ = cg.palette_max(*WIN_C)
    uses = dm.max_uses(*WIN_C)
    if uses > MAX_CELLS_IN_WIN:
        fail.append(f"DMG: a tile fills {uses} cells of a 22 x 20 window (a use count is a byte)")
    if any(cg.fog_off[i + 1] - cg.fog_off[i] > 255 for i in range(10)) or any(dm.fog_off[i + 1] - dm.fog_off[i] > 255 for i in range(10)):
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
    if nvar > 15:
        fail.append(f"Color: a slot is shared by {nvar} tiles (a variant is a nibble)")
    nslots = k_c
    cg.slotvar = [int(col_c[t]) | (var_idx[t] << 9) for t in range(cg.nt)]
    cg.pal_words = []
    for name in PAL_NAMES:
        cols = PAL.get(name)
        cg.pal_words += [rgb555(c) for c in cols]
    # the DMG hints: a min-conflict colouring of the DMG tiles in 176 slots (the allocator takes a tile's hint slot when it is free)
    stops, legs, exits, exit_leg = geometry()
    col_d, bad_d = path_hints(dm, path_windows(stops, legs), POOL)
    dm.hint = [int(c) for c in col_d]
    if fail:
        print("gen_smap_world: BUDGET FAILURES\n  " + "\n  ".join(fail), file=sys.stderr)
        sys.exit(1)
    # ---- geometry ------------------------------------------------------------------------------------------------------------------------
    assert reachable(exits) == set(range(11)), "a stop cannot be reached from the town along the legs"
    # ---- files -------------------------------------------------------------------------------------------------------------------------------
    ufo = (W.VENUES["space"][1][0] * 8 + 62, W.VENUES["space"][1][1] * 8 + 6)
    h = ["// generated by tools/gen_smap_world.py -- do not edit", "#ifndef SMAP_WORLD_H", "#define SMAP_WORLD_H", "#include <stdint.h>", "",
         f"#define SMAPW_CW 64", f"#define SMAPW_CH 48", f"#define SMAPW_C_TILES {cg.nt}", f"#define SMAPW_D_TILES {dm.nt}",
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
         "#ifdef SMAPW_GEOMETRY   // (src/smap.c alone)",
         f"static const uint16_t smapw_stop[11][2] = {{ " + ", ".join("{ %d, %d }" % s for s in stops) + " };",
         f"static const uint8_t smapw_stopc[11][2] = {{ " + ", ".join("{ %d, %d }" % (s[0] >> 3, s[1] >> 3) for s in stops) + " };   // (the stops' cells: the dots' quick cull)",
         "static const uint8_t smapw_exit[11][4] = {   // U, D, L, R: the stop that button walks to (255: none)"]
    for s in range(11):
        h.append("    { " + ", ".join(str(v) for v in exits[s]) + " },")
    h.append("};")
    h.append("static const uint8_t smapw_exit_leg[11][4] = {   // the leg of that exit, bit 7 set when it is walked backwards")
    for s in range(11):
        h.append("    { " + ", ".join(str(v) for v in exit_leg[s]) + " },")
    h.append("};")
    h.append(f"static const uint8_t smapw_leg_n[{len(legs)}] = {{ " + ", ".join(str(len(p)) for _, _, p in legs) + " };")
    # the pace of each stretch of a leg (the stretch that ends at waypoint s, s = 1..3: two bits at 2 * (s - 1) of the leg's byte: 2 = 2 px a frame, 1 = 1 px a frame, 0 = 1 px
    # every other frame): measured, per model, by tools/dev/smap_gear.py (the streaming's budget: the tile loads a VBlank can take and the logic's lines; a dense stretch cannot
    # keep up at 2) and kept in tools/smap_gear.json: per model, per leg, the levels of its stretches
    gear_file = ROOT / "tools" / "smap_gear.json"
    gear = json.loads(gear_file.read_text()) if gear_file.exists() else {}
    packed = {}
    for m_ in ("dmg", "cgb"):
        lv_ = gear.get(m_, [[1] * 3] * len(legs))
        assert len(lv_) == len(legs) and all(len(l_) == 3 and all(v_ in (0, 1, 2) for v_ in l_) for l_ in lv_), f"tools/smap_gear.json: {m_}: three levels (0, 1, 2) a leg"
        packed[m_] = [l_[0] | (l_[1] << 2) | (l_[2] << 4) for l_ in lv_]
    h.append(f"static const uint8_t smapw_gear[2][{len(legs)}] = {{ {{ " + ", ".join(str(g_) for g_ in packed["dmg"]) + " }, { " + ", ".join(str(g_) for g_ in packed["cgb"]) + " } };   // (the pace of each stretch)")
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
        "ufo": ufo, "ndmg": dm.nt, "ncgb": cg.nt, "slots_c": nslots, "slots_c_min": k_min, "vars_max": nvar, "pal_names": PAL_NAMES, "pal": pal_cols,
        "state_end_c": cg.state_end, "state_end_d": dm.state_end, "tiles_c": bytes(dc).hex(), "tiles_d": bytes(dd).hex(),
        "win_d_21x19": n21, "win_d_22x20": n22, "win_c_pal_21x19": p21, "win_c_pal_22x20": p22, "uses_max_22x20": uses, "hint_conflicts": int(bad_d),
        "slot_of_c": [int(c) for c in col_c], "var_of_c": [var_idx[t] for t in range(cg.nt)], "hint_d": dm.hint,
        "fog_c": [cg.fog_off, cg.fog_cell, cg.fog_word], "fog_d": [dm.fog_off, dm.fog_cell, dm.fog_word], "inner_c": cg.inner, "fogint_c": cg.fogint, "fogint_d": dm.fogint,
        "zone": cg.zone, "cell_c": cg.cell, "cell_d": dm.cell,
        "disp_c": [[cg.disp(c, p) for c in range(CW * CH)] for p in range(1, 11)], "disp_d": [[dm.disp(c, p) for c in range(CW * CH)] for p in range(1, 11)],   # the world shown in unlock state p (the tests expected pictures)
    }
    (build / "smap_world.json").write_text(json.dumps(info, default=int))
    # ---- previews ------------------------------------------------------------------------------------------------------------------------------
    try:
        from PIL import Image
        for name, m in (("cgb", cg), ("dmg", dm)):
            for p in (1, 10):
                im = Image.new("RGB", (CW * 8, CH * 8))
                for y in range(CH):
                    for x in range(CW):
                        w = m.disp(y * CW + x, p)
                        t = w & 1023
                        cols = PAL.get(PAL_NAMES[w >> 10]) if m.cgb else None
                        s = m.sigs[t]
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
