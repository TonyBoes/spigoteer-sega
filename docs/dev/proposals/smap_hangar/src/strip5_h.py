"""Round 4g strip: no apron.  The runway is round 4f's (x 1 to 197, y 64 to 71, ink caps, dashed centre line on y 67) and the jet stands on the desert sand above it.
taxi=True adds a short narrow taxi strip from the doors to the runway: ink sides x 11 and x 20, navy between, y 56 to 63, open into the runway's asphalt (rows 64, 65).
shadow: a small cast shadow of the jet on the sand, light steel (index 1), typed runs on y 62 and 63."""
import strip4_h as S4

END = S4.END


def strip5(c, taxi=False):
    c.palrect(56, 64, 200, 72, "base")
    if taxi:
        for y in range(56, 64):
            c.px[y][11] = "3"
            c.px[y][20] = "3"
            for x in range(12, 20):
                c.px[y][x] = "2"
    for x in range(1, END + 1):
        cap = x in (1, END)
        join = taxi and 11 < x < 20
        c.px[64][x] = "3" if (cap or not join) else "2"
        c.px[65][x] = "3" if cap else ("2" if join else "1")
        for y in (66, 68, 69, 70):
            c.px[y][x] = "3" if cap else "2"
        c.px[67][x] = "3" if cap else ("0" if x % 8 < 4 else "2")
        c.px[71][x] = "3"


def shadow(c, runs):
    for y, x, s in runs:
        for i, ch in enumerate(s):
            c.px[y][x + i] = ch
