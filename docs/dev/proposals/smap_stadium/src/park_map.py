"""The approved stadium (park_s2, final 2 with the wavy flag) with ONE symmetric hand edit for the map: the outer 16 px of each foul line and the two outer tufts are drawn as field grass.
Why: the five right-hand field cells must take the map's GRASS palette (8 palettes per window), which has no tan, so a tan line would turn dark green there on one side only.  Both sides stop
the same way: x 0 to 15 and 80 to 95, the foul line (2 px of dirt, index 2) and the tufts at (10, 35) and (82, 35) become grass (index 1).  Rows: the outer stands (x 0 to 7 and 88 to 95)
end at y 40, the wings (x 8 to 23 and 72 to 87) at y 32, so only pixels below those rows are field."""
import park_s2 as PS

BIOME, AT, UNMERGE = PS.BIOME, PS.AT, PS.UNMERGE
FIELD_FROM = {**{x: 40 for x in range(0, 8)}, **{x: 32 for x in range(8, 16)}, **{x: 32 for x in range(80, 88)}, **{x: 40 for x in range(88, 96)}}


def build(*a, **k):
    c = PS.build(*a, **k)
    for x, y0 in FIELD_FROM.items():
        for y in range(y0, 56):
            if c.px[y][x] == "2":
                c.px[y][x] = "1"
    return c
