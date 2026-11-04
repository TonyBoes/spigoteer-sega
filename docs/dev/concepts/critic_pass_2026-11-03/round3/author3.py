#!/usr/bin/env python3
"""Food Critic round 3 (A3): the hand-typed grids of the quality pass on round 2's version A (preview + drop-in writer only).

Every pixel is typed by the artist: the face interiors, the resting hand and the rows below. This file only joins typed pieces
into 32-wide rows ('.' wall, '-' skin, '+' plum, '#' outline / black) and writes A3.txt. The beret (rows 0-3), the cravat /
jacket / shirt / notebook (rows 9-15, cols 0-20) and the topper are the CURRENT art's, retyped as is.
  author3.py  -> A3.txt (@WALK @GULP @WINCE @HAPPY @TASTE @HOLD)

Tile-pair economy (29 unique 8x16 pairs at most; round 2 A used 28): every face feature sits in cols 8-15; cols 16-17 (the
monocle ring's right side and bottom) are the same typed pixels in every pose, and so are cols 0-7 and 16-23 below row 8
except the poses that already differ there (GULP's fist, WINCE's notebook, HAPPY's notebook).
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
W = 32


def pad(r):
    assert len(r) <= W, (len(r), r)
    return r.ljust(W, ".")


def face(i4, i5, i6, i7, i8):
    """rows 4-8: interiors typed by hand (17 px for rows 4-7 = cols 4..20, 15 px for row 8 = cols 5..19); the outline
    pixels around them (left col 3, right col 21 / 20, the beret's underside on row 4) are the current art's."""
    assert len(i4) == len(i5) == len(i6) == len(i7) == 17 and len(i8) == 15, (len(i4), len(i5), len(i6), len(i7), len(i8))
    return [pad("...#" + i4 + "###"), pad("...#" + i5 + "#"), pad("...#" + i6 + "#"), pad("...#" + i7 + "#"), pad("....#" + i8 + "#")]


HAT = [                                         # rows 0-3: the current beret, every pose
    ".....####-++#####...............",
    "...##--+++++++++++###...........",
    "..#-++++++++++++++++++#.........",
    "...##################++#........",
]

# rows 9-15, cols 0-23: the current jacket, cravat and notebook, the sleeve ending at col 23 (typed once)
C = [
    ".....###############....",
    "..#######++++++###-##...",
    ".#######++++++++#-######",
    "######.###++++####-#####",
    "#+---#--###++###########",
    "#+---#--####+###########",
    "#+---###################",
]
# cols 24-31 per pose (rows 9-15). WALK: the resting hand (a fist with a thumb, knuckles to the right, a plum cuff).
E = {
    "WALK": ["........", "........", "........", "........", "........", "........", "........"],
    "TASTE": [".#----#.", ".#----#.", "##++++#.", "#######.", "#######.", "#######.", "#######."],
    "HAPPY": [".#----#.", ".#++++#.", "#######.", "#######.", "#######.", "#######.", "#######."],
    "HOLD": [".#----#.", ".#----#.", "+-----#.", "........", "........", "........", "........"],
}
HAND = {}           # filled by the hand section below
FULL = {
    "GULP": [
        ".....###############............",
        "..#######++++++###-#######......",
        ".#######++++++++#-###----#......",
        "######.###++++####-##----#......",
        "#+---#--###++########----#......",
        "#+---#--####+#############......",
        "#+---#####################......",
    ],
    "WINCE": [
        "##########++########............",
        "#+---########++###-##...........",
        "#+---###++++++++#----#######....",
        "#+---#--##++++###----#######....",
        "######--###++####----#######....",
        "############+###############....",
        "############################....",
    ],
}
HAPPY_L = [
    "####################....",
    "#-+--####++++++###-##...",
    "#+++-###++++++++#-######",
    "#-+--#--##++++####-#####",
    "#----#--###++###########",
    "############+###########",
    "########################",
]
UP = {
    "HAPPY": [(4, 27, "##"), (5, 26, "#--#"), (6, 26, "#--#"), (7, 25, "#----#"), (8, 25, "#----#")],
    "TASTE": [(5, 29, "#"), (6, 28, "#-#"), (7, 27, "#-#"), (8, 26, "#-##")],
    "HOLD": [(8, 25, "######")],
}




def over(rows, ov):
    rows = list(rows)
    for r, c, t in ov:
        rows[r] = rows[r][:c] + t + rows[r][c + len(t):]
    return rows


def pose(name, f):
    if name in FULL:
        body = FULL[name]
    elif name == "HAPPY":
        body = [a + b for a, b in zip(HAPPY_L, E["HAPPY"])]
    else:
        body = [a + b for a, b in zip(C, E[name if name in E else "WALK"])]
    return over(HAT + f, UP.get(name, [])) + [pad(r) for r in body]



sys.path.insert(0, str(HERE))
from a3_faces import FACES, WALK_E  # noqa: E402  the typed faces and the hand
E["WALK"] = WALK_E


def block(name, rows):
    assert len(rows) == 16 and all(len(r) == W for r in rows), (name, len(rows), [len(r) for r in rows])
    return f"@{name}\n" + "\n".join(rows) + "\n"


if __name__ == "__main__":
    out = ""
    for n, f in FACES.items():
        out += block(n, pose(n, face(*f))) + "\n"
    (HERE / "A3.txt").write_text(out)
    print("wrote", HERE / "A3.txt", list(FACES))
