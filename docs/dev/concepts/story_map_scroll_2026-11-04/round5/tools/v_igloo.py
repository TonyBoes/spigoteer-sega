"""The Igloo, 80 x 48. Palette IGLOO: 0 snow, 1 ice, 2 deep ice blue, 3 ink.
An ice-block dome with a tunnel entrance and a lit doorway, a cocoa sign on a post, two snowy spruces and drifts.
The dome's silhouette is typed row by row (the width list); the courses are typed templates cut to that silhouette."""
from canvas import Canvas, piece
from art import R

W, H = 80, 48
PAL = "igloo"

# silhouette: total width (ink included) of the dome rows from y = 6 (the cap), and of the tunnel rows from y = 26
DOME = [12, 20, 26, 30, 34, 38, 40, 42, 44, 46] + [48] * 21
TUNNEL = [8, 14, 18, 22, 24] + [26] * 6
# ice courses, 48 px wide (the dome's x 16 to 63), five rows a course: lit top-left row, three body rows, a broken seam
EVEN = ["(0:5 1:6 2:1)*4", "(1:11 2:1)*4", "(1:11 2:1)*4", "(1:11 2:1)*4", "(2:10 1:2)*4"]
ODD = ["0:4 1:1 2:1 (0:5 1:6 2:1)*3 0:5 1:1", "1:5 2:1 (1:11 2:1)*3 1:6", "1:5 2:1 (1:11 2:1)*3 1:6", "1:5 2:1 (1:11 2:1)*3 1:6",
       "1:1 (2:10 1:2)*3 2:10 1:1"]

SPRUCE = piece(".:7 3:2 .:7", ".:6 3:1 0:2 3:1 .:6", ".:5 3:1 0:4 3:1 .:5", ".:4 3:1 0:2 1:2 2:2 3:1 .:4", ".:3 3:1 1:4 2:4 3:1 .:3", ".:2 3:12 .:2",
               ".:4 3:1 0:6 3:1 .:4", ".:3 3:1 0:2 1:3 2:3 3:1 .:3", ".:2 3:1 1:5 2:5 3:1 .:2", ".:1 3:1 1:6 2:6 3:1 .:1", ".:1 3:14 .:1",
               ".:7 3:2 .:7", ".:7 3:2 .:7")
BOARD = piece("3:12", "3:1 0:4 1:1 0:3 1:1 0:1 3:1", "3:1 0:2 2:5 0:3 3:1", "3:1 0:2 2:5 2:1 0:2 3:1", "3:1 0:2 2:5 0:1 2:1 0:1 3:1",
              "3:1 0:2 2:5 2:1 0:2 3:1", "3:1 0:3 2:4 0:3 3:1", "3:1 0:10 3:1", "3:1 0:10 3:1", "3:12")
DRIFT = piece(".:9 1:6 .:9", ".:6 1:3 0:6 1:3 .:6", ".:4 1:2 0:10 1:3 .:5", ".:2 1:2 0:12 1:5 .:3", ".:1 1:1 0:14 1:8", "1:1 0:15 1:8", "0:14 1:10", "0:12 1:12", "1:24")


def course_row(i, parity):
    """the template row for course row i (0 at the dome's first body row), as a 48 wide string for x 16 to 63"""
    block = (i // 5 + parity) % 2
    return R((EVEN if block == 0 else ODD)[i % 5], 48)


SH_DOME = [1, 2, 3, 3, 4, 5, 5, 6, 7, 8, 9, 10, 10, 11, 11, 12, 12, 12, 12, 12, 12, 12, 11, 11, 10, 10, 9, 9, 8, 8]   # the shaded crescent on the right, row by row
SH_TUN = [1, 2, 2, 3, 3, 4, 4, 4, 4, 4]
SHADE = {"0": "1", "1": "2", "2": "2"}


def band(c, y, w, i, parity, shade, snow=False):
    left, right = 40 - w // 2, 39 + w // 2
    c.px[y][left] = "3"
    c.px[y][right] = "3"
    t = course_row(i, parity)
    for x in range(left + 1, right):
        v = ("0" if t[x - 16] != "2" else "1") if snow else (t[x - 16] if 16 <= x < 64 else "1")
        c.px[y][x] = SHADE[v] if x > right - 1 - shade else v


def build(dmg=False):
    c = Canvas("igloo", PAL, W, H)
    # ---- the dome -------------------------------------------------------------------------------------------------------
    for k, w in enumerate(DOME):
        y = 6 + k
        if k == 0:
            c.row(y, "0:34 3:12 0:34")
        else:
            band(c, y, w, k - 1, 0, SH_DOME[k - 1])
    c.row(37, "0:16 3:48 0:16")
    # ---- the tunnel in front: its courses start on the other parity ---------------------------------------------------------
    for k, w in enumerate(TUNNEL):
        y = 26 + k
        if k == 0:
            for x in range(36, 44):
                c.px[y][x] = "3"
        else:
            band(c, y, w, k - 1, 1, SH_TUN[k - 1], snow=(k <= 3))
    c.row(37, "0:16 3:48 0:16")
    # the doorway: an arch of ink, a dark room with a warm lit floor
    for x in range(37, 43):
        c.px[30][x] = "3"
    for x in range(36, 44):
        c.px[31][x] = "3"
    for y in range(32, 37):
        for x in range(35, 45):
            c.px[y][x] = "3"
    for x in range(36, 44):
        c.px[35][x] = "2"
    for x in range(37, 43):
        c.px[36][x] = "1"
    # ---- the sign post, the spruces, the drifts -----------------------------------------------------------------------------
    for y in range(22, 38):
        c.px[y][7] = "3"
        c.px[y][8] = "2"
    c.paste(2, 12, BOARD)
    c.paste(64, 8, SPRUCE)
    c.paste(64, 24 if dmg else 21, SPRUCE)                   # DMG: both spruces and both drifts on the same phase of the 8 px grid
    c.paste(0, 39, DRIFT)
    c.paste(56 if dmg else 54, 39, DRIFT)
    return c


if __name__ == "__main__":
    print(len(build().out()))
