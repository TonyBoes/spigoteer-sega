"""ROUND 3 air base for the space mountain: a HANGAR that does not read as an igloo, and the control tower with a radar dish and a mast light instead of the cross.
Palette BASE: 0 sand, 1 steel, 2 navy, 3 ink.  Light from the top left.  Everything is typed rows (the hangar), typed pieces (dish, lamp) or typed runs (tower, runway).

HANGAR 32 x 14: a low, wide shed (32 : 14) with a shallow arched roof whose ribs are vertical, an eave line with its shadow, straight walls, a hazard-stripe lintel and two big
sliding door leaves (navy, ribbed, a lit edge on each leaf, a centre seam, a light kick stripe).  An igloo is a tall round dome; this has flat walls, an eave and doors.
"""
import common as C
import kit as K

D = "."
# roof: a shallow arc, outline runs 3, 2, 1 (x 6..25, 3..28, 1..30, 0..31); ribs on x = 2 mod 4; a lit crest at the left of the top row
LEAF = "12222322222"            # one door leaf, 11 wide: a lit edge, one rib
STRIPE = "11111311111"          # the light kick band across both leaves
HAZ_L = "11331133113"           # the hazard band at the foot of the doors: x 4 to 14, the pattern 1133 on x = 4 mod 4
HAZ_R = "13311331133"           # x 17 to 27, same phase
HANGAR = [
    D * 6 + "3" * 20 + D * 6,
    D * 3 + "333" + "1" * 20 + "333" + D * 3,
    D * 1 + "33" + "111" + "2" + "111" + "2" + "111" + "2" + "111" + "2" + "111" + "2" + "111" + "2" + "11" + "33" + D * 1,
    "3" + "1" + "2" + "111" + "2" + "111" + "2" + "111" + "2" + "111" + "2" + "111" + "2" + "111" + "2" + "1111" + "3",
    "3" * 32,
    "3" + "2" * 30 + "3",
]
for k in range(5):
    HANGAR.append("3" + "11" + "3" + LEAF + "33" + LEAF + "3" + "22" + "3")
HANGAR.append("3" + "11" + "3" + STRIPE + "33" + STRIPE + "3" + "22" + "3")
HANGAR.append("3" + "11" + "3" + HAZ_L + "33" + HAZ_R + "3" + "22" + "3")
HANGAR.append("3" * 32)

# a radar dish seen face on (a ring, a lit upper left, a feed point) on a short post; a lamp box for the mast
DISH = C.G("...3...", ".33333.", "3011113", "3111113", ".33333.", "...3...", "...3...")
LAMP = C.G("333", "303", "333")


def hangar(c, x, yf):
    """x = left edge; 14 rows, the last one on row yf"""
    assert all(len(r) == 32 for r in HANGAR) and len(HANGAR) == 14, [len(r) for r in HANGAR]
    C.paste(c, x, yf - 13, HANGAR)


def tower(c, x, yf):
    """x = left edge of the shaft (8 wide); the cab is 12 wide, starts 2 px to the left of the shaft.  The round-2 tower body, unchanged; new top: a mast with a lamp (left)
    and a radar dish on a post (right)."""
    top = yf - 30
    K.box(c, x - 2, top, x + 10, top + 7, "3", "1")
    K.hl(c, top + 2, x - 1, x + 9, "0")
    K.hl(c, top + 3, x - 1, x + 9, "2")
    K.hl(c, top + 4, x - 1, x + 9, "2")
    K.rect(c, x, top + 7, x + 8, yf + 1, "1")
    K.vl(c, x, top + 7, yf + 1, "3")
    K.vl(c, x + 7, top + 7, yf + 1, "3")
    K.rect(c, x + 4, top + 8, x + 7, yf, "2")
    for y in range(top + 10, yf - 2, 8):
        K.hl(c, y, x + 1, x + 4, "2")
    K.hl(c, yf, x, x + 8, "3")
    # the top: a mast at x - 1 (cab's left end) with a lamp, a dish on a post at x + 6
    K.vl(c, x - 1, top - 6, top, "3")
    C.paste(c, x - 2, top - 9, LAMP)
    C.paste(c, x + 3, top - 7, DISH)


# the angled runway (variant only): a strip 5 rows thick whose top edge rises 1 row per 4 columns to the right (about 14 degrees), x 6 to 50, in front of the hangar and the
# tower (the variant stands them 8 px higher, foot on y 55).  Typed per column: the top row y(x) = 66 - (x - 6) // 4 is a typed run (1 row per 4 columns); the rows of a column are
# the typed characters of RW (lit edge 1, asphalt 2, centre 2, asphalt 2, shade edge 3); the centre dash 0 on columns 0-3 of every 8.
RW = "12223"


def runway(c, x0=6, x1=50, y0=66, run=4):
    for x in range(x0, x1 + 1):
        t = y0 - (x - x0) // run
        for k, ch in enumerate(RW):
            c.px[t + k][x] = ch
        if x % 8 < 4:
            c.px[t + 2][x] = "0"
