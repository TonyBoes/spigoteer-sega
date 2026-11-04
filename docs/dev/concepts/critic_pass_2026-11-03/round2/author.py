#!/usr/bin/env python3
"""Food Critic round 2: the hand-typed grids of version A and version B (preview + drop-in writer only).

Every pixel is typed by the artist: the face interiors and the rows below. This file only joins typed pieces into
32-wide rows ('.' wall, '-' skin, '+' plum, '#' outline / black) and writes <ver>.txt. The beret (rows 0-3), the cravat /
jacket / shirt / notebook (rows 9-15, cols 0-20) and the topper are the CURRENT art's, retyped as is; the face (rows
4-8) and the right arm / hand (cols 21-31) are new.
  author.py A|B   -> A.txt / B.txt (@WALK @GULP @WINCE @HAPPY @TASTE @HOLD)

Tile-pair economy (the engine's body is 4 columns of 8x16 tiles, 29 unique pairs at most, today 27): every face feature
sits in cols 8-15 and every arm detail in cols 24-31, so cols 0-7 and 16-23 are the same typed pixels in every pose
except the two noted (GULP's fist reaches col 21; WINCE's fist is on his chest).
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
# cols 24-31 per pose (rows 9-15). WALK: a fist hanging at rest (plum cuff, then the hand). TASTE: a fist at the end of the
# sleeve under the wagging finger. HAPPY: a raised fist, thumb up (empty: no glass needed). HOLD: a fist round the glass's stem
# (the engine's glass sprite is drawn over it: stem cols 27-28, foot cols 25-30 on row 12).
E = {
    "WALK": ["........", "........", "####....", "+++#....", "---#....", "---#....", "####...."],
    "TASTE": [".#----#.", ".#----#.", "##++++#.", "#######.", "#######.", "#######.", "#######."],
    "HAPPY": [".#----#.", ".#++++#.", "#######.", "#######.", "#######.", "#######.", "#######."],
    "HOLD": [".#----#.", ".#----#.", "+-----#.", "........", "........", "........", "........"],
}
# rows 9-15 typed in full where cols 0-23 are not C
FULL = {
    "GULP": [                                   # the fist is up at the glass (cols 21-24, rows 11-13); the glass sprite is drawn over it
        ".....###############............",
        "..#######++++++###-#######......",
        ".#######++++++++#-###----#......",
        "######.###++++####-##----#......",
        "#+---#--###++########----#......",
        "#+---#--####+#############......",
        "#+---#####################......",
    ],
    "WINCE": [                                  # the notebook jerks up (left), the fist clutches his chest (cols 17-20), the elbow out
        "##########++########............",
        "#+---########++###-##...........",
        "#+---###++++++++#----#######....",
        "#+---#--##++++###----#######....",
        "######--###++####----#######....",
        "############+###############....",
        "############################....",
    ],
}
HAPPY_L = [                                     # HAPPY's cols 0-23: the notebook shown with its star
    "####################....",
    "#-+--####++++++###-##...",
    "#+++-###++++++++#-######",
    "#-+--#--##++++####-#####",
    "#----#--###++###########",
    "############+###########",
    "########################",
]
# the hand above row 9 (rows 4-8), typed per pose as overlays (row, col, text)
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


# ---------------------------------------------------------------------------------------------------------------
# faces (interiors). ruler for rows 4-7: idx 0..16 = cols 4..20: left eye idx 4-6 (cols 8-10), the monocle's ring: sides
# idx 9 and 13 (cols 13, 17), its inside idx 10-12 (the pupil idx 11 = col 15), bottom row 7 idx 10-12. Row 8 (chin):
# idx 0..14 = cols 5..19, the chain's end at idx 12 (col 17).
# ---------------------------------------------------------------------------------------------------------------
def A_faces():
    """A: a plum brow raised over a hooded eye (a dash), the monocle eye looking down, a small flat mouth set under it"""
    return {
        "WALK": face("----+++--#---#---", "---------#---#---", "----###--#-#-#---", "----------###----", "-----+++----#--"),
        "GULP": face("----+++--#---#---", "---------#---#---", "----###--#-#-#---", "-------++-###----", "------++----#--"),
        "WINCE": face("----+++--#++-#---", "----###--#---#---", "----###--#-#-#---", "------###-###----", "-----+++----#--"),
        "HAPPY": face("---------#---#---", "---------#---#---", "----###--#-#-#---", "-----+---+###----", "-----+++----#--"),
        "TASTE": face("----+++--#---#---", "---------#---#---", "----###--#-#-#---", "------##--###----", "----#--#----#--"),
        "HOLD": face("---------#---#---", "---------#---#---", "----###--###-#---", "----------###----", "----+++++---#--"),
    }


def B_faces():
    """B: a heavy black brow slanting down to the nose over the left eye, the monocle open, a downturned plum mouth"""
    return {
        "WALK": face("----###--#---#---", "-------#-#-#-#---", "-----#---#---#---", "----------###----", "------++----#--"),
        "GULP": face("----###--#---#---", "-------#-#-#-#---", "----###--#---#---", "-------++-###----", "------++----#--"),
        "WINCE": face("----###--#---#---", "-------#-#-#-#---", "----###--#---#---", "------###-###----", "-----+++----#--"),
        "HAPPY": face("---------#---#---", "---------#-#-#---", "-----#---#---#---", "-----+---+###----", "-----+++----#--"),
        "TASTE": face("----###--#---#---", "-------#-#-#-#---", "-----#---#---#---", "------##--###----", "----#--#----#--"),
        "HOLD": face("---------#---#---", "---------#---#---", "----###--###-#---", "----------###----", "----+++++---#--"),
    }


def block(name, rows):
    assert len(rows) == 16 and all(len(r) == W for r in rows), (name, len(rows), [len(r) for r in rows])
    return f"@{name}\n" + "\n".join(rows) + "\n"


if __name__ == "__main__":
    v = sys.argv[1]
    F = {"A": A_faces, "B": B_faces}[v]()
    out = ""
    for n, f in F.items():
        out += block(n, pose(n, f)) + "\n"
    (HERE / f"{v}.txt").write_text(out)
    print("wrote", HERE / f"{v}.txt", list(F))
