"""New land pieces of layout A4 (water, bridges, floating logs, the log pile) and the placeholder boxes.  Every tile is eight strings of eight palette
indices, typed by hand, DMG value first.  PALETTE 'water' (pal.py): 0 the grass on the bank, 1 sand (the rim of the bank, the wood of a log),
2 water, 3 deep (the outline of a log); the ripples are glints in 1.   DMG: grass 248, sand 168, water 88, deep 24.

Which tile goes on which cell of the typed water mask is a lookup on the cell's four neighbours (the way the road tiles are picked); the mask is typed by hand.
The corner tiles and edges are each typed (light from the top left is the same for every bank: the rim carries no cast shadow).
Tiles: 3 water + 4 banks + 4 outer corners + 4 inner corners = 15; bridges 4; floating logs 2 pieces (= 2 + 2 tiles on flat water); the pile is the lodge's own log ends."""
from canvas import piece
import v_lodge

# ---- water ----------------------------------------------------------------------------------------------------------------------------------------
WF = ["22222222"] * 8                                                                        # open water
WA = ["22222222", "22222222", "21122222", "22211222", "22222112", "22222222", "22222222", "22222222"]     # ripple glint, falling to the right
WB = ["22222222", "22222222", "22222222", "22112222", "22221122", "22222222", "22222222", "22222222"]     # glint, a different rhythm
# banks: land 0, sand rim 1, water 2.  The rim steps one pixel every three, so a run of the same tile is a gentle scallop.
BN = ["00000000", "00000000", "00000000", "11000111", "22111222", "22222222", "22222222", "22222222"]     # land to the north
BS = ["22222222", "22222222", "22222222", "22111222", "11000111", "00000000", "00000000", "00000000"]     # land to the south
BW = ["00012222", "00012222", "00001222", "00001222", "00001222", "00012222", "00012222", "00012222"]     # land to the west
BE = ["22221000", "22221000", "22210000", "22210000", "22210000", "22221000", "22221000", "22221000"]     # land to the east
# outer corners (water on the inside of a bend, land round it): named by the two land sides
CNW = ["00000000", "00000000", "00000000", "00000011", "00000112", "00001122", "00011222", "00012222"]
CNE = ["00000000", "00000000", "00000000", "11000000", "21100000", "22110000", "22211000", "22221000"]
CSW = ["00012222", "00011222", "00001122", "00000112", "00000011", "00000000", "00000000", "00000000"]
CSE = ["22221000", "22211000", "22110000", "21100000", "11000000", "00000000", "00000000", "00000000"]
# inner corners (the water bends round a headland): named by the land corner
INE = ["22221000", "22222100", "22222210", "22222221", "22222222", "22222222", "22222222", "22222222"]
INW = ["00012222", "00122222", "01222222", "12222222", "22222222", "22222222", "22222222", "22222222"]
ISE = ["22222222", "22222222", "22222222", "22222222", "22222221", "22222210", "22222100", "22221000"]
ISW = ["22222222", "22222222", "22222222", "22222222", "12222222", "01222222", "00122222", "00012222"]

# ---- bridges (palette town1, the road's: 0 light, 1 plank, 2 seam and rail, 3 ink): a deck over water, 16 px wide, rails on both sides ----------------------
BR_T = ["33333333", "22222222", "00020002", "11121112", "11121112", "11121112", "11121112", "11121112"]    # road runs east to west, top half
BR_B = ["11121112", "11121112", "11121112", "11121112", "11121112", "11121112", "22222222", "33333333"]    # bottom half
BR_L = ["32000000", "32111111", "32111111", "32222222", "32111111", "32111111", "32111111", "32222222"]    # road runs north to south, left half
BR_R = ["00000023", "11111123", "11111123", "22222223", "11111123", "11111123", "11111123", "22222223"]    # right half

# ---- floating logs (pieces on flat water): 16 x 6 lying across, and the same turned a quarter for the river's flow --------------------------------------
LOGH = ["..333333333333..", ".31111111111113.", "3111131111311113", "3111111113111113", ".31111111111113.", "..333333333333.."]
LOGV = ["".join(LOGH[c][15 - r] for c in range(6)) for r in range(16)]

FLOATLOG_H = ("water", LOGH)
FLOATLOG_V = ("water", LOGV)

# ---- the log pile: the lodge's own log ends (DMG arrangement, 8 px apart), a three-two-one stack, 22 x 16 -----------------------------------------------
_pile = [["."] * 22 for _ in range(16)]
for (x, y) in ((0, 10), (8, 10), (16, 10), (4, 5), (12, 5), (8, 0)):
    for j, r in enumerate(v_lodge.LOGEND):
        for i, c in enumerate(r):
            if c != ".":
                _pile[y + j][x + i] = c
LOGPILE = ("lodge", ["".join(r) for r in _pile])

WATER_TILES = {"WF": WF, "WA": WA, "WB": WB, "BN": BN, "BS": BS, "BW": BW, "BE": BE, "CNW": CNW, "CNE": CNE, "CSW": CSW, "CSE": CSE,
               "INE": INE, "INW": INW, "ISE": ISE, "ISW": ISW}
BRIDGE_TILES = {"T": BR_T, "B": BR_B, "L": BR_L, "R": BR_R}


def water_tile(mask, cx, cy, W, H):
    """the tile of a cell of the typed water mask: a lookup on the four sides (land = a cell outside the mask; the map's south edge counts as water)"""
    def m(x, y):
        return (x, y) in mask or y >= H
    n, e, s, w = m(cx, cy - 1), m(cx + 1, cy), m(cx, cy + 1), m(cx - 1, cy)
    land = [not n, not e, not s, not w]
    k = sum(land)
    if k == 0:
        diag = {"CNE": not m(cx + 1, cy - 1), "CSE": not m(cx + 1, cy + 1), "CSW": not m(cx - 1, cy + 1), "CNW": not m(cx - 1, cy - 1)}
        d = [name for name, v in diag.items() if v]
        assert len(d) <= 1, ("two inner corners on one cell", cx, cy)
        if d:
            return {"CNE": INE, "CSE": ISE, "CSW": ISW, "CNW": INW}[d[0]]
        hh = (cx * 7 + cy * 13 + cx * cy) % 13
        return WA if hh in (3, 8) else WB if hh in (5, 11) else WF
    if k == 1:
        return BN if land[0] else BE if land[1] else BS if land[2] else BW
    assert k == 2 and land[0] != land[2] and land[1] != land[3], ("water cell with land on", land, cx, cy)
    if land[0] and land[3]:
        return CNW
    if land[0] and land[1]:
        return CNE
    if land[2] and land[1]:
        return CSE
    return CSW


# ---- placeholder boxes (marked on every sheet; not art): a hatch that keeps an assumed number of distinct tiles, a dark border -----------------------------
class Box:
    def __init__(self, w, h, pal, nuniq):
        self.w, self.h, self.pal, self.nuniq = w, h, pal, nuniq

    def out(self):
        rows = []
        for j in range(self.h):
            for y in range(8):
                r = ""
                for i in range(self.w):
                    k = (i + j * self.w) % self.nuniq
                    for x in range(8):
                        gx, gy = i * 8 + x, j * 8 + y
                        edge = gx in (0, self.w * 8 - 1) or gy in (0, self.h * 8 - 1)
                        r += "3" if edge else "2" if (x + y + 2 * k) % 8 < 3 else "1"
                rows.append(r)
        return rows

    def cellpals(self):
        return [[self.pal] * self.w for _ in range(self.h)]
