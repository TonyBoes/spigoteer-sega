"""The town venue of layout A5: today's picture (tools/smap_world/v_town.py) with the town's edge cells on the grass.

On Color the town's cells that hold both building and sky or ground took the town palette, whose index 0 is the cream of the walls, so the air round the
buildings showed cream.  Here (1) the air is found (the index 0 pixels reachable from the picture's edge, plus the pocket of sky under the bunting's end;
the awning's last cream stripe at the right edge is a wall, not air; the cobbles below row 64 are paving) and (2) a cell that has air and no cream wall
takes the town palette with the grass as index 0 ('town1@g', 'town5@g'): no pixel changes, nothing visible is recoloured but the air.
(3) The cells that have air AND cream walls (all four indices used) needed a pixel touch: the typed lists below (placement and index changes decided by hand,
looking at the picture; nothing is generated).  The edits are the same for DMG and Color: the index is the DMG shade."""
import os

import v_town

GOLD_EDGE = {"lilac": "town1@g", "lodge": "lodge", "own": "town5@g"}   # the six gold cells with air: the town's lilac edge palette, the lodge's, or an own 19th palette

W, H = v_town.W, v_town.H
AIR_ROWS = 64                                     # the cobbles (rows 64 and below) are paving

# ---- the hand-typed touch (x, y) -> index ------------------------------------------------------------------------------------------------------------
EDITS = {}


def put(ix, pts):
    for p in pts:
        EDITS[p] = ix


# 1. the three flags with an ink pennant and a cream hole: the hole is the terracotta (3 pixels; DMG 248 -> 168)
put("1", [(28, 12), (44, 12), (60, 12)])
# 2. the golden spigot's head and shaft: the lit cream pixels beside the grass gap become terracotta (11 pixels, DMG 248 -> 168)
put("1", [(44, 25), (46, 30), (44, 44)] + [(45, y) for y in range(33, 41)])
# 3. the top row of the cream box right of the shaft becomes the dark shade under the lintel (5 pixels, DMG 248 -> 88)
put("2", [(x, 39) for x in range(51, 56)])
# 4. the clock tower, left side: the tower is one pixel wider; the air column x = 0 becomes the ink outline, the old outline column x = 1 takes the wall's lit
#    colour (the cream strip is two pixels wide; at the top and the foot, where the cell also holds air, the strip is terracotta)
put("3", [(0, y) for y in list(range(14, 30)) + list(range(31, 59)) + [59]])
put("2", [(1, 14), (1, 31)])
put("1", [(1, 15), (2, 15)] + [(1, y) for y in (56, 57, 58)] + [(2, y) for y in (56, 57, 58)])
put("0", [(1, y) for y in list(range(16, 30)) + list(range(32, 56))])
# 5. the clock tower, right side (rows 14 to 29, where the hall is not against it): one pixel wider, the lilac shade side widens, ink outline moves out
put("2", [(14, y) for y in range(14, 30)])
put("3", [(15, y) for y in range(14, 30)])
# 6. between the hall and the trough: the one pixel air gap is a lilac joint (rows 48 to 58), ink below the hall's base line (rows 59 to 63, the foot of the wall)
put("2", [(41, y) for y in range(48, 59)])
put("3", [(41, y) for y in range(59, 64)] + [(40, y) for y in range(60, 64)] + [(42, 63)])
# 7. the trough's right foot: the air notch under the tavern's base line, right of the trough, is the wall's ink (7 pixels)
put("3", [(70, 60), (71, 60), (70, 61), (71, 61), (71, 62), (70, 63), (71, 63)])


def _air(rows):
    seen = set()
    st = [(x, 0) for x in range(W)] + [(x, AIR_ROWS - 1) for x in range(W)] + [(0, y) for y in range(AIR_ROWS)] + \
         [(W - 1, y) for y in range(AIR_ROWS) if not 41 <= y <= 46] + [(70, 12), (20, 20)]    # (the two seeds: the sky under the bunting)
    st = [q for q in st if rows[q[1]][q[0]] == "0"]
    while st:
        x, y = st.pop()
        if (x, y) in seen:
            continue
        seen.add((x, y))
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            a, b = x + dx, y + dy
            if 0 <= a < W and 0 <= b < AIR_ROWS and rows[b][a] == "0" and (a, b) not in seen:
                st.append((a, b))
    return seen


class _Pic:
    def __init__(self, rows, cp):
        self.rows, self.cp = rows, cp

    def out(self):
        return self.rows

    def cellpals(self):
        return self.cp


def build(dmg=False):
    p = v_town.build(dmg)
    rows = [list(r) for r in p.rows]
    for (x, y), v in EDITS.items():
        rows[y][x] = v
    rows = ["".join(r) for r in rows]
    air = _air(rows)
    cp = []
    for cy in range(H // 8):
        line = []
        for cx in range(W // 8):
            pal = p.cp[cy][cx]
            outs = [(x, y) for y in range(cy * 8, cy * 8 + 8) for x in range(cx * 8, cx * 8 + 8) if (x, y) in air]
            inner0 = [(x, y) for y in range(cy * 8, cy * 8 + 8) for x in range(cx * 8, cx * 8 + 8) if rows[y][x] == "0" and (x, y) not in air]
            if pal in ("town1", "town5") and outs:
                assert not inner0, ("a cell with air and cream walls", cx, cy, len(outs), len(inner0))
                pal += "@g"
                if pal == "town5@g":
                    pal = GOLD_EDGE.get(os.environ.get("SMAP_GOLD", "lilac"), "town5@g")
            line.append(pal)
        cp.append(line)
    return _Pic(rows, cp)
