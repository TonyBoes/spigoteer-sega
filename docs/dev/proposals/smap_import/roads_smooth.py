"""Smooth bends (bend_smooth.py) laid on the map's 12 road bends: the owner's "smooth, not just rounded" ask (Q113) and "a higher radius?" (Q115).  Not applied by default: mapctx.py uses this
instead of roads_round.py only when env SMAP_CURVE is set: "16", "24", "32", "40", "48", "56", "80" (every bend at that radius where it fits, the others keep their r8 corner),
or "fit" (each bend takes the largest radius in FIT_RADII that fits it: the largest-fit map).  SMAP_CURVE_TRIM=1 also frees the three r24 blockers by trimming the art the road covers.
apply() returns (laid, skipped, trimmed): the bends it laid (with R and the cells it rewrote), the bends it could not lay with the reasons, and the art pixels it trimmed."""
import os

import bend_smooth as B
import roads_round as RR

LINE = os.environ.get("SMAP_CURVE_LINE") == "1"       # Color: the light line in cream (needs a [ground, peach, lilac, cream] palette per ground)
TRIM = os.environ.get("SMAP_CURVE_TRIM") == "1"
CREAM = {"roadg": ["b0d080", "f0b888", "a090b0", "f8f0b0"], "roadn": ["e8f8f8", "f0b888", "a090b0", "f8f0b0"]}
FIT_RADII = [120, 96, 80, 56, 48, 40, 32, 24, 16]
ART_OK = {(52, 44), (61, 27), (61, 47)}               # ground cells that hold picture art (factory yard, lodge wood pile, cow pen fence): with TRIM the road is written over them
# interior ground cells (the block's corner inside the bend): Color palette, kerb index.  RR.INNER first (the compromises of the r8 and r24 corners), then by the cell's own palette.
GROUND_PAL = {"grass": ("town1@g", 2), "igloo": ("town1@n", 2), "zoo": ("town1@z", 2), "saloon": ("town1", 2)}                       # desert sand: town1 (its index 0 is cream, a close pale sand) so the road keeps its peach and lilac


def nz(W, c):
    return sum(1 for y in range(8) for x in range(8) if W.WORLD.px[c[1] * 8 + y][c[0] * 8 + x])


def patch_rows(R, k):
    rows = B.grid(R)
    if "E" in k:
        rows = B.flip_x(rows)
    if "S" in k:
        rows = B.flip_y(rows)
    return rows


def straight(block):
    """a cell of straight road: every row is one letter (arm along x) or every column is one letter (arm along y), no speck"""
    if any("g" in r or "o" in r or "m" in r for r in block):
        return False
    return all(len(set(r)) == 1 for r in block) or all(r == block[0] for r in block)


def check(W, roads, owner, bend, R, trim):
    cx, cy, k = bend
    n = R // 8
    sx = 1 if "W" in k else -1
    sy = 1 if "N" in k else -1
    rows = patch_rows(R, k)
    ox, oy = (min(cx, cx + sx * (n - 1))) * 8, (min(cy, cy + sy * (n - 1))) * 8
    why = []
    for j in range(n):
        for i in range(n):
            c = (cx + sx * i, cy + sy * j)
            if not (0 <= c[0] < W.CW and 0 <= c[1] < W.CH):
                why.append("beyond the map edge at %s" % (c,))
                continue
            if i == 0 and j == 0 and (cx, cy) == (37, 46) and R > 24:
                why.append("palette: the windows round (35, 44) already hold 8 palettes, the town1@g that a patch beyond r24 needs there would be the 9th")
            if i < 2 or j < 2:
                if c not in roads:
                    why.append("arm: %s is not road (the straight is too short to the next bend or junction)" % (c,))
                elif c in owner and owner[c] != (cx, cy):
                    why.append("arm: %s is shared with the bend at %s" % (c, owner[c]))
            else:
                block = [rows[(c[1] * 8 - oy) + y][(c[0] * 8 - ox):(c[0] * 8 - ox) + 8] for y in range(8)]
                if set("".join(block)) == {"g"}:
                    continue
                if c in roads:
                    why.append("%s is road" % (c,))
                elif W.WORLD.kind[c[1]][c[0]] != "ground" and not (trim and c in ART_OK):
                    why.append("%s holds a venue or a prop (%s)" % (c, W.WORLD.kind[c[1]][c[0]]))
                elif nz(W, c) >= 10 and not (trim and c in ART_OK):
                    why.append("%s holds art (%s, %d px)" % (c, W.WORLD.pal[c[1]][c[0]], nz(W, c)))
    return why


def apply(W, PAL, R, radii=None, trim=None):
    trim = TRIM if trim is None else trim
    for n, cols in CREAM.items():
        PAL.RGB.setdefault(n, [PAL.h(c) for c in cols])
    for n, cols in RR.NEW_PALS.items():
        PAL.RGB.setdefault(n, [PAL.h(c) for c in cols])
    roads = W.WORLD.roads
    outer, inner = RR.classify(roads)
    laid, skipped, owner, trimmed, fallback = [], [], {}, [], []
    plan = []
    for (cx, cy, k) in outer:
        if radii is not None:
            cands = [r for r in radii.get((cx, cy), [R]) if r in B.OUT]
        elif R == "fit":
            cands = [r for r in FIT_RADII]
        else:
            cands = [R]
        pick, why = None, []
        for RR_ in cands:
            why = check(W, roads, owner, (cx, cy, k), RR_, trim)
            if not why:
                pick = RR_
                break
        if pick is None:
            skipped.append(((cx, cy, k), why))
            continue
        for j in range(pick // 8):
            for i in range(pick // 8):
                owner.setdefault((cx + (1 if "W" in k else -1) * i, cy + (1 if "N" in k else -1) * j), (cx, cy))
        plan.append(((cx, cy, k), pick))
    # the bends it cannot lay keep the r8 corner (roads_round), the others are left to the smooth patch
    RR.apply(W, PAL, skip_outer={b[:2] for b, _ in plan},
             skip_junction={(b[0] + (1 if "W" in b[2] else -1), b[1] + (1 if "N" in b[2] else -1)) for b, _ in plan})
    for ((cx, cy, k), pick) in plan:
        n = pick // 8
        sx = 1 if "W" in k else -1
        sy = 1 if "N" in k else -1
        cells = [(cx + sx * i, cy + sy * j) for j in range(n) for i in range(n)]
        for c in cells:
            owner[c] = (cx, cy)
        rows = patch_rows(pick, k)
        ox, oy = min(c[0] for c in cells) * 8, min(c[1] for c in cells) * 8
        pal_out = RR.OUTER_PAL.get((cx, cy), "town1@g")
        touched = []
        for j in range(n):
            for i in range(n):
                c = (cx + sx * i, cy + sy * j)
                px0, py0 = c[0] * 8 - ox, c[1] * 8 - oy
                block = [rows[py0 + y][px0:px0 + 8] for y in range(8)]
                interior = i >= 2 and j >= 2
                if interior and set("".join(block)) <= {"g"}:
                    continue
                if not interior and straight(block):
                    continue                                   # the plain straight road tile stays (its own specks)
                has_g = any(("g" in r or "m" in r) for r in block)
                if has_g:
                    if interior:
                        if pick <= 24:
                            pal, kidx = RR.INNER.get(c, (pal_out, 2)) if c == (cx + sx * (n - 1), cy + sy * (n - 1)) else (pal_out, 2)
                        else:
                            pal, kidx = RR.INNER.get(c) or GROUND_PAL.get(W.WORLD.pal[c[1]][c[0]], ("town1@g", 2))
                    else:
                        pal, kidx = pal_out, 2
                    if LINE and pal == "town1@g":
                        pal = "roadg"
                    if LINE and pal == "town1@n":
                        pal = "roadn"
                else:
                    pal, kidx = "town1", 2
                art = trim and c in ART_OK
                for w, color in ((W.WORLD, True), (W.WORLD_DMG, False)):
                    for y in range(8):
                        for x in range(8):
                            ch = block[y][x]
                            if art and ch == "g":
                                continue                       # trim only: the art keeps every pixel the road does not cover
                            if color:
                                if pal == "town1":
                                    v = {"g": 0, "k": 2, "b": 1, "l": 0, "o": 0, "m": 1}[ch]
                                elif pal in ("roadg", "roadn"):
                                    v = {"g": 0, "k": 2, "b": 1, "l": 3, "o": 3, "m": 1}[ch]
                                else:
                                    v = {"g": 0, "k": kidx, "b": 1, "l": 1, "o": 1, "m": 1}[ch]
                            else:
                                v = {"g": 0, "k": 2, "b": 1, "l": 0, "o": 0, "m": 1}[ch]
                            if art and color and w.px[c[1] * 8 + y][c[0] * 8 + x] and v != w.px[c[1] * 8 + y][c[0] * 8 + x]:
                                trimmed.append((c, x, y))
                            w.px[c[1] * 8 + y][c[0] * 8 + x] = v
                W.WORLD.pal[c[1]][c[0]] = pal
                touched.append(c)
        laid.append(((cx, cy, k), pick, touched))
    return laid, skipped, trimmed
