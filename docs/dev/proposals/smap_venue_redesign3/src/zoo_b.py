"""JUNGLE ZOO version B, "Lion gate, tall giraffe and bamboo bush", 112 x 64 (14 x 8 cells).  Option 1's lion gate at cells 3 to 10, as in version A, but the
accessories swap sides and sizes: the bamboo grove (three stalks, a bush with eyes at its foot) at the LEFT, and at the right a tall giraffe whose head rises above
the lions, over a rail fence.  ZOO: cells 0-2; ZOOGATE: cells 3-13.  Light from the top left."""
import common as C
import zoo_parts as Z
import v_zoo
from canvas import Canvas

W, H = 112, 64
BIOME, AT = 'jungle', (16, 35)
UNMERGE = True


def build():
    c = Canvas("zooB", "zoo", W, H)
    c.palrect(24, 0, 112, 64, "zoogate")
    Z.gate(c, 24)
    Z.bamboo(c, (0, 1, 2), (20, 10, 28))
    C.paste(c, 4, 48, v_zoo.CANOPY)
    C.paste(c, 9, 52, v_zoo.EYES)
    Z.giraffe(c, 96, 4)
    Z.fence(c, 88, 112)
    return c
