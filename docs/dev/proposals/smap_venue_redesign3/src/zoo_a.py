"""JUNGLE ZOO version A, "Lion gate, giraffe and bamboo", 112 x 64 (14 x 8 cells).  Option 1's lion gate (round 1, unchanged) at cells 3 to 10.
From option 2: a spotted giraffe looking over a rail fence at the left of the gate, a grove of bamboo at the right.  ZOOGATE: cells 0-10 (gate, giraffe, fence);
ZOO: cells 11-13 (bamboo).  Light from the top left."""
import common as C
import zoo_parts as Z
from canvas import Canvas

W, H = 112, 64
BIOME, AT = 'jungle', (16, 35)
UNMERGE = True


def build():
    c = Canvas("zooA", "zoo", W, H)
    c.palrect(0, 0, 88, 64, "zoogate")
    Z.gate(c, 24)
    Z.giraffe(c, 8, 14)
    Z.fence(c, 0, 24)
    Z.bamboo(c, (11, 12, 13), (16, 26, 10))
    return c
