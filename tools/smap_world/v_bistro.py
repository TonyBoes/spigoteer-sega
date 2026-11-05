"""The Bistro, 72 x 56. Palette BISTRO: 0 cream (the paved yard), 1 light teal, 2 dark teal, 3 ink.
A teal brick shop front with a sign board, a striped awning, a big window with a chalk menu, a double door, a checker patio,
a round table and a clipped shrub in a pot."""
from canvas import Canvas, piece

W, H = 72, 56
PAL = "bistro"

LET = {"B": ["110", "101", "110", "101", "110"], "I": ["111", "010", "010", "010", "111"], "S": ["111", "100", "111", "001", "111"],
       "T": ["111", "010", "010", "010", "010"], "R": ["110", "101", "110", "101", "101"], "O": ["111", "101", "101", "101", "111"]}
DOOR = piece("3:12", "3:1 2:10 3:1", ("3:1 2:1 0:8 2:1 3:1", 9), "3:1 2:10 3:1", ("3:1 2:4 3:2 2:4 3:1", 3), "3:1 2:3 0:1 3:2 0:1 2:3 3:1",
             ("3:1 2:4 3:2 2:4 3:1", 4), "3:12")
G = "3:1 2:1 0:11 2:2 0:11 2:1 3:1"
WINDOW = piece("3:28", "3:1 2:26 3:1", (G, 4), "3:1 2:1 0:3 1:5 0:3 2:2 0:11 2:1 3:1", G, "3:1 2:1 0:3 1:5 0:3 2:2 0:11 2:1 3:1", G,
               "3:1 2:1 0:3 1:5 0:3 2:2 0:11 2:1 3:1", G, "3:1 2:1 0:11 2:2 0:3 1:5 0:3 2:1 3:1",
               "3:1 2:1 0:11 2:2 0:5 1:1 0:5 2:1 3:1", "3:1 2:1 0:11 2:2 0:5 1:1 0:5 2:1 3:1", G, "3:1 2:26 3:1", "3:28")
TABLE = piece(".:3 3:10 .:3", ".:1 3:2 0:10 3:2 .:1", "3:1 0:14 3:1", ".:1 3:2 2:10 3:2 .:1", ".:3 3:10 .:3",
              (".:7 3:1 2:1 3:1 .:6", 5), ".:4 3:8 .:4", ".:5 3:6 .:5")
SHRUB = piece(".:3 3:5 .:3", ".:1 3:2 1:5 3:2 .:1", "3:1 1:3 2:3 1:3 3:1", "3:1 1:2 2:5 1:2 3:1", ".:1 3:2 2:5 3:2 .:1", ".:3 3:5 .:3",
              (".:5 3:1 .:5", 2), ".:2 3:7 .:2", ".:2 3:1 2:5 3:1 .:2", ".:3 3:1 2:3 3:1 .:3", ".:3 3:5 .:3")


def build(dmg=False):
    c = Canvas("bistro", PAL, W, H)
    # ---- the sign board -------------------------------------------------------------------------------------------------
    c.row(0, "0:20 3:32 0:20")
    for y in range(1, 9):
        c.row(y, "0:20 3:1 2:30 3:1 0:20")
    c.row(9, "0:20 3:32 0:20")
    for k, ch in enumerate("BISTRO"):
        for j, r in enumerate(LET[ch]):
            for i, v in enumerate(r):
                if v == "1":
                    c.put(22 + k * 5 + i, 2 + j, "0")
    # ---- the front: cornice, brick courses of five rows and a mortar row --------------------------------------------------
    c.row(10, "0:4 3:64 0:4")
    A = "0:6 3:1 1:11 2:1 1:11 2:1 1:11 2:1 1:11 2:1 1:10 3:1 0:6"
    B = "0:6 3:1 1:5 (2:1 1:11)*4 2:1 1:4 3:1 0:6"
    if dmg:                                                  # DMG: bricks 8 wide, so the courses repeat tile for tile (the Color picture keeps 12)
        A = "0:6 3:1 2:1 (1:7 2:1)*7 1:1 3:1 0:6"
        B = "0:6 3:1 1:4 2:1 (1:7 2:1)*6 1:5 3:1 0:6"
    M = "0:6 3:1 2:58 3:1 0:6"
    y = 11
    for course in range(6):
        for _ in range(5):
            c.row(y, A if course % 2 == 0 else B)
            y += 1
        c.row(y, M)
        y += 1
    # ---- the awning ---------------------------------------------------------------------------------------------------------
    c.row(14, "0:3 3:66 0:3")
    for y in range(15, 21):
        c.row(y, "0:3 3:1 (0:4 2:4)*8 3:1 0:3")
    c.row(21, "0:3 3:1 (0:1 3:2 0:1 2:1 3:2 2:1)*8 3:1 0:3")
    # ---- window, door ------------------------------------------------------------------------------------------------------
    c.paste(10, 26, WINDOW)
    c.paste(46, 26, DOOR)
    # ---- the patio: a foot line, then a checker of 4 x 4 squares ------------------------------------------------------------------
    c.row(47, "0:4 3:64 0:4")
    for y in range(48, 52):
        c.row(y, "(1:4 0:4)*9")
    for y in range(52, 56):
        c.row(y, "(0:4 1:4)*9")
    if not dmg:                                              # DMG: no table and no potted shrub
        c.paste(5, 44, TABLE)
    if not dmg:                                              # DMG: no potted shrub
        c.paste(57, 43, SHRUB)
    return c


if __name__ == "__main__":
    print(len(build().out()))
