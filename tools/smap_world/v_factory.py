"""The Robot Factory, 80 x 56. Palette FACTORY: 0 pale yard, 1 steel, 2 dark steel, 3 ink; FACTORY_B (the sign and the battery cabinet, four
whole cells each): 0 pale, 1 orange, 2 dark steel, 3 ink.
A sawtooth-roof hall with corrugated walls, two smokestacks, a robot head on a mast, the orange ROBOCO sign, a roller door, portholes,
a battery cabinet with a bolt, a pipe along the wall and a conveyor at the front."""
from canvas import Canvas, piece

W, H = 80, 56
PAL = "factory"

LET = {"R": ["110", "101", "110", "101", "101"], "O": ["111", "101", "101", "101", "111"], "B": ["110", "101", "110", "101", "110"],
       "C": ["111", "100", "100", "100", "111"]}
ROBOT = piece(".:5 3:2 .:5", ".:1 3:10 .:1", "3:1 1:10 3:1", "3:1 1:2 0:2 1:2 0:2 1:2 3:1", "3:1 1:2 0:2 1:2 0:2 1:2 3:1", "3:1 1:3 2:4 1:3 3:1",
              ".:1 3:10 .:1")
STACK = piece("3:10", "3:1 2:8 3:1", ("3:1 1:5 2:3 3:1", 4), "3:1 2:8 3:1", ("3:1 1:5 2:3 3:1", 5), "3:1 2:8 3:1", ("3:1 1:5 2:3 3:1", 5), "3:1 2:8 3:1",
              ("3:1 1:5 2:3 3:1", 1))
SMOKE = piece(".:2 1:4 .:2", "1:8", ".:2 1:4 .:2")
PORT = piece(".:2 3:4 .:2", ".:1 3:1 0:4 3:1 .:1", "3:1 0:2 1:4 3:1", "3:1 0:1 1:5 3:1", "3:1 1:6 3:1", ".:1 3:1 1:4 3:1 .:1", ".:2 3:4 .:2")
BOLT = ["2221111", "2211122", "2111112", "2221122", "2211222", "2122222"]
BATT = (["3" * 16, "3" + "2" * 14 + "3"] + ["3" + "2" * 14 + "3"] * 2
        + ["3" + "2" * 4 + r + "2" * 3 + "3" for r in BOLT]
        + ["3" + "2" * 14 + "3"] * 3 + ["3" + "2" * 14 + "3", "3" * 16])
# the saw teeth, row by row: how many transparent pixels before the slope's ink pixel (a 18 wide tooth; the vertical face is on the right)
TOOTH_A = [15, 13, 11, 10, 8, 6, 5, 3, 1, 0]


TOOTH_A16 = [13, 11, 10, 8, 7, 5, 4, 2, 0, 0]            # DMG: the same tooth 16 wide, so the four teeth are the same tiles


def tooth_rows(dmg=False):
    rows = []
    if dmg:
        for j, a in enumerate(TOOTH_A16):
            rows.append(f".:{a} 3:3" if j == 0 else f".:{a} 3:1 2:{12 - a} 0:2 3:1")
        return piece(*rows)
    for j, a in enumerate(TOOTH_A):
        rows.append(f".:{a} 3:3" if j == 0 else f".:{a} 3:1 2:{14 - a} 0:2 3:1")
    return piece(*rows)


def build(dmg=False):
    c = Canvas("factory", PAL, W, H)
    c.palrect(24, 32, 56, 40, "factory_b")
    c.palrect(56, 32, 72, 48, "factory_b")
    # ---- smoke and stacks -------------------------------------------------------------------------------------------------
    if dmg:                                                  # DMG: both stacks and both wisps on the same phase of the 8 px grid
        c.paste(8, 0, SMOKE)
        c.paste(64, 0, SMOKE)
        c.paste(8, 6, STACK)
        c.paste(64, 6, STACK)
    else:
        c.paste(5, 0, SMOKE)
        c.paste(65, 1, SMOKE)
        c.paste(6, 6, STACK)
        c.paste(64, 6, STACK)
    # ---- the mast and the robot head --------------------------------------------------------------------------------------
    for y in range(10, 16):
        c.put(39, y, "3")
        c.put(40, y, "3")
    c.paste(34, 2, ROBOT)
    # ---- the sawtooth roof (four teeth) ----------------------------------------------------------------------------------------
    t = tooth_rows(dmg)
    for k in range(4):
        c.paste(8 + k * 16 if dmg else 4 + k * 18, 16, t)

    # ---- the hall: corrugated steel, a ridge of dark every fourth row ------------------------------------------------------------
    for y in range(26, 50):
        c.row(y, "0:4 3:1 %s:70 3:1 0:4" % ("2" if (y - 26) % 4 == 3 else "1"))
    c.row(50, "0:4 3:72 0:4")
    # pipe along the wall: ink, steel, dark underside, flanges
    c.row(28, "0:4 3:72 0:4")
    c.row(29, "0:4 3:1 0:70 3:1 0:4")
    c.row(30, "0:4 3:1 1:70 3:1 0:4")
    c.row(31, "0:4 3:72 0:4")
    for x in ((14, 38, 62) if dmg else (14, 36, 58)):
        for y in (28, 29, 30, 31):
            c.put(x, y, "3")
            c.put(x + 1, y, "2")
    # ---- the sign (whole cells, factory_b) and the battery cabinet --------------------------------------------------------------
    for y in range(32, 40):
        for x in range(24, 56):
            c.put(x, y, "3" if y in (32, 39) or x in (24, 55) else "1")
    for k, ch in enumerate("ROBOCO"):
        for j, r in enumerate(LET[ch]):
            for i, v in enumerate(r):
                if v == "1":
                    c.put(28 + k * 4 + i, 34 + j, "3")
    c.paste(56, 32, piece(*["=" + r for r in BATT]))
    # ---- the roller door ---------------------------------------------------------------------------------------------------------
    c.row(41, "0:28 3:24 0:28")
    for y in range(42, 50):
        c.row(y, "0:28 3:1 %s:22 3:1 0:28" % ("2" if y % 2 == 0 else "1"))
    c.row(50, "0:4 3:72 0:4")
    # ---- portholes on the left wall ----------------------------------------------------------------------------------------------------
    c.paste(8, 34, PORT)
    c.paste(8, 42, PORT)
    # ---- the conveyor: a belt with rollers, two crates on it ---------------------------------------------------------------------------
    c.row(51, "0:2 3:76 0:2")
    c.row(52, "0:2 3:1 (2:3 1:1)*18 2:2 3:1 0:2")
    c.row(53, "0:2 3:76 0:2")
    return c


if __name__ == "__main__":
    print(len(build().out()))
