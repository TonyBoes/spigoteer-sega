"""IGLOO option 2, "Open-door bar", 80 x 64. Palette IGLOO: 0 snow, 1 ice, 2 deep ice, 3 ink.  Light from the top left.
A wide, low ice dome (the opposite silhouette to option 1's tall one) with a big arched opening that shows the bar inside (lit room, shelf of
bottles, two mugs on the counter, two stools), a cocoa mug sign over the arch, and a snowman with a scarf in front.  Same period-8 ice pattern."""
import common as C
from canvas import Canvas
from v_igloo import DRIFT

W, H = 80, 56
BIOME, AT = 'snow', (53, 5)

HW = [6, 10, 13, 15, 17, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 28, 29, 29, 30, 30, 31, 31, 32, 32, 32, 33, 33, 33, 34, 34, 34, 34]   # y 20 to 51
MID = ["00000002", "11111112", "11111112", "22222222", "00020000", "11121111", "11121111", "22222222"]
SHADE = ["11111113", "22222223", "22222223", "33333333", "11131111", "22232222", "22232222", "33333333"]

# the arch, 20 wide: the typed arch rows, then the straight rows built round the 16 wide room typed in ROOM
ARCH = ["______33333333______", "____33" + "00000000" + "33____", "___3" + "000000000000" + "3___", "__3" + "00000000000000" + "3__", "_3" + "0" * 16 + "3_"]
ROOM = ["0000000000000000",       # r5
        "0010001000100010",       # bottle necks
        "0022002200220022",       # bottle bodies
        "3333333333333333",       # the shelf
        "0003330000033300",       # the two mugs on the counter
        "0003130000031300",
        "2222222222222222",       # the counter top
        "3333333333333333",
        "3232323232323232",       # the counter's panels
        "3333333333333333",
        "0033300000333000",       # stool seats
        "0003000000030000",
        "1111111111111111"]       # the floor
DOORWAY = C.G(*ARCH, *["_3" + r + "3_" for r in ROOM])

MUG = C.G("_333333333____", "30000000003___", "30001000103___", "31222222223333", "31222222223__3", "31222222223__3", "31222222223333",
          "31222222223___", "32222222223___", "_333333333____")

SNOWMAN = C.G("___333333___", "___333333___", "__33333333__", "__30000003__", "__30300303__", "__30002203__", "__30000013__", "___333333___",
              "_3222222223_", "_3000000013_", "300000000113", "300003000113", "300000000113", "300003000113", "_3000000113_", "__30000113__", "___333333___")


def build():
    c = Canvas("igloo2", "igloo", W, H)
    C.silh(c, 12, HW, 40, lambda x, y, k: "0" if k in (1, 2) else (SHADE if x >= 56 else MID)[y % 8][x % 8])
    for x in range(6, 74):
        c.px[44][x] = "3"
    C.paste(c, 30, 25, DOORWAY)
    C.paste(c, 33, 14, MUG)
    # contact shadow, drifts
    for x in range(8, 72):
        c.px[45][x] = "1"
    for x in list(range(14, 30)) + list(range(46, 64)):
        c.px[46][x] = "1"
    C.paste(c, 56, 47, DRIFT)
    C.paste(c, 2, 35, SNOWMAN)
    return c
