"""The Stadium, 80 x 56. Palette STADIUM: 0 white concrete, 1 red, 2 navy, 3 ink.  Light from the top left.
Navy grandstand wall, red and white striped canopy with a scalloped edge, scoreboard with red numerals, two flag poles,
three gates, two banners, a striped barrier and a pop machine at the front right."""
from canvas import Canvas, piece

W, H = 80, 56
PAL = "stadium"

DIG = {"2": ["111", "001", "111", "100", "111"], "4": ["101", "101", "111", "001", "001"],
       "1": ["010", "110", "010", "010", "111"], "7": ["111", "001", "010", "010", "010"]}
LET = {"P": ["111", "101", "111", "100", "100"], "O": ["111", "101", "101", "101", "111"]}

FLAG = piece("1:6 .:1", "1:7", "1:6 .:1", "1:4 .:3")
GATE = piece(".:2 3:6 .:2", ".:1 3:1 0:6 3:1 .:1", "3:1 0:1 3:6 0:1 3:1",
             "3:1 0:1 3:6 0:1 3:1", "3:1 0:1 3:2 0:2 3:2 0:1 3:1", "3:1 0:1 3:2 0:2 3:2 0:1 3:1",
             ("3:1 0:1 3:6 0:1 3:1", 7), "3:10")
GATE_C = piece(".:2 3:8 .:2", ".:1 3:1 0:8 3:1 .:1", "3:1 0:1 3:8 0:1 3:1",
               "3:1 0:1 3:8 0:1 3:1", "3:1 0:1 3:2 0:4 3:2 0:1 3:1", "3:1 0:1 3:2 0:4 3:2 0:1 3:1", "3:1 0:1 3:2 0:4 3:2 0:1 3:1",
               ("3:1 0:1 3:8 0:1 3:1", 8), "3:12")
BANNER = piece("3:6", ("3:1 1:4 3:1", 3), "3:1 1:1 0:2 1:1 3:1", "3:1 1:1 0:2 1:1 3:1", ("3:1 1:4 3:1", 5), "3:1 1:1 .:2 1:1 3:1", "3:2 .:2 3:2")


def popmachine():
    rows = ["." * 1 + "3" * 11 + "." * 1, "3" + "1" * 11 + "3", "3" + "0" * 11 + "3"]
    for j in range(5):
        r = "".join("3" if LET["P"][j][i] == "1" else "0" for i in range(3)) + "0" + \
            "".join("3" if LET["O"][j][i] == "1" else "0" for i in range(3)) + "0" + \
            "".join("3" if LET["P"][j][i] == "1" else "0" for i in range(3))
        rows.append("3" + r + "3")
    rows += ["3" + "0" * 11 + "3", "3" * 13, "3" + "1" * 11 + "3", "3" + "1" * 2 + "0" + "1" * 2 + "0" + "1" * 2 + "0" + "1" * 2 + "3",
             "3" + "1" * 11 + "3", "3" + "1" * 3 + "3" * 5 + "1" * 3 + "3", "3" + "1" * 11 + "3", "3" + "1" * 11 + "3",
             "3" + "2" * 11 + "3", "3" * 13]
    return rows


def build():
    c = Canvas("stadium", PAL, W, H)
    # ---- flag poles ------------------------------------------------------------------------------------------------------
    # ---- the scoreboard: ink panel in a navy rim, red numerals double size --------------------------------------------------
    c.row(2, "0:22 3:36 0:22")
    for y in range(3, 15):
        c.row(y, "0:22 3:1 2:1 3:32 2:1 3:1 0:22")
    c.row(15, "0:22 3:36 0:22")
    for k, d in enumerate("2417"):
        for j, r in enumerate(DIG[d]):
            for i, ch in enumerate(r):
                if ch == "1":
                    for dx in (0, 1):
                        for dy in (0, 1):
                            c.put(25 + k * 8 + i * 2 + dx, 4 + j * 2 + dy, "1")
    for x in (25, 33, 41, 49):
        c.put(x, 3, "0")
    # ---- canopy -----------------------------------------------------------------------------------------------------------
    c.row(16, "0:4 3:72 0:4")
    for y in range(17, 22):
        c.row(y, "0:4 3:1 (1:5 0:5)*7 3:1 0:4")
    c.row(22, "0:4 3:1 (1:1 3:3 1:1 0:1 3:3 0:1)*7 3:1 0:4")
    # ---- the grandstand wall ----------------------------------------------------------------------------------------------
    c.row(23, "0:6 3:1 2:66 3:1 0:6")
    c.row(24, "0:6 3:1 2:66 3:1 0:6")
    c.row(25, "0:6 3:1 2:2 (0:1 2:7)*8 3:1 0:6")
    for y in range(26, 45):
        c.row(y, "0:6 3:1 2:66 3:1 0:6")
    c.row(45, "0:6 3:68 0:6")
    c.paste(12, 31, GATE)
    c.paste(58, 31, GATE)
    c.paste(34, 29, GATE_C)
    c.paste(25, 28, BANNER)
    c.paste(49, 28, BANNER)
    # ---- the striped barrier, as the in-game counters --------------------------------------------------------------------
    c.row(48, "0:6 3:68 0:6")
    for y in range(49, 53):
        c.row(y, "0:6 3:1 (1:4 0:4)*8 1:2 3:1 0:6")
    c.row(53, "0:6 3:68 0:6")
    for x in (8, 70):
        for y in range(1, 16):
            c.put(x, y, "3")
    c.paste(9, 1, FLAG)
    c.paste(71, 1, FLAG)
    c.paste(66, 35, popmachine())
    return c


if __name__ == "__main__":
    print(len(build()))
