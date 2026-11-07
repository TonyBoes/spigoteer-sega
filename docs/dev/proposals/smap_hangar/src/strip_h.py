"""Round 4b strip: the hangar and tower stand 8 px higher (foot y 55, as in round 3's runway variant), so the strip has the piece's last 16 rows: an apron under the doors
(x 2 to 31, y 56 to 61, ink sides) joining a runway (x 1 to 50, y 62 to 70: ink, asphalt y 63 to 69, a dashed centre line on y 66 with period 8, ink).
tone "2" navy (the building colour on Color); tone "1" grey tarmac (BASE steel, so no new palette slot), dashes navy.  Typed runs per row."""


def strip2(c, tone="2"):
    dash = "0" if tone == "2" else "2"
    for y in range(56, 62):
        c.px[y][2] = "3"
        c.px[y][31] = "3"
        for x in range(3, 31):
            c.px[y][x] = tone
    for x in range(1, 51):
        cap = x in (1, 50)
        in_apron = 2 < x < 31
        c.px[62][x] = "3" if (cap or not in_apron) else tone
        c.px[63][x] = "3" if cap else ("1" if (tone == "2" and not in_apron) else tone)
        for y in (64, 65, 67, 68, 69):
            c.px[y][x] = "3" if cap else tone
        c.px[66][x] = "3" if cap else (dash if x % 8 < 4 else tone)
        c.px[70][x] = "3"
