"""The DMG's route plan (owner 11-11, Q17): the tile slots are planned at build time, along the roads, instead of chosen while Sal walks.

The map is not free roam.  Sal walks the legs and stands at the stops, so the cells the engine can hold at any moment (the region: the camera's view and the lines it leads by)
lie inside a known set of windows (`walk_sequences`: every pixel of every leg both ways, every stop, the glides between a stop's resting view and Sal's follow spot, each padded by
one line on every side).  A tile's slot is a property of its CELLS, not of the tile: the cells that share a window and a tile share one slot (one live range, a `node`), and two
nodes that share a window never share a slot (a graph colouring in 176 colours).  The engine then needs no search, no use counts and no drop work: a cell's slot is read from the
table, the tile is loaded when the slot holds another one, and a line leaving the region costs nothing (nothing in it can be wanted by a line that stays: the check below).

`check_plan` is the build's proof: it replays every walk, line by line (the lines that leave drop, the lines that enter load their tiles into their slots, in any order) and
asserts that after every step each cell of the window shows its own tile; it also checks the windows themselves (no slot holds two tiles in one window)."""
import numpy as np


LEAD_MAX = 6                                         # lines a stretch may load ahead of the view (the 32 x 32 map holds the view's 21 columns and 19 rows, and these)
WALK_AHEAD = 24                                      # px before a corner at which the region starts loading for the next stretch (src/smap_priv.h)


def _sg(v):
    return (v > 0) - (v < 0)


def _cam(fx, fy, cw, ch, sal_y):
    return min(max(fx - 80, 0), cw * 8 - 160), min(max(fy - sal_y, 0), ch * 8 - 144)


def seg_windows(pts, j, lead, nxt, cw, ch, sal_y, pad=1, ahead=WALK_AHEAD):
    """The windows of the stretch pts[j] -> pts[j+1], every pixel: the view padded by `pad` on every side, `lead` lines ahead in the direction of travel, and in the last `ahead` px
    `nxt` (the next stretch's lead, in its direction: the engine's walk_dirs) lines ahead along the next stretch's axis.  Returns (the windows with the zone's, the windows without)."""
    (x0, y0), (x1, y1) = pts[j], pts[j + 1]
    n = max(abs(x1 - x0), abs(y1 - y0), 1)
    ds = [(_sg(x1 - x0), _sg(y1 - y0), lead)]
    nd = None
    if j + 2 < len(pts):
        nd = (_sg(pts[j + 2][0] - x1), _sg(pts[j + 2][1] - y1), nxt)
    full, plain = [], []
    for i in range(n + 1):
        cx, cy = _cam(x0 + (x1 - x0) * i // n, y0 + (y1 - y0) * i // n, cw, ch, sal_y)
        for out, dd in ((plain, ds), (full, ds + ([nd] if nd and n - i <= ahead else []))):
            c0, c1, r0, r1 = (cx >> 3) - pad, ((cx + 159) >> 3) + pad, (cy >> 3) - pad, ((cy + 143) >> 3) + pad
            for dx, dy, N in dd:
                e = max(N - pad, 0)
                c0 -= e * (dx < 0)
                c1 += e * (dx > 0)
                r0 -= e * (dy < 0)
                r1 += e * (dy > 0)
            out.append((max(c0, 0), min(c1, cw - 1), max(r0, 0), min(r1, ch - 1)))
    return full, plain


def choose_leads(tiles, legs, cw, ch, sal_y, budget, lead_max=LEAD_MAX, pad=1):
    """How many lines each stretch loads ahead (owner 11-11: the stutter): as many as the tile slots allow.  A stretch's windows (the view, a line either side, `lead` lines ahead, and in
    the corner zone the next stretch's lead) may hold at most `budget` distinct tiles in any unlock state; the leads fall until every stretch fits.  -> {(leg, rev, stretch): lines}"""
    def count(w):
        return max(len(np.unique(tiles[s][w[2]:w[3] + 1, w[0]:w[1] + 1])) for s in tiles)
    leads = {}
    segs = []
    for li, (a, b, pts0) in enumerate(legs):
        for rev, pts in ((0, pts0), (1, pts0[::-1])):
            for j in range(len(pts) - 1):
                segs.append((li, rev, j, pts))
                leads[(li, rev, j)] = lead_max

    def worst(key, zone):
        li, rev, j, pts = key
        full, plain = seg_windows(pts, j, leads[(li, rev, j)], leads.get((li, rev, j + 1), 1), cw, ch, sal_y, pad)
        return max(count(w) for w in (full if zone else plain))
    for _ in range(100):
        again = False
        for key in segs:
            li, rev, j, pts = key
            while leads[(li, rev, j)] > 1 and worst(key, False) > budget:
                leads[(li, rev, j)] -= 1
                again = True
            while worst(key, True) > budget:
                nk = (li, rev, j + 1)
                if nk in leads and leads[nk] > 1:
                    leads[nk] -= 1
                elif leads[(li, rev, j)] > 1:
                    leads[(li, rev, j)] -= 1
                else:
                    break
                again = True
        if not again:
            break
    return leads


def walk_sequences(stops, legs, stop_order, stop_view, cw, ch, sal_y, pad=1, leads=None):
    """Ordered lists of windows (c0, c1, r0, r1): one list per leg and direction (the camera's view at every pixel of the road, padded, and the stretch's lead lines ahead: `leads`
    {(leg, rev, stretch): lines}, 1 where missing), per stop's glide (view <-> follow spot), and one window per stop."""
    leads = leads or {}

    def cam(fx, fy):
        return _cam(fx, fy, cw, ch, sal_y)

    def win(fx, fy):
        cx, cy = cam(fx, fy)
        return (max((cx >> 3) - pad, 0), min(((cx + 159) >> 3) + pad, cw - 1), max((cy >> 3) - pad, 0), min(((cy + 143) >> 3) + pad, ch - 1))
    seqs = [[win(sx, sy)] for sx, sy in stops]
    for n, (sx, sy) in zip(stop_order, stops):
        vx, vy, _ = stop_view.get(n, (None, None, 1))
        if vx is not None or vy is not None:
            seqs.append([win(sx if vx is None else vx + 80 + (sx - 80 - vx) * i // 32, sy if vy is None else vy + sal_y + (sy - sal_y - vy) * i // 32) for i in range(33)])
    for li, (a, b, pts0) in enumerate(legs):
        for rev, pts in ((0, pts0), (1, pts0[::-1])):
            seq = []
            for j in range(len(pts) - 1):
                full, _ = seg_windows(pts, j, leads.get((li, rev, j), 1), leads.get((li, rev, j + 1), 1), cw, ch, sal_y, pad)
                seq += full
            seqs.append(seq)
    return seqs


def plan_slots(tiles, seqs, cw, ch, pool, forced, colour, tabucol, log=print):
    """tiles: {state: array (ch, cw) of the tile id shown}.  The states are 11 (the cell table) and 1 (every state before it; the cells that differ have a node of their own).
    forced: tile ids whose cells all share one node (an animated tile is rewritten in one slot).  Returns (slot per cell for state 11, {cell: slot} for the cells that differ in state 1)."""
    n = cw * ch
    t11, t1 = tiles[11].reshape(-1), tiles[1].reshape(-1)
    diff = t11 != t1
    par = list(range(2 * n))

    def find(a):
        while par[a] != a:
            par[a] = par[par[a]]
            a = par[a]
        return a

    def union(a, b):
        a, b = find(a), find(b)
        if a != b:
            par[b] = a

    def key(c, s):                                   # the node a cell belongs to in state s: a cell that differs has its own node in state 1
        return c + n if (s == 1 and diff[c]) else c
    wins = sorted({w for sq in seqs for w in sq})
    for s, t in ((11, t11), (1, t1)):
        for (c0, c1, r0, r1) in wins:
            first = {}
            for y in range(r0, r1 + 1):
                for x in range(c0, c1 + 1):
                    c = y * cw + x
                    tt = int(t[c])
                    if tt in first:
                        union(first[tt], key(c, s))
                    else:
                        first[tt] = key(c, s)
        for tt in forced:                            # (an animated tile: all its cells, wherever they are, one node)
            cs = np.nonzero(t == tt)[0]
            for c in cs[1:]:
                union(key(int(cs[0]), s), key(int(c), s))
    # the nodes of cells some window holds
    used = {}
    for s, t in ((11, t11), (1, t1)):
        for (c0, c1, r0, r1) in wins:
            for y in range(r0, r1 + 1):
                for x in range(c0, c1 + 1):
                    used.setdefault(find(key(y * cw + x, s)), len(used))
    nn = len(used)
    conf = np.zeros((nn, nn), dtype=bool)
    mx = 0
    for s in (11, 1):
        ids = np.array([[used.get(find(key(y * cw + x, s)), -1) for x in range(cw)] for y in range(ch)])
        for (c0, c1, r0, r1) in wins:
            u = np.unique(ids[r0:r1 + 1, c0:c1 + 1])
            mx = max(mx, len(u))
            conf[np.ix_(u, u)] = True
    np.fill_diagonal(conf, False)
    col, k = colour(conf, 4 * pool, False)
    log(f"smap world route plan: {nn} slot nodes, the fullest window {mx} of {pool}, DSATUR {k} colours")
    if k > pool:
        col, bad = tabucol(conf, pool, col, iters=300000)
        log(f"smap world route plan: tabu search, {bad} conflicts left")
        if bad:
            raise SystemExit(f"gen_smap_world: the DMG's route plan cannot be coloured in {pool} slots ({bad} conflicts; fullest window {mx})")
    slot11 = [0] * n
    slot1 = {}
    for c in range(n):
        r = find(key(c, 11))
        if r in used:
            slot11[c] = int(col[used[r]])
    for c in range(n):
        if diff[c]:
            r = find(key(c, 1))
            if r in used:
                slot1[c] = int(col[used[r]])
    return slot11, slot1


def check_plan(tiles, slot11, slot1, seqs, cw, ch, pool):
    """The proof.  Per state: (1) in every window each slot holds one tile; (2) replaying every walk, the window after each step shows every one of its cells' tile in the cell's
    slot (the slot table is what the engine's loads leave: a cell whose slot holds another tile loads its own, a line that leaves frees nothing and costs nothing).  Raises on a failure."""
    n = cw * ch
    for s in (11, 1):
        t = tiles[s].reshape(-1)
        sl = [slot1.get(c, slot11[c]) if s == 1 else slot11[c] for c in range(n)]
        assert all(0 <= v < pool for v in sl), "a slot is out of the pool"
        for sq in seqs:
            for (c0, c1, r0, r1) in set(sq):
                seen = {}
                for y in range(r0, r1 + 1):
                    for x in range(c0, c1 + 1):
                        c = y * cw + x
                        assert seen.setdefault(sl[c], int(t[c])) == int(t[c]), ("a slot holds two tiles in one window", s, (c0, c1, r0, r1), c, sl[c])
        steps = 0
        for sq in seqs:
            res = {}                                  # slot -> tile resident (the engine's table, empty at the start of every walk: a walk may start anywhere)
            prev = None
            for w in sq:
                c0, c1, r0, r1 = w
                for y in range(r0, r1 + 1):
                    for x in range(c0, c1 + 1):
                        if prev is not None and prev[0] <= x <= prev[1] and prev[2] <= y <= prev[3]:
                            continue                  # (a cell that stays)
                        c = y * cw + x
                        res[sl[c]] = int(t[c])        # (a cell that enters: its tile loads when the slot holds another)
                for y in range(r0, r1 + 1):
                    for x in range(c0, c1 + 1):
                        c = y * cw + x
                        assert res.get(sl[c]) == int(t[c]), ("a tile is not resident when shown", s, w, (x, y), sl[c])
                prev = w
                steps += 1
    return steps


def tabucol(conf, k, init, iters=300000, seed=1):
    """TabuCol (Hertz and de Werra): a k-colouring of the graph `conf` (bool matrix) started from `init` (colours >= k are redrawn).  Returns (colour, conflicts left)."""
    rng = np.random.default_rng(seed)
    n = conf.shape[0]
    adj = [np.nonzero(conf[v])[0] for v in range(n)]
    col = np.array(init, dtype=np.int64)
    over = col >= k
    col[over] = rng.integers(0, k, int(over.sum()))
    gamma = np.zeros((n, k), dtype=np.int32)
    for v in range(n):
        np.add.at(gamma[v], col[adj[v]], 1)
    tabu = np.zeros((n, k), dtype=np.int64)
    f = int(sum(gamma[v, col[v]] for v in range(n)) // 2)
    best, bestcol = f, col.copy()
    for it in range(iters):
        if f == 0:
            return col, 0
        own = gamma[np.arange(n), col]
        cv = np.nonzero(own > 0)[0]
        sub = gamma[cv] - own[cv][:, None]
        sub[np.arange(len(cv)), col[cv]] = 10 ** 6
        cand = np.where((tabu[cv] > it) & ~(f + sub < best), 10 ** 6, sub)
        m = cand.min()
        idx = np.argwhere(cand == m)
        i, c = idx[rng.integers(len(idx))]
        v = cv[i]
        old = col[v]
        col[v] = c
        f += int(m)
        tabu[v, old] = it + int(0.6 * len(cv)) + rng.integers(0, 10)
        gamma[adj[v], old] -= 1
        gamma[adj[v], c] += 1
        if f < best:
            best, bestcol = f, col.copy()
    return bestcol, best
