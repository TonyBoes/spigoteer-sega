"""Q10 near-twin merge (owner 11-08: "Mountain changes are ok with me. Snowy area changes are ok (except water) zoo area changes are ok. Stadium area changes are ok. Road and loge area
changes are ok." and "3) No" to palette merges).  Tiles 1 to D pixels apart are folded into the most-used tile of their group (a rare tile is redrawn into a common one, never the other way
round), ONLY where every cell that uses the tile lies in an approved area, and never for water or the animated cells.

APPROVED AREAS (cells; area_masks() reads them from the layout and the cell palettes in the snapshot's dump):
  snow     palette igloo (the snowy land, the top-right mountain range and the big mountain, the igloo, its spruces and drifts); the river and the falls are palette water / protected
  zoo      palettes zoo and zoogate
  stadium  palettes stadium and park
  lodge    palette lodge
  roads    the legs' road cells (layouts.road_cells) whose palette is a town1 one, outside the town's own cells (x 22..35, y 19..27 and the paved band y 30..33)
  desert mountains (owner: "all ranges, the big mountains, peaks"): the saloon-palette cells of the five desert peaks (x 2..23, y 29..34) and the big mountain (x 10..30, y 33..42)
                   (DESERT_MOUNTAINS = False leaves them out); the sand round them is merged only where the tile is used nowhere else
NEVER (the rule "a tile is merged only if every cell using it is approved" covers the other areas): desert ground, town, factory, cow pasture and milk bar, saloon, bistro, tea house, space lounge
and airbase.  Protected, never touched and never a centre: every tile that a water cell uses (the approved very subtle shimmer rewrites the dotted water tiles), the tiles of the animated cells
(falls and its foot, stadium flag, lodge and igloo smoke, fountain, bunting, radar and lamp, factory smoke, cow tails, logs) and of the cells next to them.
Nothing is drawn: a member block is replaced by the centre's block (under the same flip for Color), in every cell that uses it."""
import numpy as np

DESERT_MOUNTAINS = True
TOWN_BOX = (22, 19, 35, 27)                 # x0, y0, x1, y1 cells: the town picture and its apron
PAVED_ROWS = (30, 33)
# animated cells in or next to the approved areas, and the excluded areas' ones (the engine's table, stage 3: docs/dev/proposals/smap_anim/NOTES.md items 1 to 9)
ANIM = ([(47, 3), (46, 4), (47, 4), (46, 5), (47, 5), (46, 6), (47, 6), (46, 7), (47, 7), (46, 8), (47, 8)]       # falls, its foot, the splash cells
        + [(7, 1), (8, 1)]                                                                                    # stadium flag
        + [(58, 19), (59, 19), (58, 20), (59, 20)]                                                            # lodge smoke and the chimney cap
        + [(56, 5)]                                                                                           # igloo smoke
        + [(13, 38), (14, 38)])                                                                               # airbase lamp and radar


def area_masks(lay, palc, cw, ch):
    """(approved, protected) as (ch, cw) bool arrays; palc[y][x] = the cell's palette name"""
    import layouts
    pal = np.array(palc, dtype=object)
    ok = np.zeros((ch, cw), dtype=bool)
    for names in (("igloo",), ("zoo", "zoogate"), ("stadium", "park"), ("lodge",)):
        ok |= np.isin(pal, names)
    roads = np.zeros((ch, cw), dtype=bool)
    for (x, y) in layouts.road_cells(lay.LEGS):
        if 0 <= x < cw and 0 <= y < ch:
            roads[y, x] = True
    town1 = np.array([[str(n).startswith("town1") for n in r] for r in palc])
    tx0, ty0, tx1, ty1 = TOWN_BOX
    town = np.zeros((ch, cw), dtype=bool)
    town[ty0:ty1 + 1, tx0:tx1 + 1] = True
    town[PAVED_ROWS[0]:PAVED_ROWS[1] + 1, tx0:tx1 + 1] = True
    ok |= roads & town1 & ~town
    if DESERT_MOUNTAINS:
        box = np.zeros((ch, cw), dtype=bool)
        box[29:35, 2:24] = True
        box[33:43, 10:31] = True
        ok |= box & (pal == "saloon")
    prot = (pal == "water")
    for (x, y) in ANIM:
        prot[max(0, y - 1):y + 2, max(0, x - 1):x + 2] = True
    return ok, prot


def _flips(a):
    g = a.reshape(-1, 8, 8)
    return [g.reshape(-1, 64), g[:, :, ::-1].reshape(-1, 64), g[:, ::-1, :].reshape(-1, 64), g[:, ::-1, ::-1].reshape(-1, 64)]


def merge(px, ok, prot, use_flips, d=2):
    """px: (ch*8, cw*8) int array.  Returns (new px, stats dict, list of (centre cells, member cells, distance))"""
    ch, cw = ok.shape
    blk = px.reshape(ch, 8, cw, 8).transpose(0, 2, 1, 3).reshape(ch, cw, 64)
    seen = {}
    for y in range(ch):
        for x in range(cw):
            seen.setdefault(blk[y, x].tobytes(), []).append((x, y))
    blocks = list(seen)
    n = len(blocks)
    arr = np.array([np.frombuffer(b, dtype=np.uint8) for b in blocks])
    use = np.array([len(seen[b]) for b in blocks])
    allowed = np.array([all(ok[y, x] and not prot[y, x] for (x, y) in seen[b]) for b in blocks])      # a member: every cell approved, none protected
    centre_ok = np.array([not any(prot[y, x] for (x, y) in seen[b]) for b in blocks])                  # a centre: not water, not animated
    A = np.zeros((n, 256), dtype=np.float32)
    for k in range(4):
        A[np.arange(n)[:, None], np.arange(64)[None, :] * 4 + k] = (arr == k)
    D = np.full((n, n), 99, dtype=np.int32)
    T = np.zeros((n, n), dtype=np.int32)
    for fi, f in enumerate(_flips(arr) if use_flips else [arr]):
        B = np.zeros((n, 256), dtype=np.float32)
        for k in range(4):
            B[np.arange(n)[:, None], np.arange(64)[None, :] * 4 + k] = (f == k)
        dd = 64 - (A @ B.T).astype(np.int32)                         # dd[i, j]: block i against block j under flip fi
        better = dd < D
        D[better] = dd[better]
        T[better] = fi
    # near[c, m]: member m folds into centre c (D[m, c] pixels apart under the flip T[m, c])
    near = (D.T <= d) & (D.T > 0)
    np.fill_diagonal(near, False)
    near &= allowed[None, :] & centre_ok[:, None]
    near &= (use[None, :] < use[:, None]) | ((use[None, :] == use[:, None]) & (np.arange(n)[None, :] > np.arange(n)[:, None]))
    deg = near.sum(axis=1)
    order = np.lexsort((np.arange(n), -deg, -use))
    gone, groups = set(), []
    for c in order:
        c = int(c)
        if c in gone or deg[c] == 0:
            continue
        mem = [int(m) for m in np.nonzero(near[c])[0] if int(m) not in gone]
        if mem:
            gone.update(mem)
            gone.add(c)
            groups.append((c, mem))
    out = px.copy()
    cells = pixels = 0
    detail = []
    for c, mem in groups:
        for m in mem:
            # D[m, c] = pixels differing between member m and the centre under flip T[m, c]: the member takes the centre's flipped image
            new = _flips(arr[c:c + 1])[int(T[m, c])][0].reshape(8, 8)
            for (x, y) in seen[blocks[m]]:
                out[y * 8:y * 8 + 8, x * 8:x * 8 + 8] = new
                cells += 1
                pixels += int(D[m, c])
            detail.append((seen[blocks[c]][0], seen[blocks[m]], int(D[m, c])))
    return out, dict(groups=len(groups), merged=sum(len(m) for _, m in groups), cells=cells, pixels=pixels), detail
