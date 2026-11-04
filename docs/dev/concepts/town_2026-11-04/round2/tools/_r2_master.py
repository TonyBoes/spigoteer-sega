"""Round 2 (2026-11-04): hand edits to the master's pieces, written out row by row (calmer facades). One-off patch."""
from pathlib import Path

p = Path(__file__).resolve().parent / "master.py"
s = p.read_text()


def rep(old, new):
    global s
    assert s.count(old) == 1, old[:60]
    s = s.replace(old, new)


# ---- GABLE: no ledge, no sills, no ground window (two upper windows and the oculus stay) ----
rep('''#B#LLL#BBBBBBBBBB#LLL#B#
#BB###BBBBBBBBBBB###BBB#
#BeeeeeBBBBBBBBBBeeeeeB#
#BBBBBBBBBBBBBBBBBBBBBB#
#BBBBBBBBBBBBBBBBBBBBBB#
#eeeeeeeeeeeeeeeeeeeeee#
''', '''#B#LLL#BBBBBBBBBB#LLL#B#
#BB###BBBBBBBBBBB###BBB#
#BBBBBBBBBBBBBBBBBBBBBB#
#BBBBBBBBBBBBBBBBBBBBBB#
#BBBBBBBBBBBBBBBBBBBBBB#
#BBBBBBBBBBBBBBBBBBBBBB#
''')
rep('''#BB#dddddd#BBBBBB###BBB#
#BB#dddddd#BBBBB#LLL#BB#
#BB#dddddd#BBBBB#LLL#BB#
#BB#dddddd#BBBBB#LLL#BB#
#BB#dddddd#BBBBB#LLL#BB#
#BB#dddded#BBBBBB###BBB#
#BB#dddddd#BBBBBeeeeeBB#
''', '''#BB#dddddd#BBBBBBBBBBBB#
#BB#dddddd#BBBBBBBBBBBB#
#BB#dddddd#BBBBBBBBBBBB#
#BB#dddddd#BBBBBBBBBBBB#
#BB#dddddd#BBBBBBBBBBBB#
#BB#dddddd#BBBBBBBBBBBB#
#BB#dddddd#BBBBBBBBBBBB#
''')

# ---- TOWER: two spire courses instead of four, no mid ledge, no sills ----
rep('''...#euuuuuu#....
...#eUUUUUUU#...
..#eUUUUUUUUU#..
..#euuuuuuuuu#..
''', '''...#eUUUUUU#....
...#eUUUUUUU#...
..#eUUUUUUUUU#..
..#euuuuuuuuu#..
''')
rep('''#BBBBBBBBBBBBBB#
#eeeeeeeeeeeeee#
#BBBBBBBBBBBBBB#
#BBBBBBBBBBBBBB#
#BB###BBBB###BB#''', '''#BBBBBBBBBBBBBB#
#BBBBBBBBBBBBBB#
#BBBBBBBBBBBBBB#
#BBBBBBBBBBBBBB#
#BB###BBBB###BB#''')
rep('''#BB###BBBB###BB#
#BeeeeeBBeeeeeB#
''', '''#BB###BBBB###BB#
#BBBBBBBBBBBBBB#
''')

# ---- TAVERN: plain roof with three courses (no staggered joints); two upper windows beside the banner (the outer two
# gone), no sills, no ledge; the shop window's mugs gone (plain lit panes) ----
rep('''RRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRR#
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
''', '''RRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRR#
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
''')
rep('''BBB###BBBBB###BB#QQQQQQ#BBB###BBBBB###B#
BB#LLL#BBB#LLL#B#QPPPPQ#BB#LLL#BBB#LLL##
BB#LLL#BBB#LLL#B#QP##PQ#BB#LLL#BBB#LLL##
BB#LLL#BBB#LLL#B#QP##PQ#BB#LLL#BBB#LLL##
BB#LLL#BBB#LLL#B#QPPPPQ#BB#LLL#BBB#LLL##
BBB###BBBBB###BB#QQQQQQ#BBB###BBBBB###B#
BBeeeeeBBBeeeeeB#QQQQQQ#BBeeeeeBBBeeeee#
BBBBBBBBBBBBBBBB#QQQQQQ#BBBBBBBBBBBBBBB#
BBBBBBBBBBBBBBBB#QQQQQQ#BBBBBBBBBBBBBBB#
eeeeeeeeeeeeeeee#QQQQQQ#eeeeeeeeeeeeeee#
''', '''BBBBBBBBBB###BBB#QQQQQQ#BBB###BBBBBBBBB#
BBBBBBBBB#LLL#BB#QPPPPQ#BB#LLL#BBBBBBBB#
BBBBBBBBB#LLL#BB#QP##PQ#BB#LLL#BBBBBBBB#
BBBBBBBBB#LLL#BB#QP##PQ#BB#LLL#BBBBBBBB#
BBBBBBBBB#LLL#BB#QPPPPQ#BB#LLL#BBBBBBBB#
BBBBBBBBBB###BBB#QQQQQQ#BBB###BBBBBBBBB#
BBBBBBBBBBBBBBBB#QQQQQQ#BBBBBBBBBBBBBBB#
BBBBBBBBBBBBBBBB#QQQQQQ#BBBBBBBBBBBBBBB#
BBBBBBBBBBBBBBBB#QQQQQQ#BBBBBBBBBBBBBBB#
BBBBBBBBBBBBBBBB#QQQQQQ#BBBBBBBBBBBBBBB#
''')
for row in ("#LMMMLLL#LLLMMML#LMMMLLL#LLLMMML#ddddd##", "#LMMM#LL#LL#MMML#LMMM#LL#LL#MMML#dddde##",
            "#LMMM#LL#LL#MMML#LMMM#LL#LL#MMML#ddddd##", "#LMMMLLL#LLLMMML#LMMMLLL#LLLMMML#ddddd##"):
    s = s.replace(row, "#LLLLLLL#LLLLLLL#LLLLLLL#LLLLLLL#ddddd##")
assert "M" not in s.split("TAVERN = ")[1].split('"""')[1]

# ---- HALL: a plain flat mass, 56 wide (x 72-127): no frieze, no string course, no windows; an alley of sky at x 128-135 ----
a = s.index('HALL = """')
b = s.index('("\\n" + "B" * 64) * 16') + len('("\\n" + "B" * 64) * 16')
s = s[:a] + 'HALL = "#" * 56 + ("\\n" + "B" * 55 + "#") * 31' + s[b:]
s = s.replace("# ---- the market hall behind the fountain (64 x 32, rows y 56-87, x 72-135): flat-topped (its roof is out of sight), a frieze of\n# small ink lozenges every 8 px, a string course, then the kit's windows (its basin hides the rest) ----",
              "# ---- the market hall behind the fountain (56 x 32, rows y 56-87, x 72-127; round 2): one plain flat mass, its right end\n# outlined, so the fountain stands in front of a quiet wall ----")

# ---- SHOPFRONT: one dark opening across the right house's ground floor (x 136-156, y 64-87), a pillar of wall at the right ----
a = s.index('SHOPFRONT = """')
b = s.index('PLACE.append(("SHOPFRONT", 136, 64))')
s = s[:a] + 'SHOPFRONT = "\\n".join(["#" * 21 + "BB#"] * 24)\n' + s[b:]
p.write_text(s)
print("ok")
