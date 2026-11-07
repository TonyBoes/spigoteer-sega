"""Milk bar round 4k (owner): "not what I wanted with the arrow. Something more like what these classic signs looked like" (refs/owner_sign_diner.jpg and
owner_sign_coffee.jpg).  Two signs, typed by hand, 24 px wide x 56 rows (canvas y 64..119, x 0..23: the lawn between the river bank and the building's wing);
the arrow is a thick filled band (6 px) with a chrome tube inside an ink outline, and a big solid head that points right at the bar.
Palette COW: 1 chrome (the tube, the letters, the bulbs), 2 pink (the band), 3 ink.  Static.
 A (coffee sign): the post is a tall vertical panel reading MILK top to bottom, the bottle on top, the panel's foot bends into the arrow.
 B (diner sign): the bottle on its pole, a band wraps round its left side and under it into the arrow, a row of bulbs along the band."""
from cow_a3 import LET
from cow_c import BOTTLE

D = "." * 10
# the arrow head, 8 wide (x 16..23), rows r46..r55 of sign A (r32..r41 of sign B); the back edge is open where the arm joins
HEAD = ["33......", "3133....", "321133..", "1222113.", "22222213", "22222213", "1222113.", "321133..", "3133....", "33......"]


def put(c, x, y, rows):
    for j, r in enumerate(rows):
        assert len(r) <= 24, (j, len(r))
        for i, ch in enumerate(r):
            if ch not in "._":
                c.px[y + j][x + i] = ch


def sign_a(c, y0=64):
    PN = "...3122222213"
    rows = {}
    rows[23] = "...3333333333" + "." * 11
    rows[24] = "...3111111113" + "." * 11
    for r in range(25, 46):
        rows[r] = PN + "." * 11
    rows[46] = PN + "..." + HEAD[0]
    rows[47] = PN + "..." + HEAD[1]
    rows[48] = "...3122222213333" + HEAD[2]
    rows[49] = "...3122222211111" + HEAD[3]
    rows[50] = "...31" + "2" * 11 + HEAD[4]
    rows[51] = "...31" + "2" * 11 + HEAD[5]
    rows[52] = "...3" + "1" * 12 + HEAD[6]
    rows[53] = "..." + "3" * 13 + HEAD[7]
    rows[54] = "." * 16 + HEAD[8]
    rows[55] = "." * 16 + HEAD[9]
    for r, s in rows.items():
        assert len(s) == 24, (r, len(s))
    put(c, 0, y0, [rows.get(r, "." * 24) for r in range(56)])
    put(c, 0, y0, BOTTLE)                                  # the bottle on top of the panel (16 wide, x 0..15)
    y = y0 + 26                                            # MILK, one letter under the other, chrome on the pink: M at x 5, the 3-wide letters at x 6
    for ch, x in (("M", 5), ("I", 6), ("L", 6), ("K", 6)):
        for j, r in enumerate(LET[ch]):
            for i, v in enumerate(r):
                if v == "1":
                    c.px[y + j][x + i] = "1"
        y += 6


def sign_b(c, y0=64):
    rows = {}
    rows[6] = ".3333." + "." * 18
    rows[7] = "311113" + "." * 18
    for r in range(8, 34):
        bulb = "1" if r % 2 == 0 else "2"
        band = "31" + bulb + "2" + "13"
        if r == 32:
            rows[r] = band + D + HEAD[0]
        elif r == 33:
            rows[r] = band + D + HEAD[1]
        else:
            rows[r] = band + "." * 18
    rows[34] = "3122" + "1" + "3" * 11 + HEAD[2]
    rows[35] = "3122" + "1" * 12 + HEAD[3]
    rows[36] = "31" + "12121212121212" + HEAD[4]
    rows[37] = "31" + "2" * 14 + HEAD[5]
    rows[38] = "3" + "1" * 15 + HEAD[6]
    rows[39] = "." + "3" * 15 + HEAD[7]
    rows[40] = "." * 16 + HEAD[8]
    rows[41] = "." * 16 + HEAD[9]
    for r, s in rows.items():
        assert len(s) == 24, (r, len(s))
    put(c, 7, y0 + 2, BOTTLE)                              # the bottle, 16 wide, x 7..22
    for y in range(y0 + 25, y0 + 46):                      # the pole behind the band
        for i, ch in enumerate("3113"):
            c.px[y][13 + i] = ch
    for i, ch in enumerate("33333333"):
        c.px[y0 + 46][11 + i] = ch
    for i, ch in enumerate("31111113"):
        c.px[y0 + 47][11 + i] = ch
    put(c, 0, y0, [rows.get(r, "." * 24) for r in range(56)])


def sign_b2(c, y0=64):
    """B after the quality pass (round 4k, final): the band is an ink outline with a 4 px pink fill (no chrome tube against the bulbs), the bulbs are 2 x 2 chrome blocks
    with a pink margin on every side (every 4 px along the band), the bottom left bend is a stepped quarter circle of radius 4 and the inside corner is chamfered"""
    rows = {}
    rows[6] = ".3333." + "." * 18
    rows[7] = "322223" + "." * 18
    for r in range(8, 34):
        band = "322223"
        if r == 32:
            rows[r] = band + D + HEAD[0]
        elif r == 33:
            rows[r] = band + D + HEAD[1]
        else:
            rows[r] = band + "." * 18
    rows[34] = "3" + "22222" + "3" * 10 + HEAD[2]
    rows[35] = "3" + "2" * 15 + HEAD[3]
    rows[36] = "3" + "2" * 15 + HEAD[4]
    rows[37] = ".3" + "2" * 14 + HEAD[5]
    rows[38] = "..3" + "2" * 13 + HEAD[6]
    rows[39] = "..." + "3" * 13 + HEAD[7]
    rows[40] = "." * 16 + HEAD[8]
    rows[41] = "." * 16 + HEAD[9]
    for r, s in rows.items():
        assert len(s) == 24, (r, len(s))
    put(c, 7, y0 + 2, BOTTLE)
    for y in range(y0 + 25, y0 + 46):
        for i, ch in enumerate("3113"):
            c.px[y][13 + i] = ch
    for i, ch in enumerate("33333333"):
        c.px[y0 + 46][11 + i] = ch
    for i, ch in enumerate("31111113"):
        c.px[y0 + 47][11 + i] = ch
    put(c, 0, y0, [rows.get(r, "." * 24) for r in range(56)])
    for (bx, br) in ((2, 10), (2, 14), (2, 18), (2, 22), (2, 26), (2, 30), (2, 34), (6, 36), (10, 36), (14, 36)):     # top left of each 2 x 2 bulb: (x, row)
        for j in range(2):
            for i in range(2):
                c.px[y0 + br + j][bx + i] = "1"


def sign_b3(c, xo, y0=64, raise_=4):
    """sign_b2 with the band's bottom (the arm and the head) raised by raise_ rows (the left side is shorter by as much, the bulb pitch stays 4) and the whole sign moved to
    x offset xo; the bottle, the pole and the foot keep their rows"""
    d = -raise_
    rows = {}
    rows[6] = ".3333." + "." * 18
    rows[7] = "322223" + "." * 18
    for r in range(8, 34 + d):
        band = "322223"
        if r == 32 + d:
            rows[r] = band + D + HEAD[0]
        elif r == 33 + d:
            rows[r] = band + D + HEAD[1]
        else:
            rows[r] = band + "." * 18
    rows[34 + d] = "3" + "22222" + "3" * 10 + HEAD[2]
    rows[35 + d] = "3" + "2" * 15 + HEAD[3]
    rows[36 + d] = "3" + "2" * 15 + HEAD[4]
    rows[37 + d] = ".3" + "2" * 14 + HEAD[5]
    rows[38 + d] = "..3" + "2" * 13 + HEAD[6]
    rows[39 + d] = "..." + "3" * 13 + HEAD[7]
    rows[40 + d] = "." * 16 + HEAD[8]
    rows[41 + d] = "." * 16 + HEAD[9]
    for r, s in rows.items():
        assert len(s) == 24, (r, len(s))
    put(c, xo + 7, y0 + 2, BOTTLE)
    for y in range(y0 + 25, y0 + 46):
        for i, ch in enumerate("3113"):
            c.px[y][xo + 13 + i] = ch
    for i, ch in enumerate("33333333"):
        c.px[y0 + 46][xo + 11 + i] = ch
    for i, ch in enumerate("31111113"):
        c.px[y0 + 47][xo + 11 + i] = ch
    put(c, xo, y0, [rows.get(r, "." * 24) for r in range(56)])
    for (bx, br) in ((2, 10), (2, 14), (2, 18), (2, 22), (2, 26), (2, 34 + d), (6, 36 + d), (10, 36 + d), (14, 36 + d)):
        for j in range(2):
            for i in range(2):
                c.px[y0 + br + j][xo + bx + i] = "1"
