"""Merge candidates: group near-identical 8x8 blocks, keep one block of each group as the representative (its pixels are not touched), and let the others show
the representative's pixels.  A merge never invents a pixel: the changed pixels are the representative's own, already hand-placed ones.
Greedy: repeatedly take the cheapest cluster-into-cluster merge (pixels changed on the map = sum over the moved members of differing pixels x cells using them),
subject to a cap DMAX on pixels that any member differs from the representative.  Animated tiles (pinned ids) are never merged.
local=True: only merge two groups that appear together in some 21x19 view (a merge of two tiles that are never on one screen helps the whole-map count only)."""
import numpy as np

import lib

VETO = set()          # (id, id) pairs the review rejected: filled by packages.py from the hand review


def prepare():
    dm = lib.model()
    sg = lib.sig_array(dm)
    g = dm.grids[lib.G.NSTATE]
    use = np.bincount(g.ravel(), minlength=len(sg))
    pin = lib.pinned_ids(dm)
    return dm, sg, use, pin


def dist_matrix(sg, weighted=False):
    """shade steps between two blocks: sum over pixels of |shade difference| (a dark pixel on a light ground costs 3); weighted=False: pixels that differ"""
    n = len(sg)
    d = np.zeros((n, n), dtype=np.int16)
    s16 = sg.astype(np.int16)
    for i in range(n):
        d[i] = np.abs(s16 - s16[i]).sum(axis=1) if weighted else (sg != sg[i]).sum(axis=1)
    return d


def occupancy(dm, n):
    """(n, CH*CW) bool: the cells of the finished map (state 11) that show each id"""
    g = dm.grids[lib.G.NSTATE]
    m = np.zeros((n, lib.CH * lib.CW), dtype=bool)
    m[g.ravel(), np.arange(lib.CH * lib.CW)] = True
    return m


def reach():
    """(cells, cells) bool: two cells that fit in one 21x19 view"""
    ys, xs = np.divmod(np.arange(lib.CH * lib.CW), lib.CW)
    return (np.abs(xs[:, None] - xs[None, :]) <= 20) & (np.abs(ys[:, None] - ys[None, :]) <= 18)


def greedy(sg, use, pin, dmax, dist, occ=None, R=None, local=False, veto=(), state=None, protect=(), cap=1 << 30, limit=None):
    """state=(rep, groups) continues an earlier stage (a smaller dmax) so packages nest"""
    n = len(sg)
    live = [i for i in range(n) if use[i] > 0 and i not in pin]
    if state is None:
        rep = {i: i for i in range(n)}
        groups = {i: [i] for i in live}
    else:
        rep, groups = dict(state[0]), {k: list(v) for k, v in state[1].items()}
    gocc = {k: occ[v].any(axis=0) for k, v in groups.items()} if local else None
    log = []
    vet = set(veto)                                          # ordered: (m, a) = block m must not be shown as block a
    while True:
        best = None
        keys = list(groups)
        arr = np.array(keys)
        for b in keys:
            if protect and any(m in protect for m in groups[b]):
                continue
            mem = np.array(groups[b])
            dm_ = dist[np.ix_(mem, arr)]
            lim = dmax if limit is None else min(dmax, int(limit[mem].min()))
            ok = (dm_.max(axis=0) <= lim) & (arr != b)
            if local:
                reachb = R[gocc[b]].any(axis=0)                       # cells within reach of any cell of group b
                ok &= np.array([bool((gocc[a] & reachb).any()) for a in keys])
            if vet:
                ok &= np.array([not any((m, a) in vet for m in groups[b]) for a in keys])
            if not ok.any():
                continue
            cost = (dm_ * use[mem][:, None]).sum(axis=0)
            cost = np.where(ok & (cost <= cap), cost, 1 << 40)
            j = int(np.lexsort((-use[arr], cost))[0])
            c = int(cost[j])
            if c >= 1 << 40:
                continue
            if best is None or c < best[0]:
                best = (c, b, int(arr[j]))
        if best is None:
            break
        c, b, a = best
        for m in groups[b]:
            rep[m] = a
        e_members = list(groups[b])
        groups[a] += groups.pop(b)
        if local:
            gocc[a] |= gocc.pop(b)
        log.append(dict(step=len(log) + 1, cost=c, rep=a, moved=b, moved_members=e_members, members=list(groups[a])))
    return rep, log, groups


def apply_map(dm, rep):
    arr = np.arange(len(dm.sigs))
    for k, v in rep.items():
        arr[k] = v
    return {p: arr[dm.grids[p]] for p in dm.ustates}, arr


def orphans(img):
    """boolean mask of pixels unlike all 8 neighbours (inside the image); the lint's own idea of a stray pixel"""
    h, w = img.shape
    pad = np.pad(img.astype(np.int16), 1, constant_values=-1)
    same = np.zeros((h, w), dtype=bool)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dy or dx:
                same |= pad[1 + dy:1 + dy + h, 1 + dx:1 + dx + w] == img
    return ~same


def auto_veto(dm, sg, use, pin, dist, base, dmax=6, lines=True):
    """ordered pairs (m, a), d(m, a) <= dmax, where showing a in place of m puts a NEW stray pixel (an orphan) in the changed cell's 3x3 context
    on any cell that shows m.  Returns the set of vetoed pairs."""
    g = dm.grids[lib.G.NSTATE]
    live = [i for i in range(len(sg)) if use[i] > 0 and i not in pin]
    cells = {i: list(zip(*[a.tolist() for a in np.nonzero(g == i)[::-1]])) for i in live}   # id -> [(x, y)]
    veto = set()
    for m in live:
        near = [a for a in live if a != m and dist[m, a] <= dmax]
        for (x, y) in cells[m]:
            x0 = min(max(x - 1, 0), lib.CW - 3)
            y0 = min(max(y - 1, 0), lib.CH - 3)
            ctx = base[y0 * 8:y0 * 8 + 24, x0 * 8:x0 * 8 + 24]
            cx, cy = (x - x0) * 8, (y - y0) * 8
            o0 = orphans(ctx)[cy:cy + 8, cx:cx + 8]
            for a in near:
                if (m, a) in veto:
                    continue
                c2 = ctx.copy()
                c2[cy:cy + 8, cx:cx + 8] = sg[a].reshape(8, 8)
                o1 = orphans(c2)[cy:cy + 8, cx:cx + 8]
                # a new orphan: orphan after, not orphan before, at a pixel that changed or sits next to one
                if (o1 & ~o0).any():
                    veto.add((m, a))
                    continue
                # a broken line: a changed pixel that was dark ink (shade 3) with a dark 4-neighbour in the context
                old = ctx[cy:cy + 8, cx:cx + 8]
                ch = old != sg[a].reshape(8, 8)
                dark = ctx == 3
                pad = np.pad(dark, 1)
                nb = pad[cy:cy + 8, cx + 1:cx + 9] | pad[cy + 2:cy + 10, cx + 1:cx + 9] | pad[cy + 1:cy + 9, cx:cx + 8] | pad[cy + 1:cy + 9, cx + 2:cx + 10]
                if lines and (ch & (old == 3) & nb).any():
                    veto.add((m, a))
                    continue
                # a new dark speck or dash: a connected run of 1 or 2 dark pixels that the after-picture has and the before-picture has not
                if small_dark(c2) - small_dark(ctx):
                    veto.add((m, a))
    return veto


def small_dark(img):
    """the set of 4-connected groups of shade-3 pixels of size 1 or 2, as frozensets of (x, y)"""
    h, w = img.shape
    seen = set()
    out = set()
    for y in range(h):
        for x in range(w):
            if img[y, x] == 3 and (x, y) not in seen:
                comp, stack = [], [(x, y)]
                seen.add((x, y))
                while stack and len(comp) <= 2:
                    px, py = stack.pop()
                    comp.append((px, py))
                    for nx, ny in ((px + 1, py), (px - 1, py), (px, py + 1), (px, py - 1)):
                        if 0 <= nx < w and 0 <= ny < h and img[ny, nx] == 3 and (nx, ny) not in seen:
                            seen.add((nx, ny))
                            stack.append((nx, ny))
                if len(comp) <= 2 and not stack:
                    out.add(frozenset(comp))
    return out


VENUES = ("Stadium", "Bistro", "Igloo", "Saloon", "Town", "Lodge", "Space", "Factory", "Zoo", "Teahouse", "Rodeo")


def venue_ids(dm, n):
    """ids with at least one cell inside a venue (state 11)"""
    g = dm.grids[lib.G.NSTATE]
    pg = lib.piece_grid()
    out = np.zeros(n, dtype=bool)
    for y in range(lib.CH):
        for x in range(lib.CW):
            if pg[y][x] in VENUES:
                out[g[y, x]] = True
    return out
