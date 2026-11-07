"""The town venue of layout A5 with the fountain redrawn as a miniature of the story square's fountain (proposal; nothing here is imported to assets/).

v_town_base.py is tools/smap_world/v_town.py with the trough, tap and jet lines (163 to 179) cut out; everything else of the picture (tower, hall, tavern,
bunting, cobbles) is the town as it is.  This module pastes the typed fountain pieces (env SMAP_FOUNTAIN = 1 or 2), keeps layout A5's hand-typed town
touches that are not about the old fountain (flags, tower), and gives every 8 x 8 cell its palette the way layout A5 does (water cells town4, the rest
town1; a cell with air takes the '@g' variant, index 0 = grass).

Letters: 0 cream, 1 terracotta, 2 lilac, 3 ink, w water (index 1, palette town4), '.' transparent.
Cell rules the drawing obeys: a water cell has no terracotta and no air; a cell with air has no cream that is not air."""
import os

import v_town_base as B

W, H = B.W, B.H
OPT = os.environ.get("SMAP_FOUNTAIN", "2")
AIR_ROWS = 64
P = B.P

# ---- the touches of layout A5 that are not about the old fountain: flags (28,12) (44,12) (60,12); the tower's left and right edge ---------------------------------------
EDITS = {}


def put(ix, pts):
    for p in pts:
        EDITS[p] = ix


put("1", [(28, 12), (44, 12), (60, 12)])
put("3", [(0, y) for y in list(range(14, 30)) + list(range(31, 59)) + [59]])
put("2", [(1, 14), (1, 31)])
put("1", [(1, 15), (2, 15)] + [(1, y) for y in (56, 57, 58)] + [(2, y) for y in (56, 57, 58)])
put("0", [(1, y) for y in list(range(16, 30)) + list(range(32, 56))])
put("2", [(14, y) for y in range(14, 30)])
put("3", [(15, y) for y in range(14, 30)])

# ---- the typed fountain pieces -------------------------------------------------------------------------------------------------------------------------------------
# Cell rules shape it: water only in cells without air or terracotta (the basin, y 48 to 63, and the tavern wall strip x 56 to 63 where the jet falls), so the
# statue, bowl and column (terracotta, lilac, ink, on grass) stay in x 42 to 55 below y 31 and only the spout reaches over the tavern wall above y 32.
# Light from the top left.  STATUE: 16 wide (x 43 to 58): domed cap (option 2), T handle, neck, body with a lever knob on the left, a spout arm that turns down
# at its end (as the story's does), collar and two plinth steps; its last row sits on the bowl's rim.  The nozzle's mouth is the row in y 31, the jet starts
# under it in y 32.
STATUE2 = P("....3333........",
            "...311223.......",
            ".3333333333.....",
            ".3111111223.....",
            ".3111222223.....",
            ".3333333333.....",
            "....3123........",
            "....3123........",
            "..33333333333333",
            "..31111111111113",
            ".331112222222223",
            "3131112223333223",
            ".331112223......",
            "..31112223......",
            ".3333333333.....",
            ".3111122223.....",
            "311111122223....")
STATUE1 = STATUE2[2:]                 # without the cap (the tighter one)
STATUE_NOZZLE_ROW = 11                # the row of STATUE2 that is y 31

# BOWL: the rim is ink (it closes the plinth; 14 wide, x 42 to 55), then the lip, then the funnel to the column (6 wide, x 46 to 51)
BOWL_ROWS = [(42, "3" * 14), (42, "31111111122223"), (43, "311111122223"), (44, "3111122223"), (45, "31112223")]
COLUMN = (46, "311223")
BLOCK = "30002223"                    # the pedestal's foot standing in the water: stone (cream, lilac), x 45 to 52, y 49 to 51

# the jet: 2 px wide, left pixel per row, y 32 to 48 (it falls over the back rim into the pool); leaves the nozzle under its mouth (x 56, 57) and drifts right
JET_LEFT = [56, 57, 57, 58, 58, 58, 59, 59, 59, 59, 60, 60, 60, 60, 60, 61, 61]
JET_GLINT = {0, 3, 7, 11, 15}         # rows where the left pixel is a cream glint


def basin(c, x0, x1):
    """y 48 to 63: back rim, three rows of water, front lip (ink, two cream rows, ink), panels with a divider every 8 px from x0, a lilac shade row, base."""
    for x in range(x0, x1 + 1):
        r = (x - x0) % 8
        end = x in (x0, x1)
        col = {48: "3", 52: "3", 55: "3", 63: "3"}
        col[49] = "3" if end else "w"
        col[50] = "3" if end else ("0" if r in (2, 3) else "w")
        col[51] = "3" if end else "w"
        col[53] = "3" if end else "0"
        col[54] = "3" if end else "0"
        for y in range(56, 62):
            col[y] = "3" if (end or r == 0) else "0"
        col[62] = "3" if (end or r == 0) else "2"
        for y, ch in col.items():
            c.px[y][x] = ch
    for k, ch in enumerate(BLOCK):                    # the foot of the column, in the water
        for y in (49, 50, 51):
            c.px[y][45 + k] = ch
    for x in (59, 60, 61, 62):                       # the foam where the jet lands
        c.px[49][x] = "0"


def paste(c, x, y, rows):
    for j, r in enumerate(rows):
        for i, ch in enumerate(r):
            if ch != ".":
                c.px[y + j][x + i] = ch


def fountain(c):
    statue = STATUE2 if OPT == "2" else STATUE1
    y0 = 31 - STATUE_NOZZLE_ROW + (len(STATUE2) - len(statue))        # the nozzle's mouth row is y 31 in both
    paste(c, 43, y0, statue)
    y = y0 + len(statue)                     # the bowl's rim row
    for k, (x, s) in enumerate(BOWL_ROWS):
        paste(c, x, y + k, [s])
    y += len(BOWL_ROWS)
    while y < 48:
        paste(c, COLUMN[0], y, [COLUMN[1]])
        y += 1
    for k, lx in enumerate(JET_LEFT):
        for i in (lx, lx + 1):
            c.px[32 + k][i] = "0" if (i == lx and k in JET_GLINT) else "w"
    basin(c, 40, 71 if OPT == "2" else 63)


class _Pic:
    def __init__(self, rows, cp):
        self.rows, self.cp = rows, cp

    def out(self):
        return self.rows

    def cellpals(self):
        return self.cp


_picture = B.picture


def _picture_fx():
    c = _picture()
    for (x, y), v in EDITS.items():
        c.px[y][x] = v
    fountain(c)
    return c


B.picture = _picture_fx


def _air(rows):
    seen = set()
    st = [(x, 0) for x in range(W)] + [(x, AIR_ROWS - 1) for x in range(W)] + [(0, y) for y in range(AIR_ROWS)] + \
         [(W - 1, y) for y in range(AIR_ROWS) if not 41 <= y <= 46] + [(70, 12), (20, 20)]
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


def build(dmg=False):
    p = B.build(dmg)
    rows = p.rows
    air = _air(rows)
    air |= {(x, y) for y in range(16, 48) for x in range(40, 56) if rows[y][x] == "0"}      # the gap between hall and tavern is air even where the stack seals it in
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
                    pal = "town1@g"        # layout A5's default (SMAP_GOLD=lilac)
            if pal == "town4":
                assert not outs, ("a water cell with air", cx, cy)
            line.append(pal)
        cp.append(line)
    return _Pic(rows, cp)
