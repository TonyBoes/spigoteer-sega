"""The typed faces (rows 4-8) and WALK's resting hand of A3, in absolute columns.

Each row is typed as {first column: pixels}; every other pixel of the row is skin '-'. Rows 4-7 cover cols 4..20, row 8 cols 5..19.
Fixed in every pose (so cols 16-17 stay one shared tile column, as in round 2 A): the monocle ring's sides (cols 13 and 17, rows 4-6),
its bottom (row 7, cols 14-16) and the chain's end (row 8, col 17). Everything a pose changes sits in cols 8-15.

No plum brow any more (it read as eyeshadow): the near eye is a heavy lid over a pupil, the monocle eye a staring dot, and the
mouth carries the sneer.
"""


def R(d, w=17, c0=4):
    r = ["-"] * w
    for col, t in d.items():
        for k, ch in enumerate(t):
            r[col - c0 + k] = ch
    return "".join(r)


def F(r4, r5, r6, r7, r8):
    return (R(r4), R(r5), R(r6), R(r7), R(r8, 15, 5))


RING = {13: "#", 17: "#"}
BOT = {14: "###"}                      # the ring's bottom, row 7
CH = {17: "#"}                         # the chain's end, row 8
FACES = {
    # judging: a heavy lid over a pupil, the monocle eye staring, the mouth curled up at the near end (a sneer)
    "WALK": F({8: "###", 13: "#", 17: "#"}, {9: "#", 13: "#", 15: "#", 17: "#"}, RING,
              {8: "+", **BOT}, {9: "++++", **CH}),
    # savouring: eyes shut in arcs, the mouth a little open
    "GULP": F(RING, {9: "##", 13: "#", 17: "#"}, {8: "#", 11: "#", 13: "#", 17: "#"},
              {8: "+", 13: "+", **BOT}, {9: "++++", **CH}),
    # the push-back: both eyes squeezed to thin chevrons, the grimace open
    "WINCE": F(RING, {8: "#", 13: "#", 15: "#", 17: "#"}, {9: "#", 13: "#", 14: "#", 17: "#"},
               {8: "#", 11: "##", **BOT}, {10: "+++", **CH}),
    # won: laughing cups, an open smile
    "HAPPY": F(RING, {8: "#", 11: "#", 13: "#", 17: "#"}, {9: "##", 13: "#", 17: "#"},
               {8: "+", 13: "+", **BOT}, {9: "++++", **CH}),
    # sloppy drink: the lid half down, the pupils sliding to the glass, a down-turned mouth
    "TASTE": F({8: "###", 13: "#", 17: "#"}, {10: "#", 13: "#", 15: "#", 17: "#"}, RING,
               {9: "++++", **BOT}, {8: "+", 13: "+", **CH}),
    # savouring with the glass held: the arcs and a small smile
    "HOLD": F(RING, {9: "##", 13: "#", 17: "#"}, {8: "#", 11: "#", 13: "#", 17: "#"},
              {8: "+", 13: "+", **BOT}, {9: "++++", **CH}),
}
# WALK's hand, rows 9-15 of cols 24-31 (8 px each): a plum cuff, then a fist, knuckles to the right and one finger crease
WALK_E = ["........", "........", "####....", "+---##..", "+----#..", "+--#-#..", "#####..."]
