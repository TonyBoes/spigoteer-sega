"""Round 4h runway: 6 rows (y 66 to 71): ink top (the jet's belly line stands on it), lit kerb, asphalt, dashed centre line on y 69 (period 8), asphalt, ink.  x 1 to 197, ink caps.
Rows 64 and 65 are plain sand above it so the jet (origin (4, 57): fin y 57-61, fuselage y 62-66, wings y 67-71) stands on sand clear of the hangar foot (y 55) and the tower
(x 36 to 48 above y 55).  All its cells are x < 56, the BASE palette; the runway's cells x 56 on are set to BASE (no mountain pixels in y 64 to 71)."""
END = 197


def strip6(c):
    c.palrect(56, 64, 200, 72, "base")
    for x in range(1, END + 1):
        cap = x in (1, END)
        c.px[66][x] = "3"
        c.px[67][x] = "3" if cap else "1"
        for y in (68, 70):
            c.px[y][x] = "3" if cap else "2"
        c.px[69][x] = "3" if cap else ("0" if x % 8 < 4 else "2")
        c.px[71][x] = "3"
