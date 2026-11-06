"""BIG MOUNTAIN option 1, "Tower butte", cells x 0-55 of the Space Lounge's desert (the hangar, tower, dish, fence and runway are today's).
Palette SALOON: 0 sand, 1 lit rock, 2 shaded rock, 3 ink.  Light from the top left.
A fluted monolith in the manner of the film's landing site: three columns 8 px wide (one typed 8 px pattern, so the whole shaft is a few tiles), a
wider lip on a flat top, a few long cracks, and a scree skirt whose edges run on 2:1 slopes.  Taller and narrower than today's butte (24 px wide)."""
import common as C
import v_space
import decor

BIOME, AT = 'desert', (1, 34)
REGION = (0, 0, 6, 6)

COL_L = "21111122"          # a lit column: separator, lit face, shaded edge (x % 8)
COL_D = "32222233"          # a column in the shade (x >= 32)
SCREE_L = ["11111111", "11111111", "12211111", "11111122", "11111111", "11221111", "11111111", "11111122"]
SCREE_D = ["22222222", "22222222", "23322222", "22222233", "22222222", "22332222", "22222222", "22222233"]


def build():
    c = v_space.build(dmg=True)
    for y in range(0, 50):
        for x in range(0, 56):
            c.px[y][x] = "0"
    # ---- the lip and the flat top ----
    for x in range(14, 42):
        c.px[2][x] = "3"
        c.px[5][x] = "3"
        c.px[3][x] = "0"
        c.px[4][x] = "1" if x < 32 else "2"
    for y in (3, 4):
        c.px[y][14] = "3"
        c.px[y][41] = "3"
    # ---- the shaft: three columns, an ink edge each side ----
    for y in range(6, 40):
        for x in range(16, 40):
            c.px[y][x] = (COL_L if x < 32 else COL_D)[x % 8]
        c.px[y][16] = "3"
        c.px[y][39] = "3"
    # ---- long cracks ----
    for y in range(8, 27):
        c.px[y][21] = "3"
    for y in range(16, 36):
        c.px[y][27] = "3"
    for y in range(12, 22):
        c.px[y][35] = "2"
    # ---- the scree skirt: 2:1 slopes, lit left, shaded right ----
    for k, y in enumerate(range(40, 50)):
        L = max(14 - 2 * k, 0)
        R = min(41 + 2 * k, 55)
        for x in range(L, R + 1):
            t = SCREE_L if x < 32 else SCREE_D
            c.px[y][x] = "3" if (x in (L, R) and k < 8) else t[y % 8][x % 8]
        if k < 8:
            for x in range(L, min(L + 2, 16)):
                c.px[y][x] = "3"
            for x in range(max(R - 1, 40), R + 1):
                c.px[y][x] = "3"
    for x in range(0, 56):
        c.px[50][x] = "3"
    for bx in (4, 44):
        C.paste(c, bx, 44, decor.ROCK[1])
    return c
