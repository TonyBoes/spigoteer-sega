"""Round 4f strip: the hangar and tower stand at foot y 55 (raised), the apron (x 2 to 55, y 56 to 63, ink sides) runs under the doors and the tower, and the runway
(8 rows, y 64 to 71: ink, lit kerb, asphalt, dashed centre line on y 67 with period 8, asphalt x3, ink) runs from x 1 to x 197 under the mountain range's foot (the foot line
is y 63).  The runway's rows lie in the last tile row, which holds no mountain, so only its palette cells are set to BASE (x 56 on).  Typed runs per row.
apron = '2' (navy, one dark block with the runway) or '1' (light concrete, ink outline all round)."""

END = 197


def strip4(c, apron='2'):
    c.palrect(56, 64, 200, 72, "base")
    for y in range(56, 64):
        c.px[y][2] = "3"
        c.px[y][55] = "3"
        for x in range(3, 55):
            c.px[y][x] = apron
    dark = apron == '2'
    for x in range(1, END + 1):
        cap = x in (1, END)
        join = dark and 2 < x < 55
        c.px[64][x] = "3" if (cap or not join) else "2"
        c.px[65][x] = "3" if cap else ("2" if join else "1")
        for y in (66, 68, 69, 70):
            c.px[y][x] = "3" if cap else "2"
        c.px[67][x] = "3" if cap else ("0" if x % 8 < 4 else "2")
        c.px[71][x] = "3"
