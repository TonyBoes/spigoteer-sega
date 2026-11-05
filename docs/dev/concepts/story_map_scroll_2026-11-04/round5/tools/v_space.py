"""The Space Lounge's desert, 112 x 72 (the UFO is a sprite that hovers beside the mountain; its landing is the lounge).
Palettes SALOON (the saloon's own, for the desert: mountain, cells x 0-55, y 0-55): 0 sand, 1 lit rock, 2 shaded rock, 3 ink;
BASE (the air base, cells x 56-111 y 0-55, and the runway strip y 56-71 across): 0 sand, 1 steel, 2 navy, 3 ink.
A layered mountain with a lit left face; a quonset hangar with a dark door, a control tower with a glass cab and an aerial, a radar dish,
a fence, and a runway with edge lights and a dashed centre line."""
from canvas import Canvas, piece

W, H = 112, 72
PAL = "saloon"

# the mountain: a stepped butte, 45 rows; the left and right edge of each row, and the ridge between lit and shaded faces, typed by hand
LEFT = [16] + [14] * 3 + [13, 12, 11, 10, 10] + [6, 6, 5, 5, 4, 4, 3, 3] + [2, 2, 1, 1, 1] + [0] * 23
RIGHT = [34] + [36] * 3 + [37, 38, 39, 40, 40] + [44, 45, 45, 46, 46, 47, 47, 48] + [49, 49, 50, 50, 51] + [52, 52, 52, 53, 53, 53, 54, 54, 54] + [55] * 14
RIDGE = [3] * 9 + [4] * 8 + [5] * 10 + [6] * 18          # the ridge sits this far right of the middle of the butte (x 28)
STRATA = {12, 21, 30, 39}
STRATA_D = {12, 20, 28, 36}                                # DMG: the four dashed courses 8 rows apart, so they are the same tiles

DISH = piece(".:4 3:4 .:4", ".:2 3:2 0:4 3:2 .:2", ".:1 3:1 0:2 1:6 3:1 .:1", "3:1 0:1 1:3 3:2 1:3 2:1 3:1", "3:1 1:4 3:2 1:3 2:1 3:1",
             "3:1 1:6 2:4 3:1", "3:1 1:3 2:7 3:1", ".:1 3:1 2:8 3:1 .:1", ".:2 3:2 2:4 3:2 .:2", ".:4 3:4 .:4",
             (".:5 3:2 .:5", 6), ".:3 3:6 .:3")
TOWER = piece(".:2 3:12 .:2", ".:1 3:14 .:1", ("3:1 2:1 0:3 2:1 0:4 2:1 0:3 2:1 3:1", 3), "3:16",
              (".:3 3:1 1:4 2:4 3:1 .:3", 5), ".:3 3:1 1:2 3:4 2:2 3:1 .:3", (".:3 3:1 1:4 2:4 3:1 .:3", 8), ".:3 3:1 1:2 3:4 2:2 3:1 .:3",
              (".:3 3:1 1:4 2:4 3:1 .:3", 9), ".:2 3:12 .:2")
HANGAR_W = [12, 20, 26, 30, 34, 36, 38, 40]            # the arch, row by row; then straight sides


def mrow(c, y, k, dmg=False):
    left, right = LEFT[k], RIGHT[k]
    xb = 28 + RIDGE[k]
    c.px[y][left] = "3"
    c.px[y][right] = "3"
    for x in range(left + 1, right):
        v = "1" if x < xb else "2"
        if v == "1" and k in (STRATA_D if dmg else STRATA) and ((x % 8 if dmg else (x - left) % 8) < 5):      # DMG: the dashes sit on the 8 px grid, not on the edge
            v = "2"
        c.px[y][x] = v
    if k < 30 and left + 1 < xb:
        c.px[y][left + 1] = "0"
    if k == 0:
        for x in range(left + 1, right):
            c.px[y][x] = "0"


def build(dmg=False):
    c = Canvas("space", PAL, W, H)
    c.palrect(56, 0, 112, 72, "base")
    c.palrect(0, 56, 56, 72, "base")
    # ---- the mountain ---------------------------------------------------------------------------------------------------------
    for k in range(45):
        mrow(c, 5 + k, k, dmg)
    for x in range(8, 48):
        c.px[50][x] = "3"
    # a few stones at its foot
    for (x, y) in (() if dmg else ((6, 52), (7, 52), (7, 53), (40, 53), (41, 53), (41, 52), (45, 54), (46, 54))):      # DMG: no stones at the foot
        c.px[y][x] = "2"
    # ---- the hangar: an arch, then straight sides, a lit left and a shaded right; a dark door ---------------------------------------------------
    for r in range(20):
        y = 30 + r
        w = HANGAR_W[r] if r < len(HANGAR_W) else 40
        left = 62 + (40 - w) // 2
        right = left + w - 1
        c.px[y][left] = "3"
        c.px[y][right] = "3"
        for x in range(left + 1, right):
            c.px[y][x] = "2" if x > right - 7 else "1"
        c.px[y][left + 1] = "0"
        if r in (6, 12):
            for x in range(left + 2, right - 6):
                c.px[y][x] = "2" if ((x % 8) < 5 if dmg else (x - left) % 6 < 4) else "1"
    for x in range(62, 102):
        c.px[49][x] = "3"
    for r, wd in enumerate([10, 16, 18, 20, 20, 20, 20, 20, 20, 20, 20]):
        y = 38 + r
        for x in range(80 - wd // 2, 80 + wd // 2):
            c.px[y][x] = "3"
    for y in range(41, 49):
        c.px[y][76] = "2"
        c.px[y][84] = "2"
    for x in range(71, 91):
        c.px[48][x] = "2"
    # ---- the tower, the dish, the aerial ---------------------------------------------------------------------------------------------------
    c.paste(96, 11, TOWER)
    for y in range(3, 11):
        c.px[y][104] = "3"
        c.px[y][103] = "3" if y == 3 else c.px[y][103]
    c.paste(58, 16, DISH)
    # ---- the fence ---------------------------------------------------------------------------------------------------------------------------
    step = 14
    for x in (() if dmg else range(0, 112, step)):           # DMG: no posts, the two rails run the whole width
        for y in range(50, 56):
            c.px[y][x] = "3"
    for x in range(1, 112):
        if dmg or x % step != 0:
            c.px[51][x] = "1"
            c.px[54][x] = "1"
    # ---- the runway ----------------------------------------------------------------------------------------------------------------------------
    c.row(56, "3:112")
    for y in range(57, 71):
        c.row(y, "2:112")
    c.row(58, "(2:4 1:1 2:3)*14")
    c.row(69, "(2:4 1:1 2:3)*14")
    for y in (63, 64):
        c.row(y, "(0:8 2:8)*7")
    c.row(71, "3:112")
    return c


if __name__ == "__main__":
    print(len(build().out()))
