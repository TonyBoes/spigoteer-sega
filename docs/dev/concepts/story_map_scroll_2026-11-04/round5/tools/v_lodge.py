"""The Lumber Lodge, 80 x 64. Palettes: LODGE (cabin, logs, stump) and FOREST (the two pine columns); both have the same ground.
LODGE: 0 forest floor, 1 lit log, 2 shaded log / board, 3 ink.  FOREST: 0 floor, 1 lit needles, 2 shaded needles, 3 ink.
A front-gable log cabin with a plank sign, antlers, a chimney with a wisp of smoke, a porch, two pine columns, a log pile and a stump."""
from canvas import Canvas, piece

W, H = 80, 64
PAL = "lodge"

PINE = piece(".:7 3:2 .:7", ".:6 3:1 1:1 2:1 3:1 .:6", ".:5 3:1 1:2 2:2 3:1 .:5", ".:4 3:1 1:3 2:3 3:1 .:4", ".:3 3:10 .:3",
             ".:5 3:1 1:2 2:2 3:1 .:5", ".:4 3:1 1:3 2:3 3:1 .:4", ".:3 3:1 1:4 2:4 3:1 .:3", ".:2 3:1 1:5 2:5 3:1 .:2", ".:2 3:12 .:2",
             ".:4 3:1 1:3 2:3 3:1 .:4", ".:3 3:1 1:4 2:4 3:1 .:3", ".:2 3:1 1:5 2:5 3:1 .:2", ".:1 3:1 1:6 2:6 3:1 .:1", ".:1 3:14 .:1",
             ".:7 3:2 .:7", ".:7 3:2 .:7", ".:6 3:4 .:6")
LOGEND = piece(".:1 3:4 .:1", "3:1 1:4 3:1", "3:1 1:1 2:2 1:1 3:1", "3:1 1:1 2:2 1:1 3:1", "3:1 1:4 3:1", ".:1 3:4 .:1")
STUMP = piece(".:2 3:8 .:2", ".:1 3:1 1:8 3:1 .:1", "3:1 1:3 2:4 1:3 3:1", ".:1 3:1 1:8 3:1 .:1", ".:2 3:1 1:3 2:4 3:1 .:1",
              ".:2 3:1 1:3 2:4 3:1 .:1", ".:2 3:1 1:3 2:4 3:1 .:1", ".:2 3:8 .:2")
DOOR = piece("3:12", "3:1 2:10 3:1", ("3:1 2:4 3:1 2:5 3:1", 6), "3:1 2:4 3:1 2:3 1:1 2:1 3:1", ("3:1 2:4 3:1 2:5 3:1", 5), "3:12")
WIN = piece("3:9", ("3:1 0:3 3:1 0:3 3:1", 3), "3:9", ("3:1 0:3 3:1 0:3 3:1", 3), "3:9", "2:11")
ANT = piece("3:1 .:2 3:1 .:7 3:1 .:2 3:1", "3:1 .:2 3:1 .:7 3:1 .:2 3:1", ".:1 3:1 .:1 3:1 .:7 3:1 .:1 3:1 .:1",
            ".:1 3:4 .:5 3:4 .:1", ".:2 3:4 .:3 3:4 .:2", ".:4 3:7 .:4", ".:6 3:3 .:6")
SMOKE = piece(".:1 1:4 .:1", "1:6", ".:1 1:4 .:1")
CHIM = piece("3:8", "3:1 1:6 3:1", ("3:1 1:2 2:4 3:1", 5), "3:1 1:2 2:4 3:1", "3:1 1:2 2:4 3:1", "3:1 1:2 2:4 3:1", "3:1 1:2 2:4 3:1", "3:1 1:2 2:4 3:1")
# the plank sign "LODGE": 3 x 5 letters, light on a shaded board
LET = {"L": ["100", "100", "100", "100", "111"], "O": ["111", "101", "101", "101", "111"], "D": ["110", "101", "101", "101", "110"],
       "G": ["111", "100", "101", "101", "111"], "E": ["111", "100", "110", "100", "111"]}

# the front gable, row by row: (floor pad each side, interior width, interior colour); the two band pixels either side are shaded wood
GABLE = [(37, 0, "-"), (36, 2, "1"), (35, 4, "2"), (34, 6, "1"), (33, 8, "1"), (32, 10, "2"), (31, 12, "1"), (30, 14, "1"), (29, 16, "2"),
         (28, 18, "1"), (27, 20, "1"), (26, 22, "2"), (25, 24, "1"), (24, 26, "1"), (23, 28, "2"), (22, 30, "1"), (21, 32, "1"),
         (20, 34, "2"), (19, 36, "1"), (18, 38, "1")]


def build(dmg=False):
    c = Canvas("lodge", PAL, W, H)
    c.palrect(0, 0, 16, 48, "forest")
    c.palrect(64, 0, 80, 48, "forest")
    # ---- the gable roof --------------------------------------------------------------------------------------------------
    for k, (pad, inner, fill) in enumerate(GABLE):
        y = 4 + k
        if inner == 0:
            c.row(y, f"0:{pad} 3:1 2:4 3:1 0:{pad}")
        else:
            c.row(y, f"0:{pad} 3:1 2:2 {fill}:{inner} 2:2 3:1 0:{pad}")
    c.row(24, "0:16 3:48 0:16")
    # ---- the log walls: three lit courses, one shaded -------------------------------------------------------------------
    for y in range(25, 50):
        c.row(y, "0:16 3:1 %s:46 3:1 0:16" % ("2" if (y - 25) % 4 == 3 else "1"))
    # porch boards
    c.row(50, "0:16 3:48 0:16")
    for y in (51, 52, 53):
        c.row(y, "0:16 3:1 2:46 3:1 0:16")
    c.row(54, "0:16 3:48 0:16")
    # ---- things on the front -------------------------------------------------------------------------------------------
    c.paste(32, 13, ANT)
    # the sign
    for y in range(27, 36):
        for x in range(29, 51):
            c.put(x, y, "3" if y in (27, 35) or x in (29, 50) else "2")
    for k, ch in enumerate("LODGE"):
        for j, r in enumerate(LET[ch]):
            for i, v in enumerate(r):
                if v == "1":
                    c.put(31 + k * 4 + i, 29 + j, "1")
    c.paste(34, 36, DOOR)
    c.paste(21, 37, WIN)
    c.paste(50, 37, WIN)
    # the chimney behind the roof edge, a wisp of smoke
    for j, r in enumerate(CHIM):
        for i, ch in enumerate(r):
            if ch != "." and c.px[7 + j][51 + i] == "0":
                c.put(51 + i, 7 + j, ch)
    c.paste(53, 3, SMOKE)
    # ---- the pines: two on each side ------------------------------------------------------------------------------------
    if dmg:                                                  # DMG: the four pines on the same phase of the 8 px grid, so they are the same tiles
        c.paste(0, 0, PINE)
        c.paste(0, 24, PINE)
        c.paste(64, 8, PINE)
        c.paste(64, 32, PINE)
    else:
        c.paste(0, 3, PINE)
        c.paste(0, 26, PINE)
        c.paste(64, 8, PINE)
        c.paste(64, 29, PINE)
    # ---- the log pile (front right) and the stump (front left) ------------------------------------------------------------
    for x in ((56, 64, 72) if dmg else (62, 68, 74)):       # DMG: the pile's logs 8 px apart
        c.paste(x, 58, LOGEND)
    for x in ((60, 68) if dmg else (65, 71)):
        c.paste(x, 53, LOGEND)
    c.paste(64 if dmg else 68, 48, LOGEND)
    c.paste(2, 54, STUMP)
    return c


if __name__ == "__main__":
    print(len(build().out()))
