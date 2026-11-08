"""BIG MOUNTAIN option 2, "Twin peaks", cells x 0-55 of the Space Lounge's desert (the hangar, tower, dish, fence and runway are today's).
Palette SALOON: 0 sand, 1 lit rock, 2 shaded rock, 3 ink.  Light from the top left.
Two summits so it cannot read as a pyramid: a tall main peak leaning left (steep lit face, 1:1 then 1:2 slopes) in front of a lower peak behind it
to the right, with the saddle where their outlines cross.  Each has its own ridge line, a lit face with a light rim and dashed strata every
8 rows (on the 8 px grid), a shaded face with its own dashes, and the foot flares to the ground."""
import common as C
import v_space

BIOME, AT = 'desert', (1, 34)
REGION = (0, 0, 6, 6)

# main peak A (front): left and right edge of each row from y = 5 (45 rows); apex at x 14
LEFT_A = [14 - k for k in range(9)] + [5, 5, 4, 4, 3, 3, 2, 2, 1, 1] + [1] * 20 + [0] * 6
RIGHT_A = [14 + k for k in range(11)] + [24, 25, 25, 26, 26, 27, 27, 28, 28, 29, 29, 30, 30, 31, 31, 32, 32, 33, 33, 34] + \
          [34, 35, 35, 36, 37, 37, 38, 39, 39, 40, 41, 41, 42, 42]
assert len(LEFT_A) == len(RIGHT_A) == 45, (len(LEFT_A), len(RIGHT_A))
# second peak B (behind): rows from y = 12 (38 rows); apex at x 38; only its right side shows past A
LEFT_B = [38 - k for k in range(9)] + [29] * 29
RIGHT_B = [38 + k for k in range(9)] + [46, 47, 47, 48, 48, 49, 49, 50, 50, 51, 51, 52, 52, 53, 53, 54, 54, 55, 55] + [55] * 10
assert len(LEFT_B) == len(RIGHT_B) == 38, (len(LEFT_B), len(RIGHT_B))


def peak(c, y0, LEFT, RIGHT, ridge, rim_rows):
    n = len(LEFT)
    for k in range(n):
        y = y0 + k
        L, R = LEFT[k], RIGHT[k]
        rx = ridge(k)
        for x in range(L, R + 1):
            if k == 0 or x in (L, R):
                v = "3"
            elif x == rx and k < n - 8:
                v = "3"
            elif x < rx:
                v = "2" if (y % 8 == 2 and x % 8 < 5) else "1"
            else:
                v = "3" if (y % 8 == 2 and x % 8 < 5) else "2"
            c.px[y][x] = v
        if k > 0:                                              # the runs that join the edges to the row above
            if LEFT[k - 1] > L:
                for x in range(L, LEFT[k - 1]):
                    c.px[y][x] = "3"
            if RIGHT[k - 1] < R:
                for x in range(RIGHT[k - 1] + 1, R + 1):
                    c.px[y][x] = "3"
        if k < rim_rows and L + 1 < rx and c.px[y][L + 1] == "1":
            c.px[y][L + 1] = "0"                               # the light rim on the lit edge


def build():
    c = v_space.build(dmg=True)
    for y in range(0, 50):
        for x in range(0, 56):
            c.px[y][x] = "0"
    peak(c, 12, LEFT_B, RIGHT_B, lambda k: 38 + k // 2, 0)
    peak(c, 5, LEFT_A, RIGHT_A, lambda k: 14 + k // 2 if k < 24 else 26 + (k - 24) // 3, 22)
    for x in range(0, 56):
        c.px[50][x] = "3"
    return c
