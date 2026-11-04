#!/usr/bin/env python3
"""Fizzwater town master (2026-11-04 proposal): ONE set of hand-drawn pixels for the square's buildings, bunting and plaza.

Transcription only. Every building row below is my hand-drawn grid (material keys, not colours); the code places each
hand-drawn piece at the position I chose (a repeated piece = the same pixels, allowed: "copying your own finished work"),
lays the INTRO's approved cobble tile over the plaza rows, and the Pour-Off venue's approved bunting row (copied pixel for
pixel from assets/approved/venues/festival_stage.txt rows 0-6, x 0-15) along the top. Nothing is generated, mirrored,
outlined or shaded by code. The hand clean-up edits are listed in EDITS with the reason for each.

Material keys (each picture's key table gives the DMG shade and colour per time of day):
  .  sky            #  ink (outlines, doors' frames, crowd)     B  wall plaster      e  lit trim / rim (bargeboard, ledges, sills)
  R  roof tiles     r  roof course line                          L  window glass      d  door wood
  M  mug (shop window)  a  awning orange  A  awning cream                               c  clock face        P  pennant orange   Q  pennant cream
  p  cobble         q  mortar                                     h  cobble highlight
"""
W, H = 160, 104

# ---- the gable house (24 x 56, rows y 32-87): the Pour-Off venue's gabled house, nearer: 45-degree gable, the lit
# (left) slope trimmed, an oculus, the venue's 5x6 window with a sill, an arched door ----
GABLE = """\
...........##...........
..........#ee#..........
.........#eBBB#.........
........#eBBBBB#........
.......#eBBBBBBB#.......
......#eBBBBBBBBB#......
.....#eBBBB##BBBBB#.....
....#eBBBB#LL#BBBBB#....
...#eBBBBB#LL#BBBBBB#...
..#eBBBBBBB##BBBBBBBB#..
.#eBBBBBBBBBBBBBBBBBBB#.
#eBBBBBBBBBBBBBBBBBBBBB#
#BBBBBBBBBBBBBBBBBBBBBB#
#BBBBBBBBBBBBBBBBBBBBBB#
#BBBBBBBBBBBBBBBBBBBBBB#
#BBBBBBBBBBBBBBBBBBBBBB#
#BBBBBBBBBBBBBBBBBBBBBB#
#BBBBBBB########BBBBBBB#
#BBBBBB#LLL##LLL#BBBBBB#
#BBBBBB#LLL##LLL#BBBBBB#
#BBBBBB#LLL##LLL#BBBBBB#
#BBBBBB#LLL##LLL#BBBBBB#
#BBBBBBB########BBBBBBB#
#BBBBBBBBBBBBBBBBBBBBBB#
#BBBBBBBBBBBBBBBBBBBBBB#
#BBBBBBBBBBBBBBBBBBBBBB#
#BBBBBBBBBBBBBBBBBBBBBB#
#BBBBBBBBBBBBBBBBBBBBBB#
#BBBBBBBBBBBBBBBBBBBBBB#
#BBBBBBBBBBBBBBBBBBBBBB#
#BBBBBBBBBBBBBBBBBBBBBB#
#BBBBBBBBBBBBBBBBBBBBBB#
#BBBBBBBBBBBBBBBBBBBBBB#
#BBBBBBBBBBBBBBBBBBBBBB#
#BBBBBBBBBBBBBBBBBBBBBB#
#BBBBBBBBBBBBBBBBBBBBBB#
#BBBBBBBBBBBBBBBBBBBBBB#
#BBBBBBBBBBBBBBBBBBBBBB#
#BBBBBBBBBBBBBBBBBBBBBB#
#BBBBBBBBBBBBBBBBBBBBBB#
#BBBBBBBBBBBBBBBBBBBBBB#
#BBBBBBBBBBBBBBBBBBBBBB#
#BBBBBBBBBBBBBBBBBBBBBB#
#BBBBBBBBBBBBBBBBBBBBBB#
#BBBBBBBBBBBBBBBBBBBBBB#
#BBBBBBBBBBBBBBBBBBBBBB#
#BBBBBBBBBBBBBBBBBBBBBB#
#BBBBBBBBBBBBBBBBBBBBBB#
#BBBBBBBBBBBBBBBBBBBBBB#
#BBBBBBBBBBBBBBBBBBBBBB#
#BBBBBBBBBBBBBBBBBBBBBB#
#BBBBBBBBBBBBBBBBBBBBBB#
#BBBBBBBBBBBBBBBBBBBBBB#
#BBBBBBBBBBBBBBBBBBBBBB#
#BBBBBBBBBBBBBBBBBBBBBB#
#BBBBBBBBBBBBBBBBBBBBBB#"""

# ---- the clock tower (16 x 68, rows y 20-87): round 5, taller than the tavern by its own change (the owner: its height
# looked odd beside the tavern; the tavern roof stays round 3's). Its body is 11 rows taller, so the cornice (y 28) and the
# clock (y 32-40) stand above the tavern's ridge (y 32), and the spire is redrawn shorter and steeper (8 rows, tip y 20)
# so its tip clears the night moon (x 9-21, y 8-21). The clock face, windows and door are round 3's pixels ----
TOWER = """\
.......##.......
......#UU#......
.....#UUUU#.....
....#uuuuuu#....
...#eUUUUUUU#...
..#eUUUUUUUUU#..
.#eUUUUUUUUUUU#.
#euuuuuuuuuuuuu#
################
#eeeeeeeeeeeeee#
#BBBBBBBBBBBBBB#
#BBBBBBBBBBBBBB#
#BBBBBB###BBBBB#
#BBBBB#ccc#BBBB#
#BBBB#ccccc#BBB#
#BBB#ccc#ccc#BB#
#BBB#ccc##cc#BB#
#BBB#ccccccc#BB#
#BBBB#ccccc#BBB#
#BBBBB#ccc#BBBB#
#BBBBBB###BBBBB#
#BBBBBBBBBBBBBB#
#BBBBBBBBBBBBBB#
#BBBBBBBBBBBBBB#
#BBBBBBBBBBBBBB#
#BBBBBBBBBBBBBB#
#BBBBBBBBBBBBBB#
#BBBBBBBBBBBBBB#
#BBBBBBBBBBBBBB#
#BBBBBBBBBBBBBB#
#BBBBBBBBBBBBBB#
#BBBBBBBBBBBBBB#
#BBBBBBBBBBBBBB#
#BBBBBBBBBBBBBB#
#BBBBBBBBBBBBBB#
#BBBBBBBBBBBBBB#
#BBBBBBBBBBBBBB#
#BB###BBBB###BB#
#B#LLL#BB#LLL#B#
#B#LLL#BB#LLL#B#
#B#LLL#BB#LLL#B#
#B#LLL#BB#LLL#B#
#BB###BBBB###BB#
#BBBBBBBBBBBBBB#
#BBBBBBBBBBBBBB#
#BBBBBBBBBBBBBB#
#BBBBBBBBBBBBBB#
#BBBBBBBBBBBBBB#
#BBBBBBBBBBBBBB#
#BBBBBB##BBBBBB#
#BBBBB#dd#BBBBB#
#BBBB#dddd#BBBB#
#BBB#dddddd#BBB#
#BBB#dddddd#BBB#
#BBB#dddddd#BBB#
#BBB#dddddd#BBB#
#BBB#dddddd#BBB#
#BBB#dddddd#BBB#
#BBB#dddddd#BBB#
#BBB#dddddd#BBB#
#BBB#dddddd#BBB#
#BBB#dddddd#BBB#
#BBB#dddddd#BBB#
#BBB#dddddd#BBB#
#BBB#dddddd#BBB#
#BBB#dddddd#BBB#
#BBB#dddddd#BBB#
#BBB#dddddd#BBB#"""

# ---- the tavern (40 x 56, rows y 32-87, x 32-71): eave-front roof (ridge on a tile top, eave on a tile bottom, courses
# every 3 rows with staggered joints), a hip at the right end; four windows and the Pour-Off's cream banner between them; a
# striped awning in the bunting's two colours over a shop window; a door ----
TAVERN = """\
########################################
eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee#
RRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRR#
RRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRR#
RRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRR#
rrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrr#
RRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRR#
RRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRR#
RRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRR#
rrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrr#
RRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRR#
RRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRR#
RRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRR#
rrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrr#
RRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRR#
########################################
BBBBBBBBBBBBBBBB########BBBBBBBBBBBBBBB#
BBBBBB###BBBBBBB#QQQQQQ#BBBBBB###BBBBBB#
BBBBB#LLL#BBBBBB#QPPPPQ#BBBBB#LLL#BBBBB#
BBBBB#LLL#BBBBBB#QP##PQ#BBBBB#LLL#BBBBB#
BBBBB#LLL#BBBBBB#QP##PQ#BBBBB#LLL#BBBBB#
BBBBB#LLL#BBBBBB#QPPPPQ#BBBBB#LLL#BBBBB#
BBBBBB###BBBBBBB#QQQQQQ#BBBBBB###BBBBBB#
BBBBBBBBBBBBBBBB#QQQQQQ#BBBBBBBBBBBBBBB#
BBBBBBBBBBBBBBBB#QQQQQQ#BBBBBBBBBBBBBBB#
BBBBBBBBBBBBBBBB#QQQQQQ#BBBBBBBBBBBBBBB#
BBBBBBBBBBBBBBBB#QQQQQQ#BBBBBBBBBBBBBBB#
BBBBBBBBBBBBBBBB#QQ##QQ#BBBBBBBBBBBBBBB#
BBBBBBBBBBBBBBBB#Q#BB#Q#BBBBBBBBBBBBBBB#
BBBBBBBBBBBBBBBB##BBBB##BBBBBBBBBBBBBBB#
BBBBBBBBBBBBBBBBB#BBBB#BBBBBBBBBBBBBBBB#
BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB#
########################################
AAaaAAaaAAaaAAaaAAaaAAaaAAaaAAaaAAaaAAa#
AAaaAAaaAAaaAAaaAAaaAAaaAAaaAAaaAAaaAAa#
AAaaAAaaAAaaAAaaAAaaAAaaAAaaAAaaAAaaAAa#
AAaaAAaaAAaaAAaaAAaaAAaaAAaaAAaaAAaaAAa#
AAaaAAaaAAaaAAaaAAaaAAaaAAaaAAaaAAaaAAa#
AA##AA##AA##AA##AA##AA##AA##AA##AA##AA##
########################################
BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB#
BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB#
BBB#################################BBB#
BBB#LLLLLLL#LLLLLLL#LLLLLLL#LLLLLLL#BBB#
BBB#LLLLLLL#LLLLLLL#LLLLLLL#LLLLLLL#BBB#
BBB#LLLLLLL#LLLLLLL#LLLLLLL#LLLLLLL#BBB#
BBB#LLLLLLL#LLLLLLL#LLLLLLL#LLLLLLL#BBB#
BBB#LLLLLLL#LLLLLLL#LLLLLLL#LLLLLLL#BBB#
BBB#LLLLLLL#LLLLLLL#LLLLLLL#LLLLLLL#BBB#
BBB#LLLLLLL#LLLLLLL#LLLLLLL#LLLLLLL#BBB#
BBB#LLLLLLL#LLLLLLL#LLLLLLL#LLLLLLL#BBB#
BBB#################################BBB#
BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB#
BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB#
BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB#
BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB#"""

# ---- the market hall behind the fountain (56 x 32, rows y 56-87, x 72-127; round 2): one plain flat mass, its right end
# outlined, so the fountain stands in front of a quiet wall ----
HALL = "#" * 56 + ("\n" + "H" * 55 + "#") * 31

# ---- the Pour-Off venue's bunting, rows 0-6 x 0-15 of assets/approved/venues/festival_stage.txt (approved A6), keys
# mapped: '-' sky -> '.', '+' orange -> 'P', '.' cream -> 'Q', '#' -> '#' ----
FEST_BUNTING = """\
##------------##
-.##--------##.#
-.++##----##...#
--++++####....#-
--++++---#....#-
---++-----#..#--
-----------##---"""

# ---- the INTRO's approved cobble tile (intro_before rows 88-103, x 0-7), keys mapped: '#' -> mortar q, 'm' -> p, 'g' -> h;
# the first row is the plaza's ink edge ----
COBBLE = ['########', 'hhhpppp#', 'ppppppp#', 'ppppppp#', 'ppppppp#', 'ppppppp#', '########', 'hhh#pppp',
          'ppp#pppp', 'ppp#pppp', 'ppp#pppp', 'ppp#pppp', '########', 'hhhpppp#', 'ppppppp#', 'ppppppp#']

# where each hand-drawn piece goes (x, y of its top-left); '.' in a piece is transparent
PLACE = [
    ("HALL", 72, 56),
    ("GABLE", -7, 32),          # round 3: -7 (was -8), so its right outline IS the tower's left outline (one line, x 16)
    ("GABLE", 136, 32),
    ("TOWER", 16, 20),
    ("TAVERN", 32, 32),
]
# ---- round 5: the right-hand house is the GABLE piece itself (the owner: the round 4 cream plaster and navy night wall
# matched nothing): the neighbours' wall (B) and windows (L) at every time of day, plain front, centred windows ----

# ---- round 4: patrons in the tavern's shop window, hand-drawn silhouettes (key i: ink at night against the lit glass; the
# wall's lilac by day; the dawn violet), in bays 1 and 4 (glass x 36-42 and 60-66, y 75-82 since round 5), clear of where Dregs stands
# in intro_a and credits_b (bays 2-3). Bay 1 raises a mug ----
PATRON_MUG = """\
.......
ii.....
ii.iii.
.i.iii.
.i..i..
.iiiiii
iiiiiii
iiiiiii"""
PATRON = """\
.......
.......
..iii..
..iii..
...i...
.iiiii.
iiiiiii
iiiiiii"""
PLACE += [("PATRON_MUG", 36, 75), ("PATRON", 60, 75)]

# ---- round 3, the sky: hand-drawn clouds. o = a day cloud (venue cream; the sky's colour at night and dawn), O = a dawn
# strip (rim gold; the sky's colour at night and by day). Each sits inside one tile row (y 16-23 or 8-15) and whole tiles
# where it can, clear of the bunting (y 0-6), the clock tower's spire and the Golden Spigot (x 92-116) ----
CLOUD_A = """\
.........ooo............
......oooooooo..........
....ooooooooooo.oooo....
..oooooooooooooooooooo..
.oooooooooooooooooooooo.
oooooooooooooooooooooooo"""
CLOUD_B = """\
.....ooo........
...ooooooo.ooo..
.oooooooooooooo.
oooooooooooooooo"""
CLOUD_C = """\
...ooo....
.ooooooo..
oooooooooo"""
STRIP_A = """\
......OOOOOOOOOOOOOOOOOO.......
..OOOOOOOOOOOOOOOOOOOOOOOOOO...."""
STRIP_B = """\
....OOOOOOOOOOOOOOOO....
OOOOOOOOOOOOOOOOOOOOOOO."""
PLACE += [("CLOUD_A", 40, 16), ("CLOUD_B", 128, 18), ("CLOUD_C", 3, 20), ("STRIP_A", 50, 14), ("STRIP_B", 124, 22)]

PIECES = {"GABLE": GABLE, "TOWER": TOWER, "TAVERN": TAVERN, "HALL": HALL,
          "PATRON_MUG": PATRON_MUG, "PATRON": PATRON,
          "CLOUD_A": CLOUD_A, "CLOUD_B": CLOUD_B, "CLOUD_C": CLOUD_C, "STRIP_A": STRIP_A, "STRIP_B": STRIP_B}

# ---- round 4: a light wall texture, two hand-drawn 8x8 brick-hint tiles (key X: by day sandstone on the lilac or cream
# plaster; at night and at dawn the wall's own colour, so it costs nothing there). Each is stamped whole into a cell of
# plain wall that I chose by hand, sparse and never two alike side by side, so the variants share tiles ----
TEX = {"A": ["........",
             ".XXX....",
             "........",
             "........",
             "........",
             ".....XX.",
             "........",
             "........"],
       "B": ["........",
             "........",
             "....XXX.",
             "........",
             "........",
             "........",
             "XX......",
             "........"]}
TEX_CELLS = {(0, 7): "A", (1, 8): "B", (0, 9): "B", (1, 10): "A",       # the left gable (x 0-15)
             (4, 7): "B", (7, 7): "A",                                  # the tavern's upper wall beside the windows
             (18, 7): "A"}                                              # the right house, above Dregs and Sal

# hand clean-up of the master (x, y): key, with the reason; see NOTES.md "Clean-up log"
EDITS = {}


def put(g, piece, x0, y0):
    for dy, row in enumerate(piece.split("\n")):
        for dx, c in enumerate(row):
            x, y = x0 + dx, y0 + dy
            if c != "." and 0 <= x < W and 0 <= y < H:
                g[y][x] = c


def master():
    g = [["."] * W for _ in range(H)]
    fb = [r.replace("-", ",").replace("+", "P").replace(".", "Q").replace(",", ".") for r in FEST_BUNTING.split("\n")]
    for y, r in enumerate(fb):
        for x in range(W):
            g[y][x] = r[x % 16]
    for name, x0, y0 in PLACE:
        put(g, PIECES[name], x0, y0)
    for y in range(88, 104):
        for x in range(W):
            c = COBBLE[y - 88][x % 8]
            g[y][x] = "#" if y == 88 else {"#": "q", "p": "p", "h": "h"}[c]
    for (tx, ty), v in TEX_CELLS.items():
        cell = {g[y][x] for y in range(ty * 8, ty * 8 + 8) for x in range(tx * 8, tx * 8 + 8)}
        assert cell == {"B"}, (tx, ty, cell)     # only whole cells of plain wall
        for dy, r in enumerate(TEX[v]):
            for dx, c in enumerate(r):
                if c == "X":
                    g[ty * 8 + dy][tx * 8 + dx] = "X"
    for (x, y), c in EDITS.items():
        g[y][x] = c
    return g


if __name__ == "__main__":
    for r in master():
        print("".join(r))
