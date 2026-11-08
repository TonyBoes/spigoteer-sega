"""(v1, commit bf8d13ff: outlines and fixes, no texture)  The Teahouse, 96 x 56, QUALITY PASS (proposal; drop-in for tools/smap_world/v_tea.py, same build(dmg) signature).
Same building, footprint, palettes (TEA, TEA_B), sign-free, door, roofs, lantern, stones, tree.  Every row below is typed by hand; the changes against v_tea.py are marked  # PASS.
Palettes TEA: 0 moss, 1 paper, 2 dark wood and roof, 3 ink.  TEA_B (the tree, the right 16 columns): 0 moss, 1 blossom, 2 deep pink, 3 ink.
Light from the top left, like the lodge, saloon and bistro beside it: lit left slopes of the roofs, bright top plane on the veranda."""
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


def build(dmg=False):
    c = Canvas("tea", PAL, W, H)
    c.palrect(80, 0, 96, 56, "tea_b")
    # ---- the upper roof.  PASS: a ridge cap (row 1), the ink outline now runs along the top of every step (4 4 4 4 3 2 px, was one ink px per row, so the
    # roof had no outline between its corners), the lit cream on the left slope tapers 2 3 3 2 2 1 1 instead of a constant 2 px band hugging the edge ----------
    c.row(1, "0:37 3:6 0:53")                                             # PASS ridge cap
    c.row(2, "0:36 3:1 1:2 2:4 3:1 0:52")
    c.row(3, "0:32 3:4 1:3 2:5 3:4 0:48")                                 # PASS
    c.row(4, "0:28 3:4 1:3 2:13 3:4 0:44")                                # PASS
    c.row(5, "0:24 3:4 1:2 2:22 3:4 0:40")                                # PASS
    c.row(6, "0:20 3:4 1:2 2:30 3:4 0:36")                                # PASS
    c.row(7, "0:17 3:3 1:1 2:39 3:3 0:33")                                # PASS
    c.row(8, "0:15 3:2 1:1 2:45 3:2 0:31")                                # PASS
    c.row(9, "0:16 3:48 0:32")                                            # PASS: the upper roof's eave gets its bottom outline (was only under the wall, 26..53)
    # ---- the upper wall (unchanged) ---------------------------------------------------------------------------------------------
    for y in range(10, 16):
        c.row(y, "0:26 3:1 2:1 1:11 2:2 1:11 2:1 3:1 0:42")
    c.row(16, "0:26 3:28 0:42")
    # ---- the lower roof, with curled eaves.  PASS: same outline and taper as above ------------------------------------------------------
    c.row(17, "0:20 3:6 2:28 3:6 0:36")                                   # PASS top edge either side of the upper wall
    c.row(18, "0:16 3:4 1:3 2:37 3:4 0:32")                               # PASS
    c.row(19, "0:12 3:4 1:3 2:45 3:4 0:28")                               # PASS
    c.row(20, "0:9 3:3 1:2 2:54 3:3 0:25")                                # PASS
    c.row(21, "0:7 3:2 1:2 2:60 3:2 0:23")                                # PASS
    c.row(22, "0:5 3:2 1:1 2:65 3:2 0:21")                                # PASS
    c.row(23, "0:4 3:1 1:1 2:69 3:1 0:20")                                # PASS
    for x, y in ((3, 22), (76, 22), (2, 21), (77, 21)):
        c.put(x, y, "3")
    c.row(24, "0:4 3:72 0:20")
    # ---- the lower wall: a beam, paper panels with a lattice, posts ----------------------------------------------------------------------
    c.row(25, "0:12 3:56 0:28")
    for y in (26, 27):
        c.row(y, "0:12 3:1 2:54 3:1 0:28")
    for y in range(28, 49):
        if y in (33, 38, 43, 48):                                        # PASS: rails 33 38 43 48, panels 5 4 4 4 (was rails 33 39: panels 5 5 9); the rail at 48 is a sill
            c.row(y, "0:12 3:1 2:2 2:17 2:2 1:12 2:2 2:17 2:2 3:1 0:28")
        else:
            c.row(y, "0:12 3:1 2:2 1:8 2:1 1:8 2:2 1:12 2:2 1:8 2:1 1:8 2:2 3:1 0:28")
    c.paste(34, 28, NOREN)
    # ---- the veranda.  PASS: row 50 is the lit top plane (paper), row 51 the dark front face, so the deck reads as a platform ---------------
    c.row(49, "0:6 3:68 0:22")
    c.row(50, "0:6 3:1 1:66 3:1 0:22")                                    # PASS
    c.row(51, "0:6 3:1 2:66 3:1 0:22")
    c.row(52, "0:6 3:68 0:22")
    c.paste(34, 53, STONE)
    c.paste(50 if dmg else 48, 53, STONE)                     # DMG: both stepping stones on the same phase of the 8 px grid
    c.paste(1, 36, LANT)                                                  # PASS: two rows higher, its base no longer fuses with the veranda's left end
    # ---- the cherry tree (unchanged) ---------------------------------------------------------------------------------------------------
    c.paste(80, 34, TREE)
    return c


if __name__ == "__main__":
    print(len(build().out()))
