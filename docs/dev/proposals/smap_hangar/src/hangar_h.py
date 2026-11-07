"""ROUND 4 hangars for the space mountain (owner: "round 3 no runway. But do a little more work on the hanger. It looks like a hut. Maybe a runway in front again,
with a little plane sitting inside the hanger doors?").  Only the hangar changes; peaks, mast, dish and tower are round 3's, untouched.
Palette BASE: 0 sand, 1 steel, 2 navy, 3 ink.  Light from the top left.  Everything below is typed rows (hangars, planes) or typed runs (the strip).
Both hangars are 34 x 16 (round 3's was 32 x 14) and stand with their foot on y 63, x 0 to 33; the tower's cab starts at x 36.
"""
import common as C

D = "."

# ------------------------------------------------------------------ option 1: ARCH FRONT.
# The whole front is one big arch (a Quonset end): a curved rim, lit on the left and shaded on the right, and a broad arched opening (24 wide, navy) with a plane in
# it seen head on.  Outline left edge by row: 10, 6, 4, 3, 2, 1, 1, 0 (steps 4, 2, 1, 1, 1, 0: the curve steepens toward the wall).
H1 = [
    D * 10 + "3" * 14 + D * 10,                                                   # r0  top of the arch
    D * 6 + "3" * 4 + "0" + "1" * 12 + "2" + "3" * 4 + D * 6,                     # r1
    D * 4 + "33" + "0" + "1" * 20 + "2" + "33" + D * 4,                           # r2
    D * 3 + "3" + "0" + "1" * 24 + "2" + "3" + D * 3,                             # r3
    D * 2 + "3" + "0" + "1" * 8 + "3" * 10 + "1" * 8 + "2" + "3" + D * 2,         # r4  the opening's crown (ink)
    D + "3" + "0" + "1" * 6 + "3" * 16 + "1" * 6 + "2" + "3" + D,                 # r5
    D + "3" + "0" + "1" * 4 + "33" + "2" * 16 + "33" + "1" * 4 + "2" + "3" + D,   # r6  opening 16 wide
    "3" + "0" + "1" * 4 + "3" + "2" * 20 + "3" + "1" * 4 + "2" + "3",             # r7  20
    "3" + "0" + "1" * 3 + "3" + "2" * 22 + "3" + "1" * 3 + "2" + "3",             # r8  22
]
for _ in range(6):                                                                # r9..r14  opening 24 wide
    H1.append("3" + "0" + "11" + "3" + "2" * 24 + "3" + "11" + "2" + "3")
H1.append("3" * 34)                                                               # r15  foot line

# the plane, head on (18 wide, hangar x 8 to 25, rows 6 to 14): tail fin over the fuselage, a straight wing (lit top, steel underside), two legs, a dark floor shadow
PLANE1 = C.G(
    D * 8 + "01" + D * 8,
    D * 8 + "01" + D * 8,
    D * 7 + "0111" + D * 7,
    D + "0" * 6 + "0111" + "0" * 6 + D,
    "1" * 7 + "0111" + "1" * 7,
    D * 7 + "0111" + D * 7,
    D * 7 + "0111" + D * 7,
    D * 4 + "1" + D * 2 + "0111" + D * 2 + "1" + D * 4,
    D * 3 + "3" * 12 + D * 3,
)

# ------------------------------------------------------------------ option 2: CURVED ROOF, SLID DOORS.
# A ribbed barrel roof (outline runs 4, 3, 2, 1: the top row is 16 wide, the eave 34), an eave line with its shadow row, a hazard lintel over the whole door span, and the
# two door leaves slid back to the sides, so the opening is a broad black slot (22 wide) with a plane standing in it, seen from the side, nose to the right.
H2 = [
    D * 9 + "3" * 16 + D * 9,                                                     # r0
    D * 5 + "3" * 4 + "0111" + "2111" * 3 + "3" * 4 + D * 5,                      # r1  ribs on x = 3 mod 4
    D * 2 + "33" + "011" + "2111" * 5 + "211" + "33" + D * 2,                     # r2
    D + "3" + "0" + "2111" * 7 + "1" + "3" + D,                                   # r3
    "3" + "01" + "2111" * 7 + "11" + "3",                                         # r4
    "3" * 34,                                                                     # r5  eave line
    "3" + "2" * 32 + "3",                                                         # r6  its shadow
    "3" + "01" + "1331" * 7 + "12" + "3",                                         # r7  hazard lintel (phase keeps ink off the opening corners)
]
for _ in range(6):                                                                # r8..r13  opening
    H2.append("3" + "01" + "121" + "3" * 22 + "121" + "12" + "3")
H2.append("3" + "01" + "121" + "2" * 22 + "121" + "12" + "3")                     # r14 floor
H2.append("3" * 34)                                                               # r15

# the plane, side view, nose to the right (22 wide, hangar x 6 to 27, rows 8 to 13): tail fin, far wing tip above the cabin, lit back, cockpit window, shaded belly, two leg stubs
PLANE2 = C.G(
    D * 2 + "01" + D * 18,
    D * 2 + "01" + D * 8 + "000" + D * 7,
    D + "0" * 15 + "1" * 3 + D * 3,
    "0" + "1" * 9 + "3" * 3 + "1" * 8 + D,
    D + "1" * 3 + "2" * 14 + D * 4,
    D * 5 + "1" + D * 9 + "1" + D * 6,
)



def _check():
    assert len(H1) == 16 and all(len(r) == 34 for r in H1), [len(r) for r in H1]
    assert len(H2) == 16 and all(len(r) == 34 for r in H2), [len(r) for r in H2]


_check()


def hangar1(c, x, yf):
    C.paste(c, x, yf - 15, H1)
    C.paste(c, x + 8, yf - 15 + 6, PLANE1)


def hangar2(c, x, yf):
    C.paste(c, x, yf - 15, H2)
    C.paste(c, x + 6, yf - 15 + 8, PLANE2)


# ------------------------------------------------------------------ the strip in front: an apron under the doors and a short runway across the foot of the piece.
# Seen from above in the map's perspective: ink outline all round, navy asphalt, a one-pixel dashed centre line (4 on, 4 off, period 8 so every strip cell is the same tile),
# a lit steel kerb line under the top ink.  Typed runs: apron x 4..29 on y 64..65, runway x 1..50 on y 66..70.
def strip(c, apron=(4, 29), run=(1, 50)):
    ax0, ax1 = apron
    rx0, rx1 = run
    for y in (64, 65):                          # the apron: ink sides, asphalt between
        c.px[y][ax0] = "3"
        c.px[y][ax1] = "3"
        for x in range(ax0 + 1, ax1):
            c.px[y][x] = "2"
    for x in range(rx0, rx1 + 1):               # the runway
        cap = x in (rx0, rx1)
        c.px[66][x] = "3" if (cap or not ax0 < x < ax1) else "2"
        c.px[67][x] = "3" if cap else "2"
        c.px[68][x] = "3" if cap else ("0" if x % 8 < 4 else "2")
        c.px[69][x] = "3" if cap else "2"
        c.px[70][x] = "3"
    for x in range(rx0 + 1, rx1):
        if not ax0 < x < ax1:
            c.px[67][x] = "1"                    # lit kerb under the top ink (not where the apron joins)
