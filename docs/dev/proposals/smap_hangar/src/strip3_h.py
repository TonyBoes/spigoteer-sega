"""Round 4c strip, hangar and tower raised 8 px (foot y 55): a 4-row apron under the doors (x 2 to 31, y 56 to 59, ink sides) joining a 9-row runway (x 1 to 50, y 60 to 68: ink
(asphalt where the apron joins), a lit kerb, asphalt, a dashed centre line on y 64 with period 8, asphalt, ink).  Navy asphalt (index 2).  Typed runs per row."""


def strip3(c):
    for y in range(56, 60):
        c.px[y][2] = "3"
        c.px[y][31] = "3"
        for x in range(3, 31):
            c.px[y][x] = "2"
    for x in range(1, 51):
        cap = x in (1, 50)
        in_apron = 2 < x < 31
        c.px[60][x] = "3" if (cap or not in_apron) else "2"
        c.px[61][x] = "3" if cap else ("2" if in_apron else "1")
        for y in (62, 63, 65, 66, 67):
            c.px[y][x] = "3" if cap else "2"
        c.px[64][x] = "3" if cap else ("0" if x % 8 < 4 else "2")
        c.px[68][x] = "3"
