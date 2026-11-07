"""SPACE LOUNGE MOUNTAIN, round 3.  The mountain is round 2's A, pixel for pixel (mountain_a.mountain is called unchanged).  Only the base changed: the HANGAR (low, wide,
ribbed shallow arch, hazard lintel, big sliding doors; base3.HANGAR) and the TOWER TOP (a mast with a lamp and a radar dish, no cross).  200 x 72 (25 x 9 cells).
mountain_a3 = no runway; mountain_a3r = with the angled runway (a variant, because it costs tiles: see NOTES)."""
import common as C
import base3 as B
import mountain_a as MA
from canvas import Canvas

W, H = 200, 72
BIOME, AT = 'desert', (1, 34)
REGION = (0, 0, 24, 8)
YF = MA.YF
RUNWAY = False


def build(runway=None):
    runway = RUNWAY if runway is None else runway
    c = Canvas("mountainA3", "saloon", W, H)
    c.palrect(0, 0, 56, 72, "base")
    MA.mountain(c)
    yb = 55 if runway else YF
    if runway:
        B.runway(c, 8, 40, 66, 2)
    B.hangar(c, 0, yb)
    B.tower(c, 38, yb)
    return c
