"""The town as a map venue (owner Q93, 11-06: option 1, the Town Hall and the Golden Spigot): 96 x 72 (12 x 9 cells), drawn like the map's other venues (front view, ink outline, one roof band,
ground around it, no frame, no backdrop). Typed by hand: runs for the flat rows, raw grids for the shapes.
Letters: 0 cream, 1 terracotta, 2 lilac, 3 ink, g gold, w water, '.' clear. g and w are index 2 and 1 read as gold (palette town5) and water (town4);
build() writes the plain indices and gives every 8 x 8 cell one palette from the letters in it (a cell that needs two is an error).
Left to right: the clock tower and town hall (terracotta, lilac roofs), the golden tap on its plinth in a trough, the tavern (lilac, awning).
Bunting runs from the tower to the chimney. The tap's spout is horizontal; its jet falls in an arc into the trough."""
from canvas import Canvas, piece
from art import R
from tiles import COBBLE, COBBLE_B

W, H = 96, 72
PAL = "town1"


def P(*rows):
    w = len(rows[0])
    for r in rows:
        assert len(r) == w, (w, len(r), r)
    return list(rows)


# ---- the clock tower ------------------------------------------------------------------------------------------------------------------------------------
SPIRE = piece(".:7 3:2 .:7", ".:7 3:2 .:7", ".:6 3:1 1:1 2:1 3:1 .:6", ".:6 3:1 1:1 2:1 3:1 .:6", ".:5 3:1 1:2 2:2 3:1 .:5", ".:5 3:1 1:2 2:2 3:1 .:5",
              ".:4 3:1 1:3 2:3 3:1 .:4", ".:4 3:1 1:3 2:3 3:1 .:4", ".:3 3:1 1:4 2:4 3:1 .:3", ".:3 3:1 1:4 2:4 3:1 .:3",
              ".:2 3:1 1:5 2:5 3:1 .:2", ".:2 3:1 1:5 2:5 3:1 .:2", ".:1 3:1 1:6 2:6 3:1 .:1", "3:16")
CLOCK = P("...3333...", ".33000033.", ".30000003.", "3000000003", "3000030003", "3000030003", "3000033303", ".30000003.", ".33000033.", "...3333...")
SLIT = P(".33.", "3003", "3003", "3003", "3003", "3003", "3003", "3003", "3333")
TDOOR = P("..3333..", ".322223.", "32222223", "32232223", "32232223", "32232223", "32232223", "32232223", "32232223", "32232223", "32232223", "32232223", "32232223")

# ---- the hall -------------------------------------------------------------------------------------------------------------------------------------------
OCULUS = P("..3333..", ".302203.", "30022003", "32222223", "32222223", "30022003", ".302203.", "..3333..")
WIN5 = P(".333.", "30003", "30003", "30003", "30003", "33333", "30003", "30003", "30003", "30003", "33333")
SILL7 = P("2222222")
HDOOR = P("..333..", ".32223.", "3222223", "3223223", "3223223", "3223223", "3220223", "3223223", "3223223", "3223223", "3223223", "3223223", "3223223")

# ---- the tap --------------------------------------------------------------------------------------------------------------------------------------------
# 14 wide, 24 tall; x 42 to 55, y 24 to 47. Light from the top left: cream edge, terracotta lit, gold shade, ink outline.
TAP = P(".3333333......",
        "30111ggg3.....",
        ".3333333......",
        "...313........",
        "...313........",
        "..33333.......",
        "..301g3.......",
        "..33333.......",
        ".3333333......",
        ".3011gg3......",
        ".3011gg3......",
        ".3011gg3333333",
        ".3011gg1111113",
        ".3011gggggggg3",
        ".3011gg3333333",
        ".3011gg3......",
        ".3011gg3......",
        ".3111g13......",
        ".3333333......",
        "333333333.....",
        "301111gg3.....",
        "311111gg3.....",
        "311111gg3.....",
        "311111gg3.....")
# the jet: 8 wide (x 56 to 63), from y 36 to y 52; two pixels thick, a cream glint on the lit edge; it leaves the nozzle level and bends down
JET = P("0ww.....",
        "www.....",
        ".www....",
        "..ww....",
        "..0ww...",
        "...ww...",
        "...ww...",
        "...0ww..",
        "....ww..",
        "....ww..",
        "....ww..",
        "....0ww.",
        ".....ww.",
        ".....ww.",
        ".....ww.",
        ".....ww.",
        ".....0w.")


def seg(c, y, x, spec):
    """type a run list into row y starting at column x (the other columns of the row are left as they are)"""
    for i, ch in enumerate(R(spec)):
        c.px[y][x + i] = ch


def bricks(c, x0, x1, y0, y1, mortar="2"):
    """brick courses typed as a template: a mortar row where y is 3 mod 4, upright joints 8 apart, shifted 4 on every other course;
    the pattern repeats every 8 px each way, so every cell of the wall is the same tile"""
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            if y % 4 == 3:
                c.px[y][x] = mortar
            elif x % 8 == (7 if (y // 4) % 2 == 0 else 3):
                c.px[y][x] = mortar


def picture():
    c = Canvas("town_a", PAL, W, H)
    # ---- the tower: spire, wall, clock, slit, door ------------------------------------------------------------------------------------------------
    c.paste(0, 0, SPIRE)
    seg(c, 14, 1, "3:1 2:12 3:1")
    for y in range(15, 30):
        seg(c, y, 1, "3:1 0:1 1:10 2:1 3:1")
    c.paste(3, 18, CLOCK)
    seg(c, 30, 0, "3:16")
    seg(c, 31, 1, "3:1 2:12 3:1")
    for y in range(32, 59):
        seg(c, y, 1, "3:1 0:1 1:10 2:1 3:1")
    bricks(c, 3, 12, 32, 58)
    c.paste(6, 36, SLIT)
    c.paste(4, 46, TDOOR)
    seg(c, 59, 1, "3:14")
    # ---- the hall: gable, cornice, wall, windows, door ----------------------------------------------------------------------------------------------
    for r in range(13):
        w, pad = 2 + 2 * r, 27 - r
        s = {0: "3:2", 1: "3:1 2:2 3:1", 2: "3:1 2:4 3:1"}.get(r, "3:1 2:2 1:%d 2:2 3:1" % (w - 6))
        seg(c, 18 + r, pad, s)
    c.paste(24, 23, OCULUS)
    seg(c, 31, 14, "3:28")
    seg(c, 32, 15, "2:25 3:1")
    for y in range(33, 59):
        seg(c, y, 15, "1:25 3:1")
    bricks(c, 15, 39, 33, 58)
    c.paste(16, 38, WIN5)
    c.paste(34, 38, WIN5)
    c.paste(15, 49, SILL7)
    c.paste(33, 49, SILL7)
    c.paste(24, 46, HDOOR)
    seg(c, 59, 15, "3:26")
    # ---- the tavern: roof, chimney, wall, windows, awning, shop front -----------------------------------------------------------------------------------
    OFF = [10, 10, 9, 8, 8, 7, 6, 6, 5, 4, 4, 3, 2, 2, 1, 0]
    PHASE = {3: 0, 7: 2, 11: 0, 15: 2}                            # roof rows (counted from the ridge) that carry a lilac course of dashes, and its phase
    for k, off in enumerate(OFF):
        y, w = 14 + k, 40 - 2 * off
        if k in (0, 15):
            body = "3:%d" % w
        elif k in PHASE:
            dash = "".join("1" if (x + PHASE[k]) % 4 == 3 else "2" for x in range(57 + off, 55 + off + w))
            body = "3:1 =%s 3:1" % dash
        else:
            body = "3:1 1:%d 3:1" % (w - 2)
        seg(c, y, 56 + off, body)
    seg(c, 8, 77, "3:8")
    for y in range(9, 19):
        seg(c, y, 77, "3:1 1:6 3:1")
    for y in (11, 15):
        seg(c, y, 79, "2:4")
    seg(c, 19, 77, "3:8")
    seg(c, 30, 56, "3:1 (2:1 3:1)*19 3:1")
    for y in range(31, 59):
        seg(c, y, 56, "3:1 2:38 3:1")
    for y in range(31, 59):
        for x in ((79, 87) if 48 <= y <= 55 else (71, 79, 87)):
            c.px[y][x] = "1"
    c.paste(65, 33, P("333333", "300003", "300003", "300003", "300003", "333333"))
    c.paste(81, 33, P("333333", "300003", "300003", "300003", "300003", "333333"))
    c.paste(64, 40, P("3" * 32, *["gggg0000" * 4] * 6, "3" * 32))
    c.paste(72, 49, P("333333333333", "300002200003", "300002200003", "300002200003", "300002200003", "300002200003", "322222222223", "333333333333"))
    c.paste(86, 49, P("33333333", "31111113", "31331133", "31331133", "31331133", "31031133", "31331133", "31331133", "31331133", "31331133"))
    seg(c, 59, 56, "3:40")
    # ---- the trough, the plinth and the golden tap -----------------------------------------------------------------------------------------------------
    seg(c, 49, 45, "3:23")
    seg(c, 50, 43, "3:1 2:25 3:1")
    for y in (51, 52, 53):
        seg(c, y, 42, "3:1 w:27 3:1")
    seg(c, 52, 64, "0:2")
    seg(c, 53, 59, "0:2")
    seg(c, 54, 42, "3:29")
    for y in range(55, 62):
        seg(c, y, 42, "3:1 0:4 2:1 0:7 2:1 0:7 2:1 0:5 3:1")
    seg(c, 62, 42, "3:1 2:27 3:1")
    seg(c, 63, 43, "3:27")
    seg(c, 48, 42, "3:11")
    for y in range(49, 54):
        seg(c, y, 42, "3:1 0:7 2:2 3:1")
    c.paste(43, 24, TAP)
    c.paste(56, 36, JET)
    # ---- bunting: a level line from the tower to the chimney, seven pennants 8 px apart (the same tiles all along) -------------------------------------
    seg(c, 10, 14, "3:63")
    FLAG = {"g": P("ggggg", ".ggg.", "..g.."), "1": P("33333", ".303.", "..3..")}
    for k, x in enumerate(range(18, 67, 8)):
        c.paste(x, 11, FLAG["g" if k % 2 == 0 else "1"])
    # ---- the forecourt: the town's two cobble tiles in front of the trough --------------------------------------------------------------------------
    for cx in range(12):
        t = COBBLE if (cx + 22 + 29) % 2 == 0 else COBBLE_B
        for j in range(8):
            for i in range(8):
                c.px[64 + j][cx * 8 + i] = t[j][i]
    return c


class _Pic:
    def __init__(self, rows, cp):
        self.rows, self.cp = rows, cp

    def out(self):
        return self.rows

    def cellpals(self):
        return self.cp


def build(dmg=False):
    """the picture as the world pastes it: rows of index digits and one palette per cell (town1 cream/terracotta/lilac/ink, town4 water, town5 gold)"""
    rows = ["".join(r) for r in picture().px]
    out = [r.replace("g", "2").replace("w", "1") for r in rows]
    # the cells with nothing in them that the open air reaches (flood from the picture's edge, cell by cell) are the land's: grass; a cell the picture
    # closes in (between the bunting and the tap) stays the town's cream
    blank = {(cx, cy) for cy in range(H // 8) for cx in range(W // 8) if all(rows[cy * 8 + j][cx * 8:cx * 8 + 8] == "0" * 8 for j in range(8))}
    air = set()
    todo = [c for c in blank if c[0] in (0, W // 8 - 1) or c[1] == 0]
    while todo:
        c = todo.pop()
        if c in air:
            continue
        air.add(c)
        todo += [n for n in ((c[0] + 1, c[1]), (c[0] - 1, c[1]), (c[0], c[1] + 1), (c[0], c[1] - 1)) if n in blank and n not in air]
    cp = []
    for cy in range(H // 8):
        line = []
        for cx in range(W // 8):
            s = "".join(rows[cy * 8 + j][cx * 8:cx * 8 + 8] for j in range(8))
            gold, water, lilac, terra = "g" in s, "w" in s, "2" in s, "1" in s
            assert not (gold and (lilac or water) or water and terra), ("a cell needs two town palettes", cx, cy)
            line.append("town4" if water else "town5" if gold else "grass" if (cx, cy) in air else "town1")
        cp.append(line)
    return _Pic(out, cp)
