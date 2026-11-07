"""Smooth bends (bend_smooth.py) laid on the map's 12 road bends: step 1 of the owner's "smooth, not just rounded" ask.  Not applied by default: mapctx.py uses this instead of roads_round.py
only when env SMAP_CURVE=16 or 24 is set.  apply() returns (laid, skipped): the bends it laid with the cells each one rewrote, and the bends it could not lay with the reason."""
import os

import bend_smooth as B
import roads_round as RR

LINE = os.environ.get("SMAP_CURVE_LINE") == "1"       # Color: the light line in cream (needs a [ground, peach, lilac, cream] palette per ground)
CREAM = {"roadg": ["b0d080", "f0b888", "a090b0", "f8f0b0"], "roadn": ["e8f8f8", "f0b888", "a090b0", "f8f0b0"]}


def apply(W, PAL, R):
    for n, cols in CREAM.items():
        PAL.RGB.setdefault(n, [PAL.h(c) for c in cols])
    for n, cols in RR.NEW_PALS.items():
        PAL.RGB.setdefault(n, [PAL.h(c) for c in cols])
    roads = W.WORLD.roads
    outer, _ = RR.classify(roads)
    n = R // 8
    laid, skipped, owner = [], [], {}
    for (cx, cy, k) in outer:
        sx = 1 if "W" in k else -1            # the patch extends east when the outer corner is on the west side
        sy = 1 if "N" in k else -1
        cells = [(cx + sx * i, cy + sy * j) for j in range(n) for i in range(n)]
        gcell = (cx + sx * (n - 1), cy + sy * (n - 1)) if R > 16 else None
        why = []
        for c in cells:
            if c == gcell:
                if c in roads:
                    why.append("ground cell %s is road" % (c,))
                elif W.WORLD.kind[c[1]][c[0]] not in ("ground",):
                    why.append("ground cell %s holds %s" % (c, W.WORLD.kind[c[1]][c[0]]))
                elif sum(1 for y in range(8) for x in range(8) if W.WORLD.px[c[1] * 8 + y][c[0] * 8 + x]) >= 10:
                    why.append("ground cell %s holds art (palette %s)" % (c, W.WORLD.pal[c[1]][c[0]]))
            elif c not in roads:
                why.append("cell %s is not road" % (c,))
            elif c in owner:
                why.append("cell %s is shared with the bend at %s" % (c, owner[c]))
        if why:
            skipped.append(((cx, cy, k), why))
            continue
        for c in cells:
            owner[c] = (cx, cy)
        rows = B.grid(R)
        if "E" in k:
            rows = B.flip_x(rows)
        if "S" in k:
            rows = B.flip_y(rows)
        # patch origin in world pixels: the patch's top left is the world cell of the smallest x and y
        ox = min(c[0] for c in cells) * 8
        oy = min(c[1] for c in cells) * 8
        pal_out = RR.OUTER_PAL.get((cx, cy), "town1@g")
        for (cxx, cyy) in cells:
            px0, py0 = (cxx * 8 - ox), (cyy * 8 - oy)
            block = [rows[py0 + y][px0:px0 + 8] for y in range(8)]
            has_g = any("g" in r for r in block)
            if has_g:
                pal, kidx = (RR.INNER.get((cxx, cyy), (pal_out, 2)) if (cxx, cyy) == gcell else (pal_out, 2))
                if (cxx, cyy) == gcell:
                    pal, kidx = RR.INNER.get(gcell, ("town1@g", 2))
                if LINE and pal == "town1@g":
                    pal = "roadg"
                if LINE and pal == "town1@n":
                    pal = "roadn"
            else:
                pal, kidx = "town1", 2
            for w, color in ((W.WORLD, True), (W.WORLD_DMG, False)):
                for y in range(8):
                    for x in range(8):
                        ch = block[y][x]
                        if color:
                            if pal == "town1":
                                v = {"g": 0, "k": 2, "b": 1, "l": 0, "o": 0}[ch]
                            elif pal in ("roadg", "roadn"):
                                v = {"g": 0, "k": 2, "b": 1, "l": 3, "o": 3}[ch]
                            else:
                                v = {"g": 0, "k": kidx, "b": 1, "l": 1, "o": 1}[ch]
                        else:
                            v = {"g": 0, "k": 2, "b": 1, "l": 0, "o": 0}[ch]
                        w.px[cyy * 8 + y][cxx * 8 + x] = v
            W.WORLD.pal[cyy][cxx] = pal
        laid.append(((cx, cy, k), cells))
    return laid, skipped
