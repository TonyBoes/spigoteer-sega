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
put("3", [(95, y) for y in range(41, 47)])        # round 4: the tavern awning's far right end gets the ink border the rest of the awning has (top y 40, bottom y 47, left x 56)
put("2", [(14, y) for y in range(14, 30)])
put("3", [(15, y) for y in range(14, 30)])

# ---- the typed fountain (round 3: one vertical axis, x 48, the middle of the gap between the hall (outline x 40) and the tavern (outline x 56)) -----------------------------
# Everything is symmetric about x 48 except the light (top left) and the statue's lever on the left against its spout on the right.
# Cell rules shape it: water only in cells with no air and no terracotta.  The gap's air cells (y 16 to 39) hold the statue (terracotta, lilac, ink); the cell row
# y 40 to 47 is closed by a low lilac garden wall across the gap (x 41 to 55, as the story's square has one behind its fountain), so its cells hold no air and may be
# water cells: there sit the bowl's lip, the column and the two spill streams.  The basin (y 48 to 63) spans x 32 to 64 (33 wide, axis 48) and covers the hall's
# lower right wall and the tavern's lower left corner; its cells x 32 to 63 hold no air and no terracotta.
# STATUE: 13 wide (x 42 to 54), axis idx 6: domed cap, T handle, neck, body (7 wide) with a lever knob on the left and a short DRY spout on the right (the same
# size as the knob, closed mouth: the story's statue spills nothing), collar, two plinth steps; its last row sits on the bowl's rim (y 39).
STATUE = ["....33333....",
          "...3112223...",
          ".33333333333.",
          ".31111122223.",
          ".31112222223.",
          ".33333333333.",
          "....31123....",
          "....31123....",
          "...3333333333",
          "...3111122223",
          ".331112222313",
          "3131112222313",
          ".331112222333",
          "..311122223..",
          "..333333333..",
          ".31111122223.",
          "3111111122223"]
STATUE_X, STATUE_Y = 42, 22          # rows y 22 to 38
RIM = (42, "3" * 13)                 # y 39 (an air cell row: ink only)
BOWL = [(42, "3000000000223"),       # y 40: the lip, a cream face (water cells from here down)
        (44, "300000223")]           # y 41: the funnel
COLUMN = (45, "3000223")             # y 42 to 51, 7 wide, x 45 to 51
FOOT = (44, "300000223")             # y 51: the column's foot in the water, 9 wide
WALL = (41, 55)                      # the garden wall behind, y 40 to 47
STREAMS = ((42, 43), (53, 54))       # the two spill streams under the lip's ends (mirror images about x 48), y 41 to 48
GLINT_ROWS = (44,)                   # a cream glint on the left pixel of each stream (the right one's glint is on its mirror pixel)
BX0, BX1 = 32, 64                    # basin ends (ink)

# BROKEN state (env SMAP_BROKEN=1; the story's square after the explosion, intro_a.txt): the statue is gone down to a jagged stub of the body on the collar and the
# plinth steps (y 32 to 38), no streams, the basin dry (its floor lilac, no water).  Same bowl, column, wall, foot and basin walls as the working state.
BROKEN = os.environ.get("SMAP_BROKEN") == "1"
STUB = ["..3.......3..",
        "..31.33.113..",
        "..311122223..",
        "..311122223.."]


def basin(c):
    """y 48 to 63: back rim, three rows of water, front lip (ink, two cream rows, ink), panels with a divider every 8 px from x 32 (so one under the axis), a lilac shade
    row, base.  The streams fall through a notch of the back rim (y 48) into the water; foam where they land."""
    for x in range(BX0, BX1 + 1):
        r = (x - BX0) % 8
        end = x in (BX0, BX1)
        col = {48: "3", 52: "3", 55: "3", 63: "3"}
        wet = "2" if BROKEN else "w"                  # dry: the floor is lilac
        col[49] = "3" if end else wet
        col[50] = "3" if end else wet
        col[51] = "3" if end else wet
        col[53] = "3" if end else "0"
        col[54] = "3" if end else "0"
        for y in range(56, 62):
            col[y] = "3" if (end or r == 0) else "0"
        col[62] = "3" if (end or r == 0) else "2"
        for y, ch in col.items():
            c.px[y][x] = ch
    if not BROKEN:
        for x in (36, 37, 59, 60):                    # glints on the water, mirror pairs about x 48
            c.px[50][x] = "0"
        for sx in (s for pair in STREAMS for s in pair):
            c.px[48][sx] = "w"                        # the notch in the rim
        for x in (41, 42, 43, 53, 54, 55):            # the foam where the streams land
            c.px[49][x] = "0"


def paste(c, x, y, rows):
    for j, r in enumerate(rows):
        for i, ch in enumerate(r):
            if ch != ".":
                c.px[y + j][x + i] = ch


def fountain(c):
    for y in range(40, 48):                           # the garden wall behind the column and the streams: ink coping, a cream cap row, lilac
        for x in range(WALL[0], WALL[1] + 1):
            c.px[y][x] = "3" if y == 40 else "2"
    statue, y0 = STATUE, STATUE_Y
    if BROKEN:
        statue = STUB + STATUE[-3:]
        y0 = 39 - len(statue)
    paste(c, STATUE_X, y0, statue)
    paste(c, RIM[0], 39, [RIM[1]])
    for k, (x, s) in enumerate(BOWL):
        paste(c, x, 40 + k, [s])
    for y in range(42, 52):
        paste(c, COLUMN[0], y, [COLUMN[1]])
    paste(c, FOOT[0], 51, [FOOT[1]])
    if not BROKEN:
        for pair in STREAMS:
            for k, x in enumerate(pair):
                for y in range(41, 48):
                    c.px[y][x] = "w"
        for y in GLINT_ROWS:
            c.px[y][STREAMS[0][0]] = "0"
            c.px[y][STREAMS[1][1]] = "0"
    basin(c)


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
    air |= {(x, y) for y in range(16, 40) for x in range(40, 56) if rows[y][x] == "0"}      # the gap between hall and tavern is air even where the stack seals it in
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
