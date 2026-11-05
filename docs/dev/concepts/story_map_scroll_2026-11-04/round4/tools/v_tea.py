"""The Teahouse, 96 x 56. Palettes TEA (house, lantern, stones): 0 moss, 1 paper, 2 dark wood and roof, 3 ink;
TEA_B (the cherry tree, the right 16 columns): 0 moss, 1 blossom, 2 deep pink, 3 ink.
A two-tier tiled roof with upturned eaves, shoji walls with a lattice, a door curtain, a veranda, a stone lantern, stepping stones
and a cherry tree in bloom."""
from canvas import Canvas, piece

W, H = 96, 56
PAL = "tea"

NOREN = piece("3:12", ("3:1 2:4 3:2 2:4 3:1", 8), ("3:12", 12))
LANT = piece(".:3 3:2 .:3", ".:1 3:6 .:1", "3:1 2:6 3:1", "3:8", ".:1 3:1 1:4 3:1 .:1", ".:1 3:1 1:4 3:1 .:1", ".:1 3:6 .:1",
             ".:2 3:1 2:2 3:1 .:2", ".:2 3:1 2:2 3:1 .:2", ".:2 3:1 2:2 3:1 .:2", "3:8", "3:8")
STONE = piece(".:1 3:6 .:1", "3:1 1:6 3:1", ".:1 3:6 .:1")
TREE = piece(".:5 3:6 .:5", ".:3 3:2 1:6 3:2 .:3", ".:2 3:1 1:3 0:2 1:5 3:1 .:2", ".:1 3:1 1:2 0:1 1:7 2:2 3:1 .:1",
             "3:1 1:9 2:5 3:1", "3:1 1:6 0:1 1:3 2:4 3:1", "3:1 1:5 2:9 3:1", ".:1 3:1 2:12 3:1 .:1", ".:2 3:2 2:8 3:2 .:2",
             ".:4 3:8 .:4", (".:6 3:1 2:2 3:1 .:6", 8), ".:4 3:8 .:4")


def centred(w, inner):
    pad = (80 - w) // 2
    return f"0:{pad} {inner} 0:{96 - pad - w}"


def build():
    c = Canvas("tea", PAL, W, H)
    c.palrect(80, 0, 96, 56, "tea_b")
    # ---- the upper roof: ink edge, a lit left edge, tiles ----------------------------------------------------------------
    for k, w in enumerate((8, 16, 24, 32, 40, 46, 50)):
        c.row(2 + k, centred(w, f"3:1 1:2 2:{w - 4} 3:1"))
    # ---- the upper wall -----------------------------------------------------------------------------------------------------
    c.row(9, "0:26 3:28 0:42")
    for y in range(10, 16):
        c.row(y, "0:26 3:1 2:1 1:11 2:2 1:11 2:1 3:1 0:42")
    c.row(16, "0:26 3:28 0:42")
    # ---- the lower roof, with curled eaves ---------------------------------------------------------------------------------------
    for k, w in enumerate((40, 48, 56, 62, 66, 70, 72)):
        c.row(17 + k, centred(w, f"3:1 1:2 2:{w - 4} 3:1"))
    for x, y in ((3, 22), (76, 22), (2, 21), (77, 21)):
        c.put(x, y, "3")
    c.row(24, "0:4 3:72 0:20")
    # ---- the lower wall: a beam, paper panels with a lattice, posts --------------------------------------------------------------------
    c.row(25, "0:12 3:56 0:28")
    for y in (26, 27):
        c.row(y, "0:12 3:1 2:54 3:1 0:28")
    for y in range(28, 49):
        if y in (33, 39):
            c.row(y, "0:12 3:1 2:2 2:17 2:2 1:12 2:2 2:17 2:2 3:1 0:28")
        else:
            c.row(y, "0:12 3:1 2:2 1:8 2:1 1:8 2:2 1:12 2:2 1:8 2:1 1:8 2:2 3:1 0:28")
    c.paste(34, 28, NOREN)
    # ---- the veranda --------------------------------------------------------------------------------------------------------------
    c.row(49, "0:6 3:68 0:22")
    for y in (50, 51):
        c.row(y, "0:6 3:1 2:66 3:1 0:22")
    c.row(52, "0:6 3:68 0:22")
    c.paste(34, 53, STONE)
    c.paste(48, 53, STONE)
    c.paste(1, 38, LANT)
    # ---- the cherry tree ---------------------------------------------------------------------------------------------------------------
    c.paste(80, 34, TREE)
    return c


if __name__ == "__main__":
    print(len(build().out()))
