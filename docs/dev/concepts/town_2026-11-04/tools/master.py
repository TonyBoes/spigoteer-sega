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
#BB###BBBBBBBBBBB###BBB#
#B#LLL#BBBBBBBBBB#LLL#B#
#B#LLL#BBBBBBBBBB#LLL#B#
#B#LLL#BBBBBBBBBB#LLL#B#
#B#LLL#BBBBBBBBBB#LLL#B#
#BB###BBBBBBBBBBB###BBB#
#BeeeeeBBBBBBBBBBeeeeeB#
#BBBBBBBBBBBBBBBBBBBBBB#
#BBBBBBBBBBBBBBBBBBBBBB#
#eeeeeeeeeeeeeeeeeeeeee#
#BBBBBBBBBBBBBBBBBBBBBB#
#BBBBBBBBBBBBBBBBBBBBBB#
#BBBBBBBBBBBBBBBBBBBBBB#
#BBBBBBBBBBBBBBBBBBBBBB#
#BBBBBBBBBBBBBBBBBBBBBB#
#BBBBBBBBBBBBBBBBBBBBBB#
#BBBBBBBBBBBBBBBBBBBBBB#
#BBBB####BBBBBBBBBBBBBB#
#BBB#dddd#BBBBBBBBBBBBB#
#BB#dddddd#BBBBBBBBBBBB#
#BB#dddddd#BBBBBBBBBBBB#
#BB#dddddd#BBBBBBBBBBBB#
#BB#dddddd#BBBBBB###BBB#
#BB#dddddd#BBBBB#LLL#BB#
#BB#dddddd#BBBBB#LLL#BB#
#BB#dddddd#BBBBB#LLL#BB#
#BB#dddddd#BBBBB#LLL#BB#
#BB#dddded#BBBBBB###BBB#
#BB#dddddd#BBBBBeeeeeBB#
#BB#dddddd#BBBBBBBBBBBB#
#BB#dddddd#BBBBBBBBBBBB#
#BB#dddddd#BBBBBBBBBBBB#
#BB#dddddd#BBBBBBBBBBBB#
#BB#dddddd#BBBBBBBBBBBB#
#BB#dddddd#BBBBBBBBBBBB#
#BB#dddddd#BBBBBBBBBBBB#
#BB#dddddd#BBBBBBBBBBBB#
#BB#dddddd#BBBBBBBBBBBB#
#BB#dddddd#BBBBBBBBBBBB#"""

# ---- the clock tower (16 x 63, rows y 25-87): spire with courses, the INTRO's clock face (its pixels, key c), two
# windows on the kit's 5x6 window, ledges, an arched door ----
TOWER = """\
.......##.......
......#eU#......
......#eU#......
.....#eUUU#.....
.....#euuu#.....
....#eUUUUU#....
....#eUUUUU#....
...#euuuuuu#....
...#eUUUUUUU#...
..#eUUUUUUUUU#..
..#euuuuuuuuu#..
.#eUUUUUUUUUUU#.
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
#eeeeeeeeeeeeee#
#BBBBBBBBBBBBBB#
#BBBBBBBBBBBBBB#
#BB###BBBB###BB#
#B#LLL#BB#LLL#B#
#B#LLL#BB#LLL#B#
#B#LLL#BB#LLL#B#
#B#LLL#BB#LLL#B#
#BB###BBBB###BB#
#BeeeeeBBeeeeeB#
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
rrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrr#
RrRRRrRRRrRRRrRRRrRRRrRRRrRRRrRRRrRRRrR#
RRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRR#
rrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrr#
RRRrRRRrRRRrRRRrRRRrRRRrRRRrRRRrRRRrRRR#
RRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRR#
rrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrr#
RrRRRrRRRrRRRrRRRrRRRrRRRrRRRrRRRrRRRrR#
RRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRR#
rrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrr#
RRRrRRRrRRRrRRRrRRRrRRRrRRRrRRRrRRRrRRR#
RRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRR#
########################################
BBBBBBBBBBBBBBBB########BBBBBBBBBBBBBBB#
BBB###BBBBB###BB#QQQQQQ#BBB###BBBBB###B#
BB#LLL#BBB#LLL#B#QPPPPQ#BB#LLL#BBB#LLL##
BB#LLL#BBB#LLL#B#QP##PQ#BB#LLL#BBB#LLL##
BB#LLL#BBB#LLL#B#QP##PQ#BB#LLL#BBB#LLL##
BB#LLL#BBB#LLL#B#QPPPPQ#BB#LLL#BBB#LLL##
BBB###BBBBB###BB#QQQQQQ#BBB###BBBBB###B#
BBeeeeeBBBeeeeeB#QQQQQQ#BBeeeeeBBBeeeee#
BBBBBBBBBBBBBBBB#QQQQQQ#BBBBBBBBBBBBBBB#
BBBBBBBBBBBBBBBB#QQQQQQ#BBBBBBBBBBBBBBB#
eeeeeeeeeeeeeeee#QQQQQQ#eeeeeeeeeeeeeee#
BBBBBBBBBBBBBBBB#QQ##QQ#BBBBBBBBBBBBBBB#
BBBBBBBBBBBBBBBB#Q#BB#Q#BBBBBBBBBBBBBBB#
BBBBBBBBBBBBBBBB##BBBB##BBBBBBBBBBBBBBB#
BBBBBBBBBBBBBBBBB#BBBB#BBBBBBBBBBBBBBBB#
BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB#
################################BBBBBBB#
AAaaAAaaAAaaAAaaAAaaAAaaAAaaAAaaBBBBBBB#
AAaaAAaaAAaaAAaaAAaaAAaaAAaaAAaaBBBBBBB#
AAaaAAaaAAaaAAaaAAaaAAaaAAaaAAaaBB###BB#
AAaaAAaaAAaaAAaaAAaaAAaaAAaaAAaaB#ddd#B#
AAaaAAaaAAaaAAaaAAaaAAaaAAaaAAaa#ddddd##
AA##AA##AA##AA##AA##AA##AA##AA###ddddd##
#################################ddddd##
#LLLLLLL#LLLLLLL#LLLLLLL#LLLLLLL#ddddd##
#LLLLLLL#LLLLLLL#LLLLLLL#LLLLLLL#ddddd##
#LLLLLLL#LLLLLLL#LLLLLLL#LLLLLLL#ddddd##
#LLLLLLL#LLLLLLL#LLLLLLL#LLLLLLL#ddddd##
#LMMMLLL#LLLMMML#LMMMLLL#LLLMMML#ddddd##
#LMMM#LL#LL#MMML#LMMM#LL#LL#MMML#dddde##
#LMMM#LL#LL#MMML#LMMM#LL#LL#MMML#ddddd##
#LMMMLLL#LLLMMML#LMMMLLL#LLLMMML#ddddd##
#################################ddddd##
eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee#ddddd##
BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB#ddddd##
BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB#ddddd##
BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB#ddddd##
BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB#ddddd##
BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB#ddddd##
BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB#ddddd##"""

# ---- the market hall behind the fountain (64 x 32, rows y 56-87, x 72-135): flat-topped (its roof is out of sight), a frieze of
# small ink lozenges every 8 px, a string course, then the kit's windows (its basin hides the rest) ----
HALL = """\
################################################################
BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB
BBB#BBBBBBB#BBBBBBB#BBBBBBB#BBBBBBB#BBBBBBB#BBBBBBB#BBBBBBB#BBBB
BB#B#BBBBB#B#BBBBB#B#BBBBB#B#BBBBB#B#BBBBB#B#BBBBB#B#BBBBB#B#BBB
BBB#BBBBBBB#BBBBBBB#BBBBBBB#BBBBBBB#BBBBBBB#BBBBBBB#BBBBBBB#BBBB
BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB
################################################################
BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB
BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB
BBB###BBBBBBBBBBBBB###BBBBBBBBBBBBB###BBBBBBBBBBBBB###BBBBBBBBBB
BB#LLL#BBBBBBBBBBB#LLL#BBBBBBBBBBB#LLL#BBBBBBBBBBB#LLL#BBBBBBBBB
BB#LLL#BBBBBBBBBBB#LLL#BBBBBBBBBBB#LLL#BBBBBBBBBBB#LLL#BBBBBBBBB
BB#LLL#BBBBBBBBBBB#LLL#BBBBBBBBBBB#LLL#BBBBBBBBBBB#LLL#BBBBBBBBB
BB#LLL#BBBBBBBBBBB#LLL#BBBBBBBBBBB#LLL#BBBBBBBBBBB#LLL#BBBBBBBBB
BBB###BBBBBBBBBBBBB###BBBBBBBBBBBBB###BBBBBBBBBBBBB###BBBBBBBBBB
BBeeeeeBBBBBBBBBBBeeeeeBBBBBBBBBBBeeeeeBBBBBBBBBBBeeeeeBBBBBBBBB""" + ("\n" + "B" * 64) * 16

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
    ("GABLE", -8, 32),          # the same house at both ends of the square: its right two thirds show at the left edge
    ("GABLE", 136, 32),
    ("TOWER", 16, 25),
    ("TAVERN", 32, 32),
]
# ---- the right-hand house's open shop front (24 x 24 at x 136, y 64): its door and ground window give way to one wide
# arched opening, dark inside, so the figures that stand in front of it (Sal at night, Dregs by day) stand out on DMG ----
SHOPFRONT = """\
........................
.....##############.....
....################....""" + ("\n...##################...") * 21
PLACE.append(("SHOPFRONT", 136, 64))

PIECES = {"GABLE": GABLE, "TOWER": TOWER, "TAVERN": TAVERN, "HALL": HALL, "SHOPFRONT": SHOPFRONT}

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
    for (x, y), c in EDITS.items():
        g[y][x] = c
    return g


if __name__ == "__main__":
    for r in master():
        print("".join(r))
